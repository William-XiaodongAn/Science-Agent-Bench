#!/usr/bin/env python3
"""Metered development probes through the supplied Evaluator only."""
import argparse, json, sys, time
import numpy as np

sys.path.insert(0, "/workspace")
from baseline.search_api import Evaluator


def configs():
    out = []
    def add(name, **kw): out.append((name, kw))
    add("default", layers=(368,))
    # Establish whether autonomous voltage feedback is the primary failure mode.
    for fb in (False, True):
        for leak in (.05, .1, .2, .35, .5, .7, 1.0):
            add(f"flat_fb{int(fb)}_l{leak}", layers=(368,), voltage_feedback=fb,
                leak=leak, spectral_radius=.9, input_scale=.1, ridge=1e-3)
    # Heterogeneous time constants in one reservoir.
    for fb in (False, True):
        for leaks in ((.005, 1.0), (.01, 1.0), (.02, 1.0), (.05, 1.0), (.01, .5)):
            add(f"hetero_fb{int(fb)}_{leaks[0]}_{leaks[1]}", layers=(368,),
                voltage_feedback=fb, leak=leaks, spectral_radius=.9, input_scale=.1,
                ridge=1e-3)
    # Parallel banks expose all timescales directly to the readout.
    for fb in (False, True):
        for leaks in ((.03,.3),(.05,.5),(.1,.7),(.1,1.0)):
            add(f"parallel_fb{int(fb)}_{leaks}", layers=(184,184), voltage_feedback=fb,
                input_to_all_layers=True, all_layers_to_output=True, inter_scale=0,
                leak=leaks, spectral_radius=.9, input_scale=.1, ridge=1e-3)
    return out


if __name__ == "__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--seed",type=int,default=0); ap.add_argument("--start",type=int,default=0); ap.add_argument("--stop",type=int)
    a=ap.parse_args(); cs=configs()[a.start:a.stop]
    v=np.load("/workspace/data/train_data.npy"); s=np.load("/workspace/data/train_stim.npy")
    ev=Evaluator(v,s,a.seed,budget=max(60,len(cs)))
    result=[]; t=time.time()
    for i,(name,cfg) in enumerate(cs,a.start):
        sc=ev.evaluate(cfg); per=ev.history[-1][2]
        result.append(dict(i=i,name=name,score=sc,per=per,config=cfg))
        print(f"{i:02d} {name:32s} {sc:.6f} {np.round(per,6)}",flush=True)
    print("elapsed",time.time()-t)
    with open(f"/workspace/experiments/probe_seed{a.seed}_{a.start}_{a.stop or 'end'}.json","w") as f: json.dump(result,f,indent=2)
