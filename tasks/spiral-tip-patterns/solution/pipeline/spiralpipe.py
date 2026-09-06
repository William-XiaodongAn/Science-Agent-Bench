"""Reference pipeline: parameters -> single sustained spiral -> tip trace -> pattern class + drawings.

run(params, outdir, ...) tries initiation protocols in order until one yields a single sustained spiral,
then writes tip_trace.csv, frames/, pattern.json, trajectory.png, snapshot.png, run_log.txt.
"""
from __future__ import annotations
import json, os, time
import numpy as np
import fk2d, tipdyn

PROTOCOLS = [
    ("obstacle", dict()),
    ("s2half", dict(s2_x_frac=0.5)),
    ("obstacle", dict(release_x=2.0, release_y=0.6)),
    ("s2half", dict(s2_x_frac=0.35)),
    ("s2half", dict(s2_x_frac=0.65)),
    ("obstacle", dict(L=27.0, N=768)),
    ("s2half", dict(s2_x_frac=0.5, L=27.0, N=768)),
]


def _single_spiral(res, late_ms=2000.0):
    m = res["t"] > res["t"][-1] - late_ms
    late = res["ntips"][m]
    return bool(res["sustained"]) and late.size > 0 and 0.7 <= late.mean() <= 1.35


def run(params: dict, outdir: str, T=8000.0, N=512, L=18.0, dt=0.1, dtype=np.float32, frame_every=100.0,
        protocols=PROTOCOLS, verbose=True, save_frames=True):
    os.makedirs(outdir, exist_ok=True)
    log = []
    t_start = time.time()
    chosen = None
    for name, kw in protocols:
        kw = dict(kw); Lp = kw.pop("L", L); Np = kw.pop("N", N)
        if verbose:
            print(f"[pipeline] protocol {name} {kw} L={Lp} N={Np}")
        t0 = time.time()
        if name == "obstacle":
            res = fk2d.run_protocol_obstacle(params, N=Np, L=Lp, dt=dt, T=T, dtype=dtype, frame_every=frame_every, verbose=False, **kw)
        else:
            res = fk2d.run_protocol(params, N=Np, L=Lp, dt=dt, T=T, dtype=dtype, frame_every=frame_every, verbose=False, s2_full_half=True, **kw)
        desc = tipdyn.describe(res["t"], res["x"], res["y"])
        ok = _single_spiral(res) and desc["cls"] != "X"
        m = res["t"] > res["t"][-1] - 2000
        entry = dict(protocol=name, options=kw, L=Lp, N=Np, sustained=bool(res["sustained"]), late_tip_clusters=float(res["ntips"][m].mean()) if m.any() else None,
                     init_event_ms=res["s2_time"], cls=desc.get("cls"), reason=desc.get("reason", ""), wall_s=round(time.time() - t0, 1), accepted=bool(ok))
        log.append(entry)
        if verbose:
            print(f"[pipeline]   -> sustained={entry['sustained']} late_clusters={entry['late_tip_clusters']} cls={entry['cls']} {entry['reason']} ({entry['wall_s']} s)")
        if ok:
            chosen = (name, kw, Lp, Np, res, desc)
            break
    if chosen is None:
        summary = dict(status="failed", attempts=log, params=params)
        with open(os.path.join(outdir, "pattern.json"), "w") as fh:
            json.dump(summary, fh, indent=1)
        with open(os.path.join(outdir, "run_log.txt"), "w") as fh:
            fh.write("no protocol produced a single sustained spiral\n" + json.dumps(log, indent=1))
        return summary
    name, kw, Lp, Np, res, desc = chosen
    # tip trace
    with open(os.path.join(outdir, "tip_trace.csv"), "w") as fh:
        fh.write("t,x_tip,y_tip\n")
        for t, x, y in zip(res["t"], res["x"], res["y"]):
            fh.write(f"{t:.2f},{'' if np.isnan(x) else f'{x:.5f}'},{'' if np.isnan(y) else f'{y:.5f}'}\n")
    # frames (u and v, downsampled to <= 128x128)
    if save_frames:
        fdir = os.path.join(outdir, "frames"); os.makedirs(fdir, exist_ok=True)
        for arr, t in zip(res["frames"], res["frame_t"]):
            np.save(os.path.join(fdir, f"frame_{int(round(t)):06d}.npy"), arr)
    # drawings
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    window = 6000.0
    m = res["t"] > res["t"][-1] - window
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(res["x"][m], res["y"][m], "k-", lw=0.7); ax.set_aspect("equal"); ax.axis("off")
    fig.savefig(os.path.join(outdir, "trajectory.png"), dpi=150, bbox_inches="tight"); plt.close(fig)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.imshow(res["u"], origin="lower", extent=[0, Lp, 0, Lp], cmap="jet", vmin=0, vmax=1.2)
    ax.plot(res["x"][m], res["y"][m], "w-", lw=0.7); ax.axis("off")
    fig.savefig(os.path.join(outdir, "snapshot.png"), dpi=150, bbox_inches="tight"); plt.close(fig)
    # pattern + log
    clean = {k: (None if isinstance(v, float) and np.isnan(v) else (float(v) if isinstance(v, (np.floating, float)) else (int(v) if isinstance(v, (np.integer,)) else v)))
             for k, v in desc.items()}
    summary = dict(status="ok", cls=desc["cls"], descriptors=clean, protocol=name, protocol_options=kw, domain_cm=Lp, grid=Np, dt_ms=dt,
                   precision=str(np.dtype(dtype)), T_ms=T, analysis_window_ms=window, init_event_ms=res["s2_time"], attempts=log,
                   params=params, wall_s=round(time.time() - t_start, 1))
    with open(os.path.join(outdir, "pattern.json"), "w") as fh:
        json.dump(summary, fh, indent=1)
    with open(os.path.join(outdir, "run_log.txt"), "w") as fh:
        fh.write(f"params: {json.dumps(params)}\nprotocol: {name} {kw}\ngrid: {Np}x{Np} over {Lp}x{Lp} cm (dx={Lp/Np:.4f} cm), dt={dt} ms, {np.dtype(dtype)}\n")
        fh.write(f"steps: {int(round(T/dt))}, model time {T} ms; initiation event at {res['s2_time']} ms\n")
        fh.write(f"tip: u=0.5 isoline x du/dt=0 (lag 0.2 ms), sampled every 1 ms; analysis window = final {window:.0f} ms\n")
        fh.write(f"class: {desc['cls']}  descriptors: {tipdyn.summarize(desc)}\nwall time: {summary['wall_s']} s\nattempts: {json.dumps(log)}\n")
    return summary


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("params", help="table row name or JSON file")
    ap.add_argument("outdir")
    ap.add_argument("--T", type=float, default=8000)
    ap.add_argument("--N", type=int, default=512)
    ap.add_argument("--f64", action="store_true")
    a = ap.parse_args()
    prm = fk2d.load_params(a.params)
    s = run(prm, a.outdir, T=a.T, N=a.N, dtype=np.float64 if a.f64 else np.float32)
    print(json.dumps({k: s[k] for k in s if k not in ("attempts", "descriptors", "params")}))
