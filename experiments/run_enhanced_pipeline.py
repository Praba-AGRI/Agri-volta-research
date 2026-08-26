import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import shutil
import numpy as np
import pandas as pd
import torch
import joblib
from collections import defaultdict
from sklearn.metrics import mean_squared_error
from ml.enhanced_dataset_builder import EnhancedDatasetBuilder
from ml.cv import RollingOriginPurgedCV
from ml.scaling import Scaler
from ml.persistence import PersistenceModel
from ml.random_forest import RFModel
from ml.enhanced_bilstm import EnhancedBiLSTMModel
from ml.bilstm import BiLSTMModel

def inner_cv_split(train_indices, n_folds=3, purge_size=576):
    N = len(train_indices)
    chunk_size = N // (n_folds + 1)
    for fold in range(n_folds):
        val_start = (fold + 1) * chunk_size
        val_end = (fold + 2) * chunk_size if fold < n_folds - 1 else N
        train_end = val_start - purge_size
        if train_end <= 0:
            continue
        yield train_indices[:train_end], train_indices[val_start:val_end]

def compute_event_metrics(y_true, y_pred, threshold=0.2025):
    # Detect contiguous events where theta < threshold
    true_event = y_true < threshold
    pred_event = y_pred < threshold
    
    # Event-level recall & precision
    # Define an event as a contiguous block of True
    def get_events(mask):
        events = []
        in_event = False
        start = 0
        for idx, val in enumerate(mask):
            if val and not in_event:
                start = idx
                in_event = True
            elif not val and in_event:
                events.append((start, idx - 1))
                in_event = False
        if in_event:
            events.append((start, len(mask) - 1))
        return events
        
    true_events = get_events(true_event)
    pred_events = get_events(pred_event)
    
    # TP: True event overlapped by at least one Predicted event
    tp = 0
    fn = 0
    for ts, te in true_events:
        overlap = False
        for ps, pe in pred_events:
            if max(ts, ps) <= min(te, pe):
                overlap = True
                break
        if overlap:
            tp += 1
        else:
            fn += 1
            
    # FP: Predicted event that does not overlap any True event
    fp = 0
    for ps, pe in pred_events:
        overlap = False
        for ts, te in true_events:
            if max(ts, ps) <= min(te, pe):
                overlap = True
                break
        if not overlap:
            fp += 1
            
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0
    
    return {
        'Precision': precision,
        'Recall': recall,
        'F1': f1,
        'TP_Events': tp,
        'FP_Events': fp,
        'FN_Events': fn
    }

def run_enhanced_pipeline(epochs=20):
    print("=== STARTING RUN 2B: ENHANCED BiLSTM DEVELOPMENT ===")
    np.random.seed(42)
    torch.manual_seed(42)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")
    
    # Define paths
    output_dir = "outputs/RUN_2B_ENHANCED"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Load joint dual-zone dataset
    # We will build datasets for Zone A and Zone B
    print("Building datasets...")
    builder_A = EnhancedDatasetBuilder('outputs/sensor_5min.parquet', target_zone='A', target_type='residual')
    dataset_A = builder_A.build_dataset()
    
    builder_B = EnhancedDatasetBuilder('outputs/sensor_5min.parquet', target_zone='B', target_type='residual')
    dataset_B = builder_B.build_dataset()
    
    features = dataset_A['feature_names_seq']
    theta_idx = features.index('theta_v')
    zone_flag_idx = features.index('zone_A_flag')
    
    # Concatenate datasets
    X_seq = np.concatenate([dataset_A['X_seq'], dataset_B['X_seq']], axis=0)
    X_rf = np.concatenate([dataset_A['X_rf'], dataset_B['X_rf']], axis=0)
    y_res = np.concatenate([dataset_A['y'], dataset_B['y']], axis=0)
    t_input = np.concatenate([dataset_A['t_input'], dataset_B['t_input']], axis=0)
    
    # Reconstruct absolute y targets
    current_theta = X_seq[:, -1, theta_idx]
    y_abs = current_theta + y_res
    
    # Sort temporally
    sort_idx = np.argsort(t_input)
    X_seq = X_seq[sort_idx]
    X_rf = X_rf[sort_idx]
    y_res = y_res[sort_idx]
    y_abs = y_abs[sort_idx]
    current_theta = current_theta[sort_idx]
    t_input = t_input[sort_idx]
    
    # Define Outer CV (Purged Rolling Origin)
    cv = RollingOriginPurgedCV(n_folds=5)
    
    fold_results = []
    transfer_results = []
    shuffled_results = []
    
    # Collect gate statistics
    gate_values = []
    gate_rain = []
    gate_dry = []
    gate_boundary = []
    
    # Collect rain metrics
    # Load 24h future rainfall
    df_raw = pd.read_parquet('outputs/sensor_5min.parquet')
    df_raw.set_index('timestamp', inplace=True)
    df_raw['P_24h_future'] = df_raw['P_B'].rolling(window=288, min_periods=1).sum().shift(-288)
    
    fold = 1
    for train_idx, val_idx in cv.split(t_input):
        print(f"\n--- FOLD {fold} ---")
        
        # 1. Leak-Free validation masking (strictly future Zone B only)
        val_zone_B_mask = (X_seq[val_idx, -1, zone_flag_idx] == 0.0)
        actual_val_idx = val_idx[val_zone_B_mask]
        
        if len(actual_val_idx) == 0:
            print(f"Skipping fold {fold} - no Zone B validation samples.")
            continue
            
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
        
        # Scale
        scaler = Scaler()
        scaler.fit(X_seq_train, X_rf_train)
        X_seq_train_scaled, X_rf_train_scaled = scaler.transform(X_seq_train, X_rf_train)
        X_seq_val_scaled, X_rf_val_scaled = scaler.transform(X_seq_val, X_rf_val)
        
        # Outer Persistence Baseline
        pers_model = PersistenceModel()
        y_pred_pers = pers_model.predict_from_current(c_val)
        pers_eval = pers_model.evaluate(y_val_abs, y_pred_pers)
        rmse_pers = pers_eval['RMSE']
        
        # Outer Random Forest Baseline
        rf = RFModel()
        rf.fit(X_rf_train_scaled, y_train_abs)
        y_pred_rf = rf.predict(X_rf_val_scaled)
        rf_eval = rf.evaluate(y_val_abs, y_pred_rf, rmse_pers)
        
        # Outer Original BiLSTM Baseline
        orig_bilstm = BiLSTMModel(input_dim=X_seq_train.shape[2], device=device)
        orig_bilstm.fit(X_seq_train_scaled, y_train_abs, epochs=epochs, batch_size=64, patience=5)
        y_pred_orig = orig_bilstm.predict(X_seq_val_scaled)
        orig_eval = orig_bilstm.evaluate(y_val_abs, y_pred_orig, rmse_pers)
        
        # 2. NESTED CV: Target Selection (Absolute vs Residual)
        print("Running nested Inner CV for target selection...")
        inner_cv = inner_cv_split(train_idx)
        inner_rmse_abs = []
        inner_rmse_res = []
        
        for i_train, i_val in inner_cv:
            # Scale inner
            inner_scaler = Scaler()
            inner_scaler.fit(X_seq[i_train], X_rf[i_train])
            X_it_scaled, _ = inner_scaler.transform(X_seq[i_train], X_rf[i_train])
            X_iv_scaled, _ = inner_scaler.transform(X_seq[i_val], X_rf[i_val])
            
            # Inner Absolute Model
            m_abs = EnhancedBiLSTMModel(input_dim=X_seq.shape[2], device=device, target_type='absolute')
            m_abs.fit(X_it_scaled, y_abs[i_train], current_theta[i_train], X_iv_scaled, y_abs[i_val], current_theta[i_val], epochs=10, patience=3)
            pred_abs, _, _ = m_abs.predict(X_iv_scaled, current_theta[i_val])
            inner_rmse_abs.append(np.sqrt(mean_squared_error(y_abs[i_val], pred_abs)))
            
            # Inner Residual Model
            m_res = EnhancedBiLSTMModel(input_dim=X_seq.shape[2], device=device, target_type='residual')
            m_res.fit(X_it_scaled, y_res[i_train], current_theta[i_train], X_iv_scaled, y_res[i_val], current_theta[i_val], epochs=10, patience=3)
            pred_res_abs, _, _ = m_res.predict(X_iv_scaled, current_theta[i_val])
            inner_rmse_res.append(np.sqrt(mean_squared_error(y_abs[i_val], pred_res_abs)))
            
        mean_inner_abs = np.mean(inner_rmse_abs)
        mean_inner_res = np.mean(inner_rmse_res)
        print(f"Inner CV RMSE - Absolute Target: {mean_inner_abs:.5f}, Residual Target: {mean_inner_res:.5f}")
        
        selected_target = 'residual' if mean_inner_res <= mean_inner_abs else 'absolute'
        print(f"Selected formulation for Fold {fold}: {selected_target.upper()}")
        
        # Train chosen configuration on complete outer training set
        enhanced_model = EnhancedBiLSTMModel(input_dim=X_seq_train.shape[2], device=device, target_type=selected_target)
        target_train = y_train_res if selected_target == 'residual' else y_train_abs
        target_val = y_val_res if selected_target == 'residual' else y_val_abs
        
        enhanced_model.fit(X_seq_train_scaled, target_train, c_train, X_seq_val_scaled, target_val, c_val, epochs=epochs, patience=7)
        
        # Predict on outer validation
        y_pred_enh, y_pred_res_val, gates = enhanced_model.predict(X_seq_val_scaled, c_val)
        enh_eval = enhanced_model.evaluate(y_val_abs, y_pred_enh, rmse_pers)
        
        # Record gate values
        gate_values.extend(gates)
        # Look up rain at these timestamps
        val_P24 = df_raw.loc[t_val, 'P_24h_future'].values
        for g, rain, moist in zip(gates, val_P24, c_val):
            if rain > 0:
                gate_rain.append(g)
            else:
                gate_dry.append(g)
            if 0.195 < moist < 0.230:
                gate_boundary.append(g)
                
        # Direction accuracy: sign of (pred - c) vs sign of (true - c)
        true_delta = y_val_abs - c_val
        pred_delta = y_pred_enh - c_val
        dir_acc = np.mean((true_delta * pred_delta) > 0)
        
        # Event metrics
        event_metrics = compute_event_metrics(y_val_abs, y_pred_enh)
        
        # Record fold metrics
        fold_results.append({
            'Fold': fold,
            'Selected_Target': selected_target,
            'Pers_RMSE': rmse_pers, 'Pers_MAE': pers_eval['MAE'],
            'RF_RMSE': rf_eval['RMSE'], 'RF_MAE': rf_eval['MAE'], 'RF_Skill': rf_eval['Skill'],
            'Orig_RMSE': orig_eval['RMSE'], 'Orig_MAE': orig_eval['MAE'], 'Orig_Skill': orig_eval['Skill'],
            'Enh_RMSE': enh_eval['RMSE'], 'Enh_MAE': enh_eval['MAE'], 'Enh_Skill': enh_eval['Skill'],
            'Direction_Accuracy': dir_acc,
            'Event_F1': event_metrics['F1'],
            'Event_Recall': event_metrics['Recall'],
            'Event_Precision': event_metrics['Precision']
        })
        
        # 3. Secondary transfer diagnostic: Zone A historical -> future Zone B
        print("Running transfer diagnostic (Zone A -> Zone B)...")
        # Keep only Zone A training indices
        train_zone_A_mask = (X_seq[train_idx, -1, zone_flag_idx] == 1.0)
        transfer_train_idx = train_idx[train_zone_A_mask]
        
        X_seq_train_A = X_seq[transfer_train_idx]
        X_rf_train_A = X_rf[transfer_train_idx]
        y_train_res_A = y_res[transfer_train_idx]
        y_train_abs_A = y_abs[transfer_train_idx]
        c_train_A = current_theta[transfer_train_idx]
        
        scaler_A = Scaler()
        scaler_A.fit(X_seq_train_A, X_rf_train_A)
        X_seq_train_scaled_A, _ = scaler_A.transform(X_seq_train_A, X_rf_train_A)
        X_seq_val_scaled_A, _ = scaler_A.transform(X_seq_val, X_rf_val)
        
        transfer_model = EnhancedBiLSTMModel(input_dim=X_seq_train.shape[2], device=device, target_type=selected_target)
        target_train_A = y_train_res_A if selected_target == 'residual' else y_train_abs_A
        transfer_model.fit(X_seq_train_scaled_A, target_train_A, c_train_A, epochs=epochs, patience=7)
        y_pred_trans, _, _ = transfer_model.predict(X_seq_val_scaled_A, c_val)
        trans_rmse = np.sqrt(mean_squared_error(y_val_abs, y_pred_trans))
        
        transfer_results.append({
            'Fold': fold,
            'Transfer_RMSE': trans_rmse,
            'Transfer_Skill': 1.0 - (trans_rmse / rmse_pers)
        })
        
        # 4. Control diagnostic: Shuffled microclimate features
        print("Running shuffled microclimate control...")
        X_seq_val_shuffled = X_seq_val.copy()
        # Shuffled features: T, RH, Tsoil, Rs, shade_fraction, VPD
        shuffle_vars = ['T', 'RH', 'Tsoil', 'Rs', 'shade_fraction', 'VPD']
        for var in shuffle_vars:
            if var in features:
                idx = features.index(var)
                # Shuffle across validation samples for this channel
                shuffled_channel = X_seq_val_shuffled[:, :, idx]
                np.random.shuffle(shuffled_channel)
                X_seq_val_shuffled[:, :, idx] = shuffled_channel
                
        _, X_rf_val_shuffled = scaler.transform(X_seq_val_shuffled, X_rf_val) # dummy scaling
        X_seq_val_shuffled_scaled, _ = scaler.transform(X_seq_val_shuffled, X_rf_val)
        
        y_pred_shuf, _, _ = enhanced_model.predict(X_seq_val_shuffled_scaled, c_val)
        shuf_rmse = np.sqrt(mean_squared_error(y_val_abs, y_pred_shuf))
        shuffled_results.append({
            'Fold': fold,
            'Shuffled_RMSE': shuf_rmse,
            'Shuffled_Skill': 1.0 - (shuf_rmse / rmse_pers)
        })
        
        fold += 1
        
    # Save statistics and summaries
    df_folds = pd.DataFrame(fold_results)
    df_folds.to_csv(os.path.join(output_dir, 'run2b_fold_results.csv'), index=False)
    
    df_trans = pd.DataFrame(transfer_results)
    df_trans.to_csv(os.path.join(output_dir, 'run2b_transfer_diagnostic.csv'), index=False)
    
    df_shuf = pd.DataFrame(shuffled_results)
    df_shuf.to_csv(os.path.join(output_dir, 'run2b_shuffled_diagnostic.csv'), index=False)
    
    # Compile Summary
    summary_data = {
        'Metric': ['Pers_RMSE', 'RF_RMSE', 'Orig_RMSE', 'Enh_RMSE', 'Transfer_RMSE', 'Shuffled_RMSE', 'Enh_Skill', 'Direction_Accuracy'],
        'Mean': [
            df_folds['Pers_RMSE'].mean(), df_folds['RF_RMSE'].mean(), df_folds['Orig_RMSE'].mean(), df_folds['Enh_RMSE'].mean(),
            df_trans['Transfer_RMSE'].mean(), df_shuf['Shuffled_RMSE'].mean(), df_folds['Enh_Skill'].mean(), df_folds['Direction_Accuracy'].mean()
        ],
        'SD': [
            df_folds['Pers_RMSE'].std(), df_folds['RF_RMSE'].std(), df_folds['Orig_RMSE'].std(), df_folds['Enh_RMSE'].std(),
            df_trans['Transfer_RMSE'].std(), df_shuf['Shuffled_RMSE'].std(), df_folds['Enh_Skill'].std(), df_folds['Direction_Accuracy'].std()
        ]
    }
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_csv(os.path.join(output_dir, 'run2b_summary.csv'), index=False)
    
    # Gate stats compilation
    gate_values = np.array(gate_values)
    gate_report = {
        'overall_mean': np.mean(gate_values),
        'overall_std': np.std(gate_values),
        'p5': np.percentile(gate_values, 5),
        'p95': np.percentile(gate_values, 95),
        'rain_mean': np.mean(gate_rain) if gate_rain else np.nan,
        'dry_mean': np.mean(gate_dry) if gate_dry else np.nan,
        'boundary_mean': np.mean(gate_boundary) if gate_boundary else np.nan
    }
    pd.DataFrame([gate_report]).T.to_csv(os.path.join(output_dir, 'run2b_gate_analysis.csv'))
    
    # Generate Markdown Report
    report = "# RUN 2B - Enhanced BiLSTM Development Report\n\n"
    report += "### Summary statistics (5-Fold CV)\n"
    report += df_summary.to_markdown(index=False) + "\n\n"
    
    report += "### Gate Distribution Analysis\n"
    for k, v in gate_report.items():
        report += f"- **{k}**: {v:.4f}\n"
    report += "\n"
    
    report += "### Event-Level Performance (Threshold < 0.2025)\n"
    report += f"- Mean Critical Recall: {df_folds['Event_Recall'].mean():.4f}\n"
    report += f"- Mean Critical Precision: {df_folds['Event_Precision'].mean():.4f}\n"
    report += f"- Mean Critical F1: {df_folds['Event_F1'].mean():.4f}\n\n"
    
    report_file = os.path.join(output_dir, 'run2b_report.md')
    with open(report_file, 'w') as f:
        f.write(report)
        
    # Copy report to current conversation directory for user visibility
    shutil.copy(report_file, 'C:/Users/Prabakaran/.gemini/antigravity-ide/brain/bf797b32-67f3-459c-aa7c-c2021d4f5291/run2b_report.md')
    
    print("RUN 2B pipeline completed successfully.")

if __name__ == '__main__':
    run_enhanced_pipeline(epochs=20)
