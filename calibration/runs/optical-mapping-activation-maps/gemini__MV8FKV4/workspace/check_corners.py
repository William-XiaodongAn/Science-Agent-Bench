import numpy as np

data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
n_frames = 7620
footer_elements = 4
raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))
pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)
frames = pixels[1:]
frames_t = np.transpose(frames, (0, 2, 1)).astype(np.float32)

mean_img = frames_t.mean(axis=0)

# Check 10x10 blocks in the 4 corners
top_left = mean_img[:10, :10]
top_right = mean_img[:10, -10:]
bottom_left = mean_img[-10:, :10]
bottom_right = mean_img[-10:, -10:]

print("Corner Mean Intensities:")
print(f"Top Left: {top_left.mean():.2f} (std={top_left.std():.2f}, min={top_left.min():.2f}, max={top_left.max():.2f})")
print(f"Top Right: {top_right.mean():.2f} (std={top_right.std():.2f}, min={top_right.min():.2f}, max={top_right.max():.2f})")
print(f"Bottom Left: {bottom_left.mean():.2f} (std={bottom_left.std():.2f}, min={bottom_left.min():.2f}, max={bottom_left.max():.2f})")
print(f"Bottom Right: {bottom_right.mean():.2f} (std={bottom_right.std():.2f}, min={bottom_right.min():.2f}, max={bottom_right.max():.2f})")

# Let's check some border pixels
# Left border, right border, top border, bottom border
print("\nBorder Mean Intensities (entire row/col):")
print(f"Top Row: {mean_img[0, :].mean():.2f}")
print(f"Bottom Row: {mean_img[-1, :].mean():.2f}")
print(f"Left Col: {mean_img[:, 0].mean():.2f}")
print(f"Right Col: {mean_img[:, -1].mean():.2f}")
