#!/usr/bin/env python3
"""Reference-free validation of the maps: sign check, onsets, split-half noise, smoothing sensitivity.
Writes validation.txt and validation.png next to the maps.  Runtime ~3 min (4 smoothing configs)."""
import os, sys, time
import numpy as np
from scipy import ndimage as ndi
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline as P

OUT = os.path.dirname(os.path.abspath(__file__))
lines = []
def log(s):
    print(s); lines.append(s)

f = P.load_stream()
mask, corr = P.tissue_mask(f, 0.7)
core = mask & (corr > 0.85)
field = f[:, mask].mean(1)
d = np.diff(field)
log(f'sign check on field trace (after negation): derivative 0.5th pct {np.percentile(d,0.5):+.2f}, '
    f'99.5th pct {np.percentile(d,99.5):+.2f} -> fast phase is upward (depolarisation up)')
onsets = P.detect_onsets(field); usable = onsets[onsets + 300 <= f.shape[0]]
log(f'onsets: {len(onsets)} detected, {len(usable)} usable: {usable.tolist()}; cycle length median {np.median(np.diff(usable)):.0f} frames')
log(f'mask: {mask.sum()} px ({mask.mean():.1%} of frame); core (corr>0.85): {core.sum()} px')

def run(sig_t, sig_xy):
    g = ndi.gaussian_filter(f, (sig_t, sig_xy, sig_xy), mode='nearest', truncate=4.0) if (sig_t or sig_xy) else f
    A, D = [], []
    for o in usable:
        a, p, _ = P.beat_maps(g[o - 60:o + 300]); A.append(a); D.append(p)
    return np.stack(A) * P.DT_MS, np.stack(D) * P.DT_MS

def split_half(S, reg, centre):
    e = np.nanmean(S[::2], 0) - np.nanmean(S[1::2], 0)
    e = e[reg]; e = e[np.isfinite(e)]
    if centre: e = e - np.median(e)
    return np.sqrt(np.mean(e ** 2)) / 2

configs = [(3, 1), (2, 1), (4, 1), (3, 1.5), (1, 0)]
res = {}
for c in configs:
    t0 = time.time(); A, D = run(*c); res[c] = (np.nanmean(A, 0), np.nanmean(D, 0))
    nmiss = np.isnan(D)[:, mask].sum(0)
    log(f'sigma_t={c[0]} sigma_xy={c[1]}: split-half noise (RMSE/2) act {split_half(A, mask, True):.2f} ms (core {split_half(A, core, True):.2f}), '
        f'APD80 {split_half(D, mask, False):.2f} ms (core {split_half(D, core, False):.2f}); '
        f'per-beat SD act {np.nanmedian(np.nanstd(A,0)[mask]):.2f} ms, APD80 {np.nanmedian(np.nanstd(D,0)[mask]):.2f} ms; '
        f'APD80 median {np.nanmedian(res[c][1][mask]):.1f} ms; in-mask px with >=1 beat lacking late 20% crossing: {(nmiss>0).sum()} '
        f'({time.time()-t0:.0f}s)')
ref = res[(3, 1)]
for c in configs[1:]:
    da = (res[c][0] - ref[0])[core]; da = da[np.isfinite(da)]; da -= np.median(da)
    dp = (res[c][1] - ref[1])[core]; dp = dp[np.isfinite(dp)]
    log(f'sensitivity vs primary (core): sigma_t={c[0]} sigma_xy={c[1]}: act RMSE {np.sqrt(np.mean(da**2)):.2f} ms, '
        f'APD80 RMSE {np.sqrt(np.mean(dp**2)):.2f} ms (bias {dp.mean():+.2f})')

act = np.load(os.path.join(OUT, 'activation_ms.npy')); apd = np.load(os.path.join(OUT, 'apd80_ms.npy'))
m = np.load(os.path.join(OUT, 'mask.npy'))
log(f'submitted maps: act finite in-mask {np.isfinite(act[m]).mean():.1%}, range {np.nanmin(act):.1f}..{np.nanmax(act):.1f} ms, SD {np.nanstd(act[m]):.2f} ms; '
    f'APD80 finite {np.isfinite(apd[m]).mean():.1%}, median {np.nanmedian(apd[m]):.1f} ms, SD {np.nanstd(apd[m]):.2f} ms; off-mask all NaN: {not np.isfinite(act[~m]).any() and not np.isfinite(apd[~m]).any()}')
open(os.path.join(OUT, 'validation.txt'), 'w').write('\n'.join(lines) + '\n')

fig, ax = plt.subplots(2, 3, figsize=(18, 11))
mean_img = -f.mean(0)
ax[0, 0].imshow(mean_img, cmap='gray'); ax[0, 0].contour(m, [.5], colors='r'); ax[0, 0].set_title('mask on mean image')
im = ax[0, 1].imshow(act, cmap='jet'); plt.colorbar(im, ax=ax[0, 1]); ax[0, 1].set_title('activation (ms, rel. to onset)')
im = ax[0, 2].imshow(apd, cmap='viridis'); plt.colorbar(im, ax=ax[0, 2]); ax[0, 2].set_title('APD80 (ms)')
o = usable[4]; g = ndi.gaussian_filter(f[o-60:o+300], (3, 1, 1), mode='nearest')
for (y, x) in [(70, 60), (70, 105), (30, 40), (60, 25)]:
    if m[y, x]:
        ax[1, 0].plot(np.arange(-60, 300) * P.DT_MS, f[o-60:o+300, y, x] - np.median(f[o-60:o-10, y, x]), lw=.5)
        ax[1, 0].plot(np.arange(-60, 300) * P.DT_MS, g[:, y, x] - np.median(g[:50, y, x]), lw=1.5, label=f'({y},{x}) act {act[y,x]:.0f} apd {apd[y,x]:.0f}')
ax[1, 0].legend(); ax[1, 0].set_title('beat 5: raw (thin) and smoothed (thick) pixel traces'); ax[1, 0].set_xlabel('ms from onset')
ax[1, 1].plot(field); ax[1, 1].plot(usable, field[usable], 'r.'); ax[1, 1].set_title('field-mean trace and onsets')
A, D = run(3, 1)
e = np.nanmean(D[::2], 0) - np.nanmean(D[1::2], 0)
im = ax[1, 2].imshow(np.where(m, e, np.nan), cmap='RdBu', vmin=-15, vmax=15); plt.colorbar(im, ax=ax[1, 2]); ax[1, 2].set_title('APD80 split-half difference (ms)')
plt.tight_layout(); plt.savefig(os.path.join(OUT, 'validation.png'), dpi=70)
