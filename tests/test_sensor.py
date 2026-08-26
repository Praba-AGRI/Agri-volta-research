import pytest
import numpy as np
import pandas as pd
from core.random_state import SimulationRandomState
from simulation.rtc import RTCModel
from simulation.sensor_emulator import SensorEmulator

@pytest.fixture
def config():
    return {
        'sensors': {
            'rtc': {
                'drift_seconds_per_day': {'nominal': 1.5},
                'jitter_ms': {'nominal': 0.0} # No jitter for predictable test
            },
            'soil_moisture': {
                'drift_per_season_percent': {'nominal': 10.0}, # 10% drift to make it obvious
                'noise_std_dev_percent': 0.0, # no noise for predictable test
                'missing_data_probability': 0.5 # high probability to test missing
            },
            'dht22': {
                'drift_per_season_percent': {'nominal': 0.0},
                'noise_std_dev_percent': 0.0,
                'missing_data_probability': 0.0
            }
        }
    }

@pytest.fixture
def rng():
    rs = SimulationRandomState(42)
    rs.set_season(1)
    return rs.get_generator(module_offset=1)

def test_rtc(config, rng):
    rtc_model = RTCModel(config, rng)
    
    # 2 days of data
    true_times = pd.date_range("2026-06-01 00:00:00", periods=576, freq="5min")
    df = rtc_model.generate_timestamps(true_times)
    
    assert len(df) == 576
    
    # Check drift at exactly 1 day (index 288)
    # elapsed time is 288 * 5 mins = 1440 mins = 1 day
    # expected drift = 1.5 seconds
    delta_at_day_1 = df['delta_t_rtc_sec'].iloc[288]
    np.testing.assert_allclose(delta_at_day_1, 1.5, atol=1e-3)

def test_sensor_emulator_drift_and_missing(config, rng):
    emulator = SensorEmulator(config, rng)
    
    num_timesteps = 100
    true_df = pd.DataFrame({
        'theta_v_A': np.full(num_timesteps, 0.20),
        'T_A': np.full(num_timesteps, 30.0)
    })
    
    obs_df = emulator.emulate_sensors(true_df)
    
    assert len(obs_df) == 100
    
    # T_A has no missing data, no noise, no drift in config
    assert not obs_df['T_A'].isna().any()
    np.testing.assert_allclose(obs_df['T_A'].values, 30.0)
    
    # theta_v_A has missing data and drift
    # Check that there are missing values (with 50% probability, highly likely some are NaN)
    assert obs_df['theta_v_A'].isna().any()
    
    # Check drift on non-missing values
    # Drift is linear over season up to 10%
    # The last value (if not missing) should be close to 0.20 + 0.20 * 0.10 = 0.22
    non_nan_indices = obs_df['theta_v_A'].dropna().index
    if len(non_nan_indices) > 0:
        last_idx = non_nan_indices[-1]
        expected_drift_factor = (last_idx / (num_timesteps - 1)) * (10.0 / 100.0)
        expected_val = 0.20 + 0.20 * expected_drift_factor
        np.testing.assert_allclose(obs_df['theta_v_A'].iloc[last_idx], expected_val, atol=1e-5)
