# Dual-Zone Agrivoltaic Field Dataset — field_2026_v1

## Description
This dataset contains real field sensor telemetry collected from a dual-zone agrivoltaic experimental deployment consisting of:
- **Zone A**: Open-field control (Full Sun exposure)
- **Zone B**: Agrivoltaic PV-shaded canopy (38.9% beam & diffuse solar radiation reduction)

The experimental campaign was conducted to evaluate real-world microclimate divergence, canopy transpirational cooling, and soil moisture retention under photovoltaic panel arrays for Cowpea (Vigna unguiculata).

## Campaign & Data Collection
- **Location**: Research Farm, Block B (11.0168 N, 76.9558 E)
- **Target Crop**: Cowpea (Vigna unguiculata)
- **Native Sampling Interval**: 5 minutes (ESP32-S3 SD-card telemetry)
- **Analytical Resampling Resolution**: 5 minutes (left-closed mean binning)
- **Field Validation Campaign Window**: 22 July 2026 to 22 August 2026 (32 Days, 18,432 5-min analytical observations)
- **Held-Out Test Window**: Days 17 to 31 (08 August 2026 to 22 August 2026)

## Sensor Transducers & Hardware Setup
- **ESP32-S3 Microcontroller**: Dual-core node with local SD-card logging and RTC synchronization.
- **BME280**: Air temperature (degC), relative humidity (%), barometric pressure (hPa).
- **BH1750 (Dual Transducer)**: Upward incident illuminance (lux) and downward reflected canopy illuminance (lux).
- **DS18B20**: Soil temperature (degC) at 10 cm root-zone depth.
- **Capacitive Soil Moisture Probes**: 2-channel analog soil volumetric water content (m3/m3).
- **DS3231 RTC**: Real-time clock hardware timestamping.

## Data Processing Pipeline
Raw SD-card telemetry is preserved 100% without modification. Quality-control processing includes:
1. Timestamp sanity validation & chronological ordering.
2. Duplicate timestamp identification and resolution.
3. Sensor status flag filtering (bme_ok == 1, bh1_ok == 1, ds18_ok == 1, rtc_ok == 1).
4. Operating range bounds checking (10 degC <= Tair <= 45 degC, 10% <= RH <= 100%, 0.05 <= Soil VWC <= 0.45 m3/m3).
5. Deterministic 5-minute left-closed resampling into Parquet research datasets.

## Zone Definitions
- **Zone A**: Open-field control plot receiving unshaded ambient solar irradiance.
- **Zone B**: Treatment plot located beneath fixed-tilt solar photovoltaic canopy array.

## Important Measurement Limitation
The BH1750 sensor measures illuminance (lux) rather than broadband solar irradiance (Rs, W/m2). Irradiance values derived via Rs = lux * 0.0079 W/m2 represent empirical estimations calibrated for daylight spectral distributions and should not be interpreted as certified pyranometer measurements.

## Dataset Structure
field_2026_v1/
├── README.md
├── LICENSE.txt
├── requirements.txt
├── metadata/
│   ├── campaign_metadata.json
│   ├── sensor_configuration.csv
│   └── data_dictionary.csv
├── raw_5min/
│   ├── zone_A/      (32 daily native CSV telemetry files: 2026-07-22 to 2026-08-22)
│   └── zone_B/      (32 daily native CSV telemetry files: 2026-07-22 to 2026-08-22)
├── analytical_5min/
│   ├── field_zone_A_5min.parquet
│   └── field_zone_B_5min.parquet
├── scripts/
│   ├── audit_field_csv.py
│   ├── qc_field_data.py
│   └── build_field_5min.py
└── manifests/
    └── SHA256SUMS.csv

## Relationship to Manuscript
This dataset provides the empirical field evidence supporting the RUN 4 real-field validation and simulation-to-field transfer analysis reported in:
Dual-Zone Agrivoltaic Microclimate Telemetry, FAO-56 Evapotranspiration, and Machine Learning Irrigation Forecasting for Cowpea (Vigna unguiculata).

## Dataset Versioning Policy
- **Dataset Version**: field_2026_v1 (FROZEN / LOCKED)
- This version is permanently frozen. Any future campaign expansions (e.g. September telemetry) will be released as field_2026_v2 under Zenodo versioning.

## License
Creative Commons Attribution 4.0 International (CC BY 4.0).
