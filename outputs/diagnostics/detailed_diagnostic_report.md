=== DETAILED DIAGNOSTICS REPORT ===

### 1. True Residual (delta_theta_24h) Statistics
Mean Residual: 0.000047
Std Residual: 0.010546
P5: -0.013089
P25: -0.005602
P50: -0.001512
P75: 0.002905
P95: 0.022877

### 2. Residual Predictability (R2 score on delta_theta_24h)
| Fold | Linear Regression R2 | Tabular Random Forest R2 | Enhanced BiLSTM R2 |
|---|---|---|---|
| Fold 1 | -15.5843 | -1.5430 | -5908644.5000 |
| Fold 2 | 0.0772 | -0.0505 | -3427359.7500 |
| Fold 3 | -0.8010 | -0.0878 | -1755022.2500 |
| Fold 4 | -1.8002 | -1.3128 | -292320.4062 |
| Fold 5 | -1.4054 | -0.8319 | -531758.5000 |

### 3. Feature Permutation delta_RMSE (RMSE_permuted - RMSE_full)
Positive value means feature group is useful (disrupting it hurts prediction).

| Fold | moisture | rainfall | radiation | vpd | soil_temp | shade | gdd |
|---|---|---|---|---|---|---|---|
| Fold 1 | -0.000052 | -0.000002 | -0.000035 | -0.000058 | 0.000005 | -0.000013 | 0.000000 |
| Fold 2 | 0.000572 | 0.000435 | 0.000950 | 0.000253 | 0.000264 | 0.000164 | 0.000000 |
| Fold 3 | 0.000573 | 0.001090 | 0.001062 | 0.000932 | 0.000034 | -0.000024 | 0.000000 |
| Fold 4 | -0.000001 | -0.000002 | -0.000001 | 0.000014 | 0.000003 | 0.000000 | 0.000000 |
| Fold 5 | 0.000088 | 0.000040 | -0.000206 | 0.000089 | 0.000084 | 0.000074 | 0.000000 |

### 4. Critical Event Detection Confusion Matrices (Threshold < 0.2025)
Compare Enhanced BiLSTM with Persistence baseline:

| Fold | Model (TP, FP, FN, TN) | Model F1 | Pers (TP, FP, FN, TN) | Pers F1 |
|---|---|---|---|---|
| Fold 1 | 0, 0, 0, 3216 | 1.0000 | 0, 0, 0, 3216 | 1.0000 |
| Fold 2 | 0, 0, 0, 3216 | 1.0000 | 0, 0, 0, 3216 | 1.0000 |
| Fold 3 | 0, 31, 0, 3185 | 0.0000 | 0, 0, 0, 3216 | 1.0000 |
| Fold 4 | 0, 91, 91, 3034 | 1.0000 | 0, 91, 91, 3034 | 1.0000 |
| Fold 5 | 0, 0, 0, 3217 | 1.0000 | 0, 0, 0, 3217 | 1.0000 |

### 5. Regime-wise RMSE Comparison
| Fold | Dry (Pers) | Dry (Enh) | Rain (Pers) | Rain (Enh) | Boundary (Pers) | Boundary (Enh) |
|---|---|---|---|---|---|---|
| Fold 1 | 0.00441 | 0.00526 | 0.00367 | 0.00354 | nan | nan |
| Fold 2 | 0.00575 | 0.00578 | 0.01204 | 0.01203 | nan | nan |
| Fold 3 | 0.01179 | 0.01217 | 0.00812 | 0.00879 | 0.01052 | 0.01247 |
| Fold 4 | 0.01219 | 0.01219 | 0.01486 | 0.01486 | 0.02904 | 0.02905 |
| Fold 5 | 0.00797 | 0.00812 | 0.01172 | 0.01194 | nan | nan |

### 6. Gate & Direction Accuracy Analysis
| Fold | Gate Mean | Gate Max | Corr(g, |true_res|) | Direction Accuracy |
|---|---|---|---|---|
| Fold 1 | 0.0001 | 0.0007 | 0.1705 | 0.4739 |
| Fold 2 | 0.0002 | 0.0058 | -0.0733 | 0.3013 |
| Fold 3 | 0.0051 | 0.1587 | 0.1348 | 0.2236 |
| Fold 4 | 0.0000 | 0.0000 | 0.1760 | 0.0939 |
| Fold 5 | 0.0028 | 0.0767 | -0.0550 | 0.3365 |

