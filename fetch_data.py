#!/usr/bin/env python3
"""Fetch the large source recordings that live in Google Drive, not in git.

Two files exceed GitHub's 100 MB limit and are hosted separately:

  ...-PM1394Cam00.dat   239 MB   the raw camera stream -- tier2's INPUT data.
                                 Needed by any solver and by the solver package.
  ...-PM1394Cam00.mat   469 MB   the expert-processed recording. Only
                                 tier_2_task_1/gt/make_gt.py reads it, and the
                                 maps it produces are already committed (396 KB),
                                 so you need this only to regenerate them.

    python fetch_data.py              # both
    python fetch_data.py --only dat   # just the solver input
    python fetch_data.py --check      # verify what is already present

Requires `gdown` (pip install gdown) for Drive downloads. Both files are shared
read-only as "anyone with the link"; downloads are verified against a recorded
sha256, which catches the truncated HTML warning page Drive sometimes returns for
large files instead of the file itself.
"""
import argparse, hashlib, subprocess, sys
from pathlib import Path

DEST = Path(__file__).parent / "tier_2_task_1"

# Google Drive file IDs. From a share link of the form
#   https://drive.google.com/file/d/<FILE_ID>/view?usp=sharing
# take the <FILE_ID> part. The file must be shared as "anyone with the link".
FILES = {
    "dat": dict(
        name="2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.dat",
        drive_id="1NGgMaJ-C5o0Ek9saW9qOFjvronNUmLRi",
        size_mb=239,
        sha256="a4354f28cc3e92754710ad9093f2dc1885722adea5227722f9ff8c1df001632c",
        note="tier2 solver input (raw camera stream)",
    ),
    "mat": dict(
        name="2024-05-02_Exp000_Rec010_Cam0-PM1394Cam00.mat",
        drive_id="1xiCGSg3X2Oz9lk4X0J63Ik51kdKiZ039",
        size_mb=469,
        sha256="5f1c1d2988d7f3eda78ad58832647f429374c8bc2e773fc7d3768fe5cb41f7ad",
        note="expert-processed; only needed to regenerate gt/",
    ),
}


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def check(keys):
    ok = True
    for k in keys:
        spec = FILES[k]
        p = DEST / spec["name"]
        if not p.exists():
            print(f"  MISSING  {spec['name']}  ({spec['size_mb']} MB) -- {spec['note']}")
            ok = False
            continue
        mb = p.stat().st_size / 1e6
        if spec["sha256"]:
            got = sha256(p)
            state = "OK" if got == spec["sha256"] else "CHECKSUM MISMATCH"
            if got != spec["sha256"]:
                ok = False
        else:
            state = "present (no checksum recorded)"
        print(f"  {state:34s} {spec['name']}  {mb:.1f} MB")
    return ok


def download(keys):
    try:
        import gdown
    except ImportError:
        sys.exit("gdown is required: pip install gdown")
    # gdown >= 5 dropped the --id flag and takes the bare id as a positional
    # argument; older versions require --id. Pick the form this install accepts.
    major = int(getattr(gdown, "__version__", "0").split(".")[0] or 0)
    for k in keys:
        spec = FILES[k]
        out = DEST / spec["name"]
        if out.exists():
            print(f"  already present, skipping: {spec['name']}")
            continue
        if not spec["drive_id"]:
            sys.exit(f"no drive_id set for '{k}' -- paste the Google Drive file id "
                     f"into FILES['{k}']['drive_id'] in {Path(__file__).name}")
        print(f"  downloading {spec['name']} ({spec['size_mb']} MB)...")
        cmd = [sys.executable, "-m", "gdown"]
        cmd += ([spec["drive_id"]] if major >= 5 else ["--id", spec["drive_id"]])
        cmd += ["-O", str(out)]
        subprocess.check_call(cmd)
        if spec["sha256"]:
            got = sha256(out)
            if got != spec["sha256"]:
                sys.exit(f"checksum mismatch for {spec['name']}:\n"
                         f"  expected {spec['sha256']}\n  got      {got}")
            print("  checksum OK")


def record(keys):
    """Print sha256 lines to paste back into FILES, so later fetches verify."""
    for k in keys:
        p = DEST / FILES[k]["name"]
        if p.exists():
            print(f'  FILES["{k}"]["sha256"] = "{sha256(p)}"')
        else:
            print(f"  {FILES[k]['name']} not present; download it first")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(FILES), help="fetch just one file")
    ap.add_argument("--check", action="store_true", help="report what is present")
    ap.add_argument("--record", action="store_true",
                    help="print sha256 of the local files, to paste into FILES")
    a = ap.parse_args()
    keys = [a.only] if a.only else list(FILES)

    if a.check:
        sys.exit(0 if check(keys) else 1)
    if a.record:
        record(keys)
        return
    download(keys)
    print()
    check(keys)


if __name__ == "__main__":
    main()
