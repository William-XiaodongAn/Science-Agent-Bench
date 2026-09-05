import numpy as np

train_r_obs = np.load("data/train_r_obs.npy")
train_I = np.load("data/train_I.npy")
eval_I = np.load("data/eval_I.npy")
t = np.load("data/t.npy")
t_obs = np.load("data/t_obs.npy")
xy = np.load("data/xy.npy")

print("train_r_obs shape:", train_r_obs.shape, "dtype:", train_r_obs.dtype, "min:", train_r_obs.min(), "max:", train_r_obs.max(), "mean:", train_r_obs.mean(), "std:", train_r_obs.std())
print("train_I shape:", train_I.shape, "dtype:", train_I.dtype, "min:", train_I.min(), "max:", train_I.max(), "mean:", train_I.mean(), "std:", train_I.std())
print("eval_I shape:", eval_I.shape, "dtype:", eval_I.dtype, "min:", eval_I.min(), "max:", eval_I.max(), "mean:", eval_I.mean(), "std:", eval_I.std())
print("t shape:", t.shape, "min:", t.min(), "max:", t.max(), "step:", t[1] - t[0])
print("t_obs shape:", t_obs.shape, "min:", t_obs.min(), "max:", t_obs.max())
print("xy shape:", xy.shape, "min:", xy.min(axis=0), "max:", xy.max(axis=0))

# Check index matching
obs_indices = (t_obs / 0.01).astype(int)
print("Observed timepoints indices first 10:", obs_indices[:10])
print("Are t_obs exactly equal to t[obs_indices]?", np.allclose(t_obs, t[obs_indices]))
