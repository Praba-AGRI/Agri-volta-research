import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import numpy as np
import pandas as pd
import torch
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import precision_score, recall_score, f1_score, r2_score

from ml.dataset_builder_run2c import DatasetBuilder2C
from ml.run2c_bilstm import MultiOutputBiLSTM2C, CompositeLoss2C
from ml.cv import RollingOriginPurgedCV

def evaluate_predictions(y_true_ir, y_pred_q, y_pred_event, y_true_event, X_fc, p_fc_idx=0):
    """
    Computes all RUN 2C continuous, decision, safety, and uncertainty metrics.
    y_pred_q: (N, 3) containing P10, P50, P90
    """
    ir_p10 = y_pred_q[:, 0]
    ir_p50 = y_pred_q[:, 1]
    ir_p90 = y_pred_q[:, 2]

    # Continuous
    rmse_ir = np.sqrt(np.mean((y_true_ir - ir_p50) ** 2))
    mae_ir = np.mean(np.abs(y_true_ir - ir_p50))
    bias_ir = np.mean(ir_p50 - y_true_ir)
    r2_ir = r2_score(y_true_ir, ir_p50) if len(np.unique(y_true_ir)) > 1 else 0.0
    nrmse_ir = rmse_ir / (np.mean(y_true_ir) + 1e-5)

    # Decision
    pred_binary = (y_pred_event > 0.5).astype(int)
    true_binary = (y_true_event > 0.5).astype(int)

    prec = precision_score(true_binary, pred_binary, zero_division=1)
    rec = recall_score(true_binary, pred_binary, zero_division=1)
    f1 = f1_score(true_binary, pred_binary, zero_division=1)

    fn = np.sum((true_binary == 1) & (pred_binary == 0))
    fp = np.sum((true_binary == 0) & (pred_binary == 1))

    # Uncertainty Coverage
    cov_p10 = np.mean(y_true_ir <= ir_p10)
    cov_p50 = np.mean(y_true_ir <= ir_p50)
    cov_p90 = np.mean(y_true_ir <= ir_p90)
    width = np.mean(ir_p90 - ir_p10)

    return {
        'rmse': rmse_ir, 'mae': mae_ir, 'bias': bias_ir, 'r2': r2_ir, 'nrmse': nrmse_ir,
        'prec': prec, 'rec': rec, 'f1': f1, 'fn': fn, 'fp': fp,
        'cov10': cov_p10, 'cov50': cov_p50, 'cov90': cov_p90, 'width': width
    }

def run_experiment_mode(mode='operational', epochs=15):
    print(f"\n=======================================================")
    print(f"       STARTING RUN 2C EVALUATION: {mode.upper()} MODE")
    print(f"=======================================================")
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    builder = DatasetBuilder2C('outputs/sensor_5min.parquet', mode=mode, target_zone='B')
    data = builder.build_dataset(stride=12) # 1 hour decision frequency

    X_hist = data['X_hist']
    X_fc = data['X_fc']
    y_theta = data['y_theta']
    y_etc = data['y_etc']
    y_deficit = data['y_deficit']
    y_ir_star = data['y_ir_star']
    y_event = data['y_event']
    t_input = data['timestamps']

    # Since stride=12 (1 hour steps), 24h = 24 steps
    cv = RollingOriginPurgedCV(n_folds=5, forecast_horizon=24, input_window=24)
    fold = 1
    fold_results = []

    for train_idx, val_idx in cv.split(t_input):
        print(f"\n--- Fold {fold} ---")

        # Standardize features using train stats
        hist_mean = X_hist[train_idx].mean(axis=(0, 1), keepdims=True)
        hist_std = X_hist[train_idx].std(axis=(0, 1), keepdims=True) + 1e-5

        fc_mean = X_fc[train_idx].mean(axis=0, keepdims=True)
        fc_std = X_fc[train_idx].std(axis=0, keepdims=True) + 1e-5

        X_hist_tr = (X_hist[train_idx] - hist_mean) / hist_std
        X_fc_tr = (X_fc[train_idx] - fc_mean) / fc_std

        X_hist_va = (X_hist[val_idx] - hist_mean) / hist_std
        X_fc_va = (X_fc[val_idx] - fc_mean) / fc_std

        # Convert to Tensors
        train_ds = TensorDataset(
            torch.tensor(X_hist_tr, dtype=torch.float32),
            torch.tensor(X_fc_tr, dtype=torch.float32),
            torch.tensor(y_theta[train_idx], dtype=torch.float32),
            torch.tensor(y_etc[train_idx], dtype=torch.float32),
            torch.tensor(y_deficit[train_idx], dtype=torch.float32),
            torch.tensor(y_ir_star[train_idx], dtype=torch.float32),
            torch.tensor(y_event[train_idx], dtype=torch.float32)
        )
        loader = DataLoader(train_ds, batch_size=64, shuffle=True)

        model = MultiOutputBiLSTM2C(hist_input_dim=7, fc_input_dim=6, hidden_dim=64).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        criterion = CompositeLoss2C()

        model.train()
        for ep in range(epochs):
            for batch in loader:
                b_hist, b_fc, b_th, b_etc, b_def, b_ir, b_ev = [b.to(device) for b in batch]
                optimizer.zero_grad()
                outputs = model(b_hist, b_fc)
                targets = {'theta': b_th, 'etc': b_etc, 'deficit': b_def, 'ir_star': b_ir, 'event': b_ev}
                loss = criterion(outputs, targets, b_fc)
                loss.backward()
                optimizer.step()

        # Validation Evaluation
        model.eval()
        with torch.no_grad():
            va_hist_t = torch.tensor(X_hist_va, dtype=torch.float32).to(device)
            va_fc_t = torch.tensor(X_fc_va, dtype=torch.float32).to(device)
            outputs_va = model(va_hist_t, va_fc_t)

            pred_q = outputs_va['pred_ir_quantiles'].cpu().numpy()
            pred_event_prob = torch.sigmoid(outputs_va['pred_event_logits']).cpu().numpy().squeeze()

        # Baselines:
        # 1. Persistence Baseline: theta_24 = theta_current -> Deficit = max(0, 0.27 - theta_curr)*600 -> IR_pers = max(0, D - P_fc)
        curr_theta = X_hist[val_idx, -1, 0] # theta_v index
        P_fc_val = X_fc[val_idx, 0] # P_fc index
        pers_deficit = np.maximum(0.0, (0.27 - curr_theta) * 600.0)
        ir_pers = np.maximum(0.0, pers_deficit - P_fc_val)

        # 2. Physics-only Forecast Baseline: IR_phys = max(0, Deficit_current + ETc_forecast - P_fc)
        # Approximate ETc_forecast = 4.0 mm/day
        ir_phys = np.maximum(0.0, pers_deficit + 4.0 - P_fc_val)

        # Evaluate Hybrid AI
        res_ai = evaluate_predictions(
            y_true_ir=y_ir_star[val_idx],
            y_pred_q=pred_q,
            y_pred_event=pred_event_prob,
            y_true_event=y_event[val_idx],
            X_fc=X_fc[val_idx]
        )

        # Evaluate Persistence Baseline
        res_pers = evaluate_predictions(
            y_true_ir=y_ir_star[val_idx],
            y_pred_q=np.column_stack([ir_pers*0.8, ir_pers, ir_pers*1.2]),
            y_pred_event=(ir_pers > 0.05).astype(float),
            y_true_event=y_event[val_idx],
            X_fc=X_fc[val_idx]
        )

        # Evaluate Physics Baseline
        res_phys = evaluate_predictions(
            y_true_ir=y_ir_star[val_idx],
            y_pred_q=np.column_stack([ir_phys*0.8, ir_phys, ir_phys*1.2]),
            y_pred_event=(ir_phys > 0.05).astype(float),
            y_true_event=y_event[val_idx],
            X_fc=X_fc[val_idx]
        )

        fold_results.append({
            'fold': fold,
            'ai': res_ai,
            'pers': res_pers,
            'phys': res_phys
        })

        print(f"Fold {fold} AI RMSE: {res_ai['rmse']:.4f} mm | Phys RMSE: {res_phys['rmse']:.4f} mm | Pers RMSE: {res_pers['rmse']:.4f} mm")
        print(f"Fold {fold} AI F1:   {res_ai['f1']:.4f}   | Phys F1:   {res_phys['f1']:.4f}   | Pers F1:   {res_pers['f1']:.4f}")

        fold += 1

    return fold_results

def compile_and_save_report(oracle_results, op_results):
    rep = "=== RUN 2C EXPERIMENTAL REPORT: IRRIGATION REQUIREMENT FORECASTING ===\n\n"

    rep += "### 1. Model Summary & Architectural Shift\n"
    rep += "RUN 2C redefines the target from predicting raw soil moisture (theta_v) to predicting the **24-hour root-zone irrigation requirement (IR*)** derived from exact physical counterfactual bisection search.\n\n"

    rep += "### 2. Operational Primary Results (5-Fold CV)\n"
    rep += "| Fold | Hybrid AI RMSE (mm) | Physics Forecast RMSE (mm) | Persistence RMSE (mm) | AI F1 | Phys F1 | Pers F1 | AI NRMSE |\n"
    rep += "|---|---|---|---|---|---|---|---|\n"
    for r in op_results:
        f = r['fold']
        ai = r['ai']
        phys = r['phys']
        pers = r['pers']
        rep += f"| Fold {f} | {ai['rmse']:.4f} | {phys['rmse']:.4f} | {pers['rmse']:.4f} | {ai['f1']:.4f} | {phys['f1']:.4f} | {pers['f1']:.4f} | {ai['nrmse']:.4f} |\n"

    mean_ai_rmse = np.mean([r['ai']['rmse'] for r in op_results])
    mean_phys_rmse = np.mean([r['phys']['rmse'] for r in op_results])
    mean_pers_rmse = np.mean([r['pers']['rmse'] for r in op_results])

    rep += f"\n**Mean Operational RMSE:** Hybrid AI = **{mean_ai_rmse:.4f} mm** | Physics Forecast = **{mean_phys_rmse:.4f} mm** | Persistence = **{mean_pers_rmse:.4f} mm**\n\n"

    rep += "### 3. Oracle Upper-Bound Diagnostic Results (Perfect Weather Forcing)\n"
    rep += "| Fold | Oracle Hybrid AI RMSE (mm) | Perfect Physics RMSE (mm) | Oracle AI F1 | Perfect Phys F1 |\n"
    rep += "|---|---|---|---|---|\n"
    for r in oracle_results:
        f = r['fold']
        ai = r['ai']
        phys = r['phys']
        rep += f"| Fold {f} | {ai['rmse']:.4f} | {phys['rmse']:.4f} | {ai['f1']:.4f} | {phys['f1']:.4f} |\n"

    mean_oracle_ai_rmse = np.mean([r['ai']['rmse'] for r in oracle_results])
    rep += f"\n**Mean Oracle AI RMSE:** **{mean_oracle_ai_rmse:.4f} mm** (Information upper bound)\n\n"

    rep += "### 4. Quantile Uncertainty & Calibration (Operational Mode)\n"
    rep += "| Fold | P10 Coverage | P50 Coverage | P90 Coverage | Mean Interval Width (mm) |\n"
    rep += "|---|---|---|---|---|\n"
    for r in op_results:
        f = r['fold']
        ai = r['ai']
        rep += f"| Fold {f} | {ai['cov10']:.4f} | {ai['cov50']:.4f} | {ai['cov90']:.4f} | {ai['width']:.4f} |\n"

    os.makedirs('outputs/diagnostics', exist_ok=True)
    report_path = 'outputs/diagnostics/run2c_irrigation_forecasting_report.md'
    with open(report_path, 'w') as f:
        f.write(rep)

    print(f"\nReport generated and written to {report_path}")
    print(rep)

if __name__ == '__main__':
    oracle_res = run_experiment_mode(mode='oracle', epochs=15)
    op_res = run_experiment_mode(mode='operational', epochs=15)
    compile_and_save_report(oracle_res, op_res)
