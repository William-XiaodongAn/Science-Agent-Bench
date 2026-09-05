# Task Instructions

You are given spiral waves in a 2D excitable medium. Run your own simulation and
reproduce the **shape of the spiral tip trajectory** shown in the reference
image.

## What you have

| File              | What it is                                                                      |
| ----------------- | ------------------------------------------------------------------------------- |
| `ref.png`         | ground-truth tip trajectories, one per pattern. This is what you have to match. |
| `table_data.tex`  | the parameters, one row per pattern                                             |
| `simulation.html` | a self-contained WebGL simulator that produced the references                   |

Match each pattern in `ref.png` to its row in `table_data.tex` by the label.

You may run `simulation.html`, port it, or write your own solver in any language.
Nothing about the method is prescribed. The references came out of the WebGL
simulator in single precision, so a reimplementation can land on a different
pattern at identical parameters. If your result looks borderline, running the
provided simulator is the safest route.

## What to produce

One folder per pattern, named by its label in the table. In each:

**`tip_trace.csv`** — the tip trajectory, one row per sample:

```
t,x_tip,y_tip
0.00,6.0121,5.9873
1.00,6.0344,5.9910
```

Cover the whole run. Include the transient; don't trim it from this file.

**`trajectory.png`** — the plot of `tip_trace.csv` with the transient removed.
Equal aspect ratio. No axes or labels needed. This is the image that gets
compared to the reference.

**`snapshot.png`** — one field snapshot from after the transient, showing the
spiral.

**`frames/`** — the field downsampled to at most 128x128, saved at least every
100 tip samples, as `frame_<t>.npy`. This is what lets a reviewer confirm your
tip trace came from a real simulation. Without it the submission fails.

**your solver code** — everything you actually ran. If you used
`./2D-3V-Model` unmodified, say so.

**`run_log.txt`** — the parameters you used, grid, `dt`, step count, wall time.

## What counts as a match

Not pixel for pixel. Your trajectory may sit at a different position, be rotated,
start at a different phase, trace a different number of circuits, and be plotted
at a different size or in different colors.

The pattern itself has to be the same. If the reference is a five-petal inward
flower, yours must be a five-petal inward flower. Circular is not linear, inward
petals are not outward petals, a meander is not a hypermeander.

A human expert makes this call.

## Rules

You may do anything to make your **simulation** correct. You may not do anything
that makes the **picture** correct without a simulation behind it.

So this is fine: any language, library, precision, grid, or time step; any
tip-detection convention; any spiral initiation protocol; running longer than
asked if you need more of the pattern; looking at the reference to understand
what you're aiming for; iterating — run, look at your own trajectory, fix the
code, run again.

And this is not: writing out a trajectory from a closed-form curve (epicycloid,
Lissajous, spirograph) instead of from a simulated field; hardcoded coordinate
arrays; reading or tracing `ref.png`; changing the parameters to get a nicer
picture; plotting anything other than the contents of `tip_trace.csv`; editing
images after they're produced.

## Before you submit

All of these still produce a plausible-looking spiral, so they're worth checking:

- transient not removed, so the initial inward relaxation reads as part of the
  pattern
- run too short to close a full meander cycle, so a flower reads as an arc
- domain too small, spiral interacted with the boundary
- periodic boundaries where they should be no-flux
- `dt` over the stability limit, so the pattern is a numerical artifact
- tip detector returning a different branch on different frames instead of
  tracking one singularity, giving a trajectory that jumps
- tip detector locking onto a spurious intersection in the wave back
