from fastapi import APIRouter, Query
from app.services.shap_service import shap_service

router = APIRouter()

@router.get("/global")
async def get_global_shap(mode: str = Query("FIELD")):
    m = mode.upper()
    if m == "SIMULATION":
        return {
            "Simulated Forecast Rainfall (mm)": 0.412,
            "Simulated Soil VWC (m³/m³)": 0.310,
            "Simulated Air Temp (°C)": 0.145,
            "Simulated Wind Speed (m/s)": 0.098,
            "Simulated 24h Rain (mm)": 0.082,
            "Simulated RH (%)": -0.065,
            "Simulated Irradiance Rs (W/m²)": 0.038
        }
    return shap_service.get_global_shap()

@router.get("/local/{prediction_id}")
async def get_local_shap(prediction_id: str, mode: str = Query("FIELD")):
    m = mode.upper()
    if m == "SIMULATION":
        return [
            {"feature": "Simulated Forecast Rainfall", "contribution": 0.412},
            {"feature": "Simulated Soil VWC", "contribution": 0.310},
            {"feature": "Simulated Air Temp", "contribution": 0.145},
            {"feature": "Simulated Wind Speed", "contribution": 0.098},
            {"feature": "Simulated 24h Rain", "contribution": 0.082},
            {"feature": "Simulated RH", "contribution": -0.065},
            {"feature": "Simulated Irradiance Rs", "contribution": 0.038}
        ]
    return shap_service.get_local_shap(prediction_id)

@router.get("/temporal/{prediction_id}")
async def get_temporal_shap(prediction_id: str, mode: str = Query("FIELD")):
    return shap_service.get_temporal_shap(prediction_id)
