import numpy as np
import sys
sys.path.insert(0, "/workspace/baseline")
import search_api

v = np.load("/workspace/data/train_data.npy")
s = np.load("/workspace/data/train_stim.npy")

configs = [
    # Best 1:
    dict(layers=(368,), voltage_feedback=True, spectral_radius=0.6, leak=0.1, ridge=1.5e-07, input_scale={'bias': 0.05, 'voltage': 0.1, 'stimulus': 0.3}),
    # Best 2:
    dict(layers=(368,), voltage_feedback=True, spectral_radius=0.5, leak=0.08, ridge=3e-07, input_scale={'bias': 0.1, 'voltage': 0.1, 'stimulus': 0.5}),
]

for idx, config in enumerate(configs):
    print(f"\n--- Config {idx}: {config} ---")
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
        print(f"  Incomplete results")
