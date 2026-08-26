import numpy as np
import pandas as pd
from typing import Dict, Any

class GDDModel:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        crop_cfg = self.config.get('crop', {})
        self.base_t = crop_cfg.get('phenology', {}).get('base_temperature_c', 10.0)
        self.max_t = crop_cfg.get('phenology', {}).get('max_temperature_c', 35.0)

    def calculate_daily_gdd(self, t_mean_daily: np.ndarray) -> np.ndarray:
        """
        Calculates daily GDD based on daily mean temperature.
        GDD = max[min(T_mean, 35) - 10, 0]
        """
        # Apply upper threshold
        t_effective = np.minimum(t_mean_daily, self.max_t)
        # Apply lower threshold and calculate GDD
        gdd = np.maximum(t_effective - self.base_t, 0.0)
        return gdd

    def calculate_cumulative_gdd(self, t_mean_daily: np.ndarray) -> np.ndarray:
        """
        Calculates cumulative GDD over the season.
        """
        daily_gdd = self.calculate_daily_gdd(t_mean_daily)
        return np.cumsum(daily_gdd)
