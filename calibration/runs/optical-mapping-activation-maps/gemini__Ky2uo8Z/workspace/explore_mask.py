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
# Let's transpose each frame: frames shape is now (7619, 128, 128)
frames = np.transpose(frames, (0, 2, 1))

# Let's look at pixel mean and std
pixel_means = np.mean(frames, axis=0)
pixel_stds = np.std(frames, axis=0)

print("Pixel Means:")
print(f"Min mean: {np.min(pixel_means):.2f}, Max mean: {np.max(pixel_means):.2f}")
print(f"Mean of means: {np.mean(pixel_means):.2f}, Median of means: {np.median(pixel_means):.2f}")

print("\nPixel Stds:")
print(f"Min std: {np.min(pixel_stds):.2f}, Max std: {np.max(pixel_stds):.2f}")
print(f"Mean of stds: {np.mean(pixel_stds):.2f}, Median of stds: {np.median(pixel_stds):.2f}")

# Let's print a small block of means to see if there's a clear threshold
# For example, let's histogram the pixel means and stds
hist_means, bin_edges_means = np.histogram(pixel_means, bins=10)
hist_stds, bin_edges_stds = np.histogram(pixel_stds, bins=10)

print("\nMean distribution:")
for i in range(10):
    print(f"[{bin_edges_means[i]:.1f}, {bin_edges_means[i+1]:.1f}]: {hist_means[i]}")

print("\nStd distribution:")
for i in range(10):
    print(f"[{bin_edges_stds[i]:.1f}, {bin_edges_stds[i+1]:.1f}]: {hist_stds[i]}")

# Let's look at a single pixel's trace over time to determine upstroke direction.
# Let's find a pixel with high std (likely on-tissue)
max_std_idx = np.unravel_index(np.argmax(pixel_stds), (128, 128))
print(f"\nPixel with max std: {max_std_idx} (std={pixel_stds[max_std_idx]:.2f})")
trace = frames[:, max_std_idx[0], max_std_idx[1]]

# Let's print the first 100 values of this trace
print("\nFirst 100 values of max std pixel trace:")
print(list(trace[:100]))

# Let's find where a transition occurs
diffs = np.diff(trace)
max_diff_idx = np.argmax(np.abs(diffs))
print(f"\nMax absolute difference in trace is at index {max_diff_idx} with value {diffs[max_diff_idx]:.2f}")
print("Trace around max absolute difference:")
print(list(trace[max_diff_idx-10 : max_diff_idx+15]))
