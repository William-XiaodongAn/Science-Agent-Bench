#!/usr/bin/env python3
import argparse,json,sys,time
import numpy as np
sys.path.insert(0,"/workspace")
from baseline.search_api import Evaluator

def configs():
 out=[]
 def add(name,**kw): out.append((name,kw))
 base=dict(layers=(368,),voltage_feedback=True,leak=.35,spectral_radius=.9,input_scale=.1,ridge=1e-3)
 for sr in (0.,.1,.3,.5,.7,.9,1.1,1.3,1.5): add(f"fb_sr{sr}",**{**base,"spectral_radius":sr})
 for sc in (.005,.01,.03,.05,.1,.2,.4,.7,1.,2.): add(f"fb_scale{sc}",**{**base,"input_scale":sc})
 for ridge in (1e-8,1e-7,1e-6,1e-5,1e-4,1e-3,1e-2,.1,1.): add(f"fb_ridge{ridge}",**{**base,"ridge":ridge})
 for vs in (.005,.01,.03,.05,.1,.2,.5,1.):
  for ss in (0.1,1.,5.):
   add(f"fb_v{vs}_s{ss}",**{**base,"input_scale":{"bias":.1,"voltage":vs,"stimulus":ss}})
 # Pure stimulus-driven reservoirs need a visible impulse.
 nf=dict(layers=(368,),voltage_feedback=False,leak=.2,spectral_radius=.9,input_scale=.1,ridge=1e-3)
 for bs in (.01,.05,.1,.3,1.):
  for ss in (.1,1.,5.,10.): add(f"nf_b{bs}_s{ss}",**{**nf,"input_scale":{"bias":bs,"stimulus":ss}})
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args()
 cs=configs()[a.start:a.stop];v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,a.seed,budget=max(60,len(cs)))
 res=[];t=time.time()
 for i,(n,c) in enumerate(cs,a.start):
  z=ev.evaluate(c);p=ev.history[-1][2];res.append(dict(i=i,name=n,score=z,per=p,config=c));print(f'{i:02d} {n:24s} {z:.6f} {np.round(p,6)}',flush=True)
 print('elapsed',time.time()-t)
 json.dump(res,open(f'/workspace/experiments/probe2_seed{a.seed}_{a.start}_{a.stop or "end"}.json','w'),indent=2)
