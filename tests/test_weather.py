import pytest
import numpy as np
import pandas as pd
from core.random_state import SimulationRandomState
from simulation.weather_engine import WeatherEngine, WeatherRegime
from simulation.rainfall_model import RainfallModel
from simulation.rainfall_partition import RainfallPartition

@pytest.fixture
def config():
    return {
        'experiment': {
            'temporal_resolution': {'timestep_minutes': 5}
        },
        'weather': {
            'rainfall': {
                'event_depth_distribution': {
                    'mean_mm': 8.0,
                    'sd_mm': 9.0,
                    'max_event_mm': 45.0
                }
            }
        },
        'rainfall_partition': {
            'zone_a': {'interception_fraction': 0.0},
            'zone_b': {
                'panel_interception': {'enabled': True, 'nominal_fraction': 0.10},
                'edge_concentration': {'enabled': True, 'use_for_central_zone': False}
            }
        }
    }

@pytest.fixture
def rng():
    rs = SimulationRandomState(42)
    rs.set_season(1)
    return rs.get_generator(module_offset=1)

def test_weather_bounds(config, rng):
    engine = WeatherEngine(config, rng)
    num_timesteps = 288 * 30 # 30 days
    df = engine.generate_weather(num_timesteps, mode="stochastic")
    
    assert (df['T_A'] >= 10.0).all() and (df['T_A'] <= 45.0).all(), "Temperature out of bounds"
    assert (df['RH_A'] >= 20.0).all() and (df['RH_A'] <= 100.0).all(), "RH out of bounds"
    assert (df['P_A'] >= 980.0).all() and (df['P_A'] <= 1030.0).all(), "Pressure out of bounds"
    assert (df['u_A'] >= 0.0).all(), "Wind speed must be >= 0"

def test_regime_persistence(config, rng):
    engine = WeatherEngine(config, rng)
    df = engine.generate_weather(2880, mode="stochastic")
    regimes = df['cloud_state'].values
    
    # Calculate transitions
    transitions = np.diff(regimes)
    no_change = np.sum(transitions == 0)
    
    # Due to high diagonal values, we expect mostly persistence
    assert no_change / len(transitions) > 0.90, "Regime persistence is too low"

def test_smoke_deterministic(config, rng):
    engine = WeatherEngine(config, rng)
    df = engine.generate_weather(288, mode="smoke")
    
    assert len(df) == 288
    # 00-06 h: clear night
    assert (df['cloud_state'].iloc[0:72] == WeatherRegime.CLEAR).all()
    # 15-17 h: rain
    assert (df['cloud_state'].iloc[180:204] == WeatherRegime.RAIN).all()

def test_rainfall_model(config, rng):
    engine = WeatherEngine(config, rng)
    df = engine.generate_weather(2880, mode="stochastic")
    
    rain_model = RainfallModel(config, rng)
    rain_incident = rain_model.generate_incident_rainfall(df, mode="stochastic")
    
    assert len(rain_incident) == 2880
    assert (rain_incident >= 0.0).all(), "Negative rainfall generated"
    
    # Rain should only happen in RAIN or HEAVY_RAIN regimes
    is_rain_regime = (df['cloud_state'] == WeatherRegime.RAIN) | (df['cloud_state'] == WeatherRegime.HEAVY_RAIN)
    assert np.all(rain_incident[~is_rain_regime] == 0.0), "Rain generated outside of rain regimes"

def test_rainfall_partition(config):
    p_incident = np.array([0.0, 5.0, 10.0])
    partition = RainfallPartition(config)
    p_a, p_b = partition.partition(p_incident)
    
    assert np.allclose(p_a, p_incident), "Zone A should receive 100% incident rain"
    assert np.allclose(p_b, p_incident * 0.90), "Zone B should receive 90% incident rain (10% intercepted)"
