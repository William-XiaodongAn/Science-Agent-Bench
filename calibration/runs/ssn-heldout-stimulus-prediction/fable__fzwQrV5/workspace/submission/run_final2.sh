#!/bin/bash
cd /workspace/work
for lam in 0.03 0.1; do
nohup python3 -c "
import sys, json, time; from fit import *
lam=$lam; mask=make_mask(); t0=time.time()
m,h=fit(mask, lam=lam, free_dev=True, iters=150, eval_guard=True, cap=1.2, sub=2, guard_sub=2, margin=1.1)
W=m().detach().numpy(); np.save(f'W_final2_{lam}.npy', W)
Re=simulate_np(W, I_ev, r0=np.full(N,0.01)); print('final2 lam',lam,'train nRMSE',nrmse(predict_obs(m),r_obs,mask),'eval max',np.nanmax(Re),'finite',np.isfinite(Re).all(),'time',time.time()-t0, flush=True)
" > final2_$lam.txt 2>&1 &
done
nohup python3 bag.py 8 0.1 1.2 > bag_8.txt 2>&1 &
nohup python3 bag.py 9 0.1 1.2 > bag_9.txt 2>&1 &
