from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import numpy as np

class RFModel:
    def __init__(self, n_estimators=100, max_depth=None, random_state=42):
        self.model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            n_jobs=1
        )
        self.name = "RandomForest"
        
    def fit(self, X_train, y_train):
        self.model.fit(X_train, y_train)
        
    def predict(self, X):
        return self.model.predict(X)
        
    def evaluate(self, y_true, y_pred, rmse_persistence):
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        skill = 1.0 - (rmse / rmse_persistence) if rmse_persistence > 0 else 0.0
        
        return {
            'RMSE': rmse,
            'MAE': mae,
            'R2': r2,
            'Skill': skill
        }
