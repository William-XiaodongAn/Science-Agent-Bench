import numpy as np

data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
n_frames = 7620
footer_elements = 4
raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))
pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)
frames = pixels[1:]  # shape (7619, 128, 128)
frames_t = np.transpose(frames, (0, 2, 1))

# Let's inspect the distribution of mean pixel intensity to see if we can find a tissue mask.
mean_img = frames_t.mean(axis=0)
print("Mean image values:")
print("Min:", mean_img.min())
print("Max:", mean_img.max())
print("Percentiles [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99]:")
print([np.percentile(mean_img, p) for p in [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99]])

# Let's define a rough mask using a percentile. For example, pixels with mean > 1000 or some threshold.
# Let's test a few thresholds and print the fraction of pixels.
for thresh in [800, 1000, 1200, 1500, 2000]:
    mask_frac = (mean_img > thresh).mean()
    print(f"Threshold {thresh}: {mask_frac:.1%} of frame is tissue")

# Now let's analyze the temporal signal of a typical tissue pixel (e.g. where mean_img is > 3000)
# We find a pixel with high intensity
tissue_y, tissue_x = np.where(mean_img > 3000)
# Select one in the middle of tissue
idx = len(tissue_y) // 2
ty, tx = tissue_y[idx], tissue_x[idx]
print(f"Selected tissue pixel at ({ty}, {tx}) with mean {mean_img[ty, tx]}")

trace = frames_t[:, ty, tx].astype(float)

# Compute temporal derivative
diff = np.diff(trace)
max_diff = np.max(diff)
min_diff = np.min(diff)
print(f"Trace max temporal difference: {max_diff}")
print(f"Trace min temporal difference: {min_diff}")

# If min_diff is much more negative than max_diff is positive, the fast deflection is downward, meaning depolarisation is downward.
# If max_diff is much more positive than min_diff is negative, the fast deflection is upward, meaning depolarisation is upward.
ratio = abs(min_diff) / abs(max_diff) if max_diff != 0 else 0
print(f"Absolute ratio of min_diff / max_diff: {ratio:.3f}")
if ratio > 1.5:
    print("Sign convention: Depolarisation is a DOWNWARD deflection (fast decrease, slow increase). We need to flip it.")
elif ratio < 0.67:
    print("Sign convention: Depolarisation is an UPWARD deflection (fast increase, slow decrease).")
else:
    print("Sign convention is ambiguous from derivative of a single pixel. Let's do a more robust check on the average trace.")

# Let's check the field-mean trace.
# We will compute the mean over tissue pixels (defined by mean_img > 1000)
tissue_mask = mean_img > 1000
field_mean_raw = frames_t[:, tissue_mask].mean(axis=1)

# Compute temporal derivative of field-mean trace
field_diff = np.diff(field_mean_raw)
f_max_diff = np.max(field_diff)
f_min_diff = np.min(field_diff)
print(f"Field-mean max temporal difference: {f_max_diff}")
print(f"Field-mean min temporal difference: {f_min_diff}")
f_ratio = abs(f_min_diff) / abs(f_max_diff)
print(f"Field-mean ratio: {f_ratio:.3f}")
if f_ratio > 1.2:
    print("FIELD MEAN: Depolarisation is a DOWNWARD deflection in raw data.")
else:
    print("FIELD MEAN: Depolarisation is an UPWARD deflection in raw data.")
