import numpy as np
train_r_obs = np.load("/workspace/data/train_r_obs.npy")
print("r_obs at t=0:")
print(train_r_obs[:, 0])
print("Mean at t=0:", train_r_obs[:, 0].mean())
print("Std at t=0:", train_r_obs[:, 0].std())
print("Min at t=0:", train_r_obs[:, 0].min())
print("Max at t=0:", train_r_obs[:, 0].max())
