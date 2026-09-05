import numpy as np
from baseline.search_api import Evaluator

v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
ev=Evaluator(v,s,seed=0,budget=60); rng=np.random.default_rng(8128); items=[]

for i in range(60):
    typ = ('flat','parallel2','parallel3','parallel5','deep2','deep3')[i % 6]
    if typ=='flat': layers=(368,)
    elif typ.endswith('2'): layers=(184,184)
    elif typ.endswith('3'): layers=(123,123,122)
    else: layers=(74,74,74,73,73)
    parallel=typ.startswith('parallel')
    L=len(layers)
    leaks=tuple(np.exp(rng.uniform(np.log(.025),np.log(.7),L))) if L>1 else float(np.exp(rng.uniform(np.log(.035),np.log(.3))))
    cfg=dict(layers=layers,voltage_feedback=False,
             input_to_all_layers=(parallel or (L>1 and rng.random()<.7)),
             all_layers_to_output=(L>1),
             input_to_output=bool(rng.random()<.75),
             spectral_radius=float(rng.uniform(.75,1.25)),
             connectivity=float(np.exp(rng.uniform(np.log(.025),np.log(.3)))),
             leak=leaks,
             input_scale={'bias':float(np.exp(rng.uniform(np.log(.02),np.log(.5)))),
                          'stimulus':float(np.exp(rng.uniform(np.log(.03),np.log(3.0))))},
             inter_scale=(0.0 if parallel else float(np.exp(rng.uniform(np.log(.02),np.log(1.5))))),
             ridge=float(10**rng.uniform(-11,-4)),
             washout=int(rng.choice([0,300,700,1000,1500,2500])),
             readout_halflife=(None if rng.random()<.8 else int(rng.choice([1000,2000,4000,8000]))))
    items.append((typ,cfg))

for i,(lab,cfg) in enumerate(items):
    sc=ev.evaluate(cfg)
    print(f'{i:02d} {sc:.6f} {np.round(ev.history[-1][2],5).tolist()} {lab} {cfg}',flush=True)
print('BEST',ev.best(),flush=True)
