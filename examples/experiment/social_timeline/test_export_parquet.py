"""Fidelity gate for export_parquet.py.

Exists because the first working version of the exporter silently corrupted
1,217 rows. `score` is legitimately NULL for network and fof exposures the
ranker never scored, and a blanket `.fillna(0)` turned every one of them into
0.0 -- which any downstream analysis reads as "least relevant post in the
feed" rather than "not scored". That is the F-38 failure class reproduced in
new code: a column quietly meaning something other than its name.

Nothing here checks that the export *runs*. It checks that what comes back
out is what went in, which is the only property that matters for a file we
hand to someone else.

    python test_export_parquet.py [--db data/social_timeline_baseline.db]
"""
from __future__ import annotations

import argparse
import json as _json
import os
import shutil
import sqlite3
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from export_parquet import export_run  # noqa: E402

PASS, FAIL = [], []


def _ci(value):
    """int for 3 or "3", else None -- trace payloads mix both."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def check(label: str, cond: bool) -> None:
    (PASS if cond else FAIL).append(label)
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/social_timeline_baseline.db")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"no such database: {args.db}")
        return 2

    out = tempfile.mkdtemp(prefix="pqgate_")
    try:
        export_run(args.db, out)
        label = os.path.basename(args.db)
        label = label.replace("social_timeline_", "").replace(".db", "")
        root = os.path.join(out, label)
        conn = sqlite3.connect(args.db)

        # ---------- exposures: the unit of analysis ----------
        ex = pd.read_parquet(os.path.join(root, "exposures"))
        src = pd.read_sql(
            "SELECT round, agent_id, post_id, author_id, feed_position, "
            "source, score FROM rec_history", conn)

        check("exposures: row count preserved", len(ex) == len(src))
        for col in ("round", "agent_id", "post_id", "author_id",
                    "feed_position"):
            check(f"exposures: {col} values identical",
                  sorted(ex[col].astype(int)) == sorted(src[col].astype(int)))
        check("exposures: source labels identical",
              sorted(ex["source"].astype(str)) ==
              sorted(src["source"].astype(str)))

        # The regression this file exists for.
        check("exposures: NULL scores stay NULL (not filled with 0)",
              int(ex.score.isna().sum()) == int(src.score.isna().sum()))
        check("exposures: no zero scores invented",
              int((ex.score == 0).sum()) ==
              int((src.score.fillna(-999) == 0).sum()))
        a = np.sort(ex.score.dropna().values)
        b = np.sort(src.score.dropna().values.astype("float32"))
        check("exposures: non-null score values match to 1e-6",
              len(a) == len(b) and np.allclose(a, b, atol=1e-6))

        # ---------- candidates: sim and recency must stay apart ----------
        cd = pd.read_parquet(os.path.join(root, "candidates"))
        csrc = pd.read_sql("SELECT sim, recency, score FROM rec_candidates",
                           conn)
        check("candidates: row count preserved", len(cd) == len(csrc))
        # Collapsing these two into one column is what produced the retracted
        # F-38. The export must never be the place that does it.
        check("candidates: sim and recency exported as separate columns",
              {"sim", "recency"}.issubset(set(cd.columns)))
        for col in ("sim", "recency", "score"):
            check(f"candidates: {col} values match to 1e-6",
                  np.allclose(np.sort(cd[col].values),
                              np.sort(csrc[col].values.astype("float32")),
                              atol=1e-6))

        # ---------- posts: the created_at/round trap ----------
        po = pd.read_parquet(os.path.join(root, "posts", "part.parquet"))
        psrc = pd.read_sql(
            "SELECT created_at, original_post_id FROM post", conn)
        check("posts: round equals source created_at",
              sorted(po["round"]) == sorted(pd.to_numeric(psrc.created_at)))
        check("posts: original_post_id nulls preserved (no invented reposts)",
              int(po.original_post_id.isna().sum()) ==
              int(psrc.original_post_id.isna().sum()))

        # ---------- actions ----------
        ac = pd.read_parquet(os.path.join(root, "actions", "part.parquet"))
        n_trace = conn.execute("SELECT COUNT(*) FROM trace").fetchone()[0]
        n_kinds = conn.execute(
            "SELECT COUNT(DISTINCT action) FROM trace").fetchone()[0]
        check("actions: row count preserved", len(ac) == n_trace)
        check("actions: every distinct action type survives",
              ac.action.nunique() == n_kinds)

        # ---------- B-34: can the export reproduce the DEPENDENT VARIABLE ----
        # The export used to pass every check above while still being unable
        # to answer the one question the package exists to answer. A trace row
        # does not say what it acted on: comment actions name a comment_id and
        # `follow` names the row it created, so both need a second table. The
        # exported package reported 41-65 % of true engagement, by a factor
        # that varied per run, which is worse than a constant bias because it
        # corrupts run-to-run comparison specifically.
        cm = pd.read_parquet(os.path.join(root, "comments", "part.parquet"))
        n_comments = conn.execute("SELECT COUNT(*) FROM comment").fetchone()[0]
        check("comments: table exported at all (the B-34 link)",
              len(cm) == n_comments)

        comment_acts = ac[ac.action.isin(
            ["create_comment", "like_comment", "unlike_comment",
             "dislike_comment", "undo_dislike_comment"])]
        check("actions: every comment action resolves to a target post",
              len(comment_acts) == 0
              or bool(comment_acts.target_post_id.notna().all()))
        check("actions: create_post has NO target post (it names its own)",
              bool(ac.loc[ac.action == "create_post",
                          "target_post_id"].isna().all()))
        follow_acts = ac[ac.action == "follow"]
        check("actions: follow resolves a target agent (B-6)",
              len(follow_acts) == 0
              or bool(follow_acts.target_agent_id.notna().all()))

        # The decisive one: engagement from the exported files alone, against
        # engagement from the database, computed the way analyze.py does it.
        seen = set(zip(ex.agent_id.tolist(), ex.post_id.tolist()))
        acted_pq = {(int(a), int(t)) for a, t
                    in zip(ac.agent_id.tolist(), ac.target_post_id.tolist())
                    if pd.notna(t)}
        eng_pq = len(seen & acted_pq)

        c2p = dict(conn.execute("SELECT comment_id, post_id FROM comment"))
        acted_db = set()
        for uid, action, info in conn.execute(
                "SELECT user_id, action, info FROM trace"):
            try:
                d = _json.loads(info) if info else {}
            except Exception:  # noqa: BLE001
                d = {}
            if not isinstance(d, dict):
                d = {}
            if action == "create_post":
                continue
            pid = next((_ci(d[k]) for k in
                        ("post_id", "original_post_id", "quoted_id",
                         "quoted_post_id", "reposted_id")
                        if _ci(d.get(k)) is not None), None)
            if pid is None and action.endswith("comment"):
                pid = c2p.get(_ci(d.get("comment_id")))
            if pid is not None:
                acted_db.add((uid, pid))
        eng_db = len(seen & acted_db)
        check(f"engagement reproducible from the package alone "
              f"({eng_pq} vs {eng_db} engaged (agent, post) pairs)",
              eng_pq == eng_db and eng_db > 0)

        # ---------- B-35: a re-export must REPLACE, not merge ----------
        # Partitioned tables write one file per round. Until this was fixed,
        # nothing removed partitions the new export does not produce, so a
        # label reused by a shorter run kept the longer run's rounds and the
        # merged result was valid Parquet with the right schema. That is how a
        # 36-agent run's rounds 5-11 ended up inside `scale99_full`.
        stale_dir = os.path.join(root, "exposures", "round=9999")
        os.makedirs(stale_dir, exist_ok=True)
        ex.head(3).to_parquet(os.path.join(stale_dir, "part.parquet"))
        n_before = len(pd.read_parquet(os.path.join(root, "exposures")))
        export_run(args.db, out)
        n_after = len(pd.read_parquet(os.path.join(root, "exposures")))
        check("re-export REPLACES stale partitions rather than merging "
              f"({n_before} -> {n_after}, source has {len(src)})",
              n_before == len(src) + 3 and n_after == len(src))

        # ---------- self-description ----------
        check("schema.json written", os.path.exists(
            os.path.join(root, "schema.json")))
        check("manifest.json carried alongside the data", os.path.exists(
            os.path.join(root, "manifest.json")))

        # ---------- the point of the exercise ----------
        pq_bytes = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, fs in os.walk(root) for f in fs
            if f.endswith(".parquet"))
        ratio = os.path.getsize(args.db) / pq_bytes
        check(f"parquet is materially smaller than sqlite ({ratio:.1f}x)",
              ratio > 5)

        conn.close()
    finally:
        shutil.rmtree(out, ignore_errors=True)

    print("=" * 62)
    print(f"{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        for f in FAIL:
            print(f"  FAILED: {f}")
        return 1
    print("Export fidelity verified: what goes in comes back out.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
