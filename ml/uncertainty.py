import shap
import torch
import numpy as np

def run_shap_analysis(model_wrapper, X_val_seq, feature_names, n_background=100, n_eval=200):
    """
    Runs DeepExplainer on the trained BiLSTM model.
    X_val_seq: (samples, 288, F) array from validation fold.
    """
    model = model_wrapper.model
    model.eval()
    
    # We sample a background from X_val_seq or if we passed X_train, from X_train
    # The spec asked to use a background from the training fold, so we'll expect X_bg here
    # Actually, let's pass X_bg explicitly
    pass

def execute_shap(model_wrapper, X_bg, X_eval, feature_names):
    device = model_wrapper.device
    model = model_wrapper.model
    model.eval()
    
    # CuDNN RNNs cannot do backward in eval mode. Temporarily disable cudnn.
    torch.backends.cudnn.enabled = False
    
    # Randomly subset the background
    np.random.seed(42)
    bg_idx = np.random.choice(X_bg.shape[0], min(100, X_bg.shape[0]), replace=False)
    X_bg_tensor = torch.tensor(X_bg[bg_idx], dtype=torch.float32).to(device)
    
    eval_idx = np.random.choice(X_eval.shape[0], min(200, X_eval.shape[0]), replace=False)
    X_eval_tensor = torch.tensor(X_eval[eval_idx], dtype=torch.float32).to(device)
    
    explainer = shap.GradientExplainer(model, X_bg_tensor)
    
    print(f"Calculating SHAP for {len(X_eval_tensor)} eval samples vs {len(X_bg_tensor)} background...", flush=True)
    # SHAP values shape for sequence: (samples, seq_len, features)
    shap_values = explainer.shap_values(X_eval_tensor)
    print("SHAP calculation done.", flush=True)
    
    # shap_values from DeepExplainer on a regression task usually returns a list of arrays or a single array
    if isinstance(shap_values, list):
        shap_values = shap_values[0]
        
    # Aggregate temporally: mean absolute SHAP value across the 288 timesteps for each feature
    # Shape becomes (samples, features)
    global_shap = np.mean(np.abs(shap_values), axis=1)
    
    # Average across the evaluated samples to get feature importance
    mean_abs_shap = np.mean(global_shap, axis=0)
    
    # Group them as requested
    groups = {
        'historical_soil_moisture': ['theta_v'],
        'temperature': ['T'],
        'humidity_vpd': ['RH', 'VPD'],
        'soil_temperature': ['Tsoil'],
        'radiation': ['Rs', 'lux_up', 'lux_down'],
        'pv_shade': ['shade_fraction', 'full_shade_flag'],
        'rainfall': ['P'],
        'thermal_time': ['daily_GDD', 'cumulative_GDD']
    }
    
    # Group sums
    grouped_importance = {}
    for group_name, feats in groups.items():
        total_imp = 0.0
        for f in feats:
            if f in feature_names:
                idx = feature_names.index(f)
                total_imp += mean_abs_shap[idx]
        grouped_importance[group_name] = total_imp
        
    torch.backends.cudnn.enabled = True
    return grouped_importance
