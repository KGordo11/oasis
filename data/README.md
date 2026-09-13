# data/

    runs/            the 24 runs behind every current claim
      control/       9 — the validated baseline (36 agents, 15 rounds, NP=4)
      fresh_context/ 3 — the memory-clearing experimental arm (F-88)
      scale99/       2 — 99-agent worlds (F-91)
      published/    10 — the original baseline behind the published findings
    sim4_package/    THE HANDOVER FOLDER. Start at runs_index.csv
    parquet/         every run compacted, partitioned by round
    reddit/          the 36 personas (input)
    twitter_dataset/ the 99 personas (input)
    _archive/        67 older runs, kept and documented. See _archive/README.md

## Where to start
Open `sim4_package/runs_index.csv`. Every other file in that folder joins to it
on `run`. Column meanings are in `sim4_package/DATA_DICTIONARY.md`.

Filter to `arm == "control"` and `complete == True` for the baseline runs.

## Rebuilding after a new run
    analyze.py --db data/runs/<arm>/social_timeline_<label>.db
    export_parquet.py --all --data-dir data --out data/parquet
    build_package.py

All three search `data/` and `data/runs/**`, so a run works from either location.
