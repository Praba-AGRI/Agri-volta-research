"""
Initialize permanent field data directories for both 2-min (September 2026) and 5-min (July-August 2026 manuscript) datasets,
copy raw SD-card telemetry CSVs from C:/Users/Prabakaran/Desktop/agrivoltaics realtime readings,
and generate SHA-256 manifests.
"""
import os
import glob
import hashlib
import shutil
import pandas as pd
from pathlib import Path

def init_field_data():
    base_dir = Path("c:/Users/Prabakaran/Desktop/Agrivoltaics simulation")
    src_dir = Path(r"C:\Users\Prabakaran\Desktop\agrivoltaics realtime readings")

    data_dir = base_dir / "data" / "field"
    
    # 2-min native directory (September campaign)
    raw_2m_a = data_dir / "raw_2min" / "zone_A"
    raw_2m_b = data_dir / "raw_2min" / "zone_B"
    qc_2m_a = data_dir / "qc_2min" / "zone_A"
    qc_2m_b = data_dir / "qc_2min" / "zone_B"

    # 5-min manuscript directory (July-August campaign)
    raw_5m_a = data_dir / "raw_5min" / "zone_A"
    raw_5m_b = data_dir / "raw_5min" / "zone_B"
    
    # Analytical outputs
    ana_5m_a = data_dir / "analytical_5min" / "zone_A"
    ana_5m_b = data_dir / "analytical_5min" / "zone_B"
    manifest_dir = data_dir / "manifests"

    for d in [raw_2m_a, raw_2m_b, qc_2m_a, qc_2m_b, raw_5m_a, raw_5m_b, ana_5m_a, ana_5m_b, manifest_dir]:
        os.makedirs(d, exist_ok=True)

    # 1. Process 5-min Manuscript files (July 22 - August 22)
    files_5m_a = sorted(glob.glob(str(src_dir / "Zone_A_5min" / "*.csv")))
    files_5m_b = sorted(glob.glob(str(src_dir / "Zone_B_5min" / "*.csv")))

    # 2. Process 2-min High-Frequency files (September 01 - September 30)
    files_2m_a = sorted(glob.glob(str(src_dir / "Zone_A_2min" / "*.csv")))
    files_2m_b = sorted(glob.glob(str(src_dir / "Zone_B_2min" / "*.csv")))

    manifest_records = []

    def process_files(files, dest_dir, zone_name, resolution_tag, dataset_ver):
        for fpath in files:
            fname = os.path.basename(fpath)
            dest_path = dest_dir / fname
            shutil.copy2(fpath, dest_path)
            
            with open(dest_path, 'rb') as f:
                h = hashlib.sha256(f.read()).hexdigest()
            size = os.path.getsize(dest_path)
            
            df = pd.read_csv(dest_path)
            min_ts = str(df['timestamp'].min()) if 'timestamp' in df.columns and len(df) > 0 else 'N/A'
            max_ts = str(df['timestamp'].max()) if 'timestamp' in df.columns and len(df) > 0 else 'N/A'
            rows = len(df)
            node_id = str(df['node_id'].iloc[0]) if 'node_id' in df.columns and len(df) > 0 else 'N/A'
            
            manifest_records.append({
                'filename': fname,
                'zone': zone_name,
                'native_resolution': resolution_tag,
                'dataset_version': dataset_ver,
                'node_id': node_id,
                'raw_rows': rows,
                'size_bytes': size,
                'sha256': h,
                'start_timestamp': min_ts,
                'end_timestamp': max_ts
            })

    process_files(files_5m_a, raw_5m_a, 'A', '5min', 'field_2026_v1')
    process_files(files_5m_b, raw_5m_b, 'B', '5min', 'field_2026_v1')

    process_files(files_2m_a, raw_2m_a, 'A', '2min', 'field_2026_v2_september')
    process_files(files_2m_b, raw_2m_b, 'B', '2min', 'field_2026_v2_september')

    manifest_df = pd.DataFrame(manifest_records)
    manifest_path = manifest_dir / 'raw_sha256.csv'
    manifest_df.to_csv(manifest_path, index=False)

    print(f"[INIT] Archived {len(files_5m_a)} Zone A 5-min files and {len(files_5m_b)} Zone B 5-min files (field_2026_v1 manuscript).")
    print(f"[INIT] Archived {len(files_2m_a)} Zone A 2-min files and {len(files_2m_b)} Zone B 2-min files (field_2026_v2 September).")
    print(f"[INIT] Total Raw Files Archived: {len(manifest_df)} | Total Raw Rows: {manifest_df['raw_rows'].sum()}")
    print(f"[INIT] Manifest saved to: {manifest_path}")

if __name__ == "__main__":
    init_field_data()
