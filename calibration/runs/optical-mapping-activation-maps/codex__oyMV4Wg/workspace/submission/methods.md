## Approach

I memory-mapped the little-endian stream after its 1024-byte header, ignored each
four-value frame footer, dropped the under-exposed frame 0, and retained the
camera's stored orientation until the final transpose. The field waveform has a
slow positive fluorescence recovery and a much faster negative deflection. I
therefore multiplied the raw values by -1 so that the fast depolarisation points
upward; the script also reproduces this decision by comparing the robust speeds
of the two field-mean slopes.

A loose temporal-range mask supplied the initial field mean. I normalized that
trace with its 5th and 95th percentiles, detected upward 0.5 crossings, and
enforced the 250-frame refractory period. After requiring 60 pre-onset and 300
post-onset samples, this gave 18 beats. I Gaussian-smoothed every beat window
with sigma 3 frames in time and 1 pixel in both spatial directions. The tissue
mask is the hole-filled largest component whose median smoothed beat amplitude
exceeded 60 camera counts. I then redetected onsets over this final tissue set
and measured and averaged all 18 beats. Maps were transposed into analysis
orientation before saving.

## What the method targets

- The baseline is the per-pixel median of window samples 0 through 49, and the
  amplitude is the smoothed window maximum minus that baseline.
- Activation is the first baseline-plus-50%-amplitude upward crossing. Its time
  is linearly interpolated between the samples bracketing the threshold; no
  derivative maximum is used.
- APD80 uses baseline plus 20% of amplitude. I locate the last sample at or
  below that level before the peak and the first such sample after the peak,
  linearly interpolate both crossings, and take their time difference.
- Crossing indices are converted with 1000/529.09 = 1.8900376 ms per frame,
  and each output value is the arithmetic mean of valid measurements over the
  18 complete beats. Off-tissue output values are NaN.

## Validation performed

The final onsets were 223, 634, 1044, 1454, 1862, 2273, 2683, 3092, 3504,
3913, 4323, 4734, 5143, 5553, 5963, 6372, 6784, and 7193 after dropping frame
0. Intervals were 408--412 frames, and the last onset retained 426 subsequent
frames. The mask contains 6,841 pixels, and both float maps are finite at 100%
of those pixels and NaN everywhere else.

I compared maps averaged from alternating nine-beat halves. After removing the
activation difference's median offset, half-map RMSE divided by two was 0.22 ms
for activation and 1.72 ms for APD80. Median within-pixel beat standard
deviations were 1.25 ms and 4.84 ms, respectively. The two halves' mean APD80
differed by -1.88 ms. Visual checks showed a continuous activation wavefront
and no isolated mask islands. No scoring/reference maps were available, so an
absolute APD80 bias against reference could not be estimated.

## Budget used

The reproducible production run took about 20 seconds on the CPU sandbox and
used a memory map plus one 360-frame float32 window at a time. Including
exploration and validation, approximately seven minutes of the available wall
clock budget were used; no GPU or internet access was used.

## Limitations

The 60-count mask threshold is recording-specific, and uncertainty is greatest
at the low-signal tissue boundary. Gaussian smoothing trades a small amount of
spatial and temporal resolution for stable threshold crossings, especially on
the slow 20% repolarisation tail. Split-half checks quantify repeatability but
cannot reveal common-mode bias or disagreement with an unavailable hand-drawn
boundary/reference map.
