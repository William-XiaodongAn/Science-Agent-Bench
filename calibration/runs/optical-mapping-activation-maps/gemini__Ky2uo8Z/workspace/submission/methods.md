## Approach
We processed raw optical mapping camera data of a beating cardiac tissue to extract spatial-temporal activation and action potential duration (APD80) maps. Frame 0 was discarded due to underexposure, and each subsequent frame was transposed to line up with the standard analysis convention. The raw signal was inverted to align with the physiological convention that depolarisation is an upward deflection. We applied a 3D Gaussian filter (sigma_t=1.5 frames, sigma_s=1.0 pixels) in both time and space to suppress noise. Onsets were detected on the normalized field-mean trace by finding 50% upward crossings with a 250-frame refractory period. For each detected beat, we extracted a window of 360 frames (starting 60 frames before the onset to 300 frames past). Baseline and amplitude were computed, and activation time and APD80 were calculated for each pixel.

## What the method targets
- **Baseline and Amplitude**: Baseline was computed as the median of the first 50 frames of the extraction window; amplitude was the maximum minus baseline.
- **Activation time**: Detected as the moment the signal first crosses 50% of its upstroke amplitude. Linear interpolation was applied between the two frames around the crossing to achieve sub-frame accuracy.
- **APD80**: Computed as the duration (in ms) the pixel spends above 20% of its upstroke amplitude, measured from the last frame at or below 20% before the peak to the first frame at or below it after the peak.
- **Beat averaging**: Signal processed across all 18 complete usable beats.

## Validation performed
- Verified frame dimensions and dropout of frame 0.
- Assessed upstroke/repolarisation direction to confirm signal inversion.
- Visualized the tissue mask via an ASCII downsampled representation of the pixel standard deviation map.
- Checked that exactly 18 usable beats were detected.
- Verified that the median in-mask APD80 is physically realistic (~500 ms) and that activation times are reasonably distributed.

## Budget used
- Memory used: ~500 MB of 16 GB.
- Execution time: ~5 seconds.
- Wall-clock time: ~10% of budget.

## Limitations
- Spatial-temporal Gaussian filtering parameters are fixed and could be optimized.
- Boundary pixels on the edge of the tissue may have lower signal-to-noise ratios, causing minor boundary estimation inaccuracies.
