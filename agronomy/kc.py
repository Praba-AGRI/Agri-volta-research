import numpy as np
from typing import Dict, Any

class KcModel:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        crop_cfg = self.config.get('crop', {})
        coeffs = crop_cfg.get('crop_coefficients', {})
        
        self.kc_ini = coeffs.get('kc_ini', 0.40)
        self.kc_mid = coeffs.get('kc_mid', 1.15)
        self.kc_end = coeffs.get('kc_end', 0.35)
        
        thresholds = crop_cfg.get('phenology', {}).get('gdd_thresholds', {})
        self.gdd_ini_end = thresholds.get('vegetative', 550.0) # End of initial stage, start of development
        self.gdd_dev_end = thresholds.get('flowering', 800.0)  # End of development, start of mid-season
        self.gdd_mid_end = thresholds.get('pod_filling', 1100.0) # End of mid-season, start of late season
        self.gdd_late_end = thresholds.get('maturity', 1350.0) # End of late season

    def calculate_kc(self, cumulative_gdd: np.ndarray) -> np.ndarray:
        """
        Calculates the crop coefficient Kc based on cumulative GDD,
        using piecewise linear transitions.
        """
        kc = np.zeros_like(cumulative_gdd, dtype=float)
        
        # Initial phase: constant Kc_ini
        idx_ini = cumulative_gdd < self.gdd_ini_end
        kc[idx_ini] = self.kc_ini
        
        # Development phase: linear increase from Kc_ini to Kc_mid
        idx_dev = (cumulative_gdd >= self.gdd_ini_end) & (cumulative_gdd < self.gdd_dev_end)
        if np.any(idx_dev):
            fraction = (cumulative_gdd[idx_dev] - self.gdd_ini_end) / (self.gdd_dev_end - self.gdd_ini_end)
            kc[idx_dev] = self.kc_ini + fraction * (self.kc_mid - self.kc_ini)
            
        # Mid-season phase: constant Kc_mid
        idx_mid = (cumulative_gdd >= self.gdd_dev_end) & (cumulative_gdd < self.gdd_mid_end)
        kc[idx_mid] = self.kc_mid
        
        # Late-season phase: linear decrease from Kc_mid to Kc_end
        idx_late = (cumulative_gdd >= self.gdd_mid_end) & (cumulative_gdd < self.gdd_late_end)
        if np.any(idx_late):
            fraction = (cumulative_gdd[idx_late] - self.gdd_mid_end) / (self.gdd_late_end - self.gdd_mid_end)
            kc[idx_late] = self.kc_mid + fraction * (self.kc_end - self.kc_mid)
            
        # Post-maturity: constant Kc_end or harvest
        idx_post = cumulative_gdd >= self.gdd_late_end
        kc[idx_post] = self.kc_end
        
        return kc
