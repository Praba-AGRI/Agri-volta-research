import pytest
import numpy as np
import pandas as pd
from core.random_state import SimulationRandomState
from simulation.weather_engine import WeatherEngine
from simulation.solar_engine import SolarEngine
from simulation.pv_shading import PVShading
from simulation.spectral_engine import SpectralEngine
from simulation.microclimate import Microclimate

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
            'shading': {'full_shade_threshold': 0.80}
        },
        'radiation': {
            'zone_b': {
                'direct_beam': {'panel_transmission': {'nominal': 0.60}},
                'diffuse': {'transmission': {'nominal': 0.85}}
            }
        },
        'microclimate': {
            'zone_b': {
                'air_temperature': {
                    'daytime_cooling_c': {'maximum': 3.5},
                    'nighttime_buffer_c': {'nominal': 0.5}
                },
                'relative_humidity': {
                    'increase_percent': {'maximum': 12.0}
                },
                'soil_temperature': {
                    'thermal_response': {'time_constant_hours': 6.0}
                },
                'wind': {'mode': 'paper_conservative'}
            }
        }
    }

@pytest.fixture
def rng():
    rs = SimulationRandomState(42)
    rs.set_season(1)
    return rs.get_generator(module_offset=1)

def test_microclimate(config, rng):
    num_timesteps = 288 * 2 # 2 days
    weather = WeatherEngine(config, rng).generate_weather(num_timesteps, mode="smoke")
    solar = SolarEngine(config).calculate_solar_position(num_timesteps)
    shading = PVShading(config).calculate_shade_fraction(solar)
    spectral = SpectralEngine(config, rng)
    rad_df = spectral.calculate_radiation(weather, solar, shading)
    
    mc = Microclimate(config)
    mc_df = mc.calculate_microclimate(weather, rad_df, shading)
    
    assert len(mc_df) == num_timesteps
    
    # Check TB behavior
    day_mask = rad_df['Rs_A'] > 0
    night_mask = ~day_mask
    
    # Daytime cooling: TB <= TA
    assert (mc_df.loc[day_mask, 'T_B'] <= weather.loc[day_mask, 'T_A'] + 1e-5).all()
    
    # Nighttime buffering: TB >= TA (when shaded)
    shaded_night_mask = night_mask & (shading['shade_fraction'] > 0)
    if shaded_night_mask.any():
        assert (mc_df.loc[shaded_night_mask, 'T_B'] >= weather.loc[shaded_night_mask, 'T_A'] - 1e-5).all()
        
    # Check RH bounds
    assert (mc_df['RH_B'] >= 0.0).all()
    assert (mc_df['RH_B'] <= 100.0).all()
    
    # Check soil temperature lag
    # Soil temperature amplitude should be smaller than air temperature amplitude
    t_a_amp = weather['T_A'].max() - weather['T_A'].min()
    tsoil_a_amp = mc_df['Tsoil_A'].max() - mc_df['Tsoil_A'].min()
    
    # Soil temp should have smaller amplitude than T_star (which is T_a + radiation)
    t_star_a = weather['T_A'] + 0.015 * rad_df['Rs_A']
    t_star_amp = t_star_a.max() - t_star_a.min()
    
    assert tsoil_a_amp < t_star_amp, "Soil temperature did not buffer the surface forcing"
