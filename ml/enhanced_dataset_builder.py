import pandas as pd
import numpy as np

class EnhancedDatasetBuilder:
    def __init__(self, sensor_path: str, target_zone: str = 'B', target_type: str = 'residual'):
        """
        target_type: 'residual' for theta_{t+288} - theta_t
                     'absolute' for theta_{t+288}
        """
        self.sensor_path = sensor_path
        self.target_type = target_type
        self.target_zone = target_zone
        
        df_raw = pd.read_parquet(sensor_path)
        
        # Filter and rename columns to generic names for the target zone
        col_map = {}
        for col in df_raw.columns:
            if col.endswith(f"_{target_zone}"):
                col_map[col] = col.replace(f"_{target_zone}", "")
            elif not col.endswith("_A") and not col.endswith("_B"):
                col_map[col] = col # Keep un-suffixed columns
                
        self.df = df_raw[list(col_map.keys())].rename(columns=col_map)
        
        if 'timestamp' in self.df.columns:
            self.df.set_index('timestamp', inplace=True)
        elif 'time' in self.df.columns:
            self.df.set_index('time', inplace=True)
        
        if not isinstance(self.df.index, pd.DatetimeIndex):
            self.df.index = pd.to_datetime(self.df.index)
            
        self.df.sort_index(inplace=True)
        
        self.timestep_min = 5
        self.window_steps = 288
        self.target_horizon = 288
        
        # Original Base Features
        self.sensor_vars = ['T', 'RH', 'P', 'Tsoil', 'theta_v', 'lux_up', 'lux_down']
        self.solar_vars = ['Rs', 'solar_zenith_deg', 'solar_azimuth_deg', 'solar_elevation_deg', 'shade_fraction', 'full_shade_flag']
        self.derived_vars = ['VPD']
        
        # Zone A Flag
        self.df['zone_A_flag'] = 1.0 if target_zone == 'A' else 0.0
        self.base_features = self.sensor_vars + self.solar_vars + self.derived_vars + ['zone_A_flag']
        
    def _causal_imputation(self):
        for var in self.sensor_vars:
            if var not in self.df.columns:
                if var in self.base_features:
                    self.base_features.remove(var)
                continue
            missing_col = f"{var}_missing"
            self.df[missing_col] = self.df[var].isna().astype(float)
            self.base_features.append(missing_col)
            self.df[var] = self.df[var].ffill(limit=6)
            
    def _derive_gdd(self):
        T_base = 10.0
        daily_tmax = self.df['T'].resample('D').max()
        daily_tmin = self.df['T'].resample('D').min()
        
        daily_gdd = ((daily_tmax + daily_tmin) / 2.0) - T_base
        daily_gdd = daily_gdd.clip(lower=0.0)
        
        daily_gdd_shifted = daily_gdd.shift(1).fillna(0.0)
        cumulative_gdd_shifted = daily_gdd_shifted.cumsum()
        
        self.df['daily_GDD'] = self.df.index.floor('D').map(daily_gdd_shifted)
        self.df['cumulative_GDD'] = self.df.index.floor('D').map(cumulative_gdd_shifted)
        self.df['daily_GDD'] = self.df['daily_GDD'].fillna(0.0)
        self.df['cumulative_GDD'] = self.df['cumulative_GDD'].fillna(0.0)
        
    def _add_temporal_features(self):
        hour = self.df.index.hour + self.df.index.minute / 60.0
        day_of_year = self.df.index.dayofyear
        
        self.df['sin_hour'] = np.sin(2 * np.pi * hour / 24.0)
        self.df['cos_hour'] = np.cos(2 * np.pi * hour / 24.0)
        self.df['sin_day'] = np.sin(2 * np.pi * day_of_year / 365.25)
        self.df['cos_day'] = np.cos(2 * np.pi * day_of_year / 365.25)
        
        self.temporal_vars = ['sin_hour', 'cos_hour', 'sin_day', 'cos_day']

    def _derive_causal_enhanced_features(self):
        """
        Derives all additional temporal and environmental dynamics features strictly causally.
        1 step = 5 min
        1h = 12 steps, 6h = 72 steps, 12h = 144 steps, 24h = 288 steps
        """
        # 1. Soil-Moisture Dynamics
        self.df['delta_theta_1h'] = self.df['theta_v'] - self.df['theta_v'].shift(12)
        self.df['delta_theta_6h'] = self.df['theta_v'] - self.df['theta_v'].shift(72)
        self.df['delta_theta_12h'] = self.df['theta_v'] - self.df['theta_v'].shift(144)
        self.df['delta_theta_24h'] = self.df['theta_v'] - self.df['theta_v'].shift(288)
        
        self.df['rolling_mean_theta_1h'] = self.df['theta_v'].rolling(12).mean()
        self.df['rolling_mean_theta_6h'] = self.df['theta_v'].rolling(72).mean()
        self.df['rolling_mean_theta_24h'] = self.df['theta_v'].rolling(288).mean()
        
        # 2. Rainfall
        self.df['P_1h'] = self.df['P'].rolling(12).sum()
        self.df['P_6h'] = self.df['P'].rolling(72).sum()
        self.df['P_12h'] = self.df['P'].rolling(144).sum()
        self.df['P_24h'] = self.df['P'].rolling(288).sum()
        
        # Time Since Last Rain (TSLR)
        is_rain = self.df['P'] > 0
        rain_groups = is_rain.cumsum()
        tslr_steps = (~is_rain).groupby(rain_groups).cumcount()
        # For the beginning of the series before any rain, set TSLR to 14400 minutes (10 days)
        tslr_steps.loc[rain_groups == 0] += 2880
        # Convert steps to minutes
        self.df['TSLR'] = tslr_steps * 5.0
        # Current rain step has TSLR = 0
        self.df.loc[is_rain, 'TSLR'] = 0.0
        
        # 3. Atmospheric Demand (VPD)
        self.df['VPD_1h'] = self.df['VPD'].rolling(12).mean()
        self.df['VPD_6h'] = self.df['VPD'].rolling(72).mean()
        self.df['VPD_24h'] = self.df['VPD'].rolling(288).mean()
        
        # 4. Radiation (Rs)
        self.df['Rs_1h'] = self.df['Rs'].rolling(12).mean()
        self.df['Rs_6h'] = self.df['Rs'].rolling(72).mean()
        self.df['Rs_24h'] = self.df['Rs'].rolling(288).mean()
        
        # 5. Shade
        self.df['mean_shade_1h'] = self.df['shade_fraction'].rolling(12).mean()
        self.df['mean_shade_6h'] = self.df['shade_fraction'].rolling(72).mean()
        self.df['mean_shade_24h'] = self.df['shade_fraction'].rolling(288).mean()
        self.df['fraction_shaded_24h'] = (self.df['shade_fraction'] > 0.05).rolling(288).mean()
        
        # 6. Thermal state
        self.df['delta_Tsoil_1h'] = self.df['Tsoil'] - self.df['Tsoil'].shift(12)
        self.df['delta_T_1h'] = self.df['T'] - self.df['T'].shift(12)
        
        self.enhanced_vars = [
            'delta_theta_1h', 'delta_theta_6h', 'delta_theta_12h', 'delta_theta_24h',
            'rolling_mean_theta_1h', 'rolling_mean_theta_6h', 'rolling_mean_theta_24h',
            'P_1h', 'P_6h', 'P_12h', 'P_24h', 'TSLR',
            'VPD_1h', 'VPD_6h', 'VPD_24h',
            'Rs_1h', 'Rs_6h', 'Rs_24h',
            'mean_shade_1h', 'mean_shade_6h', 'mean_shade_24h', 'fraction_shaded_24h',
            'delta_Tsoil_1h', 'delta_T_1h'
        ]
        
    def _extract_rf_features(self, sequence_df: pd.DataFrame) -> np.ndarray:
        current = sequence_df.iloc[-1]
        rf_features = []
        core_vars = ['theta_v', 'T', 'RH', 'Tsoil', 'VPD', 'Rs', 'shade_fraction', 'P']
        rf_features.extend([current[v] for v in core_vars])
        
        lags = [1, 12, 72, 144, 287]
        theta_col = sequence_df.columns.get_loc('theta_v')
        seq_vals = sequence_df.values
        for lag in lags:
            rf_features.append(seq_vals[-(lag+1), theta_col])
            
        theta_arr = sequence_df['theta_v'].values
        rf_features.extend([
            np.mean(theta_arr[-12:]),
            np.mean(theta_arr[-72:]),
            np.mean(theta_arr[-144:]),
            np.mean(theta_arr),
            np.min(theta_arr[-72:]),
            np.max(theta_arr[-72:]),
            theta_arr[-1] - theta_arr[-72]
        ])
        
        T_arr = sequence_df['T'].values
        VPD_arr = sequence_df['VPD'].values
        Rs_arr = sequence_df['Rs'].values
        P_arr = sequence_df['P'].values
        shade_arr = sequence_df['shade_fraction'].values
        
        rf_features.extend([
            np.mean(T_arr[-72:]),
            np.mean(VPD_arr[-72:]),
            np.sum(Rs_arr[-72:]) * 300,
            np.sum(Rs_arr) * 300,
            np.sum(P_arr[-72:]),
            np.sum(P_arr),
            np.mean(shade_arr[-72:]),
            np.mean(shade_arr)
        ])
        
        rf_features.extend([
            current['daily_GDD'],
            current['cumulative_GDD']
        ])
        
        return np.array(rf_features)
        
    def build_dataset(self):
        self._causal_imputation()
        self._derive_gdd()
        self._add_temporal_features()
        self._derive_causal_enhanced_features()
        
        feature_cols = (
            self.base_features + 
            ['daily_GDD', 'cumulative_GDD'] + 
            self.temporal_vars + 
            self.enhanced_vars
        )
        
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
        has_nan = np.isnan(data_values).any(axis=1) | np.isnan(target_values)
        
        for i in range(self.window_steps - 1, N - self.target_horizon):
            seq_start = i - self.window_steps + 1
            seq_end = i + 1
            target_idx = i + self.target_horizon
            
            if target_idx >= N:
                break
                
            # Check NaNs
            if has_nan[seq_start:seq_end].any() or has_nan[target_idx]:
                continue
                
            seq_df = df_feats.iloc[seq_start:seq_end]
            
            X_seq_list.append(seq_df.values)
            X_rf_list.append(self._extract_rf_features(seq_df))
            
            # Target Calculation based on type
            theta_t = target_values[i]
            theta_target = target_values[target_idx]
            if self.target_type == 'residual':
                y_list.append(theta_target - theta_t)
            else:
                y_list.append(theta_target)
                
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
        
    @staticmethod
    def get_feature_groups(features):
        """Categorize features into groups for analysis or modular architecture."""
        groups = {
            'state': [],
            'forcing': [],
            'agronomic': [],
            'agrivoltaic': [],
            'temporal': [],
            'other': []
        }
        
        state_vars = ['theta_v', 'Tsoil', 'T', 'RH', 'delta_theta', 'rolling_mean_theta', 'delta_Tsoil', 'delta_T']
        forcing_vars = ['P', 'VPD', 'Rs', 'TSLR']
        agronomic_vars = ['GDD']
        agrivoltaic_vars = ['shade', 'full_shade', 'lux_up', 'lux_down']
        temporal_vars = ['sin_hour', 'cos_hour', 'sin_day', 'cos_day']
        
        for f in features:
            matched = False
            for group, keywords in [
                ('state', state_vars),
                ('forcing', forcing_vars),
                ('agronomic', agronomic_vars),
                ('agrivoltaic', agrivoltaic_vars),
                ('temporal', temporal_vars)
            ]:
                if any(k in f for k in keywords):
                    groups[group].append(f)
                    matched = True
                    break
            if not matched:
                groups['other'].append(f)
                
        return groups
