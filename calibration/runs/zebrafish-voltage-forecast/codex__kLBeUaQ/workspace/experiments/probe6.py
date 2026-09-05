#!/usr/bin/env python3
import argparse,json,sys,time,itertools
import numpy as np
sys.path.insert(0,"/workspace")
from baseline.search_api import Evaluator

def configs():
 out=[]
 def add(name,**kw):out.append((name,kw))
 b=dict(layers=(368,),voltage_feedback=True,input_to_output=False,leak=.15,spectral_radius=.9,
        input_scale={"bias":.03,"voltage":.01,"stimulus":5.},ridge=1e-8,washout=1000,feedback_clip=(0.,1.))
 for vs,rr in itertools.product((0.,1e-5,1e-4,.001,.003,.01,.03,.1,.3),(1e-9,1e-8,1e-7,1e-6,1e-5,1e-4,1e-3)):
  add(f"v{vs}_r{rr}",**{**b,"input_scale":{"bias":.03,"voltage":vs,"stimulus":5.},"ridge":rr})
 for sr,ll in itertools.product((.85,.88,.9,.92,.94,1.),(.08,.12,.15,.18,.22,.3)):
  add(f"sr{sr}_l{ll}",**{**b,"spectral_radius":sr,"leak":ll})
 for clip in ((-.1,1.1),(0.,1.),(.0,.95),(.001,.98),(.0,.9)):
  add(f"clip{clip}",**{**b,"feedback_clip":clip})
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args()
 cs=configs()[a.start:a.stop];v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,a.seed,budget=max(60,len(cs)))
 res=[];t=time.time()
 for i,(n,c) in enumerate(cs,a.start):
  z=ev.evaluate(c);p=ev.history[-1][2];res.append(dict(i=i,name=n,score=z,per=p,config=c));print(f'{i:03d} {n:26s} {z:.6f} {np.round(p,6)}',flush=True)
 print('elapsed',time.time()-t);json.dump(res,open(f'/workspace/experiments/probe6_seed{a.seed}_{a.start}_{a.stop or "end"}.json','w'),indent=2)
