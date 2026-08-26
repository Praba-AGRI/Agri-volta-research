from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from app.config.settings import settings
from app.utils.logging import logger

class InfluxDBManager:
    def __init__(self):
        self.client = InfluxDBClient(
            url=settings.INFLUXDB_URL,
            token=settings.INFLUXDB_TOKEN,
            org=settings.INFLUXDB_ORG
        )
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()

    def get_bucket(self, mode: str) -> str:
        """Return the correct bucket based on dataset mode"""
        if mode.upper() == "SIMULATION":
            return settings.INFLUXDB_BUCKET_SIMULATION
        elif mode.upper() == "FIELD":
            return settings.INFLUXDB_BUCKET_FIELD
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be SIMULATION or FIELD.")

    def close(self):
        self.client.close()

influx_manager = InfluxDBManager()
