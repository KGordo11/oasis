"""Can we stop gemma writing longer posts than llama? (LF-15/16: length may explain the like signal.)

IN PLAIN WORDS
--------------
Both models get the exact briefs of an existing post set (default: set 10), but with a
tighter word target, and the posts go to a SEPARATE bank (data/llm_bias/lengthtest/), so
no real post set is touched. Then it compares post lengths with the real set.

  --band 75,85        the target printed in the prompt ("Body: 75 to 85 words.")
  --enforce 65,95     also reject and retry posts outside this range (costs retries)

Nothing is judged here: it only writes posts (about 3 minutes for 50).

    python length_test.py --label prompt80 --band 75,85
    python length_test.py --label enforce80 --band 75,85 --enforce 65,95
"""

from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors  # noqa: E402
from topics import PRIMARY  # noqa: E402

OUT = os.path.join(authors.DATA, "lengthtest")


def summarize(bank, label):
    rows = {}
    for r in bank.values():
        if r.get("ok"):
            rows.setdefault(r["author"], []).append(r["words"])
    out = {}
    for a, w in sorted(rows.items()):
        out[a] = {"n": len(w), "mean": round(st.mean(w), 1), "sd": round(st.pstdev(w), 1), "min": min(w), "max": max(w)}
    ms = [v["mean"] for v in out.values()]
    gap = round(max(ms) - min(ms), 1) if len(ms) == 2 else None
    print(f"{label:>12}: " + "  ".join(f"{a} {v['mean']}±{v['sd']} [{v['min']}-{v['max']}] n={v['n']}" for a, v in out.items())
          + f"  | gap {gap}")
    return out, gap


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--seed", type=int, default=10, help="reuse this post set's briefs")
    ap.add_argument("--band", default="75,85")
    ap.add_argument("--enforce", help="lo,hi: retry posts outside this word range")
    ap.add_argument("--authors", default="llama3.1:8b,gemma4:e2b")
    ap.add_argument("--rounds", type=int, default=5)
    a = ap.parse_args()
    lo, hi = a.band.split(",")
    authors.AUTHOR_USER = authors.AUTHOR_USER.replace("- Body: 60 to 120 words.", f"- Body: {lo} to {hi} words.")
    assert f"{lo} to {hi} words" in authors.AUTHOR_USER
    if a.enforce:
        elo, ehi = map(int, a.enforce.split(","))
        base = authors.validate_post

        def strict(obj):
            v = base(obj)
            n = len(v["body"].split())
            if not elo <= n <= ehi:
                raise ValueError(f"body {n} words (want {elo}-{ehi})")
            return v
        authors.validate_post = strict
    os.makedirs(OUT, exist_ok=True)
    authors.bank_path = lambda seed: os.path.join(OUT, f"{a.label}_s{seed}.jsonl")
    bank = authors.generate(a.seed, a.rounds, PRIMARY, a.authors.split(","))
    real = {}
    for line in open(os.path.join(authors.DATA, f"postbank_s{a.seed}.jsonl")):
        r = json.loads(line)
        if r["round"] < a.rounds and r["topic"] in PRIMARY:
            real[r["key"]] = r
    res = {"label": a.label, "band": a.band, "enforce": a.enforce, "seed": a.seed}
    res["real"], res["real_gap"] = summarize(real, f"set {a.seed}")
    res["test"], res["test_gap"] = summarize(bank, a.label)
    att = [r["attempts"] for r in bank.values()]
    res["mean_attempts"] = round(st.mean(att), 2)
    res["failed"] = sum(1 for r in bank.values() if not r.get("ok"))
    print(f"attempts per post {res['mean_attempts']}, failed {res['failed']}")
    json.dump(res, open(os.path.join(OUT, f"{a.label}_summary.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
