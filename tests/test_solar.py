import pytest
import numpy as np
import pandas as pd
from simulation.solar_engine import SolarEngine

@pytest.fixture
def config():
    return {
        'experiment': {
            'location': {
                'latitude_deg': 11.016,
                'longitude_deg': 76.971,
                'timezone': 'Asia/Kolkata',
                'elevation_m': 400.0
            },
            'temporal_resolution': {'timestep_minutes': 5}
        }
    }

def test_solar_geometry(config):
    engine = SolarEngine(config)
    # Generate 1 day (288 timesteps)
    df = engine.calculate_solar_position(288)
    
    assert len(df) == 288
    
    # Check that there are daytime and nighttime periods
    max_elevation = df['solar_elevation_deg'].max()
    min_elevation = df['solar_elevation_deg'].min()
    
    assert max_elevation > 0, "No daytime elevation found"
    assert min_elevation < 0, "No nighttime elevation found"
    
    # Check air mass at night is 0.0 as designed
    night_mask = df['solar_elevation_deg'] <= 0
    assert (df.loc[night_mask, 'air_mass'] == 0.0).all(), "Air mass at night should be 0.0"
    
    # Air mass during day should be >= 1.0
    day_mask = df['solar_elevation_deg'] > 0
    assert (df.loc[day_mask, 'air_mass'] >= 1.0).all(), "Air mass during day should be >= 1.0"
