# Ground truth — tier_2_task_1

Built by `make_gt.py` from the expert-processed `.mat`. Regenerate with:

    python gt/make_gt.py

## Files

| file | shape | meaning |
|---|---|---|
| `activation_ms.npy` | (128,128) f32 | activation time, ms, NaN off-tissue |
| `apd80_ms.npy` | (128,128) f32 | APD80, ms |
| `cv_cm_s.npy` | (128,128) f32 | conduction velocity, cm/s (see caveat) |
| `mask.npy` | (128,128) bool | tissue mask, 6104 px |
| `beats.json` | — | onsets used/dropped, noise floors, provenance |

## Frozen definitions

* **Activation time** = 50% of upstroke amplitude, linearly interpolated between
  frames. **Not** `argmax(dV/dt)`: the upstroke spans ~66 frames, so the derivative
  peak is a flat noise-dominated plateau and its beat-to-beat scatter is 6.8 ms
  versus 1.56 ms for the 50% crossing.
* **APD80** = time from the 50% upstroke crossing to 80% repolarisation.
* **Beat rule** = 50% *upward* crossing of the field-mean trace (the .mat is
  upright), 250-frame refractory; a beat counts only if ≥300 frames remain after
  its onset. For this recording **all 18 detected beats qualify** — the last onset
  is at frame 7123.65 of 7503, leaving 379 frames.
* Maps are the **mean over those 18 beats**.

## Anchors

| metric | baseline (constant prediction) | noise floor (beat-to-beat) | ratio |
|---|---|---|---|
| activation time | 19.33 ms | 1.01 ms | 22.5 |
| APD80 | 12.17 ms | 2.27 ms | 4.1 |

Noise floors are `noise_floor_*` in `beats.json`, regenerated with the maps.
An earlier revision of this file quoted 1.56 / 2.69 ms noise floors, baselines of
22.67 / 9.21 ms, and "17 usable beats, dropping onset 7353.97". All of that
described a superseded beat rule and does not match the shipped ground truth. The
numbers above are recomputed from the maps `make_gt.py` produces now: the
constant-prediction baseline is by definition the spatial SD of each map
(`spatial_sd_*` in `beats.json`), and the floors are `noise_floor_*`.

## Caveats

* `pixel_mm = 0.15` in `make_gt.py` is a **placeholder** — the true pixel pitch was
  not recorded with the data. Conduction velocity therefore has an unknown scale
  factor and is reported for reference only; it must not be a scored metric until
  the real pitch is supplied. Activation time and APD80 are unaffected.
* The raw `.dat` is **transposed** relative to the `.mat` and the mask, and its
  frame 0 is an under-exposed bad frame. `.mat[t] == transpose(.dat)[t + 71]`.
