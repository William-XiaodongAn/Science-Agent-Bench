import numpy as np

train_I = np.load("/workspace/data/train_I.npy")
eval_I = np.load("/workspace/data/eval_I.npy")

print("train_I[:, 0] min, max, mean, std:")
print(train_I[:, 0].min(), train_I[:, 0].max(), train_I[:, 0].mean(), train_I[:, 0].std())
print("eval_I[:, 0] min, max, mean, std:")
print(eval_I[:, 0].min(), eval_I[:, 0].max(), eval_I[:, 0].mean(), eval_I[:, 0].std())

print("Are train_I[:, 0] and eval_I[:, 0] equal?")
print(np.allclose(train_I[:, 0], eval_I[:, 0]))

print("First few elements of train_I[:, 0]:")
print(train_I[:5, 0])
print("First few elements of eval_I[:, 0]:")
print(eval_I[:5, 0])
