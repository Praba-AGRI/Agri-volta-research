import pytest
import numpy as np
import pandas as pd
from core.random_state import SimulationRandomState
from simulation.weather_engine import WeatherEngine
from simulation.solar_engine import SolarEngine
from simulation.pv_shading import PVShading
from simulation.spectral_engine import SpectralEngine

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
        },
        'radiation': {
            'zone_b': {
                'direct_beam': {'panel_transmission': {'nominal': 0.60}},
                'diffuse': {'transmission': {'nominal': 0.85}}
            }
        },
        'as7341': {
            'pv_filtering': {
                'blue_attenuation': {'nominal': 0.25},
                'green_attenuation': {'nominal': 0.20},
                'red_attenuation': {'nominal': 0.30},
                'far_red_modification': {'nominal_factor': 0.75},
                'nir_modification': {'nominal_factor': 0.80}
            }
        }
    }

@pytest.fixture
def rng():
    rs = SimulationRandomState(42)
    rs.set_season(1)
    return rs.get_generator(module_offset=1)

def test_radiation(config, rng):
    num_timesteps = 288 * 5 # 5 days
    weather = WeatherEngine(config, rng).generate_weather(num_timesteps, mode="stochastic")
    solar = SolarEngine(config).calculate_solar_position(num_timesteps)
    shading = PVShading(config).calculate_shade_fraction(solar)
    
    spectral = SpectralEngine(config, rng)
    rad_df = spectral.calculate_radiation(weather, solar, shading)
    
    # Check Rs >= 0
    assert (rad_df['Rs_A'] >= 0).all(), "Rs_A contains negative values"
    assert (rad_df['Rs_B'] >= 0).all(), "Rs_B contains negative values"
    
    # Check physical permissible range (e.g. <= 1200 W/m2)
    assert (rad_df['Rs_A'] <= 1200).all(), "Rs_A exceeds physical limits"
    assert (rad_df['Rs_B'] <= 1200).all(), "Rs_B exceeds physical limits"
    
    # Check direct + diffuse consistency
    np.testing.assert_allclose(rad_df['Rs_dir_A'] + rad_df['Rs_dif_A'], rad_df['Rs_A'], atol=1e-5)
    np.testing.assert_allclose(rad_df['Rs_dir_B'] + rad_df['Rs_dif_B'], rad_df['Rs_B'], atol=1e-5)
    
    # Check Zone B is always <= Zone A
    assert (rad_df['Rs_B'] <= rad_df['Rs_A'] + 1e-5).all(), "Zone B radiation exceeded Zone A"
