#!/usr/bin/env python3
import argparse,json,sys,time,itertools
import numpy as np
sys.path.insert(0,"/workspace")
from baseline.search_api import Evaluator

def configs():
 out=[]
 def add(name,**kw):out.append((name,kw))
 b=dict(layers=(368,),voltage_feedback=True,input_to_output=True,leak=.15,spectral_radius=.9,
        input_scale={"bias":.03,"voltage":0.,"stimulus":5.},ridge=1e-3,washout=1000,feedback_clip=(0.,1.))
 for rr in (1e-7,1e-6,1e-5,1e-4,3e-4,1e-3,3e-3,.01,.03,.1,.3,1.):add(f"r{rr}",**{**b,"ridge":rr})
 for sr,ll in itertools.product((.8,.85,.88,.9,.92,.95,1.,1.05),(.05,.1,.15,.2,.3,.5)):
  add(f"sr{sr}_l{ll}",**{**b,"spectral_radius":sr,"leak":ll})
 archs=[((184,184),(.08,.3)),((184,184),(.15,.4)),((123,123,122),(.05,.15,.4)),((123,123,122),(.1,.2,.5)),((92,92,92,92),(.04,.1,.22,.55))]
 for layers,leaks in archs:
  for rr in (1e-4,3e-4,1e-3,3e-3,.01,.03):
   for vs in (0.,.001,.01,.03,.1):
    add(f"par{len(layers)}_r{rr}_v{vs}",**{**b,"layers":layers,"leak":leaks,"ridge":rr,"input_scale":{"bias":.03,"voltage":vs,"stimulus":5.},"input_to_all_layers":True,"all_layers_to_output":True,"inter_scale":0})
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args()
 cs=configs()[a.start:a.stop];v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,a.seed,budget=max(60,len(cs)))
 res=[];t=time.time()
 for i,(n,c) in enumerate(cs,a.start):
  z=ev.evaluate(c);p=ev.history[-1][2];res.append(dict(i=i,name=n,score=z,per=p,config=c));print(f'{i:03d} {n:28s} {z:.6f} {np.round(p,6)}',flush=True)
 print('elapsed',time.time()-t);json.dump(res,open(f'/workspace/experiments/probe_fb_seed{a.seed}_{a.start}_{a.stop or "end"}.json','w'),indent=2)
