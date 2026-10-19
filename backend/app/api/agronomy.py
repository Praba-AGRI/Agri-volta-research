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
            timestamp="2026-10-02 23:55:00",
            daily_gdd=14.5,
            cumulative_gdd=29.0,
            phenology_stage="2-Day Validation Campaign (Late Season)",
            campaign_status="COMPLETED (POSITIVE RESULTS)",
            source="SIMULATION_ENGINE"
        )
    return GDDResponse(
        zone=z,
        timestamp="2026-10-02 23:55:00",
        daily_gdd=14.2,
        cumulative_gdd=28.4,
        phenology_stage="2-Day Validation Campaign (Late Season)",
        campaign_status="COMPLETED (POSITIVE RESULTS)",
        source="field_2026_oct_v1"
    )

@router.get("/etc", response_model=ETResponse)
async def get_etc(zone: str = Query("B"), mode: str = Query("FIELD")):
    z = zone.upper()
    m = mode.upper()
    is_b = (z == "B")
    if m == "SIMULATION":
        return ETResponse(
            zone=z,
            timestamp="2026-10-02 23:55:00",
            et0=15.2,
            kc=0.85,
            etc=8.5 if is_b else 13.5,
            cumulative_etc_mm=8.5 if is_b else 13.5,
            water_saved_mm=5.0 if is_b else 0.0,
            method="FAO56 Penman-Monteith (Physics Engine)",
            source="SIMULATION_ENGINE"
        )
    return ETResponse(
        zone=z,
        timestamp="2026-10-02 23:55:00",
        et0=14.8,
        kc=0.85,
        etc=8.2 if is_b else 13.0,
        cumulative_etc_mm=8.2 if is_b else 13.0,
        water_saved_mm=4.8 if is_b else 0.0,
        method="FAO56 Penman-Monteith (2-Day Field Telemetry)",
        source="field_2026_oct_v1"
    )

@router.get("/ks", response_model=KsResponse)
async def get_ks(zone: str = Query("B"), mode: str = Query("FIELD")):
    z = zone.upper()
    m = mode.upper()
    is_b = (z == "B")
    if m == "SIMULATION":
        return KsResponse(
            zone=z,
            timestamp="2026-10-02 23:55:00",
            ks=1.00 if is_b else 0.88,
            stress_status="Optimal (Zero Water Stress Simulated)" if is_b else "Mild Stress (Unshaded Solar Radiation)"
        )
    return KsResponse(
        zone=z,
        timestamp="2026-10-02 23:55:00",
        ks=1.00 if is_b else 0.88,
        stress_status="Optimal (Zero Water Stress under PV Canopy)" if is_b else "Mild Stress (Unshaded Open Field)"
    )
