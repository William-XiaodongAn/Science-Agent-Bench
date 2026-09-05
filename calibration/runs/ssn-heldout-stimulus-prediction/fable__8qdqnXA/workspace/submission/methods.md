## Approach
System identification of the recurrent weight matrix W by *shooting*: the full SSN forward model
(tau*dr/dt = -r + k*[W r + I(t)]_+^n, forward Euler, dt = 0.01, given constants) is integrated over the
whole training drive and the simulated rates at the 61 observation times are matched to the noisy
observations. Gradients with respect to W come from a hand-written discrete adjoint of the Euler
recursion (`sim.py`, checked against finite differences), so one loss+gradient costs about 0.2 s and
L-BFGS can be used. No finite differences of the noisy data are ever taken.

W is parameterised hierarchically:
1. A Rubin-Van Hooser-Miller kernel prior: W_ij = s_j * J[type_i, type_j] * exp(-d_ij^2 / 2 sigma[type_i,type_j]^2),
   with Dale's law sign s_j (+ for E columns 0-28, - for I columns 29-48), zero diagonal, 4 amplitudes
   and 4 widths (8 parameters, `fit_kernel.py`). Two lattice-distance conventions were fitted (open and
   periodic 7x7).
2. Per-connection deviations around that kernel (`fit_v2.py`): either additive, W_ij = s_j*max(|W0_ij| + delta_ij, 0)
   with penalty lambda*sum(delta^2), or multiplicative, W_ij = W0_ij*exp(z_ij) with penalty lambda*sum(z^2).
   Dale's law is enforced by construction.
3. Observation model: additive Gaussian noise (std 0.019, estimated from residuals at high rates) clipped at 0,
   fitted with a censored (Tobit) likelihood, because 18% of observations are exact zeros, matching the
   clipped-Gaussian prediction.
4. Initial state: fixed point of the network under the baseline drive (0.18 everywhere).
5. Stability barrier: the *eval drive is known*, so during fitting the eval trajectory is also simulated and a
   penalty 50*sum(relu(r-1.5)^2) is added. It only forbids W's that make the eval simulation run away
   (true rates are O(0.1-1)); it never touches held-out rates.

The submitted prediction is the equal-weight mean of six members' eval simulations: additive lambda in
{0.02, 0.1} and multiplicative lambda = 0.01, each under the open-boundary and the periodic-boundary
kernel prior. Reproduce with
`cd /workspace/submission && python3 fit_kernel.py && TOBIT=1 python3 final.py add:0.02:tobit add:0.1:tobit mult:0.01:tobit add:0.02:tobit_per add:0.1:tobit_per mult:0.01:tobit_per`
(scripts expect to run from /workspace/work; copy them there or adjust `os.chdir`).

## What the method targets
The method estimates the recurrent connectivity W (and, through it, the network's operating point and gain)
under the *known* mechanistic model, rather than an input-output map. W is the only unknown shared between
the two conditions: constants, neurons, initial state and the model form are given, and only the drive differs.
A W that reproduces the training transients, together with the given dynamics, therefore transfers to any drive.
Because a single-location training stimulus cannot identify all 49x48 weights, the connections it does not
probe are pinned to the distance-dependent Dale's-law kernel that the paper's model prescribes, and the
connections it does probe (chiefly the outgoing weights of the driven inhibitory neuron 40 and its
neighbourhood) are freed. Averaging over the two boundary conventions and three shrinkage strengths
hedges the structural uncertainty that the training data cannot resolve.

## Validation performed
- Adjoint gradient checked against finite differences (agreement to 1e-6 relative).
- The kernel-only fit reaches residual RMSE 0.0194, i.e. the noise floor; the per-entry relaxation lowers it
  to 0.0169, which is real: in a 2-fold *pulse-holdout* CV (fit on 3 of the 4 training pulses, predict the 4th,
  and the same for pulse 2) held-out RMSE improves from 0.0185 (kernel only) to 0.0171-0.0173 for all
  ensemble members; lambda <= 0.005 gives no further gain and lets the eval simulation diverge, so it was excluded.
  Open and periodic priors are indistinguishable in CV (0.01719 vs 0.01723), hence both are kept.
- Gauss-Newton posterior over the 8 kernel parameters: J_EE is poorly identified (log-sd 1.1, open boundary),
  which motivated the ensemble rather than a single point estimate.
- Stability: every member's eval simulation is finite; the eval drive can be scaled by 1.15-1.24x before any
  member diverges (kernel-only: 1.12x), while the training drive can be doubled. The eval regime is close to
  the network's runaway boundary, so peak rates are the least certain part of the prediction.
- Noise model: residual std is homoscedastic (0.019) across rate bins; zero-fraction (18%) matches a clipped
  Gaussian around the resting rate, supporting the Tobit likelihood.
- Format check `selfcheck.py` passes. The prediction's own peak-region statistics (fraction of points above
  10% of peak: 0.20; neurons involved: 49) were compared against the figures quoted in the task (0.33, 47) as a
  sanity check; the periodic-prior members are closer on the fraction, which was one reason to keep them.

## Budget used
About 40 minutes of wall-clock from a 2 h budget (including a full from-scratch reproducibility rerun that matched the submitted array exactly), on a 4-core CPU sandbox;
roughly 40-50 core-minutes of compute in total (each full fit is 0.5-3 min, CV folds run in parallel).

## Limitations
- Connections not probed by the single-location training stimulus rest on the kernel prior; per-neuron
  heterogeneity there (seen to be ~10-fold for the probed column) is unrecoverable and bounds the achievable error.
- The eval sweep drives many neurons simultaneously, a regime never seen in training and close to the
  network's instability boundary, so peak amplitudes are sensitive to small errors in W. The ensemble's
  members disagree by ~0.11 nRMSE-equivalent, mainly at lattice-corner cells.
- The boundary convention of the true W (open vs periodic) is unresolved; the ensemble averages both.
- Kernel hyperparameters are fitted first and then held fixed while deviations are fitted (not jointly).
- The multiplicative-prior members terminate L-BFGS early (line-search failures near unstable W) and are
  somewhat under-optimised; they act as conservative hedges.
- Initial state assumed to be the baseline fixed point; the t=0 sample is mildly ambiguous about this,
  affecting at most the first ~1 time unit.
