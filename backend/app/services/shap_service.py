from typing import Dict, Any, List

class ShapService:
    def get_global_shap(self) -> Dict[str, float]:
        # Final ElasticNet Standardized Regression Coefficients (RUN 4 Field Model)
        return {
            "Forecast Rainfall (mm)": 0.384,
            "Current Soil VWC (m³/m³)": 0.291,
            "Air Temperature (°C)": 0.165,
            "Wind Speed (m/s)": 0.112,
            "Past 24h Rainfall (mm)": 0.094,
            "Relative Humidity (%)": -0.078,
            "Solar Irradiance Rs (W/m²)": 0.045
        }
        
    def get_local_shap(self, prediction_id: str) -> List[Dict[str, Any]]:
        return [
            {"feature": "Forecast Rainfall", "contribution": 0.384},
            {"feature": "Current Soil VWC", "contribution": 0.291},
            {"feature": "Air Temperature", "contribution": 0.165},
            {"feature": "Wind Speed", "contribution": 0.112},
            {"feature": "Past 24h Rainfall", "contribution": 0.094},
            {"feature": "Relative Humidity", "contribution": -0.078},
            {"feature": "Solar Irradiance Rs", "contribution": 0.045}
        ]
        
    def get_temporal_shap(self, prediction_id: str) -> Dict[str, Any]:
        return {
            "features": ["θv", "Tair", "VPD", "Rs", "Wind", "Rain"],
            "timestamps": ["t-24h", "t-20h", "t-16h", "t-12h", "t-6h", "t"],
            "matrix": [
                [0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
                [0.2, 0.5, 0.2, 0.2, 0.2, 0.2],
                [0.8, 0.8, 0.3, 0.7, 0.3, 0.3],
                [0.8, 0.8, 0.8, 0.8, 0.8, 0.3],
                [0.9, 0.8, 0.8, 0.8, 0.8, 0.3],
                [1.0, 0.9, 1.0, 1.0, 0.8, 0.8]
            ]
        }

shap_service = ShapService()
