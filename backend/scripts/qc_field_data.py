"""
Quality Control (QC) Data Processing Script.
Processes raw files for both 2-min September and 5-min July-August manuscript datasets into clean QC Parquet files.
"""
import os
import glob
import json
import pandas as pd
from pathlib import Path

def process_qc_directory(raw_dir: Path, qc_dir: Path, zone_name: str, dataset_tag: str) -> dict:
    os.makedirs(qc_dir, exist_ok=True)
    csv_files = sorted(glob.glob(str(raw_dir / "*.csv")))
    
    dfs = []
    for f in csv_files:
        df = pd.read_csv(f)
        dfs.append(df)
        
    df_raw = pd.concat(dfs, ignore_index=True)
    df_raw['timestamp'] = pd.to_datetime(df_raw['timestamp'])
    
    raw_rows = len(df_raw)
    
    flag_cols = ['bme_ok', 'bh1_ok', 'ds18_ok', 'rtc_ok']
    existing_flags = [c for c in flag_cols if c in df_raw.columns]
    
    if existing_flags:
        qc_mask = (df_raw[existing_flags] == 1).all(axis=1)
    else:
        qc_mask = pd.Series(True, index=df_raw.index)
        
    df_flagged = df_raw[qc_mask]
    df_qc = df_flagged.sort_values('timestamp').drop_duplicates(subset=['timestamp']).copy()
    valid_rows = len(df_qc)

    parquet_path = qc_dir / f"zone_{zone_name}_{dataset_tag}_qc.parquet"
    df_qc.to_parquet(parquet_path, index=False)

    report = {
        "dataset": dataset_tag,
        "zone": zone_name,
        "raw_rows": int(raw_rows),
        "valid_rows": int(valid_rows),
        "parquet_output": str(parquet_path)
    }
    return report

def run_qc_pipeline():
    base_dir = Path("c:/Users/Prabakaran/Desktop/Agrivoltaics simulation")
    raw_2m = base_dir / "data" / "field" / "raw_2min"
    raw_5m = base_dir / "data" / "field" / "raw_5min"
    qc_dir = base_dir / "data" / "field" / "qc_2min"
    
    # Process manuscript 5-min
    q1_a = process_qc_directory(raw_5m / "zone_A", qc_dir / "zone_A", "A", "v1_manuscript")
    q1_b = process_qc_directory(raw_5m / "zone_B", qc_dir / "zone_B", "B", "v1_manuscript")

    # Process September 2-min
    q2_a = process_qc_directory(raw_2m / "zone_A", qc_dir / "zone_A", "A", "v2_september")
    q2_b = process_qc_directory(raw_2m / "zone_B", qc_dir / "zone_B", "B", "v2_september")
    
    print(f"[QC] Complete. v1 Valid Records: {q1_a['valid_rows'] + q1_b['valid_rows']} | v2 Valid Records: {q2_a['valid_rows'] + q2_b['valid_rows']}")

if __name__ == "__main__":
    run_qc_pipeline()
