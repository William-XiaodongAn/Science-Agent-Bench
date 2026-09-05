import numpy as np
import sys
sys.path.insert(0, "/workspace/baseline")
import search_api

v = np.load("/workspace/data/train_data.npy")
s = np.load("/workspace/data/train_stim.npy")

evaluator = search_api.Evaluator(v, s, seed=0, budget=100)

# Let's define fine-grained hyperparameter grid
spectral_radii = [0.3, 0.4, 0.5, 0.6, 0.7]
leaks = [0.05, 0.08, 0.1, 0.12, 0.15]
ridges = [1.5e-07, 2e-07, 3e-07, 4e-07]
input_scales = [
    0.05, 0.1, 0.15, 0.2,
    {"bias": 0.1, "voltage": 0.1, "stimulus": 0.5},
    {"bias": 0.05, "voltage": 0.1, "stimulus": 0.3},
]

import random
random.seed(123)

configs = []
for _ in range(50):
    sr = random.choice(spectral_radii)
    lk = random.choice(leaks)
    rg = random.choice(ridges)
    isc = random.choice(input_scales)
    configs.append(dict(layers=(368,), voltage_feedback=True, spectral_radius=sr, leak=lk, ridge=rg, input_scale=isc))

results = []
for idx, cfg in enumerate(configs):
    try:
        score = evaluator.evaluate(cfg)
        results.append((score, cfg))
        print(f"Config {idx}: {score:.5f} | {cfg}")
    except Exception as e:
        pass

results.sort(key=lambda x: x[0])
print("\n--- TOP 10 FINE-TUNED ---")
for i, (score, cfg) in enumerate(results[:10]):
    print(f"{i+1}: {score:.5f} | {cfg}")
