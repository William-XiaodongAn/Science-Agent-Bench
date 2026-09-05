import numpy as np
import sys
import os

# Ensure the framework can be imported
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
if "/workspace" not in sys.path:
    sys.path.insert(0, "/workspace")

from baseline import esn, search_api

def search(evaluator, seed: int) -> dict:
    """
    Automated hyperparameter search procedure using a localized coordinate descent / perturbation
    strategy on top of a carefully chosen set of fallback configurations.
    
    This guarantees finding a highly stable and optimized reservoir architecture specifically for
    the random reservoir initialization determined by the given seed, within the 60 evaluations budget.
    """
    # Create seed-specific random number generator for search decisions
    rng = np.random.default_rng(seed)
    
    # Helper to choose from a list safely without triggering NumPy inhomogeneous coercion bugs
    def safe_choice(lst):
        idx = rng.choice(len(lst))
        return lst[idx]
    
    # 1. Evaluate baseline fallbacks to guarantee a stable start and high-quality fallback
    fallbacks = [
        # Default ESN baseline
        {"layers": (368,)},
        # Single-layer tuned
        {"layers": (368,), "ridge": 1e-5},
        {"layers": (368,), "spectral_radius": 0.5, "ridge": 1e-5},
        # 3-layer baselines
        {"layers": (120, 120, 128), "all_layers_to_output": True, "input_to_all_layers": True},
        {"layers": (120, 120, 128), "all_layers_to_output": True, "input_to_all_layers": True, "spectral_radius": 1.1, "ridge": 0.01, "inter_scale": 0.2},
        {"layers": (120, 120, 128), "all_layers_to_output": True, "input_to_all_layers": True, "spectral_radius": 1.1, "ridge": 0.005, "inter_scale": 0.2},
    ]
    
    best_score = float('inf')
    best_cfg = None
    
    # Evaluate fallbacks
    for cfg in fallbacks:
        if evaluator.remaining <= 0:
            break
        try:
            score = evaluator.evaluate(cfg)
            if score < best_score:
                best_score = score
                best_cfg = cfg.copy()
        except Exception:
            pass
            
    # 2. Local perturbation / coordinate descent phase
    attempts = 0
    max_attempts = 300  # Avoid infinite loop if all neighbors are evaluated
    
    while evaluator.remaining > 0 and attempts < max_attempts:
        attempts += 1
        candidate = best_cfg.copy()
        
        # Select parameter to perturb
        param_to_perturb = safe_choice([
            "layers", 
            "spectral_radius", 
            "ridge", 
            "inter_scale", 
            "leak", 
            "input_scale", 
            "input_to_output",
            "readout_halflife"
        ])
        
        if param_to_perturb == "layers":
            # Mutate architecture layers
            new_layers = safe_choice([
                (368,),
                (184, 184),
                (120, 120, 128),
                (92, 92, 92, 92)
            ])
            candidate["layers"] = new_layers
            if len(new_layers) > 1:
                candidate["all_layers_to_output"] = True
                candidate["input_to_all_layers"] = True
                if "inter_scale" not in candidate:
                    candidate["inter_scale"] = 0.1
            else:
                candidate["all_layers_to_output"] = False
                candidate["input_to_all_layers"] = False
                candidate.pop("inter_scale", None)
                
        elif param_to_perturb == "spectral_radius":
            sr = candidate.get("spectral_radius", 0.9)
            delta = safe_choice([-0.1, -0.05, 0.05, 0.1])
            candidate["spectral_radius"] = float(np.clip(sr + delta, 0.1, 1.5))
            
        elif param_to_perturb == "ridge":
            ridge = candidate.get("ridge", 1e-3)
            factor = safe_choice([0.1, 0.2, 0.5, 2.0, 5.0, 10.0])
            candidate["ridge"] = float(np.clip(ridge * factor, 1e-8, 1.0))
            
        elif param_to_perturb == "inter_scale":
            if len(candidate.get("layers", (368,))) > 1:
                inter = candidate.get("inter_scale", 0.1)
                delta = safe_choice([-0.05, 0.05, 0.1])
                candidate["inter_scale"] = float(np.clip(inter + delta, 0.0, 0.5))
            else:
                continue
                
        elif param_to_perturb == "leak":
            leak = candidate.get("leak", 0.5)
            delta = safe_choice([-0.1, 0.1])
            candidate["leak"] = float(np.clip(leak + delta, 0.05, 1.0))
            
        elif param_to_perturb == "input_scale":
            scale = candidate.get("input_scale", 0.1)
            if not isinstance(scale, dict):
                scale = {"bias": 0.1, "voltage": 0.1, "stimulus": 0.1}
            else:
                scale = scale.copy()
            
            channel = safe_choice(["voltage", "stimulus", "bias"])
            ch_scale = scale.get(channel, 0.1)
            factor = safe_choice([0.1, 0.5, 2.0, 5.0, 10.0])
            scale[channel] = float(np.clip(ch_scale * factor, 0.01, 5.0))
            candidate["input_scale"] = scale
            
        elif param_to_perturb == "input_to_output":
            candidate["input_to_output"] = not candidate.get("input_to_output", True)
            
        elif param_to_perturb == "readout_halflife":
            candidate["readout_halflife"] = safe_choice([None, 1000, 2000, 5000, 10000])
            
        # Ensure we don't evaluate the exact same config if it's already in history
        already_evaluated = False
        try:
            cand_norm, _ = search_api.validate_config(candidate)
            for h in evaluator.history:
                h_norm, _ = search_api.validate_config(h[0])
                if cand_norm == h_norm:
                    already_evaluated = True
                    break
        except Exception:
            pass
            
        if already_evaluated:
            continue
            
        # Evaluate candidate
        try:
            score = evaluator.evaluate(candidate)
            if score < best_score:
                best_score = score
                best_cfg = candidate.copy()
        except Exception:
            pass
            
    # 3. Double check we return the absolute best found configuration from evaluator history
    best_config_from_history, best_score_from_history = evaluator.best()
    if best_config_from_history is not None:
        return best_config_from_history
    return best_cfg if best_cfg is not None else {"layers": (368,)}
