import numpy as np
import pandas as pd
from typing import Dict, Any

class WeatherRegime:
    CLEAR = 0
    PARTLY_CLOUDY = 1
    OVERCAST = 2
    RAIN = 3
    HEAVY_RAIN = 4

    @staticmethod
    def to_string(regime: int) -> str:
        return ["CLEAR", "PARTLY_CLOUDY", "OVERCAST", "RAIN", "HEAVY_RAIN"][regime]


class WeatherEngine:
    def __init__(self, config: Dict[str, Any], rng: np.random.Generator):
        self.config = config
        self.rng = rng
        self.timesteps_per_day = 288
        
        # Simple transition matrix for 5-minute timestep
        # High persistence on the diagonal
        self.transition_matrix = np.array([
            # CLR   PCLD  OVC   RN    HRN
            [0.990, 0.009, 0.001, 0.000, 0.000],  # CLEAR
            [0.015, 0.970, 0.010, 0.005, 0.000],  # PARTLY_CLOUDY
            [0.005, 0.020, 0.960, 0.010, 0.005],  # OVERCAST
            [0.000, 0.010, 0.020, 0.950, 0.020],  # RAIN
            [0.000, 0.000, 0.050, 0.150, 0.800]   # HEAVY_RAIN
        ])

    def generate_smoke_regimes(self) -> np.ndarray:
        """Deterministic 24-hour sequence for smoke testing."""
        regimes = np.zeros(self.timesteps_per_day, dtype=int)
        
        # 00-06 h: clear night
        regimes[0:72] = WeatherRegime.CLEAR
        # 06-13 h: clear morning + strong radiation
        regimes[72:156] = WeatherRegime.CLEAR
        # 13-15 h: cloudy perturbation
        regimes[156:180] = WeatherRegime.OVERCAST
        # 15-17 h: rainfall event
        regimes[180:204] = WeatherRegime.RAIN
        # 17-19 h: clearing
        regimes[204:228] = WeatherRegime.PARTLY_CLOUDY
        # 19-24 h: night
        regimes[228:288] = WeatherRegime.CLEAR
        
        return regimes

    def generate_stochastic_regimes(self, num_timesteps: int) -> np.ndarray:
        regimes = np.zeros(num_timesteps, dtype=int)
        current = WeatherRegime.CLEAR
        for t in range(num_timesteps):
            regimes[t] = current
            current = self.rng.choice(5, p=self.transition_matrix[current])
        return regimes

    def generate_weather(self, num_timesteps: int, mode: str = "stochastic") -> pd.DataFrame:
        if mode == "smoke":
            # Just repeat the 1-day smoke sequence if num_timesteps > 288
            days = int(np.ceil(num_timesteps / self.timesteps_per_day))
            base_regimes = self.generate_smoke_regimes()
            regimes = np.tile(base_regimes, days)[:num_timesteps]
        else:
            regimes = self.generate_stochastic_regimes(num_timesteps)

        time_of_day = np.arange(num_timesteps) % self.timesteps_per_day
        hour_of_day = time_of_day * 5 / 60.0

        # Base sinusoidal temperatures (nominal 22 to 38 C)
        # Min at ~5 AM, Max at ~2 PM (14.0)
        t_base = 30.0 + 8.0 * np.sin(np.pi * (hour_of_day - 9.5) / 12.0)
        
        # Base RH (anti-correlated with T)
        rh_base = 65.0 - 20.0 * np.sin(np.pi * (hour_of_day - 9.5) / 12.0)

        # Base Pressure (nominal 1000 hPa)
        p_base = 1005.0 + 2.0 * np.sin(np.pi * (hour_of_day - 4.0) / 12.0)

        # Base Wind (nominal 2.5 m/s)
        w_base = 2.5 + 1.0 * np.sin(np.pi * (hour_of_day - 8.0) / 12.0)

        # Apply regime adjustments
        T = np.zeros(num_timesteps)
        RH = np.zeros(num_timesteps)
        P = np.zeros(num_timesteps)
        W = np.zeros(num_timesteps)
        
        # Noise arrays
        t_noise = self.rng.normal(0, 0.5, num_timesteps) if mode != "smoke" else np.zeros(num_timesteps)
        rh_noise = self.rng.normal(0, 2.0, num_timesteps) if mode != "smoke" else np.zeros(num_timesteps)
        p_noise = self.rng.normal(0, 0.5, num_timesteps) if mode != "smoke" else np.zeros(num_timesteps)
        w_noise = self.rng.normal(0, 0.5, num_timesteps) if mode != "smoke" else np.zeros(num_timesteps)

        for t in range(num_timesteps):
            r = regimes[t]
            is_day = 6.0 < hour_of_day[t] < 18.0
            
            if r == WeatherRegime.CLEAR:
                dt, drh, dp, dw = 0.0, -5.0, 0.0, 0.0
            elif r == WeatherRegime.PARTLY_CLOUDY:
                dt, drh, dp, dw = (-1.0 if is_day else 0.5), 5.0, -1.0, 0.5
            elif r == WeatherRegime.OVERCAST:
                dt, drh, dp, dw = (-3.0 if is_day else 1.0), 10.0, -2.0, 1.0
            elif r == WeatherRegime.RAIN:
                dt, drh, dp, dw = (-5.0 if is_day else 0.0), 25.0, -3.0, 2.0
            elif r == WeatherRegime.HEAVY_RAIN:
                dt, drh, dp, dw = (-8.0 if is_day else -1.0), 30.0, -5.0, 4.0
                
            T[t] = t_base[t] + dt + t_noise[t]
            RH[t] = rh_base[t] + drh + rh_noise[t]
            P[t] = p_base[t] + dp + p_noise[t]
            W[t] = max(0.0, w_base[t] + dw + w_noise[t])

        # Clip values to physical limits
        T = np.clip(T, 10.0, 45.0)
        RH = np.clip(RH, 20.0, 100.0)
        P = np.clip(P, 980.0, 1030.0)

        df = pd.DataFrame({
            "cloud_state": regimes,
            "T_A": T,
            "RH_A": RH,
            "P_A": P,
            "u_A": W
        })
        return df
