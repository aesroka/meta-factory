# Meta-Factory Usage

## Historical data / Reference forecasting

Reference forecasting uses past project outcomes to correct estimates. The historical database lives at **`data/historical_projects.json`**.

- **Add outcomes after a real run:** Use `scripts/record_outcome.py` and provide the run ID; you will be prompted for actual hours/weeks per phase.
- **Seed synthetic data:** Run `python scripts/seed_historical_data.py` to add 2–3 example projects (for testing or when you have no real outcomes yet).
- **Enable reference forecasting:** Pass `--use-reference-forecast` when running the pipeline. The estimator will use median accuracy ratios from similar past projects (same mode, domain, project type) to adjust estimates.

## Hybrid context

Hybrid context (RAG + full context) is implemented for ingestion and can improve quality when you have both a RAG dataset and raw documents. It is available with **`--quality premium`** (or the relevant ingestion flag). This feature is deprioritised for further tuning until proven needed; standard quality uses RAG or transcript-only flows.

## Reference forecasting (detail)

Reference forecasting uses `data/historical_projects.json`. Seed data (e.g. from `scripts/seed_historical_data.py`) should be in place for meaningful corrections. Enable with **`--use-reference-forecast`**.
