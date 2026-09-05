# Methods

## Search strategy
The 60 evaluations of each `search(evaluator, seed)` call are spent in two phases.

1. **Portfolio (30 evaluations).** A fixed, ordered list of 30 designs (`portfolio.py`) is evaluated. All of them come from one
   design family found during development with the evaluator's own protocol (three dev origins, 4113-sample causal
   roll-outs, the same `Forecaster`): purely stimulus-driven networks (no voltage feedback) built as a chain of 2-5
   reservoirs whose states are all read out, with spectral radius 0.85-1.25, leak rates around 0.1 (a single value or a
   per-neuron log-uniform range such as 0.01-0.35), a strong inter-reservoir coupling (0.3-1.7), a stimulus input scale of
   1-5 and a very small ridge (1e-7 to 3e-5). The list is ordered by a robust offline statistic (five-seed mean dev RMSE plus
   half the worst seed's excess) with at most two variants per architecture family, so that each seed can pick the member
   that suits its own random weights.
2. **Local refinement (remaining ~30 evaluations).** A seeded (1+1) hill climb from the best portfolio member for this
   seed: log-normal jitter of the continuous hyperparameters (spectral radius, leaks, stimulus and bias scales,
   inter-reservoir scale, ridge, connectivity), occasionally a larger single-parameter move, a re-partition of units between
   two reservoirs, or a readout-wiring toggle. Spectral radii are capped at 1.3 because higher values were seen to diverge for
   some seeds. Every candidate is scored by the evaluator; the search returns `evaluator.best()`, so the returned design was
   always evaluated. A wall-clock guard (600 s) stops the loop early if evaluations are slow.

Development itself was a budgeted sequence of experiments with the same dev protocol: single-parameter changes to the
default (20 configurations), a broad random search over the whole design space (160), then three focused random searches
(160, 170, 120) in the region that worked, with the best designs re-scored on all five seeds. Selection used seeds 0-4 on
the three dev origins only; the hidden test window was never touched.

## Hypotheses tested
- **H1: the default's leak (0.5) and spectral radius (0.9) give too short a memory to represent the previous beat.**
  Slower leaks alone with voltage feedback made things worse (leak 0.1: 0.23; 0.05: 0.21; 0.02: 0.15 vs 0.122): with
  feedback, slow units destabilise the closed loop. Slow leaks only pay off without feedback (below).
- **H2: voltage feedback is the main liability.** Closed-loop error compounds: the network mistimes one repolarisation and the
  fed-back error corrupts the following beats. A stimulus-driven reservoir (no feedback) with a multi-timescale leak range
  and a larger stimulus scale scored 0.110 from a single reservoir and, once deep and near the edge of stability, 0.081-0.083,
  the best family found. Re-adding weak feedback (voltage scale 0.05-0.6) to the best chains made them diverge (RMSE 0.5-5).
- **H3: the information that predicts a beat's duration is the timing of the previous stimuli.** Free analysis of the
  training recording: APD_k correlates -0.66 with the previous inter-stimulus interval; a gradient-boosted regression on the
  previous two intervals predicts APD with 8.7 ms RMSE against a 14.6 ms standard deviation, and *every* long beat
  (APD > 60 ms) follows a short interval (96-114 ms). The relation is convex: the shorter the interval the disproportionately
  longer the next beat. A linear read-out of one leaky reservoir cannot form this product of "time since the stimulus" and
  "memory of the previous interval"; chaining reservoirs through tanh with a coupling of order 1 does. The best chain's
  predicted APD correlates 0.76 with the true APD (10.2 ms RMSE) but still under-reacts after short intervals (predicts
  ~58 ms where the truth averages ~71 ms).
- **H4: the rare long beats dominate the score.** With the best design the 2-4 beats over 60 ms in each dev window carry
  50-75% of the squared error; the RMSE over the other beats is about 0.05. This is why a window's score depends strongly on
  how many long beats it contains (per-origin dev RMSE 0.060 / 0.092 / 0.095 for the same model).
- **H5: readout details (ridge, recency weighting, direct input-to-output, washout).** Ridge must be tiny (1e-7 to 1e-5;
  1e-4 costs 0.01, 0.1 ruins it): the fit is under-, not over-parameterised (training RMSE ~0.07 vs dev 0.081). Recency
  weighting of the readout never helped (the dynamics are stationary: mean APD 47 ms in every 20-beat block). Direct
  input-to-output and a shorter washout are neutral (± 0.002). Connectivity 0.05-0.5 is neutral; very sparse (0.03) slightly worse.
- **H6: spectral radius.** Around 1 (0.85-1.25) is best without feedback; the reservoir behaves as a nonlinear delay line that
  is reset by each pulse. Radii ≥ 1.4 diverge for some seeds (one design went to RMSE 3.3 on seed 4), so the search caps it.

## What the method targets
The pacing protocol delivers each stimulus a fixed delay after the previous repolarisation, so the sequence of stimulus
times, which the model receives sample by sample, encodes the sequence of previous action-potential durations. The
dynamics show alternans with memory: a short beat is followed by a long one and vice versa, with a convex dependence on the
previous interval (long beats after intervals under ~110 ms). The returned designs exploit exactly this: a stimulus-driven
chain of leaky-tanh reservoirs whose slow units hold an exponentially decaying trace of the previous pulses (their value at
the next pulse is a convex function of the interval), whose fast units time the upstroke and plateau, and whose deeper
layers combine the two nonlinearly so that the linear readout can shift the repolarisation according to the preceding
interval. Because nothing is fed back, an error in one beat does not propagate; each beat is re-synchronised by its stimulus.
This structure is a property of the pacing protocol and of the cell's restitution, not of a particular window, and the
APD statistics are stationary over the recording, so it should hold in the test window, which directly continues the training
recording under the same protocol.

## Validation performed
- Every configuration was scored with the evaluator's protocol (three origins at 8227, 10284 and 12341 inside the training
  recording, 4113-sample causal roll-outs with the stimulus delivered one sample at a time). About 700 configurations were
  scored offline this way (seeds 0-1 or 0-2 for exploration; the best re-scored on seeds 0-4).
- The 30 portfolio members all have a five-seed dev mean between 0.0808 and 0.083 with a seed-to-seed standard deviation
  of at most 0.0015: the family is robust to the random weights, which is what the five-seed mean rewards.
- The complete search was run through the verifier's `search_api.run_search` for seeds 0-4 with the full budget: 60
  evaluations in 253-260 s per seed (five searches in parallel on four cores), no unmetered training, framework intact, the
  returned configuration always one that was evaluated. Dev RMSE of the returned designs: 0.0798, 0.0799, 0.0794, 0.0799,
  0.0792 (mean 0.0796) against 0.1218 for the untuned default. `selfcheck.py` passes. Details in `validation.txt`.
- Held-out check: the five returned designs were re-scored at five origins the evaluator never uses (5000, 6100, 7200, 9300,
  11300). Mean held-out RMSE 0.0889 for the returned designs vs 0.0878 for the portfolio's first member, i.e. the ~0.001 dev
  gain of the refinement phase is selection on the three dev windows, not a real improvement; the design family itself is
  what carries the result. (Held-out windows are harder than the dev windows because they contain more long beats and
  their models train on less data; training-set size alone changes the RMSE by only ~0.001-0.006.)
- Free analyses of the recording (no reservoir trained): APD statistics, APD predictability from the stimulus intervals,
  template oracles (template with known stimulus times 0.123; template warped to the true APD 0.062), and a per-beat
  decomposition of the best design's error.

## Limitations
- The dev protocol sees three windows of the training recording; a window's score depends heavily on how many long beats it
  contains (per-origin dev RMSE 0.060 / 0.092 / 0.095 for the same model), which no design controls. The anchor for the
  default (dev 0.122 vs hidden 0.120) suggests dev and hidden difficulty are similar, but that is one data point, and the
  five-seed dev mean of the returned designs (0.0796) is only 1.5% under the 0.0784 bar.
- The network still under-predicts the longest beats (APD > 70 ms) and cannot foresee a long beat that is not preceded by
  a short interval; with a linear readout of 368 states, capacity, not regularisation, is the limit (training RMSE ~0.07,
  ridge at 1e-6 already optimal). Some 600 designs in this family plateau at 0.080-0.083; no tweak broke through it.
- The portfolio is a prior learned offline on this recording with the evaluator's own protocol; the search is a procedure
  with a strong prior, and the 30 refinement evaluations improve the dev score by ~0.001 without improving held-out windows.
- Designs with spectral radius above ~1.3, or with voltage feedback added to a chain, can diverge; the search caps the radius
  and never turns feedback on, and a diverging candidate is scored as infinite and discarded.
