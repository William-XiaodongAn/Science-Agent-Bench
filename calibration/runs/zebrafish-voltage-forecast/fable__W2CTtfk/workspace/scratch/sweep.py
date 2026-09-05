"""Offline sweep harness: evaluates a list of configs with the real Evaluator (unlimited budget), in parallel processes.
Usage: python3 sweep.py <json-list-file> <out.jsonl>   (each line: {"config":..., "dev":..., "per":[...]})"""
import os, sys, json, time
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1"); os.environ.setdefault("MKL_NUM_THREADS", "1")
sys.path.insert(0, "/workspace/baseline"); sys.path.insert(0, "/workspace")
import numpy as np
from multiprocessing import Pool
import search_api

V = np.load("/workspace/data/train_data.npy"); S = np.load("/workspace/data/train_stim.npy")

def run(job):
    cfg, seed, origins = job["config"], job.get("seed", 0), tuple(job.get("origins", search_api.DEV_ORIGINS))
    ev = search_api.Evaluator(V, S, seed=seed, budget=10**9, origins=origins)
    t0 = time.time()
    try:
        d = ev.evaluate(cfg); per = ev.history[-1][2]
    except Exception as e:
        d = float("inf"); per = [str(e)]
    return dict(config=cfg, seed=seed, origins=list(origins), dev=d, per=per, sec=round(time.time() - t0, 2))

if __name__ == "__main__":
    jobs = json.load(open(sys.argv[1])); out = sys.argv[2]
    nproc = int(os.environ.get("NPROC", "4"))
    with Pool(nproc) as p, open(out, "a") as f:
        for r in p.imap_unordered(run, jobs):
            f.write(json.dumps(r, default=str) + "\n"); f.flush()
            print(f"{r['dev']:.4f} {r['per']} seed={r['seed']} {r['sec']}s {json.dumps(r['config'], default=str)}", flush=True)
