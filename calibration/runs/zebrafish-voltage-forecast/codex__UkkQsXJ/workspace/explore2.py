import numpy as np
from baseline.search_api import Evaluator

v = np.load('/workspace/data/train_data.npy')
s = np.load('/workspace/data/train_stim.npy')
ev = Evaluator(v, s, seed=0, budget=60)
items=[]

def add(label, **kw):
    base=dict(layers=(368,), voltage_feedback=False, spectral_radius=.9,
              leak=.1, input_scale=.1, ridge=1e-7)
    base.update(kw); items.append((label,base))

for half in (None, 500, 1000, 2000, 4000):
    for ridge in (1e-10,1e-8,1e-7,1e-6,1e-4):
        add(f'half={half} ridge={ridge}',readout_halflife=half,ridge=ridge)

for rho in (.6,.75,.9,1.05):
    for leak in (.04,.08,.15):
        add(f'rho={rho} leak={leak}',spectral_radius=rho,leak=leak)

for bs in (.03,.1,.3):
    for ss in (.03,.1,.3,1.0):
        add(f'bias={bs} stim={ss}',input_scale={'bias':bs,'stimulus':ss})

for conn in (.03,.05,.2): add(f'conn={conn}',connectivity=conn)
for wash in (0,500,2000): add(f'wash={wash}',washout=wash)
for lr in ((.005,.2),(.01,.5),(.03,1.0)):
    add(f'leakrange={lr}',leak=lr)
add('no direct',input_to_output=False)
add('parallel3',layers=(123,123,122),input_to_all_layers=True,
    all_layers_to_output=True,inter_scale=0,leak=(.05,.12,.3))

assert len(items)==60,len(items)
for i,(label,cfg) in enumerate(items):
    sc=ev.evaluate(cfg)
    print(f'{i:02d} {sc:.6f} {np.round(ev.history[-1][2],5).tolist()} {label}',flush=True)
print('BEST',ev.best(),flush=True)
