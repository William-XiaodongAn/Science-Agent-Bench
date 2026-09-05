import copy,numpy as np
from baseline.search_api import Evaluator
v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,0,60);items=[]
P=dict(layers=(74,74,74,73,73),voltage_feedback=False,input_to_all_layers=True,all_layers_to_output=True,inter_scale=0,input_to_output=True)
p38=dict(P,spectral_radius=.9751142238451121,connectivity=.030854588051763814,leak=(.45784546127878056,.1516604198425067,.044645881359243,.2779710432967935,.06343280403081282),input_scale={'bias':.1,'stimulus':1.1947949305905488},ridge=1.6723102778648208e-9,washout=1000)
p33=dict(P,spectral_radius=.9218197608151778,connectivity=.08229858786629084,leak=(.09683136010214365,.061278532857321606,.14374779149586345,.03970175860211274,.10532940739660823),input_scale={'bias':.11485717972056046,'stimulus':3.9520933387215558},ridge=8.263663288110423e-8,washout=300)
f05=dict(layers=(368,),voltage_feedback=False,input_to_output=True,spectral_radius=.9779845446780765,connectivity=.1396483754864222,leak=.1843670995008745,input_scale={'bias':.09915952112854916,'stimulus':4.098882835107174},ridge=1.4555188247975735e-8,washout=1500)
halves=(250,500,800,1200,2000,4000,8000)
for h in halves:
 for r in (1e-11,1e-10,1e-9,1e-8,1e-7,1e-6):
  c=copy.deepcopy(p38);c.update(readout_halflife=h,ridge=r);items.append((f'p38 h{h} r{r}',c))
for name,b in [('p33',p33),('f05',f05)]:
 for h in (250,500,1000,2000,4000,8000,None):
  c=copy.deepcopy(b);c['readout_halflife']=h;items.append((f'{name} h{h}',c))
# Add the unweighted p38 family explicitly.
for r in (1e-10,1e-9,1e-8,1e-7):
 c=copy.deepcopy(p38);c.update(readout_halflife=None,ridge=r);items.append((f'p38 hNone r{r}',c))
assert len(items)==60,len(items)
for i,(lab,c) in enumerate(items):
 sc=ev.evaluate(c);print(f'{i:02d} {sc:.6f} {np.round(ev.history[-1][2],5).tolist()} {lab}',flush=True)
print('BEST',ev.best(),flush=True)
