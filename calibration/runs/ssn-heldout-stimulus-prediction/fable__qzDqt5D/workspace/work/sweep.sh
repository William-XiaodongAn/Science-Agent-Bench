#!/bin/bash
cd /workspace/work
run() { python3 fit.py --seed 0 --iters 300 --sub 5 --init A_s1.npz --lam $1 --holdout $2 --out B_l$1_h$2.npz > B_l$1_h$2.log 2>&1; }
for lam in 1 3 10 30; do run $lam 0 & done; wait
for lam in 1 3 10 30; do run $lam 3 & done; wait
echo SWEEP_DONE
