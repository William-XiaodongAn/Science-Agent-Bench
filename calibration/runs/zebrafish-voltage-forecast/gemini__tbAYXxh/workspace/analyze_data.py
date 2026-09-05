import numpy as np

v = np.load("/workspace/data/train_data.npy")
s = np.load("/workspace/data/train_stim.npy")
t = np.load("/workspace/data/time.npy")[:len(v)]

print("Voltage min/max:", np.min(v), np.max(v))
print("Stimulus min/max:", np.min(s), np.max(s))
print("Voltage mean/std:", np.mean(v), np.std(v))
print("Stimulus active times:", np.where(s > 0.1)[0])
print("Number of stimuli:", np.sum(s > 0.1))
# Let's find the intervals between successive stimuli
stim_idx = np.where(s > 0.1)[0]
if len(stim_idx) > 1:
    intervals = np.diff(stim_idx)
    print("Stimulus intervals min/max/mean/std:", np.min(intervals), np.max(intervals), np.mean(intervals), np.std(intervals))
else:
    print("No multiple stimuli found")

# Let's see if the action potentials (APs) have a specific duration, or how they relate to the stimulus
# Let's check how long after the stimulus the voltage stays high
