#!/usr/bin/env python3
import argparse,json,sys,time,itertools
import numpy as np
sys.path.insert(0,"/workspace")
from baseline.search_api import Evaluator

def configs():
 parts=[(123,123,122),(100,168,100),(150,150,68),(68,150,150),(150,68,150),(80,128,160),(160,128,80),(127,137,104),(125,128,115),(130,119,119)]
 out=[]
 for layers in parts:
  for leaks in itertools.permutations((.05,.15,.4)):
   cfg=dict(layers=layers,voltage_feedback=False,input_to_all_layers=True,all_layers_to_output=True,input_to_output=True,
            inter_scale=0.,leak=leaks,spectral_radius=.9,connectivity=.1,input_scale={"bias":.03,"stimulus":5.},ridge=1e-8,washout=1000)
   out.append((f'p{layers}_{leaks}',cfg))
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);a=ap.parse_args();cs=configs();v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,a.seed,budget=60);res=[];t=time.time()
 for i,(name,c) in enumerate(cs):
  z=ev.evaluate(c);p=ev.history[-1][2];res.append(dict(i=i,name=name,score=z,per=p,config=c));print(i,z,np.round(p,6),name,flush=True)
 print('elapsed',time.time()-t);json.dump(res,open(f'/workspace/experiments/probe_permute_seed{a.seed}.json','w'),indent=2)
