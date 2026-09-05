import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

# Set seed for reproducibility
torch.manual_seed(42)
np.random.seed(42)

# Load constants and data
dt = 0.01
tau = 0.5
k = 0.5
n = 2.0
n_timepoints = 12001

train_r_obs_np = np.load("data/train_r_obs.npy")
t_obs_np = np.load("data/t_obs.npy")
train_I_np = np.load("data/train_I.npy")
eval_I_np = np.load("data/eval_I.npy")
xy_np = np.load("data/xy.npy")
W_init_np = np.load("data/W_best_stable.npy")

# Convert to torch tensors
device = torch.device("cpu")
train_r_obs = torch.tensor(train_r_obs_np, dtype=torch.float32, device=device)
train_I = torch.tensor(train_I_np, dtype=torch.float32, device=device)
eval_I = torch.tensor(eval_I_np, dtype=torch.float32, device=device)
xy = torch.tensor(xy_np, dtype=torch.float32, device=device)

# Distance matrix for spatial penalty
dist_matrix = torch.zeros(49, 49, device=device)
for i in range(49):
    for j in range(49):
        dist_matrix[i, j] = torch.norm(xy[i] - xy[j])

# Parameterize W:
# W[:, :29] = ReLU(X[:, :29])
# W[:, 29:] = -ReLU(X[:, 29:])
# with diagonal filled with 0.
X_init = torch.zeros(49, 49, dtype=torch.float32, device=device)
X_init[:, :29] = torch.tensor(W_init_np[:, :29], dtype=torch.float32)
X_init[:, 29:] = -torch.tensor(W_init_np[:, 29:], dtype=torch.float32)
X_init = torch.clamp(X_init, min=0.0)

X = nn.Parameter(X_init)

# Optimizer
optimizer = optim.Adam([X], lr=0.001)

# Target std for normalization
std_obs = train_r_obs.std().item()

best_train_nrmse = 999.0
best_W_stable_fine = None

for epoch in range(301):
    optimizer.zero_grad()
    
    W_rect = torch.zeros(49, 49, device=device)
    W_rect[:, :29] = torch.relu(X[:, :29])
    W_rect[:, 29:] = -torch.relu(X[:, 29:])
    W_rect.fill_diagonal_(0.0)
    
    # 1. Simulate training condition
    r_train = torch.zeros(49, device=device)
    r_sim_all = []
    
    for t_idx in range(n_timepoints - 1):
        drive = train_I[:, t_idx]
        rec = torch.matmul(W_rect, r_train) + drive
        rec_rect = torch.clamp(rec, min=0.0)
        r_ss = k * (rec_rect ** n)
        dr = (-r_train + r_ss) / tau
        r_train = torch.clamp(r_train + dt * dr, min=0.0)
        
        if (t_idx + 1) % 200 == 0:
            r_sim_all.append(r_train)
            
    r_sim_all = [torch.zeros(49, device=device)] + r_sim_all
    r_sim_tensor = torch.stack(r_sim_all, dim=1)
    
    # Compute train nRMSE
    rmse = torch.sqrt(torch.mean((r_sim_tensor - train_r_obs) ** 2))
    nrmse = rmse / std_obs
    
    # 2. Simulate evaluation condition (unobserved, but we enforce stability)
    r_eval = torch.zeros(49, device=device)
    max_eval_rate = torch.tensor(0.0, device=device)
    
    for t_idx in range(n_timepoints - 1):
        drive = eval_I[:, t_idx]
        rec = torch.matmul(W_rect, r_eval) + drive
        rec_rect = torch.clamp(rec, min=0.0)
        r_ss = k * (rec_rect ** n)
        dr = (-r_eval + r_ss) / tau
        r_eval = torch.clamp(r_eval + dt * dr, min=0.0)
        
        # Track the maximum rate seen during evaluation
        max_eval_rate = torch.max(max_eval_rate, r_eval.max())
    
    # Stability penalty on evaluation condition: penalize if max evaluation rate > 1.0
    stability_loss = torch.relu(max_eval_rate - 1.0) ** 2
    
    # Regularization
    spatial_loss = torch.sum((W_rect ** 2) * (dist_matrix ** 2))
    l2_loss = torch.sum(W_rect ** 2)
    
    # Combined loss
    loss = nrmse + 10.0 * stability_loss + 1e-4 * spatial_loss + 1e-5 * l2_loss
    
    loss.backward()
    torch.nn.utils.clip_grad_norm_([X], max_norm=0.5)
    optimizer.step()
    
    if epoch % 20 == 0:
        print(f"Epoch {epoch:3d} | Train nRMSE: {nrmse.item():.4f} | Stability Loss: {stability_loss.item():.4f} | Max Eval Rate: {max_eval_rate.item():.3f} | Spatial: {spatial_loss.item():.4f}")
        
    # We only save the weight matrix if the evaluation simulation remains completely stable!
    if max_eval_rate.item() < 1.0:
        if nrmse.item() < best_train_nrmse:
            best_train_nrmse = nrmse.item()
            best_W_stable_fine = W_rect.detach().cpu().numpy()

print(f"\nBest Stable Fine-tuned Train nRMSE: {best_train_nrmse:.4f}")
if best_W_stable_fine is not None:
    np.save("data/W_best_stable_fine.npy", best_W_stable_fine)
else:
    print("Warning: No stable weight matrix found during fine-tuning!")
