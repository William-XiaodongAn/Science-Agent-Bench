import os
import numpy as np
import scipy.ndimage

def compare():
    filepath = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
    num_frames = 7620
    height, width = 128, 128
    pixels_per_frame = height * width
    footer_size = 4
    
    with open(filepath, 'rb') as f:
        f.read(1024)
        data = np.fromfile(f, dtype='<u2')
    
    data = data.reshape((num_frames, pixels_per_frame + footer_size))
    frames = data[:, :pixels_per_frame].reshape((num_frames, height, width))
    frames = frames[1:]  # Drop frame 0
    frames = np.transpose(frames, (0, 2, 1))
    frames = frames.astype(np.float32)
    oriented_frames = -frames
    
    # Define mask std > 15
    pixel_stds = np.std(oriented_frames, axis=0)
    mask = pixel_stds > 15
    num_mask = np.sum(mask)
    
    # Smooth
    smoothed = scipy.ndimage.gaussian_filter(oriented_frames, sigma=(1.5, 1.0, 1.0))
    
    # Field mean and onsets
    field_mean = np.mean(smoothed[:, mask], axis=1)
    p5, p95 = np.percentile(field_mean, [5, 95])
    norm_field_mean = (field_mean - p5) / (p95 - p5)
    
    onsets = []
    refractory_until = -1
    for t in range(1, len(norm_field_mean)):
        if t < refractory_until:
            continue
        if norm_field_mean[t-1] < 0.5 and norm_field_mean[t] >= 0.5:
            onsets.append(t)
            refractory_until = t + 250
            
    usable_onsets = [o for o in onsets if o + 300 <= len(norm_field_mean)]
    ms_per_frame = 1000.0 / 529.09
    
    # Compute for the first beat
    o = usable_onsets[0]
    window = smoothed[o - 60 : o + 300, mask]
    baseline = np.median(window[:50, :], axis=0)
    window_max = np.max(window, axis=0)
    amplitude = window_max - baseline
    thresh_20 = baseline + 0.2 * amplitude
    peak_idx = np.argmax(window, axis=0)
    
    # Discrete t1, t2
    grid_indices = np.arange(360)[:, None]
    below_20 = window <= thresh_20
    t1_disc = np.max(np.where(below_20, np.where(grid_indices <= peak_idx, grid_indices, -1), -1), axis=0)
    t2_disc = np.min(np.where(below_20, np.where(grid_indices >= peak_idx, grid_indices, 9999), 9999), axis=0)
    apd_disc = (t2_disc - t1_disc) * ms_per_frame
    
    # Interpolated t1, t2
    # Before peak: crossing from t1_disc to t1_disc + 1
    # Let's ensure indices are safe
    t1_disc_safe = np.clip(t1_disc, 0, 358)
    v_t1 = window[t1_disc_safe, np.arange(num_mask)]
    v_t1_plus = window[t1_disc_safe + 1, np.arange(num_mask)]
    denom1 = np.where(v_t1_plus - v_t1 == 0, 1e-5, v_t1_plus - v_t1)
    frac1 = (thresh_20 - v_t1) / denom1
    frac1 = np.clip(frac1, 0.0, 1.0)
    t1_interp = t1_disc_safe + frac1
    
    # After peak: crossing from t2_disc - 1 to t2_disc
    t2_disc_safe = np.clip(t2_disc, 1, 359)
    v_t2_minus = window[t2_disc_safe - 1, np.arange(num_mask)]
    v_t2 = window[t2_disc_safe, np.arange(num_mask)]
    denom2 = np.where(v_t2_minus - v_t2 == 0, 1e-5, v_t2_minus - v_t2)
    frac2 = (v_t2_minus - thresh_20) / denom2
    frac2 = np.clip(frac2, 0.0, 1.0)
    t2_interp = (t2_disc_safe - 1) + frac2
    
    apd_interp = (t2_interp - t1_interp) * ms_per_frame
    
    # Filter out invalid APDs
    valid = (t1_disc != -1) & (t2_disc != 9999)
    apd_disc = apd_disc[valid]
    apd_interp = apd_interp[valid]
    
    print("Discrete APD80 stats:")
    print(f"Mean: {np.mean(apd_disc):.2f}, Std: {np.std(apd_disc):.2f}, Range: [{np.min(apd_disc):.2f}, {np.max(apd_disc):.2f}]")
    print("\nInterpolated APD80 stats:")
    print(f"Mean: {np.mean(apd_interp):.2f}, Std: {np.std(apd_interp):.2f}, Range: [{np.min(apd_interp):.2f}, {np.max(apd_interp):.2f}]")
    print(f"\nMean difference (Interp - Discrete): {np.mean(apd_interp - apd_disc):.4f} ms")

if __name__ == "__main__":
    compare()
