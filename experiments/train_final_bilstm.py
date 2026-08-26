import os
import pandas as pd
import numpy as np
import torch
import joblib
from ml.dataset_builder import DatasetBuilder
from ml.bilstm import BiLSTMModel
from ml.scaling import Scaler

def train_and_save():
    print("Training final frozen BiLSTM on RUN 1 Zone B dataset...")
    np.random.seed(42)
    torch.manual_seed(42)
    
    # 1. Build dataset
    builder_B = DatasetBuilder('outputs/sensor_5min.parquet', target_zone='B')
    dataset_B = builder_B.build_dataset()
    
    X_seq = dataset_B['X_seq']
    X_rf = dataset_B['X_rf']
    y = dataset_B['y']
    t_input = dataset_B['t_input']
    
    sort_idx = np.argsort(t_input)
    X_seq = X_seq[sort_idx]
    X_rf = X_rf[sort_idx]
    y = y[sort_idx]
    
    # 2. Scale
    scaler = Scaler()
    scaler.fit(X_seq, X_rf)
    X_seq_scaled, _ = scaler.transform(X_seq, X_rf)
    
    # 3. Train
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    bilstm = BiLSTMModel(input_dim=X_seq_scaled.shape[2], device=device)
    # We train for 50 epochs as frozen in RUN 2
    bilstm.fit(X_seq_scaled, y, epochs=50)
    
    # 4. Save
    os.makedirs('outputs/models', exist_ok=True)
    torch.save({
        'model_state_dict': bilstm.model.state_dict(),
        'input_dim': X_seq_scaled.shape[2]
    }, 'outputs/models/bilstm_model.pt')
    
    joblib.dump(scaler, 'outputs/models/scaler.pkl')
    print("Model and scaler saved to outputs/models/")

if __name__ == "__main__":
    train_and_save()
