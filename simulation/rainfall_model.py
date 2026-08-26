import numpy as np
import pandas as pd
from typing import Dict, Any

from simulation.weather_engine import WeatherRegime

class RainfallModel:
    def __init__(self, config: Dict[str, Any], rng: np.random.Generator):
        self.config = config
        self.rng = rng
        self.timestep_minutes = self.config.get('experiment', {}).get('temporal_resolution', {}).get('timestep_minutes', 5)

    def generate_incident_rainfall(self, weather_df: pd.DataFrame, mode: str = "stochastic") -> np.ndarray:
        """
        Generates incident rainfall (mm per timestep) based on weather regimes.
        """
        num_timesteps = len(weather_df)
        rain_incident = np.zeros(num_timesteps)
        regimes = weather_df['cloud_state'].values
        
        if mode == "smoke":
            # Deterministic rain event during 15-17 h
            # 2 hours = 24 timesteps. Total depth 15 mm. 15/24 = 0.625 mm/timestep
            rain_mask = (regimes == WeatherRegime.RAIN) | (regimes == WeatherRegime.HEAVY_RAIN)
            rain_incident[rain_mask] = 0.625
            return rain_incident

        # Identify contiguous blocks of rain
        in_rain = False
        event_start = 0
        
        # lognormal params for event depth (e.g. mean 8, sd 9)
        # Using approximation for lognormal mu and sigma from mean and variance
        mean_mm = self.config.get('weather', {}).get('rainfall', {}).get('event_depth_distribution', {}).get('mean_mm', 8.0)
        sd_mm = self.config.get('weather', {}).get('rainfall', {}).get('event_depth_distribution', {}).get('sd_mm', 9.0)
        max_event_mm = self.config.get('weather', {}).get('rainfall', {}).get('event_depth_distribution', {}).get('max_event_mm', 45.0)
        
        var_mm = sd_mm**2
        sigma2 = np.log(var_mm / (mean_mm**2) + 1)
        mu = np.log(mean_mm) - sigma2 / 2
        sigma = np.sqrt(sigma2)

        for t in range(num_timesteps):
            r = regimes[t]
            is_rain_regime = (r == WeatherRegime.RAIN) or (r == WeatherRegime.HEAVY_RAIN)
            
            if is_rain_regime and not in_rain:
                in_rain = True
                event_start = t
            elif not is_rain_regime and in_rain:
                in_rain = False
                event_end = t
                duration = event_end - event_start
                if duration > 0:
                    depth = self.rng.lognormal(mu, sigma)
                    depth = min(depth, max_event_mm)
                    # Distribute depth uniformly across duration with some noise
                    rates = np.ones(duration) * (depth / duration)
                    noise = self.rng.normal(0, 0.1 * rates.mean(), duration)
                    rates = np.clip(rates + noise, 0, None)
                    # Adjust to preserve total depth
                    if rates.sum() > 0:
                        rates = rates * (depth / rates.sum())
                    
                    if regimes[event_start] == WeatherRegime.HEAVY_RAIN:
                        rates *= 2.0 # double intensity for heavy rain
                        
                    rain_incident[event_start:event_end] = rates

        # Handle case where rain continues to the end of the array
        if in_rain:
            event_end = num_timesteps
            duration = event_end - event_start
            if duration > 0:
                depth = self.rng.lognormal(mu, sigma)
                depth = min(depth, max_event_mm)
                rates = np.ones(duration) * (depth / duration)
                rain_incident[event_start:event_end] = rates
                
        return rain_incident
