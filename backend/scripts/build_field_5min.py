"""
Deterministic 5-Minute Analytical Dataset Resampling Script.
Transforms QC field telemetry into standardized 5-minute analytical Parquet/CSV files.
"""
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path

def calc_vpd(t_c: pd.Series, rh_pct: pd.Series) -> pd.Series:
    e_s = 0.61078 * np.exp((17.27 * t_c) / (t_c + 237.3))
    return e_s * (1.0 - (rh_pct / 100.0))

def build_5min_dataset(qc_dir: Path, ana_dir: Path, zone_name: str, dataset_tag: str, output_name: str) -> dict:
    os.makedirs(ana_dir, exist_ok=True)
    qc_file = qc_dir / f"zone_{zone_name}_{dataset_tag}_qc.parquet"
    
    if not qc_file.exists():
        return {"error": f"QC file {qc_file} not found"}
        
    df_qc = pd.read_parquet(qc_file)
    df_qc['timestamp'] = pd.to_datetime(df_qc['timestamp'])
    df_qc = df_qc.set_index('timestamp')

    cols_mean = ['air_temp_c', 'humidity_pct', 'pressure_hpa', 'soil_temp_c', 'soil_vwc_mean', 'light_up_lux', 'light_down_lux']
    existing_cols = [c for c in cols_mean if c in df_qc.columns]

    df_5m = df_qc[existing_cols].resample('5min', label='left', closed='left').mean().interpolate(method='linear')
    
    if 'air_temp_c' in df_5m.columns and 'humidity_pct' in df_5m.columns:
        df_5m['vpd_kpa'] = calc_vpd(df_5m['air_temp_c'], df_5m['humidity_pct'])
        
    if 'light_up_lux' in df_5m.columns:
        df_5m['rs_down_wm2'] = df_5m['light_up_lux'] * 0.0079

    df_5m['zone'] = zone_name
    df_5m['mode'] = 'FIELD'
    df_5m['source'] = 'SD_ARCHIVE'
    df_5m['quality'] = 'VALID'

    parquet_out = ana_dir / f"{output_name}.parquet"
    csv_out = ana_dir / f"{output_name}.csv"

    df_5m.reset_index().to_parquet(parquet_out, index=False)
    df_5m.reset_index().to_csv(csv_out, index=False)

    rows = len(df_5m)
    print(f"[5MIN] {output_name}: {rows} analytical 5-min records generated. Saved to {parquet_out}")
    return {
        "dataset": dataset_tag,
        "zone": zone_name,
        "analytical_rows": int(rows),
        "parquet_output": str(parquet_out)
    }

def run_build_5min():
    base_dir = Path("c:/Users/Prabakaran/Desktop/Agrivoltaics simulation")
    qc_dir = base_dir / "data" / "field" / "qc_2min" / "zone_A"
    qc_dir_b = base_dir / "data" / "field" / "qc_2min" / "zone_B"
    ana_dir_a = base_dir / "data" / "field" / "analytical_5min" / "zone_A"
    ana_dir_b = base_dir / "data" / "field" / "analytical_5min" / "zone_B"

    # 1. Manuscript v1 (July-August)
    build_5min_dataset(qc_dir, ana_dir_a, "A", "v1_manuscript", "field_zone_A_5min")
    build_5min_dataset(qc_dir_b, ana_dir_b, "B", "v1_manuscript", "field_zone_B_5min")

    # 2. September v2 (September 2-min resampled to 5-min analytical)
    build_5min_dataset(qc_dir, ana_dir_a, "A", "v2_september", "field_v2_september_zone_A_5min")
    build_5min_dataset(qc_dir_b, ana_dir_b, "B", "v2_september", "field_v2_september_zone_B_5min")

if __name__ == "__main__":
    run_build_5min()
