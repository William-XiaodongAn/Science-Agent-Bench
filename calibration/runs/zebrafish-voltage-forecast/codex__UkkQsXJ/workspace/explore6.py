import copy
import numpy as np
from baseline.search_api import Evaluator
v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy')
ev=Evaluator(v,s,seed=0,budget=60);rng=np.random.default_rng(4451)
base=dict(layers=(74,74,74,73,73),voltage_feedback=False,input_to_all_layers=True,
 all_layers_to_output=True,inter_scale=0,input_to_output=True,spectral_radius=.9751142238451121,
 connectivity=.030854588051763814,leak=(.45784546127878056,.1516604198425067,.044645881359243,.2779710432967935,.06343280403081282),
 input_scale={'bias':.12418299369459748,'stimulus':1.1947949305905488},ridge=1.6723102778648208e-9,washout=1000,readout_halflife=None)
items=[]
def add(lab,**kw): c=copy.deepcopy(base);c.update(kw);items.append((lab,c))
add('base')
for x in (.75,.8,.85,.9,.95,1.,1.05,1.1):add(f'rho{x}',spectral_radius=x)
for x in (.015,.025,.04,.06,.1,.16,.25):add(f'conn{x}',connectivity=x)
for x in (.02,.05,.1,.2,.35,.5):
 add(f'bias{x}',input_scale={'bias':x,'stimulus':base['input_scale']['stimulus']})
for x in (.3,.6,1.,1.5,2.5,4.,7.):
 add(f'stim{x}',input_scale={'bias':base['input_scale']['bias'],'stimulus':x})
for x in (1e-12,1e-11,1e-10,1e-9,1e-8,1e-7,1e-6):add(f'ridge{x}',ridge=x)
for x in (0,300,700,1500,2500):add(f'wash{x}',washout=x)
for j,x in enumerate(((.04,.07,.12,.25,.5),(.5,.25,.12,.07,.04),(.04,.1,.2,.4,.7),
                      (.7,.4,.2,.1,.04),(.05,.08,.15,.3,.6),(.6,.3,.15,.08,.05))):add(f'leaks{j}',leak=x)
assert len(items)==47,len(items)

def run(lab,c):
 sc=ev.evaluate(c);print(f'{ev.n_evaluated-1:02d} {sc:.6f} {np.round(ev.history[-1][2],5).tolist()} {lab} {c}',flush=True)
for z in items:run(*z)

# Local joint perturbations around the best one-factor result.
center=copy.deepcopy(ev.best()[0])
for j in range(13):
 c=copy.deepcopy(center)
 c['spectral_radius']=float(np.clip(c['spectral_radius']*np.exp(rng.normal(0,.08)),.7,1.2))
 c['connectivity']=float(np.clip(c['connectivity']*np.exp(rng.normal(0,.35)),.01,.4))
 c['leak']=tuple(float(np.clip(x*np.exp(rng.normal(0,.25)),.02,.9)) for x in c['leak'])
 c['input_scale']={'bias':float(np.clip(c['input_scale']['bias']*np.exp(rng.normal(0,.35)),.01,.8)),
                   'stimulus':float(np.clip(c['input_scale']['stimulus']*np.exp(rng.normal(0,.35)),.2,10))}
 c['ridge']=float(np.clip(c['ridge']*np.exp(rng.normal(0,1.)),1e-13,1e-5))
 run(f'mut{j}',c)
print('BEST',ev.best(),flush=True)
