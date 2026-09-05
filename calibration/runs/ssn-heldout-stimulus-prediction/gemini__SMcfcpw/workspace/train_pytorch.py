import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import time

# Set random seed for reproducibility
torch.manual_seed(42)
np.random.seed(42)

# Load data
train_r_obs = np.load("/workspace/data/train_r_obs.npy")
t_obs = np.load("/workspace/data/t_obs.npy")
train_I = np.load("/workspace/data/train_I.npy")
eval_I = np.load("/workspace/data/eval_I.npy")
t = np.load("/workspace/data/t.npy")
xy = np.load("/workspace/data/xy.npy")

# Convert to PyTorch tensors
train_r_obs_t = torch.tensor(train_r_obs, dtype=torch.float32)
train_I_t = torch.tensor(train_I, dtype=torch.float32)
eval_I_t = torch.tensor(eval_I, dtype=torch.float32)
xy_t = torch.tensor(xy, dtype=torch.float32)

# Compute distance matrix
dist_sq = torch.sum((xy_t.unsqueeze(1) - xy_t.unsqueeze(0)) ** 2, dim=-1)

class SSNModel(nn.Module):
    def __init__(self, N=49, NE=29, tau=0.5, k=0.5, n=2.0, dt=0.01):
        super().__init__()
        self.N = N
        self.NE = NE
        self.tau = tau
        self.k = k
        self.n = n
        self.dt = dt
        
        # Initialize U to small values so W starts near 0
        self.U = nn.Parameter(torch.randn(N, N) * 0.01)
        self.r_init = nn.Parameter(torch.ones(N) * 0.0162)
        
    def get_W(self):
        # Dale's law with abs parameterization (avoids dying gradient):
        W = torch.zeros(self.N, self.N, device=self.U.device)
        W[:, :self.NE] = torch.abs(self.U[:, :self.NE])
        W[:, self.NE:] = -torch.abs(self.U[:, self.NE:])
        # Zero diagonal
        diag_mask = 1.0 - torch.eye(self.N, device=self.U.device)
        W = W * diag_mask
        return W
        
    def forward(self, I, max_r=5.0):
        n_steps = I.shape[1]
        r = torch.clamp(self.r_init, min=0.0, max=max_r)
        
        r_all = [r]
        W = self.get_W()
        
        for step in range(1, n_steps):
            r_clamp = torch.clamp(r, min=0.0, max=max_r)
            act = torch.relu(torch.matmul(W, r_clamp) + I[:, step-1])
            dr_dt = (-r_clamp + self.k * (act ** self.n)) / self.tau
            r_next = r_clamp + self.dt * dr_dt
            r = torch.relu(r_next)
            r_all.append(r)
            
        return torch.stack(r_all, dim=1)

# Training configuration
model = SSNModel()
# We can use a slightly larger learning rate or standard 0.01
optimizer = optim.Adam(model.parameters(), lr=0.01)

# Split indices for validation (first 3 pulses for training, 4th for validation)
train_indices = list(range(46))
val_indices = list(range(45, 61))

n_epochs = 300

print("Starting training with abs(U) parameterization and no regularization...")
for epoch in range(n_epochs):
    optimizer.zero_grad()
    
    r_sim = model(train_I_t, max_r=5.0)
    r_sim_obs = r_sim[:, ::200]
    
    train_loss = torch.mean((r_sim_obs[:, train_indices] - train_r_obs_t[:, train_indices]) ** 2)
    
    loss = train_loss
    
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
    optimizer.step()
    
    with torch.no_grad():
        val_loss = torch.mean((r_sim_obs[:, val_indices] - train_r_obs_t[:, val_indices]) ** 2)
        train_nrmse = torch.sqrt(train_loss) / train_r_obs_t[:, train_indices].std()
        val_nrmse = torch.sqrt(val_loss) / train_r_obs_t[:, val_indices].std()
        W = model.get_W()
        
    if epoch % 10 == 0 or epoch == n_epochs - 1:
        print(f"Epoch {epoch:3d} | Train MSE: {train_loss.item():.6f} (nRMSE: {train_nrmse.item():.4f}) | Val MSE: {val_loss.item():.6f} (nRMSE: {val_nrmse.item():.4f}) | W_max: {torch.max(torch.abs(W)).item():.4f}")
