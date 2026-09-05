#!/usr/bin/env python3
import argparse,json,sys,time
import numpy as np
sys.path.insert(0,"/workspace")
from baseline.search_api import Evaluator

def configs(n=60):
 rng=np.random.default_rng(314159); out=[]
 # Structured anchors span allocations before local randomized refinement.
 allocations=[(123,123,122),(80,180,108),(100,168,100),(150,150,68),(68,150,150),(150,68,150),(80,128,160),(160,128,80)]
 leaks=[(.03,.12,.35),(.04,.14,.4),(.05,.15,.4),(.06,.16,.45),(.07,.18,.5)]
 specs=[]
 for al in allocations:
  for lk in leaks:
   specs.append((al,lk,.9,1e-8,.03,5.,.1))
 # Mix in local variants. The order is permuted so reduced-budget checks remain representative.
 while len(specs)<n:
  raw=rng.dirichlet([5,5,4]); sz=np.maximum(50,np.floor(raw*218).astype(int)+50)
  while sz.sum()<368:sz[np.argmin(sz)]+=1
  while sz.sum()>368:sz[np.argmax(sz)]-=1
  lk=(rng.uniform(.025,.075),rng.uniform(.10,.20),rng.uniform(.3,.55))
  specs.append((tuple(map(int,sz)),lk,rng.uniform(.86,.95),10**rng.uniform(-9.5,-7),10**rng.uniform(-2,-.7),np.exp(rng.uniform(np.log(4),np.log(12))),float(rng.choice([.05,.1,.2,.4]))))
 order=np.random.default_rng(2718).permutation(len(specs[:n]))
 for j in order:
  layers,lk,sr,ridge,bias,stim,conn=specs[j]
  cfg=dict(layers=layers,voltage_feedback=False,input_to_all_layers=True,all_layers_to_output=True,input_to_output=True,
           inter_scale=0.,leak=tuple(map(float,lk)),spectral_radius=float(sr),connectivity=conn,
           input_scale={"bias":float(bias),"stimulus":float(stim)},ridge=float(ridge),washout=1000)
  out.append((f"fine{j:02d}",cfg))
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args()
 cs=configs()[a.start:a.stop];v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,a.seed,budget=max(60,len(cs)))
 res=[];t=time.time()
 for i,(name,c) in enumerate(cs,a.start):
  z=ev.evaluate(c);p=ev.history[-1][2];res.append(dict(i=i,name=name,score=z,per=p,config=c));print(f'{i:02d} {name} {z:.6f} {np.round(p,6)} {c["layers"]} {np.round(c["leak"],3)} sr{c["spectral_radius"]:.3f} r{c["ridge"]:.1e}',flush=True)
 print('elapsed',time.time()-t);json.dump(res,open(f'/workspace/experiments/probe_parfine_seed{a.seed}_{a.start}_{a.stop or "end"}.json','w'),indent=2)
