import numpy as np
import torch
import torch.nn as nn

# Load model parameters and data
train_r_obs = np.load("/workspace/data/train_r_obs.npy")
eval_I = np.load("/workspace/data/eval_I.npy")
eval_I_t = torch.tensor(eval_I, dtype=torch.float32)

# Define model with exact same architecture
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
        
    def forward(self, I, max_r=100.0): # Use a high max_r to detect runaway
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

# Let's run a training process on all 4 pulses, then test stability on eval_I
# We will do 300 epochs of training on ALL data (indices 0 to 60)
train_r_obs_t = torch.tensor(train_r_obs, dtype=torch.float32)
train_I_t = torch.tensor(np.load("/workspace/data/train_I.npy"), dtype=torch.float32)

model = SSNModel()
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

print("Training on all data...")
for epoch in range(301):
    optimizer.zero_grad()
    r_sim = model(train_I_t, max_r=5.0) # clip at 5.0 during training to stay stable
    r_sim_obs = r_sim[:, ::200]
    loss = torch.mean((r_sim_obs - train_r_obs_t) ** 2)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
    optimizer.step()
    if epoch % 50 == 0:
        nrmse = torch.sqrt(loss) / train_r_obs_t.std()
        print(f"Epoch {epoch:3d} | MSE: {loss.item():.6f} | nRMSE: {nrmse.item():.4f}")

# Now, let's run the model on eval_I WITHOUT clamping r at a small value (let's use max_r=100.0)
# to see if it remains stable on eval_I.
print("Running on eval_I with max_r=100.0...")
with torch.no_grad():
    eval_r_sim = model(eval_I_t, max_r=100.0)
    print("eval_r_sim min:", eval_r_sim.min().item(), "max:", eval_r_sim.max().item())
    print("Does it contain NaN or Inf?", torch.isnan(eval_r_sim).any().item() or torch.isinf(eval_r_sim).any().item())
