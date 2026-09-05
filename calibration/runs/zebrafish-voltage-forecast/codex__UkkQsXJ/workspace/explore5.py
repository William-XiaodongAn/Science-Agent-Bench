import numpy as np
from baseline.search_api import Evaluator
v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
ev=Evaluator(v,s,seed=0,budget=60); rng=np.random.default_rng(99173); items=[]

for i in range(30):
    cfg=dict(layers=(368,),voltage_feedback=False,input_to_output=bool(rng.random()<.8),
             spectral_radius=float(rng.uniform(.82,1.12)),
             connectivity=float(np.exp(rng.uniform(np.log(.02),np.log(.18)))),
             leak=float(np.exp(rng.uniform(np.log(.055),np.log(.24)))),
             input_scale={'bias':float(np.exp(rng.uniform(np.log(.02),np.log(.25)))),
                          'stimulus':float(np.exp(rng.uniform(np.log(.6),np.log(5.0))))},
             ridge=float(10**rng.uniform(-12,-7)),
             washout=int(rng.choice([0,300,700,1000,1500,2500])),readout_halflife=None)
    items.append(('flat',cfg))
for i in range(30):
    leaks=tuple(np.exp(rng.uniform(np.log(.035),np.log(.7),5)))
    cfg=dict(layers=(74,74,74,73,73),voltage_feedback=False,
             input_to_all_layers=True,all_layers_to_output=True,inter_scale=0,
             input_to_output=bool(rng.random()<.8),
             spectral_radius=float(rng.uniform(.8,1.15)),
             connectivity=float(np.exp(rng.uniform(np.log(.025),np.log(.3)))),
             leak=leaks,
             input_scale={'bias':float(np.exp(rng.uniform(np.log(.02),np.log(.35)))),
                          'stimulus':float(np.exp(rng.uniform(np.log(.5),np.log(5.0))))},
             ridge=float(10**rng.uniform(-12,-7)),
             washout=int(rng.choice([0,300,700,1000,1500,2500])),readout_halflife=None)
    items.append(('p5',cfg))
for i,(lab,cfg) in enumerate(items):
    sc=ev.evaluate(cfg)
    print(f'{i:02d} {sc:.6f} {np.round(ev.history[-1][2],5).tolist()} {lab} {cfg}',flush=True)
print('BEST',ev.best(),flush=True)
