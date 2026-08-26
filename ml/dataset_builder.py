import pandas as pd
import numpy as np

class DatasetBuilder:
    def __init__(self, sensor_path: str, target_zone: str = 'B'):
        self.sensor_path = sensor_path
        df_raw = pd.read_parquet(sensor_path)
        
        # Filter and rename columns to generic names for the target zone
        # E.g., T_B -> T
        col_map = {}
        for col in df_raw.columns:
            if col.endswith(f"_{target_zone}"):
                col_map[col] = col.replace(f"_{target_zone}", "")
            elif not col.endswith("_A") and not col.endswith("_B"):
                col_map[col] = col # Keep un-suffixed columns
                
        # Keep only the mapped columns
        self.df = df_raw[list(col_map.keys())].rename(columns=col_map)
        
        # Ensure it's sorted by time
        if 'timestamp' in self.df.columns:
            self.df.set_index('timestamp', inplace=True)
        elif 'time' in self.df.columns:
            self.df.set_index('time', inplace=True)
        
        # Ensure the index is actually a datetime object, otherwise resample fails
        if not isinstance(self.df.index, pd.DatetimeIndex):
            self.df.index = pd.to_datetime(self.df.index)
            
        self.df.sort_index(inplace=True)
        self.target_zone = target_zone
        
        self.timestep_min = 5
        self.window_steps = 288
        self.target_horizon = 288
        
        # Features definition
        self.sensor_vars = ['T', 'RH', 'P', 'Tsoil', 'theta_v', 'lux_up', 'lux_down']
        self.solar_vars = ['Rs', 'solar_zenith_deg', 'solar_azimuth_deg', 'solar_elevation_deg', 'shade_fraction', 'full_shade_flag']
        self.derived_vars = ['VPD'] # Rainfall is P
        self.crop_vars = ['daily_GDD', 'cumulative_GDD']
        self.base_features = self.sensor_vars + self.solar_vars + self.derived_vars
        
        # Add a static zone identifier feature
        self.df['zone_A_flag'] = 1.0 if target_zone == 'A' else 0.0
        self.base_features.append('zone_A_flag')
        
    def _causal_imputation(self):
        """
        Implements strict causal imputation:
        - Gap <= 30 min (6 steps): Forward fill.
        - Gap > 30 min: Keep as NaN (will invalidate the sequence).
        """
        # Create missingness indicators for sensors subject to packet loss
        for var in self.sensor_vars:
            if var not in self.df.columns:
                if var in self.base_features:
                    self.base_features.remove(var)
                continue
                
            missing_col = f"{var}_missing"
            self.df[missing_col] = self.df[var].isna().astype(float)
            self.base_features.append(missing_col)
            
            # Forward fill up to 6 steps (30 minutes)
            self.df[var] = self.df[var].ffill(limit=6)
            
    def _derive_gdd(self):
        """
        Derives GDD causally from the sensor T data.
        Since we need the completed daily GDD, we compute it per calendar day
        and then shift it by 1 day so that it's only available the *next* day.
        """
        T_base = 10.0
        T_max = 35.0
        
        daily_tmax = self.df['T'].resample('D').max()
        daily_tmin = self.df['T'].resample('D').min()
        
        daily_gdd = ((daily_tmax + daily_tmin) / 2.0) - T_base
        daily_gdd = daily_gdd.clip(lower=0.0)
        # Cap at T_max effectively? Simple GDD:
        
        # Shift by 1 so Day D's GDD is available on Day D+1
        daily_gdd_shifted = daily_gdd.shift(1).fillna(0.0)
        cumulative_gdd_shifted = daily_gdd_shifted.cumsum()
        
        # Map back to 5-minute intervals
        self.df['daily_GDD'] = self.df.index.floor('D').map(daily_gdd_shifted)
        self.df['cumulative_GDD'] = self.df.index.floor('D').map(cumulative_gdd_shifted)
        
        # Handle the very first day which might map to NaN if shift(1) produced NaN before fillna
        self.df['daily_GDD'] = self.df['daily_GDD'].fillna(0.0)
        self.df['cumulative_GDD'] = self.df['cumulative_GDD'].fillna(0.0)
        
    def _add_temporal_features(self):
        """Adds causal temporal features based purely on the current timestamp."""
        hour = self.df.index.hour + self.df.index.minute / 60.0
        day_of_year = self.df.index.dayofyear
        
        self.df['sin_hour'] = np.sin(2 * np.pi * hour / 24.0)
        self.df['cos_hour'] = np.cos(2 * np.pi * hour / 24.0)
        self.df['sin_day'] = np.sin(2 * np.pi * day_of_year / 365.25)
        self.df['cos_day'] = np.cos(2 * np.pi * day_of_year / 365.25)
        
        self.temporal_vars = ['sin_hour', 'cos_hour', 'sin_day', 'cos_day']
        
    def _extract_rf_features(self, sequence_df: pd.DataFrame) -> np.ndarray:
        """
        Extracts summary features and specific lags from a 288-step sequence for the RF.
        Sequence shape is (288, F).
        """
        rf_features = []
        
        # Current state (t is the last row of the sequence)
        current = sequence_df.iloc[-1]
        
        # Core current states
        core_vars = ['theta_v', 'T', 'RH', 'Tsoil', 'VPD', 'Rs', 'shade_fraction', 'P']
        rf_features.extend([current[v] for v in core_vars])
        
        # Lags of theta_v (index 287 is t, so t-1 is 286, t-12 is 275)
        # 1 step = 5 min
        # t-1 (5m), t-12 (1h), t-72 (6h), t-144 (12h), t-287 (24h approx, first step)
        lags = [1, 12, 72, 144, 287]
        theta_col = sequence_df.columns.get_loc('theta_v')
        seq_vals = sequence_df.values
        for lag in lags:
            rf_features.append(seq_vals[-(lag+1), theta_col])
            
        # Short-term summaries
        # 1h = 12 steps, 6h = 72 steps, 12h = 144 steps, 24h = 288 steps
        theta_arr = sequence_df['theta_v'].values
        rf_features.extend([
            np.mean(theta_arr[-12:]),   # 1h
            np.mean(theta_arr[-72:]),   # 6h
            np.mean(theta_arr[-144:]),  # 12h
            np.mean(theta_arr),         # 24h
            np.min(theta_arr[-72:]),    # min 6h
            np.max(theta_arr[-72:]),    # max 6h
            theta_arr[-1] - theta_arr[-72] # slope 6h
        ])
        
        # Environmental summaries
        T_arr = sequence_df['T'].values
        VPD_arr = sequence_df['VPD'].values
        Rs_arr = sequence_df['Rs'].values
        P_arr = sequence_df['P'].values
        shade_arr = sequence_df['shade_fraction'].values
        
        rf_features.extend([
            np.mean(T_arr[-72:]),       # T_mean_6h
            np.mean(VPD_arr[-72:]),     # VPD_mean_6h
            np.sum(Rs_arr[-72:]) * 300, # Rs_integral_6h (J/m2 roughly, 5 min = 300s)
            np.sum(Rs_arr) * 300,       # Rs_integral_24h
            np.sum(P_arr[-72:]),        # rain_6h
            np.sum(P_arr),              # rain_24h
            np.mean(shade_arr[-72:]),   # shade_mean_6h
            np.mean(shade_arr)          # shade_mean_24h
        ])
        
        # Crop state
        rf_features.extend([
            current['daily_GDD'],
            current['cumulative_GDD']
        ])
        
        return np.array(rf_features)

    def build_dataset(self):
        """
        Constructs the ML arrays.
        """
        self._causal_imputation()
        self._derive_gdd()
        self._add_temporal_features()
        
        feature_cols = self.base_features + self.crop_vars + self.temporal_vars
        target_col = "theta_v"
        
        # Ensure all columns exist
        missing = [c for c in feature_cols if c not in self.df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
            
        data_values = self.df[feature_cols].values
        target_values = self.df[target_col].values
        timestamps = self.df.index.values
        
        N = len(self.df)
        
        X_seq_list = []
        X_rf_list = []
        y_list = []
        t_input_end_list = []
        t_target_list = []
        
        df_feats = self.df[feature_cols]
        
        # To make extraction fast, we check NaNs first
        has_nan = np.isnan(data_values).any(axis=1) | np.isnan(target_values)
        
        for i in range(self.window_steps - 1, N - self.target_horizon):
            seq_start = i - self.window_steps + 1
            seq_end = i + 1
            target_idx = i + self.target_horizon
            
            if target_idx >= N:
                break
            
            # If there's any NaN in the input window or target, skip (due to >30m gap)
            if has_nan[seq_start:seq_end].any() or has_nan[target_idx]:
                continue
                
            seq_df = df_feats.iloc[seq_start:seq_end]
            
            X_seq_list.append(seq_df.values)
            X_rf_list.append(self._extract_rf_features(seq_df))
            y_list.append(target_values[target_idx])
            t_input_end_list.append(timestamps[i])
            t_target_list.append(timestamps[target_idx])
            
        return {
            'X_seq': np.array(X_seq_list, dtype=np.float32),
            'X_rf': np.array(X_rf_list, dtype=np.float32),
            'y': np.array(y_list, dtype=np.float32),
            't_input': np.array(t_input_end_list),
            't_target': np.array(t_target_list),
            'feature_names_seq': feature_cols
        }
