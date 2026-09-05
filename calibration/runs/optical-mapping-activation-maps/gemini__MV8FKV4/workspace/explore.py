import os
import numpy as np

data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"

# Check file size
size = os.path.getsize(data_path)
print(f"File size: {size} bytes")

# Read header
with open(data_path, 'rb') as f:
    header = f.read(1024)
print(f"Header length: {len(header)} bytes")

# Frame size parameters
n_frames = 7620
pixels_per_frame = 128 * 128
footer_elements = 4
frame_bytes = (pixels_per_frame + footer_elements) * 2  # 32776 bytes
expected_size = 1024 + n_frames * frame_bytes
print(f"Expected size for {n_frames} frames: {expected_size} bytes")

# Let's map or read the data using memmap
# We skip the 1024-byte header.
# We shape it to (7620, 16388) uint16
raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))

# Extract pixels (first 128*128)
pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)

print("Raw pixel stats:")
print("Min:", pixels.min())
print("Max:", pixels.max())
print("Mean:", pixels.mean())

# Look at frame 0 and frame 1 stats
print("Frame 0 mean:", pixels[0].mean())
print("Frame 1 mean:", pixels[1].mean())

# Drop frame 0
frames = pixels[1:] # shape (7619, 128, 128)
print("Shape after dropping frame 0:", frames.shape)

# Transpose each frame spatial dims (0, 2, 1)
# Note: transposing spatial dimensions: we want each 128x128 frame to be transposed.
frames_t = np.transpose(frames, (0, 2, 1))

# Let's check some pixel traces
# We'll compute the mean intensity of each pixel over time to find where the tissue is.
mean_img = frames_t.mean(axis=0)
print("Mean image stats:")
print("Min:", mean_img.min(), "Max:", mean_img.max(), "Mean:", mean_img.mean())

# Let's write some details to a file or stdout
# Find a pixel with high intensity (likely tissue) and plot or print its trace.
y, x = np.unravel_index(np.argmax(mean_img), mean_img.shape)
print(f"Brightest pixel at (y={y}, x={x}) with mean intensity {mean_img[y, x]}")

# Print the first 100 values of this pixel trace
trace = frames_t[:, y, x]
print("First 100 values of trace:")
print(list(trace[:100]))
