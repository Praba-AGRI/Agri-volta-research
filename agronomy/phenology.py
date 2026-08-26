import numpy as np
from typing import Dict, Any

class PhenologyStage:
    PRE_EMERGENCE = 0
    VEGETATIVE = 1
    FLOWERING = 2
    POD_FILLING = 3
    MATURITY = 4

class PhenologyModel:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        crop_cfg = self.config.get('crop', {})
        thresholds = crop_cfg.get('phenology', {}).get('gdd_thresholds', {})
        
        self.gdd_emergence = thresholds.get('emergence', 50.0)
        self.gdd_vegetative = thresholds.get('vegetative', 550.0)
        self.gdd_flowering = thresholds.get('flowering', 800.0)
        self.gdd_pod_filling = thresholds.get('pod_filling', 1100.0)
        self.gdd_maturity = thresholds.get('maturity', 1350.0)

    def determine_stage(self, cumulative_gdd: np.ndarray) -> np.ndarray:
        """
        Determines the phenological stage based on cumulative GDD.
        """
        stages = np.full(cumulative_gdd.shape, PhenologyStage.PRE_EMERGENCE, dtype=int)
        
        stages[cumulative_gdd >= self.gdd_emergence] = PhenologyStage.VEGETATIVE
        stages[cumulative_gdd >= self.gdd_flowering] = PhenologyStage.FLOWERING
        stages[cumulative_gdd >= self.gdd_pod_filling] = PhenologyStage.POD_FILLING
        stages[cumulative_gdd >= self.gdd_maturity] = PhenologyStage.MATURITY
        
        return stages
