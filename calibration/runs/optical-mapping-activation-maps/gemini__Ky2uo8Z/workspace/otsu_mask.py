import numpy as np

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

pixel_stds = np.std(frames, axis=0)
pixel_means = np.mean(frames, axis=0)

# Let's apply Otsu's thresholding manually
def otsu_threshold(image):
    # Flatten the image
    flat = image.flatten()
    # Compute histogram
    hist, bin_edges = np.histogram(flat, bins=256)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    
    # Class probabilities and class means for all possible thresholds
    weight1 = np.cumsum(hist)
    weight2 = np.cumsum(hist[::-1])[::-1]
    
    # Avoid division by zero
    weight1 = np.where(weight1 == 0, 1e-10, weight1)
    weight2 = np.where(weight2 == 0, 1e-10, weight2)
    
    mean1 = np.cumsum(hist * bin_centers) / weight1
    mean2 = (np.cumsum((hist * bin_centers)[::-1]) / weight2[::-1])[::-1]
    
    # Inter-class variance
    variance_between = weight1 * weight2 * (mean1 - mean2) ** 2
    
    # Index of maximum variance
    idx = np.argmax(variance_between)
    return bin_centers[idx]

otsu_std = otsu_threshold(pixel_stds)
otsu_mean = otsu_threshold(pixel_means)

print(f"Otsu threshold on pixel_stds: {otsu_std:.2f}")
mask_std = pixel_stds > otsu_std
print(f"Otsu std mask fraction: {np.mean(mask_std):.4f} ({np.sum(mask_std)} pixels)")

print(f"Otsu threshold on pixel_means: {otsu_mean:.2f}")
mask_mean = pixel_means > otsu_mean
print(f"Otsu mean mask fraction: {np.mean(mask_mean):.4f} ({np.sum(mask_mean)} pixels)")

# What if we use a combination of mean and std?
# e.g., on-tissue pixels are those with both mean > some threshold and std > some threshold.
# Or is it just std > 15?
# Let's write a script to check if there is an existing mask we can infer, or let's look at the shape of the mask.
