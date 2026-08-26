# Physics-Informed Domain Adaptation and Safety-Constrained Machine Learning for Smart Agrivoltaic Irrigation Control

**Authors:** Prabakaran et al.  
**Target Journal:** IEEE Transactions on AgriFood Electronics / IEEE Transactions on Sustainable Energy  

---

## Abstract
Agrivoltaic systems integrate solar photovoltaic (PV) panel arrays with agricultural crop production, modifying canopy microclimates through partial shading and altering crop evapotranspiration ($ET_c$). While machine learning algorithms hold promise for precision irrigation management, traditional continuous soil-moisture sequence forecasters (e.g., BiLSTM architectures) fail to outperform simple persistence baselines because root-zone soil-water dynamics exhibit high temporal autocorrelation ($R^2 = 0.6768$). Furthermore, raw sequence forecasting does not directly inform closed-loop irrigation decision utility. To resolve these challenges, this study presents a physically constrained 24-h minimum sufficient irrigation forecasting framework ($IR^*$) evaluated across physics simulation, 30-season Monte Carlo closed-loop control, and a 32-calendar-day physical field campaign.

Nested temporal cross-validation on the reachable evaluation set demonstrates that an ElasticNet forecaster achieves superior performance ($RMSE = 8.92\text{ mm}$, $FNR = 0.00\%$, $|ICE_{90}| = 0.0811$) compared to Quantile Random Forest ($10.91\text{ mm}$), HistGradientBoosting ($11.42\text{ mm}$), and Multi-Output BiLSTM ($12.03\text{ mm}$). In 30-season Monte Carlo closed-loop simulation, the proposed ElasticNet controller achieved paired yield non-inferiority relative to threshold IoT control ($\Delta Y = +0.9425\%$, 95% CI $[+0.564\%, +1.370\%]$) while matching the optimal physics-only forecast policy.

Finally, a 32-calendar-day field campaign comprising 46,080 raw 2-minute sensor observations (resampled to 18,432 5-minute analytical observations) revealed a 38.9% lux-derived shortwave radiation reduction under PV panels. Evaluating models on a common chronologically held-out test window (Days 17–31; 4,320 forecast origins) established that 16-day field fine-tuning reduced held-out prediction RMSE from 16.37 mm (zero-shot) to 7.33 mm (55.2% error reduction, paired daily-block bootstrap 95% CI for RMSE difference $[-14.49, -4.30]\text{ mm}$), while improving test-set $R^2$ from $-0.2867$ to $0.7421$.

---

## 1. Introduction
Agrivoltaic systems offer a dual-land-use solution for renewable energy generation and crop cultivation. However, PV panel arrays modify microclimatic drivers—attenuating solar irradiance, suppressing vapor pressure deficit ($VPD$), and reducing soil thermal storage. Conventional irrigation scheduling relies on fixed calendar rules or simple threshold IoT controllers, which fail to exploit microclimate-induced water savings. Conversely, deep learning models (such as BiLSTM sequence forecasters) frequently suffer from state-persistence traps and domain transfer failure when deployed on physical field hardware.

---

## 2. Experimental Sitemap & Methodological Framework

```text
RUN 1: Physics Simulation & FAO-56 Microclimate Model
       ↓
RUN 2: 24-h Soil-Moisture Sequence Benchmark (Persistence Winner)
       ↓
RUN 2B: Residual Predictability Audit (delta_theta_24h R2 < 0)
       ↓
RUN 2C: Target Reformulation to Physical Irrigation Requirement IR* (ElasticNet Winner)
       ↓
RUN 3A: Single-Season Closed-Loop Mechanistic Evaluation
       ↓
RUN 3B-EN: 30-Season Paired Monte Carlo Closed-Loop Simulation
       ↓
RUN 4A-4E: 32-Day Real Field Sensor Campaign & Chronological Held-Out Validation
```

---

## 3. Real Field Provenance & Microclimate Divergence Audit

A 32-calendar-day inclusive field campaign was conducted from 22 July 2026 through 22 August 2026 across dual monitoring zones (Zone A: Open Field; Zone B: Agrivoltaic Treatment).

### Table 1: Field Microclimate Divergence Summary
| Microclimate Parameter | Zone A (Open Field) | Zone B (Agrivoltaic) | Observed Divergence | Physical Mechanism |
| :--- | :---: | :---: | :---: | :--- |
| **Lux-Derived Shortwave Irradiance** | Baseline | -38.9% | **-38.9%** | Direct beam solar shading by PV panel array |
| **Peak Daytime VPD** | 1.240 kPa | 1.127 kPa | **-0.113 kPa** | Reduced canopy thermal accumulation suppresses evaporative demand |
| **Peak Daytime Air Temp** | 31.25 °C | 30.82 °C | **-0.43 °C** | Shading lowers midday ambient thermal storage |
| **Peak Daytime RH Boost** | 62.40% | 63.57% | **+1.17%** | Transpirational moisture retention under panel canopy |
| **Peak Daytime Soil Temp** | 28.90 °C | 28.42 °C | **-0.48 °C** | Reduced daytime soil heating under shaded canopy |

---

## 4. Chronological Held-Out Independent Field Validation

All models were evaluated on the **exact same common held-out test window: Days 17–31 (15 complete daily blocks; 4,320 forecast origins)**, with each origin evaluated against its corresponding 24-h-ahead target.

### Table 4: Chronological Held-Out Field Validation Matrix
| Calibration Tier | Training Window | Common Held-Out Test Window | Forecast Origins | Test RMSE (95% Daily Block-Bootstrap CI) | Test MAE (mm) | Test Bias (mm) | Test $R^2$ |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Model A (Zero-Shot)** | Simulation Only | Days 17–31 (15 Days) | **4,320** | $16.37\text{ mm}$ **[12.47, 20.62]** | $13.75\text{ mm}$ | $+7.01\text{ mm}$ | **$-0.2867$** |
| **Model B (7-Day Fine-Tuned)** | Days 1–7 (2,016 steps) | **Days 17–31 (Common Test)** | **4,320** | $12.69\text{ mm}$ **[8.30, 16.39]** | $9.83\text{ mm}$ | $+8.09\text{ mm}$ | **$0.2271$** |
| **Model C (16-Day Fine-Tuned)**| Days 1–16 (4,608 steps) | **Days 17–31 (Common Test)** | **4,320** | **$7.33\text{ mm}$ [5.66, 8.70]** | **$5.82\text{ mm}$** | **$-4.38\text{ mm}$** | **$0.7421$** |

---

## 5. Conclusion & Paper Summary Statement
RUN 4 demonstrated simulation-to-field transfer using chronologically held-out field observations. A 32-calendar-day field campaign generated 46,080 raw 2-minute sensor observations, which underwent timestamp quality control and deterministic resampling to 18,432 five-minute analytical observations. The common held-out evaluation comprised 4,320 forecast origins across 15 complete daily blocks (Days 17–31), with each origin evaluated against its corresponding 24-h-ahead irrigation-requirement target. Relative to the simulation-only model, 16-day field fine-tuning reduced held-out RMSE from 16.37 to 7.33 mm, corresponding to a 55.2% reduction. The paired daily-block bootstrap 95% confidence interval for the RMSE difference was −14.49 to −4.30 mm. MAE decreased from 13.75 to 5.82 mm, while test-set R² improved from −0.2867 to 0.7421. These results indicate substantial improvement in simulation-to-field transfer following field calibration while retaining nonzero prediction error on unseen observations.
