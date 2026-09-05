"""Controlled candidate library for the hidden sets: modest multi-parameter perturbations around the two reference bases,
so the class cannot be read off tau_d alone but spirals stay sustained."""
import sys, os, json, numpy as np
os.environ.setdefault("NUMBA_NUM_THREADS", "2")
from concurrent.futures import ProcessPoolExecutor
import fk2d


def gen(seed=7):
    rng = np.random.default_rng(seed)
    cands = {}
    # set_01 family: tau_d over the meander sequence, other parameters +-12%
    tds = [0.415, 0.41, 0.405, 0.40, 0.395, 0.375, 0.37, 0.36, 0.35, 0.34, 0.32, 0.30, 0.28, 0.26]
    for i, td in enumerate(tds):
        p = dict(fk2d.SET01)
        f = lambda: float(rng.uniform(0.88, 1.12))
        p.update(tau_d=td, tau_r=round(50 * f(), 2), tau_si=round(45 * f(), 2), tau_0=round(8.3 * f(), 2), tau_v1=round(19.6 * f(), 2),
                 tau_pv=round(3.33 * f(), 3), tau_mw=round(11 * f(), 2), V_sic=round(float(rng.uniform(0.8, 0.9)), 3))
        cands[f"m1_{i:02d}"] = p
    # set_02 family (no slow inward current): linear cores
    for i in range(8):
        p = dict(fk2d.SET02)
        tv = round(float(rng.uniform(8, 13)), 2)
        p.update(tau_d=round(float(rng.uniform(0.22, 0.30)), 4), tau_r=round(float(rng.uniform(150, 230)), 1), tau_0=round(float(rng.uniform(9, 12)), 2),
                 tau_pv=tv, tau_v1=tv, tau_v2=tv, tau_mw=round(float(rng.uniform(9, 14)), 2))
        cands[f"m2_{i:02d}"] = p
    return cands


def run_one(args):
    name, prm, outroot, T = args
    import spiralpipe
    out = os.path.join(outroot, name)
    if os.path.exists(os.path.join(out, "pattern.json")):
        return name, json.load(open(os.path.join(out, "pattern.json")))
    s = spiralpipe.run(prm, out, T=T, verbose=False)
    return name, s


if __name__ == "__main__":
    outroot = sys.argv[1]; T = float(sys.argv[2]) if len(sys.argv) > 2 else 8000
    cands = gen()
    os.makedirs(outroot, exist_ok=True)
    json.dump(cands, open(os.path.join(outroot, "candidates.json"), "w"), indent=1)
    with ProcessPoolExecutor(max_workers=6) as ex:
        for name, s in ex.map(run_one, [(n, p, outroot, T) for n, p in cands.items()]):
            d = s.get("descriptors", {})
            print(f"{name}: {s['status']} cls={s.get('cls')} protocol={s.get('protocol')} T1={d.get('T1')} R2={d.get('R2')} r1={d.get('r1')} petals={d.get('petals')} ratio={d.get('petal_ratio')} attempts={len(s['attempts'])} wall={s.get('wall_s')}", flush=True)
