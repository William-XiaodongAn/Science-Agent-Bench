# Methods

## Search strategy

Each call uses all 60 metered evaluations. The first 33 evaluations are a deterministic space-filling design over three parallel reservoirs whose sizes sum to 368. Every reservoir receives the causal stimulus, every reservoir is exposed to the readout, and `inter_scale=0` keeps the banks independent. The candidates concentrate on three leak-rate bands (roughly 0.03--0.075, 0.10--0.20, and 0.30--0.55), spectral radii 0.86--0.95, ridge values around (10^{-8}), strong stimulus scaling, and several unit allocations and connectivities.

The remaining 27 evaluations refine the best first-stage candidate for that seed. They vary ridge over two orders of magnitude, perturb spectral radius, jointly and individually perturb the three leak rates, and test nearby stimulus scale, bias scale, and connectivity. The returned configuration is the lowest-mean-RMSE configuration actually evaluated. The same candidate generator is used for every seed; reservoir weights themselves remain seed-determined by the supplied framework.

## Hypotheses tested

The untuned model appeared limited first by autonomous exposure bias. Its readout is fitted while receiving true preceding voltage, but rollout feeds prediction errors back. Removing voltage feedback reduced seed-0 dev RMSE from about 0.123 to about 0.096 once the stimulus impulse was scaled strongly. Feedback-only refinements, removal of the direct voltage-to-readout shortcut, tighter feedback clipping, and feedback through deep reservoirs did not beat the stable stimulus-driven designs; many low-ridge feedback models became markedly unstable.

A second hypothesis was that one leak rate asks the same state to represent both the within-action-potential waveform and beat-to-beat alternans memory. A three-bank parallel design with slow, medium, and fast leaks improved dev RMSE to about 0.079--0.080. Two-bank, four-bank, five-bank, per-neuron heterogeneous-leak, and serial deep alternatives were tested; none was as consistently good across seeds as three explicit timescale banks.

The pulse amplitude at the reservoir input was also limiting: the default effective impulse was very small. Scaling the stimulus channel from 0.1 to roughly 5--10 made it a reliable phase reset. Very small readout ridge (typically near (10^{-8})) improved the pulse-driven designs, whereas the same weak regularisation often destabilised feedback designs. Recency-weighted readouts, altered washout, and broad connectivity changes did not improve the best validation result.

## What the method targets

The stimulus times encode the completed history of the closed-loop experiment: after a beat repolarises, the next stimulus follows at an approximately fixed delay. Thus, at a new pulse, past inter-stimulus intervals causally convey prior action-potential durations even without feeding predicted voltage back. The slow bank retains this beat history, the medium bank describes repolarisation, and the fast bank resolves the stimulus-triggered upstroke. A strong pulse resets phase on every beat, preventing small timing errors from accumulating throughout the 4113-sample rollout.

This structure should persist into the test window because it follows from the pacing protocol rather than from future stimulus access. The model never receives or examines the future schedule: each bank updates only from the stimulus sample currently delivered.

## Validation performed

All reservoir fitting during development and in the submitted procedure was performed through `evaluator.evaluate`; no external `Forecaster.warmup` or shadow implementation was used. The exact submitted search was run with the supplied runner for seeds 0--4. It used 60/60 evaluations per seed, returned an evaluated finite 368-unit configuration each time, and produced dev RMSEs 0.07904, 0.07940, 0.07931, 0.08014, and 0.07981 (mean 0.07954). The runner reported zero unmetered training.

The fixed validation windows were also inspected separately through `evaluator.history`. The first origin was substantially easier (about 0.054--0.056 for strong designs); the two later, overlapping windows were about 0.090--0.095 and both contain the recording's exceptional 180 ms inter-stimulus interval. Candidate selection nevertheless uses the evaluator's required unweighted mean over all three origins.

## Limitations

Only about 137 paced beats are available, and the three validation windows overlap. A single extreme-duration beat therefore affects two validation scores, while the withheld window may contain a different number of such events. The search cannot see future stimulus times, cannot anticipate an intrinsically unpredictable duration excursion, and cannot establish whether the beat map is deterministic or noisy. Eliminating voltage feedback improves rollout stability but discards voltage-shape information not represented by past stimulus timing. Finally, selection among 60 configurations can itself overfit the fixed development origins; the deterministic first-stage design and narrow local refinement reduce, but do not remove, that risk.
