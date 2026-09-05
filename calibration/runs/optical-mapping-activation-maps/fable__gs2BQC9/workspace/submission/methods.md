# Activation and APD80 maps from `2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat`

Reproducible code: `load.py` (raw reader) and `pipeline.py` (everything else).
Final maps were produced with `python3 pipeline.py --sig_t 3 --sig_s 1.5`.

## Approach

1. **Read the raw stream.** 1024-byte header, then 7,620 frames of 128x128 little-endian
   uint16 plus a 4-element footer (32,776 bytes per frame). Each frame is transposed to the
   analysis convention and frame 0 (under-exposed) is dropped, leaving 7,619 frames.
2. **Sign.** On a pixel trace the deflection has a fast falling edge and a slow recovery,
   and the frame-to-frame derivative of the field mean is strongly negatively skewed
   (min -9.8 vs max +5.6 counts/frame). Depolarisation is therefore a *downward*
   deflection in this file; the whole stack is negated so that depolarisation is upward.
3. **Tissue mask.** Beat-averaged upstroke amplitude per pixel (window max minus baseline
   median, averaged over provisional beats). The log-amplitude histogram is cleanly bimodal;
   an Otsu threshold (54.7 counts) separates the modes. Binary opening, keep components of
   at least 200 px, fill holes, closing, fill holes. Result: 7,409 px (45% of the frame),
   a single blob following the visible preparation.
4. **Beat onsets.** Field mean over mask pixels, normalised between its 5th and 95th
   percentiles, 50% upward crossing, 250-frame refractory. 19 onsets are found
   (interval 409-411 frames); the last (frame 7,602) has only 17 frames after it and is
   discarded, leaving the 18 usable beats.
5. **Denoising.** Gaussian smoothing in time (sigma 3 frames, 5.7 ms) and space
   (sigma 1.5 px), applied before the definitions. The spatial filter is a normalised
   convolution restricted to the mask so that edge pixels are not diluted by background.
6. **Definitions, applied per beat and per pixel** on the smoothed stack, in a window
   from 60 frames before onset to 300 frames after: baseline = median of the first 50
   frames; amplitude = window max minus baseline; activation = first upward crossing of
   baseline + 50% amplitude, linearly interpolated between the two bracketing frames;
   APD80 = (first frame at or below baseline + 20% amplitude after the peak) minus
   (last frame at or below that level before the peak), times 1.8900 ms.
7. **Report** the mean over the 18 beats, NaN off-mask, float32.

## What the method targets

- Baseline/amplitude: step 6 uses exactly the median of the first 50 window frames and the
  window maximum, per pixel and per beat.
- Activation time: the 50% level crossing with linear interpolation, not the derivative
  peak. The smoothing in step 5 only reduces noise; it does not change the estimator.
- APD80: frame-index difference between the two 20% crossings around the peak, converted
  with the 529.09 fps frame period; no interpolation, as the definition is stated in frames.
- Mean over usable beats: all 18 beats have 300 frames after onset and are all used; onsets
  come from the field-mean trace exactly as specified.
- The denoising is the one degree of freedom not fixed by the definitions. It was chosen
  because the 20% repolarisation crossing sits on a slow tail (about 0.6% of amplitude per
  frame), where noise makes the "first frame at or below" crossing fire early; smoothing
  removes that bias without distorting the waveform (checked below).

## Validation performed

No reference was available; checks used internal consistency only.

- **Beat structure.** 18 usable beats at a very regular 410-frame (775 ms) cycle length;
  the inverted field-mean trace has a fast upstroke (~50 frames from 3% to 90%) and a slow
  repolarisation, as an action potential should.
- **Maps look physiological.** Activation propagates smoothly from the right edge to the
  left (5th-95th percentile spread about 60 ms, total about 80 ms); APD80 is 510 ms at the
  median with a sharp spatial step (500 vs 480 ms) near column 80. Every in-mask pixel has
  a finite activation and APD80 value.
- **Split-half noise** (odd vs even beats, RMSE of the difference / 2, median offset
  removed for activation): 0.25 ms activation, 1.94 ms APD80 over the whole mask;
  0.14 ms and 1.30 ms in the tissue core (more than 6 px from the boundary).
- **Sensitivity to the denoising level.** Compared with the final (3 frames, 1.5 px)
  setting, (2, 1) differs by 0.34 ms activation / 1.39 ms APD80 RMS in the core, (3, 1) by
  0.17 / 0.78 ms and (3, 2) by 0.14 / 0.57 ms. All well below the pass gates.
- **Noise bias of the 20% crossing.** Without smoothing the APD80 median is 466 ms, i.e.
  about 45 ms shorter than with smoothing, confirming the early-crossing bias. Applying the
  definitions to the 18-beat average waveform (noise reduced ~4x) gives a core APD80 median
  within 1 ms of the per-beat mean at the final setting, so the residual bias in the core is
  about 1 ms. Temporal sigma 5 or more starts to distort the waveform (+2 ms), so sigma 3
  was kept.
- **Format** checked with `selfcheck.py`.

## Budget used

About 15 minutes of wall-clock time: the timer showed 7,170 s remaining when work started and
about 6,450 s when the submission was written. Each full pipeline run takes about 15 s on
4 CPU cores and under 2 GB RAM; roughly 15 runs were made for the smoothing sweep and checks.

## Limitations

- The mask is deliberately generous (45% of the frame). The outer 3-5 px ring has low
  signal-to-noise: beat-to-beat SD of activation up to 9 ms there and a remaining
  early-crossing APD80 bias of roughly 10 ms (per-beat mean 499 ms vs 508 ms from the
  beat-averaged waveform). If the reference boundary includes that ring, APD80 agreement
  there will be worse than in the core.
- The denoising level is a judgment call; the exact filter used for the reference is
  unknown. Differences among plausible modest settings are below 0.4 ms (activation) and
  2 ms (APD80) in the core, but a reference with much lighter smoothing would carry a
  larger noise-induced APD80 shortening than these maps.
- Spatial smoothing (1.5 px) slightly blurs the sharp APD80 step near column 80.
- The 60-frame pre-onset baseline window overlaps the end of the previous beat's tail at
  this cycle length; this is inherent to the frozen definition and was not corrected.
- Pixel pitch is unknown; no conduction velocity was computed.
