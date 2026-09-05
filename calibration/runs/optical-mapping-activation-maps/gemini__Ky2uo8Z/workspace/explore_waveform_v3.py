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
max_std_idx = np.unravel_index(np.argmax(pixel_stds), (128, 128))
trace = frames[:, max_std_idx[0], max_std_idx[1]]

# Print trace values at regular intervals around a peak
print("Trace every 10 frames from index 6500 to 7000:")
for i in range(6500, 7000, 10):
    print(f"Index {i}: {trace[i]:.1f}")
