#!/usr/bin/env python3
"""Ground-truth builder for tier_3_task_1 (zebrafish voltage forecasting).

Splits the zebrafish cardiac voltage recording into the train/test partition used
by Delshad & Cherry (2025), Chaos 35:093126, and records the anchors.

The paper's split (Sec. III A): 80% train / 20% test, with the first 1000 points
of the training set reserved for pre-training (washout). The resulting test
window is t = 16455..20567 ms, which is the 16.5-20.5 s range plotted in the
paper's Figs. 7 and 14 -- confirming the partition.

Emits:
  train_data.npy   (16454,)  voltage, training segment          [released]
  train_stim.npy   (16454,)  stimulus, training segment         [released]
  test_stim.npy    (4113,)   stimulus, test segment             [released]
  time.npy         (20567,)  full time base, ms                 [released]
  test_data.npy    (4113,)   voltage, test segment              [HIDDEN ANSWER]
  meta.json                  split indices, constants, anchors
"""
import argparse, json
import numpy as np
import scipy.io as sio
from pathlib import Path

TRAIN_FRAC = 0.80
PRETRAIN = 1000       # washout points at the head of the training set

# Zebrafish RMSE values reported by Delshad & Cherry (2025). Fig. 14(b), the
# DHESN-io+ (CN) structure with 368 neurons in 5 layers, is the lowest of them.
# It is a BASELINE TO BEAT, not a floor: it is one published method's result, and
# a better method should score below it.
PAPER = {
    "esn_plus_96":        0.1064,   # Fig. 7(a)
    "esn_plus_368":       0.1021,   # Fig. 7(b)
    "hesn_plus_cn_96":    0.0907,   # Fig. 7(c)
    "hesn_plus_cn_368":   0.0879,   # Fig. 7(d)
    "desn_io_plus_368":   0.0972,   # Fig. 14(a)
    "dhesn_io_plus_368":  0.0784,   # Fig. 14(b)  <- best reported
}


def rmse(pred, target):
    return float(np.sqrt(np.mean((np.asarray(pred) - np.asarray(target)) ** 2)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mat", type=Path,
                    default=Path(__file__).parent.parent / "dataset1.mat")
    ap.add_argument("--out", type=Path, default=Path(__file__).parent)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    m = sio.loadmat(args.mat)
    x = m["data"].ravel().astype(np.float64)
    s = m["stimulus"].ravel().astype(np.float64)
    t = m["time"].ravel().astype(np.float64)
    n = len(x)
    assert len(s) == len(t) == n, "data/stimulus/time length mismatch"

    n_train = int(round(TRAIN_FRAC * n))
    train_x, test_x = x[:n_train], x[n_train:]
    n_test = len(test_x)

    np.save(args.out / "train_data.npy", train_x)
    np.save(args.out / "train_stim.npy", s[:n_train])
    np.save(args.out / "test_stim.npy", s[n_train:])
    np.save(args.out / "test_data.npy", test_x)
    np.save(args.out / "time.npy", t)

    # Anchors. The do-nothing reference is the training-set mean carried forward;
    # predicting the test mean is not available to a solver (it needs the answer)
    # but is recorded because it equals the test standard deviation and so bounds
    # what any constant can achieve.
    anchors = {
        "baseline_train_mean": round(rmse(np.full(n_test, train_x.mean()), test_x), 4),
        "baseline_persistence": round(rmse(np.full(n_test, train_x[-1]), test_x), 4),
        "constant_best_possible": round(float(test_x.std()), 4),
        "paper_baseline_dhesn_io_plus_368": PAPER["dhesn_io_plus_368"],
    }

    # The paper's tuning budget (Sec. III B), quoted so a submission can be
    # compared on equal terms rather than by spending unlimited search.
    budget = dict(
        bayesopt_iterations_by_depth={"1_layer": 20, "2_layer": 30, "3_layer": 40,
                                      "4_layer": 50, "5_layer": 60},
        repeats=5,
        reported_statistic="mean over the 5 repeats",
        reservoir_sizes=[96, 144, 240, 368],
        search_space=dict(input_weight_scale=[0.05, 0.2],
                          connection_probability=[0.02, 0.15],
                          spectral_radius=[0.8, 1.2],
                          leaking_rate=[0.5, 1.0]),
    )

    meta = dict(
        n_total=n, n_train=n_train, n_test=n_test,
        train_frac=TRAIN_FRAC, pretrain_points=PRETRAIN,
        dt_ms=float(np.median(np.diff(t))),
        test_start_ms=float(t[n_train]), test_end_ms=float(t[-1]),
        data_range=[float(x.min()), float(x.max())],
        stim_amplitude=float(s.max()),
        stim_count_train=int((s[:n_train] != 0).sum()),
        stim_count_test=int((s[n_train:] != 0).sum()),
        paper_zebrafish_rmse=PAPER,
        paper_tuning_budget=budget,
        anchors=anchors,
    )
    (args.out / "meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
