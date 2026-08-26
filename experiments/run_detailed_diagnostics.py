import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from ml.enhanced_dataset_builder import EnhancedDatasetBuilder
from ml.cv import RollingOriginPurgedCV
from ml.scaling import Scaler
from ml.persistence import PersistenceModel
from ml.enhanced_bilstm import EnhancedBiLSTMModel

def get_confusion_matrix(y_true, y_pred, threshold=0.2025):
    true_pos = (y_true < threshold)
    pred_pos = (y_pred < threshold)
    
    tp = np.sum(true_pos & pred_pos)
    fp = np.sum(~true_pos & pred_pos)
    fn = np.sum(true_pos & ~pred_pos)
    tn = np.sum(~true_pos & ~pred_pos)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 1.0
    
    return tp, fp, fn, tn, precision, recall, f1

def run_diagnostics(epochs=20):
    print("=== STARTING DETAILED RUN 2B DIAGNOSTIC PIPELINE ===")
    np.random.seed(42)
    torch.manual_seed(42)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # 1. Load data
    builder_A = EnhancedDatasetBuilder('outputs/sensor_5min.parquet', target_zone='A', target_type='residual')
    dataset_A = builder_A.build_dataset()
    builder_B = EnhancedDatasetBuilder('outputs/sensor_5min.parquet', target_zone='B', target_type='residual')
    dataset_B = builder_B.build_dataset()
    
    features = dataset_A['feature_names_seq']
    theta_idx = features.index('theta_v')
    zone_flag_idx = features.index('zone_A_flag')
    
    # Concatenate & sort
    X_seq = np.concatenate([dataset_A['X_seq'], dataset_B['X_seq']], axis=0)
    X_rf = np.concatenate([dataset_A['X_rf'], dataset_B['X_rf']], axis=0)
    y_res = np.concatenate([dataset_A['y'], dataset_B['y']], axis=0)
    t_input = np.concatenate([dataset_A['t_input'], dataset_B['t_input']], axis=0)
    
    current_theta = X_seq[:, -1, theta_idx]
    y_abs = current_theta + y_res
    
    sort_idx = np.argsort(t_input)
    X_seq = X_seq[sort_idx]
    X_rf = X_rf[sort_idx]
    y_res = y_res[sort_idx]
    y_abs = y_abs[sort_idx]
    current_theta = current_theta[sort_idx]
    t_input = t_input[sort_idx]
    
    # Feature groups for permutation testing
    feature_groups = {
        'moisture': ['theta_v', 'delta_theta', 'rolling_mean_theta'],
        'rainfall': ['P', 'P_1h', 'P_6h', 'P_12h', 'P_24h', 'TSLR'],
        'radiation': ['Rs', 'Rs_1h', 'Rs_6h', 'Rs_24h', 'solar_zenith', 'solar_azimuth', 'solar_elevation'],
        'vpd': ['VPD', 'VPD_1h', 'VPD_6h', 'VPD_24h'],
        'soil_temp': ['Tsoil', 'delta_Tsoil'],
        'shade': ['shade_fraction', 'full_shade', 'mean_shade', 'fraction_shaded'],
        'gdd': ['GDD']
    }
    
    cv = RollingOriginPurgedCV(n_folds=5)
    
    # Reports list
    fold_reports = []
    
    # Loading 24h future rainfall
    df_raw = pd.read_parquet('outputs/sensor_5min.parquet')
    df_raw.set_index('timestamp', inplace=True)
    df_raw['P_24h_future'] = df_raw['P_B'].rolling(window=288, min_periods=1).sum().shift(-288)
    
    fold = 1
    for train_idx, val_idx in cv.split(t_input):
        print(f"\n--- FOLD {fold} DIAGNOSTICS ---")
        
        # Validation mask (strictly future Zone B only)
        val_zone_B_mask = (X_seq[val_idx, -1, zone_flag_idx] == 0.0)
        actual_val_idx = val_idx[val_zone_B_mask]
        
        X_seq_train = X_seq[train_idx]
        X_rf_train = X_rf[train_idx]
        y_train_res = y_res[train_idx]
        y_train_abs = y_abs[train_idx]
        c_train = current_theta[train_idx]
        
        X_seq_val = X_seq[actual_val_idx]
        X_rf_val = X_rf[actual_val_idx]
        y_val_res = y_res[actual_val_idx]
        y_val_abs = y_abs[actual_val_idx]
        c_val = current_theta[actual_val_idx]
        t_val = t_input[actual_val_idx]
        
        # Predictability: R2 of delta_theta using Linear and RF
        print("Checking linear and RF residual predictability...")
        # Flatten sequence to train tabular regressors
        # We take the last timestep features for tabular models, or flat sequence. Let's take last step.
        X_tab_train = X_seq_train[:, -1, :]
        X_tab_val = X_seq_val[:, -1, :]
        
        lr = LinearRegression()
        lr.fit(X_tab_train, y_train_res)
        lr_preds = lr.predict(X_tab_val)
        lr_r2 = r2_score(y_val_res, lr_preds)
        
        rf_tab = RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1)
        rf_tab.fit(X_tab_train, y_train_res)
        rf_preds = rf_tab.predict(X_tab_val)
        rf_r2 = r2_score(y_val_res, rf_preds)
        
        # Scale for BiLSTM
        scaler = Scaler()
        scaler.fit(X_seq_train, X_rf_train)
        X_seq_train_scaled, _ = scaler.transform(X_seq_train, X_rf_train)
        X_seq_val_scaled, _ = scaler.transform(X_seq_val, X_rf_val)
        
        # Train Enhanced BiLSTM
        print("Training Enhanced BiLSTM...")
        model = EnhancedBiLSTMModel(input_dim=X_seq.shape[2], device=device, target_type='residual')
        model.fit(X_seq_train_scaled, y_train_res, c_train, X_seq_val_scaled, y_val_res, c_val, epochs=epochs, patience=7)
        
        y_pred_abs, y_pred_res, gates = model.predict(X_seq_val_scaled, c_val)
        bilstm_r2 = r2_score(y_val_res, y_pred_res)
        
        # Persistence Baseline predictions
        y_pred_pers = c_val
        
        # Absolute RMSE comparison
        rmse_pers = np.sqrt(mean_squared_error(y_val_abs, y_pred_pers))
        rmse_enh = np.sqrt(mean_squared_error(y_val_abs, y_pred_abs))
        
        # Feature permutation tests
        print("Running feature permutation tests...")
        permutation_results = {}
        for group_name, feat_list in feature_groups.items():
            X_seq_val_shuffled = X_seq_val.copy()
            # Shuffle each matching feature channel
            for feat in feat_list:
                if feat in features:
                    f_idx = features.index(feat)
                    shuffled_channel = X_seq_val_shuffled[:, :, f_idx]
                    np.random.shuffle(shuffled_channel)
                    X_seq_val_shuffled[:, :, f_idx] = shuffled_channel
            
            # Predict
            X_seq_val_shuf_scaled, _ = scaler.transform(X_seq_val_shuffled, X_rf_val)
            pred_abs_shuf, _, _ = model.predict(X_seq_val_shuf_scaled, c_val)
            rmse_shuf = np.sqrt(mean_squared_error(y_val_abs, pred_abs_shuf))
            permutation_results[group_name] = rmse_shuf - rmse_enh
            
        # Direction accuracy: sign of (pred - c) vs sign of (true - c)
        true_delta = y_val_abs - c_val
        pred_delta = y_pred_abs - c_val
        # Only count steps where true change is non-zero to avoid division by zero or bias
        valid_change_mask = true_delta != 0
        if np.sum(valid_change_mask) > 0:
            dir_acc = np.mean((true_delta[valid_change_mask] * pred_delta[valid_change_mask]) > 0)
        else:
            dir_acc = np.nan
            
        # Confusion Matrices for Critical Events
        print("Analyzing critical event detection...")
        tp_m, fp_m, fn_m, tn_m, prec_m, rec_m, f1_m = get_confusion_matrix(y_val_abs, y_pred_abs)
        tp_p, fp_p, fn_p, tn_p, prec_p, rec_p, f1_p = get_confusion_matrix(y_val_abs, y_pred_pers)
        
        # Regime-wise analysis
        val_P24 = df_raw.loc[t_val, 'P_24h_future'].values
        dry_mask = val_P24 == 0
        rain_mask = val_P24 > 0
        boundary_mask = (0.195 < c_val) & (c_val < 0.230)
        
        def calc_rmse(true, pred):
            if len(true) == 0: return np.nan
            return np.sqrt(mean_squared_error(true, pred))
            
        regimes = {
            'Dry': (dry_mask, 'rain'),
            'Rain': (rain_mask, 'rain'),
            'Boundary': (boundary_mask, 'boundary')
        }
        
        regime_rmse = {}
        for r_name, (mask, _) in regimes.items():
            regime_rmse[f'{r_name}_Pers'] = calc_rmse(y_val_abs[mask], y_pred_pers[mask])
            regime_rmse[f'{r_name}_Enh'] = calc_rmse(y_val_abs[mask], y_pred_abs[mask])
            
        # Gate correlation to residual magnitude
        corr_gate_res = np.corrcoef(gates, np.abs(y_val_res))[0, 1] if len(gates) > 1 else np.nan
        
        # Save fold report
        fold_reports.append({
            'fold': fold,
            'lr_r2': lr_r2,
            'rf_r2': rf_r2,
            'bilstm_r2': bilstm_r2,
            'rmse_pers': rmse_pers,
            'rmse_enh': rmse_enh,
            'dir_acc': dir_acc,
            'corr_gate_res': corr_gate_res,
            'gate_mean': np.mean(gates),
            'gate_max': np.max(gates),
            'perm': permutation_results,
            'regimes': regime_rmse,
            'event_model': (tp_m, fp_m, fn_m, tn_m, prec_m, rec_m, f1_m),
            'event_pers': (tp_p, fp_p, fn_p, tn_p, prec_p, rec_p, f1_p)
        })
        
        fold += 1
        
    # Compile diagnostic output
    print("\n=== COMPILING DIAGNOSTIC REPORT ===")
    rep = "=== DETAILED DIAGNOSTICS REPORT ===\n\n"
    
    # 1. Residual distribution across the entire dataset
    rep += "### 1. True Residual (delta_theta_24h) Statistics\n"
    rep += f"Mean Residual: {np.mean(y_res):.6f}\n"
    rep += f"Std Residual: {np.std(y_res):.6f}\n"
    percentiles = [5, 25, 50, 75, 95]
    for p in percentiles:
        rep += f"P{p}: {np.percentile(y_res, p):.6f}\n"
    rep += "\n"
    
    # 2. Predictability of residuals
    rep += "### 2. Residual Predictability (R2 score on delta_theta_24h)\n"
    rep += "| Fold | Linear Regression R2 | Tabular Random Forest R2 | Enhanced BiLSTM R2 |\n"
    rep += "|---|---|---|---|\n"
    for r in fold_reports:
        rep += f"| Fold {r['fold']} | {r['lr_r2']:.4f} | {r['rf_r2']:.4f} | {r['bilstm_r2']:.4f} |\n"
    rep += "\n"
    
    # 3. Permutation feature importance
    rep += "### 3. Feature Permutation delta_RMSE (RMSE_permuted - RMSE_full)\n"
    rep += "Positive value means feature group is useful (disrupting it hurts prediction).\n\n"
    groups = list(feature_groups.keys())
    rep += "| Fold | " + " | ".join(groups) + " |\n"
    rep += "|---|" + "|".join(["---" for _ in groups]) + "|\n"
    for r in fold_reports:
        rep += f"| Fold {r['fold']} | " + " | ".join([f"{r['perm'][g]:.6f}" for g in groups]) + " |\n"
    rep += "\n"
    
    # 4. Event detection confusion matrices
    rep += "### 4. Critical Event Detection Confusion Matrices (Threshold < 0.2025)\n"
    rep += "Compare Enhanced BiLSTM with Persistence baseline:\n\n"
    rep += "| Fold | Model (TP, FP, FN, TN) | Model F1 | Pers (TP, FP, FN, TN) | Pers F1 |\n"
    rep += "|---|---|---|---|---|\n"
    for r in fold_reports:
        m = r['event_model']
        p = r['event_pers']
        rep += f"| Fold {r['fold']} | {m[0]}, {m[1]}, {m[2]}, {m[3]} | {m[6]:.4f} | {p[0]}, {p[1]}, {p[2]}, {p[3]} | {p[6]:.4f} |\n"
    rep += "\n"
    
    # 5. Regime-wise RMSE comparison
    rep += "### 5. Regime-wise RMSE Comparison\n"
    rep += "| Fold | Dry (Pers) | Dry (Enh) | Rain (Pers) | Rain (Enh) | Boundary (Pers) | Boundary (Enh) |\n"
    rep += "|---|---|---|---|---|---|---|\n"
    for r in fold_reports:
        reg = r['regimes']
        rep += f"| Fold {r['fold']} | {reg['Dry_Pers']:.5f} | {reg['Dry_Enh']:.5f} | {reg['Rain_Pers']:.5f} | {reg['Rain_Enh']:.5f} | {reg['Boundary_Pers']:.5f} | {reg['Boundary_Enh']:.5f} |\n"
    rep += "\n"
    
    # 6. Gate and Direction Analysis
    rep += "### 6. Gate & Direction Accuracy Analysis\n"
    rep += "| Fold | Gate Mean | Gate Max | Corr(g, |true_res|) | Direction Accuracy |\n"
    rep += "|---|---|---|---|---|\n"
    for r in fold_reports:
        rep += f"| Fold {r['fold']} | {r['gate_mean']:.4f} | {r['gate_max']:.4f} | {r['corr_gate_res']:.4f} | {r['dir_acc']:.4f} |\n"
    rep += "\n"
    
    print(rep)
    
    # Save report
    os.makedirs('outputs/diagnostics', exist_ok=True)
    with open('outputs/diagnostics/detailed_diagnostic_report.md', 'w') as f:
        f.write(rep)
        
    print("Detailed diagnostic report written to outputs/diagnostics/detailed_diagnostic_report.md")

if __name__ == '__main__':
    run_diagnostics(epochs=20)
