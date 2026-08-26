import csv
import os
from io import StringIO
import pandas as pd
from pathlib import Path
from fastapi import APIRouter, Query, Response
from typing import Optional

router = APIRouter()

PARAM_MAP = {
    "soil_moisture": "soil_vwc_mean",
    "soil_vwc_mean": "soil_vwc_mean",
    "air_temperature": "air_temp_c",
    "relative_humidity": "humidity_pct",
    "soil_temperature": "soil_temp_c",
    "radiation": "rs_down_wm2",
    "vpd": "vpd_kpa"
}

def get_base_dir() -> Path:
    if Path("/app/data").exists():
        return Path("/app")
    return Path(".")

@router.get("/csv")
@router.get("/sensors")
async def export_csv(
    zone: str = Query("A", description="A, B, or BOTH"),
    parameter: str = Query("soil_moisture"),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    resolution: str = Query("5m"),
    mode: str = Query("FIELD"),
    dataset_version: Optional[str] = Query("field_2026_v1")
):
    base_dir = get_base_dir()
    zone_upper = zone.upper()
    col_name = PARAM_MAP.get(parameter, "soil_vwc_mean")
    zones = ["A", "B"] if zone_upper in ["BOTH", "ALL"] else [zone_upper]

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['timestamp', 'zone', 'mode', 'parameter', 'value', 'quality', 'source', 'dataset_version'])

    for z in zones:
        if dataset_version == "field_2026_v2_september":
            p_file = base_dir / "data" / "field" / "analytical_5min" / f"zone_{z}" / f"field_v2_september_zone_{z}_5min.parquet"
        else:
            p_file = base_dir / "data" / "field" / "analytical_5min" / f"zone_{z}" / f"field_zone_{z}_5min.parquet"
            if not p_file.exists():
                p_file = base_dir / "outputs" / "FIELD_VALIDATION" / f"field_zone_{z}_5min.parquet"

        if p_file.exists():
            df = pd.read_parquet(p_file)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')
            else:
                df.index = pd.to_datetime(df.index)

            df = df.sort_index()

            if start and start not in ["-7d", "now()"]:
                try:
                    df = df[df.index >= pd.to_datetime(start)]
                except Exception:
                    pass
            if end and end != "now()":
                try:
                    df = df[df.index <= pd.to_datetime(end)]
                except Exception:
                    pass

            if resolution in ["1h", "60m"] and col_name in df.columns:
                df = df[[col_name]].resample("1h").mean().dropna()
            elif resolution in ["1d", "24h"] and col_name in df.columns:
                df = df[[col_name]].resample("1D").mean().dropna()

            if col_name in df.columns:
                for ts, row in df.iterrows():
                    val = float(row[col_name]) if pd.notna(row[col_name]) else ""
                    writer.writerow([str(ts), z, mode.upper(), parameter, val, "VALID", "SD_ARCHIVE", dataset_version or "field_2026_v1"])

    filename = f"agrivoltaic_{mode.lower()}_{parameter}_{zone_upper}_{resolution}.csv"
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/predictions")
async def export_predictions(zone: str = Query("A"), mode: str = Query("FIELD")):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['issued_at', 'target_at', 'zone', 'mode', 'predicted_ir_p50_mm', 'actual_ir_mm', 'dataset_version'])
    writer.writerow([pd.Timestamp.now().isoformat(), pd.Timestamp.now().isoformat(), zone.upper(), mode.upper(), 4.8, 4.6, 'field_2026_v1'])
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=predictions_{zone}_{mode}.csv"}
    )
