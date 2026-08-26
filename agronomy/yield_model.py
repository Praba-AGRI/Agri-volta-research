import numpy as np
import pandas as pd
from typing import Dict, Any

from agronomy.phenology import PhenologyStage

class YieldModel:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        crop_cfg = self.config.get('crop', {})
        growth = crop_cfg.get('growth', {})
        self.base_hi = growth.get('harvest_index', 0.35)

    def calculate_yield(self, df_daily: pd.DataFrame) -> Dict[str, float]:
        """
        Calculates final yield from daily crop data.
        Returns total biomass and pod yield.
        """
        if len(df_daily) == 0:
            return {'total_biomass_g': 0.0, 'yield_g': 0.0}
            
        final_biomass = df_daily['Biomass_g'].iloc[-1]
        
        # Calculate water stress factor during critical stages (flowering + pod filling)
        critical_stages = (df_daily['phenology_stage'] == PhenologyStage.FLOWERING) | \
                          (df_daily['phenology_stage'] == PhenologyStage.POD_FILLING)
                          
        if critical_stages.any():
            mean_ks_critical = df_daily.loc[critical_stages, 'Ks'].mean()
        else:
            mean_ks_critical = 1.0
            
        # Severe water stress during critical stages reduces Harvest Index
        # Simplified empirical reduction: HI = HI_base * (0.5 + 0.5 * Ks_critical)
        hi_actual = self.base_hi * (0.5 + 0.5 * mean_ks_critical)
        
        final_yield = final_biomass * hi_actual
        
        return {
            'total_biomass_g': final_biomass,
            'harvest_index': hi_actual,
            'yield_g': final_yield
        }
