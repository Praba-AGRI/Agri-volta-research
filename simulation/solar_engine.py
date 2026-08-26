import numpy as np
import pandas as pd
import pvlib
from typing import Dict, Any

class SolarEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        loc_cfg = self.config.get('experiment', {}).get('location', {})
        self.latitude = loc_cfg.get('latitude_deg', 11.016)
        self.longitude = loc_cfg.get('longitude_deg', 76.971)
        self.timezone = loc_cfg.get('timezone', 'Asia/Kolkata')
        self.elevation = loc_cfg.get('elevation_m', 0.0) or 0.0
        
        # We define a base starting date for the season. For generic simulation, any date works, 
        # but let's use a standard summer date for Coimbatore.
        self.start_date = pd.Timestamp("2026-06-01 00:00:00", tz=self.timezone)
        
        self.timestep_minutes = self.config.get('experiment', {}).get('temporal_resolution', {}).get('timestep_minutes', 5)

    def calculate_solar_position(self, num_timesteps: int) -> pd.DataFrame:
        """
        Calculates solar position using pvlib for the given number of timesteps.
        """
        times = pd.date_range(
            start=self.start_date,
            periods=num_timesteps,
            freq=f'{self.timestep_minutes}min'
        )
        
        location = pvlib.location.Location(
            self.latitude,
            self.longitude,
            tz=self.timezone,
            altitude=self.elevation
        )
        
        solar_position = location.get_solarposition(times)
        
        # We want to extract the key components and return a simpler DataFrame
        df = pd.DataFrame({
            'solar_zenith_deg': solar_position['zenith'].values,
            'solar_elevation_deg': solar_position['elevation'].values,
            'solar_azimuth_deg': solar_position['azimuth'].values,
            'apparent_zenith_deg': solar_position['apparent_zenith'].values,
        })
        
        # Calculate air mass
        df['air_mass'] = pvlib.atmosphere.get_relative_airmass(df['apparent_zenith_deg'])
        # Handle NA or negative values for air mass near/below horizon
        df['air_mass'] = df['air_mass'].fillna(0.0)
        df.loc[df['solar_elevation_deg'] <= 0, 'air_mass'] = 0.0

        return df
