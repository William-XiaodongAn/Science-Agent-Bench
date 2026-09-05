import numpy as np

data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
n_frames = 7620
footer_elements = 4
raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))
pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)
frames = pixels[1:]
frames_t = np.transpose(frames, (0, 2, 1)).astype(np.float32)

mean_img = frames_t.mean(axis=0)

# Let's print an ASCII map of the mean image to understand the shape of the tissue.
# We'll downsample the 128x128 image to 32x32 for ASCII display.
from scipy.ndimage import zoom
downsampled = zoom(mean_img, 0.25) # 32x32

print("ASCII representation of the mean image intensity:")
chars = " .:-=+*#%@"
for r in range(32):
    row_str = ""
    for c in range(32):
        val = downsampled[r, c]
        # map val from [600, 5200] to [0, 9]
        idx = int(clip := np.clip((val - 600) / 4600 * 9, 0, 9))
        row_str += chars[idx]
    print(row_str)
