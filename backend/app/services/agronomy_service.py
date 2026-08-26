from datetime import datetime
from typing import Dict, Any

class AgronomyService:
    # Hardcoded crop coefficients (example values for Agrivoltaic crop)
    BASE_TEMP = 10.0 # Base temperature for GDD calculation
    
    @staticmethod
    def calculate_gdd(t_max: float, t_min: float) -> float:
        """Calculate daily Growing Degree Days"""
        mean_temp = (t_max + t_min) / 2.0
        gdd = mean_temp - AgronomyService.BASE_TEMP
        return max(0.0, gdd)
        
    @staticmethod
    def determine_phenology(cumulative_gdd: float) -> str:
        """Determine phenological stage from cumulative GDD"""
        if cumulative_gdd < 200:
            return "Initial"
        elif cumulative_gdd < 500:
            return "Crop Development"
        elif cumulative_gdd < 900:
            return "Mid-Season"
        else:
            return "Late Season"
            
    @staticmethod
    def get_kc(stage: str) -> float:
        """Return crop coefficient based on stage"""
        stages = {
            "Initial": 0.4,
            "Crop Development": 0.8,
            "Mid-Season": 1.15,
            "Late Season": 0.7
        }
        return stages.get(stage, 0.4)
        
    @staticmethod
    def calculate_etc(et0: float, kc: float) -> float:
        """Calculate Crop Evapotranspiration"""
        return et0 * kc
        
    @staticmethod
    def calculate_ks(soil_moisture: float, theta_fc: float, theta_wp: float, p: float = 0.5) -> float:
        """
        Calculate water stress coefficient (Ks)
        theta_fc: Field Capacity
        theta_wp: Wilting Point
        p: Depletion fraction
        """
        raw = theta_fc - theta_wp # Total available water
        taw = raw
        raw_depleted = theta_fc - soil_moisture
        
        if raw_depleted <= p * taw:
            return 1.0
        elif raw_depleted >= taw:
            return 0.0
        else:
            return (taw - raw_depleted) / ((1 - p) * taw)

agronomy_service = AgronomyService()
