# Methods

## Search strategy

All numbers below are dev RMSEs from the shipped evaluator protocol (three origins inside the training recording, 4113-sample
causal roll-outs, mean over the origins), averaged over reservoir seeds 0-2 unless stated. Every reservoir training used in
development went through that same `Evaluator` (with a large budget, in a separate development process); the submitted
`search.py` uses at most 60 evaluations and trains nothing itself.

The 60 evaluations are spent in three phases, identically for each seed (only the seed of the random perturbations changes):

1. **Control and anchors (7 evaluations).** The untuned default (368 units, voltage feedback) is evaluated once as the control.
   Then five anchors of the design family described below (a single 368-unit reservoir driven only by the stimulus, stimulus
   gain 20-100, leak either fixed at 0.07-0.1 or per-neuron log-uniform in [0.01-0.03, 0.2-0.5], ridge 1e-7 to 1e-6) and one
   two-reservoir variant (184+184 units, stimulus into both, readout from both, strong inter-reservoir coupling, weak
   stimulus gain) are evaluated. The best anchor becomes the incumbent and fixes the architecture family that is refined.
2. **Coordinate descent (about 36 evaluations).** The knobs of the incumbent are moved one at a time, up and down, on
   log10 scales: ridge (step 0.5 decades), stimulus gain (0.4), the two ends of the leak range (0.3 each), spectral radius
   (linear, 0.05) and connectivity (0.4 decades); three passes with the steps halved after each pass. A move is accepted only if
   it improves the dev RMSE by more than 0.3 % (the dev surface of this family is flat, and its residual variation is
   dominated by one unpredictable beat, see below, so smaller differences are noise).
3. **Seeded random perturbations (remaining evaluations).** Two knobs at a time are perturbed with Gaussian steps of the
   initial size around the incumbent, accepted under the same margin, until the budget is used up.

The search returns `evaluator.best()`, i.e. a configuration it has evaluated. Bounds keep the design in the regime that was
robust across seeds (stimulus gain 2-200, spectral radius 0.5-0.95, leak in [0.005, 1], ridge in [3e-9, 1e-4], connectivity
0.02-1). A wall-clock guard stops the refinement after 780 s; in practice the 60 evaluations take about 90 s.

## Hypotheses tested

**H1. The default is limited by feeding its own voltage back with fast dynamics (dev 0.120, seeds 0-1).** The teacher-forced
readout fits the one-step map almost perfectly (training RMSE 0.006), but in closed loop the errors compound. Slowing the
leak alone helped (leak 0.2: 0.106) but slower still (0.05-0.1) diverged on some seeds (0.22-0.25), as did a small ridge or a
larger voltage input scale (0.5-0.8). A stronger stimulus gain with the feedback kept helped a little (0.097). The feedback
family is fragile: its best members were 0.095-0.097 and every attempt to make its readout less regularised diverged.
*Partly confirmed:* the feedback is the source of the instability, but removing it, not tuning it, is what works.

**H2. Everything that is predictable is in the stimulus timing, so a stimulus-only reservoir should do as well or better.**
The pacing protocol keeps the diastolic interval fixed (measured: 45-52 ms), so each inter-stimulus interval equals the
previous action-potential duration plus a constant: the stimulus channel tells the network the duration of the previous
beat. The durations alternate (lag-1 correlation -0.63) and the relation is nonlinear (previous interval 95-105 ms gives a
duration of about 92 ms, 105-115 about 82 ms, 115 ms and above about 62-68 ms). Free analyses on the recording set the
scale: a mean-beat template scores 0.119 (the default ESN is doing no better than that); a per-lag linear regression of the
beat waveform on the previous two intervals with quadratic terms scores 0.084; the oracle that knows each beat's duration
scores 0.056. A stimulus-only reservoir with the default gain scored 0.180, i.e. worse than the default, *until the stimulus
gain was raised*: gain 2 with multi-timescale leaks gave 0.105, gain 20 gave 0.101, and with the other two changes below the
family reached 0.081-0.082. *Confirmed.*

**H3. The stimulus pulse must saturate the units.** The stimulus is a 1 ms pulse of amplitude 0.2; with input scale 0.1 it
moves a unit by 0.02 and the network state is nearly a linear superposition of past pulses, from which a linear readout
cannot form the nonlinear interval-to-duration map. Raising the stimulus gain from 2 to 20 to 50 improved 0.096 -> 0.083 ->
0.082 (with leak 0.07, ridge 1e-6/1e-7); 100-300 were flat (0.082). *Confirmed; saturating from 20 upward.*

**H4. The reservoir must remember the previous one or two intervals while drawing the current beat.** With leak 0.5 the units
forget in a few milliseconds. Fixed leaks of 0.07-0.1 were best (0.082); 0.03-0.05 were worse (0.085-0.091: the state can no
longer resolve the phase inside the 120 ms beat), 0.15 slightly worse (0.086). A per-neuron log-uniform range [0.02, 0.3]
combining both timescales was the best single change (0.0811 over seeds 0-4, sd 0.0005) and is the first anchor.
*Confirmed.*

**H5. The readout is over-regularised.** With no feedback there is no divergence to guard against, and the ridge of 1e-3 was
biasing the rare long beats toward the mean. Ridge 1e-3 -> 1e-5 -> 1e-6 -> 1e-7 gave 0.099 -> 0.089 -> 0.083 -> 0.082; 1e-8
started to overfit (0.084-0.086, seed dependent). *Confirmed, optimum near 1e-7.*

**H6. Deeper or parallel reservoirs form richer features.** Two reservoirs with strong inter-scale (2.0), readout from both and
weak stimulus gain matched the single reservoir (0.082) but with a strong stimulus gain they were worse (0.087-0.11) and
erratic across seeds, and on the outlier-trimmed metric (below) they were always worse than the single reservoir (0.056-0.059
vs 0.053). Parallel banks (inter-scale 0) with different leaks gained nothing (0.096, like a single reservoir at that gain).
*Rejected*: the size is not the limit either (a 120-unit stimulus-driven reservoir scores 0.0824, 368 units 0.0818).

**H7. Other knobs.** Spectral radius: 0.85-0.9 best, 0.95-1.0 worse (0.085-0.09), above 1 much worse. Connectivity: flat
between 0.05 and 1.0 (dense marginally better, 0.080). Bias scale 0-0.5 flat, 2.0 worse. Recency weighting of the readout
(half-life 3000-8000 samples): no gain. Washout 500-2000: flat. Direct input-to-readout connection: irrelevant.

## What the method targets

The returned designs are stimulus-driven echo state networks: a single 368-unit reservoir (occasionally the search's
perturbations change knobs but never the family), no voltage feedback, stimulus gain 20-200 so each pacing pulse drives the
tanh units into saturation, per-neuron leaks spanning roughly 0.01-0.4 (memories from a few milliseconds to a few hundred
milliseconds), spectral radius about 0.9 and a ridge of about 1e-7. After a pulse the fast units trace out the phase inside
the beat (the readout draws the upstroke, plateau and repolarisation as a function of time since the pulse), while the slow
units still carry the saturated imprint of the previous pulses, so the state at any moment is a nonlinear function of the
last two or three inter-stimulus intervals. Because the protocol holds the diastolic interval fixed, those intervals are the
previous durations, and the linear readout can therefore select a long or a short beat shape according to the alternans
rule. Diagnostics on the dev windows: per-beat predicted durations correlate 0.87 with the recorded ones (RMSE 7 ms against
a standard deviation of 13 ms), versus 0.56 for the best feedback design.

This structure holds in the test window because it is a property of the pacing protocol and of the cell's restitution, not of
a particular stretch of the recording: the diastolic interval drifts only from 45 to 52 ms over the training recording (it
is 50-51 ms in the last 3 s, which the test window continues), and the alternation pattern in the last 30 beats is the same
as earlier. The open-loop design also degrades gracefully: with saturating units and no feedback, an interval outside the
training range produces a bounded, mean-like beat rather than a divergence.

## Validation performed

* Evaluator protocol (fixed): three origins (8227, 10284, 12341), 4113-sample causal roll-outs, mean RMSE.
* Development sweeps of about 700 evaluations in total through the same evaluator (seeds 0-2, some over seeds 0-4) built the
  design family and the anchor list; per-origin and per-beat diagnostics were used to interpret them.
* **Outlier decomposition.** The recording contains one extra-long beat (interval 180 ms, duration 131 ms, at about 13.1 s)
  inside the windows of the second and third dev origins. It is unpredictable from the stimulus history (the previous
  interval was ordinary), and it and the two beats after it account for most of the dev error there: the best designs score
  0.055 on the first origin and 0.092-0.096 on the other two, but 0.049-0.056 on those two once that beat and the two
  following are excluded. Rankings on the trimmed metric agree with the full metric within the family, so the search is not
  tuned to the outlier, but differences below about 0.001 between designs are noise.
* **Search runs as the verifier will run them** (`run_search.py`, seeds 0-4, budget 60): 60/60 evaluations each, no
  unmetered training, no framework shadowing, the returned configuration always one that was evaluated, 87 s per search when
  run alone (about 260 s with four searches sharing four cores). Returned dev RMSEs 0.0795-0.0800 (control 0.116-0.126); all five returned designs are single stimulus-driven reservoirs with gain 20-200, leak ranges inside [0.014, 0.4], ridge 0.8e-7 to 3e-7, spectral radius 0.90-0.91.
* **Pseudo-test of the search procedure itself:** the search was re-run for seeds 0-4 with an evaluator whose three origins lie earlier (4114, 6170, 8227), and the returned
  configuration was scored on the last 4113 training samples (12341-16454), which that search never saw. Mean over the five
  seeds: searched design 0.0972, the fixed first anchor 0.0957, the untuned default 0.1288 (this window contains the outlier
  beat). The searched designs are consistently 0.001-0.003 behind the anchor, which is the expected cost of selecting on a
  flat, noisy dev surface (the anchor itself was chosen with the full dev set, so the comparison favours it); a 1 % acceptance
  margin or refining only ridge, gain and leaks changed nothing (0.0977, 0.0979). The family, not the fine-tuning, carries
  the improvement, and the search reproduces it on every seed.

## Limitations

* The search cannot see the test window; the dev estimate is dominated by one unpredictable beat, so the fine-tuning phase
  distinguishes designs by differences that are partly noise. The acceptance margin limits, but does not remove, this.
* The forecast of a beat's duration relies on the alternans rule holding and on the diastolic interval staying near 50 ms.
  Beats that break the rule (such as the 180 ms interval in the training data) are mispredicted by every design tried, and the
  slow units then carry the wrong context for two or three more beats. A test window containing such a beat would score near
  0.08; one without would score near 0.055-0.06.
* Only stimulus timing enters the model: the network never observes the actual voltage during the test roll-out, so it cannot
  correct itself within a beat. This is inherent to the protocol (the feedback variants only feed back predictions, and we
  found them fragile).
* The evaluator's three origins share training data with each other and with the final model, so the dev RMSE is not an
  independent estimate of the test RMSE; it is the study's own selection criterion and is used only to select.
* All conclusions were drawn on a single cell and a single recording.
