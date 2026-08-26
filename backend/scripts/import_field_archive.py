"""
One-Time Field Archive Import Script.
Writes campaign metadata, data import records (registering field_2026_v1 as LOCKED and field_2026_v2_september as ACTIVE),
and manuscript validation records into the metadata database.
"""
import os
import sys
import hashlib
import json
import pandas as pd
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session
from app.database.postgres import engine, Base, SessionLocal
from app.models.field import FieldCampaign, DataImport, ValidationRun

def compute_file_hash(filepath: Path) -> str:
    if not filepath.exists():
        return "N/A"
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def import_archive():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    base_dir = Path("c:/Users/Prabakaran/Desktop/Agrivoltaics simulation")
    manifest_path = base_dir / "data" / "field" / "manifests" / "raw_sha256.csv"
    qc_report_path = base_dir / "data" / "field" / "qc_2min" / "zone_A" / "zone_A_v1_manuscript_qc.parquet"
    ana_a_v1 = base_dir / "data" / "field" / "analytical_5min" / "zone_A" / "field_zone_A_5min.parquet"
    ana_a_v2 = base_dir / "data" / "field" / "analytical_5min" / "zone_A" / "field_v2_september_zone_A_5min.parquet"

    raw_hash = compute_file_hash(manifest_path)
    qc_hash = compute_file_hash(qc_report_path)
    ana_v1_hash = compute_file_hash(ana_a_v1)
    ana_v2_hash = compute_file_hash(ana_a_v2)

    # 1. Field Campaign
    existing_campaign = db.query(FieldCampaign).filter(FieldCampaign.name == "Field Campaign 2026").first()
    if not existing_campaign:
        campaign = FieldCampaign(
            name="Field Campaign 2026",
            start_time="2026-07-22 00:00:00",
            end_time="2026-09-30 23:58:00",
            sampling_native="2 min / 5 min",
            sampling_analysis="5 min",
            location="Agrivoltaic Experimental Research Station",
            status="COMPLETED"
        )
        db.add(campaign)

    # 2. Data Import v1 (Manuscript dataset - LOCKED = True)
    existing_v1 = db.query(DataImport).filter(DataImport.dataset_version == "field_2026_v1").first()
    if not existing_v1:
        imp_v1 = DataImport(
            dataset_version="field_2026_v1",
            status="LOCKED",
            locked=True,
            raw_sha256=raw_hash,
            qc_sha256=qc_hash,
            analysis_sha256=ana_v1_hash,
            zone="ALL",
            raw_rows=18432,
            valid_rows=18432,
            analytical_rows=18432
        )
        db.add(imp_v1)

    # 3. Data Import v2 (September dataset - ACTIVE)
    existing_v2 = db.query(DataImport).filter(DataImport.dataset_version == "field_2026_v2_september").first()
    if not existing_v2:
        imp_v2 = DataImport(
            dataset_version="field_2026_v2_september",
            status="ACTIVE",
            locked=False,
            raw_sha256=raw_hash,
            qc_sha256=qc_hash,
            analysis_sha256=ana_v2_hash,
            zone="ALL",
            raw_rows=61632,
            valid_rows=61632,
            analytical_rows=40896
        )
        db.add(imp_v2)

    # 4. Manuscript Validation Runs
    db.query(ValidationRun).filter(ValidationRun.dataset_version == "field_2026_v1").delete()
    
    v_zero = ValidationRun(
        dataset_version="field_2026_v1",
        model_version="ElasticNet_RUN4",
        test_window="Days 17-31 Chronological Held-out",
        adaptation_days=0,
        adaptation_type="Zero-Shot",
        rmse_mm=16.37,
        mae_mm=13.75,
        r2_score=-0.2867
    )
    v_7day = ValidationRun(
        dataset_version="field_2026_v1",
        model_version="ElasticNet_RUN4",
        test_window="Days 17-31 Chronological Held-out",
        adaptation_days=7,
        adaptation_type="7-Day Adaptation",
        rmse_mm=12.69,
        mae_mm=9.83,
        r2_score=0.2271
    )
    v_16day = ValidationRun(
        dataset_version="field_2026_v1",
        model_version="ElasticNet_RUN4",
        test_window="Days 17-31 Chronological Held-out",
        adaptation_days=16,
        adaptation_type="16-Day Adaptation",
        rmse_mm=7.33,
        mae_mm=5.82,
        r2_score=0.7421
    )
    
    db.add_all([v_zero, v_7day, v_16day])
    db.commit()
    db.close()

    print("[IMPORT] Dataset field_2026_v1 successfully registered and LOCKED.")
    print("[IMPORT] Dataset field_2026_v2_september successfully registered and ACTIVE.")

if __name__ == "__main__":
    import_archive()
