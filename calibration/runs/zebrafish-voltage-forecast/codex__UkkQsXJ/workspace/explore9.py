import numpy as np
from baseline.search_api import Evaluator
v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy')
ev=Evaluator(v,s,seed=0,budget=60);rng=np.random.default_rng(90210);items=[]
for i in range(60):
 L=5 if i<48 else 4
 # Near-balanced random integer allocation, always exactly 368 units.
 raw=rng.dirichlet(np.full(L,8.0)); sizes=np.maximum(30,(raw*368).astype(int))
 while sizes.sum()>368: sizes[np.argmax(sizes)]-=1
 while sizes.sum()<368: sizes[np.argmin(sizes)]+=1
 leaks=tuple(float(x) for x in np.exp(rng.uniform(np.log(.035),np.log(.7),L)))
 c=dict(layers=tuple(int(x) for x in sizes),voltage_feedback=False,input_to_all_layers=True,
  all_layers_to_output=True,inter_scale=0,input_to_output=bool(rng.random()<.9),
  spectral_radius=float(rng.uniform(.82,1.03)),connectivity=float(np.exp(rng.uniform(np.log(.025),np.log(.22)))),
  leak=leaks,input_scale={'bias':float(np.exp(rng.uniform(np.log(.03),np.log(.3)))),
  'stimulus':float(np.exp(rng.uniform(np.log(.65),np.log(4.5))))},ridge=float(10**rng.uniform(-10.5,-7)),
  washout=int(rng.choice([0,300,700,1000,1500,2500])),readout_halflife=None)
 items.append(c)
for i,c in enumerate(items):
 sc=ev.evaluate(c);print(f'{i:02d} {sc:.6f} {np.round(ev.history[-1][2],5).tolist()} {c}',flush=True)
print('BEST',ev.best(),flush=True)
