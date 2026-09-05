## Approach
We fit a full mechanistic model of the circuit and simulate it under the held-out drive. The model is
exactly the task's Eqs. 1-6 in stacked form, `tau dr/dt = -r + k([W r + I(t)]_+)^n`, with the given
constants (tau=0.5, k=0.5, n=2) and the given forward-Euler integrator (dt=0.01, rates clipped at 0).
The only unknowns are the 49x49 recurrent matrix `W` and a scalar initial rate `r(0)` (fitted; comes
out at ~0.008, i.e. the circuit starts below its baseline fixed point).

`W` is parameterised as a Dale's-law, distance-dependent backbone times per-connection deviations:

    W_ij = s_j * J[a_i, b_j] * exp(-d_ij^2 / (2 sigma[a_i, b_j]^2)) * exp(delta_ij),   W_ii = 0

where `s_j` is +1 for excitatory and -1 for inhibitory presynaptic units, `a_i, b_j` in {E, I} are the
cell types, `d_ij` is the Euclidean lattice distance from `xy.npy`, `J` and `sigma` are 2x2 (8 backbone
parameters) and `delta` is a 49x49 log-deviation matrix with an L2 penalty `lam * sum(delta^2)`.

Parameters are fitted by shooting: the full trajectory under `train_I.npy` is simulated in PyTorch with
forward Euler, sampled at the 61 observation times, and compared to `train_r_obs.npy` through a
censored-Gaussian (Tobit) likelihood, because the recordings are Gaussian-noisy rates clipped at zero
(18% of samples are exactly 0). The noise s.d. is a fitted parameter (0.020). Gradients are taken
through the 12000-step integration with autograd (Adam, 400 iterations at a 5x coarser Euler step for
speed, then 80 iterations at the true dt=0.01). The final prediction is a weighted average of the eval
trajectories of an ensemble of fits, each simulated with the exact task integrator. Two backbone kernel
families are used because they fit the training data equally well (log-likelihoods within a few nats)
yet predict different eval trajectories: the Gaussian kernel above (8 members: 6 independent seeds with
lam=3, one chain initialised from the backbone-only fit, one seed with lam=1) and an exponential kernel
`exp(-d_ij/sigma[a_i,b_j])` (4 independent seeds, lam=3). The two families receive equal total weight
(members equal within a family). Members whose linearised dynamics go unstable anywhere along their own
eval trajectory would be dropped (none did).

Scripts: `ssn.py` (simulator, likelihood), `fit.py` (fitting), `ensemble.py` (stability filter +
averaging, writes `r_pred.npy`), `run_all.sh` (the exact sequence of calls).

## What the method targets
The method estimates the recurrent connectivity `W` (plus the initial state), i.e. the one object that
is shared between the training and held-out conditions; everything else (constants, integrator, drive)
is given. A generative model of the dynamics transfers to a new stimulus by construction, whereas a
stimulus-response regression would not.

Because the training stimulus only drives ~13 neurons around lattice site (2,4) appreciably, the data
identify `W` only within that active block. The distance-Gaussian, cell-type-specific backbone is what
carries the estimate to the rest of the lattice, which the sweeping eval stimulus excites in full; the
per-connection deviations capture the clear neuron-specific departures from the backbone inside the
active block (e.g. one E cell at distance 1 from the drive centre fires 4x more than three others with
identical drive) and are shrunk to the backbone elsewhere. Dale's law and the zero diagonal are imposed
exactly. Stability under the *held-out* drive is checked explicitly (largest real part of the Jacobian
eigenvalues along the simulated eval trajectory), since with n=2 a slightly-too-strong `W` is not
slightly wrong but divergent.

## Validation performed
- Leave-one-pulse-out on the training recording (fit on 3 pulses, predict the 4th at the observation
  times): the backbone alone gives RMSE 0.0239 / 0.0218 (pulses 1 and 4) against the noisy
  observations; adding deviations gives 0.0187 / 0.0172 for lam=1 and lam=3, 0.0191 / 0.0175 for lam=10,
  0.0201 / 0.0180 for lam=30. The noise floor (fitted s.d. of the clipped noise) is ~0.020, so lam=3 was
  chosen as the strongest penalty that is not worse than the best.
- Kernel comparison by the same leave-one-pulse-out protocol (lam=3, from scratch): Gaussian kernel
  0.0188 / 0.0171, exponential kernel 0.0192 / 0.0171 (pulses 1 / 4). The two families are
  indistinguishable on the training recording, which is why both are kept and weighted equally.
- Independent random initialisations of the backbone converge to the same J/sigma and the same
  likelihood (within a few nats); one earlier chain converged to a sharper, stronger E->E kernel with a
  worse likelihood (by ~5 nats) and was not used as the primary family.
- Ensemble spread on the eval condition (12 members, all with training RMSE 0.0170-0.0171 at the
  observation times): within the Gaussian family the 6 independent lam=3 seeds agree to nRMSE 0.03-0.05
  of their family mean; the exponential-kernel members differ from the Gaussian family mean by nRMSE
  0.23-0.27 (0.36-0.41 restricted to the peak region). Against the final weighted mean the members sit
  at nRMSE 0.11-0.18 (the chain member at 0.31). The eval prediction is therefore much less certain than
  the training fit, and model averaging is used to reduce that variance.
- Stability: for each member, the largest real part of the Jacobian eigenvalues along its eval
  trajectory is negative (Gaussian lam=3 members -0.40 to -0.46, lam=1 member -0.13, exponential members
  -1.09 to -1.17), and the simulated eval rates are bounded (peaks 0.51-0.55, training peak ~1.0). A parallel chain with lam=1 predicted 7x recurrent amplification in a corner
  cluster of E cells (eval peak 0.88, Jacobian margin only -0.04) and was excluded as an outlier in
  favour of the lam=3 family (tied in cross-validation, far better margin). A Monte-Carlo check showed that multiplying all connections by random lognormal
  factors of s.d. 0.3 makes half the eval simulations diverge, i.e. the fitted network is close to the
  stability boundary under the sweeping stimulus; this is why the stability filter is part of the
  pipeline.
- `selfcheck.py` passes (shape, finiteness, non-negativity).
The held-out answer was never available in the container; nothing above uses it.

## Budget used
Wall-clock: about 1.7 h of a 2 h session, on a 4-core CPU sandbox (no GPU), no internet. Compute: each
fit is 300-400 Adam iterations at dt=0.05 (~0.5 s per forward+backward through the 2400-step
integration) plus, for ensemble members, 80 iterations at dt=0.01 (~2-3 s each). In total ~35 fits
(3 backbone-only, 4 backbone hold-out runs, 8 penalty-sweep hold-out runs, 12 ensemble members with
their 12 refinements, 4 kernel-comparison hold-out runs), run 3-5 at a time; roughly 60 CPU-core-minutes.

## Limitations
- Columns of `W` belonging to neurons that were quiet during training (most of the lattice) are pure
  backbone; any true neuron-specific heterogeneity there (which the active block shows is substantial,
  log-deviations up to ~0.8) is unrecoverable from this recording and will dominate the eval error.
- E->E amplitude and width are partially degenerate given data only at lattice distances 1 and sqrt(2);
  the eval prediction in E-cell-dense patches of the lattice is correspondingly uncertain (this is where
  ensemble members disagree most).
- The observation model assumes additive Gaussian noise clipped at zero with a constant s.d.; the
  initial state is assumed uniform across neurons.
- Only Gaussian distance kernels were considered for the backbone; the true generator may be sparse or
  use a different kernel or boundary condition.
