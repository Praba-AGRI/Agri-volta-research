import numpy as np
import pandas as pd
from typing import Dict, Any

class SensorEmulator:
    def __init__(self, config: Dict[str, Any], rng: np.random.Generator):
        self.config = config
        self.rng = rng
        
    def _apply_sensor_effects(self, true_series: pd.Series, sensor_cfg: Dict[str, Any]) -> pd.Series:
        """
        Applies noise, drift, and packet loss to a single true physical series.
        """
        num_timesteps = len(true_series)
        observed = true_series.copy().values
        
        if num_timesteps == 0:
            return true_series.copy()
            
        # Extract params (defaulting to zero if not found)
        noise_std = sensor_cfg.get('noise_std_dev_percent', 0.0)
        drift_nominal = sensor_cfg.get('drift_per_season_percent', {}).get('nominal', 0.0)
        missing_prob = sensor_cfg.get('missing_data_probability', 0.0)
        
        # 1. Noise
        # For percentage noise, standard deviation is % of the true value. 
        # For variables near 0, we can add a small absolute baseline noise, but we'll stick to percentage as specified.
        # Wait, if true_val = 0, noise = 0? Let's treat the config value as % of the nominal range or reading.
        # For simplicity, treat 'percent' as % of the reading.
        noise = self.rng.normal(0, noise_std / 100.0, num_timesteps) * observed
        
        # 2. Drift
        # Linear drift over the season
        # drift_factor goes from 0 to drift_nominal/100
        time_fraction = np.linspace(0, 1, num_timesteps)
        drift_factor = time_fraction * (drift_nominal / 100.0)
        
        # Apply noise and drift
        # Observed = True + Noise + Drift
        observed = observed + noise + observed * drift_factor
        
        # 3. Calibration (Identity mapping for now)
        # 4. Packet Loss (Missing data)
        if missing_prob > 0.0:
            missing_mask = self.rng.random(num_timesteps) < missing_prob
            observed[missing_mask] = np.nan
            
        return pd.Series(observed, index=true_series.index)

    def emulate_sensors(self, true_df: pd.DataFrame) -> pd.DataFrame:
        """
        Emulates all sensors defined in the configuration.
        """
        sensors_cfg = self.config.get('sensors', {})
        
        # Map dataframe columns to sensor configurations
        # We need a generic way to apply this. For now, hardcode the main variables to their sensor blocks
        # T, RH -> dht22
        # Tsoil -> ds18b20
        # theta_v -> soil_moisture
        # AS7341_* -> as7341
        
        obs_df = pd.DataFrame(index=true_df.index)
        
        for col in true_df.columns:
            if col in ['timestamp', 'season_id', 'zone']:
                obs_df[col] = true_df[col]
                continue
                
            cfg_block = {}
            if col.startswith('T_A') or col.startswith('T_B') or col.startswith('RH_A') or col.startswith('RH_B'):
                cfg_block = sensors_cfg.get('dht22', {})
            elif col.startswith('Tsoil'):
                cfg_block = sensors_cfg.get('ds18b20', {})
            elif col.startswith('theta_v'):
                cfg_block = sensors_cfg.get('soil_moisture', {})

            
            # If no specific config, just copy the true value or assume ideal
            obs_df[col] = self._apply_sensor_effects(true_df[col], cfg_block)
            
        return obs_df
