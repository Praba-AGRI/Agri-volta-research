import numpy as np
import pandas as pd
from typing import Dict, Any

from agronomy.et0 import ET0Model

class ETDemandModel:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.et0_model = ET0Model(config)
        
        timestep_cfg = self.config.get('experiment', {}).get('temporal_resolution', {})
        self.timestep_minutes = timestep_cfg.get('timestep_minutes', 5)
        self.timesteps_per_day = 1440 // self.timestep_minutes

    def calculate_zone_demand(self, df_5min: pd.DataFrame, zone_prefix: str) -> pd.DataFrame:
        """
        Calculates localized atmospheric demand for a specific zone (e.g. 'A' or 'B').
        First calculates daily localized demand, then disaggregates to 5-min intervals.
        """
        num_days = len(df_5min) // self.timesteps_per_day
        
        # Calculate daily aggregates for the specific zone
        t_col = f'T_{zone_prefix}'
        rh_col = f'RH_{zone_prefix}'
        u_col = f'u_{zone_prefix}'
        rs_col = f'Rs_{zone_prefix}' # W/m2
        
        # Reshape to (days, timesteps_per_day)
        t_mat = df_5min[t_col].values.reshape(num_days, self.timesteps_per_day)
        rh_mat = df_5min[rh_col].values.reshape(num_days, self.timesteps_per_day)
        u_mat = df_5min[u_col].values.reshape(num_days, self.timesteps_per_day)
        rs_mat = df_5min[rs_col].values.reshape(num_days, self.timesteps_per_day)
        
        t_max = np.max(t_mat, axis=1)
        t_min = np.min(t_mat, axis=1)
        t_mean = np.mean(t_mat, axis=1)
        
        rh_max = np.max(rh_mat, axis=1)
        rh_min = np.min(rh_mat, axis=1)
        
        u2 = np.mean(u_mat, axis=1)
        
        # Convert Rs from W/m2 (5-min average) to MJ/m2/day
        # 1 W/m2 = 1 J/s/m2
        # Sum over day: sum(Rs) * (5 * 60) J/m2 -> / 1e6 MJ/m2
        seconds_per_step = self.timestep_minutes * 60
        rs_daily = np.sum(rs_mat, axis=1) * seconds_per_step / 1e6
        
        df_daily = pd.DataFrame({
            'T_max': t_max,
            'T_min': t_min,
            'T_mean': t_mean,
            'RH_max': rh_max,
            'RH_min': rh_min,
            'u2': u2,
            'Rs': rs_daily
        })
        
        # Calculate localized daily demand using FAO-56 logic but applied to local conditions
        daily_demand = self.et0_model.calculate_daily_et0(df_daily)['ET0'].values
        
        # Disaggregate to 5-minute intervals based on radiation profile
        # w_t = Rs_t / sum(Rs_t) for the day
        # If sum(Rs_t) == 0, distribute evenly during daytime hours (6am - 6pm)
        
        et_5min = np.zeros(len(df_5min))
        
        time_of_day = np.arange(self.timesteps_per_day)
        daylight_mask = (time_of_day >= (6 * 60 // self.timestep_minutes)) & (time_of_day < (18 * 60 // self.timestep_minutes))
        
        for d in range(num_days):
            day_rs = rs_mat[d, :]
            total_rs = np.sum(day_rs)
            
            start_idx = d * self.timesteps_per_day
            end_idx = start_idx + self.timesteps_per_day
            
            if total_rs > 0:
                w_t = day_rs / total_rs
            else:
                w_t = np.zeros(self.timesteps_per_day)
                w_t[daylight_mask] = 1.0 / np.sum(daylight_mask)
                
            et_5min[start_idx:end_idx] = daily_demand[d] * w_t
            
        return pd.DataFrame({
            f'ET_demand_daily_{zone_prefix}': np.repeat(daily_demand, self.timesteps_per_day),
            f'ET_demand_5min_{zone_prefix}': et_5min
        })
