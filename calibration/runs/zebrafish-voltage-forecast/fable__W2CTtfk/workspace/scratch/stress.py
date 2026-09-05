import sys, os, json; os.environ["OMP_NUM_THREADS"]="1"
sys.path.insert(0,'/workspace/baseline'); sys.path.insert(0,'/workspace')
import numpy as np
from esn import Forecaster
from multiprocessing import Pool
v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
def nf(ss, rd, **kw):
    c=dict(layers=(368,), voltage_feedback=False, ridge=rd, input_scale=dict(bias=0.1, stimulus=ss)); c.update(kw); return c
D={'g5_r1e-8':nf(5.0,1e-8,leak=(0.03,0.3)),'g20_r1e-7':nf(20.0,1e-7,leak=(0.03,0.3)),'g20_r3e-7':nf(20.0,3e-7,leak=(0.03,0.3)),
   'g50_r1e-7':nf(50.0,1e-7,leak=(0.03,0.3)),'g50_r1e-6':nf(50.0,1e-6,leak=(0.03,0.3)),'g5_r1e-6':nf(5.0,1e-6,leak=(0.03,0.3)),
   'bank2_g20':nf(20.0,1e-7,layers=(184,184), leak=(0.2,0.05), inter_scale=0.0, input_to_all_layers=True, all_layers_to_output=True)}
def job(a):
    name,sd=a; f=Forecaster(sd, **D[name]); f.warmup(v,s); W=np.abs(f.Wout)
    out=[name,sd,f.train_rmse,W.mean(),W.max()]
    # steady-state stress: regular schedule, skip the first 1000 ms transient; also a 'training-like' replay
    for iv in (95,120,200):
        st=np.zeros(4000); st[60::iv]=0.2; g=Forecaster(sd, **D[name]); g.warmup(v,s); q=np.array([g.step(x) for x in st])
        out.append((q[1000:].min(),q[1000:].max(), q[:1000].min(), q[:1000].max()))
    return out
with Pool(4) as p:
    for o in p.imap(job, [(n,sd) for n in D for sd in (0,4)]):
        name,sd,tr,wm,wx,a,b,c=o
        print(f'{name:10s} seed {sd}: train {tr:.4f} |W| mean {wm:7.1f} max {wx:8.1f} | steady-state range @95ms [{a[0]:.2f},{a[1]:.2f}] @120 [{b[0]:.2f},{b[1]:.2f}] @200 [{c[0]:.2f},{c[1]:.2f}] | transient min {min(a[2],b[2],c[2]):.2f}')
