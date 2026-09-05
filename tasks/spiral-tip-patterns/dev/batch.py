import sys, os, json, numpy as np
os.environ.setdefault("NUMBA_NUM_THREADS", "2")
from concurrent.futures import ProcessPoolExecutor
import fk2d

def gen_candidates(seed=20260905, n1=24, n2=12):
    rng = np.random.default_rng(seed)
    cands = {}
    for i in range(n1):
        p = dict(fk2d.SET01)
        p.update(tau_d=round(float(rng.uniform(0.30, 0.42)), 4), tau_r=round(float(rng.uniform(35, 75)), 2), tau_si=round(float(rng.uniform(30, 70)), 2),
                 tau_0=round(float(rng.uniform(6, 12)), 2), tau_v1=round(float(rng.uniform(10, 30)), 2), tau_pv=round(float(rng.uniform(2.5, 5)), 3),
                 tau_mw=round(float(rng.uniform(8, 30)), 2), V_sic=round(float(rng.uniform(0.7, 0.9)), 3), V_v=round(float(rng.uniform(0.04, 0.06)), 4))
        cands[f"s1_{i:02d}"] = p
    for i in range(n2):
        p = dict(fk2d.SET02)
        tv = round(float(rng.uniform(6, 20)), 2)
        p.update(tau_d=round(float(rng.uniform(0.2, 0.35)), 4), tau_r=round(float(rng.uniform(100, 250)), 1), tau_0=round(float(rng.uniform(8, 14)), 2),
                 tau_pv=tv, tau_v1=tv, tau_v2=tv, tau_mw=round(float(rng.uniform(8, 30)), 2))
        cands[f"s2_{i:02d}"] = p
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
    cands = gen_candidates()
    os.makedirs(outroot, exist_ok=True)
    json.dump(cands, open(os.path.join(outroot, "candidates.json"), "w"), indent=1)
    with ProcessPoolExecutor(max_workers=6) as ex:
        for name, s in ex.map(run_one, [(n, p, outroot, T) for n, p in cands.items()]):
            d = s.get("descriptors", {})
            print(f"{name}: {s['status']} cls={s.get('cls')} protocol={s.get('protocol')} T1={d.get('T1')} R2={d.get('R2')} r1={d.get('r1')} petals={d.get('petals')} attempts={len(s['attempts'])} wall={s.get('wall_s')}", flush=True)
