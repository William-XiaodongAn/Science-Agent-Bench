#!/usr/bin/env python3
"""Frozen ground-truth builder for tier_2_task_1.

Reads the expert-processed .mat and emits three per-pixel maps averaged over the
usable beats. The .mat is already UPRIGHT -- depolarisation is an upward
deflection. Verified from the waveform asymmetry: the field-mean trace rises
10-90% in 57 ms and falls 90-10% in 202 ms, and a cardiac action potential has a
fast upstroke and slow repolarisation. Do not negate it.

  activation_ms.npy  (128,128) float32  activation time, 50% upstroke, NaN off-tissue
  apd80_ms.npy       (128,128) float32  APD80
  cv_cm_s.npy        (128,128) float32  conduction velocity from the activation gradient
  mask.npy           (128,128) bool     tissue mask (== live pixels of the .mat)
  beats.json                            beat onsets + provenance

Beat rule (frozen): onsets detected on the field-mean trace by 50% downward
crossing with a 250-frame refractory; a beat is usable only if the recording
holds APD_WINDOW frames after its onset. This drops the truncated final beat.
"""
import json, numpy as np, scipy.io as sio
from pathlib import Path

MAT = "2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.mat"
OUT = Path("gt")
FPS = 529.09          # from the .dat per-frame microsecond timestamps
DT = 1000.0 / FPS     # ms per frame
PRE = 60              # frames of baseline kept before each onset
APD_WINDOW = 300      # frames after onset required for a beat to be "complete"
REFRACTORY = 250
PIXEL_MM = 0.15       # placeholder: physical pixel pitch, see note in README

def field_onsets(sig):
    s = (sig - np.percentile(sig, 5)) / (np.percentile(sig, 95) - np.percentile(sig, 5))
    idx = np.where(np.diff((s > 0.5).astype(int)) == 1)[0]   # upright: upward crossing
    out = []
    for i in idx:
        if out and i - out[-1] < REFRACTORY:
            continue
        y0, y1 = s[i], s[i + 1]
        out.append(i + (0.5 - y0) / (y1 - y0) if y1 != y0 else float(i))
    return np.array(out)

def main():
    OUT.mkdir(exist_ok=True)
    d = sio.loadmat(MAT)["data"]
    T, H, W = d.shape
    mask = d.std(axis=0) > 0
    trace = d[:, mask].mean(axis=1)
    onsets = field_onsets(trace)
    usable = [o for o in onsets if int(o) + APD_WINDOW <= T and int(o) - PRE >= 0]
    dropped = [float(o) for o in onsets if o not in usable]

    acts, apds = [], []
    for o in usable:
        b = int(round(o))
        v = d[b - PRE: b - PRE + APD_WINDOW + PRE][:, mask].astype(np.float64)
        base = np.percentile(v[:PRE - 10], 50, axis=0)
        peak = v.max(axis=0)
        amp = peak - base

        # activation = 50% of upstroke amplitude, linearly interpolated between
        # frames. argmax(dV/dt) is 4x noisier here: the upstroke spans ~66 frames,
        # so the derivative peak is a flat, noise-dominated plateau.
        half = base + 0.5 * amp
        at = np.full(v.shape[1], np.nan)
        for j in range(v.shape[1]):
            w = np.where(v[:, j] >= half[j])[0]
            if not len(w) or w[0] == 0:
                continue
            i = w[0]
            y0, y1 = v[i - 1, j], v[i, j]
            at[j] = ((i - 1) + (half[j] - y0) / (y1 - y0)) * DT
        acts.append(at)
        lvl = base + 0.2 * amp                     # APD80 threshold
        a = np.full(v.shape[1], np.nan)
        pk = np.argmax(v, axis=0)
        for j in range(v.shape[1]):
            p = pk[j]
            up = np.where(v[:p + 1, j] <= lvl[j])[0]
            dn = np.where(v[p:, j] <= lvl[j])[0]
            if len(up) and len(dn):
                a[j] = (dn[0] + p - up[-1]) * DT
        apds.append(a)

    A = np.array(acts); D = np.array(apds)
    act_flat = np.nanmean(A, axis=0)
    apd_flat = np.nanmean(D, axis=0)

    act = np.full((H, W), np.nan, np.float32); act[mask] = act_flat
    apd = np.full((H, W), np.nan, np.float32); apd[mask] = apd_flat

    # conduction velocity from the activation-time gradient: |CV| = 1/|grad T|
    gy, gx = np.gradient(np.where(mask, act, np.nan))
    gmag = np.sqrt(gy ** 2 + gx ** 2)              # ms per pixel
    with np.errstate(divide="ignore", invalid="ignore"):
        cv = (PIXEL_MM / gmag) * 100.0             # mm/ms -> cm/s
    cv = np.where(mask & np.isfinite(cv), cv, np.nan).astype(np.float32)

    np.save(OUT / "activation_ms.npy", act)
    np.save(OUT / "apd80_ms.npy", apd)
    np.save(OUT / "cv_cm_s.npy", cv)
    np.save(OUT / "mask.npy", mask)

    # beat-to-beat repeatability = the noise floor each metric can be scored against
    meta = dict(
        fps=FPS, dt_ms=DT, n_frames=int(T), n_pixels=int(mask.sum()),
        onsets_all=[round(float(o), 2) for o in onsets],
        onsets_used=[round(float(o), 2) for o in usable],
        onsets_dropped=[round(o, 2) for o in dropped],
        apd_window_frames=APD_WINDOW, pre_frames=PRE, pixel_mm=PIXEL_MM,
        noise_floor_activation_ms=float(np.nanmedian(np.nanstd(A, axis=0))),
        noise_floor_apd80_ms=float(np.nanmedian(np.nanstd(D, axis=0))),
        spatial_sd_activation_ms=float(np.nanstd(act_flat)),
        spatial_sd_apd80_ms=float(np.nanstd(apd_flat)),
    )
    (OUT / "beats.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))

if __name__ == "__main__":
    main()
