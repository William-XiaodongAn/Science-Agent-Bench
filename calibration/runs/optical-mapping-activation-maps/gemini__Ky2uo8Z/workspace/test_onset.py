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

# Orient signal so depolarisation is upward (raw is downward, so multiply by -1)
oriented_frames = -frames

# Define mask using a reasonable standard deviation threshold, e.g., 15
pixel_stds = np.std(oriented_frames, axis=0)
mask = pixel_stds > 15

# Calculate field-mean trace
field_mean = np.mean(oriented_frames[:, mask], axis=1)

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

print(f"Detected {len(onsets)} onsets:")
print(onsets)
