# Spiral-Tip Pattern Benchmark

Can a model reproduce a **qualitative dynamical observable** from a PDE, instead
of just writing code that runs?

Each task gives a spiral wave in a 2D excitable medium. The model runs its own
simulation at given parameters and has to reproduce the **shape of the spiral tip
trajectory**. Getting it right needs a correct solver, a correct spiral
initiation, correct tip detection, and enough integration past the transient. Get
any one wrong and the simulation still runs and still looks like a spiral, but
the tip pattern comes out wrong.

Grading is on pattern class, not pointwise error. Two dynamically identical runs
can differ by a phase shift or a translation and have huge pointwise error, so
nRMSE-style metrics are the wrong tool here.

## Files in this folder

| File              | What it is                                                     |
| ----------------- | -------------------------------------------------------------- |
| `INSTRUCTIONS.md` | the prompt handed to the model                                 |
| `ref.png`         | ground-truth tip trajectories. This is what has to be matched. |
| `table_data.tex`  | parameters, one row per pattern                                |
| `./2D-3V-Model`   | self-contained WebGL simulator that produced the references    |

Human baseliners get exactly the same four files.

## What comes back

For each pattern, one output folder containing:

- `trajectory.png` — the tip trajectory plot, transient removed
- `snapshot.png` — one field snapshot showing the spiral
- `tip_trace.csv` — `t,x_tip,y_tip` over the whole run, transient included
- `frames/` — field downsampled to 128x128, saved every ~100 tip samples
- the solver code that was actually run, plus a run log

`frames/` is what makes the run auditable. A tip trace with no field behind it
can't be checked.

## Grading

Three stages, all must pass.

**1. Provenance (LLM judge).** Gets the code, `tip_trace.csv`, a sample of
`frames/`, and the log. It answers one question: was this trajectory produced by
simulating the specified model at the specified parameters?

Automatic fail: trajectory generated from a closed-form curve (epicycloid,
Lissajous, spirograph) instead of a field; hardcoded coordinates; any read of
`ref.png`; parameters that don't match the table; `frames/` missing or
inconsistent with the tip trace; the plot drawn from something other than
`tip_trace.csv`.

Not a fail: different tip-detection convention, different grid or `dt`, different
language, longer or shorter run.

**2. Pattern match (human expert).** Reference and submission side by side,
binary pass.

May differ: position, rotation, starting phase, number of circuits traced, image
size, colors, line style, small scale differences.

Must match: the pattern class, and for flowers the petal count.

| Code   | Pattern                             |
| ------ | ----------------------------------- |
| `C`    | circular core, rigid rotation       |
| `Fi-n` | flower, `n` petals pointing inward  |
| `Fo-n` | flower, `n` petals pointing outward |
| `L`    | linear or near-linear core          |
| `D`    | net drift on top of rotation        |
| `H`    | hypermeander, no repeating pattern  |

Blind the expert to which model produced which image and randomize the order.

**3. Report.** Sample k=8 per pattern per model. Report pass@1 and pass@8, a
per-class breakdown of what fails, and the provenance-fail rate **separately** —
how often a model fakes it is its own finding, not something to fold into the
pass rate.

## Human baseline

Same four files, same output format, same grading. Log active time, not elapsed.
Two tiers reported separately: domain expert (has worked with excitable media or
cardiac models) and general programmer (comfortable with Python and numerics, no
domain background). With per-pattern human times you can fit model success
against `log(human time)` and read off a 50% time horizon.

## Known issues to settle

- `ref.png` must be stripped of metadata, and every panel plotted in an identical
  style. If circular cores get a different aspect ratio than linear ones, the
  pattern is guessable without simulating anything.
- Published parameter sets and their figures are in the training data. Check for
  contamination: ask for the pattern class from the parameters alone, no
  simulation. If it beats chance, resample those parameters.
- `ref.png` means vision-capable models only. Record that in the results table.
- The references came from the WebGL simulator in single precision. A
  reimplementation can land on a different pattern near a meander bifurcation, so
  keep sampled parameters away from boundaries.
- Does petal count have to match exactly, or within one? This decides how close
  to a bifurcation the sampling can get.
