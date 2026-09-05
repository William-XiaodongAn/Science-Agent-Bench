#!/usr/bin/env python3
"""
Cardiac Optical Mapping Processing Pipeline.
Author: Gemini CLI
Date: Friday, September 4, 2026

This script processes raw voltage-sensitive dye optical mapping data
to extract tissue mask, activation times, and APD80 repolarization times.
"""

import os
import numpy as np
from scipy.ndimage import gaussian_filter, label, binary_fill_holes

def main():
    data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
    submission_dir = "/workspace/submission"
    os.makedirs(submission_dir, exist_ok=True)

    n_frames = 7620
    footer_elements = 4

    print("Step 1: Loading raw 16-bit little-endian camera recording...")
    # Skipping the 1024-byte header, read 16-bit little-endian unsigned integers.
    raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))
    
    # Extract frame pixels (first 128x128 elements of each frame)
    pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)
    
    # Drop frame 0 as it is under-exposed
    frames = pixels[1:]
    
    # Transpose each frame to align spatial orientation with the reference analysis convention
    frames_t = np.transpose(frames, (0, 2, 1)).astype(np.float32)
    print(f"Data shape after transpose: {frames_t.shape}")

    print("Step 2: Applying spatio-temporal Gaussian filtering...")
    # Modest Gaussian smoothing: Sigma T = 3.0 frames, Sigma S = 1.5 pixels
    # Resolves noise plateaus, especially for the 20% repolarization level.
    filtered_data = gaussian_filter(frames_t, sigma=(3.0, 1.5, 1.5))

    # Step 3: Sign Convention and Signal Orientation
    # The upstroke is a downward deflection in the raw data, so we negate the signal
    # to orient it so that depolarization is an upward deflection.
    oriented_data = -filtered_data

    print("Step 4: Defining and cleaning tissue mask...")
    # Compute the average spatial image
    mean_img = frames_t.mean(axis=0)
    
    # Threshold background pixels at 1000 counts
    raw_mask = mean_img > 1000
    
    # Label connected components to clean background noise specks
    labeled, num_features = label(raw_mask)
    sizes = [np.sum(labeled == i) for i in range(1, num_features + 1)]
    largest_label = np.argmax(sizes) + 1
    
    # Keep only the largest component and fill any internal holes
    mask = binary_fill_holes(labeled == largest_label)
    print(f"Cleaned tissue mask coverage: {mask.mean():.2%} of the frame.")

    print("Step 5: Detecting beat onsets from field-mean trace...")
    # Compute the field-mean trace (spatial average over tissue pixels)
    field_mean = oriented_data[:, mask].mean(axis=1)
    
    # Normalise between its 5th and 95th percentiles
    p5 = np.percentile(field_mean, 5)
    p95 = np.percentile(field_mean, 95)
    norm_trace = (field_mean - p5) / (p95 - p5)

    # 50% upward crossing with a 250-frame refractory period
    onsets = []
    i = 0
    N = len(norm_trace)
    while i < N - 1:
        if norm_trace[i] <= 0.5 and norm_trace[i+1] > 0.5:
            onsets.append(i + 1)
            i += 250
        else:
            i += 1

    print(f"Detected {len(onsets)} beat onsets. Selecting the first 18 complete beats.")
    beats = onsets[:18]

    # Pre-allocate accumulators to compute pixel-wise averages over the 18 beats
    act_sum = np.zeros((128, 128), dtype=np.float32)
    apd_sum = np.zeros((128, 128), dtype=np.float32)
    act_count = np.zeros((128, 128), dtype=np.float32)
    apd_count = np.zeros((128, 128), dtype=np.float32)

    time_indices = np.arange(360)[:, None, None]
    ny, nx = 128, 128
    grid_y, grid_x = np.ogrid[:ny, :nx]

    print("Step 6: Recovering activation and repolarisation maps across beats...")
    for b_idx, onset in enumerate(beats):
        # Beat window starts 60 frames before beat onset and runs 300 frames past it (360 frames total)
        window_start = onset - 60
        window_end = onset + 300
        window_data = oriented_data[window_start:window_end, :, :]
        
        # Baseline: median of the first 50 frames of the window
        baseline = np.median(window_data[:50, :, :], axis=0)
        
        # Amplitude: window maximum minus baseline
        amplitude = np.max(window_data, axis=0) - baseline
        
        # Thresholds (50% for activation, 20% for APD80)
        thresh_50 = baseline + 0.5 * amplitude
        thresh_20 = baseline + 0.2 * amplitude
        
        # 1. Activation time: moment the pixel first crosses 50% upstroke amplitude
        crossings = (window_data[:-1, :, :] <= thresh_50[None, :, :]) & (window_data[1:, :, :] > thresh_50[None, :, :])
        has_crossing = crossings.any(axis=0)
        t_act = np.argmax(crossings, axis=0)
        
        v_t = window_data[t_act, grid_y, grid_x]
        v_t1 = window_data[t_act + 1, grid_y, grid_x]
        
        # Linear interpolation
        t_frac = t_act + (thresh_50 - v_t) / (v_t1 - v_t + 1e-10)
        
        # Convert crossing frame back to absolute recording frame, and make it relative to the onset
        act_frame = (window_start + t_frac) - onset
        act_ms = act_frame * (1000.0 / 529.09)
        
        # 2. APD80: time spent above 20% of upstroke amplitude
        t_peak = np.argmax(window_data, axis=0)
        
        # Last frame at or below the 20% level before the peak
        cond_before = (time_indices < t_peak[None, :, :]) & (window_data <= thresh_20[None, :, :])
        indices_before = np.where(cond_before, time_indices, -1)
        t1 = np.max(indices_before, axis=0)
        
        # First frame at or below the 20% level after the peak
        cond_after = (time_indices > t_peak[None, :, :]) & (window_data <= thresh_20[None, :, :])
        indices_after = np.where(cond_after, time_indices, 9999)
        t2 = np.min(indices_after, axis=0)
        
        # APD80 duration in ms
        apd_ms = (t2 - t1) * (1000.0 / 529.09)
        
        # Accumulate values for pixels that successfully met crossing/detection requirements
        valid_act = mask & has_crossing
        act_sum[valid_act] += act_ms[valid_act]
        act_count[valid_act] += 1
        
        valid_apd = mask & (t1 != -1) & (t2 != 9999)
        apd_sum[valid_apd] += apd_ms[valid_apd]
        apd_count[valid_apd] += 1

    print("Step 7: Computing final averaged maps and applying mask...")
    # Initialize output maps filled with NaNs
    final_activation = np.full((128, 128), np.nan, dtype=np.float32)
    final_apd80 = np.full((128, 128), np.nan, dtype=np.float32)

    # Divide by count to get mean over all usable beats
    valid_act_mask = mask & (act_count >= 1)
    final_activation[valid_act_mask] = act_sum[valid_act_mask] / act_count[valid_act_mask]

    valid_apd_mask = mask & (apd_count >= 1)
    final_apd80[valid_apd_mask] = apd_sum[valid_apd_mask] / apd_count[valid_apd_mask]

    # Explicitly set off-tissue pixels to NaN
    final_activation[~mask] = np.nan
    final_apd80[~mask] = np.nan

    # Step 8: Save maps
    np.save(os.path.join(submission_dir, "mask.npy"), mask)
    np.save(os.path.join(submission_dir, "activation_ms.npy"), final_activation)
    np.save(os.path.join(submission_dir, "apd80_ms.npy"), final_apd80)

    print("Pipeline successfully completed and outputs saved!")

if __name__ == "__main__":
    main()
