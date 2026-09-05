## Approach

Forward-simulated the specified SSN with forward Euler at `dt=0.01`. Estimated two Dale-compliant, zero-diagonal spatial recurrent models from the noisy training observations. Each of the four E/I blocks used a positive Gaussian distance kernel with separately fitted magnitude and width; inhibitory columns were negated. Parameters minimized a censored-Gaussian observation likelihood (`sigma=0.020`) so zeros created by clipping were not treated as exact latent zeros. Weak L2 shrinkage selected stable solutions. For neurons substantially driven in training (`max(I_i)>0.30`), fitted shrinkage-regularized multipliers on incoming E and I weights, then refitted the population kernel. The prediction is a fixed weighted ensemble of unnormalized and outgoing-column-normalized boundary variants, with 70% weight on joint refits and 70% total weight on the better unnormalized boundary model.

## What the method targets

The method estimates the shared recurrent operator: its E/I signs, spatial decay, population coupling strengths, and identifiable neuron-specific incoming gains. These properties belong to the circuit rather than the stimulus, so the fitted operator can be integrated with `eval_I.npy` even though the drive moves to new lattice locations.

## Validation performed

Checked censored-noise scale on quiet training intervals; compared Gaussian, exponential, periodic, row-normalized, and column-normalized spatial priors; held out each complete training pulse; and performed a nested strongest-pulse holdout while estimating both kernel and row corrections only from the remaining pulses. Checked Dale signs, zero diagonal, finite trajectories, nonnegative rates, stability under the full evaluation drive, exact output shape, and reproducibility with the supplied script. The final format was checked with `/workspace/selfcheck.py`.

## Budget used

Approximately 55 minutes wall-clock on one CPU, with under 1 CPU-hour of numerical optimization and simulation; no GPU and no internet.

## Limitations

One fixed training location cannot identify every individual synapse. Most transfer therefore comes from the isotropic spatial/type prior, and row corrections are retained only for sufficiently stimulated neurons. Boundary normalization is not uniquely identifiable, so a small model ensemble is used. Unobserved neuron-specific connectivity and any non-Gaussian anisotropy remain unresolved.
