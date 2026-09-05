# Methods

## Search strategy

Each seed gets its own 60-configuration search. The first eight evaluations are fixed anchors found in pilot sweeps. They include five parallel-bank designs and three single-reservoir controls. The next 42 evaluations sample the promising region: 32 five-bank parallel reservoirs (24 balanced and eight mildly unbalanced partitions) and ten flat reservoirs. The last ten locally perturb one of the three best configurations for that seed. The returned configuration is the lowest mean development RMSE actually evaluated. Searches with a smaller diagnostic budget stop at that budget.

The search concentrates on spectral radii 0.80--1.04, leaks spanning roughly 0.035--0.70, strong stimulus scaling, low ridge penalties, and several washouts. All candidates have exactly 368 units. No reservoir is trained outside `evaluator.evaluate`.

## Hypotheses tested

The first hypothesis was that the default is limited by teacher-forcing mismatch: during fitting it receives true previous voltage, but during a 4113-sample forecast it receives its own output. Removing voltage feedback improved seed-0 development RMSE from about 0.123 to about 0.095; extensive tuning of feedback models plateaued near 0.111 and sometimes became unstable.

The second hypothesis was that the 1 ms stimulus should act as a strong phase reset. Increasing stimulus input scale and reducing readout regularisation improved the best stimulus-only models from about 0.095 to about 0.081.

The third hypothesis was that one reservoir timescale is insufficient for the fast upstroke, plateau/repolarisation, and beat-to-beat alternation. Five parallel reservoirs with different leaks improved the best observed development RMSE to about 0.0795. Per-neuron log-uniform leak ranges, serial reservoirs, recency weighting, altered clipping, and broad washout changes were tested but were not better than discrete parallel banks.

## What the method targets

The returned models are driven only by the causally delivered stimulus. A strong pulse synchronises their within-beat phase, avoiding accumulated voltage-feedback error. Parallel reservoirs provide distinct fading-memory timescales: fast units represent action-potential morphology, while slower units preserve preceding intervals and alternating state across beats. Those features match the pacing protocol and do not depend on knowing future stimulus times, so the same structure should persist in the held-out continuation.

## Validation performed

Candidate comparisons used the supplied evaluator: for each network seed it refits at all three fixed training origins and performs causal 4113-sample rollouts. Pilot sweeps covered feedback, topology, spectral radius, connectivity, leaks, channel scales, ridge, washout, readout recency, and direct-input options. As a secondary, non-selection diagnostic, the five selected designs were evaluated from a later training origin after the isolated 180 ms beat; over the remaining 3162 samples their RMSEs were 0.0597, 0.0645, 0.0618, 0.0599, and 0.0591. The final procedure was also run through `baseline/run_search.py` for all five seeds, checking the evaluation count, returned-configuration membership, size, finite development scores, framework integrity, and unmetered warmup count. `selfcheck.py` was run as the final interface check.

## Limitations

The hidden voltage and hidden stimulus schedule are unavailable, so selection can only estimate continuation performance from the three fixed origins. Two development windows contain the same unusually long beat and are therefore correlated. The search also tunes random-feature models separately by seed; its low-ridge solutions may be sensitive to reservoir realisation, although the anchors and per-seed refinement reduce that risk.
