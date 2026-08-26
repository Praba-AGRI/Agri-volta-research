import time
import json
import random
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

# Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
TOPIC_A = "agrivoltaic/zone/A/telemetry"
TOPIC_B = "agrivoltaic/zone/B/telemetry"

def generate_payload(zone):
    now = datetime.now(timezone.utc).isoformat()
    if zone == "A":
        return {
            "device_id": "ESP32_ZONE_A",
            "zone": "A",
            "timestamp": now,
            "soil_moisture": round(random.uniform(0.20, 0.25), 3),
            "air_temperature": round(random.uniform(30.0, 33.0), 1),
            "relative_humidity": round(random.uniform(55.0, 65.0), 1),
            "soil_temperature": round(random.uniform(28.0, 31.0), 1),
            "radiation": round(random.uniform(600, 800), 1),
            "rainfall": 0.0,
            "vpd": round(random.uniform(1.2, 1.8), 2),
            "shade_fraction": 0.0
        }
    else:
        return {
            "device_id": "ESP32_ZONE_B",
            "zone": "B",
            "timestamp": now,
            "soil_moisture": round(random.uniform(0.23, 0.27), 3),
            "air_temperature": round(random.uniform(28.0, 30.0), 1),
            "relative_humidity": round(random.uniform(65.0, 75.0), 1),
            "soil_temperature": round(random.uniform(26.0, 29.0), 1),
            "radiation": round(random.uniform(300, 500), 1),
            "rainfall": 0.0,
            "vpd": round(random.uniform(0.8, 1.1), 2),
            "shade_fraction": 0.42
        }

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}", flush=True)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect

print(f"Connecting to MQTT Broker at {MQTT_BROKER}:{MQTT_PORT}...", flush=True)
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

try:
    while True:
        payload_a = generate_payload("A")
        client.publish(TOPIC_A, json.dumps(payload_a))
        print(f"Published Zone A: {payload_a['timestamp']}", flush=True)
        
        payload_b = generate_payload("B")
        client.publish(TOPIC_B, json.dumps(payload_b))
        print(f"Published Zone B: {payload_b['timestamp']}", flush=True)
        
        # Publish every 5 seconds for simulation (real hardware uses 5 mins)
        time.sleep(5)
except KeyboardInterrupt:
    print("Simulation stopped.")
    client.loop_stop()
    client.disconnect()
