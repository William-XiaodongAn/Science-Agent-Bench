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

pixel_means = np.mean(frames, axis=0)
pixel_stds = np.std(frames, axis=0)

# Check corner pixels (likely background)
corners = [
    pixel_means[:10, :10],
    pixel_means[:10, -10:],
    pixel_means[-10:, :10],
    pixel_means[-10:, -10:]
]
print("Corner Means (first/last 10 rows/cols):")
for i, c in enumerate(corners):
    print(f"Corner {i}: mean={np.mean(c):.2f}, std={np.std(c):.2f}, range=[{np.min(c):.2f}, {np.max(c):.2f}]")

corner_stds = [
    pixel_stds[:10, :10],
    pixel_stds[:10, -10:],
    pixel_stds[-10:, :10],
    pixel_stds[-10:, -10:]
]
print("\nCorner Stds (first/last 10 rows/cols):")
for i, c in enumerate(corner_stds):
    print(f"Corner {i}: mean={np.mean(c):.2f}, std={np.std(c):.2f}, range=[{np.min(c):.2f}, {np.max(c):.2f}]")

# Let's print the central region (likely tissue)
center_mean = pixel_means[40:80, 40:80]
center_std = pixel_stds[40:80, 40:80]
print(f"\nCenter Mean (40:80, 40:80): mean={np.mean(center_mean):.2f}, std={np.std(center_mean):.2f}, range=[{np.min(center_mean):.2f}, {np.max(center_mean):.2f}]")
print(f"Center Std (40:80, 40:80): mean={np.mean(center_std):.2f}, std={np.std(center_std):.2f}, range=[{np.min(center_std):.2f}, {np.max(center_std):.2f}]")
