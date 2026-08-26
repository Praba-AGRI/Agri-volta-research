import pytest
import numpy as np
import pandas as pd
from agronomy.phenology import PhenologyStage
from agronomy.crop_growth import CropGrowthModel
from agronomy.yield_model import YieldModel

@pytest.fixture
def config():
    return {
        'crop': {
            'phenology': {
                'gdd_thresholds': {
                    'emergence': 50.0,
                    'vegetative': 550.0,
                    'flowering': 800.0,
                    'pod_filling': 1100.0,
                    'maturity': 1350.0
                }
            },
            'growth': {
                'rue_g_mj': 1.8,
                'k_extinction': 0.65,
                'max_lai': 4.5,
                'harvest_index': 0.35
            }
        }
    }

def test_crop_growth_and_yield(config):
    growth_model = CropGrowthModel(config)
    yield_model = YieldModel(config)
    
    num_days = 100
    gdd = np.linspace(0, 1500, num_days)
    
    # Simple stages mapping based on GDD for testing
    stages = np.full(num_days, PhenologyStage.PRE_EMERGENCE)
    stages[gdd >= 50] = PhenologyStage.VEGETATIVE
    stages[gdd >= 800] = PhenologyStage.FLOWERING
    stages[gdd >= 1100] = PhenologyStage.POD_FILLING
    stages[gdd >= 1350] = PhenologyStage.MATURITY
    
    # Introduce some water stress at the end
    ks = np.linspace(1.0, 0.5, num_days)
    
    df_daily = pd.DataFrame({
        'cumulative_gdd': gdd,
        'phenology_stage': stages,
        'Rs': np.full(num_days, 20.0), # 20 MJ/m2/day
        'Ks': ks
    })
    
    growth_df = growth_model.calculate_daily_growth(df_daily)
    
    # Combine dfs for yield model
    df_daily = pd.concat([df_daily, growth_df], axis=1)
    
    result = yield_model.calculate_yield(df_daily)
    
    # Checks
    assert (growth_df['Biomass_g'] >= 0).all()
    assert (growth_df['LAI'] >= 0).all()
    assert (growth_df['dBiomass_g'] >= 0).all()
    
    assert result['total_biomass_g'] >= 0
    assert result['yield_g'] >= 0
    
    # Check that stress during flowering/pod filling reduced harvest index below 0.35
    assert result['harvest_index'] < 0.35
    
    # Check Ks is between 0 and 1
    assert (df_daily['Ks'] >= 0.0).all()
    assert (df_daily['Ks'] <= 1.0).all()
