=== RUN 2C EXPERIMENTAL REPORT: IRRIGATION REQUIREMENT FORECASTING ===

### 1. Model Summary & Architectural Shift
RUN 2C redefines the target from predicting raw soil moisture (theta_v) to predicting the **24-hour root-zone irrigation requirement (IR*)** derived from exact physical counterfactual bisection search.

### 2. Operational Primary Results (5-Fold CV)
| Fold | Hybrid AI RMSE (mm) | Physics Forecast RMSE (mm) | Persistence RMSE (mm) | AI F1 | Phys F1 | Pers F1 | AI NRMSE |
|---|---|---|---|---|---|---|---|
| Fold 1 | 16.1603 | 33.2964 | 35.6933 | 0.9579 | 0.8345 | 0.7212 | 0.4467 |
| Fold 2 | 16.6810 | 31.7366 | 34.5699 | 0.9437 | 0.9211 | 0.8146 | 0.4678 |
| Fold 3 | 11.2362 | 30.1842 | 32.9188 | 0.9832 | 0.9132 | 0.8285 | 0.2911 |
| Fold 4 | 8.0783 | 27.2376 | 30.8255 | 1.0000 | 0.9755 | 0.9416 | 0.2077 |
| Fold 5 | 19.4905 | 32.0254 | 34.1273 | 0.9036 | 0.7926 | 0.7288 | 0.5925 |

**Mean Operational RMSE:** Hybrid AI = **14.3293 mm** | Physics Forecast = **30.8960 mm** | Persistence = **33.6270 mm**

### 3. Oracle Upper-Bound Diagnostic Results (Perfect Weather Forcing)
| Fold | Oracle Hybrid AI RMSE (mm) | Perfect Physics RMSE (mm) | Oracle AI F1 | Perfect Phys F1 |
|---|---|---|---|---|
| Fold 1 | 22.8722 | 33.3273 | 0.9579 | 0.8479 |
| Fold 2 | 17.1526 | 31.6668 | 0.9437 | 0.9079 |
| Fold 3 | 11.0764 | 30.2137 | 0.9832 | 0.9265 |
| Fold 4 | 8.1837 | 27.1853 | 1.0000 | 1.0000 |
| Fold 5 | 22.5111 | 31.9771 | 0.9036 | 0.8032 |

**Mean Oracle AI RMSE:** **16.3592 mm** (Information upper bound)

### 4. Quantile Uncertainty & Calibration (Operational Mode)
| Fold | P10 Coverage | P50 Coverage | P90 Coverage | Mean Interval Width (mm) |
|---|---|---|---|---|
| Fold 1 | 0.0809 | 0.1103 | 0.0809 | 13.5278 |
| Fold 2 | 0.1066 | 1.0000 | 1.0000 | 47.1409 |
| Fold 3 | 0.0331 | 1.0000 | 0.9963 | 44.9033 |
| Fold 4 | 0.0000 | 1.0000 | 1.0000 | 44.7675 |
| Fold 5 | 0.1795 | 1.0000 | 0.9963 | 14.3510 |
