import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

class PersistenceModel:
    def __init__(self):
        self.name = "Persistence"
        
    def predict(self, X_seq):
        """
        X_seq is expected to be of shape (samples, window_steps, features)
        The prediction is simply the last observed value of the target feature.
        """
        # Assuming theta_v is at a specific index, or we expect the user to pass it directly
        # To make it robust, we'll assume the caller extracts the 'theta_v' column
        # Or, the caller passes the 1D array of current theta_v values
        pass
        
    def predict_from_current(self, current_theta_v):
        """
        current_theta_v: 1D array of shape (samples,) representing theta_v at time t
        """
        return current_theta_v
        
    def evaluate(self, y_true, y_pred):
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        return {
            'RMSE': rmse,
            'MAE': mae,
            'R2': r2
        }
