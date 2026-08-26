/**
 * ============================================================================
 *               AGRIVOLTAIC RESEARCH — NODE 1 MASTER FIRMWARE
 *                v4.1 — CLEANED, TIME-ALIGNED & CALIBRATED
 * ============================================================================
 * Board  : 7SEMI ESP32-S3-WROOM-1U N8R8 on Ozobot Devkit
 * Project: Explainable AI Irrigation Decision Support System
 *          Under Tropical Agrivoltaic Conditions
 * ============================================================================
 */

// ============================================================================
// SECTION 1 — USER CONFIGURATION & CONSTANTS
// ============================================================================

#define NODE_ID             "NODE1"
#define ZONE                "B"               // "A" = Open Field | "B" = Agrivoltaic

// --- Network settings ---
#define WIFI_SSID           "Sri Ram"
#define WIFI_PASSWORD       "PASSWORD"

// --- MQTT broker settings ---
#define MQTT_BROKER         "10.181.203.89"
#define MQTT_PORT           1883
#define MQTT_USER           ""
#define MQTT_PASSWORD       ""
#define MQTT_TOPIC          "agrivoltaic/zone/" ZONE "/telemetry"

// --- Clock and storage settings ---
#define TZ_OFFSET_SEC       19800             // IST = UTC + 5:30
#define LOG_INTERVAL_MIN    2                 // Log interval in minutes
#define CSV_FILENAME        "/node1_data.csv"

// --- Soil calibration settings ---
#define SOIL_CALIBRATED     0                 // 1 = Calibrated, 0 = Raw ADC only
#define SOIL_CAL_A          -0.000265f        // Calibration slope
#define SOIL_CAL_B          0.848f            // Calibration intercept

// --- Solar radiation conversion settings ---
#define LUX_TO_WM2          0.0079f           // Photopic approximation factor
#define FAO56_REF_ALBEDO    0.23f             // FAO-56 Reference surface albedo constant
#define MIN_RS_FOR_ALBEDO   20.0f             // Minimum incoming radiation to compute albedo

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

// --- Hardware SPI bus pins ---
#define SPI_MOSI            11
#define SPI_MISO            13
#define SPI_SCK             12
#define BME280_CS           10
#define SD_CS               14

// --- Shared I2C bus pins ---
#define I2C_SDA             8
#define I2C_SCL             9

// --- Sensor pins ---
#define DS18B20_PIN         4
#define SOIL_PIN_1          5
#define SOIL_PIN_2          6

// --- Onboard status LED pin ---
#define RGB_PIN             48
#define RGB_COUNT           1

// ============================================================================
// SECTION 3 — LIBRARIES AND HEADERS
// ============================================================================

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
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
BH1750              lightUp(0x23);            // Incident light sensor (I2C 0x23)
BH1750              lightDown(0x5C);          // Reflected light sensor (I2C 0x5C)
OneWire             oneWire(DS18B20_PIN);
DallasTemperature   ds18b20(&oneWire);
RTC_DS3231          rtc;
Adafruit_NeoPixel   led(RGB_COUNT, RGB_PIN, NEO_GRB + NEO_KHZ800);

WiFiClient          espClient;
PubSubClient        mqttClient(espClient);

// ============================================================================
// SECTION 5 — SYSTEM STATE VARIABLES
// ============================================================================

bool bmeOK = false, bh1OK = false, bh2OK = false;
bool ds18OK = false, rtcOK = false, sdOK = false;
bool wifiOK = false;

unsigned long logCount = 0;
int lastLoggedSlot = -1;
unsigned long lastFallbackLog = 0;

// ============================================================================
// SECTION 6 — STATUS DISPLAY LED HELPERS
// ============================================================================

void setRGB(uint8_t r, uint8_t g, uint8_t b) {
  led.setPixelColor(0, led.Color(r, g, b));
  led.show();
}

void rgbOff()    { setRGB(0, 0, 0);    }
void rgbCyan()   { setRGB(0, 60, 60);  }
void rgbBlue()   { setRGB(0, 0, 80);   }
void rgbWhite()  { setRGB(50, 50, 50); }
void rgbGreen()  { setRGB(0, 80, 0);   }
void rgbYellow() { setRGB(80, 80, 0);  }
void rgbPurple() { setRGB(50, 0, 50);  }
void rgbRed()    { setRGB(80, 0, 0);   }

// ============================================================================
// SECTION 7 — METRIC COMPUTATION & VALIDATION
// ============================================================================

inline bool inRange(float v, float lo, float hi) {
  return (!isnan(v) && v >= lo && v <= hi);
}

float validate(float v, float lo, float hi) {
  return inRange(v, lo, hi) ? v : INVALID;
}

float calculateVPD(float tempC, float rhPct) {
  if (tempC == INVALID || rhPct == INVALID) return INVALID;
  float es  = 0.6108f * expf((17.27f * tempC) / (tempC + 237.3f));
  float ea  = es * (rhPct / 100.0f);
  float vpd = es - ea;
  return (vpd < 0.0f) ? 0.0f : vpd;
}

float soilADCtoVWC(int rawAdc) {
#if SOIL_CALIBRATED
  if (rawAdc < ADC_MIN || rawAdc > ADC_MAX) return INVALID;
  float vwc = SOIL_CAL_A * (float)rawAdc + SOIL_CAL_B;
  if (vwc < 0.0f)  vwc = 0.0f;
  if (vwc > 0.60f) vwc = 0.60f;
  return vwc;
#else
  (void)rawAdc;
  return INVALID;
#endif
}

// ============================================================================
// SECTION 8 — NETWORK AND TELEMETRY MANAGEMENT
// ============================================================================

void connectWiFi() {
  Serial.printf("WiFi connecting to: %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
    if (attempts % 2 == 0) rgbOff(); else rgbBlue();
  }

  if (WiFi.status() != WL_CONNECTED) {
    wifiOK = false;
    Serial.println("\nWiFi FAILED — logging locally with DS3231.");
    rgbPurple();
    delay(1500);
    return;
  }

  wifiOK = true;
  Serial.printf("\nWiFi OK — IP: %s\n", WiFi.localIP().toString().c_str());
  rgbWhite();

  configTime(TZ_OFFSET_SEC, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("NTP syncing");

  struct tm ti;
  int n = 0;
  while (!getLocalTime(&ti) && n < 20) { delay(500); Serial.print("."); n++; }

  if (n < 20) {
    char b[25];
    strftime(b, sizeof(b), "%Y-%m-%d %H:%M:%S", &ti);
    Serial.printf("\nNTP OK — %s\n", b);
    if (rtcOK) {
      rtc.adjust(DateTime(ti.tm_year + 1900, ti.tm_mon + 1, ti.tm_mday,
                          ti.tm_hour, ti.tm_min, ti.tm_sec));
      Serial.println("DS3231 synced to NTP local time.");
    }
  } else {
    Serial.println("\nNTP FAILED — using DS3231 time.");
  }
}

void connectMQTT() {
  if (!wifiOK) return;
  int attempts = 0;
  while (!mqttClient.connected() && attempts < 3) {
    Serial.printf("MQTT connecting to %s:%d ... ", MQTT_BROKER, MQTT_PORT);
    String cid = String("ESP32_") + NODE_ID + "_" + ZONE;
    bool ok = (strlen(MQTT_USER) > 0)
      ? mqttClient.connect(cid.c_str(), WIFI_SSID, WIFI_PASSWORD)
      : mqttClient.connect(cid.c_str());
    if (ok) { Serial.println("connected."); return; }
    Serial.printf("failed (state %d). Retry in 2s.\n", mqttClient.state());
    delay(2000);
    attempts++;
  }
}

void checkConnections() {
  if (WiFi.status() != WL_CONNECTED) {
    wifiOK = false;
    Serial.println("WiFi lost — reconnecting.");
    WiFi.reconnect();
    int n = 0;
    while (WiFi.status() != WL_CONNECTED && n < 10) { delay(500); n++; }
    wifiOK = (WiFi.status() == WL_CONNECTED);
    if (wifiOK) { Serial.println("WiFi reconnected."); connectMQTT(); }
    else        { Serial.println("Offline — SD logging continues."); }
  } else if (!mqttClient.connected()) {
    connectMQTT();
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

  Serial.printf("BME280 verify read: T=%.2fC RH=%.1f%% P=%.2fhPa -> %s\n",
                t, h, p, ok ? "PLAUSIBLE" : "OUT OF RANGE");
  return ok;
}

void initAllSensors() {
  Serial.println("\n--- Sensor Initialisation ---");

  Wire.begin(I2C_SDA, I2C_SCL);

  // [FIX 2] Shared Hardware SPI bus setup
  SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI, -1);

  // Set CS pins HIGH to release the bus
  pinMode(BME280_CS, OUTPUT); digitalWrite(BME280_CS, HIGH);
  pinMode(SD_CS,     OUTPUT); digitalWrite(SD_CS,     HIGH);
  delay(10);

  // --- BME280 over Hardware SPI ---
  bmeOK = bme.begin();
  Serial.printf("BME280  [HW SPI CS=10]: %s\n", bmeOK ? "detected" : "FAILED");
  if (bmeOK) {
    bme.setSampling(Adafruit_BME280::MODE_NORMAL,
                    Adafruit_BME280::SAMPLING_X1,   // Temperature
                    Adafruit_BME280::SAMPLING_X1,   // Pressure
                    Adafruit_BME280::SAMPLING_X1,   // Humidity
                    Adafruit_BME280::FILTER_X16,
                    Adafruit_BME280::STANDBY_MS_500);
    delay(200);
  }

  // --- Dual BH1750 light sensors ---
  bh1OK = lightUp.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, 0x23, &Wire);
  Serial.printf("BH1750-1[I2C 0x23]:     %s (upward, incident)\n",
                bh1OK ? "OK" : "FAILED");
  bh2OK = lightDown.begin(BH1750::CONTINUOUS_HIGH_RES_MODE, 0x5C, &Wire);
  Serial.printf("BH1750-2[I2C 0x5C]:     %s (downward, reflected)\n",
                bh2OK ? "OK" : "FAILED");

  // --- OneWire DS18B20 soil temp ---
  ds18b20.begin();
  ds18b20.setResolution(12);
  int dsCount = ds18b20.getDeviceCount();
  ds18OK = (dsCount > 0);
  Serial.printf("DS18B20 [1-Wire GPIO4]: %s (%d device%s)\n",
                ds18OK ? "OK" : "FAILED", dsCount, dsCount == 1 ? "" : "s");

  // --- DS3231 Real-Time Clock ---
  rtcOK = rtc.begin(&Wire);
  if (rtcOK) {
    Serial.printf("DS3231  [I2C 0x68]:     OK %s\n",
      rtc.lostPower() ? "(lost power — will sync)" : "(time retained)");
  } else {
    Serial.println("DS3231  [I2C 0x68]:     FAILED");
  }

  // --- MicroSD card setup ---
  sdOK = SD.begin(SD_CS, SPI);
  if (sdOK) {
    Serial.printf("MicroSD [HW SPI CS=14]: OK (%llu MB)\n",
                  SD.cardSize() / (1024ULL * 1024ULL));
  } else {
    Serial.println("MicroSD [HW SPI CS=14]: FAILED");
  }

  // [FIX 3] Re-verify BME280 to confirm it didn't lock up during SD init
  if (bmeOK) {
    Serial.println("Re-verifying BME280 after SD bus initialisation...");
    bmeOK = verifyBME280();
  }

  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  Serial.println("ADC     [GPIO5+6]:      OK (12-bit, 0-3.3V)");
}

// ============================================================================
// SECTION 10 — FILE DATA RECORDING HELPERS
// ============================================================================

void writeCSVHeader() {
  if (!sdOK) return;
  if (SD.exists(CSV_FILENAME)) {
    Serial.println("CSV exists — appending.");
    return;
  }
  File f = SD.open(CSV_FILENAME, FILE_WRITE);
  if (!f) { Serial.println("ERROR: cannot create CSV."); return; }

  f.println(
    "timestamp,node_id,zone,"
    "air_temp_c,humidity_pct,pressure_hpa,vpd_kpa,"
    "soil_temp_c,"
    "soil_adc_1,soil_adc_2,soil_vwc_1,soil_vwc_2,soil_vwc_mean,"
    "light_up_lux,light_down_lux,albedo,"
    "rs_down_wm2,rs_up_wm2,rns_fao56_wm2,rns_measured_wm2,"
    "bme_ok,bh1_ok,bh2_ok,ds18_ok,rtc_ok,sd_ok,wifi_ok,mqtt_ok"
  );
  f.close();
  Serial.println("CSV header written.");
}

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
  return "0000-00-00 00:00:00";
}

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
  return "1970-01-01T00:00:00+05:30";
}

// ============================================================================
// SECTION 11 — READ, LOG AND PUBLISH METRICS
// ============================================================================

void readAndLog() {
  rgbYellow();
  logCount++;

  // --- Read BME280 ---
  float airTemp = INVALID, humidity = INVALID, pressure = INVALID;
  if (bmeOK) {
    airTemp  = validate(bme.readTemperature(),        T_MIN,  T_MAX);
    humidity = validate(bme.readHumidity(),           RH_MIN, RH_MAX);
    pressure = validate(bme.readPressure() / 100.0F,  P_MIN,  P_MAX);
  }
  float vpd = calculateVPD(airTemp, humidity);

  // --- Read DS18B20 ---
  float soilTemp = INVALID;
  if (ds18OK) {
    ds18b20.requestTemperatures();
    float raw = ds18b20.getTempCByIndex(0);
    if (raw != -127.0f && raw != 85.0f) {
      soilTemp = validate(raw, SOILT_MIN, SOILT_MAX);
    }
  }

  // --- Read Soil Moisture ADCs ---
  int soil1 = analogRead(SOIL_PIN_1);
  int soil2 = analogRead(SOIL_PIN_2);
  bool s1valid = (soil1 >= ADC_MIN && soil1 <= ADC_MAX);
  bool s2valid = (soil2 >= ADC_MIN && soil2 <= ADC_MAX);

  float vwc1 = s1valid ? soilADCtoVWC(soil1) : INVALID;
  float vwc2 = s2valid ? soilADCtoVWC(soil2) : INVALID;
  float vwcMean = INVALID;
  if (vwc1 != INVALID && vwc2 != INVALID) vwcMean = (vwc1 + vwc2) * 0.5f;

  // --- Read BH1750 Light Sensors ---
  float luxUp   = bh1OK ? validate(lightUp.readLightLevel(),   0.0f, LUX_MAX) : INVALID;
  float luxDown = bh2OK ? validate(lightDown.readLightLevel(), 0.0f, LUX_MAX) : INVALID;

  // --- Calculate Shortwave Solar Radiation ---
  float rsDown = (luxUp   != INVALID) ? (luxUp   * LUX_TO_WM2) : INVALID;
  float rsUp   = (luxDown != INVALID) ? (luxDown * LUX_TO_WM2) : INVALID;

  float albedo = INVALID;
  if (rsDown != INVALID && rsUp != INVALID && rsDown > MIN_RS_FOR_ALBEDO) {
    albedo = rsUp / rsDown;
    if (albedo < 0.0f) albedo = 0.0f;
    if (albedo > 1.0f) albedo = 1.0f;
  }

  float rnsFAO = (rsDown != INVALID) ? (1.0f - FAO56_REF_ALBEDO) * rsDown : INVALID;
  float rnsMeas = INVALID;
  if (rsDown != INVALID && rsUp != INVALID) {
    rnsMeas = rsDown - rsUp;
    if (rnsMeas < 0.0f) rnsMeas = 0.0f;
  }

  String ts    = getTimestamp();
  String isoTs = getISO8601();
  bool   mqttUp = mqttClient.connected();

  // --- Print to Serial ---
  Serial.println("\n========================================");
  Serial.printf("[%s] Log #%lu | %s | Zone %s\n", ts.c_str(), logCount, NODE_ID, ZONE);
  Serial.println("----------------------------------------");
  Serial.printf("Air   : T=%.2fC  RH=%.1f%%  P=%.2fhPa  VPD=%.3fkPa\n", airTemp, humidity, pressure, vpd);
  Serial.printf("Soil  : T=%.2fC  ADC1=%d  ADC2=%d  VWC=%s\n", soilTemp, soil1, soil2, (vwcMean == INVALID) ? "uncalibrated" : String(vwcMean, 3).c_str());
  Serial.printf("Light : Up=%.1flux  Down=%.1flux  Albedo=%.4f\n", luxUp, luxDown, albedo);
  Serial.printf("Rad   : Rs_dn=%.2f  Rs_up=%.2f  Rns_fao=%.2f  Rns_meas=%.2f W/m2\n", rsDown, rsUp, rnsFAO, rnsMeas);
  Serial.printf("Health: BME=%d BH1=%d BH2=%d DS18=%d RTC=%d SD=%d WiFi=%d MQTT=%d\n", bmeOK, bh1OK, bh2OK, ds18OK, rtcOK, sdOK, wifiOK, mqttUp);

  // --- Write to SD Card ---
  if (sdOK) {
    File f = SD.open(CSV_FILENAME, FILE_APPEND);
    if (f) {
      f.printf("%s,%s,%s,", ts.c_str(), NODE_ID, ZONE);
      f.printf("%.2f,%.2f,%.2f,%.3f,", airTemp, humidity, pressure, vpd);
      f.printf("%.2f,", soilTemp);
      f.printf("%d,%d,%.4f,%.4f,%.4f,", soil1, soil2, vwc1, vwc2, vwcMean);
      f.printf("%.2f,%.2f,%.4f,", luxUp, luxDown, albedo);
      f.printf("%.2f,%.2f,%.2f,%.2f,", rsDown, rsUp, rnsFAO, rnsMeas);
      f.printf("%d,%d,%d,%d,%d,%d,%d,%d\n", bmeOK?1:0, bh1OK?1:0, bh2OK?1:0, ds18OK?1:0, rtcOK?1:0, sdOK?1:0, wifiOK?1:0, mqttUp?1:0);
      f.close();
      Serial.println("SD write: OK");
    } else {
      Serial.println("SD write: FAILED");
      sdOK = SD.begin(SD_CS, SPI);
    }
  } else {
    sdOK = SD.begin(SD_CS, SPI);
    if (sdOK) { Serial.println("SD recovered."); writeCSVHeader(); }
  }

  // --- Publish to MQTT ---
  if (wifiOK && mqttUp) {
    JsonDocument doc;
    doc["device_id"] = "ESP32_ZONE_" ZONE;
    doc["node_id"]   = NODE_ID;
    doc["zone"]      = ZONE;
    doc["timestamp"] = isoTs;

    if (airTemp  != INVALID) doc["air_temperature"]   = roundf(airTemp  * 100) / 100.0f;
    if (humidity != INVALID) doc["relative_humidity"] = roundf(humidity * 10)  / 10.0f;
    if (pressure != INVALID) doc["pressure"]          = roundf(pressure * 100) / 100.0f;
    if (vpd      != INVALID) doc["vpd"]               = roundf(vpd * 1000) / 1000.0f;
    if (soilTemp != INVALID) doc["soil_temperature"]  = roundf(soilTemp * 100) / 100.0f;

    if (s1valid) doc["soil_adc_1"] = soil1;
    if (s2valid) doc["soil_adc_2"] = soil2;

    if (vwc1    != INVALID) doc["soil_moisture_1"]    = roundf(vwc1    * 1000) / 1000.0f;
    if (vwc2    != INVALID) doc["soil_moisture_2"]    = roundf(vwc2    * 1000) / 1000.0f;
    if (vwcMean != INVALID) doc["soil_moisture_mean"] = roundf(vwcMean * 1000) / 1000.0f;
    doc["soil_calibrated"] = (bool)SOIL_CALIBRATED;

    if (luxUp   != INVALID) doc["lux_incident"]  = roundf(luxUp   * 10) / 10.0f;
    if (luxDown != INVALID) doc["lux_reflected"] = roundf(luxDown * 10) / 10.0f;
    if (albedo  != INVALID) doc["albedo"]        = roundf(albedo * 10000) / 10000.0f;

    if (rsDown  != INVALID) {
      doc["radiation"]   = roundf(rsDown * 100) / 100.0f;
      doc["rs_incoming"] = roundf(rsDown * 100) / 100.0f;
    }
    if (rsUp    != INVALID) doc["rs_reflected"]   = roundf(rsUp    * 100) / 100.0f;
    if (rnsFAO  != INVALID) doc["rns_fao56"]      = roundf(rnsFAO  * 100) / 100.0f;
    if (rnsMeas != INVALID) doc["rns_measured"]   = roundf(rnsMeas * 100) / 100.0f;

    String payload;
    serializeJson(doc, payload);

    if (mqttClient.publish(MQTT_TOPIC, payload.c_str())) {
      Serial.printf("MQTT publish: OK (%d bytes)\n", payload.length());
    } else {
      Serial.println("MQTT publish: FAILED");
    }
  }

  checkConnections();
  rgbGreen();
}

// ============================================================================
// SECTION 12 — FIRMWARE SETUP LIFE CYCLE
// ============================================================================

void setup() {
  Serial.begin(115200);
  delay(2000);

  led.begin();
  led.setBrightness(50);
  rgbCyan();

  Serial.println("========================================");
  Serial.printf(" AGRIVOLTAIC %s — ZONE %s  (firmware v4.1)\n", NODE_ID, ZONE);
  Serial.println("========================================");

  initAllSensors();
  connectWiFi();

  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setBufferSize(768);
  if (wifiOK) connectMQTT();

  writeCSVHeader();

  Serial.println("\n========================================");
  Serial.println(" BOOT STATUS");
  Serial.println("========================================");
  Serial.printf(" BME280  (T/RH/P)   : %s\n", bmeOK  ? "OK" : "*** FAILED ***");
  Serial.printf(" BH1750-1 (upward)  : %s\n", bh1OK  ? "OK" : "*** FAILED ***");
  Serial.printf(" BH1750-2 (downward): %s\n", bh2OK  ? "OK" : "*** FAILED ***");
  Serial.printf(" DS18B20 (soil T)   : %s\n", ds18OK ? "OK" : "*** FAILED ***");
  Serial.printf(" DS3231  (RTC)      : %s\n", rtcOK  ? "OK" : "*** FAILED ***");
  Serial.printf(" MicroSD (logging)  : %s\n", sdOK   ? "OK" : "*** FAILED ***");
  Serial.printf(" WiFi               : %s\n", wifiOK ? "OK" : "OFFLINE");
  Serial.printf(" MQTT               : %s\n", mqttClient.connected() ? "OK" : "OFFLINE");
  Serial.printf(" Soil calibration   : %s\n", SOIL_CALIBRATED ? "APPLIED" : "NOT APPLIED");
  Serial.println("========================================");

  bool criticalOK = bmeOK && bh1OK && bh2OK && ds18OK && sdOK;
  if (criticalOK) { rgbGreen(); Serial.println(" All critical sensors OK."); }
  else            { rgbRed();   Serial.println(" CRITICAL FAILURE — check wiring."); }

  delay(3000);
  readAndLog();
  lastFallbackLog = millis();

  Serial.printf("\nLogging on wall-clock %d-minute boundaries.\n", LOG_INTERVAL_MIN);
}

// ============================================================================
// SECTION 13 — MAIN EXECUTION LOOP
// ============================================================================

void loop() {
  if (wifiOK) mqttClient.loop();

  // Log on exact RTC wall-clock boundaries (aligned to interval)
  if (rtcOK) {
    DateTime now = rtc.now();
    int slot = (now.hour() * 60 + now.minute()) / LOG_INTERVAL_MIN;
    if ((now.minute() % LOG_INTERVAL_MIN == 0) && slot != lastLoggedSlot) {
      lastLoggedSlot = slot;
      readAndLog();
      lastFallbackLog = millis();
    }
  } else {
    // Fall back to simple millis interval if RTC is offline
    if (millis() - lastFallbackLog >= (unsigned long)LOG_INTERVAL_MIN * 60000UL) {
      lastFallbackLog = millis();
      readAndLog();
    }
  }

  // Periodic visual heartbeat status
  static unsigned long lastBeat = 0;
  if (millis() - lastBeat >= 3000) {
    lastBeat = millis();
    rgbOff();
    delay(60);
    if (!bmeOK || !sdOK)                        rgbRed();
    else if (wifiOK && mqttClient.connected())  rgbGreen();
    else                                        rgbPurple();
  }

  delay(50);
}
