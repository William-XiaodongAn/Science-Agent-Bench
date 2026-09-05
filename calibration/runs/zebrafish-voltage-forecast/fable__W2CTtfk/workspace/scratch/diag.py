import sys, os; os.environ["OMP_NUM_THREADS"]="4"
sys.path.insert(0,'/workspace/baseline'); sys.path.insert(0,'/workspace')
import numpy as np, json
from esn import Forecaster
import causal_runner
v=np.load('/workspace/data/train_data.npy'); s=np.load('/workspace/data/train_stim.npy')
cfg=json.loads(sys.argv[1]) if len(sys.argv)>1 else dict(layers=(368,), voltage_feedback=False, leak=0.15, ridge=1e-8, input_scale=dict(bias=0.1, stimulus=5.0))
H=4113
def apd_of(seg):
    up=np.argmax(seg>0.5); after=np.where(seg[up:]<0.2)[0]; return up+(after[0] if len(after) else len(seg)-up)
for o in (8227,10284,12341):
    f=Forecaster(0, **cfg); p=causal_runner.rollout(f, v[:o], s[:o], s[o:o+H]); tr=v[o:o+H]
    err=p-tr; print(f'origin {o}: rmse {np.sqrt(np.mean(err**2)):.4f} train_rmse {f.train_rmse:.4f}')
    st=np.where(s[o:o+H]>0)[0]
    # error by phase since stimulus
    ph=np.full(H,-1); 
    for i,x in enumerate(st):
        e=st[i+1] if i+1<len(st) else H; ph[x:e]=np.arange(e-x)
    for lo,hi in ((0,10),(10,30),(30,50),(50,70),(70,90),(90,120),(120,200)):
        m=(ph>=lo)&(ph<hi); print(f'   phase {lo:3d}-{hi:3d}: rms err {np.sqrt(np.mean(err[m]**2)):.4f}  n={m.sum()}')
    # per-beat: true apd vs predicted apd, peak
    rows=[]
    for i,x in enumerate(st[:-1]):
        e=st[i+1]; ta=apd_of(tr[x:e]); pa=apd_of(p[x:e]); rows.append((ta,pa,tr[x:e].max(),p[x:e].max(),np.sqrt(np.mean(err[x:e]**2))))
    rows=np.array(rows); print('   true APD / pred APD / true peak / pred peak / beat rmse'); print(np.round(rows[:20],2).T)
    print('   corr(true apd, pred apd)', np.corrcoef(rows[:,0],rows[:,1])[0,1].round(3), 'sd(true-pred apd)', (rows[:,0]-rows[:,1]).std().round(2), 'mean bias', (rows[:,1]-rows[:,0]).mean().round(2))
    # true APD vs prev APD: does the model use alternation? correlate pred APD with prev true APD
    print('   corr(pred apd_n, true apd_n-1)', np.corrcoef(rows[1:,1],rows[:-1,0])[0,1].round(3), '  corr(true apd_n, true apd_n-1)', np.corrcoef(rows[1:,0],rows[:-1,0])[0,1].round(3))
