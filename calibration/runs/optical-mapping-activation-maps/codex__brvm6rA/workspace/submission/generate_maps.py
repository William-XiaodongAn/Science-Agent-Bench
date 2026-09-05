#!/usr/bin/env python3
"""Recover tissue, activation-time, and APD80 maps from the raw recording."""

from pathlib import Path

import numpy as np
from scipy.ndimage import binary_fill_holes, gaussian_filter, label


DATA = Path("/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat")
OUT = Path("/workspace/submission")
N_FRAME = 7620
NY = NX = 128
RECORD_WORDS = NY * NX + 4
DT_MS = 1000.0 / 529.09


def read_recording() -> np.ndarray:
    """Return frames after the bad first frame, transposed and sign-corrected."""
    raw = np.memmap(
        DATA, dtype="<u2", mode="r", offset=1024,
        shape=(N_FRAME, RECORD_WORDS),
    )
    # Camera fluorescence deflects downward during depolarisation.  Negation
    # makes the physiological upstroke positive.  Swap camera x/y here too.
    frames = np.asarray(raw[1:, : NY * NX], dtype=np.float32)
    frames = frames.reshape(-1, NY, NX).transpose(0, 2, 1)
    return -frames


def tissue_mask(oriented: np.ndarray) -> np.ndarray:
    """Inclusive mask from robust temporal signal amplitude."""
    sample = oriented[::5]
    dynamic_range = np.percentile(sample, 95, axis=0) - np.percentile(
        sample, 5, axis=0
    )
    dynamic_range = gaussian_filter(dynamic_range.astype(np.float32), 1.0)
    # Negation reverses percentiles, but the range remains positive.  Keep the
    # dominant connected signal-bearing object and fill its internal holes.
    candidates = dynamic_range > 80.0
    components, count = label(candidates)
    if count == 0:
        raise RuntimeError("No signal-bearing component found")
    sizes = np.bincount(components.ravel())
    mask = components == (1 + np.argmax(sizes[1:]))
    return binary_fill_holes(mask).astype(bool)


def beat_onsets(oriented: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Detect field-mean 50% upward crossings with 250-frame refractory."""
    trace = oriented[:, mask].mean(axis=1, dtype=np.float64)
    p5, p95 = np.percentile(trace, (5, 95))
    normalised = (trace - p5) / (p95 - p5)
    candidates = np.flatnonzero(
        (normalised[:-1] < 0.5) & (normalised[1:] >= 0.5)
    )
    kept: list[int] = []
    for crossing_left_frame in candidates:
        i = int(crossing_left_frame)
        if not kept or i - kept[-1] >= 250:
            kept.append(i)
    # A window uses [onset-60, onset+300); retain only complete windows.
    return np.asarray(
        [i for i in kept if i >= 60 and i + 300 <= oriented.shape[0]],
        dtype=np.int32,
    )


def one_beat_maps(window: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Apply the frozen per-beat crossing definitions to one 360-frame window."""
    baseline = np.median(window[:50], axis=0)
    peak_index = np.argmax(window, axis=0)
    peak = np.take_along_axis(window, peak_index[None], axis=0)[0]
    amplitude = peak - baseline

    # Activation: first upward 50% crossing, with linear interpolation.
    level50 = baseline + 0.50 * amplitude
    upward50 = (window[:-1] < level50) & (window[1:] >= level50)
    act_left = np.argmax(upward50, axis=0)
    y0 = np.take_along_axis(window, act_left[None], axis=0)[0]
    y1 = np.take_along_axis(window, (act_left + 1)[None], axis=0)[0]
    fraction = np.divide(
        level50 - y0, y1 - y0,
        out=np.zeros_like(level50), where=(y1 != y0),
    )
    activation_frames = act_left.astype(np.float32) + fraction

    # APD80: specified bounding frame indices at the 20% level.  On the
    # upstroke use the last <= sample before the peak; on recovery use the
    # first <= sample after it.
    level20 = baseline + 0.20 * amplitude
    time = np.arange(window.shape[0], dtype=np.int16)[:, None, None]
    pre_ok = (time <= peak_index) & (window <= level20)
    rise_frame = np.where(pre_ok, time, -1).max(axis=0)
    post_ok = (time >= peak_index) & (window <= level20)
    fall_frame = np.where(post_ok, time, window.shape[0]).min(axis=0)
    apd_frames = (fall_frame - rise_frame).astype(np.float32)

    valid_act = upward50.any(axis=0) & (amplitude > 0)
    valid_apd = (rise_frame >= 0) & (fall_frame < window.shape[0]) & (amplitude > 0)
    activation_frames[~valid_act] = np.nan
    apd_frames[~valid_apd] = np.nan
    return activation_frames * DT_MS, apd_frames * DT_MS


def measure(
    oriented: np.ndarray,
    mask: np.ndarray,
    onsets: np.ndarray,
    sigma_time: float = 3.0,
    sigma_space: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Smooth once, measure all beats, and return means plus beat stacks."""
    smooth = gaussian_filter(
        oriented, sigma=(sigma_time, sigma_space, sigma_space),
        mode="nearest", output=np.float32,
    )
    activation_beats, apd_beats = [], []
    for onset in onsets:
        window = smooth[onset - 60 : onset + 300]
        activation, apd = one_beat_maps(window)
        activation_beats.append(activation)
        apd_beats.append(apd)
    activation_stack = np.stack(activation_beats)
    apd_stack = np.stack(apd_beats)
    with np.errstate(invalid="ignore"):
        activation_mean = np.nanmean(activation_stack, axis=0)
        apd_mean = np.nanmean(apd_stack, axis=0)
    activation_mean[~mask] = np.nan
    apd_mean[~mask] = np.nan
    return (
        activation_mean.astype(np.float32),
        apd_mean.astype(np.float32),
        activation_stack.astype(np.float32),
        apd_stack.astype(np.float32),
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    oriented = read_recording()
    mask = tissue_mask(oriented)
    onsets = beat_onsets(oriented, mask)
    if len(onsets) != 18:
        raise RuntimeError(f"Expected 18 complete beats, detected {len(onsets)}: {onsets}")
    activation, apd80, _, _ = measure(oriented, mask, onsets)
    np.save(OUT / "mask.npy", mask)
    np.save(OUT / "activation_ms.npy", activation)
    np.save(OUT / "apd80_ms.npy", apd80)
    print(f"mask pixels: {mask.sum()}")
    print(f"complete beat onsets (post-drop frame): {onsets.tolist()}")
    print(f"activation finite in mask: {np.isfinite(activation[mask]).mean():.4f}")
    print(f"APD80 finite in mask: {np.isfinite(apd80[mask]).mean():.4f}")


if __name__ == "__main__":
    main()
