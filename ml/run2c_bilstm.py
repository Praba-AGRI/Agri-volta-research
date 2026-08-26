import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class QuantileLoss(nn.Module):
    def __init__(self, quantiles=[0.10, 0.50, 0.90]):
        super().__init__()
        self.quantiles = quantiles

    def forward(self, preds, target):
        # preds: (N, 3), target: (N, 1)
        losses = []
        for i, q in enumerate(self.quantiles):
            errors = target - preds[:, i:i+1]
            loss = torch.max((q - 1) * errors, q * errors)
            losses.append(torch.mean(loss))
        return sum(losses)

class MultiOutputBiLSTM2C(nn.Module):
    def __init__(self, hist_input_dim=7, fc_input_dim=6, hidden_dim=64):
        super().__init__()

        # 1. Historical Encoder (Conv1D + BiLSTM)
        self.conv1d = nn.Conv1d(hist_input_dim, 32, kernel_size=5, padding=2)
        self.bilstm = nn.LSTM(32, hidden_dim, num_layers=2, batch_first=True, bidirectional=True)

        # Temporal Attention
        self.attn = nn.Linear(hidden_dim * 2, 1)

        # 2. Forecast Encoder
        self.fc_encoder = nn.Sequential(
            nn.Linear(fc_input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 32),
            nn.ReLU()
        )

        # 3. Shared Latent Fusion Layer
        fusion_dim = hidden_dim * 2 + 32
        self.fusion = nn.Sequential(
            nn.Linear(fusion_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.1)
        )

        # 4. Multi-Output Heads
        self.theta_head = nn.Linear(64, 1)
        self.etc_head = nn.Linear(64, 1)
        self.deficit_head = nn.Linear(64, 1)
        self.quantile_ir_head = nn.Linear(64, 3) # IR10, IR50, IR90
        self.event_head = nn.Linear(64, 1) # Sigmoid P(IR>0)

    def forward(self, X_hist, X_fc):
        # X_hist: (N, 288, 7), X_fc: (N, 6)
        batch_size = X_hist.size(0)

        # 1. Encode History
        # Conv1D expects (N, C, L)
        h_conv = F.relu(self.conv1d(X_hist.transpose(1, 2))).transpose(1, 2)
        lstm_out, _ = self.bilstm(h_conv) # (N, 288, 128)

        # Attention weights over 288 steps
        attn_weights = F.softmax(self.attn(lstm_out), dim=1) # (N, 288, 1)
        h_hist = torch.sum(lstm_out * attn_weights, dim=1) # (N, 128)

        # 2. Encode Forecast
        h_fc = self.fc_encoder(X_fc) # (N, 32)

        # 3. Fuse Latents
        h_fused = torch.cat([h_hist, h_fc], dim=1) # (N, 160)
        latent = self.fusion(h_fused) # (N, 64)

        # 4. Heads
        pred_theta = self.theta_head(latent)
        pred_etc = F.relu(self.etc_head(latent))
        pred_deficit = F.relu(self.deficit_head(latent))
        pred_ir_quantiles = F.relu(self.quantile_ir_head(latent))
        pred_event_logits = self.event_head(latent)

        return {
            'pred_theta': pred_theta,
            'pred_etc': pred_etc,
            'pred_deficit': pred_deficit,
            'pred_ir_quantiles': pred_ir_quantiles,
            'pred_event_logits': pred_event_logits
        }

class CompositeLoss2C(nn.Module):
    def __init__(self, lambda_Q=1.0, lambda_CE=0.5, lambda_C=0.5, lambda_U=1.5):
        super().__init__()
        self.quantile_loss = QuantileLoss(quantiles=[0.10, 0.50, 0.90])
        self.bce_loss = nn.BCEWithLogitsLoss()
        self.lambda_Q = lambda_Q
        self.lambda_CE = lambda_CE
        self.lambda_C = lambda_C
        self.lambda_U = lambda_U

    def forward(self, outputs, targets, X_fc):
        # targets: dict of tensors ('theta', 'etc', 'deficit', 'ir_star', 'event')
        pred_theta = outputs['pred_theta']
        pred_etc = outputs['pred_etc']
        pred_deficit = outputs['pred_deficit']
        pred_ir_q = outputs['pred_ir_quantiles']
        pred_event_logits = outputs['pred_event_logits']

        y_theta = targets['theta'].unsqueeze(1)
        y_etc = targets['etc'].unsqueeze(1)
        y_deficit = targets['deficit'].unsqueeze(1)
        y_ir_star = targets['ir_star'].unsqueeze(1)
        y_event = targets['event'].unsqueeze(1)

        # 1. Auxiliary Regression Losses
        loss_aux = F.mse_loss(pred_theta, y_theta) + F.mse_loss(pred_etc, y_etc) + F.mse_loss(pred_deficit, y_deficit)

        # 2. Quantile Loss on IR*
        loss_Q = self.quantile_loss(pred_ir_q, y_ir_star)

        # 3. Binary Event Cross Entropy
        loss_CE = self.bce_loss(pred_event_logits, y_event)

        # 4. Underprediction Penalty (Asymmetric Risk for P50)
        ir_p50 = pred_ir_q[:, 1:2]
        under_error = torch.clamp(y_ir_star - ir_p50, min=0.0)
        loss_U = torch.mean(under_error ** 2)

        # 5. Physical Consistency Loss
        # Deficit consistency: D_hat approx max(0, 0.27 - theta_hat) * 600
        calc_deficit = torch.clamp((0.27 - pred_theta) * 600.0, min=0.0)
        loss_consistency = F.l1_loss(pred_deficit, calc_deficit)

        total_loss = (
            0.2 * loss_aux + 
            self.lambda_Q * loss_Q + 
            self.lambda_CE * loss_CE + 
            self.lambda_U * loss_U + 
            self.lambda_C * loss_consistency
        )

        return total_loss
