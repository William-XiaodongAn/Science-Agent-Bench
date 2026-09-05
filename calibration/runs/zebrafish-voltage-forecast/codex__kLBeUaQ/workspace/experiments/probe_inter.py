#!/usr/bin/env python3
import argparse,json,sys,time,itertools
import numpy as np
sys.path.insert(0,"/workspace")
from baseline.search_api import Evaluator

def configs():
 out=[]
 def add(n,**c):out.append((n,c))
 base=dict(layers=(123,123,122),voltage_feedback=False,all_layers_to_output=True,input_to_output=True,
           input_scale={"bias":.03,"stimulus":5.},connectivity=.1,washout=1000)
 for leaks,ia,inter,sr,rr in itertools.product([(.03,.12,.35),(.05,.15,.4),(.07,.18,.5)],(False,True),(0.,.001,.003,.01,.03,.1,.3),(.86,.9,.94),(1e-9,1e-8,1e-7)):
  add(f'i{inter}_{ia}_{leaks}_{sr}_{rr}',**base,leak=leaks,input_to_all_layers=ia,inter_scale=inter,spectral_radius=sr,ridge=rr)
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args()
 cs=configs()[a.start:a.stop];v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,a.seed,budget=max(60,len(cs)))
 res=[];t=time.time()
 for i,(name,c) in enumerate(cs,a.start):
  z=ev.evaluate(c);p=ev.history[-1][2];res.append(dict(i=i,name=name,score=z,per=p,config=c));print(i,z,np.round(p,6),name,flush=True)
 print('elapsed',time.time()-t);json.dump(res,open(f'/workspace/experiments/probe_inter_seed{a.seed}_{a.start}_{a.stop or "end"}.json','w'),indent=2)
