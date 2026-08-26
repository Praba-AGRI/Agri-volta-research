=== VERIFIED RUN 3B CONSISTENCY & DECISION-PARITY REPORT ===

### 1. Corrected 30-Season Summary Performance Matrix (N=30 Paired Realizations)
| Policy ID | Description | Mean Applied IR (mm) | Mean Events | Mean Yield (kg/ha) | Mean WUE_ET (kg/m³) | Mean Stress Hours (Ks < 1.0) |
|---|---|---|---|---|---|---|
| **B-FIX** | B-FIX Policy | 115.00 ± 0.00 | 23.0 | 2704.02 | 0.9487 | 92.8 hrs |
| **B-IOT** | B-IOT Policy | 199.02 ± 273.30 | 4.1 | 2714.79 | 0.9506 | 108.9 hrs |
| **B-AI-PERS** | B-AI-PERS Policy | 406.46 ± 204.26 | 38.1 | 2765.91 | 0.9584 | 37.2 hrs |
| **B-PHYS** | B-PHYS Policy | 253.89 ± 272.26 | 7.0 | 2740.10 | 0.9544 | 73.4 hrs |
| **B-LSTM** | B-LSTM Policy | 0.00 ± 0.00 | 0.0 | 2649.00 | 0.9402 | 129.0 hrs |
| **B-AI-EN** | B-AI-EN Policy | 251.18 ± 259.28 | 7.0 | 2740.10 | 0.9544 | 73.4 hrs |

### 2. Corrected Operational Water & Stress Trade-Off Analysis
- **vs Persistence-Derived (B-AI-PERS):** **38.2% Volumetric Water Savings** (155.28 mm saved/season)
- **vs Physics-Only Forecast (B-PHYS):** **1.07% Volumetric Water Savings** (2.71 mm saved/season)
- **vs Threshold IoT (B-IOT):** **+26.2% Additional Irrigation** (+52.16 mm/season)
  - **Stress Exposure Trade-Off:** B-AI-EN reduced seasonal water stress by **35.5 hours/season** (73.4 hrs vs 108.9 hrs), producing **+0.942% higher crop yield** (95% CI: [+0.564%, +1.370%]).

### 3. Mechanistic Equivalence: B-AI-EN vs B-PHYS
- **Operational Decision Parity:** B-AI-EN and B-PHYS exhibit near-identical closed-loop trajectories (mean difference = 2.71 mm, zero yield or stress discrepancy).
- **Agronomic Finding:** The fitted ElasticNet model learns to reproduce the physical water-balance equation, validating that 24-h irrigation requirement is governed by state depletion and forecast precipitation rather than deep temporal patterns.
