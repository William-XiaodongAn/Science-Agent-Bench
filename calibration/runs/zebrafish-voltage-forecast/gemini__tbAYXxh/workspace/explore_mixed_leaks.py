import numpy as np
import sys
sys.path.insert(0, "/workspace/baseline")
import search_api

v = np.load("/workspace/data/train_data.npy")
s = np.load("/workspace/data/train_stim.npy")

evaluator = search_api.Evaluator(v, s, seed=0, budget=100)

configs = [
    # 1. With voltage feedback, per-neuron leaks
    dict(layers=(368,), voltage_feedback=True, spectral_radius=0.5, leak=(0.01, 0.5), ridge=1e-06, input_scale=0.1),
    dict(layers=(368,), voltage_feedback=True, spectral_radius=0.5, leak=(0.05, 0.5), ridge=1e-06, input_scale=0.1),
    dict(layers=(368,), voltage_feedback=True, spectral_radius=0.5, leak=(0.05, 0.95), ridge=1e-06, input_scale=0.1),
    dict(layers=(368,), voltage_feedback=True, spectral_radius=0.5, leak=(0.1, 0.9), ridge=1e-06, input_scale=0.1),
    # 2. Without voltage feedback, per-neuron leaks
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=(0.01, 0.5), ridge=1e-06, input_scale=0.2),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=(0.05, 0.5), ridge=1e-06, input_scale=0.2),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=(0.05, 0.95), ridge=1e-06, input_scale=0.2),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=(0.1, 0.9), ridge=1e-06, input_scale=0.2),
    # Let's also test different ridge values for Candidate 0 to see if 1e-7 or 1e-8 is better
    dict(layers=(368,), voltage_feedback=True, spectral_radius=0.5, leak=0.1, ridge=1e-07, input_scale=0.1),
    dict(layers=(368,), voltage_feedback=True, spectral_radius=0.5, leak=0.1, ridge=1e-08, input_scale=0.1),
    dict(layers=(368,), voltage_feedback=True, spectral_radius=0.5, leak=0.1, ridge=1e-05, input_scale=0.1),
]

for i, cfg in enumerate(configs):
    try:
        score = evaluator.evaluate(cfg)
        print(f"Config {i}: {cfg} -> Dev RMSE: {score:.5f}")
    except Exception as e:
        print(f"Config {i} failed: {e}")
