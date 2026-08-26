"""
Deterministic seed generation for the Agrivoltaic Simulation.
"""
import numpy as np
import random
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

class SimulationRandomState:
    def __init__(self, master_seed: int):
        self.master_seed = master_seed
        self.current_season_id = None
        self._set_global_seed(master_seed)

    def _set_global_seed(self, seed: int):
        """Sets the global seeds for Python, NumPy, and TensorFlow."""
        random.seed(seed)
        np.random.seed(seed)
        if TF_AVAILABLE:
            tf.random.set_seed(seed)

    def set_season(self, season_id: int):
        """
        Derives a deterministic seed for the given season and sets it globally.
        season_seed = master_seed + season_id
        """
        self.current_season_id = season_id
        season_seed = self.master_seed + season_id
        self._set_global_seed(season_seed)
        return season_seed

    def get_generator(self, module_offset: int = 0) -> np.random.Generator:
        """
        Returns an independent numpy Generator for a specific module within a season.
        This ensures modules don't perturb each other's random streams if called in different orders.
        """
        if self.current_season_id is None:
            raise ValueError("Season ID must be set before generating module-specific streams.")
        
        # We hash the season seed and the module offset to create a unique independent seed.
        # This keeps the streams deterministic and independent.
        module_seed = hash((self.master_seed, self.current_season_id, module_offset)) % (2**32)
        return np.random.default_rng(module_seed)

