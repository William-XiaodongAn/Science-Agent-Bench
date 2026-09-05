"""Fenton-Karma 3-variable model on a 2D square, replicating the numerical scheme of the
2D-3V-Model WebGL tool (explicit Euler, 9-point Laplacian with gamma = 1/3, clamp-to-edge
boundaries), plus an automated cross-field (S1-S2) spiral initiation and the tool's
tip definition: intersection of the u = U_th isoline with the du/dt = 0 line.

Development copy (reference solver for the spiral-tip-pattern task).
"""
from __future__ import annotations
import argparse, json, os, time
import numpy as np
import numba as nb

PARAM_ORDER = ["tau_pv", "tau_v1", "tau_v2", "tau_pw", "tau_mw", "tau_d", "tau_0", "tau_r",
               "tau_si", "K", "V_sic", "V_c", "V_v", "C_si"]

SET01 = dict(tau_pv=3.33, tau_v1=19.6, tau_v2=1000.0, tau_pw=667.0, tau_mw=11.0, tau_d=0.42,
             tau_0=8.3, tau_r=50.0, tau_si=45.0, K=10.0, V_sic=0.85, V_c=0.13, V_v=0.055, C_si=1.0)
SET02 = dict(tau_pv=10.0, tau_v1=10.0, tau_v2=10.0, tau_pw=667.0, tau_mw=11.0, tau_d=0.25,
             tau_0=10.0, tau_r=190.0, tau_si=45.0, K=10.0, V_sic=0.85, V_c=0.13, V_v=0.055, C_si=0.0)
SET03 = dict(tau_pv=3.33, tau_v1=19.6, tau_v2=1250.0, tau_pw=870.0, tau_mw=41.0, tau_d=0.25, tau_0=12.5, tau_r=33.33, tau_si=29.0, K=10.0, V_sic=0.85, V_c=0.13, V_v=0.04, C_si=1.0)
SET04 = dict(tau_pv=3.33, tau_v1=15.6, tau_v2=5.0, tau_pw=350.0, tau_mw=80.0, tau_d=0.407, tau_0=9.0, tau_r=34.0, tau_si=26.5, K=15.0, V_sic=0.45, V_c=0.15, V_v=0.04, C_si=1.0)
SET05 = dict(tau_pv=3.33, tau_v1=12.0, tau_v2=2.0, tau_pw=1000.0, tau_mw=100.0, tau_d=0.362, tau_0=5.0, tau_r=33.33, tau_si=29.0, K=15.0, V_sic=0.70, V_c=0.13, V_v=0.04, C_si=1.0)
SET06 = dict(tau_pv=3.33, tau_v1=9.0, tau_v2=8.0, tau_pw=250.0, tau_mw=60.0, tau_d=0.395, tau_0=9.0, tau_r=33.33, tau_si=29.0, K=15.0, V_sic=0.50, V_c=0.13, V_v=0.04, C_si=1.0)
SET07 = dict(tau_pv=10.0, tau_v1=7.0, tau_v2=7.0, tau_pw=250.0, tau_mw=60.0, tau_d=0.25, tau_0=12.0, tau_r=100.0, tau_si=29.0, K=15.0, V_sic=0.50, V_c=0.13, V_v=0.04, C_si=0.0)
SET08 = dict(tau_pv=13.03, tau_v1=19.6, tau_v2=1250.0, tau_pw=800.0, tau_mw=40.0, tau_d=0.45, tau_0=12.5, tau_r=33.25, tau_si=29.0, K=10.0, V_sic=0.85, V_c=0.13, V_v=0.04, C_si=1.0)
SET09 = dict(tau_pv=3.33, tau_v1=15.0, tau_v2=2.0, tau_pw=670.0, tau_mw=61.0, tau_d=0.25, tau_0=12.5, tau_r=28.0, tau_si=29.0, K=10.0, V_sic=0.45, V_c=0.13, V_v=0.05, C_si=1.0)
SET10 = dict(tau_pv=10.0, tau_v1=40.0, tau_v2=333.0, tau_pw=1000.0, tau_mw=65.0, tau_d=0.115, tau_0=12.5, tau_r=25.0, tau_si=22.22, K=10.0, V_sic=0.85, V_c=0.13, V_v=0.025, C_si=1.0)
SETS = {f"set_{i+1:02d}": s for i, s in enumerate([SET01, SET02, SET03, SET04, SET05, SET06, SET07, SET08, SET09, SET10])}

# table_data.tex rows (A-E = set_01 base with tau_d varied; F = set_02 base)
TABLE = {
    "A": dict(SET01, tau_d=0.41),
    "B": dict(SET01, tau_d=0.381),
    "C": dict(SET01, tau_d=0.389),
    "D": dict(SET01, tau_d=0.36),
    "E": dict(SET01, tau_d=0.25),
    "F": dict(SET02),
    "F1": dict(SET02, C_si=1.0),
}
TABLE.update(SETS)


@nb.njit(parallel=True, cache=True)
def _step(u, v, w, un, vn, wn, dt, dx2inv, D, prm):
    tau_pv, tau_v1, tau_v2, tau_pw, tau_mw, tau_d, tau_0, tau_r, tau_si, K, V_sic, V_c, V_v, C_si = (
        prm[0], prm[1], prm[2], prm[3], prm[4], prm[5], prm[6], prm[7], prm[8], prm[9], prm[10], prm[11], prm[12], prm[13])
    N = u.shape[0]
    gamma = 1.0 / 3.0
    for i in nb.prange(N):
        im = i - 1 if i > 0 else 0
        ip = i + 1 if i < N - 1 else N - 1
        for j in range(N):
            jm = j - 1 if j > 0 else 0
            jp = j + 1 if j < N - 1 else N - 1
            U = u[i, j]; V = v[i, j]; W = w[i, j]
            p = 1.0 if U >= V_c else 0.0
            q = 1.0 if U >= V_v else 0.0
            tau_mv = (1.0 - q) * tau_v1 + q * tau_v2
            Ifi = -V * p * (U - V_c) * (1.0 - U) / tau_d
            Iso = U * (1.0 - p) / tau_0 + p / tau_r
            x = K * (U - V_sic)
            if x < -3.0:
                tn = -1.0
            elif x > 3.0:
                tn = 1.0
            else:
                tn = x * (27.0 + x * x) / (27.0 + 9.0 * x * x)
            Isi = -W * (1.0 + tn) / (2.0 * tau_si) * C_si
            dV = (1.0 - p) * (1.0 - V) / tau_mv - p * V / tau_pv
            dW = (1.0 - p) * (1.0 - W) / tau_mw - p * W / tau_pw
            vn[i, j] = V + dV * dt
            wn[i, j] = W + dW * dt
            lap5 = (u[ip, j] - 2.0 * U + u[im, j]) + (u[i, jp] - 2.0 * U + u[i, jm])
            lap9 = u[ip, jp] + u[ip, jm] + u[im, jm] + u[im, jp] - 4.0 * U
            lap = ((1.0 - gamma) * lap5 + gamma * 0.5 * lap9 * 2.0) * dx2inv
            un[i, j] = U + dt * (D * lap - (Ifi + Iso + Isi))


def detect_tips(u, u_prev, thr, dx):
    """Tool's definition: cells where the u = thr isoline and the du/dt = 0 line both cross,
    intersection by the same linearisation as tiptShader.frag. Returns (x, y) in cm, array (n, 2)."""
    F = u - thr
    G = u - u_prev
    f0 = F[:-1, :-1]; fx = F[:-1, 1:]; fy = F[1:, :-1]; fxy = F[1:, 1:]
    g0 = G[:-1, :-1]; gx = G[:-1, 1:]; gy = G[1:, :-1]; gxy = G[1:, 1:]
    s = (f0 >= 0).astype(np.int8) + (fx >= 0) + (fy >= 0) + (fxy >= 0)
    bv = (s > 0) & (s < 4)
    s2 = (g0 >= 0).astype(np.int8) + (gx >= 0) + (gy >= 0) + (gxy >= 0)
    bdv = (s2 > 0) & (s2 < 4)
    cand = np.argwhere(bv & bdv)
    if cand.size == 0:
        return np.zeros((0, 2))
    ii, jj = cand[:, 0], cand[:, 1]
    a0 = f0[ii, jj].astype(np.float64); ax = fx[ii, jj] - a0; ay = fy[ii, jj] - a0
    b0 = g0[ii, jj].astype(np.float64); bx = gx[ii, jj] - b0; by = gy[ii, jj] - b0
    det = ax * by - ay * bx
    ok = np.abs(det) > 1e-30
    with np.errstate(divide="ignore", invalid="ignore"):
        xl = -(a0 * by - b0 * ay) / det
        yl = -(ax * b0 - bx * a0) / det
    ok &= (xl > 0) & (xl < 1) & (yl > 0) & (yl < 1)
    pts = np.stack([(jj[ok] + xl[ok]) * dx, (ii[ok] + yl[ok]) * dx], axis=1)
    return pts


def cluster_points(pts, radius):
    """Greedy clustering; returns cluster centroids sorted by size (largest first)."""
    if len(pts) == 0:
        return []
    remaining = pts.copy()
    clusters = []
    while len(remaining):
        seed = remaining[0]
        d = np.hypot(remaining[:, 0] - seed[0], remaining[:, 1] - seed[1])
        members = remaining[d < radius]
        clusters.append((len(members), members.mean(axis=0)))
        remaining = remaining[d >= radius]
    clusters.sort(key=lambda c: -c[0])
    return [c[1] for c in clusters]


class Sim:
    """State + stepping; S1 planar wave at t=0; S2 (lower-left recovered quadrant) on demand."""

    def __init__(self, prm, N=512, L=18.0, dt=0.1, D=0.001, dtype=np.float32, s1_frac=0.05, w0=0.4):
        self.prm = prm; self.N = N; self.L = L; self.dt = dt; self.D = D; self.dtype = dtype
        self.dx = L / N; self.dx2inv = 1.0 / (self.dx * self.dx)
        self.prm_arr = np.array([prm[k] for k in PARAM_ORDER], dtype=np.float64)
        self.u = np.zeros((N, N), dtype=dtype); self.v = np.ones((N, N), dtype=dtype); self.w = np.full((N, N), w0, dtype=dtype)
        self.un = np.empty_like(self.u); self.vn = np.empty_like(self.v); self.wn = np.empty_like(self.w)
        self.u[:, : int(round(s1_frac * N))] = 1.0
        self.step_no = 0

    @property
    def t(self):
        return self.step_no * self.dt

    def step(self):
        _step(self.u, self.v, self.w, self.un, self.vn, self.wn, self.dt, self.dx2inv, self.D, self.prm_arr)
        self.u, self.un = self.un, self.u; self.v, self.vn = self.vn, self.v; self.w, self.wn = self.wn, self.w
        self.step_no += 1

    def midline_state(self, rec_v=0.6):
        """x_front, x_rec (in grid columns) along the middle row."""
        N = self.N; mid = N // 2; V_c = self.prm["V_c"]
        row_u = self.u[mid]; row_v = self.v[mid]
        excited = np.nonzero(row_u >= V_c)[0]
        x_front = int(excited.max()) if excited.size else -1
        rec = np.nonzero((row_u < V_c) & (row_v > rec_v) & (np.arange(N) < max(x_front, 0)))[0]
        if rec.size:
            x_rec = int(rec.max())
        else:
            x_rec = N if (x_front < 0 and self.t > 50) else -1
        return x_front, x_rec

    def apply_s2(self, x_cols, half="lower"):
        mid = self.N // 2
        if half == "lower":
            self.u[:mid, :x_cols] = 1.0
        else:
            self.u[mid:, :x_cols] = 1.0

    def frame(self, size=128):
        """(2, n, n) float32: u and v downsampled to at most `size` points per side (whole sheet)."""
        ds = max(1, -(-self.N // size))
        return np.stack([self.u[::ds, ::ds], self.v[::ds, ::ds]]).astype(np.float32)


def run_protocol(prm, N=512, L=18.0, dt=0.1, T=8000.0, D=0.001, dtype=np.float32, thr=0.5, tip_every=1.0,
                 tip_lag_steps=2, frame_every=100.0, s2_x_frac=0.4, s2_full_half=False, s2_max_t=1500.0,
                 max_jump=1.5, verbose=True, sustain_check_t=1500.0, sustain_min_frac=0.5):
    """One S1-S2 run. Returns dict(t, x, y, ntips, frames, frame_t, s2_time, u, v, w, dx, L, wall, sustained)."""
    sim = Sim(prm, N=N, L=L, dt=dt, D=D, dtype=dtype)
    nsteps = int(round(T / dt))
    tip_stride = max(1, int(round(tip_every / dt)))
    frame_stride = max(1, int(round(frame_every / dt)))
    ts, xs, ys, ntips = [], [], [], []
    frames, frame_t = [], []
    s2_done = False; s2_time = None
    u_lag = sim.u.copy()
    last_tip = None
    t0 = time.time()
    for step in range(1, nsteps + 1):
        sim.step(); t = sim.t
        if not s2_done and step % 10 == 0:
            x_front, x_rec = sim.midline_state()
            if (x_rec >= s2_x_frac * N) or t >= s2_max_t:
                sim.apply_s2(N if s2_full_half else max(x_rec, 1))
                s2_done = True; s2_time = t
                if verbose:
                    print(f"  S2 at t={t:.1f} ms (x_front={x_front*sim.dx:.2f} cm, x_rec={x_rec*sim.dx:.2f} cm)")
        if (step + tip_lag_steps) % tip_stride == 0:
            u_lag = sim.u.copy()
        if step % tip_stride == 0:
            pts = detect_tips(sim.u, u_lag, thr, sim.dx)
            cl = cluster_points(pts, radius=0.3)
            tip = None
            if cl:
                if last_tip is None:
                    tip = cl[0]
                else:
                    dists = [np.hypot(c[0] - last_tip[0], c[1] - last_tip[1]) for c in cl]
                    k = int(np.argmin(dists))
                    if dists[k] < max_jump:
                        tip = cl[k]
                    elif np.isnan(xs[-1]) and len(xs) > 300 and all(np.isnan(xs[-300:])):
                        tip = cl[0]   # lost for 300 samples: re-acquire the largest cluster
            if tip is not None:
                last_tip = tip
            ts.append(t); ntips.append(len(cl))
            xs.append(tip[0] if tip is not None else np.nan)
            ys.append(tip[1] if tip is not None else np.nan)
            # early abort: spiral dead (no tip for 600 ms after the sustain check window opened)
            if s2_done and t > s2_time + sustain_check_t and len(xs) > 600 and np.all(np.isnan(xs[-600:])):
                if verbose:
                    print(f"  spiral lost at t={t:.0f} ms; aborting run")
                break
        if step % frame_stride == 0:
            frames.append(sim.frame()); frame_t.append(t)
        if verbose and nsteps >= 10 and step % (nsteps // 10) == 0:
            print(f"  t={t:.0f} ms  ({time.time()-t0:.1f} s)  tips={ntips[-1] if ntips else 0}")
    ts = np.array(ts); xs = np.array(xs); ys = np.array(ys)
    sustained = False
    if s2_time is not None:
        m = ts > s2_time + sustain_check_t
        sustained = m.sum() > 0 and np.mean(~np.isnan(xs[m])) >= sustain_min_frac and not np.isnan(xs[-1])
    return dict(t=ts, x=xs, y=ys, ntips=np.array(ntips), frames=np.array(frames), frame_t=np.array(frame_t),
                s2_time=s2_time, u=sim.u.copy(), v=sim.v.copy(), w=sim.w.copy(), dx=sim.dx, L=L, wall=time.time() - t0,
                sustained=bool(sustained), s2_x_frac=s2_x_frac, N=N, dt=dt, T=T, dtype=str(np.dtype(dtype)))


def simulate(prm, s2_fracs=(0.4, 0.3, 0.55, 0.7), **kw):
    """Adaptive protocol: try S2 placements until a sustained spiral is obtained."""
    last = None
    for frac in s2_fracs:
        if kw.get("verbose", True):
            print(f" protocol: S2 when recovered region reaches {frac:.2f} L")
        res = run_protocol(prm, s2_x_frac=frac, **kw)
        res["attempts"] = (last["attempts"] + 1) if last else 1
        if res["sustained"]:
            return res
        last = res
    return last


def plot_result(res, path, transient=1500.0, title=""):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(15, 5))
    m = res["t"] > transient
    axs[0].imshow(res["u"], origin="lower", extent=[0, res["L"], 0, res["L"]], cmap="jet", vmin=0, vmax=1.2)
    axs[0].plot(res["x"][m], res["y"][m], "w-", lw=0.6)
    axs[0].set_title(f"{title} final u + tip path (t>{transient:.0f})")
    axs[1].plot(res["x"][m], res["y"][m], "k-", lw=0.6); axs[1].set_aspect("equal"); axs[1].set_title("tip trajectory")
    axs[2].plot(res["t"], res["x"], label="x"); axs[2].plot(res["t"], res["y"], label="y"); axs[2].legend(); axs[2].set_title("tip coords vs t")
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)


def load_params(spec):
    if spec in TABLE:
        return dict(TABLE[spec])
    if os.path.exists(spec):
        with open(spec) as fh:
            return json.load(fh)
    raise SystemExit(f"unknown parameter spec {spec}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("row")
    ap.add_argument("--N", type=int, default=512)
    ap.add_argument("--T", type=float, default=8000)
    ap.add_argument("--dt", type=float, default=0.1)
    ap.add_argument("--f64", action="store_true")
    ap.add_argument("--full-half", action="store_true", help="S2 excites the whole lower half (v1 protocol)")
    ap.add_argument("--s2", type=float, default=None, help="single S2 placement fraction (no retries)")
    ap.add_argument("--out", default="out")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    prm = load_params(a.row)
    name = os.path.splitext(os.path.basename(a.row))[0]
    print(f"{name}: tau_d={prm['tau_d']} C_si={prm['C_si']}  N={a.N} dt={a.dt} T={a.T} {'f64' if a.f64 else 'f32'}")
    kw = dict(N=a.N, T=a.T, dt=a.dt, dtype=np.float64 if a.f64 else np.float32, s2_full_half=a.full_half)
    res = simulate(prm, **kw) if a.s2 is None else run_protocol(prm, s2_x_frac=a.s2, **kw)
    tag = f"{name}_N{a.N}_dt{a.dt}_{'f64' if a.f64 else 'f32'}{a.tag}"
    np.savez_compressed(os.path.join(a.out, f"{tag}.npz"), t=res["t"], x=res["x"], y=res["y"], ntips=res["ntips"],
                        frames=res["frames"], frame_t=res["frame_t"], u=res["u"], v=res["v"], s2_time=res["s2_time"] or -1,
                        sustained=res["sustained"], s2_x_frac=res["s2_x_frac"], params=json.dumps(prm))
    plot_result(res, os.path.join(a.out, f"{tag}.png"), title=name)
    lost = float(np.isnan(res["x"]).mean())
    print(f"done in {res['wall']:.1f} s; sustained={res['sustained']} attempts={res.get('attempts', 1)}; tip lost fraction {lost:.3f}; S2 at {res['s2_time']} (frac {res['s2_x_frac']})")


def run_protocol_obstacle(prm, N=512, L=18.0, dt=0.1, T=8000.0, D=0.001, dtype=np.float32, thr=0.5, tip_every=1.0,
                          tip_lag_steps=2, frame_every=100.0, obst_len_frac=0.5, obst_thick=0.12, release_x=1.0,
                          release_y=0.3, max_jump=1.5, verbose=True, sustain_check_t=1500.0, sustain_min_frac=0.5,
                          s1_frac=0.05, release_max_t=1500.0):
    """Obstacle-pivot initiation: planar wave from the bottom edge; a temporary unexcitable line along y = L/2
    for x < obst_len_frac*L blocks the left part of the wave, the right part wraps around the line's end; the line
    is released once the wrapped front has come back over its top side (release_x cm left of the end, release_y cm
    above it), leaving a single free end at the domain centre."""
    sim = Sim(prm, N=N, L=L, dt=dt, D=D, dtype=dtype, s1_frac=0.0)
    sim.u[: int(round(s1_frac * N)), :] = 1.0          # S1 from the bottom edge (rows = y)
    dx = sim.dx
    yc = N // 2; half = max(1, int(round(0.5 * obst_thick / dx)))
    xe = int(round(obst_len_frac * N))
    mask = np.zeros((N, N), dtype=bool); mask[yc - half: yc + half + 1, :xe] = True
    probe = (yc + half + int(round(release_y / dx)), max(0, xe - int(round(release_x / dx))))
    nsteps = int(round(T / dt)); tip_stride = max(1, int(round(tip_every / dt))); frame_stride = max(1, int(round(frame_every / dt)))
    ts, xs, ys, ntips, frames, frame_t = [], [], [], [], [], []
    released = False; release_t = None
    u_lag = sim.u.copy(); last_tip = None; t0 = time.time()
    V_c = prm["V_c"]
    for step in range(1, nsteps + 1):
        sim.step(); t = sim.t
        if not released:
            sim.u[mask] = 0.0; sim.v[mask] = 1.0; sim.w[mask] = 1.0
            if step % 10 == 0 and (sim.u[probe] >= V_c or t >= release_max_t):
                released = True; release_t = t
                if verbose:
                    print(f"  obstacle released at t={t:.1f} ms")
        if (step + tip_lag_steps) % tip_stride == 0:
            u_lag = sim.u.copy()
        if step % tip_stride == 0:
            pts = detect_tips(sim.u, u_lag, thr, dx)
            if not released:   # ignore detections on the obstacle line itself
                pts = pts[np.abs(pts[:, 1] - yc * dx) > 2 * obst_thick] if len(pts) else pts
            cl = cluster_points(pts, radius=0.3)
            tip = None
            if cl:
                if last_tip is None:
                    tip = cl[0]
                else:
                    dists = [np.hypot(c[0] - last_tip[0], c[1] - last_tip[1]) for c in cl]
                    k = int(np.argmin(dists))
                    if dists[k] < max_jump:
                        tip = cl[k]
                    elif len(xs) > 300 and np.all(np.isnan(xs[-300:])):
                        tip = cl[0]
            if tip is not None:
                last_tip = tip
            ts.append(t); ntips.append(len(cl)); xs.append(tip[0] if tip is not None else np.nan); ys.append(tip[1] if tip is not None else np.nan)
            if released and t > release_t + sustain_check_t and len(xs) > 600 and np.all(np.isnan(xs[-600:])):
                if verbose:
                    print(f"  spiral lost at t={t:.0f} ms; aborting run")
                break
        if step % frame_stride == 0:
            frames.append(sim.frame()); frame_t.append(t)
        if verbose and nsteps >= 10 and step % (nsteps // 10) == 0:
            print(f"  t={t:.0f} ms  ({time.time()-t0:.1f} s)  tips={ntips[-1] if ntips else 0}")
    ts = np.array(ts); xs = np.array(xs); ys = np.array(ys)
    sustained = False
    if release_t is not None:
        m = ts > release_t + sustain_check_t
        sustained = m.sum() > 0 and np.mean(~np.isnan(xs[m])) >= sustain_min_frac and not np.isnan(xs[-1])
    return dict(t=ts, x=xs, y=ys, ntips=np.array(ntips), frames=np.array(frames), frame_t=np.array(frame_t),
                s2_time=release_t, u=sim.u.copy(), v=sim.v.copy(), w=sim.w.copy(), dx=dx, L=L, wall=time.time() - t0,
                sustained=bool(sustained), s2_x_frac=obst_len_frac, N=N, dt=dt, T=T, dtype=str(np.dtype(dtype)), protocol="obstacle")
