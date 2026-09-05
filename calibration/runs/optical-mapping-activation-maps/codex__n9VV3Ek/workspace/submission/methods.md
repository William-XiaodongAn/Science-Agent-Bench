## Approach

I memory-mapped the little-endian stream after its 1024-byte header, discarded the four footer words per frame, and removed under-exposed frame 0. Each 128 by 128 frame was transposed into the analysis convention. Representative spatially averaged waveforms showed a rapid fluorescence decrease followed by slow recovery, so I negated fluorescence to make depolarisation upward. The tissue mask is the largest connected region whose spatially smoothed 5th-to-95th-percentile temporal excursion exceeds 60 camera counts; enclosed holes are filled. This conservative boundary covers 56.2% of the image and intentionally includes a low-SNR rim so as not to discard tissue edge pixels.

The field mean over this mask was normalised using its 5th and 95th percentiles. Upward 50% crossings separated by at least 250 frames yielded 18 complete onsets. For each onset I extracted frames -60 through +299, with extra padding solely for filtering, inverted the signal, and applied a Gaussian filter with temporal sigma 3 frames and spatial sigma 1 pixel. Per-beat measurements were averaged and stored as float32 arrays; off-mask entries are NaN.

## What the method targets

Within every 360-frame beat window, the baseline is the per-pixel median of its first 50 frames and amplitude is the window maximum minus that baseline. Activation is the first upward crossing of baseline plus 50% amplitude and is linearly interpolated between its bracketing samples. APD80 is the elapsed time from the last sample at or below baseline plus 20% amplitude before the peak to the first sample at or below that level after the peak. Frame measurements use 1000/529.09 = 1.89004 ms per frame. Activation is reported relative to the detected beat onset before averaging; this only selects a convenient global zero and preserves the scored spatial pattern.

## Validation performed

I checked the byte count against exactly 7,620 complete records, checked the frame transpose explicitly in all spatial operations, and excluded frame 0. The polarity decision was based on waveform morphology rather than an assumed dye sign. Detection produced the expected 18 usable onsets, approximately frames 224, 634, 1044, 1454, 1862, 2274, 2683, 3091, 3504, 3914, 4322, 4734, 5144, 5554, 5964, 6372, 6784, and 7193 after dropping frame 0. The later crossing is too close to the recording end and was correctly rejected.

As reference-free repeatability validation, odd- and even-beat mean maps were compared. In the high-signal core (robust excursion at least 100 counts), half their difference gave about 0.2 ms activation RMSE after removal of its median offset and about 1.6 ms APD80 RMSE. I also checked in-mask finiteness, plausible APD scale, onset refractory spacing, and NaNs outside the tissue mask. Repeatability is worse in the deliberately retained low-signal outer rim, which is why the core result is stated separately rather than presented as whole-mask precision.

## Budget used

The solution used CPU-only NumPy and SciPy, no internet and no GPU. It processes one padded beat at a time instead of materialising the roughly 500 MB recording as float32. A full reproducible run takes roughly 15 seconds in the supplied sandbox and stays comfortably below the 16 GB memory allowance; exploratory checks and parameter validation used only a small fraction of the available wall-clock budget.

## Limitations

The mask is an intensity-excursion segmentation rather than a hand-traced anatomical boundary, so it deliberately includes some noisy peripheral pixels and may differ locally from a manual outline. Gaussian smoothing improves crossing precision but can slightly blend measurements across sharp spatial boundaries and broadens very fast temporal features. Low-amplitude rim pixels can lack a valid post-peak 20% crossing and remain NaN. No external reference was available for optimisation or scoring, and the absent pixel pitch prevents reporting conduction velocity in physical units.
