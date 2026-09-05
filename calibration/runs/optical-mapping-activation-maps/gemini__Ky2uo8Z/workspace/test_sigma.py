import os
import numpy as np
import scipy.ndimage

def test_sigma():
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
    
    # Let's test a few standard deviation thresholds to see how they affect the mask
    # and then test different sigmas
    for th in [12, 15, 18]:
        pixel_stds = np.std(oriented_frames, axis=0)
        mask = pixel_stds > th
        
        # Test a few sigma configurations
        for sigma_t, sigma_s in [(1.0, 0.5), (1.5, 0.75), (1.5, 1.0), (2.0, 1.0), (2.0, 1.5)]:
            smoothed = scipy.ndimage.gaussian_filter(oriented_frames, sigma=(sigma_t, sigma_s, sigma_s))
            field_mean = np.mean(smoothed[:, mask], axis=1)
            p5 = np.percentile(field_mean, 5)
            p95 = np.percentile(field_mean, 95)
            norm_field_mean = (field_mean - p5) / (p95 - p5)
            
            # Detect onsets
            onsets = []
            refractory_until = -1
            for t in range(1, len(norm_field_mean)):
                if t < refractory_until:
                    continue
                if norm_field_mean[t-1] < 0.5 and norm_field_mean[t] >= 0.5:
                    onsets.append(t)
                    refractory_until = t + 250
            
            usable_onsets = [o for o in onsets if o + 300 <= len(norm_field_mean)]
            
            # Compute maps for first 2 usable beats (to speed up test)
            num_usable = 2
            act_accum = np.zeros(np.sum(mask), dtype=np.float32)
            apd_accum = np.zeros(np.sum(mask), dtype=np.float32)
            
            ms_per_frame = 1000.0 / 529.09
            
            for o in usable_onsets[:num_usable]:
                window = smoothed[o - 60 : o + 300, mask]
                baseline = np.median(window[:50, :], axis=0)
                window_max = np.max(window, axis=0)
                amplitude = window_max - baseline
                thresh_50 = baseline + 0.5 * amplitude
                thresh_20 = baseline + 0.2 * amplitude
                
                # Activation
                crossings_50 = (window[:-1, :] < thresh_50) & (window[1:, :] >= thresh_50)
                first_cross = np.argmax(crossings_50, axis=0) + 1
                v_prev = window[first_cross - 1, np.arange(np.sum(mask))]
                v_curr = window[first_cross, np.arange(np.sum(mask))]
                denom = np.where(v_curr - v_prev == 0, 1e-5, v_curr - v_prev)
                frac = (thresh_50 - v_prev) / denom
                act_ms = ((first_cross - 1) + frac - 60) * ms_per_frame
                act_accum += act_ms
                
                # APD80 (without linear interpolation)
                peak_idx = np.argmax(window, axis=0)
                grid_indices = np.arange(360)[:, None]
                below_20 = window <= thresh_20
                t1 = np.max(np.where(below_20, np.where(grid_indices <= peak_idx, grid_indices, -1), -1), axis=0)
                t2 = np.min(np.where(below_20, np.where(grid_indices >= peak_idx, grid_indices, 9999), 9999), axis=0)
                apd_ms = (t2 - t1) * ms_per_frame
                apd_accum += apd_ms
                
            mean_act = np.mean(act_accum / num_usable)
            mean_apd = np.mean(apd_accum / num_usable)
            std_act = np.std(act_accum / num_usable)
            std_apd = np.std(apd_accum / num_usable)
            
            print(f"th={th:2d}, sigma_t={sigma_t:.1f}, sigma_s={sigma_s:.2f} | Act: mean={mean_act:6.2f}, std={std_act:5.2f} | APD80: mean={mean_apd:6.2f}, std={std_apd:5.2f} | Onsets: {len(usable_onsets)}")

if __name__ == "__main__":
    test_sigma()
