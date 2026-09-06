"""Spiral-tip trajectory descriptors and pattern classification.

Classes: C (circular core, rigid rotation), FI (flower, petals inward), FO (flower, petals outward),
L (linear core), D (net drift / boundary-dominated), H (hypermeander), X (no usable trajectory).

Input: uniformly sampled tip trace (t in ms, x, y in cm; NaN where the tip was not found).
Two-frequency picture: z(t) = c(t) + zeta(t); zeta = fast loop (spiral rotation, period T1, sense s1),
c = centre path (precession/drift, period T2, sense s2). Petals point inward when s1 == s2, outward when
s1 != s2; the same conclusion is reached geometrically from where the slow points of the loops sit.
"""
from __future__ import annotations
import numpy as np

CLASSES = ["C", "FI", "FO", "L", "D", "H", "X"]


def _fill_gaps(t, z, max_gap_ms=80.0):
    ok = ~np.isnan(z.real)
    if ok.sum() < 10:
        return z, 0.0, np.ones(len(t), bool)
    zi = np.interp(t, t[ok], z.real[ok]) + 1j * np.interp(t, t[ok], z.imag[ok])
    bad = np.zeros(len(t), bool)
    idx = np.nonzero(~ok)[0]
    if idx.size:
        splits = np.nonzero(np.diff(idx) > 1)[0] + 1
        step = t[1] - t[0]
        for run in np.split(idx, splits):
            if (t[run[-1]] - t[run[0]] + step) > max_gap_ms:
                bad[run] = True
    return zi, float(np.mean(~bad)), bad


def _longest_valid(t, z, bad):
    if not bad.any():
        return t, z
    idx = np.nonzero(~bad)[0]
    splits = np.nonzero(np.diff(idx) > 1)[0] + 1
    best = max(np.split(idx, splits), key=len)
    return t[best], z[best]


def _winding_rate(t, z):
    """Net revolutions per second of the complex signal z about 0 (unwrapped angle)."""
    ang = np.unwrap(np.angle(z))
    return (ang[-1] - ang[0]) / (2 * np.pi) / ((t[-1] - t[0]) / 1000.0)


def _spectrum_peak(t, z, pmin, pmax):
    dt = t[1] - t[0]
    zz = np.nan_to_num(z - np.nanmean(z)); n = len(zz)
    Z = np.fft.fft(zz * np.hanning(n)); f = np.fft.fftfreq(n, d=dt); P = np.abs(Z) ** 2
    band = (np.abs(f) >= 1.0 / pmax) & (np.abs(f) <= 1.0 / pmin)
    if not band.any():
        return np.nan, np.nan, 0.0, np.nan
    k = np.argmax(np.where(band, P, -1)); fk = f[k]
    mband = (np.sign(f) == -np.sign(fk)) & (np.abs(np.abs(f) - abs(fk)) <= 0.25 * abs(fk))
    mirror = float(P[mband].max() / P[k]) if (P[k] > 0 and mband.any()) else np.nan
    sel = (np.sign(f) == np.sign(fk)) & (np.abs(np.abs(f) - abs(fk)) <= 0.15 * abs(fk))
    tot = P[np.abs(f) > 0].sum()
    return 1.0 / abs(fk), float(fk), float(P[sel].sum() / tot) if tot > 0 else 0.0, mirror


def _boxcar(z, w):
    w = max(1, int(w)); k = np.ones(w) / w
    return np.convolve(z.real, k, mode="same") + 1j * np.convolve(z.imag, k, mode="same")


def describe(t, x, y, window_ms=6000.0, min_window_ms=3000.0):
    t = np.asarray(t, float); x = np.asarray(x, float); y = np.asarray(y, float)
    out = dict(cls="X", reason="")
    if len(t) < 200:
        out["reason"] = "too_few_samples"; return out
    order = np.argsort(t); t = t[order]; x = x[order]; y = y[order]
    keep = np.concatenate([[True], np.diff(t) > 0]); t = t[keep]; x = x[keep]; y = y[keep]
    dt_in = float(np.median(np.diff(t)))
    if abs(dt_in - 1.0) > 0.05:      # resample to 1 ms (NaN runs preserved via nearest-sample lookup)
        tt = np.arange(t[0], t[-1] + 1e-9, 1.0)
        idx = np.clip(np.searchsorted(t, tt), 0, len(t) - 1)
        near = np.abs(t[idx] - tt) <= max(dt_in, 1.0)
        xx = np.where(near, x[idx], np.nan); yy = np.where(near, y[idx], np.nan)
        ok = ~np.isnan(x)
        if ok.sum() > 2:
            xi = np.interp(tt, t[ok], x[ok]); yi = np.interp(tt, t[ok], y[ok])
            xx = np.where(np.isnan(xx), np.nan, xi); yy = np.where(np.isnan(yy), np.nan, yi)
        t, x, y = tt, xx, yy
    dt = 1.0
    m = t > t[-1] - window_ms
    t = t[m]; z = x[m] + 1j * y[m]
    z, valid, bad = _fill_gaps(t, z)
    out["valid_frac"] = valid
    if valid < 0.7:
        out["reason"] = "tip_lost"; return out
    t, z = _longest_valid(t, z, bad)
    span = t[-1] - t[0]
    out["span_ms"] = float(span)
    if span < min_window_ms:
        out["reason"] = "trajectory_too_short"; return out
    # ---- fast loop: heading winding of the (lightly smoothed) velocity
    zs = _boxcar(z, max(1, int(round(3.0 / dt))))
    v = np.gradient(zs, dt)
    turn_rate = _winding_rate(t[5:-5], v[5:-5])          # turns per second, signed
    if abs(turn_rate) < 0.5:
        out["reason"] = "no_rotation"; return out
    T1 = 1000.0 / abs(turn_rate); s1 = int(np.sign(turn_rate))
    Tspec, fspec, conc1, mirror = _spectrum_peak(t, z, pmin=0.5 * T1, pmax=2.0 * T1)
    out.update(T1=float(T1), s1=s1, T1_spectral=Tspec, mirror_ratio=mirror)
    w = int(round(T1 / dt))
    if w >= len(z) // 3:
        out["reason"] = "window_too_short_for_period"; return out
    c = _boxcar(z, w)
    edge = w // 2 + 1
    zc = z[edge:-edge]; cc = c[edge:-edge]; tc = t[edge:-edge]
    zeta = zc - cc
    r1 = float(np.median(np.abs(zeta)))
    # linearity of the loop motion: eigenvalue ratio of zeta's covariance over one-period windows
    ratios = []
    for s in range(0, len(zeta) - w, max(1, w // 2)):
        seg = zeta[s: s + w]
        ev = np.linalg.eigvalsh(np.cov(np.vstack([seg.real, seg.imag])))
        if ev[1] > 1e-12:
            ratios.append(ev[0] / ev[1])
    lin = float(1.0 - np.median(ratios)) if ratios else np.nan
    out.update(r1=r1, linearity=lin)
    # ---- centre path
    cen = cc.mean(); rel = cc - cen
    A_c = float(np.sqrt(np.mean(np.abs(rel) ** 2)))
    R2 = float(np.mean(np.abs(rel))); cv_R2 = float(np.std(np.abs(rel)) / R2) if R2 > 0 else np.nan
    extent = float(max(np.ptp(cc.real), np.ptp(cc.imag)))
    path_len = float(np.sum(np.abs(np.diff(cc)))); net = float(abs(cc[-1] - cc[0]))
    straight = net / path_len if path_len > 0 else 0.0
    ring_rate = _winding_rate(tc, rel) if R2 > 1e-3 else 0.0
    revs = abs(ring_rate) * (tc[-1] - tc[0]) / 1000.0
    T2 = 1000.0 / abs(ring_rate) if abs(ring_rate) > 1e-6 else np.inf
    s2 = int(np.sign(ring_rate)) if abs(ring_rate) > 1e-6 else 0
    T2s, f2s, conc2, _ = _spectrum_peak(tc, cc, pmin=1.2 * T1, pmax=(tc[-1] - tc[0]) / 1.2)
    # periodicity of the centre path: normalised autocorrelation at lag T2 (1 = the path repeats exactly every T2)
    lag = int(round(T2 / dt)) if np.isfinite(T2) else 0
    if 10 <= lag <= len(rel) - 50:
        a = rel[:-lag]; b = rel[lag:]
        ac = float(np.real(np.vdot(a, b)) / np.sqrt(np.vdot(a, a).real * np.vdot(b, b).real + 1e-300))
    else:
        ac = np.nan
    out.update(A_c=A_c, R2=R2, cv_R2=cv_R2, extent=extent, c_net=net, straightness=float(straight),
               T2=float(T2), s2=s2, ring_revs=float(revs), T2_spectral=T2s, c_concentration=conc2, c_autocorr=ac)
    # ---- geometric petal orientation: slow points of the loops vs centre-path radius
    speed = np.abs(np.gradient(zc, dt))
    mins = np.nonzero((speed[1:-1] <= speed[:-2]) & (speed[1:-1] < speed[2:]))[0] + 1
    keep = []; last = -10 ** 9
    for i in mins:
        if (i - last) * dt >= 0.5 * T1:
            keep.append(i); last = i
    keep = np.array(keep, int)
    if len(keep) >= 3 and R2 > 1e-3:
        out["petal_offset"] = float((np.median(np.abs(zc[keep] - cen)) - R2) / max(r1, 1e-6))
    else:
        out["petal_offset"] = np.nan
    # ---- classification
    if (not np.isnan(mirror) and mirror > 0.4 and not np.isnan(lin) and lin > 0.6):
        cls = "L"
    elif A_c < 0.2 * max(r1, 1e-6) and extent < 0.8 * max(r1, 1e-6):   # stated rule: wander < 20% of the loop radius; the extent bound only
        # excludes a slow straight creep hiding behind a small RMS (extent of a uniform drift = 2*sqrt(3)*RMS ~ 0.7 r1 at the limit)
        cls = "C"
    elif R2 > 5.0 or (revs < 0.8 and net > max(3.0, 4 * r1)):
        cls = "D"
    elif revs >= 1.2 and not np.isnan(cv_R2) and cv_R2 < 0.5 and not np.isnan(ac) and ac >= 0.6:
        same = (s1 * s2) > 0
        cls = "FI" if same else "FO"
        # orientation follows the kinematic definition (same sense -> loops inside -> inward petals);
        # petal_offset is kept for information only
        ratio = T2 / T1
        out["petal_ratio"] = float(ratio)
        out["petals"] = int(round(ratio - 1)) if same else int(round(ratio + 1))
    else:
        cls = "H"
    out["cls"] = cls
    return out


def summarize(d):
    keys = ["cls", "T1", "s1", "r1", "linearity", "mirror_ratio", "A_c", "R2", "cv_R2", "extent", "straightness", "T2", "s2",
            "ring_revs", "c_concentration", "c_autocorr", "petal_ratio", "petals", "valid_frac", "reason"]
    parts = []
    for k in keys:
        if k in d:
            v = d[k]
            parts.append(f"{k}={v:.3g}" if isinstance(v, float) else f"{k}={v}")
    return " ".join(parts)


if __name__ == "__main__":
    import sys
    for path in sys.argv[1:]:
        d = np.load(path)
        desc = describe(d["t"], d["x"], d["y"])
        print(f"{path.split('/')[-1]:34s} {summarize(desc)}")


# ----------------------------------------------------------------------------- shape statistics (human-calibrated, v0.2)
def _centre_path(t, x, y, window_ms=6000.0):
    """(t, z, c, r1, T1) on the analysis window with NaN gaps interpolated; c = running mean over one loop period."""
    t = np.asarray(t, float); x = np.asarray(x, float); y = np.asarray(y, float)
    d = describe(t, x, y, window_ms=window_ms)
    if "T1" not in d:
        return None
    m = t > t[-1] - window_ms; t = t[m]; z = x[m] + 1j * y[m]; ok = ~np.isnan(z)
    if ok.sum() < 100:
        return None
    z = np.interp(t, t[ok], z.real[ok]) + 1j * np.interp(t, t[ok], z.imag[ok])
    dt = float(np.median(np.diff(t))) or 1.0
    w = max(1, int(round(d["T1"] / dt))); c = _boxcar(z, w); e = w // 2 + 1
    return t[e:-e], z[e:-e], c[e:-e], max(d["r1"], 1e-3), d["T1"]


def drift_leg_curvature(t, x, y, corner_deg=35.0, min_leg_r1=8.0):
    """Drift patterns: the centre path (loops removed) resampled by arc length (0.25 loop radii), smoothed over 2 radii;
    corners = stretches where the net heading change within 3 radii reaches `corner_deg`; legs = stretches between corners
    at least `min_leg_r1` radii long. Returns dict(max_sagitta = max over legs of (max chord deviation / leg length),
    max_net_turn_deg, legs = [(net_turn_deg, sagitta, length_r1), ...]). The reviewer requires straight legs: reference
    0.017, accepted pipelines <= 0.029, rejected (curved or curling runs) >= 0.040."""
    cp = _centre_path(t, x, y)
    if cp is None:
        return dict(max_sagitta=np.nan, max_net_turn_deg=np.nan, legs=[])
    _, _, c, r1, _ = cp
    s = np.concatenate([[0.0], np.cumsum(np.abs(np.diff(c)))]); L = s[-1]
    if L < 10 * r1:
        return dict(max_sagitta=np.nan, max_net_turn_deg=np.nan, legs=[])
    step = 0.25 * r1; su = np.arange(0, L, step); cu = np.interp(su, s, c.real) + 1j * np.interp(su, s, c.imag)
    k = 8; cu = _boxcar(cu, k)[k:-k]
    th = np.unwrap(np.angle(np.diff(cu))); dth = np.diff(th)
    win = 12; net = np.convolve(dth, np.ones(win), mode="same"); corner = np.abs(np.degrees(net)) >= corner_deg
    corner = np.convolve(corner.astype(int), np.ones(win), mode="same") > 0
    legs = []; i = 0; n = len(dth)
    while i < n:
        if corner[i]:
            i += 1; continue
        j = i
        while j < n and not corner[j]:
            j += 1
        if (j - i) * step >= min_leg_r1 * r1:
            seg = cu[i:j + 1]; chord = seg[-1] - seg[0]
            if abs(chord) > 1e-9:
                u = chord / abs(chord); dev = np.abs(np.imag((seg - seg[0]) * np.conj(u)))
                nett = abs(np.degrees(th[min(j, len(th) - 1)] - th[i]))
                legs.append((float(nett), float(dev.max() / abs(chord)), float((j - i) * step / r1)))
        i = j
    if not legs:
        return dict(max_sagitta=np.nan, max_net_turn_deg=np.nan, legs=[])
    return dict(max_sagitta=max(l[1] for l in legs), max_net_turn_deg=max(l[0] for l in legs), legs=legs)


def linear_core_cusp_angle(t, x, y):
    """Linear cores: at the ends of the straight runs (local maxima of the distance from the running centre, at least
    0.8 loop radii out) the reversal angle between the chords 0.25 radii before and after the end point; 180 = sharp cusp.
    Returns dict(median_angle_deg, n_ends). Reference and accepted pipelines 171-173 deg; rounded, petal-like ends 113-129."""
    cp = _centre_path(t, x, y)
    if cp is None:
        return dict(median_angle_deg=np.nan, n_ends=0)
    _, zc, cc, r1, _ = cp
    r = np.abs(zc - cc); zs = _boxcar(zc, 3); Lc = 0.25 * r1; ang = []
    for i in range(30, len(r) - 30):
        if r[i] < 0.8 * r1 or r[i] < r[i - 30:i + 31].max():
            continue
        def chord(direction):
            acc = 0.0; j = i
            while 0 < j < len(zs) - 1 and acc < Lc:
                j += direction; acc += abs(zs[j] - zs[j - direction])
            return zs[j] - zs[i]
        vin = -chord(-1); vout = chord(+1)
        if abs(vin) < 1e-9 or abs(vout) < 1e-9:
            continue
        ang.append(np.degrees(np.arccos(np.clip(np.real(vin * np.conj(vout)) / (abs(vin) * abs(vout)), -1, 1))))
    return dict(median_angle_deg=(float(np.median(ang)) if ang else np.nan), n_ends=len(ang))
