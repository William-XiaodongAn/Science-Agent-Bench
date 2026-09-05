#!/usr/bin/env python3
import argparse,json,sys,time,itertools
import numpy as np
sys.path.insert(0,"/workspace")
from baseline.search_api import Evaluator

def configs():
 out=[]
 def add(name,layers,leaks,sr=.9,ridge=1e-8,conn=.1):
  out.append((name,dict(layers=layers,voltage_feedback=False,input_to_all_layers=True,all_layers_to_output=True,input_to_output=True,inter_scale=0.,leak=leaks,spectral_radius=sr,connectivity=conn,input_scale={"bias":.03,"stimulus":5.},ridge=ridge,washout=1000)))
 archs=[(184,184),(123,123,122),(92,92,92,92),(74,74,74,73,73)]
 for layers in archs:
  n=len(layers)
  leaksets=[tuple([x]*n) for x in (.08,.12,.16,.22,.3)]
  leaksets += [tuple(np.geomspace(lo,hi,n)) for lo,hi in ((.03,.3),(.03,.5),(.05,.4),(.05,.7),(.08,.5),(.1,.8))]
  for leaks in leaksets:
   for ridge in (1e-9,1e-8,1e-7): add(f'b{n}_{leaks}_{ridge}',layers,leaks,ridge=ridge)
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args();cs=configs()[a.start:a.stop];v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,a.seed,budget=max(60,len(cs)));res=[];t=time.time()
 for i,(name,c) in enumerate(cs,a.start):
  z=ev.evaluate(c);p=ev.history[-1][2];res.append(dict(i=i,name=name,score=z,per=p,config=c));print(i,z,np.round(p,6),name,flush=True)
 print('elapsed',time.time()-t);json.dump(res,open(f'/workspace/experiments/probe_banks_seed{a.seed}_{a.start}_{a.stop or "end"}.json','w'),indent=2)
