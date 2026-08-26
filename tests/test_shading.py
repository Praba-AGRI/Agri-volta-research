import pytest
import numpy as np
import pandas as pd
from simulation.solar_engine import SolarEngine
from simulation.pv_shading import PVShading

@pytest.fixture
def config():
    return {
        'experiment': {
            'location': {
                'latitude_deg': 11.016,
                'longitude_deg': 76.971,
                'timezone': 'Asia/Kolkata'
            },
            'temporal_resolution': {'timestep_minutes': 5}
        },
        'pv_geometry': {
            'baseline_virtual_geometry': {
                'panel': {'tilt_deg': 15.0, 'azimuth_deg': 180.0, 'length_m': 2.0},
                'mounting': {'lower_edge_height_m': 2.5},
                'array': {'row_pitch_m': 6.0}
            },
            'shading': {
                'full_shade_threshold': 0.80
            }
        }
    }

def test_pv_shading(config):
    solar_engine = SolarEngine(config)
    solar_df = solar_engine.calculate_solar_position(288) # 1 day
    
    shading = PVShading(config)
    shading_df = shading.calculate_shade_fraction(solar_df)
    
    assert len(shading_df) == 288
    
    # 0 <= shade_fraction <= 1
    assert (shading_df['shade_fraction'] >= 0.0).all()
    assert (shading_df['shade_fraction'] <= 1.0).all()
    
    # Nighttime shade handling
    night_mask = solar_df['solar_elevation_deg'] <= 0
    assert (shading_df.loc[night_mask, 'shade_fraction'] == 0.0).all()
    
    # Full shade flag logic
    expected_flags = (shading_df['shade_fraction'] >= 0.80).astype(int)
    assert (shading_df['full_shade_flag'] == expected_flags).all()
