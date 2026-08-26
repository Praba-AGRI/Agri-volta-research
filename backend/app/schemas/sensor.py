from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class DataQualityFlag(str, Enum):
    VALID = "VALID"
    MISSING = "MISSING"
    INVALID = "INVALID"
    STALE = "STALE"
    OUTLIER = "OUTLIER"
    DUPLICATE = "DUPLICATE"

class TelemetryPayload(BaseModel):
    device_id: str = Field(..., description="Unique ESP32 device identifier")
    zone: str = Field(..., description="Zone identifier (A or B)")
    timestamp: datetime = Field(..., description="Observation timestamp")
    
    # Air BME280 parameters
    air_temperature: Optional[float] = None
    relative_humidity: Optional[float] = None
    pressure: Optional[float] = None
    vpd: Optional[float] = None
    
    # Soil Dallas DS18B20 temperature
    soil_temperature: Optional[float] = None
    
    # Soil capacitive moisture sensors
    soil_adc_1: Optional[int] = None
    soil_adc_2: Optional[int] = None
    soil_moisture_1: Optional[float] = None
    soil_moisture_2: Optional[float] = None
    soil_moisture_mean: Optional[float] = None
    soil_moisture: Optional[float] = None  # Mapping compatible
    soil_calibrated: Optional[bool] = None

    # BH1750 ambient light sensors
    lux_incident: Optional[float] = None
    lux_reflected: Optional[float] = None
    albedo: Optional[float] = None
    radiation: Optional[float] = None
    
    # v4 Shortwave Radiation Chain parameters
    rs_incoming: Optional[float] = None
    rs_reflected: Optional[float] = None
    rns_fao56: Optional[float] = None
    rns_measured: Optional[float] = None
    
    # Optional/deprecating compatibility fields
    rainfall: Optional[float] = None
    shade_fraction: Optional[float] = None

class ValidatedTelemetry(TelemetryPayload):
    quality: DataQualityFlag = DataQualityFlag.VALID
    quality_reason: Optional[str] = None
    received_at: datetime = Field(default_factory=datetime.utcnow, description="Server ingestion timestamp")
    device_timestamp: Optional[datetime] = None
