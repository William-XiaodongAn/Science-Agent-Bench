import torch
import torch.nn as nn
import numpy as np
import time

device = torch.device("cpu")

# Load data
train_r_obs_np = np.load("data/train_r_obs.npy")
train_I_np = np.load("data/train_I.npy")
t_obs = np.load("data/t_obs.npy")
xy_np = np.load("data/xy.npy")

N = 49
NE = 29
NI = 20
dt = 0.01
tau = 0.5
k = 0.5
n = 2.0
dt_tau = dt / tau

# Precompute distances
d_np = np.zeros((N, N))
for i in range(N):
    for j in range(N):
        d_np[i, j] = np.linalg.norm(xy_np[i] - xy_np[j])

# Train / Val indices
# train_I has 12001 steps, corresponding to t=0..120
# t_obs has 61 steps (every 200 steps). Let's train on first 45 obs (t <= 90) and validate on the remaining 16 (t > 90)
train_obs_mask = t_obs <= 90.0
val_obs_mask = t_obs > 90.0

print(f"Num training observations: {np.sum(train_obs_mask)}")
print(f"Num validation observations: {np.sum(val_obs_mask)}")

def evaluate_config(use_spatial=True, learn_scales=True, l2_reg_weight=1e-5, n_epochs=150, lr=0.01):
    # Convert arrays to PyTorch tensors
    train_r_obs = torch.tensor(train_r_obs_np, dtype=torch.float32, device=device)
    train_I = torch.tensor(train_I_np, dtype=torch.float32, device=device)
    d = torch.tensor(d_np, dtype=torch.float32, device=device)
    
    # Parameters
    W_raw_E = torch.full((N, NE), 0.01, dtype=torch.float32, device=device, requires_grad=True)
    W_raw_I = torch.full((N, NI), 0.01, dtype=torch.float32, device=device, requires_grad=True)
    r0 = torch.tensor(train_r_obs_np[:, 0], dtype=torch.float32, device=device, requires_grad=True)
    
    params = [W_raw_E, W_raw_I, r0]
    
    if use_spatial and learn_scales:
        log_sigma_EE = torch.tensor(0.4, dtype=torch.float32, device=device, requires_grad=True) # log(1.5)
        log_sigma_EI = torch.tensor(0.4, dtype=torch.float32, device=device, requires_grad=True)
        log_sigma_IE = torch.tensor(0.4, dtype=torch.float32, device=device, requires_grad=True)
        log_sigma_II = torch.tensor(0.4, dtype=torch.float32, device=device, requires_grad=True)
        params.extend([log_sigma_EE, log_sigma_EI, log_sigma_IE, log_sigma_II])
    else:
        # Fixed scales
        s_EE = s_EI = s_IE = s_II = 1.5
        
    optimizer = torch.optim.Adam(params, lr=lr)
    
    best_val_mse = float('inf')
    best_epoch = 0
    
    for epoch in range(1, n_epochs + 1):
        # 1. Build spatial envelope if used
        if use_spatial:
            if learn_scales:
                s_EE = torch.exp(log_sigma_EE)
                s_EI = torch.exp(log_sigma_EI)
                s_IE = torch.exp(log_sigma_IE)
                s_II = torch.exp(log_sigma_II)
            
            scale_matrix = torch.zeros((N, N), device=device)
            scale_matrix[:NE, :NE] = s_EE
            scale_matrix[:NE, NE:] = s_EI
            scale_matrix[NE:, :NE] = s_IE
            scale_matrix[NE:, NE:] = s_II
            
            envelope = torch.exp(- d / scale_matrix)
        else:
            envelope = 1.0
            
        # 2. Construct W matching Dale's law and zero diagonal
        W_E = torch.clamp(W_raw_E, min=0.0)
        W_I = -torch.clamp(W_raw_I, min=0.0)
        W = torch.cat([W_E, W_I], dim=1) # (N, N)
        W = W * envelope
        W = W * (1.0 - torch.eye(N, device=device))
        
        # 3. Simulate
        r = r0
        r_list = [r]
        for t in range(12001 - 1):
            drive = train_I[:, t]
            input_to_units = torch.matmul(W, r) + drive
            rectified_input = torch.clamp(input_to_units, min=0.0)
            ss_rate = k * torch.pow(rectified_input, n)
            dr_dt = -r + ss_rate
            r_next = r + dt_tau * dr_dt
            r = torch.clamp(r_next, min=0.0, max=5.0)
            
            if (t + 1) % 200 == 0:
                r_list.append(r)
                
        r_sim_obs = torch.stack(r_list, dim=1)
        
        # 4. Losses
        # Compute MSE only on training timepoints
        train_mse = torch.mean((r_sim_obs[:, train_obs_mask] - train_r_obs[:, train_obs_mask]) ** 2)
        val_mse = torch.mean((r_sim_obs[:, val_obs_mask] - train_r_obs[:, val_obs_mask]) ** 2)
        
        # L2 weight decay on raw weights
        l2_reg = l2_reg_weight * (torch.sum(W_raw_E ** 2) + torch.sum(W_raw_I ** 2))
        
        loss = train_mse + l2_reg
        
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, max_norm=1.0)
        optimizer.step()
        
        val_mse_val = val_mse.item()
        if val_mse_val < best_val_mse:
            best_val_mse = val_mse_val
            best_epoch = epoch
            
    # Print results
    print(f"Config | Spatial: {use_spatial} | Learn scales: {learn_scales} | L2: {l2_reg_weight} | Best Val MSE: {best_val_mse:.6f} at epoch {best_epoch} | Train MSE: {train_mse.item():.6f}")
    if use_spatial and learn_scales:
        print(f"   Learned scales: s_EE={s_EE.item():.2f}, s_EI={s_EI.item():.2f}, s_IE={s_IE.item():.2f}, s_II={s_II.item():.2f}")
    return best_val_mse

# Run a few configs
print("Running baseline uncoupled model on validation part...")
# Baseline uncoupled (W=0) on train_obs_mask vs val_obs_mask
# We can load the simulation from simulate_uncoupled.py or just compute it
# Let's run evaluate_config with L2 = 1e9 to force W=0
evaluate_config(use_spatial=False, learn_scales=False, l2_reg_weight=1e3, n_epochs=1, lr=0.0)

print("\nRunning configuration evaluations:")
evaluate_config(use_spatial=False, learn_scales=False, l2_reg_weight=0.0, n_epochs=120)
evaluate_config(use_spatial=False, learn_scales=False, l2_reg_weight=1e-4, n_epochs=120)
evaluate_config(use_spatial=True, learn_scales=False, l2_reg_weight=1e-5, n_epochs=120)
evaluate_config(use_spatial=True, learn_scales=True, l2_reg_weight=1e-5, n_epochs=120)
evaluate_config(use_spatial=True, learn_scales=True, l2_reg_weight=1e-4, n_epochs=120)
