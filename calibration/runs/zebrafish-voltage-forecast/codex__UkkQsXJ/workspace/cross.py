import numpy as np
from baseline.search_api import Evaluator
v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')

P=dict(layers=(74,74,74,73,73),voltage_feedback=False,input_to_all_layers=True,all_layers_to_output=True,inter_scale=0,readout_halflife=None)
F=dict(layers=(368,),voltage_feedback=False,readout_halflife=None)
cs=[]
def add(name,base,**kw): x=dict(base);x.update(kw);cs.append((name,x))
add('p38',P,input_to_output=True,spectral_radius=.9751142238451121,connectivity=.030854588051763814,leak=(.45784546127878056,.1516604198425067,.044645881359243,.2779710432967935,.06343280403081282),input_scale={'bias':.12418299369459748,'stimulus':1.1947949305905488},ridge=1.6723102778648208e-9,washout=1000)
add('p35',P,input_to_output=True,spectral_radius=.8202288683915362,connectivity=.1785374529199306,leak=(.6016890448301291,.2550579795178623,.5822473363411206,.03722579924032839,.03875585252735811),input_scale={'bias':.2083893464389161,'stimulus':.9763628411373245},ridge=1.3589921707888723e-11,washout=1000)
add('p43',P,input_to_output=False,spectral_radius=.9980116452939995,connectivity=.09748789334136276,leak=(.11957118344324506,.2795643521257177,.07156750958599555,.23597700065149793,.11336653708205173),input_scale={'bias':.029923752738096613,'stimulus':1.8013867354450035},ridge=1.0015374862383776e-11,washout=0)
add('p33',P,input_to_output=True,spectral_radius=.9218197608151778,connectivity=.08229858786629084,leak=(.09683136010214365,.061278532857321606,.14374779149586345,.03970175860211274,.10532940739660823),input_scale={'bias':.11485717972056046,'stimulus':3.9520933387215558},ridge=8.263663288110423e-8,washout=300)
add('p03',P,input_to_output=True,spectral_radius=.9707902255010203,connectivity=.17446955320738144,leak=(.1844568048330077,.5576779310581741,.08097752095055558,.04302207542374283,.2207984088443655),input_scale={'bias':.2343472036871118,'stimulus':1.9253585658070511},ridge=7.465404451725223e-10,washout=2500)
add('f05',F,input_to_output=True,spectral_radius=.9779845446780765,connectivity=.1396483754864222,leak=.1843670995008745,input_scale={'bias':.09915952112854916,'stimulus':4.098882835107174},ridge=1.4555188247975735e-8,washout=1500)
add('f02',F,input_to_output=True,spectral_radius=.9356121729982958,connectivity=.07722209415346953,leak=.15545761894102034,input_scale={'bias':.07363203732327193,'stimulus':4.349851161579297},ridge=8.387864810210989e-8,washout=700)
add('f21',F,input_to_output=True,spectral_radius=.8598820173471546,connectivity=.041103856474607244,leak=.08430851926458317,input_scale={'bias':.05964299319371115,'stimulus':3.961427020731568},ridge=1.6580748831077058e-10,washout=1500)

if __name__ == '__main__':
 for seed in range(5):
  ev=Evaluator(v,s,seed=seed,budget=60)
  for name,c in cs:
   sc=ev.evaluate(c);print(seed,name,f'{sc:.6f}',np.round(ev.history[-1][2],5).tolist(),flush=True)
