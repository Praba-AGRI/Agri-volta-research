import asyncio
import json
import aiomqtt
from app.config.settings import settings
from app.utils.logging import logger
from app.mqtt.validator import TelemetryValidator
from app.database.influx import influx_manager

class MQTTManager:
    def __init__(self):
        self.host = settings.MQTT_HOST
        self.port = settings.MQTT_PORT
        self.username = settings.MQTT_USERNAME
        self.password = settings.MQTT_PASSWORD
        self.topics = ["agrivoltaic/zone/+/telemetry"]
        
    async def start(self):
        try:
            async with aiomqtt.Client(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password
            ) as client:
                for topic in self.topics:
                    await client.subscribe(topic)
                    logger.info(f"Subscribed to MQTT topic: {topic}")
                
                async for message in client.messages:
                    await self.process_message(message)
        except aiomqtt.MqttError as e:
            logger.error(f"MQTT Error: {e}")
            
    async def process_message(self, message: aiomqtt.Message):
        topic = str(message.topic)
        payload_str = message.payload.decode()
        try:
            payload = json.loads(payload_str)
            validated_data = TelemetryValidator.validate(payload)
            
            logger.info(f"Processed telemetry from {validated_data.zone} - Quality: {validated_data.quality.value}")
            
            # Dispatch to Database Service (InfluxDB)
            bucket = settings.INFLUXDB_BUCKET_FIELD
            
            point = {
                "measurement": "field_measurements",
                "tags": {
                    "zone": validated_data.zone,
                    "device_id": validated_data.device_id,
                    "quality": validated_data.quality.value
                },
                "time": validated_data.device_timestamp.isoformat() if validated_data.device_timestamp else validated_data.timestamp.isoformat(),
                "fields": {
                    "soil_moisture": validated_data.soil_moisture,
                    "soil_moisture_1": validated_data.soil_moisture_1,
                    "soil_moisture_2": validated_data.soil_moisture_2,
                    "soil_moisture_mean": validated_data.soil_moisture_mean,
                    "soil_adc_1": validated_data.soil_adc_1,
                    "soil_adc_2": validated_data.soil_adc_2,
                    "soil_calibrated": validated_data.soil_calibrated,
                    "air_temperature": validated_data.air_temperature,
                    "relative_humidity": validated_data.relative_humidity,
                    "soil_temperature": validated_data.soil_temperature,
                    "radiation": validated_data.radiation,
                    "rs_incoming": validated_data.rs_incoming,
                    "rs_reflected": validated_data.rs_reflected,
                    "rns_fao56": validated_data.rns_fao56,
                    "rns_measured": validated_data.rns_measured,
                    "lux_incident": validated_data.lux_incident,
                    "lux_reflected": validated_data.lux_reflected,
                    "albedo": validated_data.albedo,
                    "pressure": validated_data.pressure,
                    "rainfall": validated_data.rainfall,
                    "vpd": validated_data.vpd,
                    "shade_fraction": validated_data.shade_fraction,
                    "received_at": validated_data.received_at.isoformat()
                }
            }
            # Remove None fields
            point["fields"] = {k: v for k, v in point["fields"].items() if v is not None}
            
            influx_manager.write_api.write(bucket=bucket, org=settings.INFLUXDB_ORG, record=point)
            
            # Dispatch to WebSocket Manager
            from app.websocket.manager import manager
            # Broadcast the validated data as dictionary
            ws_payload = validated_data.model_dump(mode='json')
            
            import asyncio
            # In a real app we might run this in a background task
            # asyncio.create_task(manager.broadcast(ws_payload))
            await manager.broadcast(ws_payload)
            
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON payload on topic {topic}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

mqtt_manager = MQTTManager()
