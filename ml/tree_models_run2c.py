import numpy as np
from sklearn.linear_model import ElasticNet
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from typing import Dict, Any

class QuantileHistGradientBoosting2C:
    def __init__(self, learning_rate=0.1, max_iter=100, min_samples_leaf=20, l2_regularization=0.0):
        self.model_10 = HistGradientBoostingRegressor(loss='quantile', quantile=0.10, learning_rate=learning_rate, max_iter=max_iter, min_samples_leaf=min_samples_leaf, l2_regularization=l2_regularization, random_state=42)
        self.model_50 = HistGradientBoostingRegressor(loss='quantile', quantile=0.50, learning_rate=learning_rate, max_iter=max_iter, min_samples_leaf=min_samples_leaf, l2_regularization=l2_regularization, random_state=42)
        self.model_90 = HistGradientBoostingRegressor(loss='quantile', quantile=0.90, learning_rate=learning_rate, max_iter=max_iter, min_samples_leaf=min_samples_leaf, l2_regularization=l2_regularization, random_state=42)

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.model_10.fit(X, y)
        self.model_50.fit(X, y)
        self.model_90.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        p10 = self.model_10.predict(X)
        p50 = self.model_50.predict(X)
        p90 = self.model_90.predict(X)
        # Ensure monotonic quantiles
        p10 = np.minimum(p10, p50)
        p90 = np.maximum(p90, p50)
        return np.column_stack([p10, p50, p90])

class QuantileRandomForest2C:
    def __init__(self, n_estimators=100, max_depth=None, min_samples_leaf=1):
        self.rf = RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, min_samples_leaf=min_samples_leaf, random_state=42, n_jobs=-1)

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.rf.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        # Extract predictions across individual trees
        tree_preds = np.array([tree.predict(X) for tree in self.rf.estimators_]) # (n_trees, N)
        p10 = np.percentile(tree_preds, 10, axis=0)
        p50 = np.percentile(tree_preds, 50, axis=0)
        p90 = np.percentile(tree_preds, 90, axis=0)
        return np.column_stack([p10, p50, p90])
