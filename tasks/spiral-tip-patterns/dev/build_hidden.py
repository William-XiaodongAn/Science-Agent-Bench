"""Assemble tests/sealed/hidden_sets.json from the controlled batch + robustness screen.  usage: build_hidden.py name1 name2 ..."""
import sys, json, os
root = "out/cand2"; cands = json.load(open(f"{root}/candidates.json"))
out = {}
for i, n in enumerate(sys.argv[1:]):
    s = json.load(open(f"{root}/{n}/pattern.json")); d = s["descriptors"]
    rob = {v: json.load(open(f"out/robust/{n}_{v}.json")) for v in ("f64", "N768", "s2half", "T12") if os.path.exists(f"out/robust/{n}_{v}.json")}
    rec = dict(params=cands[n], cls=s["cls"], T1=round(d["T1"], 1), r1=round(d["r1"], 3), R2=round(d["R2"], 3),
               petal_ratio=(round(d["petal_ratio"], 2) if d.get("petal_ratio") is not None else None), petals=d.get("petals"),
               source=n, robustness={v: dict(cls=r["cls"], petal_ratio=(None if r.get("petal_ratio") is None else round(r["petal_ratio"], 2)), sustained=r["sustained"]) for v, r in rob.items()},
               note=f"base {'set_01' if cands[n]['C_si'] > 0 else 'set_02'} perturbed; reference pipeline {s['protocol']} protocol")
    out[f"H{i+1}"] = rec
path = "/Users/guangzeluo/agent_task_generator/ai4science/Science-Agent-Bench/tasks/spiral-tip-patterns/tests/sealed/hidden_sets.json"
json.dump(out, open(path, "w"), indent=1)
for k, v in out.items():
    print(k, v["source"], v["cls"], v["petal_ratio"], {a: b["cls"] for a, b in v["robustness"].items()})
