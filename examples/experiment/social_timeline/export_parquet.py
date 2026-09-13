"""Export a run's SQLite database to partitioned Parquet (D-15).

Why this exists
---------------
The current pipeline has two storage problems and they are not the same
problem (F-52).

The database is merely large. Projected to 1,000 agents x 1,000 rounds it is
about 43.5M rows and ~14.7 GB, and SQLite copes with that.

What does not cope is `_analysis.json`: a single fully-materialised JSON
document that every analysis tool reads, 1.6 MB at 36x15 and multiple GB at
target scale. The hinge that keeps the pipeline consistent is exactly what
stops it scaling.

Parquet fixes both at once. Measured on `baseline`, `rec_history` and
`rec_candidates` come to 14.7 bytes/row against SQLite's 338 -- 0.62 GB
against 14.20 GB at target, a 23x reduction -- and the result opens directly
in pandas, R (`arrow`), DuckDB, Polars, Spark and Tableau with no converter
and no bespoke reader.

Layout
------
    <out>/
      manifest.json                     the run's own manifest, copied verbatim
      schema.json                       column types, units, and the traps below
      exposures/round=NN/part.parquet   one row per post shown to an agent
      candidates/round=NN/part.parquet  one row per scored candidate
      posts/part.parquet                every post written
      actions/part.parquet              the trace table, one row per action
      agents/part.parquet               the 36 personas as the run saw them
      follows/part.parquet              edges, with the round they formed
      rounds/part.parquet               per-round boundaries and phase timings

Partitioning by round is what makes the common query cheap: round-windowed
analysis touches only its partitions, and a run can be examined while it is
still running. Tables that are not round-shaped are written whole.

Traps this export closes
------------------------
Two of the schema traps in the build log are fixed here rather than passed on:

  * upstream's `user_id` column actually holds an `agent_id`
    (`platform.py:407`). Every exported table uses `agent_id`, and
    `schema.json` says so.
  * `created_at` on a post is the round number, not a timestamp. It is
    exported as `round` (int) so nothing downstream parses it as a date.

Usage
-----
    python export_parquet.py --db data/social_timeline_baseline.db
    python export_parquet.py --all --data-dir data --out data/parquet

Then, in whatever you like:

    pandas   pd.read_parquet("exposures/")
    duckdb   SELECT * FROM 'exposures/*/*.parquet'
    R        arrow::open_dataset("exposures/")
    polars   pl.scan_parquet("exposures/**/*.parquet")
"""
from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import sqlite3
import sys
import time

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

log = logging.getLogger("social_timeline.export")

COMPRESSION = "zstd"

# Right-sized dtypes. This is where the 23x comes from: SQLite stores every
# integer in a variable-length field with per-row overhead, while Parquet
# stores a typed column it can then compress. `source` and `action` are
# categorical -- a handful of distinct strings across millions of rows.
DTYPES = {
    "exposures": {"round": "int32", "agent_id": "int32", "post_id": "int64",
                  "author_id": "int32", "feed_position": "int16",
                  "source": "category", "score": "float32"},
    "candidates": {"round": "int32", "agent_id": "int32", "post_id": "int64",
                   "author_id": "int32", "rank": "int16", "sim": "float32",
                   "recency": "float32", "score": "float32"},
    "posts": {"post_id": "int64", "agent_id": "int32", "round": "int32",
              "original_post_id": "Int64", "num_likes": "int32",
              "num_dislikes": "int32", "num_shares": "int32"},
    "actions": {"agent_id": "int32", "round": "int32", "action": "category"},
    "agents": {"agent_id": "int32", "num_followings": "int32",
               "num_followers": "int32"},
    "follows": {"follow_id": "int64", "follower_id": "int32",
                "followee_id": "int32", "round": "int32"},
    "rounds": {"round": "int32", "n_posts": "int32", "n_follows": "int32"},
}

# SELECTs are explicit rather than `SELECT *` so a schema change upstream
# fails loudly here instead of silently changing what analysis sees.
QUERIES = {
    "exposures": """
        SELECT round, agent_id, post_id, author_id, feed_position, source,
               score
          FROM rec_history""",
    "candidates": """
        SELECT round, agent_id, post_id, author_id, rank, sim, recency, score
          FROM rec_candidates""",
    "posts": """
        SELECT post_id, user_id AS agent_id, original_post_id, content,
               quote_content, created_at AS round, num_likes, num_dislikes,
               num_shares
          FROM post""",
    "actions": """
        SELECT user_id AS agent_id, created_at AS round, action, info
          FROM trace""",
    "agents": """
        SELECT agent_id, user_id, user_name, name, bio, num_followings,
               num_followers
          FROM user""",
    "follows": """
        SELECT follow_id, follower_id, followee_id, created_at AS round
          FROM follow""",
    "rounds": """
        SELECT round, n_posts, n_follows FROM round_boundary""",
}

PARTITIONED = {"exposures", "candidates"}


def _coerce(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Apply the declared dtypes, tolerating columns that are absent or null.

    Nullable integer columns use pandas' `Int64` rather than numpy `int64`
    because `original_post_id` is legitimately NULL for anything that is not a
    repost, and a silent 0 there would invent reposts that never happened.
    """
    for col, dt in DTYPES.get(name, {}).items():
        if col not in df.columns:
            continue
        try:
            if dt == "category":
                df[col] = df[col].astype("category")
                continue

            num = pd.to_numeric(df[col], errors="coerce")
            n_null = int(num.isna().sum())

            if dt.startswith("float"):
                # NEVER fill a measure. `score` is legitimately NULL for the
                # 1,217 network and fof exposures the ranker never scored, and
                # filling those with 0.0 tells every downstream reader they
                # were the *least* relevant posts in the feed. That is the
                # F-38 failure exactly: a column quietly meaning something
                # other than its name. float32 carries NaN; let it.
                df[col] = num.astype(dt)
            elif dt.startswith("Int"):
                df[col] = num.astype(dt)          # nullable by construction
            elif n_null:
                # A null in a column declared non-nullable is a fact about the
                # data, not something to paper over. Widen to the nullable
                # type and say so, rather than inventing a zero.
                widened = "Int64"
                log.warning("  %s.%s: %d null(s) in a column declared %s "
                            "-> exporting as %s, not filling",
                            name, col, n_null, dt, widened)
                df[col] = num.astype(widened)
            else:
                df[col] = num.astype(dt)
        except (TypeError, ValueError) as exc:
            log.warning("  %s.%s: leaving as %s (%s)", name, col,
                        df[col].dtype, exc)
    return df


def _write(df: pd.DataFrame, path: str) -> int:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), path,
                   compression=COMPRESSION)
    return os.path.getsize(path)


def _write_csv(df: pd.DataFrame, path: str) -> int:
    """Write the same table as CSV, for Excel and anything else that cannot
    read Parquet.

    Not the default, and worth saying why. CSV has no types, so the
    `user_id`-is-really-`agent_id` and `created_at`-is-really-`round` traps
    come back as untyped strings for the reader to misinterpret, and NULL
    becomes indistinguishable from empty -- which is exactly the confusion
    that turned 1,217 unscored exposures into zeros the first time. It is also
    ~20x larger. Offered because Excel is a real constraint, not because it is
    a good interchange format.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    return os.path.getsize(path)


def export_run(db_path: str, out_root: str, also_csv: bool = False) -> dict:
    """Export one run. Returns a summary dict."""
    label = os.path.basename(db_path)
    label = label.replace("social_timeline_", "").replace(".db", "")
    out = os.path.join(out_root, label)
    os.makedirs(out, exist_ok=True)

    conn = sqlite3.connect(db_path)
    summary = {"label": label, "tables": {}}
    t0 = time.time()

    for name, sql in QUERIES.items():
        try:
            df = pd.read_sql(sql, conn)
        except Exception as exc:  # noqa: BLE001
            # A missing table is a fact about the run, not a crash: the
            # pre-three-tier runs predate some of these.
            log.warning("  %-11s skipped (%s)", name, exc)
            summary["tables"][name] = {"rows": 0, "skipped": str(exc)}
            continue

        df = _coerce(df, name)
        rows = len(df)

        if also_csv and rows:
            # One flat file per table -- partitioning helps a query engine and
            # only annoys a spreadsheet.
            _write_csv(df, os.path.join(out, "csv", f"{name}.csv"))

        if rows and name in PARTITIONED and "round" in df.columns:
            total = 0
            for rnd, part in df.groupby("round", observed=True):
                total += _write(part.drop(columns=["round"]),
                                os.path.join(out, name, f"round={int(rnd)}",
                                             "part.parquet"))
            nparts = int(df["round"].nunique())
        else:
            total = _write(df, os.path.join(out, name, "part.parquet")) \
                if rows else 0
            nparts = 1 if rows else 0

        summary["tables"][name] = {
            "rows": rows, "bytes": total, "partitions": nparts,
            "bytes_per_row": round(total / rows, 1) if rows else 0}
        log.info("  %-11s %8d rows  %9.1f KB  %s",
                 name, rows, total / 1e3,
                 f"{nparts} partitions" if nparts > 1 else "")

    conn.close()

    # The run manifest travels with the data. Without it the export is a pile
    # of numbers with no record of the configuration that produced them --
    # which is the provenance failure the build log's F-46 is about.
    man = db_path.replace(".db", ".json")
    if os.path.exists(man):
        with open(man) as fh:
            manifest = json.load(fh)
        with open(os.path.join(out, "manifest.json"), "w") as fh:
            json.dump(manifest, fh, indent=2)
        summary["manifest"] = True

    _write_schema(out, summary)

    summary["seconds"] = round(time.time() - t0, 2)
    summary["total_bytes"] = sum(
        t.get("bytes", 0) for t in summary["tables"].values())
    summary["sqlite_bytes"] = os.path.getsize(db_path)
    return summary


def _write_schema(out: str, summary: dict) -> None:
    """Write the data dictionary next to the data.

    Self-describing output is half the point of D-15: the reader should not
    have to know that `user_id` means `agent_id`, or that `created_at` on a
    post is a round number. Anything that had to be explained in a build log
    belongs here instead.
    """
    schema = {
        "produced_by": "export_parquet.py",
        "compression": COMPRESSION,
        "read_with": {
            "pandas": "pd.read_parquet('exposures/')",
            "duckdb": "SELECT * FROM 'exposures/*/*.parquet'",
            "R": "arrow::open_dataset('exposures/')",
            "polars": "pl.scan_parquet('exposures/**/*.parquet')",
        },
        "conventions": {
            "agent_id": "Stable across runs: persona #7 is agent 7 in every "
                        "run, because select_diverse() is deterministic. This "
                        "is what makes paired run-to-run comparison valid.",
            "round": "Integer round index. Upstream stores this in a column "
                     "called `created_at` typed DATETIME; it is NOT a "
                     "timestamp and is exported as `round` so nothing "
                     "downstream parses it as a date.",
            "user_id_trap": "Upstream's `user_id` columns actually hold "
                            "agent ids (platform.py:407). Every table here "
                            "uses `agent_id`.",
            "source": "Feed tier. Three-tier runs: network / fof / "
                      "discovery. Pre-three-tier runs: following / recsys / "
                      "both. The two vocabularies are NOT interchangeable -- "
                      "see manifest.algorithm.feed_model to tell which "
                      "builder produced this run.",
            "sim_vs_score": "`sim` is cosine similarity; `score` is "
                            "sim * recency. They are stored separately on "
                            "purpose. Collapsing them is what produced the "
                            "retracted F-38.",
        },
        "tables": {
            "exposures": "One row per post shown to an agent. The unit of "
                         "analysis: every row is a decision the agent made, "
                         "to act or not act.",
            "candidates": "One row per scored candidate, including those "
                          "never shown. Lets you ask what an agent could "
                          "have seen.",
            "posts": "Every post written. `round` is when it was written.",
            "actions": "Every action attempted, including ones later "
                       "rejected. `info` is a JSON string whose shape varies "
                       "by action.",
            "agents": "The personas as the run saw them.",
            "follows": "Directed edges, with the round they formed.",
            "rounds": "Per-round boundaries.",
        },
        "row_counts": {k: v.get("rows", 0)
                       for k, v in summary["tables"].items()},
    }
    with open(os.path.join(out, "schema.json"), "w") as fh:
        json.dump(schema, fh, indent=2)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", help="one database to export")
    ap.add_argument("--all", action="store_true",
                    help="export every social_timeline_*.db in --data-dir")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", default=None,
                    help="output root (default: <data-dir>/parquet)")
    ap.add_argument("--csv", action="store_true",
                    help="also write flat CSVs alongside the Parquet, for "
                         "Excel. Larger and untyped -- Parquet is the format "
                         "to prefer wherever the reader supports it.")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    out_root = args.out or os.path.join(args.data_dir, "parquet")

    if args.all:
        # Runs live either directly in data/ or grouped under data/runs/<arm>/
        # (and data/_archive/... ). Search recursively so the layout can change
        # without the export silently finding nothing.
        dbs = sorted(set(
            glob.glob(os.path.join(args.data_dir, "social_timeline_*.db"))
            + glob.glob(os.path.join(args.data_dir, "runs", "**",
                                     "social_timeline_*.db"), recursive=True)))
    elif args.db:
        dbs = [args.db]
    else:
        ap.error("pass --db or --all")

    if not dbs:
        log.error("no databases found")
        return 1

    results = []
    for db in dbs:
        log.info("%s", os.path.basename(db))
        results.append(export_run(db, out_root, also_csv=args.csv))

    log.info("=" * 70)
    tp = sum(r["total_bytes"] for r in results)
    ts = sum(r["sqlite_bytes"] for r in results)
    nrows = sum(t.get("rows", 0) for r in results
                for t in r["tables"].values())
    log.info("%d run(s), %s rows", len(results), f"{nrows:,}")
    log.info("sqlite  %8.1f MB", ts / 1e6)
    log.info("parquet %8.1f MB   (%.1fx smaller, %.1f bytes/row)",
             tp / 1e6, ts / tp if tp else 0, tp / nrows if nrows else 0)
    log.info("written to %s", out_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
