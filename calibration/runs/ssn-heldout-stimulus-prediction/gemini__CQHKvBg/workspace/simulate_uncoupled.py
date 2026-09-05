import numpy as np

# Load constants
tau = 0.5
k = 0.5
n = 2.0
dt = 0.01
T = 120.0
n_steps = 12001
N = 49

train_r_obs = np.load("data/train_r_obs.npy")
train_I = np.load("data/train_I.npy")
t_obs = np.load("data/t_obs.npy")
obs_indices = (t_obs / dt).astype(int)

# Simulate with W = 0
r = np.zeros((N, n_steps))
# What should r[:, 0] be? Let's use train_r_obs[:, 0] as initial state
r[:, 0] = train_r_obs[:, 0]

dt_tau = dt / tau
for t in range(n_steps - 1):
    # input at time t
    drive = train_I[:, t]
    # W * r is 0
    rectified_input = np.maximum(0, drive)
    ss_rate = k * (rectified_input ** n)
    dr_dt = -r[:, t] + ss_rate
    r_next = r[:, t] + dt_tau * dr_dt
    r[:, t+1] = np.maximum(0, r_next)

# Compute MSE
r_sim_obs = r[:, obs_indices]
mse = np.mean((r_sim_obs - train_r_obs) ** 2)
print("Uncoupled (W=0) MSE against train_r_obs:", mse)

# Let's compare with a do-nothing baseline (predicting each neuron's mean rate)
neuron_means = train_r_obs.mean(axis=1, keepdims=True)
do_nothing_pred = np.repeat(neuron_means, 61, axis=1)
do_nothing_mse = np.mean((do_nothing_pred - train_r_obs) ** 2)
print("Do-nothing mean baseline MSE:", do_nothing_mse)
