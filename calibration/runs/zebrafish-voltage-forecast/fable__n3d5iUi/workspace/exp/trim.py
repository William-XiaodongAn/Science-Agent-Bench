import sys, json; sys.path.insert(0,'/workspace/baseline')
import numpy as np, esn, causal_runner
from multiprocessing import Pool
v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
H=4113; ORIG=(8227,10284,12341)
stim_idx=np.where(s>0)[0]; isi=np.diff(stim_idx)
bad=stim_idx[np.where(isi>=170)[0]]  # onset of outlier beats
mask=np.ones(len(v),bool)
for b in bad:
    k=np.searchsorted(stim_idx,b); end=stim_idx[min(k+3,len(stim_idx)-1)]; mask[b:end]=False
def run(args):
    cfg,seed=args; out=[]
    for o in ORIG:
        f=esn.Forecaster(seed,**cfg); p=causal_runner.rollout(f,v[:o],s[:o],s[o:o+H]); t=v[o:o+H]; m=mask[o:o+H]
        out.append((np.sqrt(np.mean((p-t)**2)), np.sqrt(np.mean((p[m]-t[m])**2))))
    return cfg,seed,out
if __name__=='__main__':
    C=json.load(open(sys.argv[1])); seeds=[int(x) for x in sys.argv[2].split(',')]
    with Pool(4) as pool: res=pool.map(run,[(c,sd) for c in C for sd in seeds])
    agg={}
    for cfg,sd,out in res: agg.setdefault(json.dumps(cfg,sort_keys=True),[]).append(out)
    rows=[]
    for k,lst in agg.items():
        a=np.array(lst)  # seeds x origins x 2
        rows.append((a[:,:,0].mean(), a[:,:,1].mean(), a[:,:,0].mean(0), a[:,:,1].mean(0), k))
    rows.sort(key=lambda r:r[1])
    for full,trim,po,pt,k in rows: print(f"full {full:.4f} trim {trim:.4f} | per-origin full {np.round(po,4)} trim {np.round(pt,4)} | {k}")
