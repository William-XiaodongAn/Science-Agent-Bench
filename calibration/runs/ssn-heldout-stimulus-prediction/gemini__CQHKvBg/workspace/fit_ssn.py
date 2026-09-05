import torch
import torch.nn as nn
import numpy as np
import time

# Check if CUDA is available (though sandbox says CPU only, we write device-agnostic code)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)

# Load data and constants
train_r_obs = torch.tensor(np.load("data/train_r_obs.npy"), dtype=torch.float32, device=device)
train_I = torch.tensor(np.load("data/train_I.npy"), dtype=torch.float32, device=device)
t_obs = np.load("data/t_obs.npy")
obs_indices = (t_obs / 0.01).astype(int)

N = 49
NE = 29
NI = 20
n_steps = 12001
dt = 0.01
tau = 0.5
k = 0.5
n = 2.0
dt_tau = dt / tau

# Initialize parameters
# W_raw_E is for excitatory units (columns 0-28)
# W_raw_I is for inhibitory units (columns 29-48)
# Both are positive raw variables, clamped to >=0 during forward
W_raw_E = torch.full((N, NE), 0.01, dtype=torch.float32, device=device, requires_grad=True)
W_raw_I = torch.full((N, NI), 0.01, dtype=torch.float32, device=device, requires_grad=True)

# Initial rate r0, initialized with the observed initial rate
r0 = torch.tensor(train_r_obs[:, 0], dtype=torch.float32, device=device, requires_grad=True)

# Optimizer
optimizer = torch.optim.Adam([W_raw_E, W_raw_I, r0], lr=0.01)

# Training loop
n_epochs = 200
for epoch in range(1, n_epochs + 1):
    start_time = time.time()
    
    # Construct W matching Dale's law and zero diagonal
    W_E = torch.clamp(W_raw_E, min=0.0)
    W_I = -torch.clamp(W_raw_I, min=0.0)
    W = torch.cat([W_E, W_I], dim=1) # (N, N)
    W = W * (1.0 - torch.eye(N, device=device))
    
    # Simulate
    r = r0
    r_list = [r]
    for t in range(n_steps - 1):
        drive = train_I[:, t]
        input_to_units = torch.matmul(W, r) + drive
        rectified_input = torch.clamp(input_to_units, min=0.0)
        ss_rate = k * torch.pow(rectified_input, n)
        dr_dt = -r + ss_rate
        r_next = r + dt_tau * dr_dt
        # Clip rates to prevent explosion during early/unstable training phases
        r = torch.clamp(r_next, min=0.0, max=5.0)
        
        if (t + 1) % 200 == 0:
            r_list.append(r)
            
    r_sim_obs = torch.stack(r_list, dim=1)
    
    # Loss: MSE + small L2 weight penalty
    mse_loss = torch.mean((r_sim_obs - train_r_obs) ** 2)
    l2_reg = 1e-5 * (torch.sum(W_raw_E ** 2) + torch.sum(W_raw_I ** 2))
    loss = mse_loss + l2_reg
    
    optimizer.zero_grad()
    loss.backward()
    
    # Clip gradients to prevent gradient explosion
    torch.nn.utils.clip_grad_norm_([W_raw_E, W_raw_I, r0], max_norm=1.0)
    
    optimizer.step()
    
    elapsed = time.time() - start_time
    if epoch == 1 or epoch % 10 == 0:
        print(f"Epoch {epoch:03d} | Loss: {loss.item():.6f} | MSE: {mse_loss.item():.6f} | Time: {elapsed:.2f}s")
