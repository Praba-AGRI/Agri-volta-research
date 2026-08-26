from fastapi import APIRouter, Query
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel

router = APIRouter()

class ElasticNetPredictionResponse(BaseModel):
    issued_at: str
    target_time: str
    zone: str
    model_version: str
    ir_10: float
    ir_50: float
    ir_90: float
    applied_volume_mm: float
    safety_status: str
    confidence: str

@router.get("/latest", response_model=ElasticNetPredictionResponse)
async def get_latest_prediction(zone: str = Query("B", description="A or B")):
    current = datetime.now(timezone.utc)
    target = current + timedelta(hours=24)
    
    # Zone B ElasticNet Frozen Forecaster response
    ir_10 = 2.8 if zone.upper() == "B" else 4.1
    ir_50 = 4.8 if zone.upper() == "B" else 7.2
    ir_90 = 7.1 if zone.upper() == "B" else 9.8
    
    return ElasticNetPredictionResponse(
        issued_at=current.isoformat(),
        target_time=target.isoformat(),
        zone=zone.upper(),
        model_version="ELASTICNET-RUN2C-FROZEN-v1.0",
        ir_10=ir_10,
        ir_50=ir_50,
        ir_90=ir_90,
        applied_volume_mm=ir_50,
        safety_status="SAFE (Ks = 1.0)",
        confidence="HIGH (|ICE90| = 0.0811)"
    )

@router.get("/performance")
async def get_performance(mode: str = Query("OPERATIONAL")):
    return {
        "dataset_mode": mode.upper(),
        "freeze_winner": "ElasticNet Linear",
        "models": [
            {"model": "ElasticNet Linear", "rmse_ir_mm": 8.92, "fnr": 0.000, "ice90": 0.0811, "status": "FROZEN WINNER"},
            {"model": "Quantile Random Forest", "rmse_ir_mm": 10.91, "fnr": 0.0229, "ice90": 0.1000, "status": "ELIGIBLE"},
            {"model": "HistGradientBoosting", "rmse_ir_mm": 11.42, "fnr": 0.0717, "ice90": 0.0985, "status": "ELIGIBLE"},
            {"model": "Multi-Output BiLSTM", "rmse_ir_mm": 12.03, "fnr": 0.0000, "ice90": 0.3082, "status": "CALIBRATION FAIL"},
            {"model": "Physics-Only Forecast", "rmse_ir_mm": 31.68, "fnr": 0.2074, "ice90": 0.2210, "status": "INELIGIBLE"},
            {"model": "Persistence Baseline", "rmse_ir_mm": 34.36, "fnr": 0.3276, "ice90": 0.2850, "status": "INELIGIBLE"}
        ]
    }

@router.get("/attributions")
async def get_attributions():
    return {
        "model": "ElasticNet Linear (Frozen RUN 2C)",
        "attributions": [
            {"feature": "fc_P (Forecast 24h Rainfall)", "std_coef": -3.3264, "impact": "Strongly Decreases IR"},
            {"feature": "curr_theta (Current Soil Moisture)", "std_coef": -1.4901, "impact": "Decreases IR"},
            {"feature": "hist_T (Past Mean Air Temp)", "std_coef": 1.1092, "impact": "Increases IR (ET Demand)"},
            {"feature": "fc_u (Forecast Wind Speed)", "std_coef": -0.7420, "impact": "Aerodynamic Transport"},
            {"feature": "hist_P (Past 24h Rainfall)", "std_coef": 0.5528, "impact": "Antecedent Storage Adjustment"},
            {"feature": "fc_RH (Forecast Humidity)", "std_coef": -0.3152, "impact": "Lower VPD Decreases IR"},
            {"feature": "fc_Rs (Forecast Solar Radiation)", "std_coef": 0.2544, "impact": "Increases Radiation ET"}
        ]
    }
