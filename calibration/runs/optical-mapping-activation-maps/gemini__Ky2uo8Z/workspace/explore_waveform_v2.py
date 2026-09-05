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
# transpose each frame
frames = np.transpose(frames, (0, 2, 1))

# Convert to float32
frames = frames.astype(np.float32)

pixel_stds = np.std(frames, axis=0)
max_std_idx = np.unravel_index(np.argmax(pixel_stds), (128, 128))
print(f"Pixel with max std: {max_std_idx} (std={pixel_stds[max_std_idx]:.2f})")
trace = frames[:, max_std_idx[0], max_std_idx[1]]

# Let's find where transitions occur on the float32 trace
diffs = np.diff(trace)
# Let's find the absolute maximum difference and look at the trace around there
max_diff_idx = np.argmax(np.abs(diffs))
print(f"Max absolute difference in trace is at index {max_diff_idx} with value {diffs[max_diff_idx]:.2f}")
print("Trace around max absolute difference:")
for i in range(max_diff_idx-10, max_diff_idx+40):
    if 0 <= i < len(trace):
        print(f"Index {i}: {trace[i]:.1f} (diff: {trace[i+1]-trace[i]:.1f})")

# Let's check some local min and max over the whole trace to see the periodicity
# This is a cardiac mapping signal. It should have 18 beats over 7619 frames.
# 7619 / 18 is around 423 frames per beat.
# Let's print the indices where the trace changes the most in 10-frame windows.
# Or let's plot the trace (we can save it as text or compute some properties).
print("\nIs it upward or downward?")
# In an action potential with upstroke and repolarisation:
# - An UPWARD action potential: rapid rise (large positive derivative), slow decay (smaller negative derivative).
# - A DOWNWARD action potential: rapid drop (large negative derivative), slow rise (smaller positive derivative).
# Let's check the maximum positive derivative and the maximum negative derivative.
max_pos_deriv = np.max(diffs)
min_neg_deriv = np.min(diffs)
print(f"Max positive derivative: {max_pos_deriv:.2f}")
print(f"Min negative (max absolute negative) derivative: {min_neg_deriv:.2f}")
# If the absolute value of the minimum negative derivative is much larger than the maximum positive derivative,
# then the rapid transition is downwards, so depolarisation is a downward deflection.
# If max positive derivative is much larger than absolute of min negative, it is an upward deflection.
