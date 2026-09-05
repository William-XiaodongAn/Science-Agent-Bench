import numpy as np
from scipy.ndimage import gaussian_filter

data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
n_frames = 7620
footer_elements = 4

print("Loading raw data...")
raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))
pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)
frames = pixels[1:]  # drop frame 0
frames_t = np.transpose(frames, (0, 2, 1)).astype(np.float32)

print("Filtering data...")
# Temporal sigma=1.5, Spatial sigma=1.0
filtered_data = gaussian_filter(frames_t, sigma=(1.5, 1.0, 1.0))

# We use -filtered_data to orient it so depolarisation is upward (since raw depolarisation is downward)
oriented_data = -filtered_data

# Let's define the tissue mask using a threshold of 1000 on the mean image
mean_img = frames_t.mean(axis=0)
mask = mean_img > 1000
print(f"Mask covers {mask.mean():.1%} of the frame.")

# Compute the field-mean trace on oriented data
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
print("First 3 onsets:", onsets[:3])

# Let's test on the first beat (onset = onsets[0])
onset = onsets[0]
print(f"\nProcessing Beat 0 at onset {onset}...")

# Window: from onset - 60 to onset + 300
window_start = onset - 60
window_end = onset + 300
window_data = oriented_data[window_start:window_end, :, :]  # shape (360, 128, 128)

# Baseline: median of first 50 frames of the window
baseline = np.median(window_data[:50, :, :], axis=0)  # shape (128, 128)

# Amplitude: max in window minus baseline
amplitude = np.max(window_data, axis=0) - baseline  # shape (128, 128)

# Upstroke thresholds
thresh_50 = baseline + 0.5 * amplitude
thresh_20 = baseline + 0.2 * amplitude

# 1. Activation time: moment the pixel first crosses 50% threshold
# Find first t such that window_data[t] <= thresh_50 < window_data[t+1]
crossings = (window_data[:-1, :, :] <= thresh_50[None, :, :]) & (window_data[1:, :, :] > thresh_50[None, :, :])
has_crossing = crossings.any(axis=0)

# np.argmax along axis 0 returns the first index where crossings is True
t_act = np.argmax(crossings, axis=0)

# Extract values at t_act and t_act + 1
ny, nx = 128, 128
grid_y, grid_x = np.ogrid[:ny, :nx]
v_t = window_data[t_act, grid_y, grid_x]
v_t1 = window_data[t_act + 1, grid_y, grid_x]

# Interpolated crossing frame relative to window start
t_frac = t_act + (thresh_50 - v_t) / (v_t1 - v_t + 1e-10)

# Convert to absolute frame index, and subtract onset to get relative to onset
act_frame = (window_start + t_frac) - onset
act_ms = act_frame * (1000.0 / 529.09)

# 2. APD80: from last frame <= 20% before peak to first frame <= 20% after peak
t_peak = np.argmax(window_data, axis=0)

time_indices = np.arange(360)[:, None, None]

# cond_before: t < t_peak and window_data <= thresh_20
cond_before = (time_indices < t_peak[None, :, :]) & (window_data <= thresh_20[None, :, :])
indices_before = np.where(cond_before, time_indices, -1)
t1 = np.max(indices_before, axis=0)

# cond_after: t > t_peak and window_data <= thresh_20
cond_after = (time_indices > t_peak[None, :, :]) & (window_data <= thresh_20[None, :, :])
indices_after = np.where(cond_after, time_indices, 9999)
t2 = np.min(indices_after, axis=0)

# APD80 duration
apd_frames = t2 - t1
apd_ms = apd_frames * (1000.0 / 529.09)

# Make sure we only keep valid pixels
valid_act = mask & has_crossing
valid_apd = mask & (t1 != -1) & (t2 != 9999)

print("\n--- Statistics inside mask ---")
print(f"Valid activation pixels in mask: {valid_act[mask].mean():.1%}")
print(f"Valid APD80 pixels in mask: {valid_apd[mask].mean():.1%}")

print("Activation ms in mask (valid):")
print("  Min:", np.min(act_ms[valid_act]))
print("  Max:", np.max(act_ms[valid_act]))
print("  Mean:", np.mean(act_ms[valid_act]))
print("  Median:", np.median(act_ms[valid_act]))

print("APD80 ms in mask (valid):")
print("  Min:", np.min(apd_ms[valid_apd]))
print("  Max:", np.max(apd_ms[valid_apd]))
print("  Mean:", np.mean(apd_ms[valid_apd]))
print("  Median:", np.median(apd_ms[valid_apd]))
