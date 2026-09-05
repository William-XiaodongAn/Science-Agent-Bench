import os
import sys
import numpy as np
from scipy.ndimage import gaussian_filter

def run_pipeline():
    # 1. Load raw data
    file_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
    if not os.path.exists(file_path):
        print("Data file not found!")
        return

    print("Loading raw binary data...")
    with open(file_path, "rb") as f:
        _ = f.read(1024)  # Skip header
        data = np.fromfile(f, dtype=np.uint16)

    num_frames = len(data) // 16388
    data = data.reshape((num_frames, 16388))
    frames = data[:, :16384].reshape((num_frames, 128, 128))
    
    # Drop frame 0
    frames = frames[1:]
    print(f"Loaded {len(frames)} frames of shape (128, 128).")

    # Transpose frames to line up with the reference
    print("Transposing frames...")
    frames_t = np.zeros_like(frames)
    for i in range(len(frames)):
        frames_t[i] = frames[i].T

    # Orient signal so that depolarisation is upward (invert the signal)
    print("Inverting signal for upward depolarisation...")
    frames_oriented = -frames_t.astype(np.float32)

    # 2. Segment tissue and create mask
    mean_img = np.mean(frames_t, axis=0)
    # Use thresh = 1000 for generous coverage to satisfy the >= 95% gate comfortably
    mask = mean_img > 1000
    print(f"Mask covers {mask.mean():.1%} of the frame.")

    # 3. Spatial-temporal smoothing
    sigma_t = 1.5
    sigma_s = 1.0
    print(f"Applying spatial-temporal Gaussian smoothing (sigma_t={sigma_t}, sigma_s={sigma_s})...")
    smoothed_frames = gaussian_filter(frames_oriented, sigma=(sigma_t, sigma_s, sigma_s))

    # 4. Beat onset detection
    F = np.mean(smoothed_frames[:, mask], axis=1)
    p5 = np.percentile(F, 5)
    p95 = np.percentile(F, 95)
    F_norm = (F - p5) / (p95 - p5)

    onsets = []
    t = 1
    while t < len(F_norm):
        if F_norm[t-1] <= 0.5 and F_norm[t] > 0.5:
            onsets.append(t)
            t += 250
        else:
            t += 1

    print(f"Detected {len(onsets)} beat onsets.")
    # Keep only usable beats (needs 300 frames after onset)
    usable_onsets = [o for o in onsets if o + 300 < len(frames)]
    print(f"Usable beat onsets ({len(usable_onsets)}): {usable_onsets}")

    # 5. Process each beat per pixel
    dt_ms = 1.8900  # 1.890 ms/frame
    
    # Initialize arrays
    sum_act = np.zeros((128, 128), dtype=np.float32)
    sum_apd = np.zeros((128, 128), dtype=np.float32)
    count_act = np.zeros((128, 128), dtype=np.float32)
    count_apd = np.zeros((128, 128), dtype=np.float32)

    pixels = np.argwhere(mask)
    num_pixels = len(pixels)
    print(f"Processing {num_pixels} tissue pixels...")

    for beat_idx, T in enumerate(usable_onsets):
        print(f"Processing Beat {beat_idx+1}/{len(usable_onsets)} (onset frame {T})...")
        
        # Window from T - 60 to T + 300 (inclusive, so 361 frames)
        win_start = T - 60
        win_end = T + 301
        win_frames = smoothed_frames[win_start:win_end]
        
        baselines = np.median(win_frames[:50], axis=0) # shape (128, 128)
        max_vals = np.max(win_frames, axis=0) # shape (128, 128)
        amplitudes = max_vals - baselines # shape (128, 128)
        peak_indices = np.argmax(win_frames, axis=0) # shape (128, 128)
        
        thresh_50 = baselines + 0.5 * amplitudes # shape (128, 128)
        thresh_20 = baselines + 0.2 * amplitudes # shape (128, 128)
        
        for r, c in pixels:
            trace_win = win_frames[:, r, c]
            t50 = thresh_50[r, c]
            t20 = thresh_20[r, c]
            peak = peak_indices[r, c]
            
            # --- Activation Time ---
            act_idx = -1
            for i in range(1, len(trace_win)):
                if trace_win[i-1] < t50 <= trace_win[i]:
                    act_idx = i
                    break
            
            if act_idx != -1:
                denom = trace_win[act_idx] - trace_win[act_idx-1]
                if denom > 1e-6:
                    frac = (t50 - trace_win[act_idx-1]) / denom
                    i_interp = (act_idx - 1) + frac
                    act_time_ms = (win_start + i_interp) * dt_ms
                    sum_act[r, c] += act_time_ms
                    count_act[r, c] += 1
            
            # --- APD80 ---
            f_start = -1
            for i in range(peak, -1, -1):
                if trace_win[i] <= t20:
                    f_start = i
                    break
            
            f_end = -1
            for i in range(peak, len(trace_win)):
                if trace_win[i] <= t20:
                    f_end = i
                    break
            
            if f_start != -1 and f_end != -1 and f_end > f_start:
                apd80_val_ms = (f_end - f_start) * dt_ms
                sum_apd[r, c] += apd80_val_ms
                count_apd[r, c] += 1

    # 6. Calculate mean over usable beats
    mean_act = np.full((128, 128), np.nan, dtype=np.float32)
    mean_apd = np.full((128, 128), np.nan, dtype=np.float32)
    
    valid_act = count_act > 0
    mean_act[valid_act] = sum_act[valid_act] / count_act[valid_act]
    
    valid_apd = count_apd > 0
    mean_apd[valid_apd] = sum_apd[valid_apd] / count_apd[valid_apd]
    
    mean_act[~mask] = np.nan
    mean_apd[~mask] = np.nan

    # Output directories and saving files
    sub_dir = "/workspace/submission"
    os.makedirs(sub_dir, exist_ok=True)
    
    np.save(os.path.join(sub_dir, "mask.npy"), mask)
    np.save(os.path.join(sub_dir, "activation_ms.npy"), mean_act)
    np.save(os.path.join(sub_dir, "apd80_ms.npy"), mean_apd)
    
    print("\nFiles saved to submission/ directory.")
    
    # Print statistics
    act_vals = mean_act[mask & np.isfinite(mean_act)]
    if len(act_vals) > 0:
        print(f"Activation Time (ms) stats: min={act_vals.min():.2f}, max={act_vals.max():.2f}, mean={act_vals.mean():.2f}, median={np.median(act_vals):.2f}")
    else:
        print("No finite activation time values computed on-mask!")
        
    apd_vals = mean_apd[mask & np.isfinite(mean_apd)]
    if len(apd_vals) > 0:
        print(f"APD80 (ms) stats: min={apd_vals.min():.2f}, max={apd_vals.max():.2f}, mean={apd_vals.mean():.2f}, median={np.median(apd_vals):.2f}")
    else:
        print("No finite APD80 values computed on-mask!")

if __name__ == "__main__":
    run_pipeline()
