import numpy as np

train_r_obs = np.load("/workspace/data/train_r_obs.npy")
t_obs = np.load("/workspace/data/t_obs.npy")

# Let's print the sum of observed rates at each timepoint to see the pulses
sum_r = train_r_obs.sum(axis=0)
for i, (time, s) in enumerate(zip(t_obs, sum_r)):
    print(f"Index {i:2d}: t={time:5.1f}, sum_r={s:7.4f}")
