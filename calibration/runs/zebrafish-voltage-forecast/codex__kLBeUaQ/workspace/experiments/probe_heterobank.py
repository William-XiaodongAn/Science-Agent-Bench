#!/usr/bin/env python3
import argparse,json,sys,time,itertools
import numpy as np
sys.path.insert(0,"/workspace")
from baseline.search_api import Evaluator

def configs():
 out=[]
 def add(n,**c):out.append((n,c))
 base=dict(voltage_feedback=False,input_to_all_layers=True,all_layers_to_output=True,input_to_output=True,inter_scale=0.,
           input_scale={"bias":.03,"stimulus":5.},connectivity=.1,washout=1000)
 arch=[(123,123,122),(92,92,92,92),(74,74,74,73,73)]
 for layers,(lo,hi),sr,rr in itertools.product(arch,[(.01,.5),(.02,.5),(.03,.5),(.05,.5),(.02,.8),(.05,.8),(.08,.6)],(.86,.9,.94),(1e-9,1e-8,1e-7)):
  add(f'h{len(layers)}_{lo}_{hi}_{sr}_{rr}',**base,layers=layers,leak=(lo,hi),spectral_radius=sr,ridge=rr)
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args()
 cs=configs()[a.start:a.stop];v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,a.seed,budget=max(60,len(cs)))
 res=[];t=time.time()
 for i,(name,c) in enumerate(cs,a.start):
  z=ev.evaluate(c);p=ev.history[-1][2];res.append(dict(i=i,name=name,score=z,per=p,config=c));print(i,name,z,np.round(p,6),flush=True)
 print('elapsed',time.time()-t);json.dump(res,open(f'/workspace/experiments/probe_heterobank_seed{a.seed}_{a.start}_{a.stop or "end"}.json','w'),indent=2)
