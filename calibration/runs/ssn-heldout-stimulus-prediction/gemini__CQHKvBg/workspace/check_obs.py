import numpy as np

train_r_obs = np.load("data/train_r_obs.npy")
train_I = np.load("data/train_I.npy")
t_obs = np.load("data/t_obs.npy")
xy = np.load("data/xy.npy")

print("First 5 timepoints of train_r_obs for neuron 0:")
print(train_r_obs[0, :5])

print("Let's look at train_I for neuron 0 at first 5 obs indices:")
obs_indices = (t_obs / 0.01).astype(int)
print(train_I[0, obs_indices[:5]])

# Compute some basic statistics of train_r_obs over neurons
print("Mean rate of each neuron over time:")
means = train_r_obs.mean(axis=1)
print("Min mean:", means.min(), "Max mean:", means.max())

# Let's see how much variation there is in train_I over neurons and time
print("train_I mean per neuron:")
I_means = train_I.mean(axis=1)
print("Min I_mean:", I_means.min(), "Max I_mean:", I_means.max())
