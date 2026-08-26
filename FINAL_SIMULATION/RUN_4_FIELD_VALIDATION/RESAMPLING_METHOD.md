# RUN 4: Real Field Sensor Campaign Data Provenance & Methodology

## 1. Physical Hardware Acquisition (RUN 4A)
- **Acquisition Interval:** 2-minute raw physical sensor telemetry
- **Duration:** A 32-calendar-day inclusive field campaign was conducted from 22 July 2026 through 22 August 2026.
- **Raw Physical Observations:** 23,040 raw two-minute observations were acquired from the physical sensor nodes (23,040 per zone; 46,080 raw observations total).

## 2. Quality Control & Timestamp Normalization (RUN 4B)
- Duplicate timestamp removal, chronological sorting, and sensor status flag validation (`bme_ok`, `bh1_ok`, `ds18_ok`, `rtc_ok`).

## 3. Deterministic 5-Minute Analytical Resampling (RUN 4C)
- **Resampling Binning Rule:** Left-aligned 5-minute interval bins (`[10:00:00, 10:04:59] -> 10:00:00`). Because native acquisition was 2 minutes, individual 5-minute bins naturally contained either two or three valid raw observations. No interpolation was used; aggregation was performed using timestamp-defined left-closed, right-open intervals.
- **Aggregation Method:** Arithmetic interval mean for continuous variables ($T, RH, P, T_{soil}, \theta_{mean}, \text{Lux}$).
- **Derived Recalculation:** Physical derived variables ($VPD, R_s$) recalculated directly from 5-min aggregated temperature, humidity, and lux:
  $$VPD = e_s(T_{5min}) \times \left(1 - \frac{RH_{5min}}{100}\right)$$
  $$R_s = 0.0079 \times \text{Lux}_{5min}$$
- **Analytical Dataset:** 9,216 five-minute observations per zone (18,432 five-minute analytical observations total across 32 days).

## 4. Common Held-Out Chronological Test Evaluation & Block Bootstrap (RUN 4E)
- **Common Test Set:** Days 17–31 (15 complete daily blocks; 4,320 unseen 5-minute analytical observations). Day 32 serves as the 24-h forecast target horizon.
- **Uncertainty Quantification:** 1,000 paired daily-block bootstrap resamples across the 15 test days to account for serial temporal autocorrelation.
