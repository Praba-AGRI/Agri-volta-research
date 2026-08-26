from sqlalchemy import Column, Integer, String, Date, Boolean, Text
from app.database.postgres import Base

class ExperimentConfig(Base):
    __tablename__ = "experiment_configs"

    experiment_id = Column(String, primary_key=True, index=True)
    experiment_name = Column(String, index=True)
    crop = Column(String)
    field_site = Column(String)
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)
    zone_A_description = Column(Text)
    zone_B_description = Column(Text)
    sampling_interval = Column(Integer)  # in seconds
    active = Column(Boolean, default=True)
