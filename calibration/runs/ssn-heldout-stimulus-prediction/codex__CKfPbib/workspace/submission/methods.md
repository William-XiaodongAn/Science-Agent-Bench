## Approach

model_family: Dale-constrained spatial SSN
connectivity: four Gaussian distance kernels indexed by postsynaptic and presynaptic E/I type, zero diagonal
fit: forward-simulation least squares on the 61 noisy observations, with alternating kernel and regularized neuron-specific E/I input corrections
regularization: L2 shrinkage toward the spatial kernel; corrections taper to zero for presynaptic columns not activated by the training stimulus
selection: regularization selected by holding out a complete training pulse
prediction: forward Euler with dt=0.01, tau=0.5, k=0.5, n=2, rectified inputs, and non-negative rate clipping

## What the method targets

target: the shared recurrent operator W
transfer_rationale: W, neuron identities, and lattice geometry are shared across conditions, while only the known external drive changes; estimating a stable Dale-compliant spatial operator therefore transfers to the moving stimulus.

## Validation performed

checks: held-out whole-pulse prediction; multiple initial parameter fits; forward stability on the full evaluation drive; local Jacobian stability margin; output shape, dtype, finiteness, and non-negativity; repository selfcheck
answer_access: none

## Budget used

wall_clock: approximately 50 minutes
compute: one CPU process; NumPy/SciPy; under 1 GB working memory

## Limitations

The single fixed-location training stimulus cannot identify arbitrary individual synapses. The distance kernel supplies those unobserved connections, while fitted neuron-specific corrections are strongly shrunk and restricted to well-excited presynaptic columns. Residual non-spatial connectivity heterogeneity may therefore be missed.
