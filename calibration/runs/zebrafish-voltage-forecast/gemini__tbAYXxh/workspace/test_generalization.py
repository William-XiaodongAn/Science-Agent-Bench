import numpy as np
import sys
sys.path.insert(0, "/workspace/baseline")
import search_api

v = np.load("/workspace/data/train_data.npy")
s = np.load("/workspace/data/train_stim.npy")

candidates = [
    # 1. Best with feedback
    dict(layers=(368,), voltage_feedback=True, spectral_radius=0.5, leak=0.1, ridge=1e-06, input_scale=0.1),
    # 2. Best with no feedback
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.3, leak=0.1, ridge=1e-06, input_scale=0.1),
    # 3. Another with no feedback, larger input_scale
    dict(layers=(368,), voltage_feedback=False, spectral_radius=1.1, leak=0.05, ridge=1e-06, input_scale=0.2),
    # 4. Multilayer with feedback
    dict(layers=(184, 184), voltage_feedback=True, spectral_radius=0.7, leak=0.1, ridge=0.001, input_scale=0.1, inter_scale=0.2, all_layers_to_output=False, input_to_all_layers=True),
    # 5. Default but lower ridge
    dict(layers=(368,), voltage_feedback=True, spectral_radius=0.9, leak=0.5, ridge=1e-05, input_scale=0.1),
]

for idx, config in enumerate(candidates):
    print(f"\n--- Candidate {idx}: {config} ---")
    scores = []
    for seed in range(5):
        evaluator = search_api.Evaluator(v, s, seed=seed, budget=10)
        try:
            score = evaluator.evaluate(config)
            scores.append(score)
            print(f"  Seed {seed} -> Dev RMSE: {score:.5f}")
        except Exception as e:
            print(f"  Seed {seed} failed: {e}")
    if len(scores) == 5:
        print(f"  Mean Dev RMSE: {np.mean(scores):.5f} (std: {np.std(scores):.5f})")
    else:
        print(f"  Incomplete results (only {len(scores)}/5 seeds succeeded)")
