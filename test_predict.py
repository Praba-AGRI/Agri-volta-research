import os
import sys
import numpy as np
import pandas as pd
import torch

from ml.dataset_builder import DatasetBuilder
from ml.scaling import Scaler
from ml.bilstm import BiLSTMModel

def run_test():
    builder_A = DatasetBuilder('outputs/sensor_5min.parquet', target_zone='A')
    # Limit rows to avoid RAM issues
    builder_A.df = builder_A.df.iloc[:2000]
    dataset_A = builder_A.build_dataset()
    
    builder_B = DatasetBuilder('outputs/sensor_5min.parquet', target_zone='B')
    builder_B.df = builder_B.df.iloc[:2000]
    dataset_B = builder_B.build_dataset()

    X_seq = np.concatenate([dataset_A['X_seq'], dataset_B['X_seq']], axis=0)
    X_rf = np.concatenate([dataset_A['X_rf'], dataset_B['X_rf']], axis=0)
    y = np.concatenate([dataset_A['y'], dataset_B['y']], axis=0)
    features = dataset_A['feature_names_seq']

    ablation_vars = ['shade_fraction', 'full_shade_flag', 'Rs', 'VPD', 'Tsoil']
    drop_indices = [features.index(v) for v in ablation_vars if v in features]

    train_idx = np.arange(0, len(X_seq) // 2)
    val_idx = np.arange(len(X_seq) // 2, len(X_seq))

    X_seq_train_abl, X_seq_val_abl = X_seq[train_idx].copy(), X_seq[val_idx].copy()

    for i in drop_indices:
        X_seq_train_abl[:, :, i] = 0.0
        X_seq_val_abl[:, :, i] = 0.0

    scaler = Scaler()
    scaler.fit(X_seq_train_abl, X_rf[train_idx])
    X_seq_train_scaled, _ = scaler.transform(X_seq_train_abl, X_rf[train_idx])
    X_seq_val_scaled, _ = scaler.transform(X_seq_val_abl, X_rf[val_idx])

    bilstm_abl = BiLSTMModel(input_dim=X_seq.shape[2], device='cpu')
    print(f"X_seq.shape[2] = {X_seq.shape[2]}")
    
    # Just test predict
    print("Testing predict...")
    try:
        y_pred = bilstm_abl.predict(X_seq_val_scaled)
        print("Success! Prediction length:", len(y_pred))
    except Exception as e:
        print(f"Error during predict: {e}")
        
    print("Done.")

if __name__ == '__main__':
    run_test()
