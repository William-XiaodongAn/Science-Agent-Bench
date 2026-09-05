"""Final pipeline. Each member = prior:lambda:tag, tag in {tobit, tobit_per}. Fits any missing member on all
training data (fit_v2.py with eval-boundedness barrier), simulates the eval drive, averages the members,
writes /workspace/submission/r_pred.npy.  Example:
  python3 final.py add:0.02:tobit add:0.1:tobit mult:0.01:tobit add:0.02:tobit_per add:0.1:tobit_per mult:0.01:tobit_per"""
import numpy as np, sys, os, subprocess
os.chdir('/workspace/work')
configs=sys.argv[1:]; procs=[]
def parse(c):
    prior,lam,tag=c.split(':'); return prior,float(lam),'_'+tag
for c in configs:
    prior,lam,tag=parse(c)
    if not os.path.exists(f'v2_eval_{prior}_{lam}{tag}.npy'):
        env={**os.environ,'TOBIT':'1' if 'tobit' in tag else '0','PERIODIC':'1' if 'per' in tag else '0'}
        procs.append(subprocess.Popen(['python3','fit_v2.py',prior,'full',str(lam)],env=env,stdout=open(f'final_{prior}_{lam}{tag}.log','w'),stderr=subprocess.STDOUT))
for p in procs: p.wait()
preds=[]
for c in configs:
    prior,lam,tag=parse(c); e=np.load(f'v2_eval_{prior}_{lam}{tag}.npy')
    assert np.isfinite(e).all() and e.max()<5, c
    print('%-24s eval max %.3f mean %.4f frac>10%%peak %.3f'%(c,e.max(),e.mean(),(e>0.1*e.max()).mean())); preds.append(e)
preds=np.array(preds); ens=np.clip(preds.mean(0),0,None)
spread=np.sqrt(((preds-ens[None])**2).mean()); print('member spread rms %.4f (nRMSE-equiv %.3f)'%(spread,spread/ens.std()))
print('ensemble max %.3f frac>10%%peak %.3f neurons %d'%(ens.max(),(ens>0.1*ens.max()).mean(),(ens>0.1*ens.max()).any(1).sum()))
os.makedirs('/workspace/submission',exist_ok=True)
np.save('/workspace/submission/r_pred.npy',ens.astype(np.float64))
for f in ['sim.py','fit_kernel.py','fit_v2.py','final.py','theta_kernel_0.npy','theta_kernel_1.npy']: subprocess.run(['cp',f,'/workspace/submission/'])
print('written',ens.shape)
