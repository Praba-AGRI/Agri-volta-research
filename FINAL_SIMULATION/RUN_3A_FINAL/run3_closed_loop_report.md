=== RUN 3 EXPERIMENTAL REPORT: CLOSED-LOOP POLICY EVALUATION ===

### 1. 70-Day Monsoon Closed-Loop Performance Matrix (Zone B Agrivoltaics)
| Policy ID | Controller Description | Total Applied IR (mm) | IR Events | Final Yield (kg/ha) | WUE (kg/m³) | Stress Exposure (Ks < 1.0) |
|---|---|---|---|---|---|---|
| **B_AI** | B_AI Policy | 52.74 mm | 2 | 2558.97 | 0.9217 | 0.0 hrs |
| **B_LSTM** | B_LSTM Policy | 0.00 mm | 0 | 2558.56 | 0.9215 | 7.5 hrs |
| **B_AI_PERS** | B_AI_PERS Policy | 201.29 mm | 35 | 2558.97 | 0.9217 | 0.0 hrs |
| **B_IOT** | B_IOT Policy | 0.00 mm | 0 | 2558.56 | 0.9215 | 7.5 hrs |
| **B_FIX** | B_FIX Policy | 115.00 mm | 23 | 2558.97 | 0.9217 | 0.0 hrs |

### 2. Operational Water Savings & Crop Safety Analysis
- **Applied Irrigation (Proposed ElasticNet B_AI):** **52.74 mm** (2 targeted events)
- **Applied Irrigation (Fixed Schedule B_FIX):** **115.00 mm** (23 events)
- **Applied Irrigation (Persistence AI B_AI_PERS):** **201.29 mm** (35 events)
- **Applied Irrigation (Threshold IoT B_IOT):** **0.00 mm** (0 events due to monsoon rain dominance)

**Water Savings Performance:**
- **54.1% Volumetric Water Reduction vs Fixed Schedule B_FIX** (62.26 mm saved)
- **73.8% Volumetric Water Reduction vs Persistence AI B_AI_PERS** (148.55 mm saved)
- **Crop Stress Elimination:** B_AI eliminated all 7.5 hours of stress observed in B_IOT ($K_s = 1.0$ throughout the 70 days), achieving maximum potential yield (2558.97 kg/ha).
