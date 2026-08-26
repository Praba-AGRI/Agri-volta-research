from fastapi import APIRouter, Query
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

class GDDResponse(BaseModel):
    zone: str
    timestamp: str
    daily_gdd: float
    cumulative_gdd: float
    phenology_stage: str
    campaign_status: str
    source: str

class ETResponse(BaseModel):
    zone: str
    timestamp: str
    et0: float
    kc: float
    etc: float
    cumulative_etc_mm: float
    water_saved_mm: float
    method: str
    source: str

class KsResponse(BaseModel):
    zone: str
    timestamp: str
    ks: float
    stress_status: str

@router.get("/gdd", response_model=GDDResponse)
async def get_gdd(zone: str = Query("B"), mode: str = Query("FIELD")):
    z = zone.upper()
    m = mode.upper()
    if m == "SIMULATION":
        return GDDResponse(
            zone=z,
            timestamp="DIGITAL_TWIN_ACTIVE",
            daily_gdd=9.4,
            cumulative_gdd=712.4,
            phenology_stage="Simulated Late Grain Fill",
            campaign_status="SIMULATION_RUNNING",
            source="SIMULATION_ENGINE"
        )
    return GDDResponse(
        zone=z,
        timestamp="2026-08-22 23:55:00",
        daily_gdd=0.0,
        cumulative_gdd=684.5,
        phenology_stage="Maturity / Harvested (Completed)",
        campaign_status="FINISHED",
        source="SD_ARCHIVE"
    )

@router.get("/etc", response_model=ETResponse)
async def get_etc(zone: str = Query("B"), mode: str = Query("FIELD")):
    z = zone.upper()
    m = mode.upper()
    is_b = (z == "B")
    if m == "SIMULATION":
        return ETResponse(
            zone=z,
            timestamp="DIGITAL_TWIN_ACTIVE",
            et0=154.2,
            kc=0.88,
            etc=121.8 if is_b else 139.5,
            cumulative_etc_mm=121.8 if is_b else 139.5,
            water_saved_mm=17.7 if is_b else 0.0,
            method="FAO56 Penman-Monteith (Simulated)",
            source="SIMULATION_ENGINE"
        )
    return ETResponse(
        zone=z,
        timestamp="2026-08-22 23:55:00",
        et0=142.8,
        kc=0.85,
        etc=112.4 if is_b else 128.5,
        cumulative_etc_mm=112.4 if is_b else 128.5,
        water_saved_mm=16.1 if is_b else 0.0,
        method="FAO56 Penman-Monteith",
        source="SD_ARCHIVE"
    )

@router.get("/ks", response_model=KsResponse)
async def get_ks(zone: str = Query("B"), mode: str = Query("FIELD")):
    z = zone.upper()
    m = mode.upper()
    if m == "SIMULATION":
        return KsResponse(
            zone=z,
            timestamp="DIGITAL_TWIN_ACTIVE",
            ks=0.98,
            stress_status="Mild Transpirational Stress (Simulated)"
        )
    return KsResponse(
        zone=z,
        timestamp="2026-08-22 23:55:00",
        ks=1.00,
        stress_status="Optimal (No Water Stress)"
    )
