import numpy as np

data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
n_frames = 7620
footer_elements = 4
raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))
pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)
frames = pixels[1:]  # shape (7619, 128, 128)
frames_t = np.transpose(frames, (0, 2, 1))

mean_img = frames_t.mean(axis=0)

# Let's perform Otsu's thresholding to find the optimal separation between background and tissue
# We can implement Otsu's thresholding from scratch using numpy
def otsu_threshold(img):
    counts, bin_edges = np.histogram(img, bins=256)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    
    weight1 = np.cumsum(counts)
    weight2 = np.cumsum(counts[::-1])[::-1]
    
    mean1 = np.cumsum(counts * bin_centers) / weight1
    mean2 = (np.cumsum((counts * bin_centers)[::-1]) / weight2[::-1])[::-1]
    
    variance12 = weight1[:-1] * weight2[1:] * (mean1[:-1] - mean2[1:]) ** 2
    idx = np.argmax(variance12)
    return bin_centers[idx]

otsu_thresh = otsu_threshold(mean_img)
print(f"Otsu's threshold: {otsu_thresh:.2f}")
print(f"Fraction of pixels above Otsu's threshold: {(mean_img > otsu_thresh).mean():.1%}")

# Let's implement the beat detection on field-mean trace.
# "Beat onsets are detected on the field-mean trace (mean over tissue pixels, normalised between its 5th and 95th percentiles) by the 50% upward crossing, with a 250-frame refractory period."
# Wait! Let's write a function to detect onsets for a given mask and a given sign direction (positive or negative).
# Since depolarisation is a downward deflection in the raw data, if we flip the signal:
# flipped_frames = -frames_t (or constant - frames_t)
# Then the field-mean trace is flipped_mean = -mean over tissue pixels.
# Let's check how the normalization works:
# "normalised between its 5th and 95th percentiles" -> trace_norm = (trace - p5) / (p95 - p5)
# Then the "50% upward crossing" is when trace_norm crosses 0.5 from below to above.
# Let's check this.

def detect_onsets(mask, flip=True):
    # Field-mean trace over the mask
    field_mean = frames_t[:, mask].mean(axis=1)
    if flip:
        field_mean = -field_mean
    
    p5 = np.percentile(field_mean, 5)
    p95 = np.percentile(field_mean, 95)
    norm_trace = (field_mean - p5) / (p95 - p5)
    
    # 50% upward crossing with a 250-frame refractory period
    onsets = []
    i = 0
    N = len(norm_trace)
    while i < N - 1:
        # Check if we have an upward crossing of 0.5
        if norm_trace[i] <= 0.5 and norm_trace[i+1] > 0.5:
            onsets.append(i + 1) # frame index of crossing
            i += 250 # refractory period
        else:
            i += 1
            
    return norm_trace, onsets

for thresh in [otsu_thresh, 1000, 1100, 1200]:
    mask = mean_img > thresh
    norm_trace, onsets = detect_onsets(mask)
    print(f"Threshold {thresh:.1f}: found {len(onsets)} onsets")
    print("Onsets:", onsets)
    if len(onsets) > 0:
        # Check consecutive onset diffs
        diffs = np.diff(onsets)
        print("Onset intervals (frames):", diffs)
        print("Onset intervals (ms):", diffs * 1.890)
