import numpy as np
from scipy.ndimage import gaussian_filter

data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
n_frames = 7620
footer_elements = 4

raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))
pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)
frames = pixels[1:]
frames_t = np.transpose(frames, (0, 2, 1)).astype(np.float32)

# Use optimal filtering
filtered_data = gaussian_filter(frames_t, sigma=(3.0, 1.5, 1.5))
oriented_data = -filtered_data

mean_img = frames_t.mean(axis=0)
mask = mean_img > 1000

# Onsets
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

# We will run both methods on Beat 0 and calculate statistics
onset = beats[0]
window_start = onset - 60
window_end = onset + 300
window_data = oriented_data[window_start:window_end, :, :]

baseline = np.median(window_data[:50, :, :], axis=0)
amplitude = np.max(window_data, axis=0) - baseline
thresh_20 = baseline + 0.2 * amplitude

t_peak = np.argmax(window_data, axis=0)
time_indices = np.arange(360)[:, None, None]

# Method 1: No interpolation (from last frame <= 20% before peak to first frame <= 20% after peak)
cond_before = (time_indices < t_peak[None, :, :]) & (window_data <= thresh_20[None, :, :])
indices_before = np.where(cond_before, time_indices, -1)
t1 = np.max(indices_before, axis=0)

cond_after = (time_indices > t_peak[None, :, :]) & (window_data <= thresh_20[None, :, :])
indices_after = np.where(cond_after, time_indices, 9999)
t2 = np.min(indices_after, axis=0)

apd_no_interp = (t2 - t1) * (1000.0 / 529.09)

# Method 2: Linear interpolation around the two crossings
# 2.1 Crossing 1 (before peak): between t1 and t1+1
# Since t1 is the LAST frame <= 20% before peak, window_data[t1] <= thresh_20 < window_data[t1+1]
# Note: we need to handle the case where t1 is at the peak or invalid, but inside mask they are valid.
ny, nx = 128, 128
grid_y, grid_x = np.ogrid[:ny, :nx]

# We ensure t1 is valid and t1 < t_peak
valid_t1 = (t1 != -1) & (t1 < t_peak)
# Clip t1 to safe bounds for indexing
t1_clipped = np.clip(t1, 0, 358)
v_t1 = window_data[t1_clipped, grid_y, grid_x]
v_t1_plus = window_data[t1_clipped + 1, grid_y, grid_x]
T1_interp = t1_clipped + (thresh_20 - v_t1) / (v_t1_plus - v_t1 + 1e-10)

# 2.2 Crossing 2 (after peak): between t2-1 and t2
# Since t2 is the FIRST frame <= 20% after peak, window_data[t2-1] > thresh_20 >= window_data[t2]
valid_t2 = (t2 != 9999) & (t2 > t_peak)
t2_clipped = np.clip(t2, 1, 359)
v_t2_minus = window_data[t2_clipped - 1, grid_y, grid_x]
v_t2 = window_data[t2_clipped, grid_y, grid_x]
T2_interp = (t2_clipped - 1) + (v_t2_minus - thresh_20) / (v_t2_minus - v_t2 + 1e-10)

apd_interp = (T2_interp - T1_interp) * (1000.0 / 529.09)

valid_mask = mask & valid_t1 & valid_t2

print("APD80 statistics in mask:")
print("Method 1 (No interpolation):")
print("  Mean:", np.mean(apd_no_interp[valid_mask]))
print("  Median:", np.median(apd_no_interp[valid_mask]))
print("  Min:", np.min(apd_no_interp[valid_mask]))
print("  Max:", np.max(apd_no_interp[valid_mask]))
print("  Roughness:", (np.mean(np.abs(np.diff(apd_no_interp, axis=0))[valid_mask[:-1, :]]) + np.mean(np.abs(np.diff(apd_no_interp, axis=1))[valid_mask[:, :-1]])) / 2)

print("\nMethod 2 (With interpolation):")
print("  Mean:", np.mean(apd_interp[valid_mask]))
print("  Median:", np.median(apd_interp[valid_mask]))
print("  Min:", np.min(apd_interp[valid_mask]))
print("  Max:", np.max(apd_interp[valid_mask]))
print("  Roughness:", (np.mean(np.abs(np.diff(apd_interp, axis=0))[valid_mask[:-1, :]]) + np.mean(np.abs(np.diff(apd_interp, axis=1))[valid_mask[:, :-1]])) / 2)
