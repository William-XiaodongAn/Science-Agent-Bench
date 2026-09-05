import os
import numpy as np
import scipy.ndimage

def run_pipeline():
    filepath = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
    num_frames = 7620
    height, width = 128, 128
    pixels_per_frame = height * width
    footer_size = 4
    
    print("Loading raw data...")
    with open(filepath, 'rb') as f:
        f.read(1024)
        data = np.fromfile(f, dtype='<u2')
    
    data = data.reshape((num_frames, pixels_per_frame + footer_size))
    frames = data[:, :pixels_per_frame].reshape((num_frames, height, width))
    frames = frames[1:]  # Drop frame 0
    frames = np.transpose(frames, (0, 2, 1))
    frames = frames.astype(np.float32)
    
    # Orient signal so depolarisation is upward (raw is downward, so multiply by -1)
    oriented_frames = -frames
    
    # 1. Define mask
    # Let's use std > 12 as our tissue mask to be slightly generous and cover all reference pixels.
    pixel_stds = np.std(oriented_frames, axis=0)
    mask = pixel_stds > 12
    num_mask_pixels = np.sum(mask)
    print(f"Mask covers {np.mean(mask):.4f} of the frame ({num_mask_pixels} pixels) with std > 12")
    
    # 2. Spatial-Temporal Gaussian Smoothing
    print("Applying Gaussian smoothing in time and space...")
    # Modest smoothing: sigma_t = 1.5 frames, sigma_s = 1.0 pixel
    smoothed_frames = scipy.ndimage.gaussian_filter(oriented_frames, sigma=(1.5, 1.0, 1.0))
    
    # 3. Detect Beat Onsets on Field-Mean Trace (using smoothed frames)
    # field_mean is mean over tissue pixels
    field_mean = np.mean(smoothed_frames[:, mask], axis=1)
    
    # Normalise between 5th and 95th percentiles
    p5 = np.percentile(field_mean, 5)
    p95 = np.percentile(field_mean, 95)
    norm_field_mean = (field_mean - p5) / (p95 - p5)
    
    # Detect onsets with 50% upward crossing and 250-frame refractory period
    onsets = []
    refractory_until = -1
    for t in range(1, len(norm_field_mean)):
        if t < refractory_until:
            continue
        if norm_field_mean[t-1] < 0.5 and norm_field_mean[t] >= 0.5:
            onsets.append(t)
            refractory_until = t + 250
            
    print(f"Detected {len(onsets)} onsets: {onsets}")
    
    # Usable beats are those with at least 300 frames after onset
    usable_onsets = [o for o in onsets if o + 300 <= len(norm_field_mean)]
    num_usable = len(usable_onsets)
    print(f"Usable onsets ({num_usable}): {usable_onsets}")
    
    # Initialize 3D arrays to store per-beat results for averaging using np.nanmean
    all_activations = np.full((num_usable, height, width), np.nan, dtype=np.float32)
    all_apd80s_interp = np.full((num_usable, height, width), np.nan, dtype=np.float32)
    all_apd80s_disc = np.full((num_usable, height, width), np.nan, dtype=np.float32)
    
    ms_per_frame = 1000.0 / 529.09
    
    # 4. Process each beat
    for beat_idx, o in enumerate(usable_onsets):
        print(f"Processing beat {beat_idx+1}/{num_usable} (onset at frame {o})...")
        window_start = o - 60
        window_end = o + 300
        # shape: (360, height, width)
        window = smoothed_frames[window_start:window_end, :, :]
        
        # Extract for mask pixels
        window_mask = window[:, mask] # shape (360, num_mask_pixels)
        
        # Baseline = median of first 50 frames
        baseline = np.median(window_mask[:50, :], axis=0)
        # Amplitude = window maximum minus baseline
        window_max = np.max(window_mask, axis=0)
        amplitude = window_max - baseline
        
        # Thresholds
        thresh_50 = baseline + 0.5 * amplitude
        thresh_20 = baseline + 0.2 * amplitude
        
        # --- Activation Time Calculation ---
        # First 50% crossing in upstroke
        crossings_50 = (window_mask[:-1, :] < thresh_50) & (window_mask[1:, :] >= thresh_50)
        has_crossing_50 = np.any(crossings_50, axis=0)
        
        # argmax returns the first True index
        first_cross_idx = np.argmax(crossings_50, axis=0) + 1
        
        v_prev = window_mask[first_cross_idx - 1, np.arange(num_mask_pixels)]
        v_curr = window_mask[first_cross_idx, np.arange(num_mask_pixels)]
        denom_act = np.where(v_curr - v_prev == 0, 1e-5, v_curr - v_prev)
        frac_act = (thresh_50 - v_prev) / denom_act
        frac_act = np.clip(frac_act, 0.0, 1.0)
        
        act_frame_rel = (first_cross_idx - 1) + frac_act - 60
        act_ms = act_frame_rel * ms_per_frame
        
        # Store activation time
        all_activations[beat_idx, mask] = np.where(has_crossing_50, act_ms, np.nan)
        
        # --- APD80 Calculation ---
        peak_idx = np.argmax(window_mask, axis=0)
        grid_indices = np.arange(360)[:, None]
        below_20 = window_mask <= thresh_20
        
        # Discrete t1, t2
        t1_disc = np.max(np.where(below_20, np.where(grid_indices <= peak_idx, grid_indices, -1), -1), axis=0)
        t2_disc = np.min(np.where(below_20, np.where(grid_indices >= peak_idx, grid_indices, 9999), 9999), axis=0)
        valid_apd = (t1_disc != -1) & (t2_disc != 9999)
        
        # Discrete APD80
        apd_ms_disc = (t2_disc - t1_disc) * ms_per_frame
        all_apd80s_disc[beat_idx, mask] = np.where(valid_apd, apd_ms_disc, np.nan)
        
        # Interpolated APD80
        # t1_interp (before peak crossing)
        t1_disc_safe = np.clip(t1_disc, 0, 358)
        v_t1 = window_mask[t1_disc_safe, np.arange(num_mask_pixels)]
        v_t1_plus = window_mask[t1_disc_safe + 1, np.arange(num_mask_pixels)]
        denom_t1 = np.where(v_t1_plus - v_t1 == 0, 1e-5, v_t1_plus - v_t1)
        frac_t1 = (thresh_20 - v_t1) / denom_t1
        frac_t1 = np.clip(frac_t1, 0.0, 1.0)
        t1_interp = t1_disc_safe + frac_t1
        
        # t2_interp (after peak crossing)
        t2_disc_safe = np.clip(t2_disc, 1, 359)
        v_t2_minus = window_mask[t2_disc_safe - 1, np.arange(num_mask_pixels)]
        v_t2 = window_mask[t2_disc_safe, np.arange(num_mask_pixels)]
        denom_t2 = np.where(v_t2_minus - v_t2 == 0, 1e-5, v_t2_minus - v_t2)
        frac_t2 = (v_t2_minus - thresh_20) / denom_t2
        frac_t2 = np.clip(frac_t2, 0.0, 1.0)
        t2_interp = (t2_disc_safe - 1) + frac_t2
        
        apd_ms_interp = (t2_interp - t1_interp) * ms_per_frame
        all_apd80s_interp[beat_idx, mask] = np.where(valid_apd, apd_ms_interp, np.nan)

    # 5. Averaging across beats using np.nanmean
    activation_ms = np.full((height, width), np.nan, dtype=np.float32)
    apd80_ms_interp = np.full((height, width), np.nan, dtype=np.float32)
    apd80_ms_disc = np.full((height, width), np.nan, dtype=np.float32)
    
    # We only compute average inside mask
    activation_ms[mask] = np.nanmean(all_activations[:, mask], axis=0)
    apd80_ms_interp[mask] = np.nanmean(all_apd80s_interp[:, mask], axis=0)
    apd80_ms_disc[mask] = np.nanmean(all_apd80s_disc[:, mask], axis=0)
    
    # Check finite pixels
    fin_act = np.isfinite(activation_ms[mask]).mean()
    fin_apd_interp = np.isfinite(apd80_ms_interp[mask]).mean()
    fin_apd_disc = np.isfinite(apd80_ms_disc[mask]).mean()
    
    print("\nProcessing Results (std > 12):")
    print(f"Finite activation pixels in mask: {fin_act:.2%}")
    print(f"Finite APD80 (interp) pixels in mask: {fin_apd_interp:.2%}")
    print(f"Finite APD80 (disc) pixels in mask: {fin_apd_disc:.2%}")
    
    print(f"Activation: mean={np.nanmean(activation_ms):.2f}, std={np.nanstd(activation_ms):.2f}")
    print(f"APD80 (interp): mean={np.nanmean(apd80_ms_interp):.2f}, std={np.nanstd(apd80_ms_interp):.2f}")
    print(f"APD80 (disc): mean={np.nanmean(apd80_ms_disc):.2f}, std={np.nanstd(apd80_ms_disc):.2f}")
    
    # Let's save the interpolated version as the main file, and we can also save a copy of the discrete one
    # to evaluate later if needed.
    os.makedirs("/workspace/submission", exist_ok=True)
    np.save("/workspace/submission/mask.npy", mask)
    np.save("/workspace/submission/activation_ms.npy", activation_ms)
    np.save("/workspace/submission/apd80_ms.npy", apd80_ms_interp) # default is interpolated
    
    # Save the script to the submission folder as required:
    # "Keep the reproducible script(s) that produced the maps in /workspace/submission/ too."
    import shutil
    shutil.copy2(__file__, "/workspace/submission/reproducible_pipeline.py")
    print("Files successfully saved to /workspace/submission/!")

if __name__ == "__main__":
    run_pipeline()
