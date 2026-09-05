import torch
import torch.nn as nn
import numpy as np

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

d_np = np.zeros((N, N))
for i in range(N):
    for j in range(N):
        d_np[i, j] = np.linalg.norm(xy_np[i] - xy_np[j])

train_obs_mask = t_obs <= 90.0
val_obs_mask = t_obs > 90.0

def test_gaussian(l2_reg_weight=1e-5, n_epochs=120):
    train_r_obs = torch.tensor(train_r_obs_np, dtype=torch.float32, device=device)
    train_I = torch.tensor(train_I_np, dtype=torch.float32, device=device)
    d = torch.tensor(d_np, dtype=torch.float32, device=device)
    
    W_raw_E = torch.full((N, NE), 0.01, dtype=torch.float32, device=device, requires_grad=True)
    W_raw_I = torch.full((N, NI), 0.01, dtype=torch.float32, device=device, requires_grad=True)
    r0 = torch.tensor(train_r_obs_np[:, 0], dtype=torch.float32, device=device, requires_grad=True)
    
    log_sigma_EE = torch.tensor(0.4, dtype=torch.float32, device=device, requires_grad=True)
    log_sigma_EI = torch.tensor(0.4, dtype=torch.float32, device=device, requires_grad=True)
    log_sigma_IE = torch.tensor(0.4, dtype=torch.float32, device=device, requires_grad=True)
    log_sigma_II = torch.tensor(0.4, dtype=torch.float32, device=device, requires_grad=True)
    
    params = [W_raw_E, W_raw_I, r0, log_sigma_EE, log_sigma_EI, log_sigma_IE, log_sigma_II]
    optimizer = torch.optim.Adam(params, lr=0.01)
    
    best_val_mse = float('inf')
    best_train_mse = 0.0
    
    for epoch in range(1, n_epochs + 1):
        s_EE = torch.exp(log_sigma_EE)
        s_EI = torch.exp(log_sigma_EI)
        s_IE = torch.exp(log_sigma_IE)
        s_II = torch.exp(log_sigma_II)
        
        scale_matrix = torch.zeros((N, N), device=device)
        scale_matrix[:NE, :NE] = s_EE
        scale_matrix[:NE, NE:] = s_EI
        scale_matrix[NE:, :NE] = s_IE
        scale_matrix[NE:, NE:] = s_II
        
        # Gaussian envelope
        envelope = torch.exp(- (d ** 2) / (2.0 * (scale_matrix ** 2)))
        
        W_E = torch.clamp(W_raw_E, min=0.0)
        W_I = -torch.clamp(W_raw_I, min=0.0)
        W = torch.cat([W_E, W_I], dim=1)
        W = W * envelope
        W = W * (1.0 - torch.eye(N, device=device))
        
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
        
        train_mse = torch.mean((r_sim_obs[:, train_obs_mask] - train_r_obs[:, train_obs_mask]) ** 2)
        val_mse = torch.mean((r_sim_obs[:, val_obs_mask] - train_r_obs[:, val_obs_mask]) ** 2)
        
        reg_loss = l2_reg_weight * (torch.sum(W_raw_E ** 2) + torch.sum(W_raw_I ** 2))
        loss = train_mse + reg_loss
        
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, max_norm=1.0)
        optimizer.step()
        
        val_mse_val = val_mse.item()
        if val_mse_val < best_val_mse:
            best_val_mse = val_mse_val
            best_train_mse = train_mse.item()
            
    print(f"Gaussian Envelope | L2: {l2_reg_weight:.1e} | Best Val MSE: {best_val_mse:.6f} | Train MSE: {best_train_mse:.6f}")
    print(f"    Scales: EE={s_EE.item():.2f}, EI={s_EI.item():.2f}, IE={s_IE.item():.2f}, II={s_II.item():.2f}")

test_gaussian()
