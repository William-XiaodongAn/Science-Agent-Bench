import numpy as np
from baseline.search_api import Evaluator
v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy')
ev=Evaluator(v,s,seed=0,budget=60);rng=np.random.default_rng(70707);items=[]
for i in range(30):
 lo=float(np.exp(rng.uniform(np.log(.005),np.log(.08)))); hi=float(np.exp(rng.uniform(np.log(max(.12,lo*3)),np.log(1.0))))
 c=dict(layers=(368,),voltage_feedback=False,input_to_output=True,
  spectral_radius=float(rng.uniform(.78,1.08)),connectivity=float(np.exp(rng.uniform(np.log(.02),np.log(.25)))),
  leak=(lo,hi),input_scale={'bias':float(np.exp(rng.uniform(np.log(.02),np.log(.3)))),
  'stimulus':float(np.exp(rng.uniform(np.log(.5),np.log(5.))))},ridge=float(10**rng.uniform(-11,-6)),
  washout=int(rng.choice([0,300,700,1000,1500,2500])),readout_halflife=None)
 items.append(('range1',c))
for i in range(30):
 lo=float(np.exp(rng.uniform(np.log(.005),np.log(.08)))); hi=float(np.exp(rng.uniform(np.log(max(.12,lo*3)),np.log(1.0))))
 c=dict(layers=(74,74,74,73,73),voltage_feedback=False,input_to_all_layers=True,all_layers_to_output=True,
  inter_scale=0,input_to_output=True,spectral_radius=float(rng.uniform(.78,1.08)),
  connectivity=float(np.exp(rng.uniform(np.log(.02),np.log(.25)))),leak=(lo,hi),
  input_scale={'bias':float(np.exp(rng.uniform(np.log(.02),np.log(.3)))),
  'stimulus':float(np.exp(rng.uniform(np.log(.5),np.log(5.))))},ridge=float(10**rng.uniform(-11,-6)),
  washout=int(rng.choice([0,300,700,1000,1500,2500])),readout_halflife=None)
 items.append(('range5',c))
for i,(lab,c) in enumerate(items):
 sc=ev.evaluate(c);print(f'{i:02d} {sc:.6f} {np.round(ev.history[-1][2],5).tolist()} {lab} {c}',flush=True)
print('BEST',ev.best(),flush=True)
