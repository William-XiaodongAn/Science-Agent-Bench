import numpy as np
import sys
sys.path.insert(0, "/workspace/baseline")
import search_api

v = np.load("/workspace/data/train_data.npy")
s = np.load("/workspace/data/train_stim.npy")

evaluator = search_api.Evaluator(v, s, seed=0, budget=100)

configs = [
    # feedback = False, low leak, varying spectral radius
    dict(layers=(368,), voltage_feedback=False, spectral_radius=0.1, leak=0.1, ridge=1e-6),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=0.5, leak=0.1, ridge=1e-6),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=0.9, leak=0.1, ridge=1e-6),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=0.1, ridge=1e-6),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.3, leak=0.1, ridge=1e-6),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.5, leak=0.1, ridge=1e-6),
    # varying leak
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=0.05, ridge=1e-6),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=0.02, ridge=1e-6),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=0.01, ridge=1e-6),
    # varying ridge
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=0.05, ridge=1e-5),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=0.05, ridge=1e-7),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=0.05, ridge=1e-8),
    # varying input scale
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=0.05, ridge=1e-6, input_scale=0.05),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=0.05, ridge=1e-6, input_scale=0.2),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=0.05, ridge=1e-6, input_scale=0.5),
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=0.05, ridge=1e-6, input_scale=1.0),
]

for i, cfg in enumerate(configs):
    try:
        score = evaluator.evaluate(cfg)
        print(f"Config {i}: {cfg} -> Dev RMSE: {score:.5f}")
    except Exception as e:
        print(f"Config {i} failed: {e}")
