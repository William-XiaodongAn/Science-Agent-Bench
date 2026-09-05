#!/usr/bin/env python3
"""Activation / APD80 maps from a raw optical-mapping stream.

Usage: python3 pipeline.py [--sigma_t 3] [--sigma_xy 1] [--out /workspace/submission]

Steps
 1. read 16-bit LE stream (1024-byte header, 128*128 + 4 footer words per frame), drop frame 0,
    transpose each frame, negate (depolarisation is a downward deflection in this file).
 2. tissue mask: correlation of each pixel with the field-mean trace > 0.7, fill holes, largest
    connected component, binary closing (radius 4 px), 2-px dilation.
 3. Gaussian smoothing in time (sigma_t frames) and space (sigma_xy px).
 4. beat onsets on the field-mean trace (mean over mask, normalised 5th..95th percentile,
    50% upward crossing, 250-frame refractory); a beat is usable if onset + 300 <= n_frames.
 5. per beat, window [onset-60, onset+300): baseline = median of first 50 frames,
    amplitude = window max - baseline, activation = interpolated first 50% crossing,
    APD80 = frames from last <=20% before peak to first <=20% after peak, in ms.
 6. mean over usable beats -> activation_ms (relative to beat onset), apd80_ms; NaN off-mask.
 7. in-mask pixels that are not tissue-like (corr < 0.3) or have extreme beat-to-beat scatter
    are filled from the nearest reliable pixel (a few dozen border / motion-edge pixels).
"""
import argparse, os, time
import numpy as np
from scipy import ndimage as ndi

FPS = 529.09
DT_MS = 1000.0 / FPS
PATH = '/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat'


def load_stream(path=PATH):
    raw = np.fromfile(path, dtype='<u2', offset=1024)
    n = raw.size // 16388
    raw = raw[:n * 16388].reshape(n, 16388)[:, :16384].reshape(n, 128, 128)
    f = raw[1:].astype(np.float32)                      # drop under-exposed frame 0
    f = np.ascontiguousarray(np.transpose(f, (0, 2, 1)))  # stored transposed
    return -f                                           # depolarisation upward


def tissue_mask(f, thr=0.7, dilate=2, close_radius=4):
    tr = f.reshape(f.shape[0], -1).mean(1)
    fz = (tr - tr.mean()) / tr.std()
    X = f.reshape(f.shape[0], -1)
    mu = X.mean(0); sd = X.std(0)
    corr = ((fz @ X) / f.shape[0] - fz.mean() * mu) / sd
    corr = corr.reshape(128, 128)
    m = corr > thr
    m = ndi.binary_fill_holes(m)
    lab, n = ndi.label(m)
    if n > 1:
        sizes = ndi.sum(m, lab, range(1, n + 1))
        m = lab == (1 + np.argmax(sizes))
    if close_radius:
        yy, xx = np.mgrid[-close_radius:close_radius + 1, -close_radius:close_radius + 1]
        m = ndi.binary_closing(m, structure=(xx ** 2 + yy ** 2) <= close_radius ** 2) | m
    if dilate:
        m = ndi.binary_dilation(m, iterations=dilate)
    return m, corr


def detect_onsets(trace, refractory=250):
    p5, p95 = np.percentile(trace, [5, 95])
    n = (trace - p5) / (p95 - p5)
    on, last = [], -10**9
    for i in range(1, len(n)):
        if n[i - 1] < 0.5 <= n[i] and i - last > refractory:
            on.append(i); last = i
    return np.array(on)


def beat_maps(W, pre=60):
    """W: (360, H, W) window. Returns activation (frames, rel. to onset) and APD80 (frames)."""
    T = W.shape[0]
    base = np.median(W[:50], axis=0)
    amp = W.max(0) - base
    # activation: first crossing of 50 %
    thr = base + 0.5 * amp
    above = W >= thr
    i = above.argmax(0)                                  # first True (amp>0 guarantees one)
    i0 = np.clip(i - 1, 0, T - 1)
    v1 = np.take_along_axis(W, i[None], 0)[0]
    v0 = np.take_along_axis(W, i0[None], 0)[0]
    frac = (thr - v0) / (v1 - v0)
    act = (i - 1) + frac
    bad = (i == 0) | (amp <= 0) | ~np.isfinite(frac)
    act = np.where(bad, np.nan, act) - pre
    # APD80: last <=20% frame before peak, first <=20% frame after peak
    thr20 = base + 0.2 * amp
    peak = W.argmax(0)
    below = W <= thr20
    idx = np.arange(T)[:, None, None]
    before = np.where(below & (idx < peak), idx, -1).max(0)
    after = np.where(below & (idx > peak), idx, T + 10).min(0)
    apd = (after - before).astype(np.float32)
    apd[(before < 0) | (after > T) | (amp <= 0)] = np.nan
    return act.astype(np.float32), apd, amp.astype(np.float32)


def fill_nan(img, mask):
    """Fill NaNs inside mask by nearest finite in-mask value."""
    out = img.copy()
    src = np.isfinite(img) & mask
    if src.all() or not src.any():
        return out
    _, (iy, ix) = ndi.distance_transform_edt(~src, return_indices=True)
    fill = ~src & mask
    out[fill] = img[iy[fill], ix[fill]]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sigma_t', type=float, default=3.0)
    ap.add_argument('--sigma_xy', type=float, default=1.0)
    ap.add_argument('--corr_thr', type=float, default=0.7)
    ap.add_argument('--out', default='/workspace/submission')
    ap.add_argument('--min_corr', type=float, default=0.3, help='in-mask pixels below this corr are filled')
    ap.add_argument('--max_sd_act', type=float, default=10.0, help='ms; beat-to-beat SD above -> filled')
    ap.add_argument('--max_sd_apd', type=float, default=45.0, help='ms; beat-to-beat SD above -> filled')
    ap.add_argument('--save_beats', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    f = load_stream()
    print(f'loaded {f.shape} in {time.time()-t0:.1f}s')
    mask, corr = tissue_mask(f, a.corr_thr)
    print(f'mask pixels {mask.sum()}')
    field = f[:, mask].mean(1)
    onsets = detect_onsets(field)
    usable = onsets[onsets + 300 <= f.shape[0]]
    print(f'onsets {len(onsets)} usable {len(usable)}: {usable.tolist()}')
    if a.sigma_t > 0 or a.sigma_xy > 0:
        f = ndi.gaussian_filter(f, sigma=(a.sigma_t, a.sigma_xy, a.sigma_xy), mode='nearest', truncate=4.0)
        print(f'smoothed in {time.time()-t0:.1f}s')
    acts, apds, amps = [], [], []
    for o in usable:
        act, apd, amp = beat_maps(f[o - 60:o + 300])
        acts.append(act); apds.append(apd); amps.append(amp)
    acts = np.stack(acts); apds = np.stack(apds); amps = np.stack(amps)
    act_ms = np.nanmean(acts, 0) * DT_MS
    apd_ms = np.nanmean(apds, 0) * DT_MS
    nan_act = (~np.isfinite(act_ms) & mask).sum(); nan_apd = (~np.isfinite(apd_ms) & mask).sum()
    print(f'in-mask NaN before fill: act {nan_act}, apd {nan_apd}; '
          f'beats missing (apd) per in-mask pixel: mean {np.isnan(apds[:, mask]).sum(0).mean():.3f}')
    # reliability: in-mask pixels whose time course is not tissue-like (corr < 0.3, e.g. a motion
    # edge or a dilated border pixel) or whose beat-to-beat scatter is far outside the in-mask
    # distribution are filled from the nearest reliable pixel instead of reporting garbage.
    sd_act = np.nanstd(acts, 0) * DT_MS; sd_apd = np.nanstd(apds, 0) * DT_MS
    unreliable = mask & ((corr < a.min_corr) | (sd_act > a.max_sd_act) | (sd_apd > a.max_sd_apd))
    print(f'unreliable in-mask pixels filled from neighbours: {unreliable.sum()} '
          f'(corr<{a.min_corr}: {(mask & (corr < a.min_corr)).sum()}, sd_act>{a.max_sd_act}: {(mask & (sd_act > a.max_sd_act)).sum()}, '
          f'sd_apd>{a.max_sd_apd}: {(mask & (sd_apd > a.max_sd_apd)).sum()})')
    act_ms[unreliable] = np.nan; apd_ms[unreliable] = np.nan
    act_ms = fill_nan(act_ms, mask); apd_ms = fill_nan(apd_ms, mask)
    act_ms[~mask] = np.nan; apd_ms[~mask] = np.nan
    np.save(os.path.join(a.out, 'mask.npy'), mask.astype(bool))
    np.save(os.path.join(a.out, 'activation_ms.npy'), act_ms.astype(np.float32))
    np.save(os.path.join(a.out, 'apd80_ms.npy'), apd_ms.astype(np.float32))
    if a.save_beats:
        np.savez_compressed(os.path.join(a.out, 'per_beat.npz'), act_frames=acts, apd_frames=apds,
                            amp=amps, onsets=usable, corr=corr, field=field)
    v = act_ms[mask]; w = apd_ms[mask]
    print(f'activation ms: range {np.nanmin(v):.1f}..{np.nanmax(v):.1f}, sd {np.nanstd(v):.2f}')
    print(f'APD80 ms: median {np.nanmedian(w):.1f}, sd {np.nanstd(w):.2f}, range {np.nanmin(w):.1f}..{np.nanmax(w):.1f}')
    print(f'done in {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
