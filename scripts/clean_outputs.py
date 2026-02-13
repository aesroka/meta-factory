#!/usr/bin/env python3
"""Clean old run outputs under outputs/ so they are not committed and disk stays small.

Usage:
  python scripts/clean_outputs.py              # delete all run dirs except outputs/sample/
  python scripts/clean_outputs.py --keep 5      # keep the 5 most recent runs, delete the rest
  python scripts/clean_outputs.py --older-than-days 7   # delete runs older than 7 days
"""

import argparse
from pathlib import Path
import time


OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"
# Directories we never delete
KEEP_NAMES = {"sample"}


def run_dirs():
    """Yield (path, mtime) for each run-like directory (run_*, test_*, showcase_*)."""
    if not OUTPUTS_DIR.exists():
        return
    for p in OUTPUTS_DIR.iterdir():
        if not p.is_dir() or p.name in KEEP_NAMES:
            continue
        if p.name.startswith(("run_", "test_", "showcase_")):
            try:
                mtime = p.stat().st_mtime
            except OSError:
                continue
            yield p, mtime


def main():
    ap = argparse.ArgumentParser(description="Clean old run outputs under outputs/")
    ap.add_argument("--keep", type=int, default=None, help="Keep this many most recent runs, delete the rest")
    ap.add_argument("--older-than-days", type=float, default=None, help="Delete runs older than this many days")
    ap.add_argument("--dry-run", action="store_true", help="Only print what would be deleted")
    args = ap.parse_args()

    dirs = list(run_dirs())
    if not dirs:
        print("No run directories to clean.")
        return

    # Sort by mtime descending (newest first)
    dirs.sort(key=lambda x: x[1], reverse=True)

    to_delete = []
    if args.keep is not None:
        to_delete = [p for p, _ in dirs[args.keep:]]
    elif args.older_than_days is not None:
        cutoff = time.time() - (args.older_than_days * 24 * 3600)
        to_delete = [p for p, m in dirs if m < cutoff]
    else:
        to_delete = [p for p, _ in dirs]

    if not to_delete:
        print("Nothing to delete.")
        return

    if args.dry_run:
        print("Would delete:")
        for p in to_delete:
            print(f"  {p}")
        return

    for p in to_delete:
        try:
            for f in p.rglob("*"):
                if f.is_file():
                    f.unlink()
            for d in sorted(p.rglob("*"), key=lambda x: len(x.parts), reverse=True):
                if d.is_dir():
                    d.rmdir()
            p.rmdir()
            print(f"Deleted {p}")
        except OSError as e:
            print(f"Error deleting {p}: {e}")


if __name__ == "__main__":
    main()
