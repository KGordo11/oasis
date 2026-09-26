"""Health check for finished design-v2 worlds -- run after every world, before trusting its numbers.

IN PLAIN WORDS
--------------
A world can "finish" and still be wrong: a person skipped, a decision recorded twice,
an answer cut off, the wrong model playing someone, the OASIS database disagreeing
with the decision log, or a run that was slowed down by something else on the machine.
This script checks each of those and prints PASS / WARN / FAIL per world. It reads
files only and never calls a model, so it is safe to run while a campaign is going.

    python check_world.py                  # every finished world whose label starts v2_
    python check_world.py --labels v2_s13_w1
Exit code 1 if any world FAILs.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
WORLDS = os.path.join(REPO, "data", "llm_bias", "worlds")
sys.path.insert(0, HERE)
from personas import PINNED_BANK_HASH, PINNED_CORE99_HASH  # noqa: E402


def load(lab):
    d = os.path.join(WORLDS, lab)
    man = json.load(open(os.path.join(d, "manifest.json")))
    dec = [json.loads(l) for l in open(os.path.join(d, "decisions.jsonl")) if l.strip()]
    return man, dec


def check(lab, baseline):
    man, dec = load(lab)
    cfg = man["config"]
    fails, warns, notes = [], [], []
    n_exp = cfg["agents"] * man.get("n_posts", 50)
    if "finished_at" not in man:
        fails.append("not finished")
    if len(dec) != n_exp:
        fails.append(f"{len(dec)} decisions, expected {n_exp}")
    pairs = Counter((d["agent_id"], d["post_key"]) for d in dec)
    dup = sum(1 for v in pairs.values() if v > 1)
    if dup:
        fails.append(f"{dup} person-post pairs recorded twice")
    if man.get("persona_bank_hash") != PINNED_BANK_HASH or man.get("core99_hash") != PINNED_CORE99_HASH:
        fails.append("persona fingerprint differs from the pinned 99")
    judges = cfg["judges"]
    wrong = sum(1 for d in dec if d["judge"] != judges[(d["agent_id"] + cfg["world"]) % len(judges)])
    if wrong:
        fails.append(f"{wrong} decisions played by the wrong model (rotation broken)")
    oc = Counter(d["outcome"] for d in dec)
    bad = len(dec) - oc.get("chose", 0)
    if bad:
        (fails if bad > 0.01 * len(dec) else warns).append(f"{bad} decisions without a valid choice {dict(oc)}")
    cut = sum(1 for d in dec if d.get("done_reason") == "length")
    think = sum(d.get("thinking_chars", 0) for d in dec)
    retry = sum(1 for d in dec if d.get("attempts", 1) > 1)
    if cut:
        warns.append(f"{cut} answers cut off at the token limit")
    if think:
        warns.append(f"{think} characters of hidden thinking")
    if retry > 0.02 * len(dec):
        warns.append(f"{retry} decisions needed a retry")
    # OASIS database must agree with the decision log
    db = os.path.join(WORLDS, lab, "oasis.db")
    if os.path.exists(db):
        c = sqlite3.connect(db)
        n_like = c.execute("select count(*) from like").fetchone()[0]
        n_dis = c.execute("select count(*) from dislike").fetchone()[0]
        n_post = c.execute("select count(*) from post").fetchone()[0]
        c.close()
        a = Counter(d["action"] for d in dec)
        if (n_like, n_dis) != (a.get("like", 0), a.get("dislike", 0)):
            fails.append(f"OASIS db likes/dislikes {n_like}/{n_dis} != log {a.get('like', 0)}/{a.get('dislike', 0)}")
        if n_post != man.get("n_posts", 50):
            fails.append(f"OASIS db has {n_post} posts")
    # behaviour and speed against the other finished worlds
    fmt = cfg.get("format", "scroll")
    for j in judges:
        g = [d for d in dec if d["judge"] == j]
        if not g:
            continue
        like = 100 * np.mean([d["action"] == "like" for d in g])
        spd = man.get("judges", {}).get(j, {})
        notes.append(f"{j}: like {like:.0f}%  {spd.get('s_per_decision', float('nan')):.2f} s/decision"
                     f"{' (resumed: timing covers only part)' if spd.get('rows', spd.get('decisions', 0)) < len(g) else ''}")
        bj = baseline.get((j, fmt))
        if bj:
            b_like = np.mean([x[0] for x in bj])
            b_sd = max(3.0, float(np.std([x[0] for x in bj])) if len(bj) > 1 else 3.0)
            if abs(like - b_like) > max(10, 3 * b_sd):
                warns.append(f"{j} like rate {like:.0f}% vs {b_like:.0f}% in other worlds")
            b_s = np.median([x[1] for x in bj if x[1]]) if any(x[1] for x in bj) else None
            s = spd.get("s_per_decision")
            if s and b_s and s > 1.2 * b_s:
                warns.append(f"{j} {s:.2f} s/decision vs usual {b_s:.2f} (machine busy? B-32)")
    status = "FAIL" if fails else "WARN" if warns else "PASS"
    return status, fails, warns, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels")
    ap.add_argument("--prefix", default="v2_s")
    a = ap.parse_args()
    labs = sorted(os.path.basename(os.path.dirname(m)) for m in glob.glob(os.path.join(WORLDS, "*", "manifest.json")))
    labs = [l for l in labs if l.startswith(a.prefix) and "finished_at" in json.load(open(os.path.join(WORLDS, l, "manifest.json")))]
    targets = a.labels.split(",") if a.labels else labs
    # baseline: like rate and speed per judge over every finished world (flash attention on only, for speed)
    base = {}
    for l in labs:
        man, dec = load(l)
        fa = man.get("ollama_server", {}).get("OLLAMA_FLASH_ATTENTION") == "true"
        fmt = man["config"].get("format", "scroll")
        for j, v in man.get("judges", {}).items():
            g = [d for d in dec if d["judge"] == j]
            if g:
                full = v.get("rows", v.get("decisions", 0)) >= len(g)
                base.setdefault((j, fmt), []).append((100 * np.mean([d["action"] == "like" for d in g]),
                                               v.get("s_per_decision") if (fa and full) else None))
    worst = 0
    for l in targets:
        st, f, w, n = check(l, base)
        worst = max(worst, {"PASS": 0, "WARN": 1, "FAIL": 2}[st])
        print(f"{st}  {l}  " + " | ".join(n))
        for x in f:
            print(f"   FAIL: {x}")
        for x in w:
            print(f"   warn: {x}")
    sys.exit(1 if worst == 2 else 0)


if __name__ == "__main__":
    main()
