import numpy as np
import sys
sys.path.insert(0, "/workspace/baseline")
import search_api

v = np.load("/workspace/data/train_data.npy")
s = np.load("/workspace/data/train_stim.npy")

evaluator = search_api.Evaluator(v, s, seed=0, budget=100)

configs = [
    # No feedback, default parameters otherwise
    dict(layers=(368,), voltage_feedback=False),
    # No feedback, smaller/larger spectral radius
    dict(layers=(368,), voltage_feedback=False, spectral_radius=0.5),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=0.9),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.2),
    # No feedback, different leaks
    dict(layers=(368,), voltage_feedback=False, leak=0.1),
    dict(layers=(368,), voltage_feedback=False, leak=0.3),
    dict(layers=(368,), voltage_feedback=False, leak=0.5),
    dict(layers=(368,), voltage_feedback=False, leak=0.7),
    dict(layers=(368,), voltage_feedback=False, leak=0.9),
    # No feedback, per-neuron leaks
    dict(layers=(368,), voltage_feedback=False, leak=(0.05, 0.95)),
    # No feedback, ridge tuning
    dict(layers=(368,), voltage_feedback=False, ridge=1e-4),
    dict(layers=(368,), voltage_feedback=False, ridge=1e-5),
    dict(layers=(368,), voltage_feedback=False, ridge=1e-6),
    # Let's combine lower ridge with other parameters
    dict(layers=(368,), voltage_feedback=False, spectral_radius=0.9, leak=0.1, ridge=1e-6),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=0.9, leak=0.3, ridge=1e-6),
]

for i, cfg in enumerate(configs):
    try:
        score = evaluator.evaluate(cfg)
        print(f"Config {i}: {cfg} -> Dev RMSE: {score:.5f}")
    except Exception as e:
        print(f"Config {i} failed: {e}")
