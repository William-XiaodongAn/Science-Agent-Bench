#!/bin/bash
cd /workspace/work
for lam in 0.03 0.1 0.3; do
nohup python3 -c "
import sys, json, time; from fit import *
lam=$lam; mask=make_mask(); t0=time.time()
m,h=fit(mask, lam=lam, free_dev=True, iters=200, eval_guard=True, cap=2.0, sub=1)
W=m().detach().numpy(); np.save(f'W_final_{lam}.npy', W); torch.save(m.state_dict(), f'm_final_{lam}.pt')
Re=simulate_np(W, I_ev, r0=np.full(N,0.01)); print('lam',lam,'train nRMSE',nrmse(predict_obs(m),r_obs,mask),'eval max',np.nanmax(Re),'finite',np.isfinite(Re).all(),'time',time.time()-t0, flush=True)
" > final_$lam.txt 2>&1 &
done
