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

for th_std in [10, 12, 15, 18, 20, 25, 30]:
    mask = pixel_stds > th_std
    frac = np.mean(mask)
    print(f"Threshold std > {th_std}: fraction of frame = {frac:.4f} ({np.sum(mask)} pixels)")

print("\nLet's also look at mean thresholds:")
for th_mean in [700, 800, 900, 1000, 1100, 1200]:
    mask = pixel_means > th_mean
    frac = np.mean(mask)
    print(f"Threshold mean > {th_mean}: fraction of frame = {frac:.4f} ({np.sum(mask)} pixels)")
