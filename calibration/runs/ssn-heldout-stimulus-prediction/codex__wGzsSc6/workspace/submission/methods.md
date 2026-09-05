## Approach

I fitted a Dale-compliant SSN and then integrated the supplied Euler equations. The prior connectivity has four positive-magnitude E/I block kernels, each an isotropic Gaussian of lattice distance; presynaptic inhibitory columns receive a minus sign and the diagonal is zero. Eight kernel parameters were fitted by bounded nonlinear least squares against a continuous training rollout. I then made a regularized multiple-shooting refinement: every pair of adjacent observations defines an exact 200-step rollout, with per-row/per-presynaptic-type gains and small local edge corrections. Corrections are projected onto Dale's law, limited to squared distance at most 13, and shrunk toward the Gaussian model. The final model was refitted on all intervals and simulated from the shared zero initial state under `eval_I.npy`.

## What the method targets

The method estimates the recurrent connectivity and its spatial, cell-type, sign, and stability structure. Those properties are shared between conditions, unlike a fitted training response curve, so they transfer when the Gaussian moves to new lattice locations. Exact flow-map fitting targets the transient dynamics without taking finite differences of the coarse noisy samples.

## Validation performed

Regularization was selected by holding out two complete groups of training-pulse intervals. The chosen refinement reduced held-out endpoint RMSE from 0.0201 for the kernel alone to about 0.0171, near the estimated recording-noise floor. A final continuous training replay had RMSE about 0.0174. I checked Dale signs, the zero diagonal, non-negativity, finiteness, continuous-rollout stability, deterministic regeneration, output shape, and the supplied `selfcheck.py`; no held-out response values were available or used.

## Budget used

Approximately 22 minutes wall-clock on CPU only. Model selection used small NumPy/SciPy simulations and single-threaded PyTorch optimization; the final reproducible run takes under one minute in this environment. No network access or GPU was used.

## Limitations

One fixed training center cannot identify every individual synapse. The Gaussian/local shrinkage prior therefore dominates poorly excited and long-range connections, and true nonstationary or strongly irregular connectivity could be missed. The initial state is inferred as zero from the recording at time zero. Parameter uncertainty is not propagated into the single submitted trajectory.
