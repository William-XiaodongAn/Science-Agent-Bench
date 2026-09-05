import numpy as np

train_r_obs = np.load("data/train_r_obs.npy")
train_I = np.load("data/train_I.npy")
eval_I = np.load("data/eval_I.npy")

print("train_r_obs at t=0:")
print(train_r_obs[:, 0])

print("train_I at t=0:")
print(train_I[:, 0])

print("eval_I at t=0:")
print(eval_I[:, 0])

print("Are train_I[:, 0] and eval_I[:, 0] equal?")
print(np.allclose(train_I[:, 0], eval_I[:, 0]))
