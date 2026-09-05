import os
import numpy as np
import subprocess
from scipy.ndimage import gaussian_filter

# Define paths
data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
submission_dir = "/workspace/submission"
os.makedirs(submission_dir, exist_ok=True)

n_frames = 7620
footer_elements = 4

print("Loading raw camera data...")
raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))
pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)
frames = pixels[1:]  # Drop frame 0
frames_t = np.transpose(frames, (0, 2, 1)).astype(np.float32)

print("Applying Gaussian filtering (Sigma T=3.0, Sigma S=1.5)...")
filtered_data = gaussian_filter(frames_t, sigma=(3.0, 1.5, 1.5))

# Orient signal so depolarisation is upward (raw is downward, so we negate)
oriented_data = -filtered_data

# Define tissue mask: mean intensity > 1000
mean_img = frames_t.mean(axis=0)
mask = mean_img > 1000
print(f"Tissue mask fraction: {mask.mean():.1%}")

# Compute field-mean trace on oriented data
field_mean = oriented_data[:, mask].mean(axis=1)
p5 = np.percentile(field_mean, 5)
p95 = np.percentile(field_mean, 95)
norm_trace = (field_mean - p5) / (p95 - p5)

# Detect onsets
onsets = []
i = 0
N = len(norm_trace)
while i < N - 1:
    if norm_trace[i] <= 0.5 and norm_trace[i+1] > 0.5:
        onsets.append(i + 1)
        i += 250
    else:
        i += 1

print(f"Detected {len(onsets)} onsets.")
# Use the first 18 beats
beats_to_use = onsets[:18]
print(f"Using {len(beats_to_use)} beats for map construction.")

# Accumulators for mean maps
act_sum = np.zeros((128, 128), dtype=np.float32)
apd_sum = np.zeros((128, 128), dtype=np.float32)
act_count = np.zeros((128, 128), dtype=np.float32)
apd_count = np.zeros((128, 128), dtype=np.float32)

time_indices = np.arange(360)[:, None, None]
ny, nx = 128, 128
grid_y, grid_x = np.ogrid[:ny, :nx]

for b_idx, onset in enumerate(beats_to_use):
    window_start = onset - 60
    window_end = onset + 300
    window_data = oriented_data[window_start:window_end, :, :]  # shape (360, 128, 128)
    
    # Baseline & Amplitude
    baseline = np.median(window_data[:50, :, :], axis=0)
    amplitude = np.max(window_data, axis=0) - baseline
    
    # Thresholds
    thresh_50 = baseline + 0.5 * amplitude
    thresh_20 = baseline + 0.2 * amplitude
    
    # 1. Activation time
    crossings = (window_data[:-1, :, :] <= thresh_50[None, :, :]) & (window_data[1:, :, :] > thresh_50[None, :, :])
    has_crossing = crossings.any(axis=0)
    t_act = np.argmax(crossings, axis=0)
    
    v_t = window_data[t_act, grid_y, grid_x]
    v_t1 = window_data[t_act + 1, grid_y, grid_x]
    
    t_frac = t_act + (thresh_50 - v_t) / (v_t1 - v_t + 1e-10)
    act_frame = (window_start + t_frac) - onset
    act_ms = act_frame * (1000.0 / 529.09)
    
    # 2. APD80
    t_peak = np.argmax(window_data, axis=0)
    
    # Last frame <= 20% before peak
    cond_before = (time_indices < t_peak[None, :, :]) & (window_data <= thresh_20[None, :, :])
    indices_before = np.where(cond_before, time_indices, -1)
    t1 = np.max(indices_before, axis=0)
    
    # First frame <= 20% after peak
    cond_after = (time_indices > t_peak[None, :, :]) & (window_data <= thresh_20[None, :, :])
    indices_after = np.where(cond_after, time_indices, 9999)
    t2 = np.min(indices_after, axis=0)
    
    # APD80 duration in ms (no interpolation, literal interpretation)
    apd_ms = (t2 - t1) * (1000.0 / 529.09)
    
    # Update accumulators for valid pixels
    valid_act = mask & has_crossing
    act_sum[valid_act] += act_ms[valid_act]
    act_count[valid_act] += 1
    
    valid_apd = mask & (t1 != -1) & (t2 != 9999)
    apd_sum[valid_apd] += apd_ms[valid_apd]
    apd_count[valid_apd] += 1

# Compute average maps
final_activation = np.full((128, 128), np.nan, dtype=np.float32)
final_apd80 = np.full((128, 128), np.nan, dtype=np.float32)

# Only output values where count is >= 1 (or can require all 18 beats to be valid)
valid_act_mask = mask & (act_count >= 1)
final_activation[valid_act_mask] = act_sum[valid_act_mask] / act_count[valid_act_mask]

valid_apd_mask = mask & (apd_count >= 1)
final_apd80[valid_apd_mask] = apd_sum[valid_apd_mask] / apd_count[valid_apd_mask]

# Ensure off-tissue pixels are NaN as per the prompt
final_activation[~mask] = np.nan
final_apd80[~mask] = np.nan

# Save maps
np.save(os.path.join(submission_dir, "mask.npy"), mask)
np.save(os.path.join(submission_dir, "activation_ms.npy"), final_activation)
np.save(os.path.join(submission_dir, "apd80_ms.npy"), final_apd80)

print("\nSaved maps to", submission_dir)
print("Activation map finite percent:", np.isfinite(final_activation[mask]).mean() * 100)
print("APD80 map finite percent:", np.isfinite(final_apd80[mask]).mean() * 100)

# Check with selfcheck.py
print("\nRunning selfcheck.py...")
# Create a dummy methods.md first if it doesn't exist
methods_path = os.path.join(submission_dir, "methods.md")
if not os.path.exists(methods_path):
    with open(methods_path, "w") as f:
        f.write("## Approach\nThis is a temporary placeholder of more than 300 characters to pass the initial format checks while we verify and refine the maps.\n## What the method targets\nMore descriptions about how the steps map to the definitions.\n## Validation performed\nDetails about validation.\n## Budget used\nDetails about budget.\n## Limitations\nDetails about limitations.\n")

subprocess.run(["python3", "/workspace/selfcheck.py"])
