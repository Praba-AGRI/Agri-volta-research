import numpy as np
import pandas as pd
from typing import Dict, Any

class IrrigationPolicy:
    def __init__(self, config: Dict[str, Any], policy_name: str):
        self.config = config
        self.policy_name = policy_name
        self.irrigation_cfg = self.config.get('irrigation', {})
        
        # Physical constraints
        soil_props = self.config.get('soil', {}).get('hydraulic_properties', {})
        self.theta_fc = soil_props.get('theta_field_capacity', {}).get('nominal', 0.27)
        self.z_r = self.config.get('soil', {}).get('depth_mm', 600.0)
        
        self.decision_hour = self.irrigation_cfg.get('irrigation_application', {}).get('decision_hour', 6)
        
    def calculate_volume(self, etc: float, p_eff: float, current_theta: float) -> float:
        """
        IR_t = max(0, ETc - Peff)
        Capped at field capacity storage: (theta_fc - theta_current) * Zr
        """
        # We need the daily ETc. Or the forecast ETc? 
        # Wait, the user specified: max(0, ET_c - P_effective)
        # But wait, which ET_c? ET_c of the past day or the next day?
        # Usually irrigation replaces the PREVIOUS day's ETc - Peff, or meets the current demand.
        # Let's say we pass the relevant ETc and Peff.
        ir_demand = max(0.0, etc - p_eff)
        cap = max(0.0, (self.theta_fc - current_theta) * self.z_r)
        return min(ir_demand, cap)
        
    def evaluate(self, t_idx: int, timestamp: pd.Timestamp, 
                 state: Dict[str, Any], env_history: Dict[str, Any]) -> float:
        raise NotImplementedError

class FixedCalendarPolicy(IrrigationPolicy):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "Fixed Calendar")
        cfg = self.irrigation_cfg.get('policies', {}).get('baseline_1_fixed', {}).get('primary_schedule', {})
        self.interval_days = cfg.get('interval_days', 3)
        self.volume_mm = cfg.get('depth_mm', 15.0)
        self.days_since_last = 0
        
    def evaluate(self, t_idx: int, timestamp: pd.Timestamp, 
                 state: Dict[str, Any], env_history: Dict[str, Any]) -> float:
        
        if timestamp.hour == self.decision_hour and timestamp.minute == 0:
            self.days_since_last += 1
            if self.days_since_last >= self.interval_days:
                self.days_since_last = 0
                return self.volume_mm, {'decision_type': 'IRRIGATE'}
            return 0.0, {'decision_type': 'HOLD'}
        return 0.0, {}

class ThresholdIoTPolicy(IrrigationPolicy):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "Threshold IoT")
        self.theta_critical = self.irrigation_cfg.get('thresholds', {}).get('critical_theta', {}).get('value', 0.2025)
        
    def evaluate(self, t_idx: int, timestamp: pd.Timestamp, 
                 state: Dict[str, Any], env_history: Dict[str, Any]) -> float:
                 
        if timestamp.hour == self.decision_hour and timestamp.minute == 0:
            current_theta = state['theta_sensor']
            if current_theta < self.theta_critical:
                # Calculate required volume
                # For IoT, we might replace the previous 24h ETc - Peff
                # Or just fill to FC. Wait, user specified: "same refill equation as proposed"
                etc_24h = np.sum(env_history['ETc_24h'])  # We will pass the past 24h ETc array
                p_eff_24h = np.sum(env_history['P_eff_24h'])
                vol = self.calculate_volume(etc_24h, p_eff_24h, current_theta)
                return vol, {'decision_type': 'IRRIGATE'}
            return 0.0, {'decision_type': 'HOLD'}
        return 0.0, {}

class ProposedAIPolicy(IrrigationPolicy):
    def __init__(self, config: Dict[str, Any], model, scaler):
        super().__init__(config, "Proposed AI")
        ai_cfg = self.irrigation_cfg.get('policies', {}).get('proposed_ai', {})
        self.theta_critical = self.irrigation_cfg.get('thresholds', {}).get('critical_theta', {}).get('value', 0.2025)
        self.theta_buffer = self.irrigation_cfg.get('thresholds', {}).get('buffer_theta', {}).get('value', 0.2200)
        self.window_days = ai_cfg.get('et0_reference', {}).get('window_days', 7)
        self.model = model # Frozen BiLSTM Model instance
        self.scaler = scaler # Frozen Scaler instance
        self.delay_active = False
        self.days_elapsed = 0
        
    def evaluate(self, t_idx: int, timestamp: pd.Timestamp, 
                 state: Dict[str, Any], env_history: Dict[str, Any]) -> float:
        
        # Track days elapsed for the warmup period
        if timestamp.hour == self.decision_hour and timestamp.minute == 0:
            self.days_elapsed += 1

        if timestamp.hour == self.decision_hour and timestamp.minute == 0:
            # Warm-up check: AI not active until 7 completed days
            if self.days_elapsed < self.window_days:
                # Fallback to HOLD or IoT during warmup? Let's fallback to IoT logic
                current_theta = state['theta_sensor']
                if current_theta < self.theta_critical:
                    etc_24h = np.sum(env_history['ETc_24h'])
                    p_eff_24h = np.sum(env_history['P_eff_24h'])
                    vol = self.calculate_volume(etc_24h, p_eff_24h, current_theta)
                    return vol, {'decision_type': 'WARMUP_IOT', 'forecast_theta': np.nan}
                return 0.0, {'decision_type': 'WARMUP_HOLD', 'forecast_theta': np.nan}

            # Get the forecast
            # X_seq shape expected by model: (1, 288, num_features)
            X_seq = env_history['X_seq'] 
            current_theta = state['theta_sensor']
            # Apply scaling
            X_seq_scaled, _ = self.scaler.transform(X_seq, np.zeros((1, 1))) # dummy rf
            if hasattr(self.model, 'target_type'):
                forecast_theta, _, _ = self.model.predict(X_seq_scaled, np.array([current_theta]))
                forecast_theta = forecast_theta[0]
            else:
                forecast_theta = self.model.predict(X_seq_scaled)[0]
            
            # Get rolling ET0
            et0_mean_7d = env_history['ET0_mean_7d']
            et0_current = env_history['ET0_current_24h']
            
            decision_type = 'HOLD'
            
            if forecast_theta < self.theta_critical:
                decision_type = 'IRRIGATE'
            elif self.theta_critical <= forecast_theta < self.theta_buffer:
                if et0_current >= et0_mean_7d:
                    decision_type = 'IRRIGATE'
                else:
                    decision_type = 'DELAY' # Delay 24h
            else:
                decision_type = 'HOLD' # Hold
                
            if decision_type == 'IRRIGATE':
                current_theta = state['theta_sensor']
                etc_24h = np.sum(env_history['ETc_24h'])
                p_eff_24h = np.sum(env_history['P_eff_24h'])
                vol = self.calculate_volume(etc_24h, p_eff_24h, current_theta)
                return vol, {'decision_type': decision_type, 'forecast_theta': float(forecast_theta)}
                
            return 0.0, {'decision_type': decision_type, 'forecast_theta': float(forecast_theta)}
            
        return 0.0, {}

class PersistenceAIPolicy(IrrigationPolicy):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, "Persistence AI")
        ai_cfg = self.irrigation_cfg.get('policies', {}).get('proposed_ai', {})
        self.theta_critical = self.irrigation_cfg.get('thresholds', {}).get('critical_theta', {}).get('value', 0.2025)
        self.theta_buffer = self.irrigation_cfg.get('thresholds', {}).get('buffer_theta', {}).get('value', 0.2200)
        self.window_days = ai_cfg.get('et0_reference', {}).get('window_days', 7)
        self.days_elapsed = 0
        
    def evaluate(self, t_idx: int, timestamp: pd.Timestamp, 
                 state: Dict[str, Any], env_history: Dict[str, Any]) -> float:
        
        # Track days elapsed for the warmup period
        if timestamp.hour == self.decision_hour and timestamp.minute == 0:
            self.days_elapsed += 1

        if timestamp.hour == self.decision_hour and timestamp.minute == 0:
            # Warm-up check: AI not active until 7 completed days
            if self.days_elapsed < self.window_days:
                # Fallback to HOLD or IoT during warmup? Let's fallback to IoT logic
                current_theta = state['theta_sensor']
                if current_theta < self.theta_critical:
                    etc_24h = np.sum(env_history['ETc_24h'])
                    p_eff_24h = np.sum(env_history['P_eff_24h'])
                    vol = self.calculate_volume(etc_24h, p_eff_24h, current_theta)
                    return vol, {'decision_type': 'WARMUP_IOT', 'forecast_theta': np.nan}
                return 0.0, {'decision_type': 'WARMUP_HOLD', 'forecast_theta': np.nan}

            # Get the forecast - using persistence!
            forecast_theta = state['theta_sensor']
            
            # Get rolling ET0
            et0_mean_7d = env_history['ET0_mean_7d']
            et0_current = env_history['ET0_current_24h']
            
            decision_type = 'HOLD'
            
            if forecast_theta < self.theta_critical:
                decision_type = 'IRRIGATE'
            elif self.theta_critical <= forecast_theta < self.theta_buffer:
                if et0_current >= et0_mean_7d:
                    decision_type = 'IRRIGATE'
                else:
                    decision_type = 'DELAY' # Delay 24h
            else:
                decision_type = 'HOLD' # Hold
                
            if decision_type == 'IRRIGATE':
                current_theta = state['theta_sensor']
                etc_24h = np.sum(env_history['ETc_24h'])
                p_eff_24h = np.sum(env_history['P_eff_24h'])
                vol = self.calculate_volume(etc_24h, p_eff_24h, current_theta)
                return vol, {'decision_type': decision_type, 'forecast_theta': float(forecast_theta)}
                
            return 0.0, {'decision_type': decision_type, 'forecast_theta': float(forecast_theta)}
            
        return 0.0, {}
