from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from app.database.postgres import Base
import datetime

class FieldCampaign(Base):
    __tablename__ = "field_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, default="Field Campaign 2026")
    start_time = Column(String, default="2026-07-22 00:00:00")
    end_time = Column(String, default="2026-08-22 23:55:00")
    sampling_native = Column(String, default="2 min")
    sampling_analysis = Column(String, default="5 min")
    location = Column(String, default="Agrivoltaic Experimental Research Station")
    status = Column(String, default="COMPLETED")

class DataImport(Base):
    __tablename__ = "data_imports"

    id = Column(Integer, primary_key=True, index=True)
    dataset_version = Column(String, index=True, default="field_2026_v1")
    status = Column(String, default="COMPLETED")
    locked = Column(Boolean, default=True)
    raw_sha256 = Column(String)
    qc_sha256 = Column(String)
    analysis_sha256 = Column(String)
    zone = Column(String, default="ALL")
    raw_rows = Column(Integer, default=18432)
    valid_rows = Column(Integer, default=18432)
    analytical_rows = Column(Integer, default=18432)
    import_time = Column(String, default=lambda: datetime.datetime.now().isoformat())

class ValidationRun(Base):
    __tablename__ = "validation_runs"

    id = Column(Integer, primary_key=True, index=True)
    dataset_version = Column(String, default="field_2026_v1")
    model_version = Column(String, default="ElasticNet_RUN4")
    test_window = Column(String, default="Days 17-31 Chronological Held-out")
    adaptation_days = Column(Integer) # 0, 7, 16
    adaptation_type = Column(String) # Zero-Shot, 7-Day Adaptation, 16-Day Adaptation
    rmse_mm = Column(Float)
    mae_mm = Column(Float)
    r2_score = Column(Float)
