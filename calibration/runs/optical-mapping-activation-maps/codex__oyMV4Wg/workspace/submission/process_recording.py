#!/usr/bin/env python3
"""Recover tissue, activation-time, and APD80 maps from the raw recording."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_fill_holes, gaussian_filter, label


HEIGHT = 128
WIDTH = 128
HEADER_BYTES = 1024
FOOTER_VALUES = 4
FPS = 529.09
DT_MS = 1000.0 / FPS
WINDOW_PRE = 60
WINDOW_POST = 300
TEMPORAL_SIGMA = 3.0
SPATIAL_SIGMA = 1.0
MASK_AMPLITUDE_COUNTS = 60.0


def open_recording(path: Path) -> np.memmap:
    """Return frame-zero-dropped camera pixels in their stored orientation."""
    stride = HEIGHT * WIDTH + FOOTER_VALUES
    n_values = (path.stat().st_size - HEADER_BYTES) // np.dtype("<u2").itemsize
    if n_values % stride:
        raise ValueError("File size is inconsistent with the documented frame stride")
    n_frames = n_values // stride
    stream = np.memmap(
        path, dtype="<u2", mode="r", offset=HEADER_BYTES, shape=(n_frames, stride)
    )
    return stream[1:, : HEIGHT * WIDTH]  # frame 0 is under-exposed


def detect_polarity(raw: np.ndarray, provisional_pixels: np.ndarray) -> float:
    """Choose +1/-1 so that the fast field-mean deflection points upward."""
    trace = raw[:, provisional_pixels].mean(axis=1, dtype=np.float64)
    # Beat averaging across tissue makes a separate temporal smoother unnecessary.
    derivative = np.diff(trace)
    upward_speed = np.percentile(derivative, 99.5)
    downward_speed = -np.percentile(derivative, 0.5)
    return -1.0 if downward_speed > upward_speed else 1.0


def detect_onsets(
    raw: np.ndarray, storage_mask: np.ndarray, polarity: float
) -> list[int]:
    """Detect integer samples after field-mean normalized 50% upward crossings."""
    trace = polarity * raw[:, storage_mask].mean(axis=1, dtype=np.float64)
    low, high = np.percentile(trace, [5.0, 95.0])
    normalized = (trace - low) / (high - low)
    candidates = np.flatnonzero(
        (normalized[:-1] < 0.5) & (normalized[1:] >= 0.5)
    ) + 1

    refractory_filtered: list[int] = []
    for onset in candidates:
        onset = int(onset)
        if not refractory_filtered or onset - refractory_filtered[-1] >= 250:
            refractory_filtered.append(onset)

    n_frames = raw.shape[0]
    return [
        onset
        for onset in refractory_filtered
        if onset >= WINDOW_PRE and onset + WINDOW_POST <= n_frames
    ]


def smooth_oriented_window(
    raw: np.ndarray, onset: int, polarity: float
) -> np.ndarray:
    window = raw[
        onset - WINDOW_PRE : onset + WINDOW_POST, : HEIGHT * WIDTH
    ].reshape(WINDOW_PRE + WINDOW_POST, HEIGHT, WIDTH)
    window = gaussian_filter(
        window.astype(np.float32),
        sigma=(TEMPORAL_SIGMA, SPATIAL_SIGMA, SPATIAL_SIGMA),
        mode="reflect",
    )
    return polarity * window


def interpolate_crossing(
    signal: np.ndarray, level: np.ndarray, later_index: np.ndarray
) -> np.ndarray:
    """Interpolate a crossing whose surrounding indices are j-1 and j."""
    rows, cols = np.indices(later_index.shape)
    j = np.clip(later_index, 1, signal.shape[0] - 1)
    y0 = signal[j - 1, rows, cols]
    y1 = signal[j, rows, cols]
    denominator = y1 - y0
    return (j - 1) + np.divide(
        level - y0,
        denominator,
        out=np.full(level.shape, np.nan, dtype=np.float32),
        where=np.abs(denominator) > 1e-7,
    )


def measure_window(signal: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Apply the frozen 50%-activation and 20%-APD definitions to one beat."""
    n_time = signal.shape[0]
    time_index = np.arange(n_time)[:, None, None]
    baseline = np.median(signal[:50], axis=0)
    peak_index = np.argmax(signal, axis=0)
    maximum = np.max(signal, axis=0)
    amplitude = maximum - baseline

    level50 = baseline + 0.5 * amplitude
    first_above50 = np.argmax(signal >= level50, axis=0)
    activation = interpolate_crossing(signal, level50, first_above50)

    level20 = baseline + 0.2 * amplitude
    at_or_below20 = signal <= level20
    pre_index = np.max(
        np.where(at_or_below20 & (time_index < peak_index[None]), time_index, -1),
        axis=0,
    )
    post_index = np.min(
        np.where(
            at_or_below20 & (time_index > peak_index[None]), time_index, n_time
        ),
        axis=0,
    )
    up20 = interpolate_crossing(signal, level20, pre_index + 1)
    down20 = interpolate_crossing(signal, level20, post_index)
    apd80 = down20 - up20

    valid = (
        (amplitude > 0)
        & (first_above50 > 0)
        & (pre_index >= 0)
        & (post_index < n_time)
        & np.isfinite(activation)
        & np.isfinite(apd80)
        & (apd80 > 0)
    )
    activation = np.where(valid, activation, np.nan).astype(np.float32)
    apd80 = np.where(valid, apd80, np.nan).astype(np.float32)
    return activation, apd80, amplitude.astype(np.float32)


def amplitude_mask(
    raw: np.ndarray, onsets: list[int], polarity: float
) -> np.ndarray:
    amplitudes = []
    for onset in onsets:
        signal = smooth_oriented_window(raw, onset, polarity)
        baseline = np.median(signal[:50], axis=0)
        amplitudes.append(np.max(signal, axis=0) - baseline)
    median_amplitude = np.median(np.stack(amplitudes), axis=0)

    # Transpose from camera storage to the requested analysis convention.
    thresholded = median_amplitude.T > MASK_AMPLITUDE_COUNTS
    components, n_components = label(thresholded)
    if n_components == 0:
        raise RuntimeError("No connected tissue component was found")
    sizes = np.bincount(components.ravel())
    largest = components == (np.argmax(sizes[1:]) + 1)
    return binary_fill_holes(largest).astype(bool)


def nanmean_stack(values: list[np.ndarray]) -> np.ndarray:
    stack = np.stack(values)
    finite = np.isfinite(stack)
    count = finite.sum(axis=0)
    total = np.nansum(stack, axis=0, dtype=np.float64)
    return np.divide(
        total,
        count,
        out=np.full(count.shape, np.nan, dtype=np.float64),
        where=count > 0,
    ).astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("/workspace/data/2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"),
    )
    parser.add_argument("--output", type=Path, default=Path("/workspace/submission"))
    args = parser.parse_args()

    raw = open_recording(args.input)

    # A loose signal-bearing set is sufficient for the first field trace.
    sampled = raw[::10].astype(np.float32)
    robust_range = np.percentile(sampled, 95, axis=0) - np.percentile(
        sampled, 5, axis=0
    )
    provisional_pixels = robust_range > 50.0
    polarity = detect_polarity(raw, provisional_pixels)
    preliminary_onsets = detect_onsets(raw, provisional_pixels, polarity)

    mask = amplitude_mask(raw, preliminary_onsets, polarity)
    storage_mask = mask.T.reshape(-1)
    onsets = detect_onsets(raw, storage_mask, polarity)
    if len(onsets) != 18:
        raise RuntimeError(f"Expected 18 complete beats, detected {len(onsets)}: {onsets}")

    activations: list[np.ndarray] = []
    durations: list[np.ndarray] = []
    for onset in onsets:
        activation, apd80, _ = measure_window(
            smooth_oriented_window(raw, onset, polarity)
        )
        activations.append(activation)
        durations.append(apd80)

    # Measurements are currently in camera storage orientation.
    activation_ms = (nanmean_stack(activations).T * DT_MS).astype(np.float32)
    apd80_ms = (nanmean_stack(durations).T * DT_MS).astype(np.float32)

    # Keep every reported in-mask value well-defined; this only removes a few
    # very-low-signal boundary pixels from the conservative initial mask.
    mask &= np.isfinite(activation_ms) & np.isfinite(apd80_ms)
    activation_ms[~mask] = np.nan
    apd80_ms[~mask] = np.nan

    args.output.mkdir(parents=True, exist_ok=True)
    np.save(args.output / "mask.npy", mask.astype(bool))
    np.save(args.output / "activation_ms.npy", activation_ms.astype(np.float32))
    np.save(args.output / "apd80_ms.npy", apd80_ms.astype(np.float32))

    print(f"Polarity multiplier: {polarity:+.0f}")
    print(f"Usable onsets after dropped frame 0: {onsets}")
    print(f"Mask pixels: {mask.sum()} / {mask.size}")
    print(
        "Activation ms percentiles:",
        np.percentile(activation_ms[mask], [1, 25, 50, 75, 99]),
    )
    print(
        "APD80 ms percentiles:",
        np.percentile(apd80_ms[mask], [1, 25, 50, 75, 99]),
    )


if __name__ == "__main__":
    main()
