import numpy as np

class RollingOriginPurgedCV:
    def __init__(self, n_folds=5, forecast_horizon=288, input_window=288):
        self.n_folds = n_folds
        self.forecast_horizon = forecast_horizon
        self.input_window = input_window
        
    def split(self, t_input_end):
        """
        Yields (train_idx, val_idx) for 5 rolling origin folds.
        
        t_input_end is an array of timestamps corresponding to the end of the input window.
        
        Rules:
        Let v_start be the first index of validation.
        The last index of training t_train must satisfy:
        t_input_end[t_train] + forecast_horizon < t_input_end[v_start] - input_window
        Actually, in terms of array indices (assuming regular 5 min spacing):
        t_train_idx + forecast_horizon < v_start_idx - input_window
        This means v_start_idx - t_train_idx > forecast_horizon + input_window = 576.
        """
        N = len(t_input_end)
        
        # We need to divide the dataset into n_folds + 1 chunks (1 for initial train, n_folds for val)
        chunk_size = N // (self.n_folds + 1)
        
        # Purge size in indices
        purge_size = self.forecast_horizon + self.input_window
        
        for fold in range(self.n_folds):
            # Validation indices
            val_start = (fold + 1) * chunk_size
            # The last fold gets all the remaining data
            val_end = (fold + 2) * chunk_size if fold < self.n_folds - 1 else N
            
            # Train indices: from 0 up to val_start - purge_size
            train_end = val_start - purge_size
            
            if train_end <= 0:
                raise ValueError(f"Dataset too small to support fold {fold} with purge_size {purge_size}")
                
            train_idx = np.arange(0, train_end)
            val_idx = np.arange(val_start, val_end)
            
            yield train_idx, val_idx
