#!/usr/bin/env python3
"""Build the solver-facing package: everything a solver needs, nothing that answers the task.

The working copy in this repo is the AUTHOR's copy -- it holds ground truth,
reference solutions and scoring anchors alongside the inputs. Handing that to a
solver leaks the answer. This script copies out only the released half.

    python make_solver_package.py --out ../solver_package

What is withheld, and why:
  tier1  gt/eval_r.npy      the hidden trajectory -- the answer itself
         gt/W_true.npy      the connectivity the task asks you to recover
         gt/make_gt.py      regenerates both of the above
         meta.json          filtered, not copied: see SOLVER_KEYS below
  tier2  gt/                every map in it is an answer; beats.json and
                            task_config.toml carry the scoring anchors
  tier3  gt/test_data.npy   the forecast target
         gt/meta.json       filtered: split sizes are released, anchors are not

meta.json is rewritten rather than dropped: solvers legitimately need the physical
constants, but the same file also carries the true spectral radius (the scale of
the answer), the eval trajectory's std and max (the metric's normaliser), the eval
stimulus parameters, and the scoring anchors.
"""
import argparse, json, shutil
from pathlib import Path

# Constants a solver is told in instruction.md, and nothing else.
SOLVER_KEYS = ["N", "NE", "NI", "L", "dt", "T", "n_timepoints", "stride",
               "tau", "k", "n"]

TIER1_INPUTS = ["t.npy", "xy.npy", "train_r_obs.npy", "train_I.npy", "eval_I.npy"]
TIER2_RAW = ["2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat"]
TIER3_INPUTS = ["train_data.npy", "train_stim.npy", "test_stim.npy", "time.npy"]
# Split geometry a solver needs; the anchors and the paper's numbers stay behind.
TIER3_KEYS = ["n_total", "n_train", "n_test", "train_frac", "pretrain_points",
              "dt_ms", "test_start_ms", "test_end_ms", "data_range",
              "stim_amplitude",
              # the tuning budget is a stated task constraint, not an answer
              "paper_tuning_budget"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("../solver_package"))
    ap.add_argument("--force", action="store_true", help="overwrite an existing --out")
    args = ap.parse_args()
    root = Path(__file__).parent

    if args.out.exists():
        if not args.force:
            raise SystemExit(f"{args.out} exists; pass --force to overwrite")
        shutil.rmtree(args.out)

    # ---- tier1 ----------------------------------------------------------
    d = args.out / "tier1_task_1"
    (d / "data").mkdir(parents=True)
    for f in TIER1_INPUTS:
        shutil.copy2(root / "tier1_task_1/gt" / f, d / "data" / f)
    full = json.loads((root / "tier1_task_1/gt/meta.json").read_text())
    missing = [k for k in SOLVER_KEYS if k not in full]
    if missing:
        raise SystemExit(f"meta.json is missing expected keys: {missing}")
    (d / "data" / "constants.json").write_text(
        json.dumps({k: full[k] for k in SOLVER_KEYS}, indent=1))
    shutil.copy2(root / "tier1_task_1/instruction.md", d / "instruction.md")

    # ---- tier2 ----------------------------------------------------------
    d = args.out / "tier_2_task_1"
    (d / "data").mkdir(parents=True)
    for f in TIER2_RAW:
        src = root / "tier_2_task_1" / f
        if not src.exists():
            raise SystemExit(
                f"missing {f} -- it is hosted in Google Drive, not git. "
                f"Run:  python fetch_data.py --only dat")
        shutil.copy2(src, d / "data" / f)
    shutil.copy2(root / "tier_2_task_1/instruction.md", d / "instruction.md")

    # ---- tier3 ----------------------------------------------------------
    d = args.out / "tier_3_task_1"
    (d / "data").mkdir(parents=True)
    for f in TIER3_INPUTS:
        shutil.copy2(root / "tier_3_task_1/gt" / f, d / "data" / f)
    full3 = json.loads((root / "tier_3_task_1/gt/meta.json").read_text())
    missing = [k for k in TIER3_KEYS if k not in full3]
    if missing:
        raise SystemExit(f"tier3 meta.json is missing expected keys: {missing}")
    (d / "data" / "split.json").write_text(
        json.dumps({k: full3[k] for k in TIER3_KEYS}, indent=1))
    shutil.copy2(root / "tier_3_task_1/instruction.md", d / "instruction.md")
    for pdf in (root / "tier_3_task_1").glob("*.pdf"):
        shutil.copy2(pdf, d / pdf.name)     # the source paper is public

    # ---- verify no answer slipped through --------------------------------
    banned = {"eval_r.npy", "W_true.npy", "make_gt.py", "meta.json",
              "activation_ms.npy", "apd80_ms.npy", "mask.npy", "cv_cm_s.npy",
              "beats.json", "dist_gt.npz", "task_config.toml",
              "test_data.npy", "dataset1.mat"}
    leaked = [p for p in args.out.rglob("*") if p.name in banned]
    if leaked:
        raise SystemExit("REFUSING: answer files present: " +
                         ", ".join(str(p) for p in leaked))
    # Probes are scoped per task: tier3's search space legitimately names
    # "spectral_radius" as an ESN hyperparameter range, which has nothing to do
    # with tier1's spectral_radius anchor. A global probe list would reject it.
    probes = {
        "tier1_task_1": ("anchors", "spectral_radius", "eval_r_std", "eval_r_max",
                         "eval_stim", "noise_floor", "oracle", "n_edges",
                         "active_fraction"),
        "tier_2_task_1": ("anchors", "noise_floor", "spatial_sd", "baseline"),
        "tier_3_task_1": ("anchors", "paper_zebrafish_rmse", "baseline_train_mean",
                          "0.0784"),
    }
    for f in args.out.rglob("*.json"):
        task = next((t for t in probes if t in f.parts), None)
        if task is None:
            continue
        txt = f.read_text()
        for probe in probes[task]:
            if probe in txt:
                raise SystemExit(f"REFUSING: {f} still contains '{probe}'")

    files = sorted(p for p in args.out.rglob("*") if p.is_file())
    total = sum(p.stat().st_size for p in files)
    print(f"solver package -> {args.out}   {len(files)} files, {total/1e6:.1f} MB")
    for p in files:
        print(f"  {p.relative_to(args.out)}  ({p.stat().st_size/1e6:.2f} MB)")
    print("\nchecked: no ground truth, no reference solution, no scoring anchors")


if __name__ == "__main__":
    main()
