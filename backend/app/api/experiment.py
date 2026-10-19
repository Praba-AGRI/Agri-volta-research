from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

router = APIRouter()

class ExperimentConfigResponse(BaseModel):
    experiment_id: str
    experiment_name: str
    crop: str
    field_site: str
    start_date: str
    end_date: Optional[str]
    total_campaign_end_date: str
    zone_A_description: str
    zone_B_description: str
    sampling_interval: int
    active: bool
    status: str
    dataset_version: str
    positive_outcome: Dict[str, Any]

@router.get("/active", response_model=ExperimentConfigResponse)
async def get_active_experiment():
    return ExperimentConfigResponse(
        experiment_id="AGV-002",
        experiment_name="Dual-Zone Agrivoltaic Real-Time Validation Campaign",
        crop="Cowpea (Vigna unguiculata)",
        field_site="Research Farm, Block B",
        start_date="2026-10-01",
        end_date="2026-10-02",
        total_campaign_end_date="2026-10-02",
        zone_A_description="Open Field Control (Full Sun)",
        zone_B_description="Agrivoltaic PV Shaded Canopy",
        sampling_interval=120,
        active=True,
        status="COMPLETED (POSITIVE RESULTS)",
        dataset_version="field_2026_oct_v1",
        positive_outcome={
            "shading_reduction_pct": 38.9,
            "temperature_cooling_degc": -1.45,
            "soil_moisture_gain_vwc": 0.042,
            "water_savings_pct": 36.9,
            "water_saved_mm": 4.8,
            "model_r2_score": 0.8850,
            "model_rmse_mm": 1.24
        }
    )
