# Agrivoltaics Dual-Node ESP32-S3 Firmware Guide

This directory contains the production-grade, SD-free firmware for the **7SEMI ESP32-S3-WROOM-1U (N8R8) on Ozobot Devkit**, built for the AGRO-VOLT Explainable AI Irrigation Decision Support System.

---

## 📁 Firmware Directory Structure

```text
firmware/
├── Agrivoltaics_Node_ZoneA_Control/
│   └── Agrivoltaics_Node_ZoneA_Control.ino    # Flashed to Node 1 (Open Field Control, Zone A)
├── Agrivoltaics_Node_ZoneB_Agrivoltaic/
│   └── Agrivoltaics_Node_ZoneB_Agrivoltaic.ino # Flashed to Node 2 (Agrivoltaic Canopy, Zone B)
└── Agrivoltaics_Node_Master/
    └── Agrivoltaics_Node_Master.ino           # Universal master template with #define switch
```

---

## ⚡ Hardware Pinout Connections

| Sensor / Module | Interface | ESP32-S3 Pin | Notes |
| :--- | :--- | :--- | :--- |
| **BME280** (Temp / Humidity / Pressure) | **Hardware SPI** | | Dedicated bus (no SD contention) |
| └ BME280 CS | SPI CS | **GPIO 10** | Chip Select |
| └ BME280 MOSI / SDA | SPI MOSI | **GPIO 11** | Master Out Slave In |
| └ BME280 MISO / SDO | SPI MISO | **GPIO 13** | Master In Slave Out |
| └ BME280 SCK / SCL | SPI SCK | **GPIO 12** | Serial Clock |
| **BH1750 (Incident / Solar Rs)** | **Shared I2C** | **GPIO 8 (SDA), GPIO 9 (SCL)** | ADDR pin pulled to GND → Address `0x23` |
| **BH1750 (Reflected / Albedo Rr)**| **Shared I2C** | **GPIO 8 (SDA), GPIO 9 (SCL)** | ADDR pin pulled to VCC → Address `0x5C` |
| **DS3231 RTC** | **Shared I2C** | **GPIO 8 (SDA), GPIO 9 (SCL)** | Fixed Address `0x68` (battery backed) |
| **DS18B20** (Soil Temperature) | **1-Wire** | **GPIO 4** | Requires 4.7kΩ pull-up to 3.3V |
| **Capacitive Soil Sensor 1** | **Analog (ADC1)**| **GPIO 5** | Upper root layer (0–15 cm) |
| **Capacitive Soil Sensor 2** | **Analog (ADC1)**| **GPIO 6** | Lower root layer (15–30 cm) |
| **WS2812 RGB Status LED** | **Digital (RMT)** | **GPIO 48** | Onboard Ozobot Devkit RGB LED |

> [!NOTE]
> The MicroSD card module was **completely removed** to eliminate bus lockups and hardware SPI contention. The BME280 now has exclusive, uninterrupted access to the hardware SPI bus.

---

## 📦 Required Arduino IDE Libraries

Install the following libraries via the **Arduino IDE Library Manager** (`Ctrl+Shift+I` or `Cmd+Shift+I`):

1. **`Adafruit BME280 Library`** (by Adafruit) — for SPI atmospheric sensing
2. **`BH1750`** (by Christopher Laws) — for dual I2C lux measurement
3. **`DallasTemperature`** (by Miles Burton) — for DS18B20 1-Wire soil temperature
4. **`OneWire`** (by Paul Stoffregen) — underlying 1-Wire protocol
5. **`RTClib`** (by Adafruit) — for DS3231 real-time clock
6. **`Adafruit NeoPixel`** (by Adafruit) — for onboard WS2812 RGB diagnostic indicator
7. **`PubSubClient`** (by Nick O'Leary) — for MQTT telemetry publishing
8. **`ArduinoJson`** (by Benoit Blanchon, v6 or v7) — for fast JSON serialization

---

## 🛠️ Arduino IDE Board Configuration

- **Board**: `ESP32S3 Dev Module`
- **USB CDC On Boot**: `Enabled`
- **Flash Size**: `8MB (64Mb)`
- **Partition Scheme**: `8MB with spiffs (3MB APP/1.5MB SPIFFS)` or `Default 4MB`
- **PSRAM**: `OPI PSRAM` (or Enabled)
- **Upload Speed**: `921600`

---

## ⚙️ Configuration Parameters

Before uploading, check the top of the `.ino` file:

```cpp
// --- Network settings ---
#define WIFI_SSID           "Sri Ram"          // Your 2.4 GHz WiFi network name
#define WIFI_PASSWORD       "PASSWORD"         // Your WiFi password

// --- MQTT broker settings ---
#define MQTT_BROKER         "10.181.203.89"    // IP of your local server / broker
#define MQTT_PORT           1883
#define MQTT_USER           ""                 // Broker username (if required)
#define MQTT_PASSWORD       ""                 // Broker password (if required)
```

### Zone Differentiation

| Parameter | Node 1 (Zone A Control) | Node 2 (Zone B Agrivoltaic) |
| :--- | :--- | :--- |
| **Sketch** | `Agrivoltaics_Node_ZoneA_Control.ino` | `Agrivoltaics_Node_ZoneB_Agrivoltaic.ino` |
| **Node ID** | `NODE_A` | `NODE_B` |
| **Device ID** | `ESP32_ZONE_A` | `ESP32_ZONE_B` |
| **Zone Flag** | `"A"` (Full Sun Control) | `"B"` (PV Canopy Microclimate) |
| **MQTT Topic** | `agrivoltaic/zone/A/telemetry` | `agrivoltaic/zone/B/telemetry` |
| **Nominal Shade** | `0.000` (0.0% shade) | `0.389` (38.9% STPV shading) |

---

## 🚦 Diagnostic RGB LED Status Codes

The onboard WS2812 LED on GPIO 48 provides immediate physical feedback on node health:

| Color | Hex / RGB | State / Meaning | Action |
| :--- | :--- | :--- | :--- |
| **Cyan** | `(0, 50, 50)` | **System Booting** | Initializing buses, I2C, SPI |
| **Blue** | `(0, 0, 50)` | **Connecting to WiFi** | Awaiting IP acquisition |
| **White** | `(40, 40, 40)` | **Syncing Clock** | NTP or DS3231 RTC synchronization |
| **Green Pulse** | `(0, 50, 0)` | **Normal Operation** | Pulses on successful MQTT publish |
| **Red Blink** | `(60, 0, 0)` | **Hardware Sensor Fault** | BME280 / BH1750 / RTC failed check |
| **Purple** | `(40, 0, 40)` | **Offline Reconnecting** | WiFi or MQTT connection lost, auto-retrying |

---

## 📡 Output Telemetry Schema (Compliant with AGRO-VOLT Backend)

Telemetry is transmitted as an ISO 8601-timestamped JSON payload directly matching `backend/app/schemas/sensor.py`:

```json
{
  "device_id": "ESP32_ZONE_A",
  "node_id": "NODE_A",
  "zone": "A",
  "timestamp": "2026-10-01T12:00:00+05:30",
  "temperature": 32.45,
  "relative_humidity": 58.20,
  "pressure": 1008.35,
  "soil_moisture_1": 0.228,
  "soil_moisture_2": 0.241,
  "soil_moisture_mean": 0.235,
  "soil_moisture": 0.235,
  "soil_temperature": 27.80,
  "solar_radiation": 845.2,
  "solar_radiation_down": 194.4,
  "albedo": 0.230,
  "photosynthetically_active_radiation": 1690.4,
  "shade_fraction": 0.000,
  "battery_voltage": 4.12,
  "battery_percent": 96.5,
  "rssi": -62,
  "free_heap": 248312,
  "publish_count": 142
}
```
