#!/usr/bin/env python3
"""Recover tissue, activation-time, and APD80 maps from the raw recording."""

from pathlib import Path

import numpy as np
from scipy.ndimage import binary_fill_holes, gaussian_filter, label


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"
OUT = Path(__file__).resolve().parent

HEIGHT = WIDTH = 128
HEADER_BYTES = 1024
FRAME_WORDS = HEIGHT * WIDTH + 4
N_FRAMES_FILE = 7620
FPS = 529.09
DT_MS = 1000.0 / FPS

# Frozen analysis-window parameters.
PRE_FRAMES = 60
POST_FRAMES = 300
BASELINE_FRAMES = 50
REFRACTORY_FRAMES = 250

# Denoising and mask parameters.  The mask threshold is intentionally
# conservative (wider than the high-SNR core) to retain the tissue boundary.
TEMPORAL_SIGMA = 3.0
SPATIAL_SIGMA = 1.0
MASK_RANGE_THRESHOLD = 60.0


def open_pixels() -> np.ndarray:
    expected = HEADER_BYTES + N_FRAMES_FILE * FRAME_WORDS * 2
    if DATA.stat().st_size != expected:
        raise ValueError(f"Unexpected input length: {DATA.stat().st_size} != {expected}")
    stream = np.memmap(
        DATA,
        dtype="<u2",
        mode="r",
        offset=HEADER_BYTES,
        shape=(N_FRAMES_FILE, FRAME_WORDS),
    )
    # Drop the under-exposed first frame and the four-word camera footer.
    return stream[1:, : HEIGHT * WIDTH]


def make_mask(raw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # Robust cyclic signal excursion, evaluated on every tenth frame.  Convert
    # storage order to analysis order with the required spatial transpose.
    sampled = raw[::10].astype(np.float32)
    q05, q95 = np.percentile(sampled, (5, 95), axis=0)
    signal_range = (q95 - q05).reshape(HEIGHT, WIDTH).T
    signal_range = gaussian_filter(signal_range, sigma=SPATIAL_SIGMA)
    candidate = signal_range > MASK_RANGE_THRESHOLD

    # Keep the single coherent preparation and fill any enclosed pinholes.
    components, count = label(candidate)
    if count == 0:
        raise RuntimeError("Tissue segmentation is empty")
    sizes = np.bincount(components.ravel())
    sizes[0] = 0
    mask = components == int(np.argmax(sizes))
    return binary_fill_holes(mask).astype(bool), signal_range


def detect_onsets(raw: np.ndarray, mask: np.ndarray) -> list[int]:
    # The recording's fluorescence falls on depolarisation, so negate it.  The
    # transpose relation means an analysis-order mask is transposed before it
    # indexes a storage-order flattened frame.
    field_trace = -raw[:, mask.T.ravel()].mean(axis=1, dtype=np.float64)
    q05, q95 = np.percentile(field_trace, (5, 95))
    normalised = (field_trace - q05) / (q95 - q05)
    candidates = np.flatnonzero(
        (normalised[:-1] < 0.5) & (normalised[1:] >= 0.5)
    ) + 1

    refractory_filtered: list[int] = []
    for crossing in candidates:
        crossing = int(crossing)
        if not refractory_filtered or crossing - refractory_filtered[-1] >= REFRACTORY_FRAMES:
            refractory_filtered.append(crossing)

    return [
        onset
        for onset in refractory_filtered
        if onset >= PRE_FRAMES and onset + POST_FRAMES <= raw.shape[0]
    ]


def crossing_maps(signal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Apply the frozen definitions to one denoised, oriented beat window."""
    time_points = signal.shape[0]
    frame_index = np.arange(time_points, dtype=np.int16)[:, None, None]
    baseline = np.median(signal[:BASELINE_FRAMES], axis=0)
    peak_index = np.argmax(signal, axis=0)
    amplitude = np.max(signal, axis=0) - baseline

    # First upward 50% crossing, with linear sub-frame interpolation.
    level50 = baseline + 0.5 * amplitude
    crosses50 = (signal[:-1] <= level50) & (signal[1:] > level50)
    has_activation = crosses50.any(axis=0) & (amplitude > 0)
    lower = np.argmax(crosses50, axis=0)
    y0 = np.take_along_axis(signal, lower[None], axis=0)[0]
    y1 = np.take_along_axis(signal, (lower + 1)[None], axis=0)[0]
    activation = lower + (level50 - y0) / (y1 - y0 + np.float32(1e-12))
    activation[~has_activation] = np.nan

    # APD80 uses the specified bracketing samples: the last at/below 20%
    # before the peak and the first at/below 20% after it.
    level20 = baseline + 0.2 * amplitude
    before = (signal <= level20) & (frame_index < peak_index[None])
    after = (signal <= level20) & (frame_index > peak_index[None])
    start20 = np.max(np.where(before, frame_index, -1), axis=0)
    end20 = np.min(np.where(after, frame_index, time_points), axis=0)
    has_apd = (start20 >= 0) & (end20 < time_points)
    apd_frames = (end20 - start20).astype(np.float32)
    apd_frames[~has_apd] = np.nan
    return activation.astype(np.float32), apd_frames


def process_beats(raw: np.ndarray, onsets: list[int]) -> tuple[np.ndarray, np.ndarray]:
    activation_beats = []
    apd_beats = []
    temporal_pad = int(np.ceil(4 * TEMPORAL_SIGMA))

    for onset in onsets:
        first = onset - PRE_FRAMES
        stop = onset + POST_FRAMES
        padded = raw[first - temporal_pad : stop + temporal_pad]
        # The transpose changes stored (x,y) to the analysis (y,x) convention.
        oriented = -padded.reshape(-1, HEIGHT, WIDTH).transpose(0, 2, 1).astype(np.float32)
        denoised = gaussian_filter(
            oriented,
            sigma=(TEMPORAL_SIGMA, SPATIAL_SIGMA, SPATIAL_SIGMA),
            mode="reflect",
        )[temporal_pad:-temporal_pad]
        activation, apd = crossing_maps(denoised)
        activation_beats.append((activation - PRE_FRAMES) * DT_MS)
        apd_beats.append(apd * DT_MS)

    return np.stack(activation_beats), np.stack(apd_beats)


def split_half_rmse(beats: np.ndarray, region: np.ndarray, remove_offset: bool) -> float:
    # Restrict first so all-NaN off-mask pixels do not emit irrelevant warnings.
    selected = beats[:, region]
    difference = np.nanmean(selected[::2], axis=0) - np.nanmean(selected[1::2], axis=0)
    values = difference[np.isfinite(difference)]
    if remove_offset:
        values = values - np.median(values)
    # Dividing the half-map difference by two estimates the 18-beat-map noise.
    return float(np.sqrt(np.mean(values * values)) / 2)


def main() -> None:
    raw = open_pixels()
    mask, signal_range = make_mask(raw)
    onsets = detect_onsets(raw, mask)
    if len(onsets) != 18:
        raise RuntimeError(f"Expected 18 complete beats, found {len(onsets)}: {onsets}")

    activation_beats, apd_beats = process_beats(raw, onsets)
    with np.errstate(invalid="ignore"):
        activation_map = np.nanmean(activation_beats, axis=0).astype(np.float32)
        apd_map = np.nanmean(apd_beats, axis=0).astype(np.float32)

    activation_map[~mask] = np.nan
    apd_map[~mask] = np.nan
    np.save(OUT / "mask.npy", mask)
    np.save(OUT / "activation_ms.npy", activation_map)
    np.save(OUT / "apd80_ms.npy", apd_map)

    core = mask & (signal_range >= 100.0)
    print(f"mask pixels: {mask.sum()} ({mask.mean():.3%} of frame)")
    print(f"complete beat onsets: {onsets}")
    print(f"activation finite in mask: {np.isfinite(activation_map[mask]).mean():.3%}")
    print(f"APD80 finite in mask: {np.isfinite(apd_map[mask]).mean():.3%}")
    print(
        "high-signal-core split-half/2 RMSE: "
        f"activation={split_half_rmse(activation_beats, core, True):.3f} ms, "
        f"APD80={split_half_rmse(apd_beats, core, False):.3f} ms"
    )
    print(f"median APD80 in mask: {np.nanmedian(apd_map[mask]):.3f} ms")


if __name__ == "__main__":
    main()
