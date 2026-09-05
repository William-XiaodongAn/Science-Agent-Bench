#!/usr/bin/env python3
"""Reproduce r_pred.npy from the fitted, stability-regularized SSN model."""

from pathlib import Path
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = Path(__file__).resolve().parent


def kernel_matrix(xy: np.ndarray, q: np.ndarray) -> np.ndarray:
    """Four Gaussian E/I kernels; columns obey Dale's law."""
    n_cells = len(xy)
    inhibitory = np.arange(n_cells) >= 29
    dist2 = ((xy[:, None, :] - xy[None, :, :]) ** 2).sum(axis=2)
    w = np.zeros((n_cells, n_cells), dtype=np.float64)
    for post_type in range(2):
        for pre_type in range(2):
            z = 2 * post_type + pre_type
            mask = ((inhibitory[:, None] == post_type)
                    & (inhibitory[None, :] == pre_type))
            sign = -1.0 if pre_type else 1.0
            w[mask] = sign * q[z] * np.exp(
                -dist2[mask] / (2.0 * q[4 + z] ** 2)
            )
    np.fill_diagonal(w, 0.0)
    return w


def corrected_matrix(base: np.ndarray, gains: np.ndarray,
                     observed_column_weight: np.ndarray) -> np.ndarray:
    """Apply shrunken row corrections only to observed presynaptic columns."""
    inhibitory = np.arange(base.shape[0]) >= 29
    excitatory_part = base.copy()
    excitatory_part[:, inhibitory] = 0.0
    inhibitory_part = base.copy()
    inhibitory_part[:, ~inhibitory] = 0.0
    n_cells = base.shape[0]
    ge = gains[:n_cells, None]
    gi = gains[n_cells:, None]
    p = observed_column_weight[None, :]
    return (excitatory_part * (1.0 + (ge - 1.0) * p)
            + inhibitory_part * (1.0 + (gi - 1.0) * p))


def integrate(w: np.ndarray, drive: np.ndarray) -> np.ndarray:
    tau, dt, k = 0.5, 0.01, 0.5
    rates = np.zeros(w.shape[0], dtype=np.float64)
    result = np.zeros_like(drive, dtype=np.float64)
    step = dt / tau
    for j in range(drive.shape[1] - 1):
        total_input = w @ rates + drive[:, j]
        target = k * np.maximum(total_input, 0.0) ** 2
        rates += step * (target - rates)
        np.maximum(rates, 0.0, out=rates)
        result[:, j + 1] = rates
    return result


def main() -> None:
    xy = np.load(DATA / "xy.npy").astype(np.float64)
    eval_drive = np.load(DATA / "eval_I.npy").astype(np.float64)
    params = np.load(OUT / "model_params.npz")
    base = kernel_matrix(xy, params["q"])
    w = corrected_matrix(base, params["gains"], params["column_weight"])
    prediction = integrate(w, eval_drive)
    if prediction.shape != (49, 12001):
        raise RuntimeError(f"unexpected output shape: {prediction.shape}")
    if not np.isfinite(prediction).all() or np.any(prediction < 0.0):
        raise RuntimeError("simulation produced invalid rates")
    np.save(OUT / "r_pred.npy", prediction)


if __name__ == "__main__":
    main()
