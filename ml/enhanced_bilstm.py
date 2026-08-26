import torch
import torch.nn as nn
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

class MultiScaleConv(nn.Module):
    def __init__(self, input_dim, out_dim=64):
        super().__init__()
        assert out_dim % 4 == 0, "out_dim must be divisible by 4"
        self.conv3 = nn.Conv1d(input_dim, out_dim // 4, kernel_size=3, padding=1)
        self.conv12 = nn.Conv1d(input_dim, out_dim // 4, kernel_size=12, padding=6)
        self.conv36 = nn.Conv1d(input_dim, out_dim // 4, kernel_size=36, padding=18)
        self.conv_proj = nn.Conv1d(input_dim, out_dim // 4, kernel_size=1)
        self.relu = nn.ReLU()
        
    def forward(self, x):
        # x shape: (batch, seq_len, features) -> transpose to (batch, features, seq_len)
        x_t = x.transpose(1, 2)
        
        out3 = self.relu(self.conv3(x_t))
        out12 = self.relu(self.conv12(x_t))[:, :, :x.shape[1]]
        out36 = self.relu(self.conv36(x_t))[:, :, :x.shape[1]]
        out_proj = self.relu(self.conv_proj(x_t))
        
        out = torch.cat([out3, out12, out36, out_proj], dim=1) # (batch, out_dim, seq_len)
        return out.transpose(1, 2) # (batch, seq_len, out_dim)

class TemporalAttention(nn.Module):
    def __init__(self, hidden_dim):
        super().__init__()
        self.attn = nn.Linear(hidden_dim, 1)
        
    def forward(self, x):
        # x: (batch, seq_len, hidden_dim)
        scores = self.attn(x) # (batch, seq_len, 1)
        weights = torch.softmax(scores, dim=1) # (batch, seq_len, 1)
        context = torch.sum(x * weights, dim=1) # (batch, hidden_dim)
        return context, weights

class ResidualAttentionBiLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, dropout=0.2, use_conv=True):
        super().__init__()
        self.use_conv = use_conv
        
        if use_conv:
            self.conv_front = MultiScaleConv(input_dim, out_dim=64)
            lstm_in_dim = 64
        else:
            lstm_in_dim = input_dim
            
        self.lstm1 = nn.LSTM(
            input_size=lstm_in_dim, 
            hidden_size=hidden_dim, 
            num_layers=1, 
            batch_first=True, 
            bidirectional=True
        )
        self.dropout1 = nn.Dropout(dropout)
        
        self.lstm2 = nn.LSTM(
            input_size=hidden_dim * 2, 
            hidden_size=hidden_dim, 
            num_layers=1, 
            batch_first=True, 
            bidirectional=True
        )
        self.dropout2 = nn.Dropout(dropout)
        
        self.attention = TemporalAttention(hidden_dim * 2)
        
        # Dense feature projection
        self.dense = nn.Sequential(
            nn.Linear(hidden_dim * 2, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, 32),
            nn.ReLU()
        )
        
        # Residual prediction head
        self.residual_head = nn.Linear(32, 1)
        
        # Gate prediction head (g_t in [0, 1])
        self.gate_head = nn.Sequential(
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        # x shape: (batch, seq_len, features)
        if self.use_conv:
            features = self.conv_front(x)
        else:
            features = x
            
        out, _ = self.lstm1(features)
        out = self.dropout1(out)
        
        out, _ = self.lstm2(out)
        out = self.dropout2(out)
        
        context, attn_weights = self.attention(out) # context shape: (batch, hidden_dim * 2)
        
        dense_out = self.dense(context)
        
        residual = self.residual_head(dense_out) # shape: (batch, 1)
        gate = self.gate_head(dense_out)         # shape: (batch, 1)
        
        return residual, gate, attn_weights

class CompositeLoss(nn.Module):
    def __init__(self, theta_wp=0.15, theta_fc=0.35, lambda_B=1.0, lambda_T=0.1, gamma=1000.0):
        super().__init__()
        self.huber = nn.HuberLoss()
        self.theta_wp = theta_wp
        self.theta_fc = theta_fc
        self.lambda_B = lambda_B
        self.lambda_T = lambda_T
        self.gamma = gamma
        
    def forward(self, pred_absolute, true_absolute, pred_residual, true_residual):
        # 1. Huber Forecast Loss
        loss_H = self.huber(pred_absolute, true_absolute)
        
        # 2. Physical Penalty
        violation_low = torch.relu(self.theta_wp - pred_absolute)
        violation_high = torch.relu(pred_absolute - self.theta_fc)
        loss_B = torch.mean(violation_low**2 + violation_high**2)
        
        # 3. Differentiable Trend Margin Loss
        loss_T = torch.mean(torch.log(1.0 + torch.exp(-self.gamma * pred_residual * true_residual)))
        
        loss = loss_H + self.lambda_B * loss_B + self.lambda_T * loss_T
        return loss, loss_H, loss_B, loss_T

class EnhancedBiLSTMModel:
    def __init__(self, input_dim, device='cpu', lr=0.001, target_type='residual', use_conv=True):
        self.device = device
        self.target_type = target_type
        self.model = ResidualAttentionBiLSTM(input_dim=input_dim, use_conv=use_conv).to(self.device)
        self.criterion = CompositeLoss()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        self.name = "EnhancedBiLSTM"
        
    def fit(self, X_train, y_train, current_theta_train, X_val=None, y_val=None, current_theta_val=None, epochs=150, batch_size=64, patience=15):
        # y_train is the target loaded from the dataset builder
        # If target_type is 'residual', y_train is delta_theta_24h = theta_{t+288} - theta_t
        # If target_type is 'absolute', y_train is theta_{t+288}
        
        X_t = torch.tensor(X_train, dtype=torch.float32)
        y_t = torch.tensor(y_train, dtype=torch.float32).view(-1, 1)
        c_t = torch.tensor(current_theta_train, dtype=torch.float32).view(-1, 1)
        
        if X_val is not None:
            X_v = torch.tensor(X_val, dtype=torch.float32)
            y_v = torch.tensor(y_val, dtype=torch.float32).view(-1, 1)
            c_v = torch.tensor(current_theta_val, dtype=torch.float32).view(-1, 1)
            
        dataset = torch.utils.data.TensorDataset(X_t, y_t, c_t)
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        best_loss = float('inf')
        patience_counter = 0
        best_state = None
        
        for epoch in range(epochs):
            self.model.train()
            train_loss = 0
            
            for bx, by, bc in loader:
                bx, by, bc = bx.to(self.device), by.to(self.device), bc.to(self.device)
                
                self.optimizer.zero_grad()
                pred_res, gate, _ = self.model(bx)
                
                if self.target_type == 'residual':
                    pred_abs = bc + gate * pred_res
                    true_abs = bc + by
                    loss, _, _, _ = self.criterion(pred_abs, true_abs, pred_res, by)
                else:
                    pred_abs = pred_res
                    true_abs = by
                    loss, _, _, _ = self.criterion(pred_abs, true_abs, pred_res - bc, by - bc)
                    
                loss.backward()
                self.optimizer.step()
                
                train_loss += loss.item() * bx.size(0)
                
            train_loss /= len(X_t)
            
            if X_val is not None:
                self.model.eval()
                val_loss = 0
                val_dataset = torch.utils.data.TensorDataset(X_v, y_v, c_v)
                val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
                
                with torch.no_grad():
                    for vx, vy, vc in val_loader:
                        vx, vy, vc = vx.to(self.device), vy.to(self.device), vc.to(self.device)
                        pred_res, gate, _ = self.model(vx)
                        
                        if self.target_type == 'residual':
                            pred_abs = vc + gate * pred_res
                            true_abs = vc + vy
                            loss, _, _, _ = self.criterion(pred_abs, true_abs, pred_res, vy)
                        else:
                            pred_abs = pred_res
                            true_abs = vy
                            loss, _, _, _ = self.criterion(pred_abs, true_abs, pred_res - vc, vy - vc)
                            
                        val_loss += loss.item() * vx.size(0)
                        
                val_loss /= len(X_val)
                
                if val_loss < best_loss:
                    best_loss = val_loss
                    best_state = self.model.state_dict()
                    patience_counter = 0
                else:
                    patience_counter += 1
                    
                if patience_counter >= patience:
                    break
                    
        if best_state is not None:
            self.model.load_state_dict(best_state)
            
    def predict(self, X, current_theta, batch_size=64):
        """Returns the absolute predictions, residuals, gates, and attention weights."""
        self.model.eval()
        X_t = torch.tensor(X, dtype=torch.float32)
        c_t = torch.tensor(current_theta, dtype=torch.float32).view(-1, 1)
        dataset = torch.utils.data.TensorDataset(X_t, c_t)
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=False)
        
        all_absolute = []
        all_residual = []
        all_gates = []
        
        with torch.no_grad():
            for bx, bc in loader:
                bx, bc = bx.to(self.device), bc.to(self.device)
                pred_res, gate, _ = self.model(bx)
                
                if self.target_type == 'residual':
                    pred_abs = bc + gate * pred_res
                else:
                    pred_abs = pred_res
                    pred_res = pred_abs - bc
                    
                all_absolute.append(pred_abs.cpu().numpy().flatten())
                all_residual.append(pred_res.cpu().numpy().flatten())
                all_gates.append(gate.cpu().numpy().flatten())
                
        return (
            np.concatenate(all_absolute),
            np.concatenate(all_residual),
            np.concatenate(all_gates)
        )
        
    def predict_mc_dropout(self, X, current_theta, n_passes=100, batch_size=64):
        """Enables MC Dropout by setting the model to train mode during inference."""
        self.model.train()
        X_t = torch.tensor(X, dtype=torch.float32)
        c_t = torch.tensor(current_theta, dtype=torch.float32).view(-1, 1)
        dataset = torch.utils.data.TensorDataset(X_t, c_t)
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=False)
        
        predictions = []
        with torch.no_grad():
            for _ in range(n_passes):
                pass_preds = []
                for bx, bc in loader:
                    bx, bc = bx.to(self.device), bc.to(self.device)
                    pred_res, gate, _ = self.model(bx)
                    if self.target_type == 'residual':
                        pred_abs = bc + gate * pred_res
                    else:
                        pred_abs = pred_res
                    pass_preds.append(pred_abs.cpu().numpy().flatten())
                predictions.append(np.concatenate(pass_preds))
                
        predictions = np.array(predictions) # (passes, samples)
        mu = np.mean(predictions, axis=0)
        sigma = np.std(predictions, axis=0, ddof=1)
        return mu, sigma
        
    def evaluate(self, y_true_absolute, y_pred_absolute, rmse_persistence):
        """Calculates standard regression evaluation metrics and Skill Score."""
        rmse = np.sqrt(mean_squared_error(y_true_absolute, y_pred_absolute))
        mae = mean_absolute_error(y_true_absolute, y_pred_absolute)
        r2 = r2_score(y_true_absolute, y_pred_absolute)
        skill = 1.0 - (rmse / rmse_persistence) if rmse_persistence > 0 else 0.0
        
        return {
            'RMSE': rmse,
            'MAE': mae,
            'R2': r2,
            'Skill': skill
        }
