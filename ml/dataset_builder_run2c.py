import pandas as pd
import numpy as np
import torch
from typing import Dict, Any, Tuple

from agronomy.soil_water import SoilWaterBalance

class ForecastErrorGenerator:
    """
    Generates physically structured weather forecast errors to avoid oracle leakage.
    Uses fixed seed policy for reproducibility.
    """
    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)

    def generate_noisy_forecast(self, df_future_288: pd.DataFrame, zone_prefix: str = 'B') -> Dict[str, float]:
        """
        Takes the future 288 timesteps (24 hours) and creates a noisy, realistic 24-h forecast summary.
        """
        p_col = f'P_{zone_prefix}'
        t_col = f'T_{zone_prefix}'
        rh_col = f'RH_{zone_prefix}'
        rs_col = f'Rs_{zone_prefix}'
        u_col = f'u_{zone_prefix}'

        true_P_sum = df_future_288[p_col].sum()
        true_T_mean = df_future_288[t_col].mean()
        true_RH_mean = df_future_288[rh_col].mean()
        true_Rs_sum = df_future_288[rs_col].sum() * 300 / 1e6 # MJ/m2
        true_u_mean = df_future_288[u_col].mean()

        # 1. Structured Rain Noise (Zero inflation / false rain / intensity error)
        if true_P_sum == 0.0:
            # 10% chance of false rain forecast
            if self.rng.rand() < 0.10:
                fc_P = self.rng.uniform(0.5, 3.0)
            else:
                fc_P = 0.0
        else:
            # 15% chance of missing small rain
            if true_P_sum < 2.0 and self.rng.rand() < 0.15:
                fc_P = 0.0
            else:
                # Multiplicative intensity noise ~ N(1.0, 0.2)
                scale = max(0.2, self.rng.normal(1.0, 0.2))
                fc_P = true_P_sum * scale

        # 2. Temperature Noise ~ N(0, 1.2 C)
        fc_T = true_T_mean + self.rng.normal(0.0, 1.2)

        # 3. RH Noise ~ N(0, 4.0%)
        fc_RH = np.clip(true_RH_mean + self.rng.normal(0.0, 4.0), 10.0, 100.0)

        # 4. Radiation Noise ~ N(1.0, 0.12)
        rs_scale = max(0.3, self.rng.normal(1.0, 0.12))
        fc_Rs = true_Rs_sum * rs_scale

        # 5. Wind Noise ~ N(0, 0.3 m/s)
        fc_u = max(0.1, true_u_mean + self.rng.normal(0.0, 0.3))

        # Derive VPD from forecast T and RH causally
        e_s = 0.61078 * np.exp((17.27 * fc_T) / (fc_T + 237.3))
        e_a = e_s * (fc_RH / 100.0)
        fc_VPD = max(0.0, e_s - e_a)

        return {
            'P_fc': fc_P,
            'T_fc': fc_T,
            'RH_fc': fc_RH,
            'Rs_fc': fc_Rs,
            'u_fc': fc_u,
            'VPD_fc': fc_VPD
        }

class CounterfactualLabelEngine:
    """
    Generates exact physical labels by running forward simulations of SoilWaterBalance
    and solving for IR* using bisection search.
    """
    def __init__(self, config: Dict[str, Any], theta_target: float = 0.27, z_r: float = 600.0):
        self.swb = SoilWaterBalance(config)
        self.theta_target = theta_target
        self.z_r = z_r

    def compute_counterfactual_and_ir_star(
        self, 
        initial_theta: float, 
        p_surface_24h: np.ndarray, 
        et_demand_24h: np.ndarray, 
        kc_24h: np.ndarray
    ) -> Tuple[float, float, float, float]:
        """
        Runs 24h simulation (288 steps) from initial_theta.
        Returns: (theta_24h_no_ir, etc_24h_sum, deficit_24h_mm, ir_star_mm)
        """
        # 1. Counterfactual A: No Irrigation (IR = 0)
        df_no_ir = self.swb.simulate_zone(
            p_surface=p_surface_24h,
            et_demand=et_demand_24h,
            kc=kc_24h,
            initial_theta=initial_theta
        )
        theta_24h_no_ir = df_no_ir['theta_v'].iloc[-1]
        etc_24h_sum = df_no_ir['ETc_mm'].sum()
        deficit_24h_mm = max(0.0, self.theta_target - theta_24h_no_ir) * self.z_r

        # If terminal moisture without irrigation already reaches or exceeds target, IR* = 0
        if theta_24h_no_ir >= self.theta_target - 1e-5:
            return theta_24h_no_ir, etc_24h_sum, deficit_24h_mm, 0.0, True

        # 2. Bisection Search for Minimum IR* applied at step 0
        ir_low = 0.0
        ir_high = 80.0 # Maximum safe single irrigation dose cap (mm)
        tol = 0.01 # mm tolerance

        def eval_ir(ir_val: float) -> float:
            p_with_ir = p_surface_24h.copy()
            if ir_val > 0:
                max_rate = 1.8 # mm per 5-min step (21.6 mm/hr < Ksat 25 mm/hr)
                n_full = int(ir_val // max_rate)
                rem = ir_val - (n_full * max_rate)
                if n_full > 0:
                    p_with_ir[:min(288, n_full)] += max_rate
                if rem > 0 and n_full < 288:
                    p_with_ir[n_full] += rem
            df_sim = self.swb.simulate_zone(
                p_surface=p_with_ir,
                et_demand=et_demand_24h,
                kc=kc_24h,
                initial_theta=initial_theta
            )
            # We target peak soil moisture reaching Field Capacity (0.27)
            return df_sim['theta_v'].max()

        # Verify upper bound sufficiency
        max_theta = eval_ir(ir_high)
        if max_theta < self.theta_target - 1e-5:
            # Target unreachable even with 80mm
            return theta_24h_no_ir, etc_24h_sum, deficit_24h_mm, ir_high, False

        # Monotonicity check
        theta_low = eval_ir(ir_low)
        theta_mid_check = eval_ir(10.0)
        if theta_mid_check < theta_low - 1e-4:
            raise ValueError(f"Soil water balance non-monotonicity detected! IR=0 -> {theta_low}, IR=10 -> {theta_mid_check}")

        # Bisection loop
        for _ in range(15):
            ir_mid = (ir_low + ir_high) / 2.0
            theta_mid = eval_ir(ir_mid)

            if abs(theta_mid - self.theta_target) < 1e-5 or (ir_high - ir_low) < tol:
                break

            if theta_mid >= self.theta_target:
                ir_high = ir_mid
            else:
                ir_low = ir_mid

        ir_star = (ir_low + ir_high) / 2.0
        return theta_24h_no_ir, etc_24h_sum, deficit_24h_mm, ir_star, True

class DatasetBuilder2C:
    def __init__(self, sensor_path: str, mode: str = 'operational', target_zone: str = 'B'):
        """
        mode: 'oracle' or 'operational'
        """
        self.sensor_path = sensor_path
        self.mode = mode
        self.target_zone = target_zone
        self.df_raw = pd.read_parquet(sensor_path)
        
        # Config for SWB
        self.config = {
            'soil': {
                'depth_mm': 600.0,
                'hydraulic_properties': {
                    'theta_field_capacity': {'nominal': 0.27},
                    'theta_wilting_point': {'nominal': 0.12},
                    'theta_saturation': {'nominal': 0.42},
                    'saturated_hydraulic_conductivity_mm_hr': 25.0
                }
            },
            'experiment': {'temporal_resolution': {'timestep_minutes': 5}}
        }
        
        self.label_engine = CounterfactualLabelEngine(self.config, theta_target=0.27, z_r=600.0)
        self.error_gen = ForecastErrorGenerator(seed=42)

    def build_dataset(self, stride: int = 12, filter_unreachable: bool = True) -> Dict[str, np.ndarray]:
        """
        Builds dataset with historical 24h sequence, forecast 24h summary features, and exact counterfactual labels.
        stride: 12 steps = 1 hour decision interval
        """
        df = self.df_raw.copy()
        
        # Feature columns for history
        theta_col = f'theta_v_{self.target_zone}'
        p_col = f'P_{self.target_zone}'
        t_col = f'T_{self.target_zone}'
        rh_col = f'RH_{self.target_zone}'
        rs_col = f'Rs_{self.target_zone}'
        vpd_col = f'VPD_{self.target_zone}'
        tsoil_col = f'Tsoil_{self.target_zone}'
        et_col = f'ET_demand_5min_{self.target_zone}'

        window = 288 # 24 hours
        horizon = 288 # 24 hours
        N = len(df)

        X_hist_list = []
        X_fc_list = []
        y_theta_list = []
        y_etc_list = []
        y_deficit_list = []
        y_ir_star_list = []
        reachable_list = []
        timestamps_list = []

        print(f"Generating RUN 2C dataset (Mode: {self.mode}, Stride: {stride} steps)...")

        # Assume constant Kc = 1.0 for counterfactual label generation (or dynamic if available)
        kc_dummy = np.ones(horizon)

        for i in range(window - 1, N - horizon, stride):
            t_origin = i
            t_start = t_origin - window + 1
            t_end = t_origin + 1
            t_future_end = t_origin + horizon + 1

            # 1. Historical sequence (shape: 288, 7)
            sub_hist = df.iloc[t_start:t_end]
            hist_arr = np.column_stack([
                sub_hist[theta_col].values,
                sub_hist[p_col].values,
                sub_hist[t_col].values,
                sub_hist[rh_col].values,
                sub_hist[rs_col].values,
                sub_hist[vpd_col].values,
                sub_hist[tsoil_col].values
            ])

            # 2. Weather Forecast (Next 288 steps)
            sub_future = df.iloc[t_end:t_future_end]
            if len(sub_future) < 288:
                break

            if self.mode == 'oracle':
                fc_dict = {
                    'P_fc': sub_future[p_col].sum(),
                    'T_fc': sub_future[t_col].mean(),
                    'RH_fc': sub_future[rh_col].mean(),
                    'Rs_fc': sub_future[rs_col].sum() * 300 / 1e6,
                    'u_fc': sub_future[f'u_{self.target_zone}'].mean(),
                    'VPD_fc': sub_future[vpd_col].mean()
                }
            else:
                fc_dict = self.error_gen.generate_noisy_forecast(sub_future, zone_prefix=self.target_zone)

            fc_arr = np.array([
                fc_dict['P_fc'], fc_dict['T_fc'], fc_dict['RH_fc'],
                fc_dict['Rs_fc'], fc_dict['u_fc'], fc_dict['VPD_fc']
            ], dtype=np.float32)

            # 3. Ground-truth Counterfactual Label Generation
            init_theta = sub_hist[theta_col].iloc[-1]
            p_fut = sub_future[p_col].values
            et_fut = sub_future[et_col].values

            theta_24h, etc_24h, deficit_24h, ir_star, is_reachable = self.label_engine.compute_counterfactual_and_ir_star(
                initial_theta=init_theta,
                p_surface_24h=p_fut,
                et_demand_24h=et_fut,
                kc_24h=kc_dummy
            )

            X_hist_list.append(hist_arr)
            X_fc_list.append(fc_arr)
            y_theta_list.append(theta_24h)
            y_etc_list.append(etc_24h)
            y_deficit_list.append(deficit_24h)
            y_ir_star_list.append(ir_star)
            reachable_list.append(is_reachable)
            timestamps_list.append(df['timestamp'].iloc[t_origin])

        X_h_arr = np.array(X_hist_list, dtype=np.float32)
        X_f_arr = np.array(X_fc_list, dtype=np.float32)
        y_th_arr = np.array(y_theta_list, dtype=np.float32)
        y_et_arr = np.array(y_etc_list, dtype=np.float32)
        y_def_arr = np.array(y_deficit_list, dtype=np.float32)
        y_ir_arr = np.array(y_ir_star_list, dtype=np.float32)
        reach_arr = np.array(reachable_list, dtype=bool)
        ts_arr = np.array(timestamps_list)

        print(f"Dataset generated! Total origins: {len(y_ir_arr)} | Reachable: {np.sum(reach_arr)} | Unreachable: {np.sum(~reach_arr)} ({np.mean(reach_arr)*100:.1f}%)")

        if filter_unreachable:
            mask = reach_arr
            return {
                'X_hist': X_h_arr[mask],
                'X_fc': X_f_arr[mask],
                'y_theta': y_th_arr[mask],
                'y_etc': y_et_arr[mask],
                'y_deficit': y_def_arr[mask],
                'y_ir_star': y_ir_arr[mask],
                'y_event': (y_ir_arr[mask] > 0.05).astype(np.float32),
                'timestamps': ts_arr[mask],
                'target_reachable': reach_arr[mask],
                'total_origins': len(y_ir_arr),
                'n_reachable': int(np.sum(reach_arr)),
                'n_unreachable': int(np.sum(~reach_arr))
            }
        else:
            return {
                'X_hist': X_h_arr,
                'X_fc': X_f_arr,
                'y_theta': y_th_arr,
                'y_etc': y_et_arr,
                'y_deficit': y_def_arr,
                'y_ir_star': y_ir_arr,
                'y_event': (y_ir_arr > 0.05).astype(np.float32),
                'timestamps': ts_arr,
                'target_reachable': reach_arr,
                'total_origins': len(y_ir_arr),
                'n_reachable': int(np.sum(reach_arr)),
                'n_unreachable': int(np.sum(~reach_arr))
            }
