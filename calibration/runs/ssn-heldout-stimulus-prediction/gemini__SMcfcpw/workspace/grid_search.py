import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

# Set random seed
torch.manual_seed(42)
np.random.seed(42)

# Load data
train_r_obs = np.load("/workspace/data/train_r_obs.npy")
train_I = np.load("/workspace/data/train_I.npy")
eval_I = np.load("/workspace/data/eval_I.npy")
xy = np.load("/workspace/data/xy.npy")

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
        self.U = nn.Parameter(torch.randn(N, N) * 0.01)
        self.r_init = nn.Parameter(torch.ones(N) * 0.0162)
        
    def get_W(self):
        W = torch.zeros(self.N, self.N, device=self.U.device)
        W[:, :self.NE] = torch.abs(self.U[:, :self.NE])
        W[:, self.NE:] = -torch.abs(self.U[:, self.NE:])
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

# List of hyperparams to search
reg_l2_list = [1e-5, 3e-5, 1e-4, 3e-4, 1e-3]
reg_dist_list = [0.0, 1e-5, 1e-4, 1e-3]

results = []

for reg_l2 in reg_l2_list:
    for reg_dist in reg_dist_list:
        print(f"\n--- Testing reg_l2={reg_l2:.2e}, reg_dist={reg_dist:.2e} ---")
        torch.manual_seed(42)
        np.random.seed(42)
        
        model = SSNModel()
        optimizer = optim.Adam(model.parameters(), lr=0.01)
        
        # Train for 150 epochs
        for epoch in range(151):
            optimizer.zero_grad()
            r_sim = model(train_I_t, max_r=5.0)
            r_sim_obs = r_sim[:, ::200]
            
            train_loss = torch.mean((r_sim_obs - train_r_obs_t) ** 2)
            
            W = model.get_W()
            l2_reg_loss = torch.mean(W ** 2)
            dist_reg_loss = torch.mean((W ** 2) * dist_sq)
            
            loss = train_loss + reg_l2 * l2_reg_loss + reg_dist * dist_reg_loss
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            
        # Evaluate stability on eval_I
        with torch.no_grad():
            eval_r_sim = model(eval_I_t, max_r=100.0)
            eval_max = eval_r_sim.max().item()
            train_nrmse = (torch.sqrt(train_loss) / train_r_obs_t.std()).item()
            
        is_stable = eval_max < 10.0
        print(f"Result: Train nRMSE = {train_nrmse:.4f} | Eval Max Rate = {eval_max:.4f} | Stable? {is_stable}")
        results.append({
            'reg_l2': reg_l2,
            'reg_dist': reg_dist,
            'train_nrmse': train_nrmse,
            'eval_max': eval_max,
            'is_stable': is_stable
        })

# Print summary of stable runs
print("\n=== SUMMARY OF STABLE RUNS ===")
stable_runs = [r for r in results if r['is_stable']]
stable_runs = sorted(stable_runs, key=lambda x: x['train_nrmse'])
for r in stable_runs:
    print(f"reg_l2={r['reg_l2']:.2e}, reg_dist={r['reg_dist']:.2e} -> Train nRMSE={r['train_nrmse']:.4f}, Eval Max={r['eval_max']:.4f}")
