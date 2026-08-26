# IEEE Transactions Manuscript Package & Complete Project Directory

This repository contains the complete research software, physical environmental simulation, safety-constrained forecasting framework, 30-season Monte Carlo closed-loop evaluation, and 32-calendar-day physical field validation package for smart agrivoltaic irrigation control.

---

## 📌 Executive Sitemap & Research Pipeline

```text
RUN 1: Environmental & Agronomic Physics Simulation
       ↓ (Microclimate, PV panel shading attenuation, FAO-56 crop response)
RUN 2: 24-h Soil-Moisture Forecasting Benchmark
       ↓ (Soil moisture is highly autocorrelated; Persistence > RF > BiLSTM)
RUN 2B: Residual Predictability Diagnostics
       ↓ (Proves delta_theta_24h residual is near-zero and intrinsically un-predictable)
RUN 2C: 24-h Irrigation-Requirement Forecasting
       ↓ (Target reformulated to physical minimum sufficient irrigation IR*; ElasticNet winner)
RUN 3A: Single-Season Mechanistic Closed-Loop Demonstration
       ↓ (Proves ElasticNet triggers targeted events eliminating stress during dry spells)
RUN 3B-EN: 30-Season Paired Monte Carlo Evaluation
       ↓ (N=30 paired seasons; ElasticNet matches physics policy, reduces IR by 38.2% vs Persistence)
RUN 4A-4E: Real Field Sensor Campaign, Timestamp-QC, 5-Minute Resampling & Chronological Held-Out Validation
       ↓ (46,080 raw 2-min observations -> 18,432 5-min analytical observations; 38.9% shortwave reduction; Model C achieves 7.33mm RMSE, R2 = 0.7421 on 4,320 forecast origins across Days 17-31)
```

---

## 📁 Publication Package Structure

- **`IEEE_MANUSCRIPT_PACKAGE/FIGURES/`**:
  - `Fig1_Agrivoltaic_Microclimate_Divergence.png`: Diurnal microclimate comparison (Zone A Open Field vs Zone B Agrivoltaic).
  - `Fig2_Soil_Moisture_Persistence.png`: 24-h soil moisture persistence scatter plot ($R^2 = 0.6768$, $MAE = 0.0065	ext{ VWC}$).
  - `Fig3_Simulation_to_Field_Transfer.png`: Chronological held-out field predictions (Model A Zero-Shot vs Model C 16-Day Fine-Tuned).
  - `Fig4_ElasticNet_Feature_Attributions_SHAP.png`: Standardized model weights ($eta^{std}$) and SHAP importance spectrum.
  - `Fig5_Water_Stress_Pareto_Frontier.png`: 30-season Monte Carlo Pareto optimization frontier across 6 policies.
- **`IEEE_MANUSCRIPT_PACKAGE/TABLES/`**:
  - `Table1_Microclimate_Divergence.csv`: Microclimate shifts under PV panels.
  - `Table2_Model_Selection_RUN2C.csv`: RUN 2C nested temporal CV model comparison.
  - `Table3_MonteCarlo_30Seasons.csv`: 30-season policy comparison metrics & bootstrapped yield differences.
  - `Table4_Field_Transfer_Holdout.csv`: Chronological held-out transfer evaluation metrics & daily-block bootstrap 95% CIs.
- **`IEEE_MANUSCRIPT_PACKAGE/MANUSCRIPT/`**:
  - `IEEE_Transactions_Manuscript.md`: Complete IEEE Transactions LaTeX-ready manuscript markdown text.

---

## 🛠️ Reproduction Instructions

### 1. Environment Setup
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Execute Full Research Pipeline
```bash
python experiments/run_experiment_1_simulation.py
python experiments/run_experiment_2c_ir.py
python experiments/run_experiment_3b_mc.py
python experiments/run_field_provenance_pipeline.py
python scripts/generate_ieee_package.py
```

---

## 📜 Manuscript Summary Abstract

RUN 4 demonstrated simulation-to-field transfer using chronologically held-out field observations. A 32-calendar-day field campaign generated 46,080 raw 2-minute sensor observations, which underwent timestamp quality control and deterministic resampling to 18,432 five-minute analytical observations. The common held-out evaluation comprised 4,320 forecast origins across 15 complete daily blocks (Days 17–31), with each origin evaluated against its corresponding 24-h-ahead irrigation-requirement target. Relative to the simulation-only model, 16-day field fine-tuning reduced held-out RMSE from 16.37 to 7.33 mm, corresponding to a 55.2% reduction. The paired daily-block bootstrap 95% confidence interval for the RMSE difference was −14.49 to −4.30 mm. MAE decreased from 13.75 to 5.82 mm, while test-set R² improved from −0.2867 to 0.7421. These results indicate substantial improvement in simulation-to-field transfer following field calibration while retaining nonzero prediction error on unseen observations.
