import os
import numpy as np

filepath = "/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
num_frames = 7620
height, width = 128, 128
pixels_per_frame = height * width
footer_size = 4

print("Loading data...")
with open(filepath, 'rb') as f:
    header = f.read(1024)
    # read everything as uint16
    data = np.fromfile(f, dtype='<u2')

print(f"Total elements loaded: {data.size}")
expected_size = num_frames * (pixels_per_frame + footer_size)
print(f"Expected elements: {expected_size}")

if data.size == expected_size:
    print("Size match! Reshaping...")
    # Reshape to (num_frames, pixels_per_frame + footer_size)
    data = data.reshape((num_frames, pixels_per_frame + footer_size))
    # Extract frames
    frames = data[:, :pixels_per_frame].reshape((num_frames, height, width))
    # Extract footers
    footers = data[:, pixels_per_frame:]
    print("Frames shape:", frames.shape)
    print("Footers shape:", footers.shape)
    
    # Check drop frame 0
    # Let's see some basic stats of the frames (e.g. mean, standard deviation, min, max)
    # Frame 0 is under-exposed and must be dropped. Let's see how under-exposed it is.
    print("\nFrame statistics (first 5 frames):")
    for i in range(5):
        f_mean = np.mean(frames[i])
        f_std = np.std(frames[i])
        f_min = np.min(frames[i])
        f_max = np.max(frames[i])
        print(f"Frame {i}: mean={f_mean:.2f}, std={f_std:.2f}, range=[{f_min}, {f_max}]")
    
    # Save a small subset or run some diagnostics
else:
    print("Size mismatch!")
