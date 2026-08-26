import pytest
import numpy as np
import pandas as pd
import torch
from ml.enhanced_dataset_builder import EnhancedDatasetBuilder
from ml.enhanced_bilstm import ResidualAttentionBiLSTM, CompositeLoss

def test_enhanced_dataset_builder_shape_and_targets():
    # Build dataset using actual data
    builder_res = EnhancedDatasetBuilder('outputs/sensor_5min.parquet', target_zone='B', target_type='residual')
    data_res = builder_res.build_dataset()
    
    # Assert shapes
    assert 'X_seq' in data_res
    assert 'y' in data_res
    assert 't_input' in data_res
    
    samples = len(data_res['y'])
    assert data_res['X_seq'].shape[0] == samples
    assert data_res['X_seq'].shape[1] == 288 # input sequence window
    
    # Verify target calculation: residual vs absolute
    builder_abs = EnhancedDatasetBuilder('outputs/sensor_5min.parquet', target_zone='B', target_type='absolute')
    data_abs = builder_abs.build_dataset()
    
    theta_idx = builder_res.base_features.index('theta_v')
    
    # Check first few samples
    for i in range(min(5, samples)):
        current_theta = data_res['X_seq'][i, -1, theta_idx]
        y_res = data_res['y'][i]
        y_abs = data_abs['y'][i]
        
        # y_abs should equal current_theta + y_res
        assert np.allclose(y_abs, current_theta + y_res, atol=1e-5)

def test_enhanced_dataset_builder_causality():
    builder = EnhancedDatasetBuilder('outputs/sensor_5min.parquet', target_zone='B', target_type='residual')
    data = builder.build_dataset()
    
    features = data['feature_names_seq']
    theta_idx = features.index('theta_v')
    delta_24h_idx = features.index('delta_theta_24h')
    tslr_idx = features.index('TSLR')
    p_idx = features.index('P')
    
    X_seq = data['X_seq']
    
    # Verify each sample's features are strictly causal
    # e.g., delta_theta_24h at the last step (index 287) of sequence i must equal theta_v[287] - theta_v[0]
    for i in range(min(10, len(X_seq))):
        current_theta = X_seq[i, 287, theta_idx]
        theta_24h_ago = X_seq[i, 0, theta_idx] # index 0 is exactly 287 steps ago (approx 24h)
        delta_theta_24h_val = X_seq[i, 287, delta_24h_idx]
        
        assert np.allclose(delta_theta_24h_val, current_theta - theta_24h_ago, atol=1e-5)
        
        # Verify TSLR (Time Since Last Rain) calculation
        # If current P > 0, TSLR must be 0.
        current_p = X_seq[i, 287, p_idx]
        current_tslr = X_seq[i, 287, tslr_idx]
        if current_p > 0:
            assert np.allclose(current_tslr, 0.0, atol=1e-5)

def test_residual_attention_bilstm_shapes():
    batch_size = 4
    seq_len = 288
    input_dim = 40
    
    x = torch.randn(batch_size, seq_len, input_dim)
    
    model = ResidualAttentionBiLSTM(input_dim=input_dim, hidden_dim=32, use_conv=True)
    residual, gate, attn_weights = model(x)
    
    assert residual.shape == (batch_size, 1)
    assert gate.shape == (batch_size, 1)
    assert attn_weights.shape == (batch_size, seq_len, 1)
    
    # Verify gate is in [0, 1]
    assert torch.all(gate >= 0.0) and torch.all(gate <= 1.0)

def test_composite_loss():
    theta_wp = 0.15
    theta_fc = 0.35
    criterion = CompositeLoss(theta_wp=theta_wp, theta_fc=theta_fc)
    
    pred_absolute = torch.tensor([[0.12], [0.25], [0.38]]) # 0.12 violates wp, 0.38 violates fc
    true_absolute = torch.tensor([[0.20], [0.25], [0.30]])
    pred_residual = torch.tensor([[-0.01], [0.0], [0.01]])
    true_residual = torch.tensor([[-0.02], [0.0], [0.02]])
    
    loss, loss_H, loss_B, loss_T = criterion(pred_absolute, true_absolute, pred_residual, true_residual)
    
    assert loss.item() > 0
    assert loss_B.item() > 0 # physical violation should trigger penalty
    assert loss_T.item() > 0 # trend loss should compute
