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

model = SSNModel()
optimizer = optim.Adam(model.parameters(), lr=0.01)

n_epochs = 301
stability_weight = 1e-3  # Weight for the stability penalty on eval_I

print("Training with direct stability loss on eval_I...")
for epoch in range(n_epochs):
    optimizer.zero_grad()
    
    # 1. Run simulation on train_I (clipping at 5.0 to be safe)
    r_sim_train = model(train_I_t, max_r=5.0)
    r_sim_obs = r_sim_train[:, ::200]
    
    # Compute MSE on training data
    train_loss = torch.mean((r_sim_obs - train_r_obs_t) ** 2)
    
    # 2. Run simulation on eval_I (clipping at 5.0 to prevent runaway NaNs)
    r_sim_eval = model(eval_I_t, max_r=5.0)
    
    # Stability loss: penalize simulated rates on eval_I that exceed 1.5
    # The true rates have a peak around 1.0, so anything > 1.5 is likely starting to run away
    stability_loss = torch.mean(torch.relu(r_sim_eval - 1.5) ** 2)
    
    loss = train_loss + stability_weight * stability_loss
    
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
    optimizer.step()
    
    if epoch % 50 == 0:
        train_nrmse = torch.sqrt(train_loss) / train_r_obs_t.std()
        print(f"Epoch {epoch:3d} | Train MSE: {train_loss.item():.6f} (nRMSE: {train_nrmse.item():.4f}) | Stability Loss: {stability_loss.item():.6f} | Eval Max Rate: {r_sim_eval.max().item():.4f}")

# Now, let's run the model on eval_I WITHOUT clamping r at 5.0 (let's use max_r=100.0)
# to see if the stability loss successfully prevented runaway!
print("\nTesting stability of final model on eval_I (max_r=100.0):")
with torch.no_grad():
    eval_r_sim = model(eval_I_t, max_r=100.0)
    print("eval_r_sim min:", eval_r_sim.min().item(), "max:", eval_r_sim.max().item())
    print("Is it stable (< 100.0)?", eval_r_sim.max().item() < 100.0)
