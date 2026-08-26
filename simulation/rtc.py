import numpy as np
import pandas as pd
from typing import Dict, Any

class RTCModel:
    def __init__(self, config: Dict[str, Any], rng: np.random.Generator):
        self.config = config
        self.rng = rng
        
        rtc_cfg = self.config.get('sensors', {}).get('rtc', {})
        self.drift_sec_per_day = rtc_cfg.get('drift_seconds_per_day', {}).get('nominal', 1.5)
        self.jitter_ms = rtc_cfg.get('jitter_ms', {}).get('nominal', 50.0)

    def generate_timestamps(self, true_timestamps: pd.DatetimeIndex) -> pd.DataFrame:
        """
        Generates observed RTC timestamps incorporating drift and jitter.
        Returns a DataFrame with true and rtc timestamps, and delta.
        """
        num_timesteps = len(true_timestamps)
        
        # Calculate days elapsed since start
        if num_timesteps == 0:
            return pd.DataFrame()
            
        start_time = true_timestamps[0]
        elapsed_days = pd.Series(true_timestamps - start_time).dt.total_seconds().values / 86400.0
        
        # Drift component (seconds)
        drift = elapsed_days * self.drift_sec_per_day
        
        # Jitter component (seconds)
        jitter = self.rng.normal(0, self.jitter_ms / 1000.0, num_timesteps)
        
        total_offset_sec = drift + jitter
        
        # Create timedelta array
        offsets = pd.to_timedelta(total_offset_sec, unit='s')
        
        rtc_timestamps = true_timestamps + offsets
        
        df = pd.DataFrame({
            'true_timestamp': true_timestamps,
            'rtc_timestamp': rtc_timestamps,
            'delta_t_rtc_sec': total_offset_sec
        })
        
        return df
