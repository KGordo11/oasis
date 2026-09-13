"""Build a single, tool-ready data package from every exported run.

WHY THIS EXISTS
---------------
`export_parquet.py` writes one directory per run, partitioned by round. That is
the right shape for the pipeline and the wrong shape for anybody else: opening
it in R, Stata, Tableau or Excel means stitching 55 directories together by
hand, and the per-round wall-clock timings -- the numbers the efficiency work
actually produced -- are not in there at all, because they only ever existed in
the run logs.

This produces the other shape. One directory, one file per table, every run
stacked with a `run` column, plus an index that says what each run WAS. A
person given this folder can answer "how long did a round take at 99 agents"
or "what did agents engage with" without reading any of our code.

WHAT IT WRITES

    runs_index.csv        one row per run: config, wall clock, engagement.
                          Start here. Every other file joins to it on `run`.
    round_timings.csv     per-round wall clock. The efficiency dataset.
    exposures.parquet     the core analytic table: every post shown to every
                          agent, with feed position, tier and score.
    actions.parquet       every action every agent took.
    posts.parquet         post text and engagement counts.
    agents.parquet        the 36 (or 99) personas.
    candidates.parquet    the full ranker input -- large, Parquet only.
    DATA_DICTIONARY.md    what every column means.
    README.md             load it in Python / R / Excel.

CSV is written alongside Parquet for everything except `candidates`, which is
tens of millions of rows and would be unusable as text.

USAGE
    python build_package.py                       # all exported runs
    python build_package.py --out data/sim4_package
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

import pandas as pd

# Runs at the validated configuration, which are the ones any statistical
# claim should be made on. Everything else is kept but flagged, because a
# package that silently drops runs is how a reader reaches a wrong conclusion.
VALIDATED = re.compile(r"^(np4_val_r\d+|bank_r\d+)$")

# Runs that are a deliberate EXPERIMENTAL ARM, not the control condition and not
# junk. Flagged separately so they are neither pooled with the control nor
# mistaken for diagnostics. F-88: fresh-context is 3.09x faster and yields 1.02x
# data per hour -- a wash, and a different behavioural regime.
ARMS = {"fc_full": "fresh_context", "lean_": "lean_actions",
        "scale99_full": "scale_99agents"}

CSV_TABLES = ("exposures", "actions", "posts", "agents", "rounds", "follows")


def read_table(run_dir: str, table: str) -> pd.DataFrame | None:
    files = sorted(glob.glob(os.path.join(run_dir, table, "**", "*.parquet"),
                             recursive=True))
    if not files:
        return None
    frames = []
    for f in files:
        d = pd.read_parquet(f)
        # round= partitions carry the round in the PATH, not the columns
        m = re.search(r"round=(\d+)", f)
        if m and "round" not in d.columns:
            d["round"] = int(m.group(1))
        frames.append(d)
    return pd.concat(frames, ignore_index=True) if frames else None


def round_timings(run_dir: str, label: str) -> pd.DataFrame | None:
    """Per-round wall clock, read from the run's own manifest.

    These numbers exist nowhere else. F-81 -- cost ramps for three rounds then
    plateaus -- and F-91's agent-scaling exponent are derived entirely from
    them, so they belong in the package rather than in a log file nobody else
    will read.

    B-27: this used to scrape `/tmp/*_<label>.log` for "round N done in Xs"
    lines. The first glob hit won, and it took every matching line in the file.
    That published the mislabelled 36-agent run's timings under the name
    `scale99_full` -- eleven rounds of 36-agent numbers for a five-round
    99-agent run -- because B-26's relabelling never reached /tmp. The manifest
    is written by the run itself, is per-run by construction, and cannot be
    contaminated by a neighbouring log. Read that instead.
    """
    mpath = os.path.join(run_dir, "manifest.json")
    if not os.path.exists(mpath):
        return None
    try:
        m = json.load(open(mpath))
    except (OSError, json.JSONDecodeError):
        return None
    rounds = m.get("rounds")
    if not isinstance(rounds, list) or not rounds:
        return None
    rows = [(r.get("round"), r.get("seconds")) for r in rounds
            if isinstance(r, dict) and r.get("seconds") is not None]
    if not rows:
        return None
    df = pd.DataFrame({"run": label,
                       "round": [int(r) for r, _ in rows],
                       "wall_seconds": [float(s) for _, s in rows]})
    # A run's timings must sum to its own total. Anything else means the
    # manifest is inconsistent and the caller should not silently publish it.
    total = m.get("total_seconds")
    if total and abs(df.wall_seconds.sum() - float(total)) > 0.05 * float(total):
        print(f"  WARNING {label}: round seconds sum to "
              f"{df.wall_seconds.sum():.0f}s against total_seconds {total:.0f}s")
    return df


def manifest_row(run_dir: str, label: str) -> dict:
    row = {"run": label}
    mpath = os.path.join(run_dir, "manifest.json")
    if not os.path.exists(mpath):
        return row
    try:
        m = json.load(open(mpath))
    except (OSError, json.JSONDecodeError):
        return row
    cfg = m.get("config", m) or {}
    for src, keys in ((cfg, ("agents", "rounds", "model", "semaphore",
                             "temperature", "personas", "lean_actions",
                             "terse_tools", "shared_prefix", "max_tool_rounds",
                             "smart_tool_loop", "max_tokens", "seed",
                             "ollama_num_parallel_client_env")),
                      (m, ("total_seconds", "started_at", "finished_at",
                           "tool_loop_short_circuits"))):
        for k in keys:
            if k in src:
                row[k] = src[k]
    tw = m.get("turns_without_action") or {}
    row["action_rate"] = tw.get("action_rate")
    row["agent_turns_total"] = tw.get("agent_turns_total")
    ps = m.get("phase_share") or {}
    for k, v in ps.items():
        row[f"phase_pct_{k}"] = v
    return row


def find_analysis(label: str, data_dir: str) -> str | None:
    """Locate a run's analysis JSON.

    Runs were grouped into `data/runs/<arm>/` on 2026-09-11 to keep the working
    directory readable. Both layouts are searched so nothing breaks whichever
    way a run is filed, and so archived runs can be analysed in place.
    """
    name = f"social_timeline_{label}_analysis.json"
    direct = os.path.join(data_dir, name)
    if os.path.exists(direct):
        return direct
    hits = glob.glob(os.path.join(data_dir, "**", name), recursive=True)
    return hits[0] if hits else None


def engagement(label: str, data_dir: str) -> float | None:
    """Share of shown posts an agent acted on -- analyze.py's definition."""
    p = find_analysis(label, data_dir)
    if p is None:
        return None
    try:
        agents = (json.load(open(p)).get("agents") or {})
    except (OSError, json.JSONDecodeError):
        return None
    hit = sum(len(a.get("seen_and_acted") or []) for a in agents.values())
    shown = hit + sum(len(a.get("seen_and_ignored") or [])
                      for a in agents.values())
    return round(100 * hit / shown, 3) if shown else None


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--parquet-dir", default="data/parquet")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", default="data/sim4_package")
    args = ap.parse_args()

    runs = sorted(d for d in os.listdir(args.parquet_dir)
                  if os.path.isdir(os.path.join(args.parquet_dir, d)))
    if not runs:
        print(f"  no exported runs under {args.parquet_dir}")
        return 1
    os.makedirs(args.out, exist_ok=True)

    index, timings = [], []
    tables: dict[str, list[pd.DataFrame]] = {}
    for label in runs:
        run_dir = os.path.join(args.parquet_dir, label)
        row = manifest_row(run_dir, label)
        row["engagement_pct"] = engagement(label, args.data_dir)
        row["validated_config"] = bool(VALIDATED.match(label))
        # A run still in flight exports partially. Flag it rather than leaving
        # a bare NaN for another tool to average over by accident.
        row["complete"] = row.get("total_seconds") is not None
        row["arm"] = next((v for k, v in ARMS.items() if label.startswith(k)),
                          "control" if VALIDATED.match(label) else "")
        index.append(row)

        t = round_timings(run_dir, label)
        if t is not None:
            timings.append(t)

        for table in ("exposures", "actions", "posts", "agents", "rounds",
                      "follows", "candidates"):
            d = read_table(run_dir, table)
            if d is None or d.empty:
                continue
            d.insert(0, "run", label)
            tables.setdefault(table, []).append(d)

    idx = pd.DataFrame(index)
    front = [c for c in ("run", "arm", "validated_config", "complete", "agents", "rounds",
                         "model", "total_seconds", "engagement_pct")
             if c in idx.columns]
    idx = idx[front + [c for c in idx.columns if c not in front]]
    idx.to_csv(os.path.join(args.out, "runs_index.csv"), index=False)
    print(f"  runs_index.csv          {len(idx):>7} runs")

    if timings:
        tt = pd.concat(timings, ignore_index=True)
        tt.to_csv(os.path.join(args.out, "round_timings.csv"), index=False)
        print(f"  round_timings.csv       {len(tt):>7} rows  "
              f"({tt['run'].nunique()} runs have timings)")

    for table, frames in sorted(tables.items()):
        d = pd.concat(frames, ignore_index=True)
        d.to_parquet(os.path.join(args.out, f"{table}.parquet"),
                     compression="zstd", index=False)
        note = ""
        if table in CSV_TABLES:
            d.to_csv(os.path.join(args.out, f"{table}.csv.gz"),
                     index=False, compression="gzip")
            note = "+ csv.gz"
        print(f"  {table+'.parquet':<24}{len(d):>7} rows  {note}")

    write_docs(args.out, idx, tables)
    total = sum(os.path.getsize(os.path.join(args.out, f))
                for f in os.listdir(args.out))
    print(f"\n  package: {args.out}  ({total/1e6:.1f} MB)")
    return 0


def write_docs(out: str, idx: pd.DataFrame, tables: dict) -> None:
    n_val = int(idx["validated_config"].sum()) if "validated_config" in idx else 0
    open(os.path.join(out, "DATA_DICTIONARY.md"), "w").write(f"""# Data dictionary

Every file carries a `run` column. Join anything to `runs_index.csv` on it.

## runs_index.csv — start here
One row per run ({len(idx)} runs, {n_val} at the validated configuration).

| column | meaning |
|---|---|
| `run` | run label; the join key for every other file |
| `complete` | FALSE if the run was still in flight when the package was built — exclude these |
| `arm` | `control` for the validated baseline, `fresh_context` / `lean_actions` for experimental arms, blank for diagnostics. **Compare arms against `control`; never pool them** |
| `validated_config` | TRUE for runs at the measured, validated setup. **Statistical claims should use these only** — the others are diagnostics, failed models and abandoned configs, kept for transparency rather than dropped |
| `agents`, `rounds` | world size and length |
| `model` | the language model that drove the agents |
| `total_seconds` | wall clock for the whole run |
| `engagement_pct` | share of posts shown to an agent that the agent acted on. **The study's dependent variable** |
| `action_rate` | share of agent-turns producing any action |
| `phase_pct_*` | share of run time in each pipeline phase |
| `lean_actions`, `terse_tools`, `shared_prefix`, `max_tool_rounds`, `smart_tool_loop` | configuration switches |

## round_timings.csv — the efficiency dataset
| column | meaning |
|---|---|
| `run`, `round` | which run, which round (0-indexed) |
| `wall_seconds` | wall clock for that round |

Cost per round ramps for the first three rounds as feeds fill, then plateaus.
Averaging across all rounds understates steady-state cost by about 2.4x, so
filter to `round >= 4` for a plateau figure.

## exposures.parquet / .csv.gz — the core analytic table
Every post shown to every agent.

| column | meaning |
|---|---|
| `agent_id` | who saw it |
| `post_id` | what they saw |
| `author_id` | who wrote it |
| `feed_position` | slot in the feed, 0 = top |
| `source` | which tier placed it: `network` (someone they follow), `fof` (friend-of-friend), `discovery` (recommended) |
| `score` | ranker score, NULL where the tier does not score |

## actions.parquet / .csv.gz
| column | meaning |
|---|---|
| `agent_id`, `round`, `action` | who did what, when |
| `info` | JSON payload; contains `post_id` for post-directed actions |

## posts.parquet, agents.parquet, rounds.parquet, follows.parquet
Post text and like/share counts; persona records; per-round post and follow
totals; the follow graph with the round each edge formed.

## candidates.parquet — Parquet only
Full ranker input: every candidate considered for every agent every round,
with similarity, recency and final score. Large by design; no CSV.
""")

    open(os.path.join(out, "README.md"), "w").write(f"""# Sim 4 data package

{len(idx)} runs of the OASIS social-timeline simulation. Self-contained: no
code from this repository is needed to read it.

Start with `runs_index.csv`, then join on `run`. Column meanings are in
`DATA_DICTIONARY.md`.

**Filter to `validated_config == True and complete == True` for statistical
work.** The other runs
are diagnostics, rejected models and abandoned configurations. They are
included so nothing is hidden, not because they are comparable.

## Python
```python
import pandas as pd
runs = pd.read_csv("runs_index.csv")
exp  = pd.read_parquet("exposures.parquet")

good = runs[runs.validated_config]
print(good.engagement_pct.describe())

# engagement by feed tier
acts = pd.read_parquet("actions.parquet")
```

## R
```r
library(arrow); library(dplyr)
runs <- read.csv("runs_index.csv")
exp  <- read_parquet("exposures.parquet")
exp %>% count(source)
```

## Excel / Tableau / SPSS
Open the `.csv.gz` files (Excel reads them once decompressed). `candidates` is
Parquet only — it is too large for a spreadsheet.

## A caution on averaging round timings
`round_timings.csv` includes the ramp. Filter to `round >= 4` for
steady-state cost; averaging everything understates it by roughly 2.4x.
""")


if __name__ == "__main__":
    sys.exit(main())
