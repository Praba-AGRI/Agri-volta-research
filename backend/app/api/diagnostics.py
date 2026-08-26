from fastapi import APIRouter, Query
from typing import Dict, Any

router = APIRouter()

@router.get("/summary")
async def get_diagnostics_summary(mode: str = Query("FIELD")) -> Dict[str, Any]:
    m = mode.upper()
    if m == "SIMULATION":
        return {
            "campaign_status": "SIMULATION_ENGINE_ACTIVE",
            "dataset_version": "simulation_v1",
            "mqtt_status": "SIMULATED",
            "expected_packets": 18432,
            "sampling_interval_min": 5,
            "total_audited_observations": 18432,
            "completeness_percent": 100.0,
            "zone_a": {
                "status": "SIMULATED",
                "packet_count": 9216,
                "packet_loss_pct": 0.0,
                "last_seen": "DIGITAL_TWIN_ACTIVE",
                "health": {
                    "bme280": 100.0,
                    "bh1750": 100.0,
                    "ds18b20": 100.0,
                    "rtc": 100.0
                }
            },
            "zone_b": {
                "status": "SIMULATED",
                "packet_count": 9216,
                "packet_loss_pct": 0.0,
                "last_seen": "DIGITAL_TWIN_ACTIVE",
                "health": {
                    "bme280": 100.0,
                    "bh1750": 100.0,
                    "ds18b20": 100.0,
                    "rtc": 100.0
                }
            }
        }

    return {
        "campaign_status": "FINISHED",
        "dataset_version": "field_2026_v1",
        "mqtt_status": "ONLINE",
        "expected_packets": 18432,
        "sampling_interval_min": 5,
        "total_audited_observations": 18432,
        "completeness_percent": 100.0,
        "zone_a": {
            "status": "COMPLETED",
            "packet_count": 9216,
            "packet_loss_pct": 0.0,
            "last_seen": "2026-08-22T23:55:00Z",
            "health": {
                "bme280": 100.0,
                "bh1750": 100.0,
                "ds18b20": 100.0,
                "rtc": 100.0
            }
        },
        "zone_b": {
            "status": "COMPLETED",
            "packet_count": 9216,
            "packet_loss_pct": 0.0,
            "last_seen": "2026-08-22T23:55:00Z",
            "health": {
                "bme280": 100.0,
                "bh1750": 100.0,
                "ds18b20": 100.0,
                "rtc": 100.0
            }
        }
    }
