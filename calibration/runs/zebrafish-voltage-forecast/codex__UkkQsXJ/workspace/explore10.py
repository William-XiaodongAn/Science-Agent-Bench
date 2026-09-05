import copy,numpy as np
from baseline.search_api import Evaluator
v=np.load('/workspace/data/train_data.npy');s=np.load('/workspace/data/train_stim.npy');ev=Evaluator(v,s,0,60);items=[]
P=dict(layers=(74,74,74,73,73),voltage_feedback=False,input_to_all_layers=True,all_layers_to_output=True,input_to_output=True,readout_halflife=None)
bases=[
 dict(P,spectral_radius=.9751142238451121,connectivity=.030854588051763814,leak=(.45784546127878056,.1516604198425067,.044645881359243,.2779710432967935,.06343280403081282),input_scale={'bias':.1,'stimulus':1.1947949305905488},ridge=1.6723102778648208e-9,washout=1000),
 dict(P,spectral_radius=.8202288683915362,connectivity=.1785374529199306,leak=(.6016890448301291,.2550579795178623,.5822473363411206,.03722579924032839,.03875585252735811),input_scale={'bias':.2083893464389161,'stimulus':.9763628411373245},ridge=1.3589921707888723e-11,washout=1000),
 dict(P,spectral_radius=.9218197608151778,connectivity=.08229858786629084,leak=(.09683136010214365,.061278532857321606,.14374779149586345,.03970175860211274,.10532940739660823),input_scale={'bias':.11485717972056046,'stimulus':3.9520933387215558},ridge=8.263663288110423e-8,washout=300),
 dict(P,spectral_radius=.9707902255010203,connectivity=.17446955320738144,leak=(.1844568048330077,.5576779310581741,.08097752095055558,.04302207542374283,.2207984088443655),input_scale={'bias':.2343472036871118,'stimulus':1.9253585658070511},ridge=7.465404451725223e-10,washout=2500),
 dict(P,input_to_output=False,spectral_radius=.9980116452939995,connectivity=.09748789334136276,leak=(.11957118344324506,.2795643521257177,.07156750958599555,.23597700065149793,.11336653708205173),input_scale={'bias':.029923752738096613,'stimulus':1.8013867354450035},ridge=1.0015374862383776e-11,washout=0),
]
for bi,b in enumerate(bases):
 for inter in (0,.001,.003,.01,.03,.1,.3,.7,1.,2.):
  c=copy.deepcopy(b);c['inter_scale']=inter;items.append((f'b{bi} inter{inter}',c))
# Variants that expose only the final transformed layer.
for inter in (.001,.003,.01,.03,.1,.3,.7,1.,2.):
 c=copy.deepcopy(bases[0]);c.update(inter_scale=inter,all_layers_to_output=False);items.append((f'last inter{inter}',c))
# A serial cascade receiving the stimulus only at layer zero.
c=copy.deepcopy(bases[0]);c.update(inter_scale=.3,input_to_all_layers=False);items.append(('serial-only',c))
assert len(items)==60
for i,(lab,c) in enumerate(items):
 sc=ev.evaluate(c);print(f'{i:02d} {sc:.6f} {np.round(ev.history[-1][2],5).tolist()} {lab}',flush=True)
print('BEST',ev.best(),flush=True)
