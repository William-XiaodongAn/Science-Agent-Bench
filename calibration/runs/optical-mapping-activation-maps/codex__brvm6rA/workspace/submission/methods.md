## Approach

I memory-mapped the little-endian stream after its 1024-byte header, discarded frame 0, removed each frame's four-word footer, reshaped to 128 by 128, and transposed every frame into the analysis convention. Inspection of representative traces and the field mean showed a rapid downward fluorescence deflection followed by slow recovery, so I negated the data to make depolarisation upward.

The mask is the filled largest connected component of a robust signal-amplitude image (temporal 95th minus 5th percentile, sampled every fifth frame and spatially Gaussian-smoothed with sigma 1 pixel) thresholded at 80 camera counts. This deliberately includes the low-SNR boundary rather than selecting only the easy centre. For timing, I Gaussian-smoothed the oriented movie with sigma 3 frames in time and 1 pixel in each spatial axis. The script detects beats, measures every complete beat independently, and saves the mean maps as float32 with NaN outside the Boolean mask.

## What the method targets

The field trace is the mean over mask pixels and is normalised using its 5th and 95th percentiles. Beat onsets are its upward 50% crossings, retaining crossings at least 250 frames apart and only onsets with a complete window from 60 frames before through 300 frames after. This found all 18 expected complete beats.

In each 360-frame beat window and at each pixel, the baseline is the median of its first 50 samples and amplitude is the smoothed-window maximum minus that baseline. Activation is the first upward crossing of baseline plus 50% amplitude, linearly interpolated between its bounding samples. APD80 uses baseline plus 20% amplitude: its start is the last at-or-below-threshold frame before the peak and its end is the first at-or-below-threshold frame after the peak. Their frame-index difference is converted with 1000/529.09 ms per frame. Maps are arithmetic means across the 18 beats.

## Validation performed

I checked the byte-derived frame count (7,620), removal of the anomalous first frame, footer handling, transpose, and sign against the recording's dimensions and waveform morphology. Detected post-drop onset left indices were 223, 633, 1043, 1453, 1861, 2272, 2682, 3091, 3503, 3913, 4321, 4733, 5142, 5552, 5962, 6371, 6783, and 7192; intervals are physiologically consistent and the final window is complete. All in-mask pixels are finite in both output maps.

As a no-reference repeatability test, I compared odd- and even-beat mean maps and divided their difference by two to estimate the noise of an 18-beat mean. After removing the activation offset, RMSE on a higher-confidence signal core (robust amplitude above 100 counts; 6,203 pixels) was 0.21 ms for activation and 1.65 ms for APD80. Across the deliberately inclusive 7,540-pixel mask it was 2.42 ms and 4.15 ms, respectively; inspection localized the excess to a small low-signal outer fringe. I also visually checked that activation is a smooth propagating wave and that APD80 lacks isolated failure pixels. No reference maps were used.

## Budget used

CPU-only NumPy/SciPy processing was used. The full oriented float32 movie occupies about 500 MB, and smoothing plus working arrays remained well inside the 16 GB memory allowance. Parameter selection used a small comparison of temporal Gaussian sigmas from 1.5 to 3.5 frames and spatial sigmas near 1 pixel, evaluated by split-half repeatability.

## Limitations

The amplitude threshold is in camera counts and is specific to this exposure; an acquisition with different gain would need a rescaled or adaptive threshold. The inclusive mask trades noisier estimates at its outermost fringe for high tissue coverage. Gaussian smoothing introduces a small degree of spatial mixing near boundaries, and APD80 remains less repeatable than activation because its 20% recovery threshold lies on the slow noisy tail. Activation times retain an arbitrary common window-relative offset, as allowed by the scoring definition.
