import os
import numpy as np
from scipy.ndimage import gaussian_filter

data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
n_frames = 7620
footer_elements = 4

print("Loading raw camera data...")
raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))
pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)
frames = pixels[1:]  # Drop frame 0
frames_t = np.transpose(frames, (0, 2, 1)).astype(np.float32)

# Define tissue mask: mean intensity > 1000
mean_img = frames_t.mean(axis=0)
mask = mean_img > 1000

# We will test several combinations of sigma_t and sigma_s
# For each, we compute:
# 1. Beat-to-beat standard deviation of activation times and APD80 (averaged across tissue pixels)
# 2. Spatial roughness (mean absolute difference with spatial neighbors) of the averaged maps

grid_y, grid_x = np.ogrid[:128, :128]
time_indices = np.arange(360)[:, None, None]

def evaluate_sigmas(sigma_t, sigma_s):
    # Filter
    filtered_data = gaussian_filter(frames_t, sigma=(sigma_t, sigma_s, sigma_s))
    oriented_data = -filtered_data
    
    # Detect onsets
    field_mean = oriented_data[:, mask].mean(axis=1)
    p5 = np.percentile(field_mean, 5)
    p95 = np.percentile(field_mean, 95)
    norm_trace = (field_mean - p5) / (p95 - p5)
    onsets = []
    i = 0
    while i < len(norm_trace) - 1:
        if norm_trace[i] <= 0.5 and norm_trace[i+1] > 0.5:
            onsets.append(i + 1)
            i += 250
        else:
            i += 1
            
    beats = onsets[:18]
    
    # Pre-allocate arrays to store individual beat maps
    act_beats = np.full((18, 128, 128), np.nan, dtype=np.float32)
    apd_beats = np.full((18, 128, 128), np.nan, dtype=np.float32)
    
    for b_idx, onset in enumerate(beats):
        window_start = onset - 60
        window_end = onset + 300
        window_data = oriented_data[window_start:window_end, :, :]
        
        baseline = np.median(window_data[:50, :, :], axis=0)
        amplitude = np.max(window_data, axis=0) - baseline
        thresh_50 = baseline + 0.5 * amplitude
        thresh_20 = baseline + 0.2 * amplitude
        
        # Activation
        crossings = (window_data[:-1, :, :] <= thresh_50[None, :, :]) & (window_data[1:, :, :] > thresh_50[None, :, :])
        has_crossing = crossings.any(axis=0)
        t_act = np.argmax(crossings, axis=0)
        
        v_t = window_data[t_act, grid_y, grid_x]
        v_t1 = window_data[t_act + 1, grid_y, grid_x]
        t_frac = t_act + (thresh_50 - v_t) / (v_t1 - v_t + 1e-10)
        act_frame = (window_start + t_frac) - onset
        act_ms = act_frame * (1000.0 / 529.09)
        
        # APD80
        t_peak = np.argmax(window_data, axis=0)
        cond_before = (time_indices < t_peak[None, :, :]) & (window_data <= thresh_20[None, :, :])
        indices_before = np.where(cond_before, time_indices, -1)
        t1 = np.max(indices_before, axis=0)
        
        cond_after = (time_indices > t_peak[None, :, :]) & (window_data <= thresh_20[None, :, :])
        indices_after = np.where(cond_after, time_indices, 9999)
        t2 = np.min(indices_after, axis=0)
        apd_ms = (t2 - t1) * (1000.0 / 529.09)
        
        # Save to beat maps
        valid_act = mask & has_crossing
        act_beats[b_idx, valid_act] = act_ms[valid_act]
        
        valid_apd = mask & (t1 != -1) & (t2 != 9999)
        apd_beats[b_idx, valid_apd] = apd_ms[valid_apd]
        
    # Calculate average maps
    mean_act = np.nanmean(act_beats, axis=0)
    mean_apd = np.nanmean(apd_beats, axis=0)
    
    # 1. Beat-to-beat precision (standard deviation over beats, averaged across tissue)
    # Note: we first remove the mean activation time of each beat to prevent global jitter from inflating the std
    # For activation time, the zero of each beat is arbitrary, so we subtract the median of each beat map first
    act_beats_aligned = np.zeros_like(act_beats)
    for b_idx in range(18):
        med = np.nanmedian(act_beats[b_idx, mask])
        act_beats_aligned[b_idx] = act_beats[b_idx] - med
        
    act_precision = np.nanmean(np.nanstd(act_beats_aligned, axis=0)[mask])
    apd_precision = np.nanmean(np.nanstd(apd_beats, axis=0)[mask])
    
    # 2. Spatial roughness of the final averaged maps (mean absolute gradient)
    # We compute gradients along y and x
    act_dy = np.abs(np.diff(mean_act, axis=0))
    act_dx = np.abs(np.diff(mean_act, axis=1))
    # We only count gradients where both pixels are inside the mask
    mask_dy = mask[:-1, :] & mask[1:, :]
    mask_dx = mask[:, :-1] & mask[:, 1:]
    act_roughness = (np.mean(act_dy[mask_dy]) + np.mean(act_dx[mask_dx])) / 2
    
    apd_dy = np.abs(np.diff(mean_apd, axis=0))
    apd_dx = np.abs(np.diff(mean_apd, axis=1))
    apd_roughness = (np.mean(apd_dy[mask_dy]) + np.mean(apd_dx[mask_dx])) / 2
    
    # Also count fraction of finite pixels in the mask
    finite_act_frac = np.isfinite(mean_act[mask]).mean()
    finite_apd_frac = np.isfinite(mean_apd[mask]).mean()
    
    return {
        "sigma_t": sigma_t,
        "sigma_s": sigma_s,
        "act_precision_ms": act_precision,
        "apd_precision_ms": apd_precision,
        "act_roughness_ms": act_roughness,
        "apd_roughness_ms": apd_roughness,
        "finite_act_frac": finite_act_frac,
        "finite_apd_frac": finite_apd_frac
    }

# Test grid of parameters
test_cases = [
    (0.01, 0.01),  # almost no smoothing
    (1.0, 0.5),
    (1.5, 1.0),
    (2.0, 1.0),
    (3.0, 1.5),
    (4.0, 2.0),
    (5.0, 2.5),
]

print(f"{'Sigma T':<10} {'Sigma S':<10} {'Act Prec (ms)':<15} {'APD Prec (ms)':<15} {'Act Rough (ms)':<15} {'APD Rough (ms)':<15} {'Fin Act%':<10} {'Fin APD%':<10}")
print("-" * 110)
for st, ss in test_cases:
    res = evaluate_sigmas(st, ss)
    print(f"{res['sigma_t']:<10.2f} {res['sigma_s']:<10.2f} {res['act_precision_ms']:<15.4f} {res['apd_precision_ms']:<15.4f} {res['act_roughness_ms']:<15.4f} {res['apd_roughness_ms']:<15.4f} {res['finite_act_frac']:<10.1%} {res['finite_apd_frac']:<10.1%}")
