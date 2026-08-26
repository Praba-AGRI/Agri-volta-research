import pytest
import numpy as np
import pandas as pd
from agronomy.soil_water import SoilWaterBalance

@pytest.fixture
def config():
    return {
        'experiment': {
            'temporal_resolution': {'timestep_minutes': 5}
        },
        'soil': {
            'depth_mm': 600.0,
            'properties': {
                'field_capacity_vvc': 0.22,
                'wilting_point_vvc': 0.08,
                'saturation_vvc': 0.45,
                'saturated_hydraulic_conductivity_mm_hr': 25.0
            }
        }
    }

def test_soil_water_balance(config):
    soil_model = SoilWaterBalance(config)
    
    num_steps = 10
    # Provide a simple pulse of rain
    p_surface = np.zeros(num_steps)
    p_surface[2] = 10.0 # 10 mm of rain at step 2
    
    # Provide some ET demand
    et_demand = np.full(num_steps, 0.5)
    kc = np.full(num_steps, 1.0)
    
    # We'll start at FC
    initial_theta = 0.22
    s_initial = initial_theta * 600.0 # 132 mm
    
    df = soil_model.simulate_zone(p_surface, et_demand, kc, initial_theta=initial_theta)
    
    assert len(df) == num_steps
    
    # Manual water balance check for step 0
    # Ks should be 1.0 since we start at FC
    assert df['Ks'].iloc[0] == 1.0
    # ETc should be 0.5
    assert df['ETc_mm'].iloc[0] == 0.5
    # S_mm should be 132 + 0 - 0.5 = 131.5
    assert df['S_mm'].iloc[0] == 131.5
    
    # Step 2: Rain of 10 mm
    # Water in: 10 mm. Ksat = 25 mm/hr = 2.083 mm/5min.
    # So infiltrated = 2.083 mm, Runoff = 7.917 mm.
    # Previous S_mm (step 1) = 131.0
    # S_new = 131.0 + 2.083 - 0.5 = 132.583
    # Wait, S_fc is 132.0. So 132.583 > 132.0, meaning drainage = 0.583 mm.
    # S_final = 132.0
    
    # Let's verify Ksat
    ksat_step = 25.0 * (5.0 / 60.0) # 2.0833
    
    # Just check mass balance over the whole simulation
    total_in = p_surface.sum()
    total_out = df['Runoff_mm'].sum() + df['Drainage_mm'].sum() + df['ETc_mm'].sum()
    s_final = df['S_mm'].iloc[-1]
    
    np.testing.assert_allclose(s_initial + total_in - total_out, s_final, atol=1e-5)
    
    # Check that runoff occurred at step 2
    assert df['Runoff_mm'].iloc[2] > 0
    np.testing.assert_allclose(df['Runoff_mm'].iloc[2], 10.0 - ksat_step, atol=1e-5)
