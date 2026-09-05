import numpy as np

train_r_obs = np.load("/workspace/data/train_r_obs.npy")
t_obs = np.load("/workspace/data/t_obs.npy")
train_I = np.load("/workspace/data/train_I.npy")
eval_I = np.load("/workspace/data/eval_I.npy")
t = np.load("/workspace/data/t.npy")
xy = np.load("/workspace/data/xy.npy")

print("train_r_obs shape:", train_r_obs.shape, "min:", train_r_obs.min(), "max:", train_r_obs.max(), "mean:", train_r_obs.mean())
print("t_obs shape:", t_obs.shape, "min:", t_obs.min(), "max:", t_obs.max())
print("train_I shape:", train_I.shape, "min:", train_I.min(), "max:", train_I.max(), "mean:", train_I.mean())
print("eval_I shape:", eval_I.shape, "min:", eval_I.min(), "max:", eval_I.max(), "mean:", eval_I.mean())
print("t shape:", t.shape, "min:", t.min(), "max:", t.max())
print("xy shape:", xy.shape)
print("First few xy coords:")
print(xy[:5])
