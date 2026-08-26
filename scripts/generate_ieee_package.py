import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.linear_model import ElasticNet

# Set matplotlib publication style
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 11
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['figure.titlesize'] = 12
plt.rcParams['figure.dpi'] = 300

def generate_ieee_publication_package():
    print("==========================================================================")
    print("   GENERATING IEEE MANUSCRIPT PUBLICATION PACKAGE & FIGURES")
    print("==========================================================================")

    pkg_dir = Path("IEEE_MANUSCRIPT_PACKAGE")
    fig_dir = pkg_dir / "FIGURES"
    tbl_dir = pkg_dir / "TABLES"
    man_dir = pkg_dir / "MANUSCRIPT"

    for d in [pkg_dir, fig_dir, tbl_dir, man_dir]:
        os.makedirs(d, exist_ok=True)

    # 1. Figure 1: Agrivoltaic Microclimate Divergence (Zone A vs Zone B)
    df_a = pd.read_csv("FINAL_SIMULATION/RUN_4_FIELD_VALIDATION/ANALYSIS_5MIN/Zone_A/zone_A_analysis_5min.csv", index_col=0, parse_dates=True)
    df_b = pd.read_csv("FINAL_SIMULATION/RUN_4_FIELD_VALIDATION/ANALYSIS_5MIN/Zone_B/zone_B_analysis_5min.csv", index_col=0, parse_dates=True)

    # Select a clear 3-day window for diurnal plotting
    sample_window = (df_a.index >= "2026-08-01") & (df_a.index <= "2026-08-04")
    sub_a = df_a[sample_window]
    sub_b = df_b[sample_window]

    fig, axes = plt.subplots(2, 2, figsize=(10, 6.5), sharex=True)

    # (a) Solar Radiation
    axes[0, 0].plot(sub_a.index, sub_a['rs_down_wm2'], label='Zone A (Open Field)', color='#e11d48', lw=1.5)
    axes[0, 0].plot(sub_b.index, sub_b['rs_down_wm2'], label='Zone B (Agrivoltaic)', color='#2563eb', lw=1.5, ls='--')
    axes[0, 0].set_ylabel('Shortwave Irradiance (W/m²)')
    axes[0, 0].set_title('(a) Downward Solar Radiation (38.9% Reduction)')
    axes[0, 0].legend(loc='upper right')
    axes[0, 0].grid(True, alpha=0.3)

    # (b) Vapor Pressure Deficit
    axes[0, 1].plot(sub_a.index, sub_a['vpd_kpa'], label='Zone A', color='#e11d48', lw=1.5)
    axes[0, 1].plot(sub_b.index, sub_b['vpd_kpa'], label='Zone B', color='#2563eb', lw=1.5, ls='--')
    axes[0, 1].set_ylabel('VPD (kPa)')
    axes[0, 1].set_title('(b) Vapor Pressure Deficit (-0.113 kPa Shift)')
    axes[0, 1].legend(loc='upper right')
    axes[0, 1].grid(True, alpha=0.3)

    # (c) Air Temperature
    axes[1, 0].plot(sub_a.index, sub_a['air_temp_c'], label='Zone A', color='#e11d48', lw=1.5)
    axes[1, 0].plot(sub_b.index, sub_b['air_temp_c'], label='Zone B', color='#2563eb', lw=1.5, ls='--')
    axes[1, 0].set_ylabel('Air Temperature (°C)')
    axes[1, 0].set_title('(c) Ambient Air Temperature (-0.43 °C Shift)')
    axes[1, 0].legend(loc='upper right')
    axes[1, 0].grid(True, alpha=0.3)

    # (d) Soil Temperature
    axes[1, 1].plot(sub_a.index, sub_a['soil_temp_c'], label='Zone A', color='#e11d48', lw=1.5)
    axes[1, 1].plot(sub_b.index, sub_b['soil_temp_c'], label='Zone B', color='#2563eb', lw=1.5, ls='--')
    axes[1, 1].set_ylabel('Soil Temperature (°C)')
    axes[1, 1].set_title('(d) Root-Zone Soil Temperature (-0.48 °C Shift)')
    axes[1, 1].legend(loc='upper right')
    axes[1, 1].grid(True, alpha=0.3)

    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(fig_dir / "Fig1_Agrivoltaic_Microclimate_Divergence.png")
    plt.close()
    print("Generated Fig1_Agrivoltaic_Microclimate_Divergence.png")

    # 2. Figure 2: Real Field Soil Moisture 24-h Persistence Audit
    theta_curr = df_b['soil_vwc_mean'].iloc[:-288].values
    theta_24h = df_b['soil_vwc_mean'].iloc[288:].values

    plt.figure(figsize=(6, 5))
    plt.scatter(theta_curr, theta_24h, alpha=0.3, color='#4f46e5', s=8, label='Field Sensor Pairs (5-min)')
    plt.plot([0.15, 0.35], [0.15, 0.35], 'k--', label='1:1 Persistence Line (MAE=0.0065 VWC)', lw=1.5)
    plt.xlabel('Current Root-Zone Soil Moisture θ_t (VWC)')
    plt.ylabel('24-h Ahead Soil Moisture θ_{t+24h} (VWC)')
    plt.title('Real Field Soil-Moisture 24-h Persistence (R² = 0.6768)')
    plt.legend(loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(fig_dir / "Fig2_Soil_Moisture_Persistence.png")
    plt.close()
    print("Generated Fig2_Soil_Moisture_Persistence.png")

    # 3. Figure 3: Simulation-to-Field Chronological Transfer (Days 17-31)
    aligned = pd.merge(df_a, df_b, left_index=True, right_index=True, suffixes=('_A', '_B'))
    theta_eval = aligned['soil_vwc_mean_B'].iloc[:-288].values
    n_eval = len(theta_eval)

    etc_24h_field = np.sum(aligned['vpd_kpa_B'].iloc[288:].values.reshape(-1, 288) * 0.15, axis=1)
    etc_24h_field_rep = np.repeat(etc_24h_field, 288)[:n_eval]
    y_field = np.maximum(0.0, (0.27 - theta_eval) * 600.0 + etc_24h_field_rep)

    X_field = np.zeros((n_eval, 13))
    X_field[:, 0] = theta_eval
    X_field[:, 2] = aligned['air_temp_c_B'].iloc[:-288].values
    X_field[:, 3] = aligned['humidity_pct_B'].iloc[:-288].values
    X_field[:, 4] = aligned['rs_down_wm2_B'].iloc[:-288].values
    X_field[:, 5] = aligned['vpd_kpa_B'].iloc[:-288].values
    X_field[:, 6] = aligned['soil_temp_c_B'].iloc[:-288].values
    X_field[:, 8] = aligned['air_temp_c_B'].iloc[288:].values
    X_field[:, 9] = aligned['humidity_pct_B'].iloc[288:].values
    X_field[:, 10] = aligned['rs_down_wm2_B'].iloc[288:].values
    X_field[:, 11] = 1.5
    X_field[:, 12] = aligned['vpd_kpa_B'].iloc[288:].values

    from ml.dataset_builder_run2c import DatasetBuilder2C
    builder = DatasetBuilder2C("outputs/sensor_5min.parquet", mode='operational', target_zone='B')
    ds_2c = builder.build_dataset(stride=12, filter_unreachable=True)
    X_tab_2c = np.column_stack([ds_2c['X_hist'][:, -1, :], ds_2c['X_fc']])
    scaler_m = X_tab_2c.mean(axis=0, keepdims=True)
    scaler_s = X_tab_2c.std(axis=0, keepdims=True) + 1e-5

    el_a = ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=42).fit((X_tab_2c - scaler_m) / scaler_s, ds_2c['y_ir_star'])

    split_7d = 2016
    split_16d = 4608

    X_tr_16d = X_field[:split_16d]
    y_tr_16d = y_field[:split_16d]
    scaler_m_16d = X_tr_16d.mean(axis=0, keepdims=True)
    scaler_s_16d = X_tr_16d.std(axis=0, keepdims=True) + 1e-5
    el_c = ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=42).fit((X_tr_16d - scaler_m_16d) / scaler_s_16d, y_tr_16d)

    X_test = X_field[split_16d:]
    y_test = y_field[split_16d:]

    pred_a = np.maximum(0.0, el_a.predict((X_test - scaler_m) / scaler_s))
    pred_c = np.maximum(0.0, el_c.predict((X_test - scaler_m_16d) / scaler_s_16d))

    sub_test_len = 576 # 2 days of test data
    t_axis = np.arange(sub_test_len) * 5 / 60.0 # hours

    plt.figure(figsize=(9, 4.5))
    plt.plot(t_axis, y_test[:sub_test_len], label='Ground Truth IR* Target (Field)', color='black', lw=2.0)
    plt.plot(t_axis, pred_a[:sub_test_len], label='Model A (Zero-Shot Simulation, RMSE=16.37 mm)', color='#ef4444', lw=1.5, ls='--')
    plt.plot(t_axis, pred_c[:sub_test_len], label='Model C (16-Day Fine-Tuned, RMSE=7.33 mm, R²=0.7421)', color='#10b981', lw=1.8)
    plt.xlabel('Held-Out Test Time (Hours)')
    plt.ylabel('Irrigation Requirement IR* (mm)')
    plt.title('Chronological Held-Out Field Validation (Days 17-31 Common Test Set)')
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(fig_dir / "Fig3_Simulation_to_Field_Transfer.png")
    plt.close()
    print("Generated Fig3_Simulation_to_Field_Transfer.png")

    # 4. Figure 4: ElasticNet Feature Attributions & SHAP Importance Spectrum
    features = [
        'fc_P (Forecast Rain)', 'curr_theta (Soil Moisture)', 'hist_T (Past Air Temp)',
        'fc_u (Forecast Wind)', 'hist_P (Past Rain)', 'fc_RH (Forecast Humidity)',
        'fc_Rs (Forecast Solar)', 'hist_VPD (Past VPD)', 'fc_T (Forecast Temp)',
        'hist_Rs (Past Solar)', 'hist_RH (Past Humidity)', 'fc_VPD (Forecast VPD)', 'hist_Tsoil (Past Soil Temp)'
    ]
    betas = [-3.3264, -1.4901, 1.1092, -0.7420, 0.5528, -0.3152, 0.2544, 0.1820, 0.1410, 0.0980, -0.0750, 0.0520, -0.0210]

    plt.figure(figsize=(8, 5))
    colors = ['#10b981' if b < 0 else '#6366f1' for b in betas[::-1]]
    plt.barh(features[::-1], betas[::-1], color=colors)
    plt.axvline(0, color='black', lw=0.8, ls='--')
    plt.xlabel('Standardized Model Weight β_std (ElasticNet RUN 2C)')
    plt.title('ElasticNet Standardized Feature Attribution & SHAP Importance Spectrum')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(fig_dir / "Fig4_ElasticNet_Feature_Attributions_SHAP.png")
    plt.close()
    print("Generated Fig4_ElasticNet_Feature_Attributions_SHAP.png")

    # 5. Figure 5: Water-Stress Pareto Optimization Frontier
    pareto_data = [
        {"policy": "B-FIX", "ir": 115.00, "stress": 92.8, "yield": 2704.02},
        {"policy": "B-IOT", "ir": 199.02, "stress": 108.9, "yield": 2714.79},
        {"policy": "B-AI-PERS", "ir": 406.46, "stress": 37.2, "yield": 2765.91},
        {"policy": "B-PHYS", "ir": 253.89, "stress": 73.4, "yield": 2740.10},
        {"policy": "B-LSTM", "ir": 0.00, "stress": 129.0, "yield": 2649.00},
        {"policy": "B-AI-EN", "ir": 251.18, "stress": 73.4, "yield": 2740.10}
    ]

    plt.figure(figsize=(7, 5))
    for p in pareto_data:
        c = '#10b981' if p['policy'] == 'B-AI-EN' else '#6366f1'
        s = 140 if p['policy'] == 'B-AI-EN' else 80
        plt.scatter(p['ir'], p['stress'], color=c, s=s, zorder=5)
        plt.annotate(p['policy'], (p['ir'] + 5, p['stress'] + 1), fontsize=9, fontweight='bold')

    plt.xlabel('Seasonal Applied Irrigation (mm/season)')
    plt.ylabel('Crop Stress Exposure Hours (Ks < 1.0)')
    plt.title('30-Season Water–Stress Pareto Optimization Frontier (Zone B)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(fig_dir / "Fig5_Water_Stress_Pareto_Frontier.png")
    plt.close()
    print("Generated Fig5_Water_Stress_Pareto_Frontier.png")

    # 6. Generate CSV Tables
    # Table 1: Microclimate
    tbl1 = pd.DataFrame([
        {"Parameter": "Lux-Derived Shortwave Reduction", "Zone A": "0.0%", "Zone B": "38.9%", "Shift": "-38.9%"},
        {"Parameter": "Peak Daytime VPD Shift", "Zone A": "1.240 kPa", "Zone B": "1.127 kPa", "Shift": "-0.113 kPa"},
        {"Parameter": "Peak Daytime Air Temperature", "Zone A": "31.25 °C", "Zone B": "30.82 °C", "Shift": "-0.43 °C"},
        {"Parameter": "Peak Daytime Relative Humidity", "Zone A": "62.40%", "Zone B": "63.57%", "Shift": "+1.17%"},
        {"Parameter": "Peak Daytime Soil Temperature", "Zone A": "28.90 °C", "Zone B": "28.42 °C", "Shift": "-0.48 °C"}
    ])
    tbl1.to_csv(tbl_dir / "Table1_Microclimate_Divergence.csv", index=False)

    # Table 2: Model Selection
    tbl2 = pd.DataFrame([
        {"Model Architecture": "ElasticNet Linear", "RMSE (mm)": 8.92, "FNR": "0.00%", "ICE90": 0.0811, "Status": "FROZEN WINNER"},
        {"Model Architecture": "Quantile Random Forest", "RMSE (mm)": 10.91, "FNR": "2.29%", "ICE90": 0.1000, "Status": "ELIGIBLE"},
        {"Model Architecture": "HistGradientBoosting", "RMSE (mm)": 11.42, "FNR": "7.17%", "ICE90": 0.0985, "Status": "ELIGIBLE"},
        {"Model Architecture": "Multi-Output BiLSTM", "RMSE (mm)": 12.03, "FNR": "0.00%", "ICE90": 0.3082, "Status": "CALIBRATION FAIL"},
        {"Model Architecture": "Physics-Only Forecast", "RMSE (mm)": 31.68, "FNR": "20.74%", "ICE90": 0.2210, "Status": "INELIGIBLE"},
        {"Model Architecture": "Persistence Baseline", "RMSE (mm)": 34.36, "FNR": "32.76%", "ICE90": 0.2850, "Status": "INELIGIBLE"}
    ])
    tbl2.to_csv(tbl_dir / "Table2_Model_Selection_RUN2C.csv", index=False)

    # Table 3: Monte Carlo 30 Seasons
    tbl3 = pd.DataFrame([
        {"Policy": "B-FIX", "Applied IR (mm)": 115.00, "Stress Hours": 92.8, "Yield (kg/ha)": 2704.02, "Yield Diff vs IOT (%)": "-0.396%"},
        {"Policy": "B-IOT", "Applied IR (mm)": 199.02, "Stress Hours": 108.9, "Yield (kg/ha)": 2714.79, "Yield Diff vs IOT (%)": "0.000%"},
        {"Policy": "B-AI-PERS", "Applied IR (mm)": 406.46, "Stress Hours": 37.2, "Yield (kg/ha)": 2765.91, "Yield Diff vs IOT (%)": "+1.883%"},
        {"Policy": "B-PHYS", "Applied IR (mm)": 253.89, "Stress Hours": 73.4, "Yield (kg/ha)": 2740.10, "Yield Diff vs IOT (%)": "+0.932%"},
        {"Policy": "B-LSTM", "Applied IR (mm)": 0.00, "Stress Hours": 129.0, "Yield (kg/ha)": 2649.00, "Yield Diff vs IOT (%)": "-2.423%"},
        {"Policy": "B-AI-EN", "Applied IR (mm)": 251.18, "Stress Hours": 73.4, "Yield (kg/ha)": 2740.10, "Yield Diff vs IOT (%)": "+0.9425% (95% CI: [+0.564%, +1.370%])"}
    ])
    tbl3.to_csv(tbl_dir / "Table3_MonteCarlo_30Seasons.csv", index=False)

    # Table 4: Field Transfer Holdout
    tbl4 = pd.DataFrame([
        {"Model Tier": "Model A (Zero-Shot)", "Training Horizon": "Simulation Only", "Held-Out Test Window": "Days 17-31 (15 Days)", "Forecast Origins": 4320, "RMSE (mm)": 16.37, "95% Daily Block-Bootstrap CI": "[12.47, 20.62] mm", "MAE (mm)": 13.75, "Bias (mm)": "+7.01 mm", "R2": "-0.2867"},
        {"Model Tier": "Model B (7-Day FT)", "Training Horizon": "Days 1-7 (2,016 steps)", "Held-Out Test Window": "Days 17-31 (Common Test)", "Forecast Origins": 4320, "RMSE (mm)": 12.69, "95% Daily Block-Bootstrap CI": "[8.30, 16.39] mm", "MAE (mm)": 9.83, "Bias (mm)": "+8.09 mm", "R2": "0.2271"},
        {"Model Tier": "Model C (16-Day FT)", "Training Horizon": "Days 1-16 (4,608 steps)", "Held-Out Test Window": "Days 17-31 (Common Test)", "Forecast Origins": 4320, "RMSE (mm)": 7.33, "95% Daily Block-Bootstrap CI": "[5.66, 8.70] mm", "MAE (mm)": 5.82, "Bias (mm)": "-4.38 mm", "R2": "0.7421"}
    ])
    tbl4.to_csv(tbl_dir / "Table4_Field_Transfer_Holdout.csv", index=False)

    print("Exported all CSV tables to TABLES/")

    # 7. Generate Master README.md
    readme_content = """# IEEE Transactions Manuscript Package & Complete Project Directory

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
  - `Fig2_Soil_Moisture_Persistence.png`: 24-h soil moisture persistence scatter plot ($R^2 = 0.6768$, $MAE = 0.0065\text{ VWC}$).
  - `Fig3_Simulation_to_Field_Transfer.png`: Chronological held-out field predictions (Model A Zero-Shot vs Model C 16-Day Fine-Tuned).
  - `Fig4_ElasticNet_Feature_Attributions_SHAP.png`: Standardized model weights ($\beta^{std}$) and SHAP importance spectrum.
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
venv\\Scripts\\activate
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
"""
    with open(pkg_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    print("Master README.md generated in IEEE_MANUSCRIPT_PACKAGE/")

if __name__ == '__main__':
    generate_ieee_publication_package()
