#!/bin/bash
# Exact sequence used to produce /workspace/submission/r_pred.npy (run from this directory).
set -e
# 1) backbone-only fits (3 seeds) and leave-one-pulse-out checks of the backbone
for s in 0 1 2; do python3 fit.py --seed $s --iters 300 --sub 5 --out A_s$s.npz & done; wait
for h in 0 1 2 3; do python3 fit.py --seed 0 --iters 300 --sub 5 --holdout $h --out A_h$h.npz & done; wait
# 2) penalty sweep for the per-connection deviations, pulses 1 and 4 held out
for lam in 1 3 10 30; do python3 fit.py --seed 0 --iters 300 --sub 5 --init A_s1.npz --lam $lam --holdout 0 --out B_l${lam}_h0.npz & done; wait
for lam in 1 3 10 30; do python3 fit.py --seed 0 --iters 300 --sub 5 --init A_s1.npz --lam $lam --holdout 3 --out B_l${lam}_h3.npz & done; wait
# 3) full-data fits: chain initialised from the backbone fit, and independent from-scratch seeds (lam=3)
python3 fit.py --seed 0 --iters 300 --sub 5 --init A_s1.npz --lam 3 --out C_l3.npz &
for s in 1 2 3; do python3 fit.py --seed $s --iters 400 --sub 5 --lam 3 --out D_s$s.npz & done; wait
for s in 4 5 6; do python3 fit.py --seed $s --iters 400 --sub 5 --lam 3 --out D_s$s.npz & done; wait
#    alternative backbone kernel (exponential) seeds, and one Gaussian seed with lam=1
for s in 1 2 3 4; do python3 fit.py --seed $s --iters 400 --sub 5 --lam 3 --kernel exp --out E_s$s.npz & done; wait
python3 fit.py --seed 1 --iters 400 --sub 5 --lam 1 --out F_s1.npz
# 4) refine each at the true integration step dt=0.01
for f in C_l3 D_s1 D_s2 D_s3 D_s4 D_s5 D_s6; do python3 fit.py --seed 0 --iters 80 --sub 1 --lr 0.01 --lam 3 --init $f.npz --out ${f}_ref.npz & done; wait
for f in E_s1 E_s2 E_s3 E_s4; do python3 fit.py --seed 0 --iters 80 --sub 1 --lr 0.01 --lam 3 --kernel exp --init $f.npz --out ${f}_ref.npz & done; wait
python3 fit.py --seed 0 --iters 80 --sub 1 --lr 0.01 --lam 1 --init F_s1.npz --out F_s1_ref.npz
# 5) stability-filtered, family-weighted ensemble average -> submission (Gaussian family 0.5, exponential family 0.5)
python3 ensemble.py /workspace/submission/r_pred.npy \
  C_l3_ref.npz:0.0625 D_s1_ref.npz:0.0625 D_s2_ref.npz:0.0625 D_s3_ref.npz:0.0625 D_s4_ref.npz:0.0625 D_s5_ref.npz:0.0625 D_s6_ref.npz:0.0625 F_s1_ref.npz:0.0625 \
  E_s1_ref.npz:0.125 E_s2_ref.npz:0.125 E_s3_ref.npz:0.125 E_s4_ref.npz:0.125
python3 /workspace/selfcheck.py
