#!/usr/bin/env python3
import argparse,json,sys,time
import numpy as np
sys.path.insert(0,"/workspace")
from baseline.search_api import Evaluator

def configs(n=60):
 rng=np.random.default_rng(20260905); parts=[]
 while len(parts)<n:
  a=int(rng.integers(75,171)); b=int(rng.integers(75,171)); c=368-a-b
  if 55<=c<=180 and (a,b,c) not in parts:parts.append((a,b,c))
 out=[]
 for i,layers in enumerate(parts):
  # Alternate two well-conditioned readout regularizers to diversify the random bases.
  ridge=(10**(-8.0 if i%2==0 else -8.5))
  cfg=dict(layers=layers,voltage_feedback=False,input_to_all_layers=True,all_layers_to_output=True,input_to_output=True,
           inter_scale=0.,leak=(.05,.15,.4),spectral_radius=.9,connectivity=.1,
           input_scale={"bias":.03,"stimulus":5.},ridge=ridge,washout=1000)
  out.append((f"partition{i:02d}",cfg))
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args()
 cs=configs()[a.start:a.stop];v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,a.seed,budget=max(60,len(cs)))
 res=[];t=time.time()
 for i,(name,c) in enumerate(cs,a.start):
  z=ev.evaluate(c);p=ev.history[-1][2];res.append(dict(i=i,name=name,score=z,per=p,config=c));print(f'{i:02d} {z:.6f} {np.round(p,6)} {c["layers"]} r{c["ridge"]:.1e}',flush=True)
 print('elapsed',time.time()-t);json.dump(res,open(f'/workspace/experiments/probe_partitions_seed{a.seed}_{a.start}_{a.stop or "end"}.json','w'),indent=2)
