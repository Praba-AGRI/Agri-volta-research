import pytest
import numpy as np
import pandas as pd
import os

from ml.dataset_builder import DatasetBuilder
from ml.cv import RollingOriginPurgedCV

@pytest.fixture(scope="module")
def sample_dataset():
    # We create a dummy sensor_5min.parquet for fast testing
    dates = pd.date_range("2026-01-01", "2026-01-30", freq="5min")
    df = pd.DataFrame(index=dates)
    
    sensor_vars = ['T', 'RH', 'P', 'Tsoil', 'theta_v', 'lux_up', 'lux_down']
    solar_vars = ['Rs', 'solar_zenith_deg', 'solar_azimuth_deg', 'solar_elevation_deg', 'shade_fraction', 'full_shade_flag']
    derived_vars = ['VPD']
    
    for v in sensor_vars + solar_vars + derived_vars:
        df[f"{v}_B"] = np.random.randn(len(df))
        
    # Introduce some NaNs to test causal imputation
    df.loc[df.index[10:15], 'T_B'] = np.nan # short gap
    df.loc[df.index[100:150], 'RH_B'] = np.nan # long gap
    
    os.makedirs("tests/dummy_outputs", exist_ok=True)
    path = "tests/dummy_outputs/sensor_5min.parquet"
    df.to_parquet(path)
    
    yield path
    # Cleanup if needed

def test_temporal_provenance_audit(sample_dataset):
    builder = DatasetBuilder(sample_dataset)
    dataset = builder.build_dataset()
    
    X_seq = dataset['X_seq']
    t_input = dataset['t_input']
    t_target = dataset['t_target']
    
    assert len(X_seq) > 0, "Dataset builder returned empty array"
    
    # Take a random sample to test
    idx = 50
    forecast_origin = pd.Timestamp(t_input[idx])
    target_timestamp = pd.Timestamp(t_target[idx])
    
    # 1. assert len(input_window) == 288
    assert X_seq[idx].shape[0] == 288, "Input window is not 288 steps"
    
    # 2. assert target_timestamp == forecast_origin + 288*5min
    expected_target = forecast_origin + pd.Timedelta(minutes=5 * 288)
    assert target_timestamp == expected_target, "Target timestamp does not match horizon"
    
    # 3. assert min(target_timestamps) > max(input_timestamps)
    assert target_timestamp > forecast_origin, "Target timestamp is not strictly after input"
    
    # 4. Check long gaps exclusion (the RH_B gap was 50 steps, should not appear in outputs)
    # The dataset builder should have filtered it out.
    assert not np.isnan(X_seq).any(), "NaNs leaked into the final sequence!"

def test_cv_purged_leakage(sample_dataset):
    builder = DatasetBuilder(sample_dataset)
    dataset = builder.build_dataset()
    
    t_input = dataset['t_input']
    
    cv = RollingOriginPurgedCV(n_folds=3, forecast_horizon=288, input_window=288)
    
    for train_idx, val_idx in cv.split(t_input):
        # assert validation_timestamps \cap training_timestamps == empty
        assert len(np.intersect1d(train_idx, val_idx)) == 0, "Train and Validation indices overlap"
        
        # assert target and input boundaries
        # max train target timestamp vs min val input timestamp
        max_t_train_input = pd.Timestamp(t_input[train_idx[-1]])
        min_v_input = pd.Timestamp(t_input[val_idx[0]])
        
        # The end of the training window + forecast_horizon must be strictly before 
        # the start of the validation input window
        # Wait, the purge condition:
        # t_train_end_idx + 288 < v_start_idx - 288
        assert train_idx[-1] + 288 < val_idx[0] - 288, "Purge condition failed!"

def test_future_substitution_leakage(sample_dataset):
    """
    Deliberately replace every value after the forecast origin with nonsense 
    and verify that the constructed input sequence and prediction target for that sample remain unchanged.
    """
    # Build original
    builder1 = DatasetBuilder(sample_dataset)
    dataset1 = builder1.build_dataset()
    
    # Pick a specific timestamp to be our origin
    t_origin = dataset1['t_input'][100]
    
    # Get original sequence and target
    orig_seq = dataset1['X_seq'][100].copy()
    orig_target = dataset1['y'][100].copy()
    
    # Now, corrupt the parquet file AFTER t_origin
    df = pd.read_parquet(sample_dataset)
    corrupted_df = df.copy()
    corrupted_df.loc[corrupted_df.index > t_origin] = 999999.0
    
    corrupt_path = "tests/dummy_outputs/corrupted_5min.parquet"
    corrupted_df.to_parquet(corrupt_path)
    
    # Build from corrupted
    builder2 = DatasetBuilder(corrupt_path)
    dataset2 = builder2.build_dataset()
    
    # Find the matching sequence
    # Since we corrupted the future, NaNs or extreme values might filter out future sequences, 
    # but index 100 should still exist identically.
    # We find the matching origin timestamp
    matching_idx = np.where(dataset2['t_input'] == t_origin)[0]
    assert len(matching_idx) == 1, "Origin sequence was lost after corruption!"
    
    new_seq = dataset2['X_seq'][matching_idx[0]]
    new_target = dataset2['y'][matching_idx[0]]
    
    # assert the input sequence is identical
    np.testing.assert_array_almost_equal(orig_seq, new_seq, err_msg="Future values leaked into input sequence!")
    
    # assert the target is completely corrupted (proving the test works and we successfully replaced the future)
    assert new_target == 999999.0, "Future substitution failed to corrupt the target, test is invalid."
    
    print("Anti-leakage future substitution test PASSED.")
