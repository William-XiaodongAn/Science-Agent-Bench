import numpy as np
from scipy.ndimage import gaussian_filter

data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
n_frames = 7620
footer_elements = 4

raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))
pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)
frames = pixels[1:]
frames_t = np.transpose(frames, (0, 2, 1)).astype(np.float32)

# Check different temporal/spatial sigmas
for sigma_t, sigma_s in [(1.5, 1.0), (3.0, 1.5), (4.0, 2.0)]:
    filtered_data = gaussian_filter(frames_t, sigma=(sigma_t, sigma_s, sigma_s))
    oriented_data = -filtered_data
    
    # Mask
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
            
    # Let's check first beat
    onset = onsets[0]
    window_start = onset - 60
    window_end = onset + 300
    window_data = oriented_data[window_start:window_end, :, :]
    
    baseline = np.median(window_data[:50, :, :], axis=0)
    amplitude = np.max(window_data, axis=0) - baseline
    thresh_50 = baseline + 0.5 * amplitude
    thresh_20 = baseline + 0.2 * amplitude
    
    crossings = (window_data[:-1, :, :] <= thresh_50[None, :, :]) & (window_data[1:, :, :] > thresh_50[None, :, :])
    has_crossing = crossings.any(axis=0)
    t_act = np.argmax(crossings, axis=0)
    ny, nx = 128, 128
    grid_y, grid_x = np.ogrid[:ny, :nx]
    v_t = window_data[t_act, grid_y, grid_x]
    v_t1 = window_data[t_act + 1, grid_y, grid_x]
    t_frac = t_act + (thresh_50 - v_t) / (v_t1 - v_t + 1e-10)
    act_frame = (window_start + t_frac) - onset
    act_ms = act_frame * (1000.0 / 529.09)
    
    valid_act = mask & has_crossing
    act_vals = act_ms[valid_act]
    
    print(f"\nSigma T={sigma_t}, Sigma S={sigma_s}:")
    print("  Activation ms percentiles [0.1, 1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9]:")
    print(" ", [np.percentile(act_vals, p) for p in [0.1, 1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9]])
    
    # APD80
    t_peak = np.argmax(window_data, axis=0)
    time_indices = np.arange(360)[:, None, None]
    cond_before = (time_indices < t_peak[None, :, :]) & (window_data <= thresh_20[None, :, :])
    indices_before = np.where(cond_before, time_indices, -1)
    t1 = np.max(indices_before, axis=0)
    
    cond_after = (time_indices > t_peak[None, :, :]) & (window_data <= thresh_20[None, :, :])
    indices_after = np.where(cond_after, time_indices, 9999)
    t2 = np.min(indices_after, axis=0)
    
    apd_frames = t2 - t1
    apd_ms = apd_frames * (1000.0 / 529.09)
    valid_apd = mask & (t1 != -1) & (t2 != 9999)
    apd_vals = apd_ms[valid_apd]
    
    print("  APD80 ms percentiles [0.1, 1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9]:")
    print(" ", [np.percentile(apd_vals, p) for p in [0.1, 1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9]])
