#!/usr/bin/env python3
import argparse,json,sys,time,itertools
import numpy as np
sys.path.insert(0,"/workspace")
from baseline.search_api import Evaluator

def configs():
 out=[]
 def add(name,**kw):out.append((name,kw))
 b=dict(voltage_feedback=False,spectral_radius=.92,input_scale={"bias":.1,"stimulus":5.},ridge=1e-8,washout=1000)
 # Fine flat interactions.
 for sr,ll in itertools.product((.89,.90,.91,.92,.93,.94),(.11,.12,.13,.14,.15,.16)):
  add(f"flat_{sr}_{ll}",**{**b,"layers":(368,),"spectral_radius":sr,"leak":ll})
 # Parallel banks and cascades with low regularisation.
 archs=[((184,184),(.08,.25)),((184,184),(.12,.35)),((184,184),(.15,.4)),
        ((123,123,122),(.05,.15,.4)),((123,123,122),(.1,.2,.5)),
        ((92,92,92,92),(.04,.1,.22,.55))]
 for layers,leaks in archs:
  for rr in (1e-9,1e-8,1e-7):
   add(f"par{len(layers)}_{leaks}_r{rr}",**{**b,"layers":layers,"leak":leaks,"ridge":rr,
       "input_to_all_layers":True,"all_layers_to_output":True,"inter_scale":0})
 for nl,layers in ((2,(184,184)),(3,(123,123,122))):
  for inter in (.01,.03,.1,.3,1.):
   for ia,ao in ((False,False),(False,True),(True,True)):
    add(f"deep{nl}_i{inter}_ia{ia}_ao{ao}",**{**b,"layers":layers,"leak":tuple([.15]*nl),
        "input_to_all_layers":ia,"all_layers_to_output":ao,"inter_scale":inter})
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args()
 cs=configs()[a.start:a.stop];v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,a.seed,budget=max(60,len(cs)))
 res=[];t=time.time()
 for i,(n,c) in enumerate(cs,a.start):
  z=ev.evaluate(c);p=ev.history[-1][2];res.append(dict(i=i,name=n,score=z,per=p,config=c));print(f'{i:03d} {n:39s} {z:.6f} {np.round(p,6)}',flush=True)
 print('elapsed',time.time()-t);json.dump(res,open(f'/workspace/experiments/probe5_seed{a.seed}_{a.start}_{a.stop or "end"}.json','w'),indent=2)
