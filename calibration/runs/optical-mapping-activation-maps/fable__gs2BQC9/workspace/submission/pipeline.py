"""Activation / APD80 maps from raw optical mapping recording (frozen definitions).

Usage: python3 pipeline.py [--sig_t 2] [--sig_s 1] [--out /workspace/submission]
"""
import argparse, os, sys
import numpy as np
from scipy import ndimage as ndi
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import load_raw, DT_MS

PRE, POST, REFRACT, NBASE = 60, 300, 250, 50

def detect_onsets(trace, refract=REFRACT):
    lo, hi = np.percentile(trace, [5, 95])
    n = (trace - lo) / (hi - lo)
    on, last = [], -10**9
    for i in range(1, len(n)):
        if n[i-1] < 0.5 <= n[i] and i - last > refract:
            on.append(i); last = i
    return np.array(on)

def tissue_mask(sig, onsets):
    """Beat-averaged amplitude SNR per pixel -> threshold -> morphological clean-up."""
    T = sig.shape[0]
    use = [o for o in onsets if o - PRE >= 0 and o + POST <= T]
    avg = np.zeros((PRE + POST,) + sig.shape[1:], np.float32)
    for o in use:
        avg += sig[o-PRE:o+POST]
    avg /= len(use)
    base = np.median(avg[:NBASE], axis=0)
    amp = avg.max(0) - base
    noise = avg[:NBASE].std(0) + 1e-6
    snr = amp / noise
    return amp, snr, avg

def clean_mask(m, min_size=200):
    m = ndi.binary_opening(m, iterations=1)
    lab, n = ndi.label(m)
    if n > 1:
        sizes = ndi.sum(m, lab, range(1, n+1))
        keep = np.isin(lab, 1 + np.flatnonzero(sizes >= max(min_size, 0.02*sizes.max())))
        m = keep
    m = ndi.binary_fill_holes(m)
    m = ndi.binary_closing(m, iterations=1)
    m = ndi.binary_fill_holes(m)
    return m

def beat_maps(win):
    """win: (PRE+POST, H, W) float32, depolarisation upward. Returns (act_frames, apd80_frames)."""
    L, H, W = win.shape
    base = np.median(win[:NBASE], axis=0)
    pk_idx = win.argmax(0)
    amp = win.max(0) - base
    ok = amp > 0
    lvl50 = base + 0.5 * amp
    lvl20 = base + 0.2 * amp
    t = np.arange(L)[:, None, None]
    # ---- activation: first upward crossing of 50% level (interpolated) ----
    above = win >= lvl50
    # first frame where above is True
    first = above.argmax(0)                       # (H,W)
    has = above.any(0) & (first > 0)
    i1 = np.clip(first, 1, L-1); i0 = i1 - 1
    v0 = np.take_along_axis(win, i0[None], 0)[0]
    v1 = np.take_along_axis(win, i1[None], 0)[0]
    act = i0 + (lvl50 - v0) / np.where(v1 != v0, v1 - v0, np.nan)
    act = np.where(has & ok, act, np.nan)
    # ---- APD80: last frame <= 20% before peak to first frame <= 20% after peak ----
    below = win <= lvl20
    before = below & (t < pk_idx[None])
    # last True before peak: use reversed argmax
    rev = before[::-1].argmax(0)
    last_before = (L - 1) - rev
    has_b = before.any(0)
    after = below & (t > pk_idx[None])
    first_after = after.argmax(0)
    has_a = after.any(0)
    apd = (first_after - last_before).astype(np.float32)
    apd = np.where(has_b & has_a & ok, apd, np.nan)
    return act.astype(np.float32), apd

def run(sig_t, sig_s, out, mask_thr=None, save=True, sig=None):
    if sig is None:
        raw = load_raw()
        sig = -(raw.astype(np.float32))          # depolarisation is downward in the file -> invert
        del raw
    T = sig.shape[0]
    # ---- provisional mask from unsmoothed data, onsets from field mean ----
    bright = sig.mean(0)  # (negative intensity) - use amplitude instead
    on0 = detect_onsets(sig[:, 32:96, 32:96].reshape(T, -1).mean(1))
    amp, snr, _ = tissue_mask(sig, on0)
    if mask_thr is None:
        # Otsu-like threshold on log amplitude
        la = np.log10(np.clip(amp, 1e-3, None)).ravel()
        hist, edges = np.histogram(la, 256)
        c = edges[:-1] + np.diff(edges)/2
        w0 = np.cumsum(hist); w1 = w0[-1] - w0
        m0 = np.cumsum(hist*c)/np.maximum(w0,1); m1 = (np.sum(hist*c)-np.cumsum(hist*c))/np.maximum(w1,1)
        v = w0*w1*(m0-m1)**2
        thr = 10**c[np.argmax(v)]
    else:
        thr = mask_thr
    mask = clean_mask(amp > thr)
    # ---- onsets on the field mean over tissue pixels ----
    fm = sig[:, mask].mean(1)
    onsets = detect_onsets(fm)
    usable = [o for o in onsets if o + POST <= T and o - PRE >= 0]
    # ---- denoise: Gaussian in time and (normalised, within-mask) in space ----
    if sig_t > 0:
        sm = ndi.gaussian_filter1d(sig, sig_t, axis=0, mode='nearest')
    else:
        sm = sig.copy()
    if sig_s > 0:
        wgt = ndi.gaussian_filter(mask.astype(np.float32), sig_s)
        sm *= mask[None].astype(np.float32)
        for i in range(sm.shape[0]):
            sm[i] = ndi.gaussian_filter(sm[i], sig_s) / np.maximum(wgt, 1e-3)
    acts, apds = [], []
    for o in usable:
        a, d = beat_maps(sm[o-PRE:o+POST])
        acts.append(a); apds.append(d)
    acts = np.stack(acts); apds = np.stack(apds)
    act_ms = np.nanmean(acts, 0) * DT_MS
    apd_ms = np.nanmean(apds, 0) * DT_MS
    act_ms[~mask] = np.nan; apd_ms[~mask] = np.nan
    res = dict(mask=mask, act=act_ms.astype(np.float32), apd=apd_ms.astype(np.float32),
               acts=acts*DT_MS, apds=apds*DT_MS, onsets=onsets, usable=usable, amp=amp, thr=thr)
    if save:
        os.makedirs(out, exist_ok=True)
        np.save(os.path.join(out, 'mask.npy'), mask.astype(bool))
        np.save(os.path.join(out, 'activation_ms.npy'), res['act'])
        np.save(os.path.join(out, 'apd80_ms.npy'), res['apd'])
    return res, sig

def split_half(res):
    """Odd/even beat split-half RMSE /2 -> expected noise of the 18-beat map."""
    m = res['mask']
    out = {}
    for k in ('acts', 'apds'):
        a = np.nanmean(res[k][0::2], 0); b = np.nanmean(res[k][1::2], 0)
        d = (a - b)[m]
        if k == 'acts':
            d = d - np.nanmedian(d)
        out[k] = np.sqrt(np.nanmean(d**2)) / 2
    return out

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--sig_t', type=float, default=2.0)
    ap.add_argument('--sig_s', type=float, default=1.0)
    ap.add_argument('--out', default='/workspace/submission')
    a = ap.parse_args()
    res, _ = run(a.sig_t, a.sig_s, a.out)
    m = res['mask']
    print('mask frac %.3f  thr %.1f  onsets %d usable %d' % (m.mean(), res['thr'], len(res['onsets']), len(res['usable'])))
    print('act finite in mask %.3f  apd finite %.3f' % (np.isfinite(res['act'][m]).mean(), np.isfinite(res['apd'][m]).mean()))
    print('act range (ms) p1..p99', np.nanpercentile(res['act'][m], [1, 50, 99]))
    print('apd80 (ms) p1..p99', np.nanpercentile(res['apd'][m], [1, 50, 99]))
    print('split-half noise (ms):', split_half(res))
