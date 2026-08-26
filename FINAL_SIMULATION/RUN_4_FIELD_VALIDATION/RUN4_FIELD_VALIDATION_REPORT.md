# RUN 4: Real Field Sensor Campaign Data Provenance & Common Chronological Validation Report

## 1. Physical Hardware Acquisition (RUN 4A)
- **Acquisition Interval:** 2-minute raw physical sensor telemetry
- **Duration:** A 32-calendar-day inclusive field campaign was conducted from 22 July 2026 through 22 August 2026.
- **Raw Physical Observations:** 23,040 raw two-minute observations were acquired from the physical sensor nodes (23,040 per zone; 46,080 raw observations total).

---

## 2. Quality Control & Timestamp Normalization (RUN 4B)
- Duplicate timestamp removal, chronological sorting, and sensor status flag validation (`bme_ok`, `bh1_ok`, `ds18_ok`, `rtc_ok = 1`).

---

## 3. Deterministic 5-Minute Analytical Resampling (RUN 4C)
- **Resampling Binning Rule:** Left-aligned 5-minute interval bins (`[10:00:00, 10:04:59] -> 10:00:00`). Because native acquisition was 2 minutes, individual 5-minute bins naturally contained either two or three valid raw observations. No interpolation was used; aggregation was performed using timestamp-defined left-closed, right-open intervals.
- **Aggregation Method:** Arithmetic interval mean for continuous variables ($T, RH, P, T_{soil}, \theta_{mean}, \text{Lux}$).
- **Derived Recalculation:** Physical derived variables ($VPD, R_s$) recalculated directly from 5-min aggregated temperature, humidity, and lux:
  $$VPD = e_s(T_{5min}) \times \left(1 - \frac{RH_{5min}}{100}\right)$$
  $$R_s = 0.0079 \times \text{Lux}_{5min}$$
- **Analytical Dataset:** 9,216 five-minute observations per zone (18,432 five-minute analytical observations total across 32 days).

---

## 4. Common Held-Out Chronological Test Evaluation & Daily Block Bootstrap (RUN 4E)
- **Common Test Set:** Days 17-31 (15 complete daily blocks; 4,320 forecast origins). Day 32 serves as the target horizon for Day 31 forecast origins.
- **Uncertainty Quantification:** 1,000 paired daily-block bootstrap resamples across the 15 test days to account for serial temporal autocorrelation.

---

## 5. Common Held-Out Evaluation Summary Matrix (Days 17-31 Common Test Set)

| Calibration Tier | Training Horizon | Common Held-Out Test Window | Forecast Origins | Test RMSE (mm) | 95% Daily Block-Bootstrap CI | Test MAE (mm) | Test Bias (mm) | Test $R^2$ |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model A (Zero-Shot)** | Simulation Only | Days 17-31 (15 Days) | 4,320 | 16.37 mm | [12.47, 20.62] mm | 13.75 mm | +7.01 mm | -0.2867 |
| **Model B (7-Day Fine-Tuned)** | Days 1-7 (2,016 steps) | **Days 17-31 (Common Test)** | **4,320** | **12.69 mm** | **[8.30, 16.39] mm** | **9.83 mm** | **+8.09 mm** | **0.2271** |
| **Model C (16-Day Fine-Tuned)** | Days 1-16 (4,608 steps) | **Days 17-31 (Common Test)** | **4,320** | **7.33 mm** | **[5.66, 8.70] mm** | **5.82 mm** | **-4.38 mm** | **0.7421** |

---

## 📜 Publication-Locked Manuscript Summary Statement

> RUN 4 demonstrated simulation-to-field transfer using chronologically held-out field observations. A 32-calendar-day field campaign generated 46,080 raw 2-minute sensor observations, which underwent timestamp quality control and deterministic resampling to 18,432 five-minute analytical observations. The common held-out evaluation comprised 4,320 forecast origins across 15 complete daily blocks (Days 17-31), with each origin evaluated against its corresponding 24-h-ahead irrigation-requirement target. Relative to the simulation-only model, 16-day field fine-tuning reduced held-out RMSE from 16.37 to 7.33 mm, corresponding to a 55.2% reduction. The paired daily-block bootstrap 95% confidence interval for the RMSE difference was -14.49 to -4.30 mm. MAE decreased from 13.75 to 5.82 mm, while test-set R2 improved from -0.2867 to 0.7421. These results indicate substantial improvement in simulation-to-field transfer following field calibration while retaining nonzero prediction error on unseen observations.
