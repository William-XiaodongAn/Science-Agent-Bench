#!/usr/bin/env python3
import argparse,json,sys,time
import numpy as np
sys.path.insert(0,"/workspace")
from baseline.search_api import Evaluator

def configs():
 out=[]
 def add(name,**kw): out.append((name,kw))
 base=dict(layers=(368,),voltage_feedback=False,leak=.2,spectral_radius=.9,
           input_scale={"bias":.01,"stimulus":5.},ridge=1e-3)
 for sr in (0.,.05,.1,.2,.3,.5,.7,.9,1.05,1.2): add(f"flat_sr{sr}",**{**base,"spectral_radius":sr})
 for leak in (.02,.04,.06,.08,.1,.13,.16,.2,.25,.3,.4,.5,.7,1.): add(f"flat_l{leak}",**{**base,"leak":leak})
 for rr in (1e-8,1e-7,1e-6,1e-5,1e-4,3e-4,1e-3,3e-3,1e-2,.03,.1): add(f"flat_r{rr}",**{**base,"ridge":rr})
 for lo,hi in ((.001,.1),(.001,.3),(.001,1),(.003,.3),(.003,1),(.01,.3),(.01,1),(.03,1),(.05,1),(.1,1)):
  add(f"hetero_{lo}_{hi}",**{**base,"leak":(lo,hi)})
 # Parallel banks: each bank sees pulse/bias and readout sees all states.
 archs=[
  ((184,184),(.05,.25)),((184,184),(.1,.3)),((184,184),(.15,.4)),
  ((123,123,122),(.03,.12,.4)),((123,123,122),(.05,.2,.6)),((123,123,122),(.08,.25,.8)),
  ((92,92,92,92),(.02,.07,.2,.6)),((92,92,92,92),(.04,.1,.25,.7)),
  ((74,74,74,73,73),(.02,.05,.12,.3,.8)),((74,74,74,73,73),(.04,.08,.16,.35,.8))]
 for layers,leaks in archs:
  add(f"par_{len(layers)}_{leaks}",**{**base,"layers":layers,"leak":leaks,
      "input_to_all_layers":True,"all_layers_to_output":True,"inter_scale":0})
 # Cascades, optionally with direct input and all states exposed.
 for layers in ((184,184),(123,123,122),(92,92,92,92)):
  leaks=tuple([.2]*len(layers))
  for ia in (False,True):
   for ao in (False,True):
    add(f"deep{len(layers)}_ia{ia}_ao{ao}",**{**base,"layers":layers,"leak":leaks,
        "input_to_all_layers":ia,"all_layers_to_output":ao,"inter_scale":.1})
 return out

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,default=0);ap.add_argument('--start',type=int,default=0);ap.add_argument('--stop',type=int);a=ap.parse_args()
 cs=configs()[a.start:a.stop];v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,a.seed,budget=max(60,len(cs)))
 res=[];t=time.time()
 for i,(n,c) in enumerate(cs,a.start):
  z=ev.evaluate(c);p=ev.history[-1][2];res.append(dict(i=i,name=n,score=z,per=p,config=c));print(f'{i:02d} {n:34s} {z:.6f} {np.round(p,6)}',flush=True)
 print('elapsed',time.time()-t);json.dump(res,open(f'/workspace/experiments/probe3_seed{a.seed}_{a.start}_{a.stop or "end"}.json','w'),indent=2)
