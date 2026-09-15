"""Gate for build_package.py — the folder handed to someone else.

Every defect this file has had was invisible from inside: B-27 published one
run's timings under another's name, B-34's half of the problem was an index that
disagreed with the tables it shipped beside, and the turn-count column was right
about a quantity nobody wanted. None of them would fail a test that only asked
whether the builder ran.

So each check below compares the package against something computed a DIFFERENT
way -- the tables against the index, the index against the manifests -- because
a package can only be wrong in ways it cannot see itself.

    python test_build_package.py [--pkg data/sim4_package]
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys

import pandas as pd

PASS, FAIL = [], []


def check(label: str, cond: bool) -> None:
    (PASS if cond else FAIL).append(label)
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", default="data/sim4_package")
    ap.add_argument("--parquet-dir", default="data/parquet")
    args = ap.parse_args()

    idx = {r["run"]: r for r in csv.DictReader(
        open(os.path.join(args.pkg, "runs_index.csv")))}
    ex = pd.read_parquet(os.path.join(args.pkg, "exposures.parquet"))
    ac = pd.read_parquet(os.path.join(args.pkg, "actions.parquet"))

    # ---------- nothing silently dropped ----------
    exported = {d for d in os.listdir(args.parquet_dir)
                if os.path.exists(os.path.join(args.parquet_dir, d, "manifest.json"))}
    check(f"every exported run appears in the index ({len(exported)} exported)",
          exported <= set(idx))

    # ---------- feed_turns is the denominator the analysis uses ----------
    refresh = ac[ac.action == "refresh"].groupby("run").size().to_dict()
    wrong = [r for r, n in refresh.items()
             if idx.get(r, {}).get("feed_turns") and int(idx[r]["feed_turns"]) != n]
    check(f"feed_turns equals the refresh count in every run ({len(refresh)} checked)",
          not wrong)
    # and that it is NOT the same as agent_turns_total, which counts round 0
    differ = [r for r in refresh
              if idx.get(r, {}).get("feed_turns") and idx[r].get("agent_turns_total")
              and int(idx[r]["feed_turns"]) != int(idx[r]["agent_turns_total"])]
    check("feed_turns is distinct from agent_turns_total (round 0 serves no feed)",
          len(differ) > 0)

    # ---------- the index must agree with the tables beside it (B-34) ----------
    seen = ex.groupby("run").apply(
        lambda d: set(zip(d.agent_id, d.post_id)), include_groups=False)
    act = ac[ac.target_post_id.notna()].groupby("run").apply(
        lambda d: set(zip(d.agent_id, d.target_post_id.astype("int64"))),
        include_groups=False)
    bad = []
    for run, s in seen.items():
        pub = idx.get(run, {}).get("engagement_pct")
        if not s or not pub:
            continue
        got = 100 * len(s & act.get(run, set())) / len(s)
        if abs(got - float(pub)) >= 0.01:
            bad.append((run, round(got, 3), float(pub)))
    check(f"engagement_pct reproduces from exposures+actions for every run "
          f"({sum(1 for r in seen.index if idx.get(r, {}).get('engagement_pct'))} checked)",
          not bad)
    if bad:
        for row in bad[:5]:
            print(f"        {row}")

    # ---------- timings belong to the run they are filed under (B-27) ----------
    tt = pd.read_csv(os.path.join(args.pkg, "round_timings.csv"))
    off = []
    for run, g in tt.groupby("run"):
        mp = os.path.join(args.parquet_dir, run, "manifest.json")
        if not os.path.exists(mp):
            continue
        total = json.load(open(mp)).get("total_seconds")
        if total and abs(g.wall_seconds.sum() - total) / total > 0.05:
            off.append(run)
    check(f"round timings sum to each run's own total_seconds within 5% "
          f"({tt.run.nunique()} runs)", not off)
    if off:
        print(f"        {off[:5]}")

    # ---------- the comment link, without which engagement is unreachable ----------
    cm_path = os.path.join(args.pkg, "comments.parquet")
    check("comments.parquet shipped (the B-34 link)", os.path.exists(cm_path))
    if os.path.exists(cm_path):
        cm = pd.read_parquet(cm_path)
        # create_comment MUST resolve: the run just created that comment, so a
        # miss means the comment table or the back-reference is broken.
        made = ac[ac.action == "create_comment"]
        check(f"every create_comment resolves to its post ({len(made)} actions)",
              len(made) == 0 or bool(made.target_post_id.notna().all()))
        # like_comment may legitimately fail to resolve: the model sometimes
        # likes a comment_id that never existed -- the comment analogue of B-10
        # phantom follows. Bound it rather than forbid it, so a real regression
        # (a broken join) still fails while the known phenomenon does not.
        liked = ac[ac.action == "like_comment"]
        phantom = int(liked.target_post_id.isna().sum()) if len(liked) else 0
        rate = phantom / len(liked) if len(liked) else 0.0
        check(f"phantom comment-likes stay rare ({phantom}/{len(liked)} = "
              f"{100*rate:.2f}%, hallucinated comment ids)", rate < 0.05)
        check(f"comments table is non-trivial ({len(cm)} rows)", len(cm) > 0)

    print("\n" + "=" * 62)
    print(f"{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        return 1
    print("The package agrees with the tables it ships and the manifests it came from.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
