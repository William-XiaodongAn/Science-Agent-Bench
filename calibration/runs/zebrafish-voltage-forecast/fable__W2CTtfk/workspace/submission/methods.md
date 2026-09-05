# Methods

## Search strategy

The submission is a two-phase search that spends the 60-configuration budget as follows.

**Phase 1, hypotheses (8 evaluations).** A fixed shortlist of designs is scored first, in priority order. All but the
last are *stimulus-driven* echo state networks (`voltage_feedback=False`) with a strong stimulus gain and a small
matched ridge (`input_scale` stimulus 20-50 with ridge 1e-7 to 3e-7: the network receives a saturating kick per
0.2 pulse, and the ridge is effectively zero relative to the state variance while keeping the readout weights 3-6x
smaller than the gain-5 / ridge-1e-8 scaling of the same accuracy). They differ in how the memory of past stimuli
is organised: (1) one 368-unit reservoir with per-neuron log-uniform leaks in [0.03, 0.3]; (2) a parallel bank of a
fast (leak 0.2) and a slow (leak 0.05) 184-unit reservoir, both driven by the input and both read out
(`inter_scale=0`, `input_to_all_layers`, `all_layers_to_output`), gain 50; (3) the multi-timescale reservoir with a
dense recurrent matrix and ridge 3e-7; (4) leaks in [0.03, 0.2] at gain 50; (5) a three-timescale bank (leaks
0.25/0.1/0.04); (6) the two-timescale bank at gain 20; (7) a single leak 0.15 at the low-gain scaling (gain 5, ridge
1e-8); (8) the framework's untuned default (voltage feedback, leak 0.5, ridge 1e-3) as the control. The shortlist
was chosen from offline experiments with the evaluator's own protocol (three fixed origins, 4113-sample causal
roll-outs) over seeds 0-4; entries 1-7 are statistically tied on the evaluator (dev RMSE 0.0807-0.0816, seed s.d.
about 0.001) and the control scores 0.116-0.126.

**Phase 2, refinement (remaining ~52 evaluations).** Coordinate moves around the incumbent, accepted only when the
dev RMSE improves: scaling the leak(s) by 0.7 or 1.4, moving one end of a per-neuron leak range, connectivity
{0.1, 0.3, 1.0}, spectral radius x0.96 / x1.04, stimulus gain x2 / x0.5 (capped at 100), ridge x3 / x1/3 (floored at
3e-8, so the search cannot drift into the ill-conditioned corner), bias gain {0.05, 0.2}, washout {500, 2000}. When no neighbour of the incumbent helps, the neighbours of the next designs in the phase-1
ranking are tried, walking down the ranking and then perturbing the incumbent again, so the whole budget is used. Moves are shuffled with a seed-dependent generator so the five searches do not visit the same
sequence. The search stops when the budget is used up or when fewer than 150 s of the 900 s wall clock remain
(a 368-unit configuration evaluates in 1.5-5 s, so the whole budget normally fits in 100-300 s), and returns the
evaluator's own record of its best configuration, so the returned dictionary is always one that was scored.

## Hypotheses tested

The default's error (dev 0.123, hidden test 0.120) was analysed first with tools that train no reservoir: the
inter-stimulus interval is not constant (96-180 ms) because the closed-loop protocol holds the diastolic interval
at ~48-52 ms, so every stimulus time encodes the previous action potential duration (APD; correlation between
interval and APD 0.99). APD alternates beat to beat (lag-1 autocorrelation -0.62) with a nonlinear return map: a
causal k-nearest-neighbour rule on the last two or three APDs predicts the next APD to 6-10 ms r.m.s. depending on
the window, where a linear rule (9-13 ms) barely beats the window mean (13-15 ms). Template forecasts that commit
to one waveform score 0.12 even with a linear APD predictor, while an oracle that knows the APD scores 0.059: the
error budget is almost entirely repolarisation timing, and a good forecaster must both know the past intervals and
hedge the repolarisation (the least-squares readout produces the conditional-mean waveform).

Hypotheses and how they fared on the evaluator (seed 0 unless stated; multi-seed figures are means over seeds 0-4):

1. *The fed-back voltage is the main liability.* Teacher forcing fits the readout to the true previous voltage; at
   roll-out it receives its own prediction, and every gain on the voltage channel above 0.1 diverged (dev 0.17-0.78).
   Removing the feedback entirely (`voltage_feedback=False`), so the network is a deterministic function of the
   stimulus times, immediately improved the default from 0.123 to 0.096 with leak 0.1 and stimulus gain 5.
   Hybrids with a tiny voltage gain (0.01-0.03) still diverged (0.24-0.59). **Confirmed; adopted.**
2. *The stimulus is under-driven.* The default injects 0.2 x 0.1 = 0.02 per pulse. Stimulus gains of 1-20 helped
   (0.123 -> 0.117 with feedback, 0.16 -> 0.096 without); above 5 the effect saturates. **Confirmed; adopted (gain 5).**
3. *The leak is too fast to hold a beat-to-beat memory.* Leak 0.5 (2 ms) vs 0.1-0.15 (7-10 ms): 0.117 -> 0.096
   without feedback. Very slow single leaks (0.05, 0.03) were worse (0.10-0.24); a per-neuron log-uniform range
   [0.03, 0.3] was the most robust single-reservoir choice (0.0816 +- 0.0005 over five seeds) and parallel
   fast/slow banks were equivalent (0.0811-0.0813). **Confirmed; adopted (multi-timescale).**
4. *The ridge shrinks exactly the small-amplitude components that carry the interval memory.* Ridge 1e-3 -> 1e-8
   went 0.117 -> 0.080 (stimulus-driven, leak 0.15); 1e-9 and 0 were numerically unstable (0.084 and blow-ups). A
   larger stimulus gain with a proportionally larger ridge (20-50 / 1e-7) is equivalent on the evaluator (0.0807-
   0.0814 over five seeds) while the fitted readout weights are 3-6x smaller (mean |W_out| ~170 vs ~600 on the full
   training set), so the high-gain scaling was adopted as the search family. **Confirmed; adopted.**
5. *Recurrence is needed for the memory* (a bank of leaky integrators alone is not enough): spectral radius 0.3 /
   0.5 / 0.7 / 0.9 / 1.0 gave 0.099 / 0.096 / 0.089 / 0.082 / 0.085. **Confirmed; 0.9 kept.**
6. *Hierarchies help.* Fast-to-slow chains matched the flat design at ridge 1e-6 (0.081) but were unstable across
   seeds at 1e-8 or with large `inter_scale` (s.d. 0.005-0.02); slow-to-fast chains were worse (0.091-0.11). Parallel
   banks (inter_scale 0) were as good as the flat multi-timescale reservoir. **Not supported beyond parallel banks.**
7. *The readout is variance-limited by the few training beats (65-99 at the dev origins).* 200-unit and 300-unit
   reservoirs matched 368 (0.0819 vs 0.0816), 100 units was slightly worse (0.084); a recency-weighted readout
   (half-life 4000-6000 samples) hurt (0.083-0.084); more training data helps modestly (learning curve 0.098 -> 0.093
   from 8000 to 10284 samples). **Partly supported; the test model, trained on 16454 samples, should benefit.**
8. *Connectivity, bias gain, washout, direct input-to-readout.* All within seed noise (0.0809-0.0817).

## What the method targets

The returned designs exploit the fact that, under this pacing protocol, the stimulus channel carries the whole
beat-to-beat state: each stimulus arrives a fixed ~50 ms after repolarisation, so the sequence of inter-stimulus
intervals is the sequence of past APDs, and the next APD is a nonlinear function of the last two or three. A
stimulus-driven reservoir with recurrent memory spanning 3-300 ms turns the recent stimulus times into a rich set of
nonlinear features; the unregularised readout uses them to (a) generate the stereotyped upstroke and plateau
phase-locked to the stimulus and (b) shift and blur the repolarisation according to the predicted APD, which is the
RMSE-optimal hedge. No fed-back voltage means no closed-loop error accumulation: the forecast at each sample depends
only on stimuli already delivered, exactly as the verifier supplies them. The structure relied on (fixed diastolic
interval, alternating APD, stereotyped waveform) is a property of the pacing protocol and the preparation, present
throughout the training recording (diastolic interval drifts only from 45 to 52 ms), so it should hold in the test
window that immediately follows it.

## Validation performed

- Offline sweeps with the evaluator's own protocol (three origins 8227/10284/12341, 4113-sample causal roll-outs,
  stimulus delivered one sample at a time), about 500 configurations, the shortlist and its neighbours over seeds 0-4.
- A six-origin check (origins 5000-13954, horizon 2500, seeds 0-1) outside the dev origins: the shortlist designs are
  tied (0.087-0.089 mean) and the default is at 0.123, so the improvement is not specific to the dev origins. The five
  configurations actually returned by the submitted searches were re-scored on the same six origins (0.087 mean over
  seeds, vs 0.088 for the unrefined shortlist head), so phase 2 does not overfit the three dev origins.
- Per-beat error attribution on the dev windows (which beats carry the squared error; see Limitations).
- Validity: each returned configuration, passed through a JSON round trip as the verifier does, was fitted on the
  full 16454-sample training recording and rolled out causally on a replay of the last 4113 training stimuli and on
  stress schedules (a stimulus every 95 ms and every 200 ms); all outputs finite and in a plausible range.
- `run_search.py`-equivalent runs of the submitted search for seeds 0-4 with the full budget: 60/60 evaluations each,
  no unmetered training, framework not shadowed, returned configuration evaluated; dev RMSE of the returned designs
  0.0794 / 0.0800 / 0.0794 / 0.0792 / 0.0796 (seeds 0-4; the untuned default scores 0.116-0.126 on the same
  evaluators). Seeds 0, 1 and 4 returned the two-timescale parallel bank (gains 25 / 50 / 10), seeds 2 and 3 the
  multi-timescale flat reservoir (dense recurrence and spectral radius 0.97 for seed 2; ridge 3.3e-8, bias 0.05 and
  washout 2000 for seed 3). Wall time 410-435 s per search when five searches share four cores single-threaded,
  78 s for 60 evaluations when run alone in-process; `selfcheck.py` passes.

## Limitations

- The search cannot see the test window; window difficulty varies widely (0.057-0.12 for the same design across
  origins), so the hidden score depends on how regular the alternans is in the last 4.1 s. In particular one beat at
  t = 13112 ms (APD 131 ms after a 51 ms beat; the designs predict ~81 ms) carries 64-72% of the squared error of
  both hard dev windows: without it they score ~0.053, like the easy windows. The dev metric is therefore dominated
  by a single rare event, and the hidden score will be ~0.055-0.06 if the test window has no such beat and closer to
  0.09 if it has one.
- The remaining error is dominated by APD unpredictability; the reservoir is within ~1-1.5 ms of a causal
  nearest-neighbour APD predictor on the hard windows, so further gains inside this model class are small.
- The design ignores the voltage entirely; if the test window contained a stimulus that failed to elicit a beat, or a
  spontaneous beat, the forecast would not react (the same is true of the study's method, which only saw its own
  prediction).
- The ridge is effectively zero, so the readout relies on the training and test states being computed identically
  (same seed, same framework), which the verifier guarantees.
- Phase 2 selects among designs that differ by less than the seed-to-seed spread on the evaluator; part of that
  selection is noise and is not expected to transfer to the test window.
