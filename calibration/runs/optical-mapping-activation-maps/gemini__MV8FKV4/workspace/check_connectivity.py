import numpy as np
from scipy.ndimage import label, binary_fill_holes

data_path = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
n_frames = 7620
footer_elements = 4
raw_data = np.memmap(data_path, dtype='<u2', mode='r', offset=1024, shape=(n_frames, 128*128 + footer_elements))
pixels = raw_data[:, :128*128].reshape(n_frames, 128, 128)
frames = pixels[1:]
frames_t = np.transpose(frames, (0, 2, 1)).astype(np.float32)

mean_img = frames_t.mean(axis=0)
mask = mean_img > 1000

# Label connected components
labeled, num_features = label(mask)
print(f"Number of connected components in raw mask: {num_features}")

# Count size of each component
sizes = [np.sum(labeled == i) for i in range(1, num_features + 1)]
print(f"Sizes of connected components: {sizes}")

# If we keep only the largest component:
largest_label = np.argmax(sizes) + 1
cleaned_mask = (labeled == largest_label)

# We can also fill holes in the cleaned mask
filled_mask = binary_fill_holes(cleaned_mask)
print(f"Size of largest component: {np.sum(cleaned_mask)} ({cleaned_mask.mean():.2%})")
print(f"Size of filled mask: {np.sum(filled_mask)} ({filled_mask.mean():.2%})")

# Let's check IoU between raw mask and filled largest component mask
def iou(m1, m2):
    return np.logical_and(m1, m2).sum() / np.logical_or(m1, m2).sum()

print(f"IoU between raw mask and filled largest component: {iou(mask, filled_mask):.4f}")
