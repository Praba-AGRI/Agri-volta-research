from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Agrivoltaic Field Monitor Backend"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"

    # MQTT
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    
    # InfluxDB
    INFLUXDB_URL: str = "http://localhost:8086"
    INFLUXDB_TOKEN: str = ""
    INFLUXDB_ORG: str = "agrivoltaics"
    INFLUXDB_BUCKET_FIELD: str = "agrivoltaic_field"
    INFLUXDB_BUCKET_SIMULATION: str = "agrivoltaic_simulation"

    # PostgreSQL
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/agrivoltaics"
    
    # ML
    MODEL_PATH: str = "models/bilstm/"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
