import numpy as np
import pandas as pd
from typing import Dict, Any

class Microclimate:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        mc_cfg = self.config.get('microclimate', {}).get('zone_b', {})
        self.dt_max = mc_cfg.get('air_temperature', {}).get('daytime_cooling_c', {}).get('maximum', 3.5)
        self.dt_night = mc_cfg.get('air_temperature', {}).get('nighttime_buffer_c', {}).get('nominal', 0.5)
        self.drh_max = mc_cfg.get('relative_humidity', {}).get('increase_percent', {}).get('maximum', 12.0)
        
        # Wind mode
        self.wind_mode = mc_cfg.get('wind', {}).get('mode', 'paper_conservative')
        
        # Soil thermal
        soil_cfg = mc_cfg.get('soil_temperature', {})
        self.tau_hours = soil_cfg.get('thermal_response', {}).get('time_constant_hours', 6.0)
        
        timestep_cfg = self.config.get('experiment', {}).get('temporal_resolution', {})
        self.dt_hours = timestep_cfg.get('timestep_minutes', 5) / 60.0
        
    def _calculate_vpd(self, t_c: np.ndarray, rh: np.ndarray) -> np.ndarray:
        """Calculate Vapor Pressure Deficit in kPa."""
        # Saturation vapor pressure (Tetens formula)
        es = 0.6108 * np.exp((17.27 * t_c) / (t_c + 237.3))
        # Actual vapor pressure
        ea = es * (rh / 100.0)
        vpd = np.maximum(0.0, es - ea)
        return vpd

    def calculate_microclimate(self, weather_df: pd.DataFrame, rad_df: pd.DataFrame, shading_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates Zone B microclimate variables and soil temperatures.
        Returns a DataFrame with both Zone A and Zone B extended variables.
        """
        num_timesteps = len(weather_df)
        
        t_a = weather_df['T_A'].values
        rh_a = weather_df['RH_A'].values
        p = weather_df['P_A'].values
        u_a = weather_df['u_A'].values
        
        rs_a = rad_df['Rs_A'].values
        rs_b = rad_df['Rs_B'].values
        sf = shading_df['shade_fraction'].values
        
        # Air Temperature
        # Delta T_B depends on shade fraction and incoming radiation relative to a peak (e.g. 1000 W/m2)
        # Nighttime: buffer effect independent of Rs
        is_day = rs_a > 0
        
        dt_b = np.zeros(num_timesteps)
        
        # Daytime cooling
        # Max cooling when max shaded and max radiation
        # The geometric sf physically maxes out around 0.32 when the sun is high.
        # To ensure the shaded microclimate realizes the configured 2.0-3.5 C cooling,
        # we normalize the shading effect relative to the panel area footprint.
        effective_sf = np.clip(sf / 0.32, 0.0, 1.0)
        rad_factor = np.clip(rs_a / 1000.0, 0.0, 1.0)
        dt_b[is_day] = self.dt_max * effective_sf[is_day] * rad_factor[is_day]
        
        # Nighttime buffering
        # Panels trap longwave radiation, warming the air slightly
        dt_b[~is_day] = -self.dt_night * effective_sf[~is_day]  # Negative delta means T_B > T_A
        
        t_b = t_a - dt_b
        
        # Relative Humidity
        # RH increases as T drops, and due to reduced mixing under panels.
        # We model this physically or empirically. Empirically:
        drh = np.zeros(num_timesteps)
        drh[is_day] = self.drh_max * effective_sf[is_day] * rad_factor[is_day]
        rh_b = np.clip(rh_a + drh, 0.0, 100.0)
        
        # Wind
        if self.wind_mode == 'paper_conservative':
            u_b = np.copy(u_a)
        else:
            u_b = u_a * (1.0 - 0.2 * sf) # Example physical attenuation
            
        # VPD
        vpd_a = self._calculate_vpd(t_a, rh_a)
        vpd_b = self._calculate_vpd(t_b, rh_b)
        
        # Soil Temperature
        # T*_soil = f(T_air, Rs)
        # Simplified surface energy balance proxy:
        t_star_a = t_a + 0.015 * rs_a
        t_star_b = t_b + 0.015 * rs_b
        
        tsoil_a = np.zeros(num_timesteps)
        tsoil_b = np.zeros(num_timesteps)
        
        # Initialize
        tsoil_a[0] = t_star_a[0]
        tsoil_b[0] = t_star_b[0]
        
        factor = self.dt_hours / self.tau_hours
        
        for t in range(1, num_timesteps):
            tsoil_a[t] = tsoil_a[t-1] + factor * (t_star_a[t-1] - tsoil_a[t-1])
            tsoil_b[t] = tsoil_b[t-1] + factor * (t_star_b[t-1] - tsoil_b[t-1])
            
        df = pd.DataFrame({
            'T_B': t_b,
            'RH_B': rh_b,
            'u_B': u_b,
            'VPD_A': vpd_a,
            'VPD_B': vpd_b,
            'Tsoil_A': tsoil_a,
            'Tsoil_B': tsoil_b
        })
        
        # Combine with original weather dataframe? No, keep it modular and let orchestrator combine.
        return df
