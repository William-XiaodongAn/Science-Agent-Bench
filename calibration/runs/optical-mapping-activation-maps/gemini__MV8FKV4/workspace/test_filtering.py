import numpy as np
import time
from scipy.ndimage import gaussian_filter

data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
n_frames = 7620
footer_elements = 4

# Load frames
raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))
pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)
frames = pixels[1:]  # drop frame 0
frames_t = np.transpose(frames, (0, 2, 1)).astype(np.float32)

print("Original data loaded, shape:", frames_t.shape, "dtype:", frames_t.dtype)

# Test Gaussian filtering
t0 = time.time()
# Let's use a modest filter: sigma_t=1.5 frames, sigma_space=1.0 pixels
# Since gaussian_filter is separable, we can specify sigma as a tuple (sigma_t, sigma_y, sigma_x)
sigma = (1.5, 1.0, 1.0)
filtered = gaussian_filter(frames_t, sigma=sigma)
t1 = time.time()

print(f"Gaussian filter completed in {t1 - t0:.2f} seconds.")
print("Filtered data shape:", filtered.shape, "dtype:", filtered.dtype)
print("Filtered stats - min:", filtered.min(), "max:", filtered.max(), "mean:", filtered.mean())
