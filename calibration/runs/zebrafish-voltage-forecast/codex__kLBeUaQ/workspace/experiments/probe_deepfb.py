#!/usr/bin/env python3
import argparse,json,sys,time
import numpy as np
sys.path.insert(0,"/workspace")
from baseline.search_api import Evaluator

def configs(n=60):
 rng=np.random.default_rng(8675309); out=[]
 anchors=[]
 for layers in ((184,184),(123,123,122),(92,92,92,92),(74,74,74,73,73)):
  nl=len(layers)
  anchors.append((layers,tuple([.15]*nl),.9,.1,.001,.01,False,False,False))
  anchors.append((layers,tuple(np.geomspace(.05,.5,nl)),.9,.1,.001,.01,False,True,False))
 specs=list(anchors)
 while len(specs)<n:
  nl=int(rng.choice([2,2,3,3,4,5])); q,r=divmod(368,nl); layers=tuple([q+1]*r+[q]*(nl-r))
  if rng.random()<.5: leaks=tuple(map(float,np.geomspace(np.exp(rng.uniform(np.log(.03),np.log(.15))),np.exp(rng.uniform(np.log(.25),np.log(.8))),nl)))
  else: leaks=tuple([float(np.exp(rng.uniform(np.log(.06),np.log(.5))))]*nl)
  sr=float(rng.uniform(.75,1.1)); inter=float(np.exp(rng.uniform(np.log(.005),np.log(1.))))
  ridge=float(10**rng.uniform(-5,-1.5)); vs=float(10**rng.uniform(-4,-.5))
  ia=bool(rng.integers(2)); ao=bool(rng.integers(2)); io=bool(rng.integers(2))
  specs.append((layers,leaks,sr,inter,ridge,vs,ia,ao,io))
 for i,(layers,leaks,sr,inter,ridge,vs,ia,ao,io) in enumerate(specs[:n]):
  cfg=dict(layers=layers,voltage_feedback=True,input_to_all_layers=ia,all_layers_to_output=ao,input_to_output=io,
           inter_scale=inter,leak=leaks,spectral_radius=sr,connectivity=.1,input_scale={"bias":.03,"voltage":vs,"stimulus":5.},
           ridge=ridge,washout=1000,feedback_clip=(0.,1.))
  out.append((f"deep{i:02d}",cfg))
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args()
 cs=configs()[a.start:a.stop];v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,a.seed,budget=max(60,len(cs)))
 res=[];t=time.time()
 for i,(name,c) in enumerate(cs,a.start):
  z=ev.evaluate(c);p=ev.history[-1][2];res.append(dict(i=i,name=name,score=z,per=p,config=c));print(f'{i:02d} {z:.6f} {np.round(p,6)} L{c["layers"]} leak{np.round(c["leak"],2)} sr{c["spectral_radius"]:.2f} int{c["inter_scale"]:.3g} r{c["ridge"]:.1e} v{c["input_scale"]["voltage"]:.3g} {c["input_to_all_layers"]}/{c["all_layers_to_output"]}/{c["input_to_output"]}',flush=True)
 print('elapsed',time.time()-t);json.dump(res,open(f'/workspace/experiments/probe_deepfb_seed{a.seed}_{a.start}_{a.stop or "end"}.json','w'),indent=2)
