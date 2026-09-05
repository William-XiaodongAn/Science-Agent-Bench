import numpy as np

mask = np.load("/workspace/submission/mask.npy")
act = np.load("/workspace/submission/activation_ms.npy")
apd = np.load("/workspace/submission/apd80_ms.npy")

print(f"Mask shape: {mask.shape}, sum={np.sum(mask)}, mean={np.mean(mask):.4f}")
print(f"Activation shape: {act.shape}")
print(f"APD80 shape: {apd.shape}")

# Finite values in-mask
fin_act = np.isfinite(act[mask])
fin_apd = np.isfinite(apd[mask])

print(f"In-mask finite activation pixels: {np.sum(fin_act)} of {np.sum(mask)} ({np.mean(fin_act):.2%})")
print(f"In-mask finite APD80 pixels: {np.sum(fin_apd)} of {np.sum(mask)} ({np.mean(fin_apd):.2%})")

if np.sum(fin_apd) < np.sum(mask):
    # Let's see some example pixels that are NaN
    nan_indices = np.where(mask & ~np.isfinite(apd))
    print(f"Number of NaN APD80 pixels in-mask: {len(nan_indices[0])}")
    print("Example NaN indices:", list(zip(nan_indices[0][:10], nan_indices[1][:10])))
