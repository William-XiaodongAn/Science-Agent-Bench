import numpy as np

data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
n_frames = 7620
footer_elements = 4
raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))
pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)
frames = pixels[1:]  # shape (7619, 128, 128)
frames_t = np.transpose(frames, (0, 2, 1)).astype(np.float32)

mean_img = frames_t.mean(axis=0)
std_img = frames_t.std(axis=0)

print("Mean image percentiles [1, 5, 10, 25, 50, 75, 90, 95, 99]:")
print([np.percentile(mean_img, p) for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]])

print("\nStd image percentiles [1, 5, 10, 25, 50, 75, 90, 95, 99]:")
print([np.percentile(std_img, p) for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]])

# Let's see if Otsu's threshold on mean_img or std_img works better, or if they are highly correlated.
corr = np.corrcoef(mean_img.ravel(), std_img.ravel())[0, 1]
print(f"\nCorrelation between mean intensity and standard deviation: {corr:.4f}")

# Let's count pixels above various std thresholds
for std_thresh in [10, 20, 30, 40, 50, 60, 80, 100]:
    frac = (std_img > std_thresh).mean()
    print(f"Std > {std_thresh}: {frac:.1%} of frame")

# Let's also look at the ratio of std to mean (coefficient of variation)
cv_img = std_img / (mean_img + 1e-5)
print("\nCV image percentiles:")
print([np.percentile(cv_img, p) for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]])
