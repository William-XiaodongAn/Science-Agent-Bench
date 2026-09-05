import torch
import torch.nn as nn
import numpy as np
import os

# Set seed for reproducibility
torch.manual_seed(42)
np.random.seed(42)

device = torch.device("cpu")

# Load data and constants
train_r_obs_np = np.load("data/train_r_obs.npy")
train_I_np = np.load("data/train_I.npy")
eval_I_np = np.load("data/eval_I.npy")
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

# Precompute distance matrix
d_np = np.zeros((N, N))
for i in range(N):
    for j in range(N):
        d_np[i, j] = np.linalg.norm(xy_np[i] - xy_np[j])

# Convert to PyTorch tensors
train_r_obs = torch.tensor(train_r_obs_np, dtype=torch.float32, device=device)
train_I = torch.tensor(train_I_np, dtype=torch.float32, device=device)
eval_I = torch.tensor(eval_I_np, dtype=torch.float32, device=device)
d = torch.tensor(d_np, dtype=torch.float32, device=device)

# Initialize parameters
W_raw_E = torch.full((N, NE), 0.01, dtype=torch.float32, device=device, requires_grad=True)
W_raw_I = torch.full((N, NI), 0.01, dtype=torch.float32, device=device, requires_grad=True)
r0 = torch.tensor(train_r_obs_np[:, 0], dtype=torch.float32, device=device, requires_grad=True)

log_sigma_EE = torch.tensor(0.4, dtype=torch.float32, device=device, requires_grad=True)
log_sigma_EI = torch.tensor(0.4, dtype=torch.float32, device=device, requires_grad=True)
log_sigma_IE = torch.tensor(0.4, dtype=torch.float32, device=device, requires_grad=True)
log_sigma_II = torch.tensor(0.4, dtype=torch.float32, device=device, requires_grad=True)

params = [W_raw_E, W_raw_I, r0, log_sigma_EE, log_sigma_EI, log_sigma_IE, log_sigma_II]
optimizer = torch.optim.Adam(params, lr=0.01)

n_epochs = 250
print("Starting training on full dataset (all 61 timepoints)...")

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
    
    # Gaussian spatial decay envelope
    envelope = torch.exp(- (d ** 2) / (2.0 * (scale_matrix ** 2)))
    
    # Dale's law and zero diagonal
    W_E = torch.clamp(W_raw_E, min=0.0)
    W_I = -torch.clamp(W_raw_I, min=0.0)
    W = torch.cat([W_E, W_I], dim=1)
    W = W * envelope
    W = W * (1.0 - torch.eye(N, device=device))
    
    # Simulate on training stimulus
    r = torch.clamp(r0, min=0.0)
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
    
    # Loss: MSE on all 61 observed timepoints + L2 regularization
    mse_loss = torch.mean((r_sim_obs - train_r_obs) ** 2)
    reg_loss = 1e-5 * (torch.sum(W_raw_E ** 2) + torch.sum(W_raw_I ** 2))
    loss = mse_loss + reg_loss
    
    optimizer.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(params, max_norm=1.0)
    optimizer.step()
    
    if epoch == 1 or epoch % 25 == 0:
        print(f"Epoch {epoch:03d} | Loss: {loss.item():.6f} | MSE: {mse_loss.item():.6f} | Scales: EE={s_EE.item():.2f}, EI={s_EI.item():.2f}, IE={s_IE.item():.2f}, II={s_II.item():.2f}")

# Final trained parameters
with torch.no_grad():
    s_EE = torch.exp(log_sigma_EE)
    s_EI = torch.exp(log_sigma_EI)
    s_IE = torch.exp(log_sigma_IE)
    s_II = torch.exp(log_sigma_II)
    
    scale_matrix = torch.zeros((N, N), device=device)
    scale_matrix[:NE, :NE] = s_EE
    scale_matrix[:NE, NE:] = s_EI
    scale_matrix[NE:, :NE] = s_IE
    scale_matrix[NE:, NE:] = s_II
    
    envelope = torch.exp(- (d ** 2) / (2.0 * (scale_matrix ** 2)))
    
    W_E = torch.clamp(W_raw_E, min=0.0)
    W_I = -torch.clamp(W_raw_I, min=0.0)
    W = torch.cat([W_E, W_I], dim=1)
    W = W * envelope
    W = W * (1.0 - torch.eye(N, device=device))

print("\n--- Final Training Summary ---")
print(f"Final training MSE: {mse_loss.item():.6f}")
print(f"Learned spatial scales: EE={s_EE.item():.3f}, EI={s_EI.item():.3f}, IE={s_IE.item():.3f}, II={s_II.item():.3f}")
print(f"W shape: {W.shape}")
print(f"W positive entries range: {W[W > 0].min().item():.5f} to {W[W > 0].max().item():.5f}")
print(f"W negative entries range: {W[W < 0].max().item():.5f} to {W[W < 0].min().item():.5f}")

# Predict on evaluation stimulus (unseen swept stimulus)
print("\nSimulating on evaluation stimulus (eval_I)...")
with torch.no_grad():
    r_eval = torch.clamp(r0, min=0.0)
    r_eval_list = [r_eval]
    for t in range(12001 - 1):
        drive = eval_I[:, t]
        input_to_units = torch.matmul(W, r_eval) + drive
        rectified_input = torch.clamp(input_to_units, min=0.0)
        ss_rate = k * torch.pow(rectified_input, n)
        dr_dt = -r_eval + ss_rate
        # Note: Do NOT use the clipping of 5.0 in the actual prediction unless necessary,
        # but the actual forward Euler rule clips at 0: max(0, r + dt * dr/dt)
        r_eval_next = r_eval + dt_tau * dr_dt
        r_eval = torch.clamp(r_eval_next, min=0.0)
        r_eval_list.append(r_eval)
        
    r_eval_pred = torch.stack(r_eval_list, dim=1)

# Check stability of predictions
pred_max = r_eval_pred.max().item()
pred_mean = r_eval_pred.mean().item()
print(f"Evaluation prediction max: {pred_max:.4f}")
print(f"Evaluation prediction mean: {pred_mean:.4f}")

# Check if there are any NaNs or Infs
if not torch.isfinite(r_eval_pred).all():
    print("WARNING: Prediction contains NaNs or Infs!")
else:
    print("Prediction is finite and clean.")

# Save submission deliverables
os.makedirs("submission", exist_ok=True)
np.save("submission/r_pred.npy", r_eval_pred.numpy())
print("Saved predicted rates to submission/r_pred.npy")
