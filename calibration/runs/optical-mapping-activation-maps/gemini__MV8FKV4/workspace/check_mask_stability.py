import numpy as np

data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
n_frames = 7620
footer_elements = 4
raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))
pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)
frames = pixels[1:]
frames_t = np.transpose(frames, (0, 2, 1)).astype(np.float32)

mean_img = frames_t.mean(axis=0)

# Generate masks
m900 = mean_img > 900
m950 = mean_img > 950
m1000 = mean_img > 1000
m1050 = mean_img > 1050
m1100 = mean_img > 1100
m1200 = mean_img > 1200

def iou(mask1, mask2):
    return np.logical_and(mask1, mask2).sum() / np.logical_or(mask1, mask2).sum()

print("Intersection-over-Union (IoU) between different masks:")
print(f"900 vs 1000: {iou(m900, m1000):.4f}")
print(f"950 vs 1000: {iou(m950, m1000):.4f}")
print(f"1000 vs 1050: {iou(m1000, m1050):.4f}")
print(f"1000 vs 1100: {iou(m1000, m1100):.4f}")
print(f"1000 vs 1200: {iou(m1000, m1200):.4f}")

# Check fractional coverage
print("\nFractional coverage:")
print(f"900: {m900.mean():.2%}")
print(f"950: {m950.mean():.2%}")
print(f"1000: {m1000.mean():.2%}")
print(f"1050: {m1050.mean():.2%}")
print(f"1100: {m1100.mean():.2%}")
print(f"1200: {m1200.mean():.2%}")
