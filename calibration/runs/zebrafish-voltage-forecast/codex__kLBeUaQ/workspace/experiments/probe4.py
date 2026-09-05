#!/usr/bin/env python3
import argparse,json,sys,time
import numpy as np
sys.path.insert(0,"/workspace")
from baseline.search_api import Evaluator

def configs():
 out=[]
 def add(name,**kw):out.append((name,kw))
 b=dict(layers=(368,),voltage_feedback=False,leak=.16,spectral_radius=.9,
        input_scale={"bias":.01,"stimulus":5.},ridge=1e-8)
 # Temporal locality of the readout.
 for hl in (None,300,500,750,1000,1500,2000,3000,4000,6000,8000,12000): add(f"hl_{hl}",**{**b,"readout_halflife":hl})
 # Local geometry around the strong flat solution.
 for sr in (.75,.8,.83,.86,.88,.9,.92,.94,.96,.98,1.,1.03): add(f"sr_{sr}",**{**b,"spectral_radius":sr})
 for ll in (.06,.08,.1,.12,.14,.16,.18,.2,.22,.25,.28): add(f"leak_{ll}",**{**b,"leak":ll})
 for bs in (0.,.001,.003,.01,.03,.1):
  for ss in (2.,5.,10.,20.): add(f"scale_{bs}_{ss}",**{**b,"input_scale":{"bias":bs,"stimulus":ss}})
 for cc in (.01,.03,.05,.1,.2,.4,.7,1.): add(f"conn_{cc}",**{**b,"connectivity":cc})
 for rr in (0.,1e-12,1e-10,1e-9,1e-8,1e-7,1e-6,1e-5):add(f"ridge_{rr}",**{**b,"ridge":rr})
 for io in (False,True):
  for wo in (0,250,500,1000,2000,4000):add(f"io_{io}_wo_{wo}",**{**b,"input_to_output":io,"washout":wo})
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args()
 cs=configs()[a.start:a.stop];v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,a.seed,budget=max(60,len(cs)))
 res=[];t=time.time()
 for i,(n,c) in enumerate(cs,a.start):
  try:z=ev.evaluate(c);p=ev.history[-1][2]
  except Exception as e:z=float('inf');p=[str(e)]
  res.append(dict(i=i,name=n,score=z,per=p,config=c));print(f'{i:03d} {n:24s} {z:.6f} {p if isinstance(p,list) else np.round(p,6)}',flush=True)
 print('elapsed',time.time()-t);json.dump(res,open(f'/workspace/experiments/probe4_seed{a.seed}_{a.start}_{a.stop or "end"}.json','w'),indent=2)
