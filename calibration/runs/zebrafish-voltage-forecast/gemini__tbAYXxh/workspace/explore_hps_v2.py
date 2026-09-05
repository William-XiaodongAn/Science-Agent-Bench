import numpy as np
import sys
import itertools
sys.path.insert(0, "/workspace/baseline")
import search_api

v = np.load("/workspace/data/train_data.npy")
s = np.load("/workspace/data/train_stim.npy")

evaluator = search_api.Evaluator(v, s, seed=0, budget=1000)

# Let's perform a grid search on seed 0 to see how low we can get
results = []

# Define grids
spectral_radii = [0.1, 0.3, 0.5, 0.7, 0.9]
leaks = [0.1, 0.3, 0.5, 0.7, 0.9, 0.95, (0.1, 0.9), (0.3, 0.99)]
ridges = [1e-3, 1e-4, 1e-5, 1e-6, 1e-7]
input_scales = [
    0.1,
    0.05,
    0.2,
    {"bias": 0.1, "voltage": 0.1, "stimulus": 0.5},
    {"bias": 0.05, "voltage": 0.1, "stimulus": 0.2},
    {"bias": 0.1, "voltage": 0.5, "stimulus": 0.1},
    {"bias": 0.1, "voltage": 0.2, "stimulus": 0.3},
]
layers_opts = [
    (368,),
    (184, 184),
]

# Since a full grid of 5 * 8 * 5 * 7 * 2 = 2800 is too large, let's do a smart random coordinate search or a random search first.
# Let's sample 100 random combinations and evaluate them.
import random
random.seed(42)

for _ in range(80):
    sr = random.choice(spectral_radii)
    lk = random.choice(leaks)
    rg = random.choice(ridges)
    isc = random.choice(input_scales)
    lyr = random.choice(layers_opts)
    
    config = {
        "layers": lyr,
        "spectral_radius": sr,
        "leak": lk,
        "ridge": rg,
        "input_scale": isc,
    }
    
    # If layers is 2-layer, we might want to also randomly choose inter_scale and connectivity
    if len(lyr) == 2:
        config["inter_scale"] = random.choice([0.0, 0.1, 0.2])
        config["all_layers_to_output"] = random.choice([True, False])
        config["input_to_all_layers"] = random.choice([True, False])
        
    try:
        score = evaluator.evaluate(config)
        results.append((score, config))
        print(f"Score: {score:.5f} for {config}")
    except Exception as e:
        print(f"Failed configuration {config}: {e}")

results.sort(key=lambda x: x[0])
print("\n--- TOP 10 CONFIGURATIONS ---")
for i, (score, config) in enumerate(results[:10]):
    print(f"{i+1}: Score={score:.5f} | {config}")
