import numpy as np

class Scaler:
    """
    StandardScaler implementation that isolates per-fold.
    """
    def __init__(self):
        self.mean_seq = None
        self.std_seq = None
        self.mean_rf = None
        self.std_rf = None
        
    def fit(self, X_seq_train, X_rf_train):
        # Scale each feature channel independently for the BiLSTM
        # X_seq_train shape: (samples, timesteps, features)
        # We compute mean and std across (samples, timesteps)
        self.mean_seq = np.nanmean(X_seq_train, axis=(0, 1), keepdims=True)
        self.std_seq = np.nanstd(X_seq_train, axis=(0, 1), keepdims=True)
        # Prevent div by 0
        self.std_seq[self.std_seq == 0] = 1.0
        
        # RF scaling
        self.mean_rf = np.nanmean(X_rf_train, axis=0, keepdims=True)
        self.std_rf = np.nanstd(X_rf_train, axis=0, keepdims=True)
        self.std_rf[self.std_rf == 0] = 1.0
        
    def transform(self, X_seq, X_rf):
        X_seq_scaled = (X_seq - self.mean_seq) / self.std_seq
        X_rf_scaled = (X_rf - self.mean_rf) / self.std_rf
        
        # Impute any remaining NaNs to 0 (mean) if somehow they slipped through or caused by std=0
        X_seq_scaled = np.nan_to_num(X_seq_scaled, nan=0.0)
        X_rf_scaled = np.nan_to_num(X_rf_scaled, nan=0.0)
        
        return X_seq_scaled, X_rf_scaled
