import sys, json; sys.path.insert(0,'/workspace/baseline')
import numpy as np, esn, causal_runner
v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
cfg=json.loads(sys.argv[1]); seed=int(sys.argv[2]) if len(sys.argv)>2 else 0
o=int(sys.argv[3]) if len(sys.argv)>3 else 8227; H=4113
f=esn.Forecaster(seed, **cfg); pred=causal_runner.rollout(f, v[:o], s[:o], s[o:o+H]); tgt=v[o:o+H]
print('train rmse', f.train_rmse, 'dev rmse', np.sqrt(np.mean((pred-tgt)**2)))
st=np.where(s[o:o+H]>0)[0]
def apd(x,i,th=0.2):
    seg=x[i:i+400]; ab=np.where(seg>th)[0]
    if len(ab)==0: return -1
    e=ab[0]
    while e+1<len(seg) and seg[e+1]>th: e+=1
    return e+1
rows=[]
for k in range(len(st)-1):
    i=st[k]; n=st[k+1]-i
    e=np.sqrt(np.mean((pred[i:i+n]-tgt[i:i+n])**2))
    rows.append((n, apd(tgt,i), apd(pred,i), round(e,3), round(pred[i:i+n].max(),2)))
print('ISI, APDtrue, APDpred, beatRMSE, peak')
for r in rows: print(r)
at=np.array([r[1] for r in rows]); ap=np.array([r[2] for r in rows])
print('APD pred corr', np.corrcoef(at,ap)[0,1], 'rmse APD', np.sqrt(np.mean((at-ap)**2)), 'sd APD', at.std())
# error by phase within beat
ph=np.zeros(H); 
for k in range(len(st)-1): ph[st[k]:st[k+1]]=np.arange(st[k+1]-st[k])
for lo in range(0,160,20):
    m=(ph>=lo)&(ph<lo+20); print('phase',lo, np.sqrt(np.mean((pred[m]-tgt[m])**2)).round(3))
