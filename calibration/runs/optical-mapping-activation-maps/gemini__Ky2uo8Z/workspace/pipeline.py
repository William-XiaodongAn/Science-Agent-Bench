import os
import numpy as np
import scipy.ndimage

def run_pipeline():
    filepath = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
    num_frames = 7620
    height, width = 128, 128
    pixels_per_frame = height * width
    footer_size = 4
    
    print("Loading data...")
    with open(filepath, 'rb') as f:
        f.read(1024)
        data = np.fromfile(f, dtype='<u2')
    
    data = data.reshape((num_frames, pixels_per_frame + footer_size))
    frames = data[:, :pixels_per_frame].reshape((num_frames, height, width))
    frames = frames[1:]  # Drop frame 0
    frames = np.transpose(frames, (0, 2, 1))
    frames = frames.astype(np.float32)
    
    # Orient signal: raw is downward deflection, so -frames makes it upward
    oriented_frames = -frames
    
    # 1. Define mask
    # We saw background noise std < 10, tissue std > 40. Let's use std > 15 as tissue mask.
    pixel_stds = np.std(oriented_frames, axis=0)
    mask = pixel_stds > 15
    print(f"Mask covers {np.mean(mask):.4f} of the frame ({np.sum(mask)} pixels)")
    
    # 2. Smoothing
    # Modest Gaussian smoothing in time and space (a few frames, about a pixel)
    # Let's try sigma_t = 1.5 frames, sigma_s = 1.0 pixel
    print("Smoothing frames...")
    smoothed_frames = scipy.ndimage.gaussian_filter(oriented_frames, sigma=(1.5, 1.0, 1.0))
    
    # 3. Detect beat onsets on the field-mean trace (using smoothed frames)
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
    # len(norm_field_mean) = 7619, so o + 300 <= 7619
    usable_onsets = [o for o in onsets if o + 300 <= len(norm_field_mean)]
    print(f"Usable onsets ({len(usable_onsets)}): {usable_onsets}")
    
    # Initialize arrays for activation and apd80 accumulation
    # Shape (128, 128), but we only compute for mask pixels
    # For each usable beat, we compute activation and apd80, then average
    num_usable = len(usable_onsets)
    act_accum = np.zeros((height, width), dtype=np.float32)
    apd_accum = np.zeros((height, width), dtype=np.float32)
    
    # Let's define the frame rate
    fps = 529.09
    ms_per_frame = 1000.0 / fps
    
    # Let's loop over pixels in the mask
    y_indices, x_indices = np.where(mask)
    num_mask_pixels = len(y_indices)
    print(f"Processing {num_mask_pixels} mask pixels over {num_usable} beats...")
    
    # We can vectorize or optimize this loop
    # For each beat, let's extract the windows for all pixels in mask
    # Window shape: (360, num_mask_pixels)
    for beat_idx, o in enumerate(usable_onsets):
        print(f"Processing beat {beat_idx+1}/{num_usable} (onset at frame {o})...")
        # Window starts 60 frames before onset and runs 300 frames past
        window_start = o - 60
        window_end = o + 300
        # shape: (360, height, width)
        window = smoothed_frames[window_start:window_end, :, :]
        
        # We only care about mask pixels
        # Extract window for mask pixels: shape (360, num_mask_pixels)
        window_mask = window[:, mask]
        
        # Baseline = median of first 50 frames
        baseline = np.median(window_mask[:50, :], axis=0) # shape (num_mask_pixels,)
        # Amplitude = window maximum minus baseline
        window_max = np.max(window_mask, axis=0) # shape (num_mask_pixels,)
        amplitude = window_max - baseline # shape (num_mask_pixels,)
        
        # 50% threshold for activation
        thresh_50 = baseline + 0.5 * amplitude # shape (num_mask_pixels,)
        # 20% threshold for APD80
        thresh_20 = baseline + 0.2 * amplitude # shape (num_mask_pixels,)
        
        # Find activation crossing
        # "moment the pixel first crosses 50% of its upstroke amplitude, linearly interpolated"
        # We look for the first index k in 1..359 where window_mask[k-1] < thresh_50 and window_mask[k] >= thresh_50
        # Let's find this for each pixel
        # Vectorized crossing search:
        # We can construct a boolean array of crossings: (359, num_mask_pixels)
        crossings_50 = (window_mask[:-1, :] < thresh_50) & (window_mask[1:, :] >= thresh_50)
        
        # For each pixel, find the first crossing
        # argmax along axis 0 returns the first True index
        first_cross_idx = np.argmax(crossings_50, axis=0) + 1 # +1 to get the crossing frame index k
        
        # Let's verify that a crossing actually occurred
        has_crossing_50 = np.any(crossings_50, axis=0)
        
        # Interpolate
        # k = first_cross_idx
        v_prev = window_mask[first_cross_idx - 1, np.arange(num_mask_pixels)]
        v_curr = window_mask[first_cross_idx, np.arange(num_mask_pixels)]
        denom = v_curr - v_prev
        # handle division by zero just in case
        denom = np.where(denom == 0, 1e-5, denom)
        frac = (thresh_50 - v_prev) / denom
        # Clip frac to [0, 1] to be safe
        frac = np.clip(frac, 0.0, 1.0)
        
        # Crossing frame relative to onset o:
        # first_cross_idx is 0-indexed relative to window start.
        # Window start is o - 60, so window index 60 is the onset o.
        # Crossing frame relative to onset o is: (first_cross_idx - 1) + frac - 60
        act_frame_rel = (first_cross_idx - 1) + frac - 60
        act_ms = act_frame_rel * ms_per_frame
        
        # APD80:
        # "from the last frame at or below the 20% level before the peak to the first frame at or below it after the peak, in ms."
        # peak_idx is the index of maximum in window
        peak_idx = np.argmax(window_mask, axis=0) # shape (num_mask_pixels,)
        
        # Let's find:
        # t1: the last frame at or below thresh_20 before the peak (i.e. index j <= peak_idx where window_mask[j] <= thresh_20)
        # t2: the first frame at or below thresh_20 after the peak (i.e. index j >= peak_idx where window_mask[j] <= thresh_20)
        
        # Let's compute t1 and t2 for each pixel
        t1 = np.zeros(num_mask_pixels, dtype=np.float32)
        t2 = np.zeros(num_mask_pixels, dtype=np.float32)
        
        # Let's loop over mask pixels (this is fast enough for ~10000 pixels)
        # Wait, can we vectorize this?
        # Yes, we can vectorize by creating index grids or using masked arrays, but a simple loop in python
        # for 10000 pixels is also extremely fast if written efficiently.
        # Let's do it efficiently with numpy operations:
        # Construct range of indices: shape (360, 1)
        grid_indices = np.arange(360)[:, None]
        
        # Condition for <= 20% threshold: (360, num_mask_pixels)
        below_20 = window_mask <= thresh_20
        
        # For t1: index j <= peak_idx where below_20 is True
        # We can mask indices > peak_idx
        indices_before = np.where(grid_indices <= peak_idx, grid_indices, -1)
        # Find the max index before peak where below_20 is True
        t1 = np.max(np.where(below_20, indices_before, -1), axis=0)
        
        # For t2: index j >= peak_idx where below_20 is True
        # We can mask indices < peak_idx
        indices_after = np.where(grid_indices >= peak_idx, grid_indices, 9999)
        # Find the min index after peak where below_20 is True
        t2 = np.min(np.where(below_20, indices_after, 9999), axis=0)
        
        # Let's check for valid t1 and t2
        valid_apd = (t1 != -1) & (t2 != 9999)
        
        # APD80 duration in frames: t2 - t1
        # Convert to ms:
        apd_ms = (t2 - t1) * ms_per_frame
        
        # If not valid, set to NaN or handle
        # Accumulate
        act_accum[mask] += np.where(has_crossing_50, act_ms, np.nan)
        apd_accum[mask] += np.where(valid_apd, apd_ms, np.nan)
        
    # Compute mean over all usable beats
    activation_ms = np.full((height, width), np.nan, dtype=np.float32)
    apd80_ms = np.full((height, width), np.nan, dtype=np.float32)
    
    activation_ms[mask] = act_accum[mask] / num_usable
    apd80_ms[mask] = apd_accum[mask] / num_usable
    
    print("\nCalculated Maps Stats:")
    print(f"Activation: mean={np.nanmean(activation_ms):.2f}, std={np.nanstd(activation_ms):.2f}, range=[{np.nanmin(activation_ms):.2f}, {np.nanmax(activation_ms):.2f}]")
    print(f"APD80: mean={np.nanmean(apd80_ms):.2f}, std={np.nanstd(apd80_ms):.2f}, range=[{np.nanmin(apd80_ms):.2f}, {np.nanmax(apd80_ms):.2f}]")
    
    # Save the output files
    os.makedirs("/workspace/submission", exist_ok=True)
    np.save("/workspace/submission/mask.npy", mask)
    np.save("/workspace/submission/activation_ms.npy", activation_ms)
    np.save("/workspace/submission/apd80_ms.npy", apd80_ms)
    print("Files saved successfully!")

if __name__ == "__main__":
    run_pipeline()
