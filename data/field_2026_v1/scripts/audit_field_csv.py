"""
Field Data Integrity Audit Script.
Checks raw CSV files (both 2-min September and 5-min July-August manuscript) without modifying them.
Reports expected rows, observed rows, missing timestamps, duplicates, status flags, and completeness %.
"""
import os
import glob
import json
import pandas as pd
import numpy as np
from pathlib import Path

def audit_directory(dir_path: Path, dataset_name: str, expected_freq: str) -> dict:
    csv_files = sorted(glob.glob(str(dir_path / "*.csv")))
    if not csv_files:
        return {"error": f"No CSV files found in {dir_path}"}
    
    dfs = []
    for f in csv_files:
        df = pd.read_csv(f)
        dfs.append(df)
    
    df_raw = pd.concat(dfs, ignore_index=True)
    observed_rows = len(df_raw)
    
    df_raw['ts_parsed'] = pd.to_datetime(df_raw['timestamp'], errors='coerce')
    unparseable_ts = df_raw['ts_parsed'].isna().sum()
    
    df_sorted = df_raw.sort_values('ts_parsed')
    duplicate_rows = df_sorted.duplicated(subset=['ts_parsed']).sum()
    
    if len(df_sorted) > 0 and unparseable_ts == 0:
        start_ts = df_sorted['ts_parsed'].min()
        end_ts = df_sorted['ts_parsed'].max()
        expected_grid = pd.date_range(start=start_ts, end=end_ts, freq=expected_freq)
        expected_rows = len(expected_grid)
    else:
        start_ts, end_ts = None, None
        expected_rows = observed_rows

    flag_cols = ['bme_ok', 'bh1_ok', 'bh2_ok', 'ds18_ok', 'rtc_ok', 'sd_ok']
    existing_flags = [c for c in flag_cols if c in df_raw.columns]
    
    if existing_flags:
        valid_flags_mask = (df_raw[existing_flags] == 1).all(axis=1)
    else:
        valid_flags_mask = pd.Series(True, index=df_raw.index)
        
    invalid_flag_count = (~valid_flags_mask).sum()

    range_mask = pd.Series(True, index=df_raw.index)
    if 'air_temp_c' in df_raw.columns:
        range_mask &= df_raw['air_temp_c'].between(-10, 60)
    if 'humidity_pct' in df_raw.columns:
        range_mask &= df_raw['humidity_pct'].between(0, 100)
    if 'pressure_hpa' in df_raw.columns:
        range_mask &= df_raw['pressure_hpa'].between(800, 1100)

    valid_mask = valid_flags_mask & range_mask & (~df_raw.duplicated(subset=['ts_parsed']))
    valid_rows = valid_mask.sum()
    completeness_pct = round((valid_rows / max(expected_rows, 1)) * 100, 2)
    
    return {
        "dataset_name": dataset_name,
        "files_count": len(csv_files),
        "expected_rows": int(expected_rows),
        "observed_rows": int(observed_rows),
        "unparseable_timestamps": int(unparseable_ts),
        "duplicate_timestamps": int(duplicate_rows),
        "invalid_sensor_flags": int(invalid_flag_count),
        "valid_rows": int(valid_rows),
        "completeness_percent": completeness_pct,
        "start_timestamp": str(start_ts),
        "end_timestamp": str(end_ts)
    }

def run_audit():
    base_dir = Path("c:/Users/Prabakaran/Desktop/Agrivoltaics simulation")
    raw_2m = base_dir / "data" / "field" / "raw_2min"
    raw_5m = base_dir / "data" / "field" / "raw_5min"
    manifest_dir = base_dir / "data" / "field" / "manifests"
    
    rep_v1_a = audit_directory(raw_5m / "zone_A", "field_2026_v1_Zone_A", "5min")
    rep_v1_b = audit_directory(raw_5m / "zone_B", "field_2026_v1_Zone_B", "5min")

    rep_v2_a = audit_directory(raw_2m / "zone_A", "field_2026_v2_september_Zone_A", "2min")
    rep_v2_b = audit_directory(raw_2m / "zone_B", "field_2026_v2_september_Zone_B", "2min")

    full_audit = {
        "field_2026_v1_manuscript": {
            "zone_A": rep_v1_a,
            "zone_B": rep_v1_b,
            "total_observed": rep_v1_a["observed_rows"] + rep_v1_b["observed_rows"]
        },
        "field_2026_v2_september": {
            "zone_A": rep_v2_a,
            "zone_B": rep_v2_b,
            "total_observed": rep_v2_a["observed_rows"] + rep_v2_b["observed_rows"]
        },
        "grand_total_observed": rep_v1_a["observed_rows"] + rep_v1_b["observed_rows"] + rep_v2_a["observed_rows"] + rep_v2_b["observed_rows"]
    }

    out_file = manifest_dir / "raw_audit_report.json"
    with open(out_file, "w") as f:
        json.dump(full_audit, f, indent=2)

    print("==========================================================================")
    print("                     FIELD DATA INTEGRITY AUDIT                           ")
    print("==========================================================================")
    print(f"Manuscript v1: Observed={full_audit['field_2026_v1_manuscript']['total_observed']} | Completeness A={rep_v1_a['completeness_percent']}% | B={rep_v1_b['completeness_percent']}%")
    print(f"September v2:  Observed={full_audit['field_2026_v2_september']['total_observed']} | Completeness A={rep_v2_a['completeness_percent']}% | B={rep_v2_b['completeness_percent']}%")
    print(f"Audit report saved to: {out_file}")
    print("==========================================================================")

if __name__ == "__main__":
    run_audit()
