import numpy as np
import pandas as pd
from typing import Dict, Any

class SoilWaterBalance:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        soil_cfg = self.config.get('soil', {})
        
        self.z_r = soil_cfg.get('depth_mm', 600.0)
        props = soil_cfg.get('hydraulic_properties', {})
        self.theta_fc = props.get('theta_field_capacity', {}).get('nominal', 0.27)
        self.theta_wp = props.get('theta_wilting_point', {}).get('nominal', 0.12)
        self.theta_sat = props.get('theta_saturation', {}).get('nominal', 0.42)
        
        # Saturated hydraulic conductivity (mm/hr -> mm/5min)
        ksat_hr = props.get('saturated_hydraulic_conductivity_mm_hr', 25.0)
        timestep = self.config.get('experiment', {}).get('temporal_resolution', {}).get('timestep_minutes', 5)
        self.ksat_step = ksat_hr * (timestep / 60.0)
        
        init = soil_cfg.get('initial_conditions', {})
        self.theta_init_a = init.get('zone_a_vvc', 0.15)
        self.theta_init_b = init.get('zone_b_vvc', 0.15)
        
        # Depletion fraction for no stress (p) - FAO-56 typical for cowpea is ~0.45
        self.p_depletion = 0.45

    def _calculate_ks(self, theta: float) -> float:
        """Calculate water stress coefficient Ks."""
        theta_c = self.theta_fc - self.p_depletion * (self.theta_fc - self.theta_wp)
        
        if theta >= theta_c:
            return 1.0
        elif theta <= self.theta_wp:
            return 0.0
        else:
            return (theta - self.theta_wp) / (theta_c - self.theta_wp)

    def simulate_zone(self, p_surface: np.ndarray, et_demand: np.ndarray, kc: np.ndarray, 
                      policy=None, sensor_noise: np.ndarray = None, env_features: Dict[str, np.ndarray] = None,
                      initial_theta: float = None) -> pd.DataFrame:
        """
        Simulates the 5-minute soil water balance for a single zone with dynamic policy evaluation.
        """
        num_steps = len(p_surface)
        irrigation = np.zeros(num_steps)
            
        theta = np.zeros(num_steps)
        s_mm = np.zeros(num_steps)
        runoff = np.zeros(num_steps)
        drainage = np.zeros(num_steps)
        etc = np.zeros(num_steps)
        ks_arr = np.zeros(num_steps)
        p_eff = np.zeros(num_steps)
        decision_types = np.array([None] * num_steps, dtype=object)
        forecast_thetas = np.zeros(num_steps)
        forecast_thetas[:] = np.nan
        
        if initial_theta is None:
            initial_theta = self.theta_fc
            
        s_t = initial_theta * self.z_r
        s_fc = self.theta_fc * self.z_r
        s_sat = self.theta_sat * self.z_r
        s_wp = self.theta_wp * self.z_r
        
        # Start time assuming 2026-06-01 00:00:00 as start
        start_time = pd.Timestamp("2026-06-01 00:00:00")
        
        for t in range(num_steps):
            timestamp = start_time + pd.Timedelta(minutes=5*t)
            
            # 1. Available water at start of step
            theta_t = s_t / self.z_r
            theta[t] = theta_t
            
            # Policy evaluation (once per day at decision hour)
            if policy is not None and t >= 288:
                if timestamp.hour == policy.decision_hour and timestamp.minute == 0:
                    # Construct state and env_history
                    current_sensor = theta_t
                    if sensor_noise is not None:
                        current_sensor += sensor_noise[t]
                        
                    # Calculate 7-day ET0 (past completed days)
                    # A completed day is 288 steps. 7 days is 2016 steps.
                    # At 06:00, the last completed day ended 6 hours ago (at midnight).
                    # Actually, we can just aggregate ET_demand from the past 7 days (t-3456 to t-1440)
                    # wait, 6 hours is 72 steps. So midnight was at t-72.
                    # 7 days before midnight is t-72 - (7 * 288) = t-2088.
                    et0_mean_7d = 0.0
                    et0_current_24h = 0.0
                    if t >= 2088:
                        et0_mean_7d = np.sum(et_demand[t-2088:t-72]) / 7.0
                    if t >= 288:
                        et0_current_24h = np.sum(et_demand[t-288:t])
                        
                    env_hist = {
                        'ETc_24h': etc[t-288:t],
                        'P_eff_24h': p_eff[t-288:t],
                        'ET0_mean_7d': et0_mean_7d,
                        'ET0_current_24h': et0_current_24h,
                        'env_features': env_features
                    }
                    
                    if env_features is not None:
                        # Construct X_seq for AI: shape (1, 288, 24)
                        # Order: T, RH, P, Tsoil, theta_v, Rs, solar_zenith_deg, solar_azimuth_deg, solar_elevation_deg, 
                        # shade_fraction, full_shade_flag, VPD, zone_A_flag, T_missing, RH_missing, P_missing, 
                        # Tsoil_missing, theta_v_missing, daily_GDD, cumulative_GDD, sin_hour, cos_hour, sin_day, cos_day
                        X_seq = np.zeros((1, 288, 24))
                        past_theta = theta[t-288:t].copy()
                        if sensor_noise is not None:
                            past_theta += sensor_noise[t-288:t]
                            
                        # Temporal variables
                        times = [start_time + pd.Timedelta(minutes=5*i) for i in range(t-288, t)]
                        hours = np.array([ts.hour + ts.minute / 60.0 for ts in times])
                        days_of_year = np.array([ts.dayofyear for ts in times])
                        
                        sin_h = np.sin(2 * np.pi * hours / 24.0)
                        cos_h = np.cos(2 * np.pi * hours / 24.0)
                        sin_d = np.sin(2 * np.pi * days_of_year / 365.25)
                        cos_d = np.cos(2 * np.pi * days_of_year / 365.25)
                        
                        # Populate array
                        X_seq[0, :, 0] = env_features['T'][t-288:t]
                        X_seq[0, :, 1] = env_features['RH'][t-288:t]
                        X_seq[0, :, 2] = env_features['P'][t-288:t]
                        X_seq[0, :, 3] = env_features['Tsoil'][t-288:t]
                        X_seq[0, :, 4] = past_theta
                        X_seq[0, :, 5] = env_features['Rs'][t-288:t]
                        X_seq[0, :, 6] = env_features['solar_zenith_deg'][t-288:t]
                        X_seq[0, :, 7] = env_features['solar_azimuth_deg'][t-288:t]
                        X_seq[0, :, 8] = env_features['solar_elevation_deg'][t-288:t]
                        X_seq[0, :, 9] = env_features['shade_fraction'][t-288:t]
                        X_seq[0, :, 10] = env_features['full_shade_flag'][t-288:t]
                        X_seq[0, :, 11] = env_features['VPD'][t-288:t]
                        X_seq[0, :, 12] = 0.0 # zone_A_flag (AI is Zone B)
                        # indices 13-17 are missing flags, initialized to 0.0
                        X_seq[0, :, 18] = env_features['daily_GDD'][t-288:t]
                        X_seq[0, :, 19] = env_features['cumulative_GDD'][t-288:t]
                        X_seq[0, :, 20] = sin_h
                        X_seq[0, :, 21] = cos_h
                        X_seq[0, :, 22] = sin_d
                        X_seq[0, :, 23] = cos_d
                        
                        env_hist['X_seq'] = X_seq
                        
                    ir_vol, meta = policy.evaluate(t, timestamp, {'theta_sensor': current_sensor}, env_hist)
                    irrigation[t] = ir_vol
                    if 'decision_type' in meta:
                        decision_types[t] = meta['decision_type']
                    if 'forecast_theta' in meta:
                        forecast_thetas[t] = meta['forecast_theta']
            
            # 2. Water stress
            ks = self._calculate_ks(theta_t)
            ks_arr[t] = ks
            
            # 3. Crop Evapotranspiration
            et_c = et_demand[t] * kc[t] * ks
            # Ensure we don't extract below WP
            et_c = min(et_c, max(0.0, s_t - s_wp))
            etc[t] = et_c
            
            # 4. Infiltration and Runoff
            water_in = p_surface[t] + irrigation[t]
            infiltrated = min(water_in, self.ksat_step)
            runoff[t] = max(0.0, water_in - infiltrated)
            
            p_eff[t] = p_surface[t] - max(0.0, p_surface[t] - self.ksat_step)
            
            # 5. Update Storage
            s_t = s_t + infiltrated - et_c
            
            # 6. Deep Percolation (Drainage)
            if s_t > s_fc:
                drainage[t] = s_t - s_fc
                s_t = s_fc
                
            s_mm[t] = s_t

        df = pd.DataFrame({
            'theta_v': theta,
            'S_mm': s_mm,
            'Runoff_mm': runoff,
            'Drainage_mm': drainage,
            'ETc_mm': etc,
            'Ks': ks_arr,
            'Irrigation_mm': irrigation,
            'decision_type': decision_types,
            'forecast_theta': forecast_thetas
        })
        
        # Calculate AI forecast error
        # future_theta_24h is the actual theta_v 24h (288 steps) after the decision time
        # i.e., what it forecast. Note the forecast is for the end of the next 24h.
        df['future_theta_24h'] = df['theta_v'].shift(-288)
        df['forecast_error'] = df['forecast_theta'] - df['future_theta_24h']
        
        return df
