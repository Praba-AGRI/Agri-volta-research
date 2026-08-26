import pytest
import numpy as np
import pandas as pd
from agronomy.et0 import ET0Model
from agronomy.et_demand import ETDemandModel

@pytest.fixture
def config():
    return {
        'experiment': {
            'location': {
                'latitude_deg': 11.016,
                'longitude_deg': 76.971,
                'elevation_m': 400.0
            },
            'temporal_resolution': {'timestep_minutes': 5}
        }
    }

def test_et0(config):
    # Known numerical test case or reasonable values
    # Let's test with a typical summer day
    df_daily = pd.DataFrame({
        'T_max': [35.0],
        'T_min': [25.0],
        'T_mean': [30.0],
        'RH_max': [80.0],
        'RH_min': [40.0],
        'u2': [2.5],
        'Rs': [22.0] # MJ/m2/day
    })
    
    et0_model = ET0Model(config)
    result = et0_model.calculate_daily_et0(df_daily)
    
    assert len(result) == 1
    et0 = result['ET0'].iloc[0]
    
    # Expected ET0 for these conditions is roughly 5-7 mm/day
    assert 4.0 <= et0 <= 8.0, f"ET0 out of expected range: {et0}"

def test_et_demand(config):
    demand_model = ETDemandModel(config)
    num_days = 2
    timesteps_per_day = 288
    total_timesteps = num_days * timesteps_per_day
    
    # Create synthetic 5-minute data
    df_5min = pd.DataFrame({
        'T_A': np.full(total_timesteps, 30.0),
        'RH_A': np.full(total_timesteps, 60.0),
        'u_A': np.full(total_timesteps, 2.5),
        'Rs_A': np.zeros(total_timesteps)
    })
    
    # Simulate daytime radiation (12 hours)
    daylight_mask = (np.arange(timesteps_per_day) >= 72) & (np.arange(timesteps_per_day) < 216)
    df_5min.loc[np.tile(daylight_mask, num_days), 'Rs_A'] = 500.0 # W/m2
    
    demand_df = demand_model.calculate_zone_demand(df_5min, 'A')
    
    assert len(demand_df) == total_timesteps
    
    # Sum of 5-min demand should equal daily demand
    daily_sum = demand_df['ET_demand_5min_A'].iloc[:timesteps_per_day].sum()
    daily_demand = demand_df['ET_demand_daily_A'].iloc[0]
    
    np.testing.assert_allclose(daily_sum, daily_demand, atol=1e-5)
    
    # Nighttime 5-min demand should be 0 since Rs is 0
    night_mask = ~np.tile(daylight_mask, num_days)
    assert np.all(demand_df.loc[night_mask, 'ET_demand_5min_A'] == 0.0)
