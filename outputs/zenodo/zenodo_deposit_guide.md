# Zenodo Dataset Deposit & Manuscript Citation Guide — field_2026_v1

> [!IMPORTANT]
> **Dataset Status**: **FROZEN & LOCKED**  
> **Zip Archive Ready for Upload**: `outputs/zenodo/field_2026_v1.zip` (7.84 MB)  
> **Archive SHA-256 Hash**: `8d3fa4ceb4a84227e120b202578b23ee4ee148a2bab983a8d4f2840bff33045a`  
> **Security Audit**: **PASSED** (0 passwords, 0 Wi-Fi credentials, 0 API keys)

---

## 1. Final Dataset Manifest Summary

| Item | Value / Description |
| :--- | :--- |
| **Dataset Version** | `field_2026_v1` (Immutable Publication Snapshot) |
| **Title** | *Dual-Zone Agrivoltaic Field Sensor Dataset: Open-Field and PV-Shaded Microclimate Telemetry* |
| **Target Crop** | Cowpea (*Vigna unguiculata*) |
| **Location** | Research Farm, Block B (11.0168° N, 76.9558° E) |
| **Zone A** | Open-Field Control (Full Sun) |
| **Zone B** | Agrivoltaic PV Canopy (38.9% shading reduction) |
| **Campaign Period** | 22 July 2026 to 22 August 2026 (32 Days) |
| **Native Sampling** | 2-minute interval (ESP32-S3 SD-card logging) |
| **Analytical Resolution** | 5-minute left-closed mean binning |
| **Audited Raw Records** | 46,080 rows (62 daily CSV files across Zone A & B) |
| **QC Valid Records** | 46,080 rows (100% timestamp sanity & operational flag validation) |
| **Analytical Records** | 18,432 5-min Parquet rows |
| **License** | Creative Commons Attribution 4.0 International (**CC BY 4.0**) |

---

## 2. Directory Structure inside `field_2026_v1.zip`

```text
field_2026_v1/
├── README.md                          (Comprehensive dataset documentation)
├── LICENSE.txt                         (CC BY 4.0 License text)
├── requirements.txt                    (Python reproducible environment spec)
├── metadata/
│   ├── campaign_metadata.json          (JSON metadata schema)
│   ├── sensor_configuration.csv        (Hardware pins, accuracy, bus addresses)
│   └── data_dictionary.csv             (Variable definitions & valid ranges)
├── raw_2min/
│   ├── zone_A/                         (32 daily native CSV files)
│   └── zone_B/                         (32 daily native CSV files)
├── qc_2min/
│   ├── zone_A/                         (Quality-controlled 2-min files)
│   └── zone_B/                         (Quality-controlled 2-min files)
├── analytical_5min/
│   ├── field_zone_A_5min.parquet       (Zone A research analytical Parquet)
│   └── field_zone_B_5min.parquet       (Zone B research analytical Parquet)
├── scripts/
│   ├── audit_field_csv.py              (Non-destructive timestamp & flag audit)
│   ├── qc_field_data.py                (Sensor flag QC filtering)
│   └── build_field_5min.py             (Deterministic 5-min resampling script)
└── manifests/
    └── SHA256SUMS.csv                  (Cryptographic SHA-256 hashes for all 145 files)
```

---

## 3. Metadata for Zenodo Upload Form

When uploading to [Zenodo Upload Form](https://zenodo.org/uploads/new):

- **Upload Type**: `Dataset`
- **Title**: `Dual-Zone Agrivoltaic Field Sensor Dataset: Open-Field and PV-Shaded Microclimate Telemetry`
- **Publication Date**: `2026-08-26`
- **Creators**: `Prabakaran, S.` (Affiliation: *Research Scholar*)
- **Description**:
  ```text
  This dataset contains real field sensor telemetry collected from a dual-zone agrivoltaic experimental deployment consisting of Zone A (Open-field control) and Zone B (Agrivoltaic PV-shaded canopy, 38.9% shading reduction) for Cowpea (Vigna unguiculata). 
  
  The dataset covers the 32-day field validation campaign from July 22 to August 22, 2026. It includes original 2-min native SD-card CSV telemetry (46,080 observations), quality-controlled records, 5-min analytical Parquet datasets (18,432 observations), sensor calibration documentation, Python data processing scripts, and SHA-256 file integrity manifests.
  ```
- **Keywords**: `Agrivoltaics`, `Microclimate`, `Precision Agriculture`, `Soil Moisture`, `Evapotranspiration`, `FAO-56`, `Cowpea`, `IoT Sensors`, `Field Validation`, `Machine Learning`, `Domain Adaptation`
- **License**: `Creative Commons Attribution 4.0 International` (`CC-BY-4.0`)
- **Version**: `field_2026_v1`

---

## 4. Manuscript Statements & Citations

### 📝 **Data Availability Statement** (for Section in Manuscript):
> **Data Availability**: The raw and quality-controlled dual-zone agrivoltaic field telemetry supporting the field-validation analysis are publicly available as version `field_2026_v1` at Zenodo: https://doi.org/10.5281/zenodo.xxxxxxx. The dataset includes the original 2-min SD-card telemetry, quality-controlled records, 5-min analytical datasets, hardware configuration metadata, data-processing transformation scripts, and cryptographic SHA-256 integrity manifests. The operational dashboard is accessible separately at http://localhost:5173.

### 📚 **Formal References Section Citation**:
> Prabakaran, S. (2026). *Dual-Zone Agrivoltaic Field Sensor Dataset: Open-Field and PV-Shaded Microclimate Telemetry (Version field_2026_v1)* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.xxxxxxx

---

## 5. Architectural Separation Architecture

```text
               PHYSICAL FIELD EXPERIMENT (Cowpea, Block B)
                                   │
                         ┌─────────┴─────────┐
                         │                   │
                  ESP32 Telemetry       SD-Card Files
                         │                   │
                         ▼                   ▼
                      MQTT                Raw CSV
                         │                   │
                         │     ┌─────────────┴─────────────┐
                         │     │ LOCAL RESEARCH ARCHIVE    │
                         │     │ ├── raw_2min/             │
                         │     │ ├── qc_2min/              │
                         │     │ ├── analytical_5min/      │
                         │     │ ├── metadata/             │
                         │     │ └── SHA256SUMS.csv        │
                         │     └─────────────┬─────────────┘
                         │                   │
                         │         ┌─────────┴─────────┐
                         │         │                   │
                         ▼         ▼                   ▼
                  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
                  │  DASHBOARD   │   │   MANUSCRIPT │   │    ZENODO    │
                  │ (Operational │   │    (RUN 4    │   │  (Citable    │
                  │ Layer: 5173) │   │   Analysis)  │   │  DOI Record) │
                  └──────────────┘   └──────────────┘   └──────────────┘
```
