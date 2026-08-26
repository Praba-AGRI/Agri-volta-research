import torch
import torch.nn as nn
import numpy as np
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

class BiLSTM(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, dropout=0.2):
        super(BiLSTM, self).__init__()
        
        self.lstm1 = nn.LSTM(
            input_size=input_dim, 
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
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 2, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        
    def forward(self, x):
        # x shape: (batch, seq_len, features)
        out, _ = self.lstm1(x)
        out = self.dropout1(out)
        
        out, (hn, cn) = self.lstm2(out)
        # We want return_sequences=False, so take the final hidden state or the last output
        # out shape is (batch, seq_len, hidden_dim * 2)
        # Taking the last sequence step
        out = out[:, -1, :]
        out = self.dropout2(out)
        
        out = self.fc(out)
        return out

class BiLSTMModel:
    def __init__(self, input_dim, device='cpu', lr=0.001):
        self.device = device
        self.model = BiLSTM(input_dim=input_dim).to(self.device)
        self.criterion = nn.MSELoss()
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        self.name = "BiLSTM"
        
    def fit(self, X_train, y_train, X_val=None, y_val=None, epochs=150, batch_size=64, patience=10):
        # Convert to tensors
        X_t = torch.tensor(X_train, dtype=torch.float32)
        y_t = torch.tensor(y_train, dtype=torch.float32).view(-1, 1)
        
        if X_val is not None:
            X_v = torch.tensor(X_val, dtype=torch.float32)
            y_v = torch.tensor(y_val, dtype=torch.float32).view(-1, 1)
            
        dataset = torch.utils.data.TensorDataset(X_t, y_t)
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        best_loss = float('inf')
        patience_counter = 0
        best_state = None
        
        for epoch in range(epochs):
            self.model.train()
            train_loss = 0
            
            for batch_x, batch_y in loader:
                batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                
                self.optimizer.zero_grad()
                outputs = self.model(batch_x)
                loss = self.criterion(outputs, batch_y)
                loss.backward()
                self.optimizer.step()
                
                train_loss += loss.item() * batch_x.size(0)
                
            train_loss /= len(X_t)
            
            print(f"Epoch {epoch+1}/{epochs} - Loss: {train_loss:.4f}", end="", flush=True)
            
            if X_val is not None:
                self.model.eval()
                val_loss = 0
                val_dataset = torch.utils.data.TensorDataset(X_v, y_v)
                val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
                with torch.no_grad():
                    for vx, vy in val_loader:
                        vx, vy = vx.to(self.device), vy.to(self.device)
                        v_out = self.model(vx)
                        val_loss += self.criterion(v_out, vy).item() * vx.size(0)
                val_loss /= len(X_val)
                    
                print(f" - Val Loss: {val_loss:.4f}", flush=True)
                
                if val_loss < best_loss:
                    best_loss = val_loss
                    best_state = self.model.state_dict()
                    patience_counter = 0
                else:
                    patience_counter += 1
                    
                if patience_counter >= patience:
                    print(" Early stopping.")
                    break
            else:
                print()
        
        if best_state is not None:
            self.model.load_state_dict(best_state)
            
    def predict(self, X, batch_size=64):
        self.model.eval()
        X_t = torch.tensor(X, dtype=torch.float32)
        dataset = torch.utils.data.TensorDataset(X_t)
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=False)
        
        all_preds = []
        with torch.no_grad():
            for (bx,) in loader:
                bx = bx.to(self.device)
                preds = self.model(bx)
                all_preds.append(preds.cpu().numpy().flatten())
                
        return np.concatenate(all_preds)
        
    def predict_mc_dropout(self, X, n_passes=100, batch_size=64):
        """
        Enables MC Dropout by explicitly setting the model to train mode during inference
        to keep dropout active.
        """
        self.model.train() # Keep dropout active
        X_t = torch.tensor(X, dtype=torch.float32)
        dataset = torch.utils.data.TensorDataset(X_t)
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=False)
        
        predictions = []
        with torch.no_grad():
            for _ in range(n_passes):
                pass_preds = []
                for (bx,) in loader:
                    bx = bx.to(self.device)
                    preds = self.model(bx)
                    pass_preds.append(preds.cpu().numpy().flatten())
                predictions.append(np.concatenate(pass_preds))
                
        predictions = np.array(predictions) # shape: (n_passes, samples)
        
        mu = np.mean(predictions, axis=0)
        # Unbiased std estimator over the N passes
        sigma = np.std(predictions, axis=0, ddof=1)
        
        return mu, sigma
        
    def evaluate(self, y_true, y_pred, rmse_persistence):
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        
        skill = 1.0 - (rmse / rmse_persistence) if rmse_persistence > 0 else 0.0
        
        return {
            'RMSE': rmse,
            'MAE': mae,
            'R2': r2,
            'Skill': skill
        }
