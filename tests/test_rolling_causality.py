import pytest
import pandas as pd
import numpy as np
import os
from ml.dataset_builder import DatasetBuilder

def test_gdd_causality():
    """
    Asserts that GDD features only contain information up to the forecast origin t.
    """
    sensor_path = 'outputs/sensor_5min.parquet'
    if not os.path.exists(sensor_path):
        pytest.skip("Sensor data not found")
        
    builder = DatasetBuilder(sensor_path, target_zone='A')
    builder._causal_imputation()
    builder._derive_gdd()
    
    # Check that for any row, the daily_GDD is NOT computed using the current day's complete data.
    # We do this by ensuring the mapped timestamp (the day the GDD was calculated from) is strictly strictly < today.
    # However, since _derive_gdd maps from the "previous day", we can verify by checking if shifting it forward respects the boundary.
    # Actually, the user assertion is: feature_asof_timestamp <= forecast_origin
    # The GDD values are mapped from `t.floor('D') - pd.Timedelta(days=1)`.
    # As long as the timestamp of the row >= t.floor('D'), it is valid.
    
    timestamps = builder.df.index
    # The index is the forecast origin t.
    # The GDD for t comes from the previous day.
    
    # We will simulate a future substitution to verify it behaviorally.
    df_original = builder.df.copy()
    
    t_test = timestamps[1000] # Random t
    
    # Corrupt all T values after t_test
    builder.df.loc[timestamps > t_test, 'T'] = 999.0
    
    builder._derive_gdd()
    
    # The GDD at t_test should be identical to the original
    assert np.isclose(builder.df.loc[t_test, 'daily_GDD'], df_original.loc[t_test, 'daily_GDD'], equal_nan=True)
    assert np.isclose(builder.df.loc[t_test, 'cumulative_GDD'], df_original.loc[t_test, 'cumulative_GDD'], equal_nan=True)

def test_rolling_causality():
    """
    Asserts that all rolling features in X_rf remain unchanged when future data is corrupted.
    F_t^{original} = F_t^{modified}
    """
    sensor_path = 'outputs/sensor_5min.parquet'
    if not os.path.exists(sensor_path):
        pytest.skip("Sensor data not found")
        
    builder_orig = DatasetBuilder(sensor_path, target_zone='A')
    dataset_orig = builder_orig.build_dataset()
    X_rf_orig = dataset_orig['X_rf']
    t_input_orig = dataset_orig['t_input']
    
    # Pick a random sequence end time t
    idx_test = len(t_input_orig) // 2
    t_test = t_input_orig[idx_test]
    
    builder_mod = DatasetBuilder(sensor_path, target_zone='A')
    
    # Corrupt ALL columns in df AFTER t_test
    # Note: we do this before build_dataset
    timestamps = builder_mod.df.index
    future_mask = timestamps > t_test
    
    for col in builder_mod.df.columns:
        if pd.api.types.is_numeric_dtype(builder_mod.df[col]):
            builder_mod.df.loc[future_mask, col] = 9999.0
            
    dataset_mod = builder_mod.build_dataset()
    X_rf_mod = dataset_mod['X_rf']
    t_input_mod = dataset_mod['t_input']
    
    # Find the corresponding index in the modified dataset (in case drops changed)
    # The sequence ending at t_test must exist and have the exact same RF features.
    
    orig_features = X_rf_orig[t_input_orig == t_test][0]
    mod_features = X_rf_mod[t_input_mod == t_test][0]
    
    # Assert F_t^{original} == F_t^{modified}
    np.testing.assert_array_almost_equal(orig_features, mod_features)
