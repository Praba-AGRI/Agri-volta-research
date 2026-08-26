=== RUN 2C FINAL MODEL SELECTION & FREEZE GATE REPORT ===

### 1. Model Ranking & Selection Matrix
| Model | Information Boundary | Mean RMSE_IR (mm) | Mean FNR | Mean |ICE90| | Mean F1 | Safety Eligible | Selected Winner |
|---|---|---|---|---|---|---|---|
| Persistence | State + Forecast | 34.3633 | 0.3276 | 0.8317 | 0.7982 | NO | No |
| PhysicsForecast | State + Forecast | 31.6833 | 0.2074 | 0.8200 | 0.8784 | NO | No |
| ElasticNet | State + Forecast | 8.9187 | 0.0000 | 0.0811 | 0.9669 | YES | YES (FROZEN) |
| RandomForest | State + Forecast | 10.9073 | 0.0229 | 0.1000 | 0.9601 | YES | No |
| HistGradientBoosting | State + Forecast | 11.4181 | 0.0717 | 0.0985 | 0.9408 | YES | No |
| BiLSTM | State + Forecast | 12.0301 | 0.0000 | 0.3082 | 0.9669 | NO | No |

### 2. Frozen Winner Details
- **Selected Model:** **ElasticNet**
- **Primary $RMSE_{IR}$:** **8.9187 mm**
- **Forecast Information Gain ($IG_{forecast}$):** **44.52%** (over Past-Only baseline)
- **Mean Predictive Interval Width ($IR_{90} - IR_{10}$):** 14.5408 mm

### 3. Provenance & Hashes
- `feature_schema_hash`: `0c6e82f26313`
- `dataset_reachability`: Total = 1633 | Reachable = 1633 (100.0%) | Unreachable = 0

### 4. Audit Status Flags
```text
VALIDATION INTEGRITY:      PASS
LABEL ENGINE:              PASS (Exact Physical Reachability Filtered)
LEAKAGE AUDIT:             PASS (Causal Provenance Verified)
ORACLE/OPERATIONAL:        EXPLAINED (Regularization Jitter)
UNCERTAINTY CALIBRATION:   PASS (|ICE90| <= 0.15)
SAFETY SELECTION:          PASS (FNR <= 0.15)
FREEZE RECOMMENDATION:     FREEZE ELASTICNET FOR RUN 3
```
