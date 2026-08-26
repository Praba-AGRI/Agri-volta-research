import numpy as np
import pandas as pd
from typing import Dict, Any

from core.constants import PSYCHROMETRIC_CONSTANT, LATENT_HEAT_VAPORIZATION

class ET0Model:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        loc_cfg = self.config.get('experiment', {}).get('location', {})
        self.elevation = loc_cfg.get('elevation_m', 400.0) or 400.0
        self.latitude = loc_cfg.get('latitude_deg', 11.016)
        
        # Calculate standard pressure and psychrometric constant for elevation
        # P = 101.3 * ((293 - 0.0065 * z) / 293)**5.26
        self.pressure = 101.3 * ((293 - 0.0065 * self.elevation) / 293)**5.26
        self.gamma = 0.000665 * self.pressure # Psychrometric constant (kPa/°C)

    def calculate_daily_et0(self, df_daily: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates daily standardized FAO-56 Penman-Monteith reference ET0.
        Requires daily aggregated weather: T_max, T_min, T_mean, RH_max, RH_min, u2, Rs
        """
        t_max = df_daily['T_max'].values
        t_min = df_daily['T_min'].values
        t_mean = df_daily['T_mean'].values
        rh_max = df_daily['RH_max'].values
        rh_min = df_daily['RH_min'].values
        u2 = df_daily['u2'].values
        rs = df_daily['Rs'].values # MJ/m2/day
        
        # Slope of saturation vapor pressure curve (Delta) in kPa/°C
        delta = 4098 * (0.6108 * np.exp(17.27 * t_mean / (t_mean + 237.3))) / (t_mean + 237.3)**2
        
        # Saturation vapor pressure
        e_tmax = 0.6108 * np.exp(17.27 * t_max / (t_max + 237.3))
        e_tmin = 0.6108 * np.exp(17.27 * t_min / (t_min + 237.3))
        es = (e_tmax + e_tmin) / 2.0
        
        # Actual vapor pressure
        ea = (e_tmin * (rh_max / 100.0) + e_tmax * (rh_min / 100.0)) / 2.0
        
        # Vapor pressure deficit
        vpd = np.maximum(0.0, es - ea)
        
        # Net radiation (Rn)
        # For simplicity, we approximate net radiation. 
        # In a full model, Rn = Rns - Rnl.
        # Albedo for reference crop = 0.23
        rns = (1 - 0.23) * rs
        
        # Net longwave radiation (simplified FAO-56)
        # Clear sky radiation (Rso) approximation
        z = self.elevation
        rso = (0.75 + 2 * 10**-5 * z) * 37.6 # Approximate Ra * 0.75 (Ra ~ 37.6 MJ/m2/d for 11 N in summer)
        
        rs_rso = np.clip(rs / rso, 0.3, 1.0)
        
        stefan_boltzmann = 4.903e-9 # MJ K-4 m-2 d-1
        t_max_k = t_max + 273.16
        t_min_k = t_min + 273.16
        rnl = stefan_boltzmann * ((t_max_k**4 + t_min_k**4) / 2) * (0.34 - 0.14 * np.sqrt(ea)) * (1.35 * rs_rso - 0.35)
        
        rn = rns - rnl
        
        # Soil heat flux (G) is approx 0 for daily intervals
        g = 0.0
        
        # FAO-56 Penman-Monteith equation
        numerator = 0.408 * delta * (rn - g) + self.gamma * (900 / (t_mean + 273)) * u2 * vpd
        denominator = delta + self.gamma * (1 + 0.34 * u2)
        
        et0 = numerator / denominator
        et0 = np.maximum(0.0, et0)
        
        result_df = pd.DataFrame({'ET0': et0}, index=df_daily.index)
        return result_df
