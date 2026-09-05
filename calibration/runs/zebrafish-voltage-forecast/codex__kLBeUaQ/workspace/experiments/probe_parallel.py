#!/usr/bin/env python3
import argparse,json,sys,time
import numpy as np
sys.path.insert(0,"/workspace")
from baseline.search_api import Evaluator

def configs(n=60):
 rng=np.random.default_rng(481516)
 out=[]
 # Hand anchors, followed by a reproducible space-filling random design.
 anchors=[
  ((123,123,122),(.05,.15,.4),.90,1e-9,.03,5.,.1),
  ((123,123,122),(.05,.15,.4),.90,1e-8,.03,5.,.1),
  ((92,92,92,92),(.04,.1,.22,.55),.90,1e-9,.03,5.,.1),
  ((184,184),(.08,.25),.90,1e-7,.03,5.,.1),
 ]
 specs=list(anchors)
 while len(specs)<n:
  nl=int(rng.choice([2,3,3,3,4,4,5]))
  # Ensure useful width in each independent bank.
  raw=rng.dirichlet(np.full(nl,3.0)); sizes=np.maximum(35,np.floor(raw*(368-35*nl)).astype(int)+35)
  while sizes.sum()>368:sizes[np.argmax(sizes)]-=1
  while sizes.sum()<368:sizes[np.argmin(sizes)]+=1
  # Ordered log-spaced time scales with jitter around the empirically good range.
  lo=np.exp(rng.uniform(np.log(.025),np.log(.09))); hi=np.exp(rng.uniform(np.log(.28),np.log(.75)))
  leaks=np.exp(np.linspace(np.log(lo),np.log(hi),nl)+rng.normal(0,.12,nl)); leaks=np.sort(np.clip(leaks,.015,.9))
  sr=rng.uniform(.84,.98); ridge=10**rng.uniform(-10,-6.2)
  bias=10**rng.uniform(-3,-.65); stim=np.exp(rng.uniform(np.log(3),np.log(20)))
  conn=float(rng.choice([.03,.05,.1,.2,.4,.7,1.]))
  specs.append((tuple(map(int,sizes)),tuple(map(float,leaks)),float(sr),float(ridge),float(bias),float(stim),conn))
 for i,(layers,leaks,sr,ridge,bias,stim,conn) in enumerate(specs[:n]):
  cfg=dict(layers=layers,voltage_feedback=False,input_to_all_layers=True,all_layers_to_output=True,
           input_to_output=True,inter_scale=0.,leak=leaks,spectral_radius=sr,connectivity=conn,
           input_scale={"bias":bias,"stimulus":stim},ridge=ridge,washout=1000)
  out.append((f"par{i:02d}",cfg))
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args()
 cs=configs()[a.start:a.stop];v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,a.seed,budget=max(60,len(cs)))
 res=[];t=time.time()
 for i,(name,c) in enumerate(cs,a.start):
  z=ev.evaluate(c);p=ev.history[-1][2];res.append(dict(i=i,name=name,score=z,per=p,config=c));print(f'{i:02d} {name} {z:.6f} {np.round(p,6)} {c["layers"]} {np.round(c["leak"],3)} sr={c["spectral_radius"]:.3f} r={c["ridge"]:.1e}',flush=True)
 print('elapsed',time.time()-t);json.dump(res,open(f'/workspace/experiments/probe_parallel_seed{a.seed}_{a.start}_{a.stop or "end"}.json','w'),indent=2)
