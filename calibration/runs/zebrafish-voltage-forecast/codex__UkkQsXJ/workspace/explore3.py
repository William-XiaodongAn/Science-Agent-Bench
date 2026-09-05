import numpy as np
from baseline.search_api import Evaluator

v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
ev=Evaluator(v,s,seed=0,budget=60); items=[]
def add(label,**kw):
    b=dict(layers=(368,),voltage_feedback=True,spectral_radius=.5,leak=.3,
           input_scale=.1,ridge=1e-3)
    b.update(kw); items.append((label,b))

for rho in (.1,.3,.5,.7,.9):
  for leak in (.1,.2,.3,.5,.8): add(f'rho={rho} leak={leak}',spectral_radius=rho,leak=leak)
for direct in (True,False):
  for ridge in (1e-8,1e-6,1e-4,1e-3,1e-2,1e-1):
    add(f'direct={direct} ridge={ridge}',input_to_output=direct,ridge=ridge)
for vs in (.01,.03,.1,.3):
  for ss in (.1,1.,5.):
    add(f'vscale={vs} sscale={ss}',input_scale={'bias':.1,'voltage':vs,'stimulus':ss})
for clip in ((0,1),(0,.95),(-.01,1.01),(.01,.9)):
  add(f'clip={clip}',feedback_clip=clip)

for ina,outa,inter,leaks in [
    (False,False,.03,(.1,.5)),(False,True,.1,(.1,.5)),
    (True,False,.1,(.1,.5)),(True,True,.1,(.1,.5)),
    (True,True,.3,(.1,.5)),(True,True,1.,(.1,.5)),
    (True,True,.3,(.3,.3))]:
  add(f'deep inall={ina} outall={outa} inter={inter} leaks={leaks}',
      layers=(184,184),input_to_all_layers=ina,all_layers_to_output=outa,
      inter_scale=inter,leak=leaks)

assert len(items)==60,len(items)
for i,(lab,cfg) in enumerate(items):
  sc=ev.evaluate(cfg)
  print(f'{i:02d} {sc:.6f} {np.round(ev.history[-1][2],5).tolist()} {lab}',flush=True)
print('BEST',ev.best(),flush=True)
