import numpy as np
import pandas as pd
from typing import Dict, Any
import pvlib

from simulation.weather_engine import WeatherRegime

class SpectralEngine:
    def __init__(self, config: Dict[str, Any], rng: np.random.Generator):
        self.config = config
        self.rng = rng
        
        rad_cfg = self.config.get('radiation', {})
        zb_rad = rad_cfg.get('zone_b', {})
        self.t_pv_dir = zb_rad.get('direct_beam', {}).get('panel_transmission', {}).get('nominal', 0.60)
        self.t_pv_dif = zb_rad.get('diffuse', {}).get('transmission', {}).get('nominal', 0.85)
        


    def calculate_radiation(self, weather_df: pd.DataFrame, solar_df: pd.DataFrame, shading_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates radiation and spectral components for Zone A and Zone B.
        """
        # Calculate clear sky GHI using a simple empirical model (Haurwitz)
        zenith = solar_df['apparent_zenith_deg'].values
        # Haurwitz model for clear sky GHI: 1098 * cos(Z) * exp(-0.057 / cos(Z))
        # We use pvlib or just manual since it's simple
        cos_z = np.cos(np.radians(zenith))
        cos_z = np.clip(cos_z, 0, 1)
        
        # Clear sky GHI
        ghi_clear = np.zeros_like(cos_z)
        day_mask = cos_z > 0
        ghi_clear[day_mask] = 1098.0 * cos_z[day_mask] * np.exp(-0.057 / cos_z[day_mask])
        
        # Cloud attenuation based on weather regime
        regimes = weather_df['cloud_state'].values
        cloud_factor = np.ones_like(ghi_clear)
        cloud_factor[regimes == WeatherRegime.PARTLY_CLOUDY] = 0.75
        cloud_factor[regimes == WeatherRegime.OVERCAST] = 0.35
        cloud_factor[regimes == WeatherRegime.RAIN] = 0.15
        cloud_factor[regimes == WeatherRegime.HEAVY_RAIN] = 0.05
        
        # Zone A total irradiance
        ghi_a = ghi_clear * cloud_factor
        
        # Decompose into Direct and Diffuse using Erbs model (needs Pandas Series with DatetimeIndex)
        # We can just implement a simplified Erbs or a rule-of-thumb:
        # kt = GHI / GHI_clear
        # For simplicity, if kt > 0.8 mostly direct, if kt < 0.3 mostly diffuse
        kt = np.zeros_like(ghi_a)
        kt[ghi_clear > 0] = ghi_a[ghi_clear > 0] / ghi_clear[ghi_clear > 0]
        kt = np.clip(kt, 0, 1)
        
        diffuse_fraction = np.zeros_like(kt)
        diffuse_fraction[kt <= 0.22] = 1.0 - 0.09 * kt[kt <= 0.22]
        diffuse_fraction[(kt > 0.22) & (kt <= 0.8)] = 0.9511 - 0.1604 * kt[(kt > 0.22) & (kt <= 0.8)] + 4.388 * kt[(kt > 0.22) & (kt <= 0.8)]**2 - 16.638 * kt[(kt > 0.22) & (kt <= 0.8)]**3 + 12.336 * kt[(kt > 0.22) & (kt <= 0.8)]**4
        diffuse_fraction[kt > 0.8] = 0.165
        
        # Ensure it's bounded and handles night
        diffuse_fraction = np.clip(diffuse_fraction, 0, 1)
        diffuse_fraction[~day_mask] = 1.0
        
        dhi_a = ghi_a * diffuse_fraction
        dni_a = (ghi_a - dhi_a) # Technically DNI * cos(Z), this is direct horizontal
        
        # Zone B Radiation
        sf = shading_df['shade_fraction'].values
        
        # R_B = R_direct,A * (1 - Sf) + R_direct,A * Sf * T_PV
        dni_b = dni_a * (1.0 - sf) + dni_a * sf * self.t_pv_dir
        dhi_b = dhi_a * self.t_pv_dif
        ghi_b = dni_b + dhi_b
        
        df = pd.DataFrame({
            'Rs_A': ghi_a,
            'Rs_dir_A': dni_a,
            'Rs_dif_A': dhi_a,
            'Rs_B': ghi_b,
            'Rs_dir_B': dni_b,
            'Rs_dif_B': dhi_b,
        })
        
        # AS7341 spectral channels removed per user instructions
        return df
