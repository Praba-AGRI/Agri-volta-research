/**
 * ============================================================================
 *           AGRIVOLTAIC RESEARCH SUITE — MASTER NODE FIRMWARE
 *                v5.0 — PRODUCTION-READY & SD-FREE STREAMER
 * ============================================================================
 * Board       : 7SEMI ESP32-S3-WROOM-1U N8R8 on Ozobot Devkit
 * Environment : Configurable Master (Zone A Control or Zone B Agrivoltaic)
 * Framework   : Arduino ESP32 core v2.0.x / v3.0.x
 * Protocol    : JSON over MQTT to AGRO-VOLT Central Intelligence Dashboard
 * ============================================================================
 */

// ============================================================================
// SECTION 1 — USER CONFIGURATION & CONSTANTS
// ============================================================================

// --- SELECT ACTIVE FIELD ZONE (Uncomment ONE) ---
// #define SELECT_ZONE_A       // Zone A: Open Field Control (Full Sun)
#define SELECT_ZONE_B          // Zone B: Agrivoltaic Canopy (PV Shaded)

#if defined(SELECT_ZONE_A)
  #define NODE_ID             "NODE_A"
  #define ZONE                "A"
  #define ZONE_NAME           "Zone A (Open Field Control)"
  #define DEVICE_ID           "ESP32_ZONE_A"
  #define MQTT_TOPIC          "agrivoltaic/zone/A/telemetry"
  #define SHADE_FRACTION_NOM  0.00f
#elif defined(SELECT_ZONE_B)
  #define NODE_ID             "NODE_B"
  #define ZONE                "B"
  #define ZONE_NAME           "Zone B (Agrivoltaic Canopy)"
  #define DEVICE_ID           "ESP32_ZONE_B"
  #define MQTT_TOPIC          "agrivoltaic/zone/B/telemetry"
  #define SHADE_FRACTION_NOM  0.389f
#else
  #error "Please select either SELECT_ZONE_A or SELECT_ZONE_B."
#endif

// --- Network settings ---
#define WIFI_SSID           "Sri Ram"
#define WIFI_PASSWORD       "PASSWORD"

// --- MQTT broker settings ---
#define MQTT_BROKER         "10.181.203.89"   // Update with host PC / broker IP
#define MQTT_PORT           1883
#define MQTT_USER           ""                // Leave empty if no authentication
#define MQTT_PASSWORD       ""

// --- Clock and transmission settings ---
#define TZ_OFFSET_SEC       19800             // Indian Standard Time (IST) = UTC + 5:30
#define LOG_INTERVAL_MIN    2                 // Telemetry interval in minutes (wall-clock aligned)
#define NTP_SERVER_1        "pool.ntp.org"
#define NTP_SERVER_2        "time.nist.gov"

// --- Soil calibration settings ---
#define SOIL_CALIBRATED     1                 // 1 = Calibrated VWC, 0 = Raw ADC only
#define SOIL_CAL_A          -0.000265f        // Empirical calibration slope
#define SOIL_CAL_B          0.848f            // Empirical calibration intercept
#define VWC_MIN_BOUND       0.05f             // Minimum plausible soil VWC (m3/m3)
#define VWC_MAX_BOUND       0.55f             // Maximum plausible soil VWC (m3/m3)

// --- Solar radiation conversion settings ---
#define LUX_TO_WM2          0.0079f           // Standard photopic lux to solar irradiance (W/m2)
#define FAO56_REF_ALBEDO    0.23f             // FAO-56 Reference surface albedo constant
#define MIN_RS_FOR_ALBEDO   20.0f             // Minimum incoming radiation (W/m2) to compute albedo

// --- Sensor validation bounds ---
#define T_MIN               -40.0f
#define T_MAX               85.0f
#define RH_MIN              0.0f
#define RH_MAX              100.0f
#define P_MIN               300.0f
#define P_MAX               1100.0f
#define SOILT_MIN           -20.0f
#define SOILT_MAX           80.0f
#define LUX_MAX             120000.0f
#define ADC_MIN             50
#define ADC_MAX             4045

#define INVALID             -999.0f

// ============================================================================
// SECTION 2 — PHYSICAL PIN ASSIGNMENTS
// ============================================================================

// --- Dedicated Hardware SPI bus pins for BME280 ---
#define SPI_MOSI            11
#define SPI_MISO            13
#define SPI_SCK             12
#define BME280_CS           10

// --- Shared I2C bus pins ---
#define I2C_SDA             8
#define I2C_SCL             9

// --- Sensor analog & 1-Wire pins ---
#define DS18B20_PIN         4                 // Dallas 1-Wire Soil Temperature
#define SOIL_PIN_1          5                 // Capacitive Soil Moisture Sensor 1
#define SOIL_PIN_2          6                 // Capacitive Soil Moisture Sensor 2

// --- Onboard WS2812 status LED pin ---
#define RGB_PIN             48
#define RGB_COUNT           1

// ============================================================================
// SECTION 3 — LIBRARIES AND HEADERS
// ============================================================================

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>

#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <BH1750.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <RTClib.h>
#include <Adafruit_NeoPixel.h>

// ============================================================================
// SECTION 4 — HARDWARE INSTANCES
// ============================================================================

Adafruit_BME280     bme(BME280_CS);           // Hardware SPI BME280
BH1750              lightUp(0x23);            // Upward incident radiation (I2C addr 0x23)
BH1750              lightDown(0x5C);          // Downward reflected radiation (I2C addr 0x5C)
OneWire             oneWire(DS18B20_PIN);
DallasTemperature   ds18b20(&oneWire);
RTC_DS3231          rtc;
Adafruit_NeoPixel   led(RGB_COUNT, RGB_PIN, NEO_GRB + NEO_KHZ800);

WiFiClient          espClient;
PubSubClient        mqttClient(espClient);

// ============================================================================
// SECTION 5 — SYSTEM STATE VARIABLES
// ============================================================================

bool bmeOK   = false;
bool bh1OK   = false;
bool bh2OK   = false;
bool ds18OK  = false;
bool rtcOK   = false;
bool wifiOK  = false;

unsigned long logCount        = 0;
int           lastLoggedSlot  = -1;
unsigned long lastFallbackLog = 0;
unsigned long lastWifiRetry   = 0;
unsigned long lastMqttRetry   = 0;
unsigned long lastNtpSync     = 0;

// ============================================================================
// SECTION 6 — STATUS DISPLAY LED HELPERS
// ============================================================================

void setRGB(uint8_t r, uint8_t g, uint8_t b) {
  led.setPixelColor(0, led.Color(r, g, b));
  led.show();
}

void rgbOff()    { setRGB(0, 0, 0);    }
void rgbCyan()   { setRGB(0, 60, 60);  }      // Booting / Initialising
void rgbBlue()   { setRGB(0, 0, 80);   }      // Connecting to WiFi
void rgbWhite()  { setRGB(50, 50, 50); }      // WiFi connected, syncing NTP
void rgbGreen()  { setRGB(0, 80, 0);   }      // Normal operation / MQTT publish OK
void rgbYellow() { setRGB(80, 80, 0);  }      // Sampling sensors
void rgbPurple() { setRGB(50, 0, 50);  }      // Offline / reconnecting
void rgbRed()    { setRGB(80, 0, 0);   }      // Sensor hardware failure

// ============================================================================
// SECTION 7 — METRIC COMPUTATION & VALIDATION
// ============================================================================

inline bool inRange(float v, float lo, float hi) {
  return (!isnan(v) && v >= lo && v <= hi);
}

float validate(float v, float lo, float hi) {
  return inRange(v, lo, hi) ? v : INVALID;
}

// FAO-56 Penman-Monteith Vapor Pressure Deficit (VPD in kPa)
float calculateVPD(float tempC, float rhPct) {
  if (tempC == INVALID || rhPct == INVALID) return INVALID;
  float es  = 0.6108f * expf((17.27f * tempC) / (tempC + 237.3f));
  float ea  = es * (rhPct / 100.0f);
  float vpd = es - ea;
  return (vpd < 0.0f) ? 0.0f : vpd;
}

// Soil ADC calibration curve to Volumetric Water Content (m3/m3)
float soilADCtoVWC(int rawAdc) {
#if SOIL_CALIBRATED
  if (rawAdc < ADC_MIN || rawAdc > ADC_MAX) return INVALID;
  float vwc = SOIL_CAL_A * (float)rawAdc + SOIL_CAL_B;
  if (vwc < VWC_MIN_BOUND) vwc = VWC_MIN_BOUND;
  if (vwc > VWC_MAX_BOUND) vwc = VWC_MAX_BOUND;
  return vwc;
#else
  (void)rawAdc;
  return INVALID;
#endif
}

// ============================================================================
// SECTION 8 — NETWORK AND TELEMETRY MANAGEMENT
// ============================================================================

void syncNTP() {
  if (!wifiOK) return;
  Serial.print("[NTP] Synchronising wall-clock time");
  configTime(TZ_OFFSET_SEC, 0, NTP_SERVER_1, NTP_SERVER_2);

  struct tm ti;
  int attempts = 0;
  while (!getLocalTime(&ti) && attempts < 15) {
    delay(300);
    Serial.print(".");
    attempts++;
  }

  if (attempts < 15) {
    char buf[30];
    strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &ti);
    Serial.printf("\n[NTP] Time synchronized successfully: %s IST\n", buf);
    if (rtcOK) {
      rtc.adjust(DateTime(ti.tm_year + 1900, ti.tm_mon + 1, ti.tm_mday,
                          ti.tm_hour, ti.tm_min, ti.tm_sec));
      Serial.println("[RTC] DS3231 RTC updated with verified NTP time.");
    }
    lastNtpSync = millis();
  } else {
    Serial.println("\n[NTP] Server unreachable — retaining DS3231 clock time.");
  }
}

void connectWiFi() {
  Serial.printf("[WIFI] Connecting to SSID: %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(300);
    Serial.print(".");
    attempts++;
    if (attempts % 2 == 0) rgbOff(); else rgbBlue();
  }

  if (WiFi.status() == WL_CONNECTED) {
    wifiOK = true;
    Serial.printf("\n[WIFI] Connected! Assigned IP: %s (RSSI: %d dBm)\n",
                  WiFi.localIP().toString().c_str(), WiFi.RSSI());
    rgbWhite();
    syncNTP();
  } else {
    wifiOK = false;
    Serial.println("\n[WIFI] Connection failed. Streaming disabled; will retry in background.");
    rgbPurple();
  }
}

bool connectMQTT() {
  if (WiFi.status() != WL_CONNECTED) {
    wifiOK = false;
    return false;
  }
  wifiOK = true;

  if (mqttClient.connected()) return true;

  Serial.printf("[MQTT] Connecting to broker %s:%d ... ", MQTT_BROKER, MQTT_PORT);
  String clientId = String("ESP32_") + NODE_ID + "_" + ZONE + "_" + String((uint32_t)ESP.getEfuseMac(), HEX);

  bool connected = false;
  if (strlen(MQTT_USER) > 0) {
    connected = mqttClient.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD);
  } else {
    connected = mqttClient.connect(clientId.c_str());
  }

  if (connected) {
    Serial.println("CONNECTED.");
    return true;
  } else {
    Serial.printf("FAILED (rc=%d). Will retry.\n", mqttClient.state());
    return false;
  }
}

void maintainConnections() {
  // 1. Maintain WiFi
  if (WiFi.status() != WL_CONNECTED) {
    wifiOK = false;
    if (millis() - lastWifiRetry >= 10000UL) {
      lastWifiRetry = millis();
      Serial.println("[WIFI] Reconnecting to network...");
      WiFi.reconnect();
    }
  } else {
    wifiOK = true;

    // 2. Maintain MQTT
    if (!mqttClient.connected()) {
      if (millis() - lastMqttRetry >= 5000UL) {
        lastMqttRetry = millis();
        connectMQTT();
      }
    } else {
      mqttClient.loop();
    }

    // 3. Periodic NTP resync (every 6 hours)
    if (millis() - lastNtpSync >= 21600000UL) {
      syncNTP();
    }
  }
}

// ============================================================================
// SECTION 9 — HARDWARE BUS INITIALISATION
// ============================================================================

bool verifyBME280() {
  float t = bme.readTemperature();
  float h = bme.readHumidity();
  float p = bme.readPressure() / 100.0F;

  bool ok = inRange(t, T_MIN, T_MAX)
         && inRange(h, RH_MIN, RH_MAX)
         && inRange(p, P_MIN, P_MAX);

  Serial.printf("[BME280] Diagnostic verification: T=%.2f C, RH=%.1f %%, P=%.2f hPa -> %s\n",
                t, h, p, ok ? "PASS" : "FAIL / OUT OF RANGE");
  return ok;
}

void initAllSensors() {
  Serial.println("\n----------------------------------------");
  Serial.println(" SENSOR HARDWARE INITIALISATION");
  Serial.println("----------------------------------------");

  // Initialise shared I2C bus
  Wire.begin(I2C_SDA, I2C_SCL);

  // Initialise dedicated Hardware SPI for BME280
  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI, -1);
  pinMode(BME280_CS, OUTPUT);
  digitalWrite(BME280_CS, HIGH);
  delay(10);

  // --- BME280 over Hardware SPI ---
  bmeOK = bme.begin();
  Serial.printf("BME280   [HW SPI CS=%d] : %s\n", BME280_CS, bmeOK ? "DETECTED" : "FAILED");
  if (bmeOK) {
    bme.setSampling(Adafruit_BME280::MODE_NORMAL,
                    Adafruit_BME280::SAMPLING_X1,   // Temperature
                    Adafruit_BME280::SAMPLING_X1,   // Pressure
                    Adafruit_BME280::SAMPLING_X1,   // Humidity
                    Adafruit_BME280::FILTER_X16,
                    Adafruit_BME280::STANDBY_MS_500);
    delay(100);
    bmeOK = verifyBME280();
  }

  // --- Dual BH1750 light sensors over I2C ---
  bh1OK = lightUp.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, 0x23, &Wire);
  Serial.printf("BH1750-1 [I2C 0x23]      : %s (Upward Pyranometer Incident)\n",
                bh1OK ? "DETECTED" : "FAILED");

  bh2OK = lightDown.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, 0x5C, &Wire);
  Serial.printf("BH1750-2 [I2C 0x5C]      : %s (Downward Reflected Albedo)\n",
                bh2OK ? "DETECTED" : "FAILED");

  // --- Dallas DS18B20 soil temp over 1-Wire ---
  ds18b20.begin();
  ds18b20.setResolution(12);
  int dsCount = ds18b20.getDeviceCount();
  ds18OK = (dsCount > 0);
  Serial.printf("DS18B20  [1-Wire GPIO%d] : %s (%d device detected)\n",
                DS18B20_PIN, ds18OK ? "DETECTED" : "FAILED", dsCount);

  // --- DS3231 Precision Real-Time Clock ---
  rtcOK = rtc.begin(&Wire);
  if (rtcOK) {
    Serial.printf("DS3231   [I2C 0x68]      : DETECTED %s\n",
                  rtc.lostPower() ? "(Power lost — awaiting NTP sync)" : "(Time valid)");
  } else {
    Serial.println("DS3231   [I2C 0x68]      : FAILED");
  }

  // Configure high-resolution Analog-to-Digital Converter
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  Serial.println("ADC      [GPIO5+6]       : CONFIGURED (12-bit, 0-3.3V attenuation)");
}

// ============================================================================
// SECTION 10 — TIMESTAMP FORMATTING HELPERS
// ============================================================================

String getTimestamp() {
  if (rtcOK) {
    DateTime n = rtc.now();
    char b[25];
    snprintf(b, sizeof(b), "%04d-%02d-%02d %02d:%02d:%02d",
             n.year(), n.month(), n.day(), n.hour(), n.minute(), n.second());
    return String(b);
  }
  struct tm ti;
  if (getLocalTime(&ti)) {
    char b[25];
    strftime(b, sizeof(b), "%Y-%m-%d %H:%M:%S", &ti);
    return String(b);
  }
  return "2026-10-01 00:00:00";
}

// Strict ISO 8601 with +05:30 IST timezone for Pydantic/backend validation
String getISO8601() {
  if (rtcOK) {
    DateTime n = rtc.now();
    char b[35];
    snprintf(b, sizeof(b), "%04d-%02d-%02dT%02d:%02d:%02d+05:30",
             n.year(), n.month(), n.day(), n.hour(), n.minute(), n.second());
    return String(b);
  }
  struct tm ti;
  if (getLocalTime(&ti)) {
    char b[35];
    strftime(b, sizeof(b), "%Y-%m-%dT%H:%M:%S+05:30", &ti);
    return String(b);
  }
  return "2026-10-01T00:00:00+05:30";
}

// ============================================================================
// SECTION 11 — READ SENSORS, LOG & PUBLISH TO DASHBOARD
// ============================================================================

void readAndPublish() {
  rgbYellow();
  logCount++;

  // 1. Read BME280 Atmospheric Transducer
  float airTemp  = INVALID;
  float humidity = INVALID;
  float pressure = INVALID;
  if (bmeOK) {
    airTemp  = validate(bme.readTemperature(),       T_MIN,  T_MAX);
    humidity = validate(bme.readHumidity(),          RH_MIN, RH_MAX);
    pressure = validate(bme.readPressure() / 100.0F, P_MIN,  P_MAX);
  }
  float vpd = calculateVPD(airTemp, humidity);

  // 2. Read DS18B20 Subsurface Soil Temperature Transducer
  float soilTemp = INVALID;
  if (ds18OK) {
    ds18b20.requestTemperatures();
    float raw = ds18b20.getTempCByIndex(0);
    if (raw != -127.0f && raw != 85.0f) {
      soilTemp = validate(raw, SOILT_MIN, SOILT_MAX);
    }
  }

  // 3. Read Soil Moisture Capacitive Transducers
  int soil1 = analogRead(SOIL_PIN_1);
  int soil2 = analogRead(SOIL_PIN_2);
  bool s1valid = (soil1 >= ADC_MIN && soil1 <= ADC_MAX);
  bool s2valid = (soil2 >= ADC_MIN && soil2 <= ADC_MAX);

  float vwc1    = s1valid ? soilADCtoVWC(soil1) : INVALID;
  float vwc2    = s2valid ? soilADCtoVWC(soil2) : INVALID;
  float vwcMean = INVALID;
  if (vwc1 != INVALID && vwc2 != INVALID) {
    vwcMean = (vwc1 + vwc2) * 0.5f;
  } else if (vwc1 != INVALID) {
    vwcMean = vwc1;
  } else if (vwc2 != INVALID) {
    vwcMean = vwc2;
  }

  // 4. Read Dual BH1750 Pyranometer Ambient Light Sensors
  float luxUp   = bh1OK ? validate(lightUp.readLightLevel(),   0.0f, LUX_MAX) : INVALID;
  float luxDown = bh2OK ? validate(lightDown.readLightLevel(), 0.0f, LUX_MAX) : INVALID;

  // 5. Shortwave Solar Radiation Balance Chain
  float rsDown = (luxUp   != INVALID) ? (luxUp   * LUX_TO_WM2) : INVALID;
  float rsUp   = (luxDown != INVALID) ? (luxDown * LUX_TO_WM2) : INVALID;

  // Surface Albedo calculation
  float albedo = INVALID;
  if (rsDown != INVALID && rsUp != INVALID && rsDown > MIN_RS_FOR_ALBEDO) {
    albedo = rsUp / rsDown;
    if (albedo < 0.0f) albedo = 0.0f;
    if (albedo > 1.0f) albedo = 1.0f;
  }

  // FAO-56 Reference Net Radiation vs Measured Net Radiation
  float rnsFAO = (rsDown != INVALID) ? (1.0f - FAO56_REF_ALBEDO) * rsDown : INVALID;
  float rnsMeas = INVALID;
  if (rsDown != INVALID && rsUp != INVALID) {
    rnsMeas = rsDown - rsUp;
    if (rnsMeas < 0.0f) rnsMeas = 0.0f;
  }

  String ts     = getTimestamp();
  String isoTs  = getISO8601();
  bool   mqttUp = mqttClient.connected();

  // Print Detailed Real-Time Sensor Values to Serial Monitor
  Serial.println("\n================================================================================");
  Serial.printf(" AGRIVOLTAIC SENSOR TELEMETRY | PACKET #%lu | %s\n", logCount, ts.c_str());
  Serial.printf(" Node: %s | Zone: %s | Device: %s\n", NODE_ID, ZONE_NAME, DEVICE_ID);
  Serial.println("================================================================================");

  // [1] Atmospheric Microclimate (BME280 on Hardware SPI)
  Serial.println(" [1] ATMOSPHERIC MICROCLIMATE (BME280 Hardware SPI):");
  if (airTemp != INVALID)  Serial.printf("     • Air Temperature        : %.2f °C\n", airTemp);
  else                     Serial.println("     • Air Temperature        : [ERROR / SENSOR DISCONNECTED]");

  if (humidity != INVALID) Serial.printf("     • Relative Humidity      : %.1f %%\n", humidity);
  else                     Serial.println("     • Relative Humidity      : [ERROR / SENSOR DISCONNECTED]");

  if (pressure != INVALID) Serial.printf("     • Barometric Pressure    : %.2f hPa\n", pressure);
  else                     Serial.println("     • Barometric Pressure    : [ERROR / SENSOR DISCONNECTED]");

  if (vpd != INVALID)      Serial.printf("     • Vapor Pressure Deficit : %.3f kPa\n", vpd);
  else                     Serial.println("     • Vapor Pressure Deficit : [N/A]");

  // [2] Subsurface Soil Microclimate (DS18B20 1-Wire & Dual ADC)
  Serial.println(" [2] SUBSURFACE SOIL MICROCLIMATE (DS18B20 1-Wire & Dual ADC):");
  if (soilTemp != INVALID) Serial.printf("     • Soil Temperature       : %.2f °C\n", soilTemp);
  else                     Serial.println("     • Soil Temperature       : [ERROR / SENSOR DISCONNECTED]");

  if (s1valid) {
    if (vwc1 != INVALID)   Serial.printf("     • Soil Moisture Sensor 1 : Raw ADC = %4d | VWC = %.3f m³/m³ (%.1f %%)\n", soil1, vwc1, vwc1 * 100.0f);
    else                   Serial.printf("     • Soil Moisture Sensor 1 : Raw ADC = %4d [ADC out of calibration range]\n", soil1);
  } else {
    Serial.println("     • Soil Moisture Sensor 1 : [DISCONNECTED / OPEN-CIRCUIT]");
  }

  if (s2valid) {
    if (vwc2 != INVALID)   Serial.printf("     • Soil Moisture Sensor 2 : Raw ADC = %4d | VWC = %.3f m³/m³ (%.1f %%)\n", soil2, vwc2, vwc2 * 100.0f);
    else                   Serial.printf("     • Soil Moisture Sensor 2 : Raw ADC = %4d [ADC out of calibration range]\n", soil2);
  } else {
    Serial.println("     • Soil Moisture Sensor 2 : [DISCONNECTED / OPEN-CIRCUIT]");
  }

  if (vwcMean != INVALID) {
    Serial.printf("     • Root-Zone Mean Moisture: %.3f m³/m³ (%.1f %%) [%s]\n",
                  vwcMean, vwcMean * 100.0f, SOIL_CALIBRATED ? "Field Calibrated" : "Raw Linear Proxy");
  } else {
    Serial.println("     • Root-Zone Mean Moisture: [INVALID]");
  }

  // [3] Solar Radiation & Energy Balance (Dual BH1750 on Shared I2C)
  Serial.println(" [3] SOLAR RADIATION & ENERGY BALANCE (Dual BH1750 Shared I2C):");
  if (luxUp != INVALID)    Serial.printf("     • Incident Light (0x23)  : %8.1f lux -> Rs Incoming  : %.2f W/m²\n", luxUp, rsDown);
  else                     Serial.println("     • Incident Light (0x23)  : [ERROR / SENSOR DISCONNECTED]");

  if (luxDown != INVALID)  Serial.printf("     • Reflected Light (0x5C) : %8.1f lux -> Rs Reflected : %.2f W/m²\n", luxDown, rsUp);
  else                     Serial.println("     • Reflected Light (0x5C) : [ERROR / SENSOR DISCONNECTED]");

  if (albedo != INVALID)   Serial.printf("     • Surface Albedo (α)     : %.4f (%.1f %%)\n", albedo, albedo * 100.0f);
  else                     Serial.println("     • Surface Albedo (α)     : [Below Min Threshold / Night]");

  if (rnsFAO != INVALID)   Serial.printf("     • Net Radiation (FAO-56) : %.2f W/m²\n", rnsFAO);
  if (rnsMeas != INVALID)  Serial.printf("     • Net Radiation (Measure): %.2f W/m²\n", rnsMeas);
  Serial.printf("     • Agrivoltaic Shading    : %.1f %% (Nominal Fraction: %.3f)\n",
                SHADE_FRACTION_NOM * 100.0f, SHADE_FRACTION_NOM);

  // [4] System & Hardware Diagnostics
  Serial.println(" [4] HARDWARE & NETWORK HEALTH:");
  Serial.printf("     • Hardware Transducers   : BME280:%s | BH1750-Up:%s | BH1750-Dn:%s | DS18B20:%s | RTC:%s\n",
                bmeOK ? "OK" : "FAIL", bh1OK ? "OK" : "FAIL", bh2OK ? "OK" : "FAIL",
                ds18OK ? "OK" : "FAIL", rtcOK ? "OK" : "FAIL");
  Serial.printf("     • WiFi Link              : %s (SSID: %s | RSSI: %d dBm | IP: %s)\n",
                wifiOK ? "CONNECTED" : "OFFLINE", WIFI_SSID, WiFi.RSSI(), WiFi.localIP().toString().c_str());
  Serial.printf("     • MQTT Telemetry Link    : %s (Broker: %s:%d)\n",
                mqttUp ? "CONNECTED" : "DISCONNECTED", MQTT_BROKER, MQTT_PORT);
  Serial.printf("     • MQTT Publish Topic     : %s\n", MQTT_TOPIC);
  Serial.printf("     • Free System Heap       : %u bytes\n", ESP.getFreeHeap());

  // Publish JSON Telemetry directly to AGRO-VOLT Central Dashboard
  if (wifiOK && mqttUp) {
#if ARDUINOJSON_VERSION_MAJOR >= 7
    JsonDocument doc;
#else
    StaticJsonDocument<1024> doc;
#endif

    // Metadata & Device Identifiers
    doc["device_id"]      = DEVICE_ID;
    doc["node_id"]        = NODE_ID;
    doc["zone"]           = ZONE;
    doc["timestamp"]      = isoTs;

    // Atmospheric Microclimate
    if (airTemp  != INVALID) doc["air_temperature"]   = roundf(airTemp  * 100) / 100.0f;
    if (humidity != INVALID) doc["relative_humidity"] = roundf(humidity * 10)  / 10.0f;
    if (pressure != INVALID) doc["pressure"]          = roundf(pressure * 100) / 100.0f;
    if (vpd      != INVALID) doc["vpd"]               = roundf(vpd * 1000)     / 1000.0f;

    // Subsurface Soil Microclimate
    if (soilTemp != INVALID) doc["soil_temperature"]  = roundf(soilTemp * 100) / 100.0f;
    if (s1valid)             doc["soil_adc_1"]        = soil1;
    if (s2valid)             doc["soil_adc_2"]        = soil2;

    if (vwc1    != INVALID)  doc["soil_moisture_1"]   = roundf(vwc1    * 1000) / 1000.0f;
    if (vwc2    != INVALID)  doc["soil_moisture_2"]   = roundf(vwc2    * 1000) / 1000.0f;
    if (vwcMean != INVALID) {
      doc["soil_moisture_mean"] = roundf(vwcMean * 1000) / 1000.0f;
      doc["soil_moisture"]      = roundf(vwcMean * 1000) / 1000.0f;
    }
    doc["soil_calibrated"] = (bool)SOIL_CALIBRATED;

    // Solar & Radiation Energy Balance
    if (luxUp   != INVALID)  doc["lux_incident"]      = roundf(luxUp   * 10)   / 10.0f;
    if (luxDown != INVALID)  doc["lux_reflected"]     = roundf(luxDown * 10)   / 10.0f;
    if (albedo  != INVALID)  doc["albedo"]            = roundf(albedo * 10000) / 10000.0f;

    if (rsDown  != INVALID) {
      doc["radiation"]   = roundf(rsDown * 100) / 100.0f;
      doc["rs_incoming"] = roundf(rsDown * 100) / 100.0f;
    }
    if (rsUp    != INVALID)  doc["rs_reflected"]      = roundf(rsUp    * 100) / 100.0f;
    if (rnsFAO  != INVALID)  doc["rns_fao56"]         = roundf(rnsFAO  * 100) / 100.0f;
    if (rnsMeas != INVALID)  doc["rns_measured"]      = roundf(rnsMeas * 100) / 100.0f;

    // Agronomic canopy attributes
    doc["rainfall"]       = 0.0f;
    doc["shade_fraction"] = SHADE_FRACTION_NOM;

    String payload;
    serializeJson(doc, payload);

    // [5] Print Full JSON Telemetry Payload to Serial Monitor
    Serial.println(" [5] OUTGOING MQTT JSON TELEMETRY PAYLOAD:");
    Serial.print("     ");
    Serial.println(payload);
    Serial.println("--------------------------------------------------------------------------------");

    if (mqttClient.publish(MQTT_TOPIC, payload.c_str(), false)) {
      Serial.printf("[MQTT] SUCCESS -> Published %d bytes to topic '%s'\n",
                    payload.length(), MQTT_TOPIC);
      rgbGreen();
    } else {
      Serial.println("[MQTT] ERROR -> Publication failed. Broker queue full or buffer overrun.");
      rgbPurple();
    }
  } else {
    Serial.println("[MQTT] Telemetry skipped — device currently offline.");
    rgbPurple();
  }
  Serial.println(" [TIP] Send 'r' or Enter in Serial Monitor to trigger immediate reading.");
  Serial.println("================================================================================\n");
}

// ============================================================================
// SECTION 12 — FIRMWARE SETUP LIFE CYCLE
// ============================================================================

void setup() {
  Serial.begin(115200);
  delay(1500);

  led.begin();
  led.setBrightness(50);
  rgbCyan();

  Serial.println("\n\n========================================================");
  Serial.printf(" AGRIVOLTAIC RESEARCH SUITE — %s\n", ZONE_NAME);
  Serial.printf(" DEVICE ID: %s | NODE: %s | FIRMWARE v5.0\n", DEVICE_ID, NODE_ID);
  Serial.println("========================================================");

  // Initialize all hardware transducers
  initAllSensors();

  // Connect to wireless network
  connectWiFi();

  // Configure MQTT client settings
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setBufferSize(1024);            // Expanded buffer for full JSON telemetry
  mqttClient.setKeepAlive(60);
  mqttClient.setSocketTimeout(15);

  if (wifiOK) connectMQTT();

  Serial.println("\n========================================================");
  Serial.println(" POST-BOOT SENSOR HEALTH REPORT");
  Serial.println("========================================================");
  Serial.printf(" BME280 Atmospheric (T/RH/P)  : %s\n", bmeOK  ? "OK" : "*** FAILED ***");
  Serial.printf(" BH1750-1 Incident Light (Up)  : %s\n", bh1OK  ? "OK" : "*** FAILED ***");
  Serial.printf(" BH1750-2 Reflected Light (Dn) : %s\n", bh2OK  ? "OK" : "*** FAILED ***");
  Serial.printf(" DS18B20 Soil Temperature      : %s\n", ds18OK ? "OK" : "*** FAILED ***");
  Serial.printf(" DS3231 High-Precision RTC     : %s\n", rtcOK  ? "OK" : "*** FAILED ***");
  Serial.printf(" WiFi Network Connection       : %s\n", wifiOK ? "CONNECTED" : "OFFLINE");
  Serial.printf(" MQTT Telemetry Broker Link    : %s\n", mqttClient.connected() ? "CONNECTED" : "OFFLINE");
  Serial.printf(" MicroSD Card Module           : REMOVED (Direct Cloud/Dashboard Streaming)\n");
  Serial.printf(" Soil Calibration Mode         : %s\n", SOIL_CALIBRATED ? "ENABLED (Slope/Intercept Active)" : "DISABLED (Raw ADC)");
  Serial.println("========================================================");

  bool criticalSensorsOK = bmeOK && bh1OK && bh2OK && ds18OK;
  if (criticalSensorsOK) {
    rgbGreen();
    Serial.println("-> All critical environmental transducers verified operational.");
  } else {
    rgbRed();
    Serial.println("-> WARNING: Transducer check failure detected. Inspect wiring.");
  }

  delay(2000);

  // Transmit initial telemetry frame immediately upon boot
  readAndPublish();
  lastFallbackLog = millis();

  Serial.printf("\n[SCHEDULER] Periodic telemetry active on %d-minute wall-clock boundaries.\n",
                LOG_INTERVAL_MIN);
  Serial.println("[SERIAL MONITOR] Press 'r' + Enter at any time to trigger an immediate sensor reading!\n");
}

// ============================================================================
// SECTION 13 — MAIN EXECUTION LOOP
// ============================================================================

void loop() {
  // Maintain background network and protocol health
  maintainConnections();

  // Serial Monitor Interactive Command Listener (Press 'r' or Enter for on-demand readout)
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    while (Serial.available()) Serial.read(); // flush trailing CR/LF
    if (cmd == 'r' || cmd == 'R' || cmd == '\n' || cmd == '\r' || cmd == ' ') {
      Serial.println("\n>>> [MANUAL TRIGGER] User requested immediate sensor reading via Serial Monitor <<<");
      readAndPublish();
      lastFallbackLog = millis();
    } else if (cmd == '?' || cmd == 'h' || cmd == 'H') {
      Serial.println("\n==================== SERIAL COMMAND MENU ====================");
      Serial.println(" 'r' or Enter : Trigger immediate reading of all sensors & publish");
      Serial.println(" 'w'          : Print detailed WiFi connection info");
      Serial.println(" 'm'          : Check MQTT broker status");
      Serial.println(" '?'          : Show this menu");
      Serial.println("=============================================================\n");
    } else if (cmd == 'w' || cmd == 'W') {
      Serial.printf("[WIFI] Status: %s | SSID: %s | IP: %s | RSSI: %d dBm | MAC: %s\n",
                    WiFi.isConnected() ? "CONNECTED" : "DISCONNECTED",
                    WiFi.SSID().c_str(), WiFi.localIP().toString().c_str(),
                    WiFi.RSSI(), WiFi.macAddress().c_str());
    } else if (cmd == 'm' || cmd == 'M') {
      Serial.printf("[MQTT] Status: %s | Broker: %s:%d | Topic: %s\n",
                    mqttClient.connected() ? "CONNECTED" : "DISCONNECTED",
                    MQTT_BROKER, MQTT_PORT, MQTT_TOPIC);
    }
  }

  // Check scheduled wall-clock boundary using precision DS3231 RTC
  if (rtcOK) {
    DateTime now = rtc.now();
    int slot = (now.hour() * 60 + now.minute()) / LOG_INTERVAL_MIN;
    if ((now.minute() % LOG_INTERVAL_MIN == 0) && slot != lastLoggedSlot) {
      lastLoggedSlot = slot;
      readAndPublish();
      lastFallbackLog = millis();
    }
  } else {
    // Fail-safe millis timer if RTC battery is unseated or offline
    if (millis() - lastFallbackLog >= (unsigned long)LOG_INTERVAL_MIN * 60000UL) {
      lastFallbackLog = millis();
      readAndPublish();
    }
  }

  // Periodic heartbeat LED feedback
  static unsigned long lastHeartbeat = 0;
  if (millis() - lastHeartbeat >= 3000UL) {
    lastHeartbeat = millis();
    rgbOff();
    delay(40);
    if (!bmeOK || !bh1OK || !bh2OK || !ds18OK) {
      rgbRed();                               // Sensor fault warning
    } else if (wifiOK && mqttClient.connected()) {
      rgbGreen();                             // 100% Healthy & Streaming
    } else {
      rgbPurple();                            // Operating offline
    }
  }

  delay(20);
}
