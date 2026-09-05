import numpy as np
import sys
sys.path.insert(0, "/workspace/baseline")
import search_api

v = np.load("/workspace/data/train_data.npy")
s = np.load("/workspace/data/train_stim.npy")

# Let's test a few specific configurations on seed 0 using Evaluator
evaluator = search_api.Evaluator(v, s, seed=0, budget=100)

configs_to_test = [
    # Default
    dict(layers=(368,)),
    # Let's see if increasing spectral radius helps
    dict(layers=(368,), spectral_radius=1.2),
    # Let's see if lowering spectral radius helps
    dict(layers=(368,), spectral_radius=0.5),
    # Let's see if leak rate helps
    dict(layers=(368,), leak=0.1),
    dict(layers=(368,), leak=0.9),
    # Let's see if per-neuron log-uniform leaks help
    dict(layers=(368,), leak=(0.05, 0.95)),
    # Let's see if input scale helps
    dict(layers=(368,), input_scale=0.01),
    dict(layers=(368,), input_scale=1.0),
    # Let's try dict input scale
    dict(layers=(368,), input_scale={"bias": 0.1, "voltage": 0.1, "stimulus": 0.5}),
    dict(layers=(368,), input_scale={"bias": 0.05, "voltage": 0.5, "stimulus": 0.2}),
    # Let's try ridge
    dict(layers=(368,), ridge=1e-5),
    dict(layers=(368,), ridge=1e-1),
    # Let's try readout_halflife
    dict(layers=(368,), readout_halflife=2000),
]

for i, cfg in enumerate(configs_to_test):
    score = evaluator.evaluate(cfg)
    print(f"Config {i}: {cfg} -> Dev RMSE: {score:.5f}")
