import numpy as np
import pandas as pd
from typing import Dict, Any

from agronomy.phenology import PhenologyStage

class CropGrowthModel:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        crop_cfg = self.config.get('crop', {})
        growth = crop_cfg.get('growth', {})
        
        # RUE in g/MJ
        self.rue = growth.get('rue_g_mj', 1.8)
        self.k_ext = growth.get('k_extinction', 0.65)
        self.max_lai = growth.get('max_lai', 4.5)
        
        # We need GDD thresholds to model LAI development
        phen = crop_cfg.get('phenology', {}).get('gdd_thresholds', {})
        self.gdd_veg = phen.get('vegetative', 550.0)
        self.gdd_flow = phen.get('flowering', 800.0)
        self.gdd_mat = phen.get('maturity', 1350.0)

    def _calculate_lai(self, cumulative_gdd: float, stage: int) -> float:
        """Simple empirical LAI curve driven by GDD."""
        if stage == PhenologyStage.PRE_EMERGENCE:
            return 0.0
            
        if cumulative_gdd <= self.gdd_flow:
            # Logistic or linear increase to max_lai
            fraction = min(1.0, cumulative_gdd / self.gdd_flow)
            return self.max_lai * (fraction ** 1.5) # slightly sigmoid
        elif cumulative_gdd <= self.gdd_mat:
            # Decline during pod filling / maturity
            fraction = (cumulative_gdd - self.gdd_flow) / (self.gdd_mat - self.gdd_flow)
            return self.max_lai * (1.0 - 0.5 * fraction) # Drops to 50% max at maturity
        else:
            return 0.0

    def calculate_daily_growth(self, df_daily: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates daily crop growth.
        Expected columns in df_daily:
        - Rs (MJ/m2/day)
        - Ks (average daily water stress 0-1)
        - cumulative_gdd
        - phenology_stage
        """
        num_days = len(df_daily)
        biomass_daily_inc = np.zeros(num_days)
        biomass = np.zeros(num_days)
        lai_arr = np.zeros(num_days)
        apar_arr = np.zeros(num_days)
        
        current_biomass = 0.0
        
        for d in range(num_days):
            gdd = df_daily['cumulative_gdd'].iloc[d]
            stage = df_daily['phenology_stage'].iloc[d]
            rs = df_daily['Rs'].iloc[d]
            ks = df_daily['Ks'].iloc[d]
            
            # PAR is approximately 50% of Rs
            par = 0.5 * rs
            
            lai = self._calculate_lai(gdd, stage)
            lai_arr[d] = lai
            
            # APAR = PAR * (1 - exp(-k * LAI))
            fapar = 1.0 - np.exp(-self.k_ext * lai)
            apar = par * fapar
            apar_arr[d] = apar
            
            # dBiomass (g/m2) = RUE (g/MJ) * APAR (MJ/m2) * Ks
            d_biomass = self.rue * apar * ks
            biomass_daily_inc[d] = d_biomass
            
            current_biomass += d_biomass
            biomass[d] = current_biomass
            
        df = pd.DataFrame({
            'LAI': lai_arr,
            'APAR_MJ': apar_arr,
            'dBiomass_g': biomass_daily_inc,
            'Biomass_g': biomass
        }, index=df_daily.index)
        
        return df
