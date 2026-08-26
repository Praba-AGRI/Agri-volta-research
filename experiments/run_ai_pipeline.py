import os
import pandas as pd
import numpy as np
import torch
from collections import defaultdict
from ml.dataset_builder import DatasetBuilder
from ml.cv import RollingOriginPurgedCV
from ml.scaling import Scaler
from ml.persistence import PersistenceModel
from ml.random_forest import RFModel
from ml.bilstm import BiLSTMModel
from ml.uncertainty import execute_shap

def run_pipeline(epochs=1, output_prefix="run2"):
    np.random.seed(42)
    torch.manual_seed(42)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}\n")
    
    # --- 1. Dataset Construction & Sample Accounting ---
    print("Building datasets...")
    # Raw counts are known: 70 days * 24 h * 12 = 20160
    raw_A = 20160
    raw_B = 20160
    
    builder_A = DatasetBuilder('outputs/sensor_5min.parquet', target_zone='A')
    dataset_A = builder_A.build_dataset()
    
    builder_B = DatasetBuilder('outputs/sensor_5min.parquet', target_zone='B')
    dataset_B = builder_B.build_dataset()
    
    # Calculate losses implicitly
    final_A = len(dataset_A['y'])
    final_B = len(dataset_B['y'])
    loss_A = raw_A - final_A
    loss_B = raw_B - final_B
    
    accounting = {
        'Raw 5-min records': [raw_A, raw_B, raw_A + raw_B],
        'Removed': [loss_A, loss_B, loss_A + loss_B],
        'Final ML samples': [final_A, final_B, final_A + final_B]
    }
    
    X_seq = np.concatenate([dataset_A['X_seq'], dataset_B['X_seq']], axis=0)
    X_rf = np.concatenate([dataset_A['X_rf'], dataset_B['X_rf']], axis=0)
    y = np.concatenate([dataset_A['y'], dataset_B['y']], axis=0)
    t_input = np.concatenate([dataset_A['t_input'], dataset_B['t_input']], axis=0)
    features = dataset_A['feature_names_seq']
    
    sort_idx = np.argsort(t_input)
    X_seq = X_seq[sort_idx]
    X_rf = X_rf[sort_idx]
    y = y[sort_idx]
    t_input = t_input[sort_idx]
    
    cv = RollingOriginPurgedCV(n_folds=5, forecast_horizon=288, input_window=288)
    
    fold_results = []
    
    # Track latest fold data for final analysis
    last_bilstm = None
    last_X_seq_train = None
    last_X_seq_val = None
    
    # Bounds for violations
    theta_wp = 0.15
    theta_fc = 0.35
    
    print("\nStarting Training...", flush=True)
    fold = 1
    for train_idx, val_idx in cv.split(t_input):
        accounting[f'Fold {fold} Train'] = [0, 0, len(train_idx)]
        accounting[f'Fold {fold} Val'] = [0, 0, len(val_idx)]
        
        X_seq_train, X_seq_val = X_seq[train_idx], X_seq[val_idx]
        X_rf_train, X_rf_val = X_rf[train_idx], X_rf[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        
        # 1. Persistence
        print(f"\n--- FOLD {fold} ---", flush=True)
        from ml.persistence import PersistenceModel
        theta_idx = features.index('theta_v')
        
        # EXTRACT UNSCALED CURRENT THETA BEFORE SCALING
        current_theta_unscaled = X_seq[val_idx][:, -1, theta_idx]
        
        scaler = Scaler()
        scaler.fit(X_seq_train, X_rf_train)
        X_seq_train, X_rf_train = scaler.transform(X_seq_train, X_rf_train)
        X_seq_val, X_rf_val = scaler.transform(X_seq_val, X_rf_val)
        
        if fold == 1:
            print("\n--- FIX 2: Target Representation & Provenance ---", flush=True)
            print(f"Target representation: Raw physical fraction (VWC)")
            print(f"Target scaling applied during training: None (y_train is passed directly)")
            print(f"Current_theta scaling: Extracted from unscaled X_seq")
            
            print("\n--- FIX 1: Unit Provenance (Fold 1) ---", flush=True)
            print(f"theta target min: {np.min(y_val):.4f}")
            print(f"theta target max: {np.max(y_val):.4f}")
            print(f"theta target mean: {np.mean(y_val):.4f}")
            print(f"theta target std: {np.std(y_val):.4f}")
        
        pers_model = PersistenceModel()
        y_pred_pers = pers_model.predict_from_current(current_theta_unscaled)
        
        if fold == 1:
            print(f"persistence prediction min: {np.min(y_pred_pers):.4f}")
            print(f"persistence prediction max: {np.max(y_pred_pers):.4f}")
            
        pers_eval = pers_model.evaluate(y_val, y_pred_pers)
        rmse_pers = pers_eval['RMSE']
        mae_pers = pers_eval['MAE']
        
        # 2. Random Forest
        rf = RFModel()
        rf.fit(X_rf_train, y_train)
        y_pred_rf = rf.predict(X_rf_val)
        
        if fold == 1:
            print(f"RF prediction min: {np.min(y_pred_rf):.4f}")
            print(f"RF prediction max: {np.max(y_pred_rf):.4f}")
            
        rf_eval = rf.evaluate(y_val, y_pred_rf, rmse_pers)
        
        # 3. BiLSTM
        bilstm = BiLSTMModel(input_dim=X_seq.shape[2], device=device)
        bilstm.fit(X_seq_train, y_train, X_val=X_seq_val, y_val=y_val, epochs=epochs)
        y_pred_lstm = bilstm.predict(X_seq_val)
        
        if fold == 1:
            print(f"LSTM prediction min: {np.min(y_pred_lstm):.4f}")
            print(f"LSTM prediction max: {np.max(y_pred_lstm):.4f}")
            
        lstm_eval = bilstm.evaluate(y_val, y_pred_lstm, rmse_pers)
        
        # Bounds violations
        violations_low = np.sum(y_pred_lstm < theta_wp)
        violations_high = np.sum(y_pred_lstm > theta_fc)
        v_rate = (violations_low + violations_high) / len(y_pred_lstm) * 100
        
        
        # Save last fold for post-hoc analysis
        last_bilstm = bilstm
        last_X_seq_train = X_seq_train
        last_X_seq_val = X_seq_val
        
        # Save fold metrics
        fold_results.append({
            'Fold': fold,
            'Pers_RMSE': rmse_pers, 'Pers_MAE': mae_pers,
            'RF_RMSE': rf_eval['RMSE'], 'RF_Skill': rf_eval['Skill'],
            'LSTM_RMSE': lstm_eval['RMSE'], 'LSTM_MAE': lstm_eval['MAE'], 'LSTM_Skill': lstm_eval['Skill'],
            'Violations_Low': violations_low, 'Violations_High': violations_high, 'Violation_Rate': v_rate
        })
        
        # Save fold metrics incrementally
        df_folds = pd.DataFrame(fold_results)
        os.makedirs('outputs', exist_ok=True)
        df_folds.to_csv(f'outputs/{output_prefix}_fold_results_partial.csv', index=False)
        
        fold += 1
        
    print("\n--- Running Final SHAP Analysis (Post-Training) ---", flush=True)
    global_shap_totals = defaultdict(float)
    N_total_evals = min(200, len(last_X_seq_val))
    shap_groups = execute_shap(last_bilstm, last_X_seq_train, last_X_seq_val, features)
    for g, v in shap_groups.items():
        global_shap_totals[g] += v
        
    print("\n--- Running MC Dropout (Post-Training) ---", flush=True)
    # 100 passes on the validation set of the last fold
    mc_preds, mc_std = last_bilstm.predict_mc_dropout(last_X_seq_val, n_passes=100)
    # Save the mean and std for the first 1000 samples to demonstrate uncertainty bounds
    mc_results = pd.DataFrame({
        'True_theta': y[val_idx][:1000],
        'MC_Mean': mc_preds[:1000],
        'MC_Std': mc_std[:1000]
    })
    mc_results.to_csv(f'outputs/{output_prefix}_mc_dropout.csv', index=False)

        
    # --- Microclimate Ablation ---
    print("\n--- Microclimate Ablation ---")
    ablation_vars = ['shade_fraction', 'full_shade_flag', 'Rs', 'VPD', 'Tsoil']
    drop_indices = [features.index(v) for v in ablation_vars if v in features]
    
    ablation_results = []
    fold = 1
    for train_idx, val_idx in cv.split(t_input):
        X_seq_train_abl, X_seq_val_abl = X_seq[train_idx].copy(), X_seq[val_idx].copy()
        
        for i in drop_indices:
            X_seq_train_abl[:, :, i] = 0.0
            X_seq_val_abl[:, :, i] = 0.0
            
        scaler = Scaler()
        scaler.fit(X_seq_train_abl, X_rf[train_idx])
        X_seq_train_scaled, _ = scaler.transform(X_seq_train_abl, X_rf[train_idx])
        X_seq_val_scaled, _ = scaler.transform(X_seq_val_abl, X_rf[val_idx])
        
        bilstm_abl = BiLSTMModel(input_dim=X_seq.shape[2], device=device)
        bilstm_abl.fit(X_seq_train_scaled, y[train_idx], X_val=X_seq_val_scaled, y_val=y[val_idx], epochs=epochs)
        
        y_pred_abl = bilstm_abl.predict(X_seq_val_scaled)
        
        current_theta_unscaled = X_seq[val_idx][:, -1, theta_idx]
        y_pred_pers = pers_model.predict_from_current(current_theta_unscaled)
        pers_eval = pers_model.evaluate(y[val_idx], y_pred_pers)
        rmse_pers = pers_eval['RMSE']
        
        abl_eval = bilstm_abl.evaluate(y[val_idx], y_pred_abl, rmse_pers)
        
        ablation_results.append({
            'Fold': fold,
            'Abl_RMSE': abl_eval['RMSE'],
            'Abl_Skill': abl_eval['Skill']
        })
        
        df_abl = pd.DataFrame(ablation_results)
        df_abl.to_csv(f'outputs/{output_prefix}_ablation_partial.csv', index=False)
        
        fold += 1
        
    # --- Reporting ---
    os.makedirs('outputs', exist_ok=True)
    
    df_folds = pd.DataFrame(fold_results)
    df_folds.to_csv(f'outputs/{output_prefix}_fold_results.csv', index=False)
    
    df_abl = pd.DataFrame(ablation_results)
    df_abl.to_csv(f'outputs/{output_prefix}_ablation.csv', index=False)
    
    # Calculate Mean & SD
    df_summary = pd.DataFrame({
        'Metric': ['Pers_RMSE', 'RF_RMSE', 'LSTM_RMSE', 'Abl_RMSE', 'LSTM_Skill', 'Abl_Skill'],
        'Mean': [
            df_folds['Pers_RMSE'].mean(), df_folds['RF_RMSE'].mean(), df_folds['LSTM_RMSE'].mean(), df_abl['Abl_RMSE'].mean(),
            df_folds['LSTM_Skill'].mean(), df_abl['Abl_Skill'].mean()
        ],
        'SD': [
            df_folds['Pers_RMSE'].std(), df_folds['RF_RMSE'].std(), df_folds['LSTM_RMSE'].std(), df_abl['Abl_RMSE'].std(),
            df_folds['LSTM_Skill'].std(), df_abl['Abl_Skill'].std()
        ]
    })
    df_summary.to_csv(f'outputs/{output_prefix}_summary.csv', index=False)
    
    # SHAP Aggregation
    shap_out = []
    for g, val in global_shap_totals.items():
        # Phij = (1 / (N * 288)) * sum( |phi| )
        norm_val = val / (N_total_evals * 288)
        shap_out.append({'Feature_Group': g, 'Mean_Absolute_SHAP': norm_val})
        
    df_shap = pd.DataFrame(shap_out).sort_values('Mean_Absolute_SHAP', ascending=False)
    df_shap.to_csv(f'outputs/{output_prefix}_shap.csv', index=False)
    
    # Markdown Report
    report_content = "# RUN 2 Statistical Report\n"
    if epochs == 1:
        report_content += "\n> [!WARNING]\n> RUN 2 — PIPELINE VALIDATION ONLY\n> NOT FOR SCIENTIFIC RESULTS\n\n"
    
    report_content += f"**Feature Count**: {len(features)}\n"
    report_content += f"**Feature Schema**: {', '.join(features)}\n\n"
    
    report_content += "### Sample Accounting\n"
    df_acc = pd.DataFrame(accounting).T
    df_acc.columns = ['Zone A', 'Zone B', 'Total']
    report_content += df_acc.to_markdown() + "\n\n"
    
    report_content += "### Model Performance (5-Fold CV)\n"
    report_content += df_summary.to_markdown() + "\n\n"
    
    report_content += "### Bounds Violations\n"
    v_rate_mean = df_folds['Violation_Rate'].mean()
    report_content += f"Mean Physical Violation Rate: {v_rate_mean:.2f}%\n\n"
    
    report_content += "### SHAP Feature Group Importance\n"
    report_content += df_shap.to_markdown() + "\n"
    
    with open(f'outputs/{output_prefix}_report.md', 'w') as f:
        f.write(report_content)
        
    import shutil
    shutil.copy(f'outputs/{output_prefix}_report.md', f'C:/Users/Prabakaran/.gemini/antigravity/brain/e6615bad-2ef1-47eb-a938-c0e4bda28a31/{output_prefix}_report.md')
    
    print(f"Pipeline completed successfully. Outputs written to outputs/{output_prefix}_*")

if __name__ == '__main__':
    # Phase 2: Full 50-epoch experiment
    run_pipeline(epochs=50, output_prefix="run2")
