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

print("Std Threshold | Pixel Count | Mask Fraction | Derivative (change in count)")
prev_count = None
for th in range(6, 31):
    count = np.sum(pixel_stds > th)
    frac = count / (128*128)
    diff = ""
    if prev_count is not None:
        diff = f"{- (count - prev_count)}"
    print(f"std > {th:2d}      | {count:11d} | {frac:.4f}        | {diff}")
    prev_count = count
