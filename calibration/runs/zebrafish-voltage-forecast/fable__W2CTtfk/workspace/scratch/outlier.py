import sys, os, json; os.environ["OMP_NUM_THREADS"]="1"
sys.path.insert(0,'/workspace/baseline'); sys.path.insert(0,'/workspace')
import numpy as np
from esn import Forecaster
import causal_runner
from multiprocessing import Pool
v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
st=np.where(s>0)[0]
def apd_of(seg):
    up=np.argmax(seg>0.5); after=np.where(seg[up:]<0.2)[0]; return up+(after[0] if len(after) else len(seg)-up)
D={}
for sd in range(5):
    c=json.load(open(f'/workspace/scratch/full_seed{sd}.json'))['config']; c['layers']=tuple(c['layers']); c['feedback_clip']=tuple(c['feedback_clip'])
    if isinstance(c['leak'],list): c['leak']=tuple(c['leak'])
    D[('returned',sd)]=c
D[('flat_range',0)]=dict(layers=(368,), voltage_feedback=False, ridge=1e-8, leak=(0.03,0.3), input_scale=dict(bias=0.1, stimulus=5.0))
D[('bank2',0)]=dict(layers=(184,184), voltage_feedback=False, ridge=1e-8, leak=(0.2,0.05), inter_scale=0.0, input_to_all_layers=True, all_layers_to_output=True, input_scale=dict(bias=0.1, stimulus=5.0))
D[('default',0)]=dict(layers=(368,))
H=4113
def job(a):
    key,o=a; name,sd=key
    f=Forecaster(sd, **D[key]); p=causal_runner.rollout(f, v[:o], s[:o], s[o:o+H]); tr=v[o:o+H]
    ws=[x-o for x in st if o<=x<o+H]; rows=[]
    for i,x in enumerate(ws[:-1]):
        e=ws[i+1]; rows.append((x, apd_of(tr[x:e]), apd_of(p[x:e]), float(np.sum((p[x:e]-tr[x:e])**2))))
    rows=np.array(rows); tot=float(np.sum((p-tr)**2))
    top=rows[np.argsort(-rows[:,3])[:3]]
    return key,o,np.sqrt(tot/H), top, tot
with Pool(4) as p:
    out=list(p.imap(job, [(k,o) for k in D for o in (8227,10284,12341)]))
for key,o,r,top,tot in out:
    desc="; ".join(f"t={int(x)+o} APD {int(a)}->pred {int(b)} share {ss/tot:.0%}" for x,a,b,ss in top)
    print(f'{key[0]:10s} seed {key[1]} origin {o}: rmse {r:.4f} | worst beats: {desc}')
