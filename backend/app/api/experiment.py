import json
import os
from fastapi import APIRouter
from typing import Optional
from pydantic import BaseModel

router = APIRouter()

CONFIG_FILE = "experiment_config.json"

DEFAULT_CONFIG = {
    "experiment_id": "AGV-001",
    "experiment_name": "Agrivoltaic Microclimate Study",
    "crop": "Cowpea (Vigna unguiculata)",
    "field_site": "Research Farm, Block B",
    "start_date": "2026-07-22",
    "end_date": "2026-08-22",
    "total_campaign_end_date": "2026-09-30",
    "zone_A_description": "Open Field Control (Full Sun)",
    "zone_B_description": "Agrivoltaic PV Shaded Canopy",
    "sampling_interval": 120,
    "active": False,
    "status": "FINISHED",
    "dataset_version": "field_2026_v1"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                # Enforce finished status for current campaign
                data["active"] = False
                data["status"] = "FINISHED"
                data["start_date"] = "2026-07-22"
                data["end_date"] = "2026-08-22"
                return data
        except Exception:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

class ExperimentResponse(BaseModel):
    experiment_id: str
    experiment_name: str
    crop: str
    field_site: str
    start_date: str
    end_date: Optional[str] = "2026-08-22"
    zone_A_description: str
    zone_B_description: str
    sampling_interval: int
    active: bool
    status: str = "FINISHED"
    dataset_version: str = "field_2026_v1"

class ExperimentUpdate(BaseModel):
    crop: str
    start_date: str
    end_date: Optional[str] = "2026-08-22"
    sampling_interval: int

@router.get("/active", response_model=ExperimentResponse)
async def get_active_experiment():
    return load_config()

@router.post("/active", response_model=ExperimentResponse)
async def update_active_experiment(payload: ExperimentUpdate):
    config = load_config()
    config["crop"] = payload.crop
    config["start_date"] = payload.start_date
    if payload.end_date:
        config["end_date"] = payload.end_date
    config["sampling_interval"] = payload.sampling_interval
    save_config(config)
    return config
