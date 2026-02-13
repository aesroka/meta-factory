# Sample output

This folder is the **only** run output committed to the repo. It shows what a successful greenfield run produces.

- **`proposal.md`** — Human-readable proposal (executive summary, delivery phases, risks, etc.). This is what you open to review a run.

Real runs write to `outputs/<run_id>/` (e.g. `outputs/run_20260213_145954/`). Those directories are **gitignored** so they are not committed.

## Cleaning up old runs

To avoid filling disk with old runs:

- **Delete all run outputs:**  
  `rm -rf outputs/run_* outputs/test_* outputs/showcase_*`

- **Keep only the last N runs:**  
  `python scripts/clean_outputs.py --keep 5`

- **Delete runs older than N days:**  
  `python scripts/clean_outputs.py --older-than-days 7`

If you don’t run the cleaner, you can always delete `outputs/` contents manually; the next run will recreate the directory.
