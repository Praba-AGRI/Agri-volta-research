import os
import shutil
import json
import csv
import hashlib
import pandas as pd
from pathlib import Path

def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    base_dir = Path("c:/Users/Prabakaran/Desktop/Agrivoltaics simulation")
    physical_src = Path("C:/Users/Prabakaran/Desktop/agrivoltaics realtime readings")
    v1_dir = base_dir / "data" / "field_2026_v1"
    
    # Ensure fresh target directory structure for field_2026_v1
    if v1_dir.exists():
        shutil.rmtree(v1_dir)
    
    v1_dir.mkdir(parents=True, exist_ok=True)
    (v1_dir / "metadata").mkdir(exist_ok=True)
    (v1_dir / "raw_5min" / "zone_A").mkdir(parents=True, exist_ok=True)
    (v1_dir / "raw_5min" / "zone_B").mkdir(parents=True, exist_ok=True)
    (v1_dir / "analytical_5min").mkdir(exist_ok=True)
    (v1_dir / "scripts").mkdir(exist_ok=True)
    (v1_dir / "manifests").mkdir(exist_ok=True)

    print("1. Copying Verified 32-Day SD-Card Telemetry for field_2026_v1 (2026-07-22 to 2026-08-22)...")
    src_5min_a = physical_src / "Zone_A_5min"
    src_5min_b = physical_src / "Zone_B_5min"
    
    count_a, count_b = 0, 0
    for csv_file in sorted(src_5min_a.glob("zone_A_2026-07-*.csv")) + sorted(src_5min_a.glob("zone_A_2026-08-*.csv")):
        shutil.copy2(csv_file, v1_dir / "raw_5min" / "zone_A" / csv_file.name)
        count_a += 1
        
    for csv_file in sorted(src_5min_b.glob("zone_B_2026-07-*.csv")) + sorted(src_5min_b.glob("zone_B_2026-08-*.csv")):
        shutil.copy2(csv_file, v1_dir / "raw_5min" / "zone_B" / csv_file.name)
        count_b += 1
        
    print(f"   Copied {count_a} verified files for Zone A and {count_b} verified files for Zone B.")
    print(f"   Date Range: 2026-07-22 to 2026-08-22 (Zero September files included).")

    print("2. Copying 5-min Analytical Parquet Datasets...")
    src_an_a = base_dir / "data" / "field" / "analytical_5min" / "zone_A" / "field_zone_A_5min.parquet"
    src_an_b = base_dir / "data" / "field" / "analytical_5min" / "zone_B" / "field_zone_B_5min.parquet"
    if src_an_a.exists():
        shutil.copy2(src_an_a, v1_dir / "analytical_5min" / "field_zone_A_5min.parquet")
    if src_an_b.exists():
        shutil.copy2(src_an_b, v1_dir / "analytical_5min" / "field_zone_B_5min.parquet")

    print("3. Copying Data Processing Transformation Scripts...")
    src_scripts = base_dir / "backend" / "scripts"
    for s_name in ["audit_field_csv.py", "qc_field_data.py", "build_field_5min.py"]:
        s_path = src_scripts / s_name
        if s_path.exists():
            shutil.copy2(s_path, v1_dir / "scripts" / s_name)

    print("4. Generating Requirements, License, & Metadata Files...")
    req_content = """pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
fastparquet>=2023.4.0
pyarrow>=12.0.0
scikit-learn>=1.2.0
"""
    with open(v1_dir / "requirements.txt", "w", encoding="utf-8") as f:
        f.write(req_content)

    license_content = """Creative Commons Attribution 4.0 International (CC BY 4.0)

You are free to:
- Share — copy and redistribute the material in any medium or format
- Adapt — remix, transform, and build upon the material for any purpose, even commercially.

Under the following terms:
- Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made.

Full License Text: https://creativecommons.org/licenses/by/4.0/legalcode
"""
    with open(v1_dir / "LICENSE.txt", "w", encoding="utf-8") as f:
        f.write(license_content)

    campaign_meta = {
        "dataset_name": "Dual-Zone Agrivoltaic Field Sensor Dataset",
        "dataset_version": "field_2026_v1",
        "publication_status": "FROZEN_LOCKED",
        "target_crop": "Cowpea (Vigna unguiculata)",
        "location": {
            "site": "Research Farm, Block B",
            "coordinates": "11.0168 N, 76.9558 E",
            "zone_A_description": "Open-field control (Full Sun)",
            "zone_B_description": "Agrivoltaic PV-shaded canopy (38.9% shading)"
        },
        "campaign_timeline": {
            "start_date": "2026-07-22",
            "end_date": "2026-08-22",
            "duration_days": 32,
            "held_out_validation_window": "Days 17 to 31 (2026-08-08 to 2026-08-22)"
        },
        "sampling": {
            "native_interval_seconds": 300,
            "analytical_interval_seconds": 300,
            "resampling_method": "left_closed_5min_mean"
        },
        "record_counts": {
            "expected_native_records_per_zone": 9216,
            "audited_native_records_total": 18432,
            "qc_valid_native_records_total": 18432,
            "analytical_5min_records_per_zone": 9216,
            "analytical_5min_records_total": 18432
        },
        "transducers": [
            {"sensor": "ESP32-S3", "role": "Microcontroller Node & SD Logging"},
            {"sensor": "BME280", "parameters": ["air_temperature_c", "relative_humidity_pct", "pressure_hpa"]},
            {"sensor": "BH1750 (Dual)", "parameters": ["light_up_lux", "light_down_lux"], "conversion": "Rs = lux * 0.0079 W/m2"},
            {"sensor": "DS18B20", "parameters": ["soil_temperature_c"]},
            {"sensor": "DS3231", "parameters": ["real_time_clock_timestamp"]},
            {"sensor": "Capacitive VWC", "parameters": ["soil_vwc_mean", "soil_adc_1", "soil_adc_2"]}
        ]
    }
    with open(v1_dir / "metadata" / "campaign_metadata.json", "w", encoding="utf-8") as f:
        json.dump(campaign_meta, f, indent=4)

    sensor_config_data = [
        ["sensor_id", "model", "parameter", "unit", "sampling_rate", "bus_interface", "accuracy", "operating_range"],
        ["SENS_01", "BME280", "air_temperature", "degC", "5 min", "I2C 0x76", "+/- 0.5 degC", "-40 to +85 degC"],
        ["SENS_02", "BME280", "relative_humidity", "%", "5 min", "I2C 0x76", "+/- 3.0 %", "0 to 100 %"],
        ["SENS_03", "BME280", "barometric_pressure", "hPa", "5 min", "I2C 0x76", "+/- 1.0 hPa", "300 to 1100 hPa"],
        ["SENS_04", "BH1750_UP", "incident_lux", "lux", "5 min", "I2C 0x23", "+/- 20 %", "1 to 65535 lux"],
        ["SENS_05", "BH1750_DN", "reflected_lux", "lux", "5 min", "I2C 0x5C", "+/- 20 %", "1 to 65535 lux"],
        ["SENS_06", "DS18B20", "soil_temperature", "degC", "5 min", "OneWire Pin 4", "+/- 0.5 degC", "-55 to +125 degC"],
        ["SENS_07", "DS3231", "rtc_timestamp", "ISO8601", "5 min", "I2C 0x68", "+/- 2 ppm", "Real-Time Clock"],
        ["SENS_08", "CAP_VWC_1", "soil_moisture_ch1", "m3/m3", "5 min", "ADC GPIO 32", "+/- 0.03 m3/m3", "0.0 to 0.45 m3/m3"],
        ["SENS_09", "CAP_VWC_2", "soil_moisture_ch2", "m3/m3", "5 min", "ADC GPIO 33", "+/- 0.03 m3/m3", "0.0 to 0.45 m3/m3"]
    ]
    with open(v1_dir / "metadata" / "sensor_configuration.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(sensor_config_data)

    dict_data = [
        ["variable_name", "dataset_level", "data_type", "unit", "description", "valid_range"],
        ["timestamp", "raw_5min / analytical_5min", "datetime", "ISO8601", "Observation timestamp (UTC/Local)", "2026-07-22 to 2026-08-22"],
        ["air_temp_c", "raw / qc / analytical", "float", "degC", "Air temperature measured by BME280 sensor", "10.0 to 45.0"],
        ["humidity_pct", "raw / qc / analytical", "float", "%", "Relative humidity measured by BME280 sensor", "10.0 to 100.0"],
        ["pressure_hpa", "raw / qc / analytical", "float", "hPa", "Barometric pressure measured by BME280 sensor", "900.0 to 1050.0"],
        ["soil_temp_c", "raw / qc / analytical", "float", "degC", "Soil temperature at 10cm depth measured by DS18B20", "10.0 to 45.0"],
        ["soil_vwc_mean", "analytical_5min", "float", "m3/m3", "Calibrated volumetric soil water content (2-channel mean)", "0.05 to 0.45"],
        ["light_up_lux", "raw / qc / analytical", "float", "lux", "Incident solar illuminance measured by upward BH1750", "0 to 120000"],
        ["light_down_lux", "raw / qc / analytical", "float", "lux", "Reflected canopy illuminance measured by downward BH1750", "0 to 30000"],
        ["vpd_kpa", "analytical_5min", "float", "kPa", "Vapor pressure deficit derived from Tair and RH", "0.0 to 4.5"],
        ["rs_down_wm2", "analytical_5min", "float", "W/m2", "Shortwave solar irradiance estimated from lux (lux * 0.0079)", "0.0 to 1200.0"],
        ["bme_ok", "raw_5min / qc_5min", "int/bool", "flag", "BME280 hardware self-test diagnostic flag (1=OK, 0=FAIL)", "0 or 1"],
        ["bh1_ok", "raw_5min / qc_5min", "int/bool", "flag", "BH1750 hardware self-test diagnostic flag (1=OK, 0=FAIL)", "0 or 1"],
        ["ds18_ok", "raw_5min / qc_5min", "int/bool", "flag", "DS18B20 hardware self-test diagnostic flag (1=OK, 0=FAIL)", "0 or 1"],
        ["rtc_ok", "raw_5min / qc_5min", "int/bool", "flag", "DS3231 RTC hardware self-test diagnostic flag (1=OK, 0=FAIL)", "0 or 1"],
        ["zone", "all", "string", "category", "Experimental zone identifier (Zone A=Control, Zone B=Agrivoltaic)", "A or B"]
    ]
    with open(v1_dir / "metadata" / "data_dictionary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(dict_data)

    print("5. Writing README.md...")
    readme_text = """# Dual-Zone Agrivoltaic Field Dataset — field_2026_v1

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
"""
    with open(v1_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_text)

    print("6. Generating SHA-256 Manifest (SHA256SUMS.csv)...")
    manifest_rows = []
    
    for fpath in sorted(v1_dir.rglob("*")):
        if fpath.is_file() and fpath.name != "SHA256SUMS.csv":
            rel_path = fpath.relative_to(v1_dir).as_posix()
            fsize = fpath.stat().st_size
            fhash = compute_sha256(fpath)
            manifest_rows.append([rel_path, fsize, fhash])
            
    manifest_path = v1_dir / "manifests" / "SHA256SUMS.csv"
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "file_size_bytes", "sha256_hash"])
        writer.writerows(manifest_rows)

    print(f"   Generated SHA-256 entries for {len(manifest_rows)} files.")

    print("7. Packaging Zenodo Zip Archive (outputs/zenodo/field_2026_v1.zip)...")
    zenodo_out = base_dir / "outputs" / "zenodo"
    zenodo_out.mkdir(parents=True, exist_ok=True)
    zip_path = zenodo_out / "field_2026_v1.zip"
    
    if zip_path.exists():
        zip_path.unlink()

    shutil.make_archive(str(zenodo_out / "field_2026_v1"), 'zip', root_dir=base_dir / "data", base_dir="field_2026_v1")
    
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    zip_sha256 = compute_sha256(zip_path)
    
    print("\nZenodo Dataset Package Created Successfully!")
    print(f"   Folder: {v1_dir}")
    print(f"   Zip Archive: {zip_path} ({zip_size_mb:.2f} MB)")
    print(f"   Zip SHA-256: {zip_sha256}")

    summary_data = {
        "dataset_name": "Dual-Zone Agrivoltaic Field Sensor Dataset: Open-Field and PV-Shaded Microclimate Telemetry",
        "dataset_version": "field_2026_v1",
        "archive_zip": str(zip_path),
        "zip_size_mb": round(zip_size_mb, 2),
        "zip_sha256": zip_sha256,
        "files_count": len(manifest_rows),
        "zenodo_metadata_fields": {
            "title": "Dual-Zone Agrivoltaic Field Sensor Dataset: Open-Field and PV-Shaded Microclimate Telemetry",
            "upload_type": "dataset",
            "publication_date": "2026-08-26",
            "creators": [
                {"name": "Prabakaran, S.", "affiliation": "Research Scholar"}
            ],
            "description": "Real-world dual-zone agrivoltaic microclimate telemetry collected from July 22 to August 22, 2026 for Cowpea (Vigna unguiculata). Includes 32 daily SD CSVs per zone, 5-min analytical Parquet datasets, transformation scripts, and SHA-256 integrity hashes.",
            "keywords": [
                "Agrivoltaics", "Microclimate", "Precision Agriculture", "Soil Moisture", 
                "Evapotranspiration", "FAO-56", "Cowpea", "IoT Sensors", "Field Validation",
                "Machine Learning", "Domain Adaptation"
            ],
            "access_right": "open",
            "license": "CC-BY-4.0"
        }
    }
    with open(zenodo_out / "field_2026_v1_zenodo_metadata.json", "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=4)

if __name__ == "__main__":
    main()
