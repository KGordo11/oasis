"""Feed test results (LD-17 item 4): does the AI that plays the crowd push its own posts to the top?

IN PLAIN WORDS
--------------
Each run: one AI plays all 50 people on one post set's 75 posts (25 per writer AI), counts visible or hidden.
  top10_share   how many of the final top 10 each writer got, per crowd and mode
  own_boost     for each writer W: its top-10 share when W runs the crowd, minus its average share when the other
                AIs run the crowd, on the same posts (the feed version of the fair comparison)
  like_boost    the same fair comparison on single reactions (double difference: each crowd first compared with its
                own habits, so a crowd that likes everything doesn't look biased)
  snowball      with visible counts, how unequal the final scores are (share of all likes that went to the top 10
                posts), against the hidden baseline
Intervals: resampling post sets (few of them, so ranges are wide; stated as such).

    python analyze_feed.py --out data/llm_bias/analysis_feed.json
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FEEDS = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..", "..")), "data", "llm_bias", "feeds")
AIS = ["llama3.1:8b", "gemma4:e2b", "mistral:7b"]


def load():
    runs = []
    for m in sorted(glob.glob(os.path.join(FEEDS, "feed_s*", "manifest.json"))):
        d = os.path.dirname(m)
        man = json.load(open(m))
        board = json.load(open(os.path.join(d, "leaderboard.json")))
        dec = [json.loads(x) for x in open(os.path.join(d, "decisions.jsonl")) if x.strip()]
        runs.append({"man": man, "board": board, "dec": dec})
    return runs


def summarise(runs, sets):
    """Per mode: top-10 share and like rate by crowd x writer, over the given post sets (with repeats allowed)."""
    out = {}
    for mode in ("visible", "hidden"):
        top = {c: {w: [] for w in AIS} for c in AIS}
        like = {c: {w: [0, 0] for w in AIS} for c in AIS}
        conc = []
        for s in sets:
            for r in runs:
                m = r["man"]
                if m["seed"] != s or m["mode"] != mode:
                    continue
                c = m["crowd"]
                for w in AIS:
                    top[c][w].append(m["top10_by_author"].get(w, 0) / 10)
                for d in r["dec"]:
                    if d["action"]:
                        like[c][d["author"]][0] += d["action"] == "like"
                        like[c][d["author"]][1] += 1
                tot = sum(max(0, b["like"]) for b in r["board"]) or 1
                conc.append(sum(b["like"] for b in r["board"][:10]) / tot)
        t = {c: {w: float(np.mean(v)) if v else float("nan") for w, v in top[c].items()} for c in AIS}
        lr = {c: {w: (v[0] / v[1] if v[1] else float("nan")) for w, v in like[c].items()} for c in AIS}
        own = {w: t[w][w] - float(np.mean([t[c][w] for c in AIS if c != w])) for w in AIS}
        # fair version: first centre each crowd on its own habits (how much more it likes writer w than the other
        # writers), then compare w's own crowd with the other crowds -- the same double difference as the main test.
        # A crowd that likes everything (mistral ~98 %) no longer looks like it favours anyone.
        rel = {c: {w: lr[c][w] - float(np.mean([lr[c][v] for v in AIS if v != w])) for w in AIS} for c in AIS}
        lown = {w: rel[w][w] - float(np.mean([rel[c][w] for c in AIS if c != w])) for w in AIS}
        out[mode] = {"top10_share": t, "like_rate": lr, "own_top10_boost": own, "own_like_boost": lown,
                     "top10_like_concentration": float(np.mean(conc)) if conc else float("nan")}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--out")
    a = ap.parse_args()
    runs = load()
    sets = sorted({r["man"]["seed"] for r in runs})
    res = {"post_sets": sets, "runs": len(runs), **summarise(runs, sets)}
    # resample post sets for ranges on the pooled boosts
    rng = np.random.default_rng(0)
    draws = {mode: {k: [] for k in ("top", "like")} for mode in ("visible", "hidden")}
    for _ in range(a.B if len(sets) > 1 else 0):
        pick = list(rng.choice(sets, size=len(sets), replace=True))
        s = summarise(runs, pick)
        for mode in draws:
            draws[mode]["top"].append(np.mean(list(s[mode]["own_top10_boost"].values())))
            draws[mode]["like"].append(np.mean(list(s[mode]["own_like_boost"].values())))
    for mode in ("visible", "hidden"):
        res[mode]["pooled_own_top10_boost"] = float(np.mean(list(res[mode]["own_top10_boost"].values())))
        res[mode]["pooled_own_like_boost"] = float(np.mean(list(res[mode]["own_like_boost"].values())))
        if draws[mode]["top"]:
            res[mode]["pooled_own_top10_boost_ci95"] = [float(np.percentile(draws[mode]["top"], q)) for q in (2.5, 97.5)]
            res[mode]["pooled_own_like_boost_ci95"] = [float(np.percentile(draws[mode]["like"], q)) for q in (2.5, 97.5)]
    print(json.dumps(res, indent=1))
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
