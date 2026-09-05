#!/usr/bin/env python3
"""Activation / APD80 maps from the raw optical-mapping stream (frozen definitions, see methods.md).

Usage: python3 pipeline.py [--sigma_t 3] [--sigma_s 1 2 4] [--out /workspace/submission] [--diag]

Steps
 1. read 16-bit LE stream (1024-byte header, 128x128 + 4-word footer per frame), transpose each frame,
    drop under-exposed frame 0, invert sign (fast deflection is downward in this file).
 2. detect beat onsets on the field-mean trace (5-95 percentile normalised, 50% upward crossing,
    250-frame refractory).
 3. Gaussian denoising in time (sigma_t frames) and space (sigma_s px); several spatial levels.
 4. per beat, window [onset-60, onset+300): baseline = median of first 50 frames, amplitude = max - baseline,
    activation = first 50% crossing (linear interpolation), APD80 = frames from the last frame <= 20% before
    the peak to the first frame <= 20% after the peak.
 5. per pixel, mean over the 18 beats; the spatial level is the finest whose beat-to-beat scatter is at the
    level of clean tissue (edges of the field of view are dim and need more spatial averaging).
 6. tissue mask from the beat-averaged amplitude (background carries a scattered-light copy of the AP at
    ~12 counts; tissue is > 2.5x that), largest component, holes filled, 1 px dilation.
"""
import argparse, os, time, json
import numpy as np
from scipy import ndimage as ndi

FN = '/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat'
NX = 128; FOOT = 4; HEADER = 1024
FPS = 529.09; DT = 1000.0 / FPS          # 1.890 ms/frame
PRE, POST, NBASE = 60, 300, 50
REFRACT = 250


def load_frames():
    raw = np.fromfile(FN, dtype='<u2', offset=HEADER)
    per = NX * NX + FOOT
    nf = raw.size // per
    raw = raw[:nf * per].reshape(nf, per)[:, :NX * NX].reshape(nf, NX, NX)
    fr = raw.transpose(0, 2, 1)[1:]            # transpose to analysis convention, drop under-exposed frame 0
    # sign: the fast deflection (depolarisation) is downward in this file -> invert so depolarisation is up
    return -fr.astype(np.float32)


def detect_onsets(trace, nf):
    p5, p95 = np.percentile(trace, [5, 95])
    n = (trace - p5) / (p95 - p5)
    up = np.where((n[:-1] < 0.5) & (n[1:] >= 0.5))[0] + 1
    onsets = []
    for i in up:
        if not onsets or i - onsets[-1] > REFRACT:
            onsets.append(int(i))
    return [o for o in onsets if o - PRE >= 0 and o + POST <= nf]


def beat_maps(W):
    """W: (360, npix) window starting PRE frames before onset. Returns act (frames from window start), apd (frames), amp."""
    T, P = W.shape
    base = np.median(W[:NBASE], axis=0)
    peak_idx = W.argmax(0)
    amp = W.max(0) - base
    thr50 = base + 0.5 * amp
    thr20 = base + 0.2 * amp
    above = W >= thr50
    k = above.argmax(0)                       # first frame at/above 50%
    ok = above.any(0) & (k > 0)
    kk = np.clip(k, 1, T - 1)
    cols = np.arange(P)
    w0 = W[kk - 1, cols]; w1 = W[kk, cols]
    with np.errstate(invalid='ignore', divide='ignore'):
        act = (kk - 1) + (thr50 - w0) / np.where(w1 != w0, w1 - w0, np.nan)
    act = np.where(ok, act, np.nan)
    below = W <= thr20
    idx = np.arange(T)[:, None]
    before = np.where(below & (idx < peak_idx[None, :]), idx, -1).max(0)
    after = np.where(below & (idx > peak_idx[None, :]), idx, T + 10).min(0)
    apd = (after - before).astype(np.float64)
    apd[(before < 0) | (after > T)] = np.nan       # no 20% crossing inside the window -> beat unusable for APD
    return act, apd, amp


def all_beats(S, onsets):
    P = NX * NX
    acts, apds, amps = [], [], []
    for o in onsets:
        act, apd, amp = beat_maps(S[o - PRE:o + POST].reshape(PRE + POST, P))
        acts.append(act); apds.append(apd); amps.append(amp)
    return np.array(acts).reshape(-1, NX, NX), np.array(apds).reshape(-1, NX, NX), np.mean(amps, 0).reshape(NX, NX)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sigma_t', type=float, default=3.0)
    ap.add_argument('--sigma_s', type=float, nargs='+', default=[1.0, 2.0, 4.0])
    ap.add_argument('--sd_act', type=float, default=2.2, help='max beat-to-beat SD of activation (ms) to accept a level')
    ap.add_argument('--sd_apd', type=float, default=8.0, help='max beat-to-beat SD of APD80 (ms) to accept a level')
    ap.add_argument('--out', default='/workspace/submission')
    ap.add_argument('--amp_factor', type=float, default=2.5)
    ap.add_argument('--dilate', type=int, default=1)
    ap.add_argument('--diag', action='store_true')
    a = ap.parse_args()
    t0 = time.time()
    S0 = load_frames()                                    # (7619,128,128), depolarisation upward
    nf = S0.shape[0]
    mean_img = -S0.mean(0)                                # camera brightness (signal is inverted)
    print(f'loaded {S0.shape} in {time.time()-t0:.1f}s', flush=True)
    # provisional tissue mask from temporal std (background ~7-8 counts) for onset detection
    std_img = S0.std(0)
    prov = std_img > 3 * np.median(std_img[std_img < np.percentile(std_img, 30)])
    onsets = detect_onsets(S0[:, prov].mean(1), nf)
    print('onsets', len(onsets), onsets, flush=True)

    levels = []
    for ss in a.sigma_s:
        S = ndi.gaussian_filter(S0, sigma=(a.sigma_t, ss, ss), mode='nearest', truncate=3.0)
        acts, apds, amp_mean = all_beats(S, onsets)
        if ss == a.sigma_s[0]:
            # tissue mask from the finest level's beat-averaged amplitude
            bg = np.median(amp_mean[mean_img < np.percentile(mean_img, 20)])
            thr = a.amp_factor * bg
            m = amp_mean > thr
            m = ndi.binary_opening(m, iterations=1)
            lab, n = ndi.label(m)
            if n > 1:
                sizes = ndi.sum(m, lab, range(1, n + 1))
                m = lab == (1 + int(np.argmax(sizes)))
            m = ndi.binary_fill_holes(m)
            if a.dilate > 0:
                m = ndi.binary_dilation(m, iterations=a.dilate)
            print(f'mask: background amplitude {bg:.1f}, threshold {thr:.1f}, fraction {m.mean():.3f} ({m.sum()} px)', flush=True)
            # final onsets from the field mean over the tissue mask
            onsets2 = detect_onsets(S0[:, m].mean(1), nf)
            if onsets2 != onsets:
                print('onsets changed with final mask; recomputing', onsets2, flush=True)
                onsets = onsets2
                acts, apds, amp_mean = all_beats(S, onsets)
            amp_fine = amp_mean
        levels.append((ss, acts, apds))
        print(f'level sigma_s={ss}: done at {time.time()-t0:.1f}s', flush=True)
    del S, S0

    # per-pixel level selection: finest level whose beat-to-beat scatter is at clean-tissue level
    nb = len(onsets)
    act_ms_levels = [(acts - PRE) * DT for _, acts, _ in levels]     # relative to onset frame
    apd_ms_levels = [apds * DT for _, _, apds in levels]
    sd_act = np.array([np.nanstd(x, 0) for x in act_ms_levels])
    sd_apd = np.array([np.nanstd(x, 0) for x in apd_ms_levels])
    accept = (sd_act <= a.sd_act) & (sd_apd <= a.sd_apd) & np.isfinite(sd_act) & np.isfinite(sd_apd)
    accept[-1] = True                                           # coarsest level is the fallback
    level = accept.argmax(0)                                    # first accepted
    level = ndi.median_filter(level, size=3)                    # remove speckle in the level map
    level = np.maximum.reduce([level] + [ndi.grey_dilation(level, size=3)]) if len(levels) > 1 else level
    act_map = np.full((NX, NX), np.nan, np.float32); apd_map = np.full((NX, NX), np.nan, np.float32)
    act_beats_sel = np.full((nb, NX, NX), np.nan, np.float32); apd_beats_sel = np.full((nb, NX, NX), np.nan, np.float32)
    for li in range(len(levels)):
        sel = level == li
        act_beats_sel[:, sel] = act_ms_levels[li][:, sel]
        apd_beats_sel[:, sel] = apd_ms_levels[li][:, sel]
    act_map = np.nanmean(act_beats_sel, 0).astype(np.float32)
    apd_map = np.nanmean(apd_beats_sel, 0).astype(np.float32)
    act_map[~m] = np.nan; apd_map[~m] = np.nan
    os.makedirs(a.out, exist_ok=True)
    np.save(os.path.join(a.out, 'mask.npy'), m.astype(bool))
    np.save(os.path.join(a.out, 'activation_ms.npy'), act_map)
    np.save(os.path.join(a.out, 'apd80_ms.npy'), apd_map)

    # validation without a reference: split-half (odd vs even beats) noise of the final map, in-mask
    def split_half(b, region, center):
        ha = np.nanmean(b[0::2], 0); hb = np.nanmean(b[1::2], 0); d = (ha - hb)[region]; d = d[np.isfinite(d)]
        if center: d = d - np.median(d)
        return float(np.sqrt(np.mean(d ** 2)) / 2)
    yy, xx = np.mgrid[0:NX, 0:NX]
    core = m & (xx >= 30) & (xx <= 105) & (yy >= 15) & (yy <= 100)
    nb_apd = np.isfinite(apd_beats_sel).sum(0)[m]
    stats = dict(sigma_t=a.sigma_t, sigma_s=a.sigma_s, sd_act_thr=a.sd_act, sd_apd_thr=a.sd_apd,
                 n_beats=nb, onsets=onsets, mask_fraction=float(m.mean()), mask_pixels=int(m.sum()),
                 amp_threshold=float(thr),
                 level_fraction_in_mask=[float((level[m] == i).mean()) for i in range(len(levels))],
                 act_finite_frac=float(np.isfinite(act_map[m]).mean()), apd_finite_frac=float(np.isfinite(apd_map[m]).mean()),
                 apd_beats_per_pixel_median=float(np.median(nb_apd)), apd_beats_min=int(nb_apd.min()),
                 frac_pixels_all18_apd=float((nb_apd == nb).mean()),
                 act_range_ms_1_99=[float(np.nanpercentile(act_map[m], 1)), float(np.nanpercentile(act_map[m], 99))],
                 apd_median_ms=float(np.nanmedian(apd_map[m])),
                 apd_range_ms_1_99=[float(np.nanpercentile(apd_map[m], 1)), float(np.nanpercentile(apd_map[m], 99))],
                 split_half_act_noise_ms_mask=split_half(act_beats_sel, m, True),
                 split_half_apd_noise_ms_mask=split_half(apd_beats_sel, m, False),
                 split_half_act_noise_ms_core=split_half(act_beats_sel, core, True),
                 split_half_apd_noise_ms_core=split_half(apd_beats_sel, core, False),
                 split_half_act_noise_ms_finest_level_mask=split_half(act_ms_levels[0], m, True),
                 split_half_apd_noise_ms_finest_level_mask=split_half(apd_ms_levels[0], m, False),
                 beat_sd_act_median_ms=float(np.nanmedian(np.nanstd(act_beats_sel, 0)[m])),
                 beat_sd_apd_median_ms=float(np.nanmedian(np.nanstd(apd_beats_sel, 0)[m])),
                 elapsed_s=time.time() - t0)
    print(json.dumps(stats, indent=1))
    with open(os.path.join(a.out, 'run_stats.json'), 'w') as f:
        json.dump(stats, f, indent=1)
    if a.diag:
        np.save(os.path.join(a.out, 'diag_level.npy'), level.astype(np.int8))
        np.save(os.path.join(a.out, 'diag_amp.npy'), amp_fine.astype(np.float32))
        np.save(os.path.join(a.out, 'diag_act_beats.npy'), act_beats_sel)
        np.save(os.path.join(a.out, 'diag_apd_beats.npy'), apd_beats_sel)
        np.save(os.path.join(a.out, 'diag_act_beats_fine.npy'), act_ms_levels[0].astype(np.float32))
        np.save(os.path.join(a.out, 'diag_apd_beats_fine.npy'), apd_ms_levels[0].astype(np.float32))


if __name__ == '__main__':
    main()
