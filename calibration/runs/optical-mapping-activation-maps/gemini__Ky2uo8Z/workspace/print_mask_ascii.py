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

# Downsample from 128x128 to 32x32 by block averaging
down_h, down_w = 32, 32
block_h, block_w = 4, 4
downsampled = np.zeros((down_h, down_w))
for r in range(down_h):
    for c in range(down_w):
        downsampled[r, c] = np.mean(pixel_stds[r*block_h:(r+1)*block_h, c*block_w:(c+1)*block_w])

# Convert to ASCII characters
chars = " .:-=+*#%@"
num_chars = len(chars)
min_val, max_val = np.min(downsampled), np.max(downsampled)
print(f"Downsampled Std Map (min={min_val:.1f}, max={max_val:.1f}):")
for r in range(down_h):
    line = ""
    for c in range(down_w):
        val = downsampled[r, c]
        # map to 0 to num_chars-1
        idx = int((val - min_val) / (max_val - min_val + 1e-5) * (num_chars - 1))
        idx = max(0, min(num_chars - 1, idx))
        line += chars[idx]
    print(line)
