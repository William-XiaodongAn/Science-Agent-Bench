"""Robustness screen for hidden-set candidates: re-run each candidate under (a) double precision, (b) 768^2 grid with
dt = 0.05 ms, (c) the S1-S2 block initiation, (d) 12 s of model time, and compare the class + petal ratio with the
pipeline's float32/512^2/obstacle result.  usage: robust.py <cand_root> name1 name2 ...  (outputs out/robust/<name>_<variant>.json)"""
import sys, os, json, numpy as np
os.environ.setdefault("NUMBA_NUM_THREADS", "2")
from concurrent.futures import ProcessPoolExecutor
import fk2d, tipdyn

VARIANTS = {
    "f64": dict(dtype=np.float64),
    "N768": dict(N=768, dt=0.05),
    "s2half": dict(protocol="s2half"),
    "T12": dict(T=12000.0),
    # the same three numerical variants under the S1-S2 protocol (for sets whose spiral the obstacle protocol cannot start)
    "s2_f64": dict(protocol="s2half", dtype=np.float64),
    "s2_N768": dict(protocol="s2half", N=768, dt=0.05),
    "s2_T12": dict(protocol="s2half", T=12000.0),
}
ONLY = os.environ.get("ROBUST_VARIANTS")
if ONLY:
    VARIANTS = {k: v for k, v in VARIANTS.items() if k in ONLY.split(",")}


def run_variant(args):
    name, prm, variant, outdir = args
    out = os.path.join(outdir, f"{name}_{variant}.json")
    if os.path.exists(out):
        return name, variant, json.load(open(out))
    kw = dict(VARIANTS[variant]); protocol = kw.pop("protocol", "obstacle")
    base = dict(N=512, L=18.0, dt=0.1, T=8000.0, dtype=np.float32, frame_every=1e9, verbose=False)
    base.update(kw)
    if protocol == "obstacle":
        res = fk2d.run_protocol_obstacle(prm, **base)
    else:
        res = fk2d.run_protocol(prm, s2_x_frac=0.5, s2_full_half=True, **base)
    d = tipdyn.describe(res["t"], res["x"], res["y"], window_ms=6000.0)
    m = res["t"] > res["t"][-1] - 2000
    rec = dict(sustained=bool(res["sustained"]), late_clusters=float(res["ntips"][m].mean()) if m.any() else None,
               cls=d.get("cls"), petal_ratio=d.get("petal_ratio"), T1=d.get("T1"), R2=d.get("R2"), r1=d.get("r1"), reason=d.get("reason", ""))
    json.dump(rec, open(out, "w"))
    return name, variant, rec


if __name__ == "__main__":
    root = sys.argv[1]; names = sys.argv[2:]
    cands = json.load(open(os.path.join(root, "candidates.json")))
    outdir = "out/robust"; os.makedirs(outdir, exist_ok=True)
    jobs = [(n, cands[n], v, outdir) for n in names for v in VARIANTS]
    base = {n: json.load(open(os.path.join(root, n, "pattern.json"))) for n in names}
    results = {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for n, v, rec in ex.map(run_variant, jobs):
            results.setdefault(n, {})[v] = rec
    for n in names:
        b = base[n]; bd = b.get("descriptors", {})
        line = f"{n}: base {b.get('cls')} ratio={bd.get('petal_ratio')}"
        agree = True
        for v in VARIANTS:
            r = results[n][v]
            ok = r["cls"] == b.get("cls")
            if ok and b.get("cls") in ("FI", "FO") and r.get("petal_ratio") is not None and bd.get("petal_ratio") is not None:
                ok = abs(r["petal_ratio"] - bd["petal_ratio"]) <= max(1.0, 0.15 * bd["petal_ratio"])
            agree &= ok
            line += f" | {v}: {r['cls']} ratio={None if r.get('petal_ratio') is None else round(r['petal_ratio'], 2)} sust={r['sustained']} late={None if r['late_clusters'] is None else round(r['late_clusters'], 2)}"
        print(("ROBUST   " if agree else "FRAGILE  ") + line, flush=True)
