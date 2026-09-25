"""Analyse design-v2 shared worlds: do personas LIKE their own model's posts more?

IN PLAIN WORDS
--------------
Each decision is one persona meeting one post: like, dislike, or nothing.
With two models (llama, gemma) that both write and both play personas, the
question is a 2 x 2 table of like rates:

                      llama's posts   gemma's posts
    llama personas         a               b
    gemma personas         c               d

"llama's posts are better" raises a AND c. "llama personas like everything"
raises a AND b. Self-preference is what is left over: (a - b) - (c - d) -- how
much more llama personas prefer llama posts over gemma posts than gemma
personas do. Reported per model as half of that, so each model gets its share,
and the same for dislike rates (where self-preference shows up as NEGATIVE).
This is the same double difference as analyze.py (it is reused), with the same
two-way persona x slot cluster bootstrap for the 95 % interval.

It also answers "why so much nothing?": for each model, how many decisions were
a deliberate "nothing" versus an answer that broke (unreadable, cut off at the
token limit, timed out), and whether "nothing" rises for topics the persona
does not care about -- which it should, if it is a real choice.

    python analyze_world.py --labels w1_s10_w0,w1_s10_w1
    python analyze_world.py --prefix w1_          # every world whose label starts w1_
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
WORLDS = os.path.join(REPO, "data", "llm_bias", "worlds")


def finished(lab):
    m = os.path.join(WORLDS, lab, "manifest.json")
    return os.path.exists(m) and "finished_at" in json.load(open(m))


def load(labels=None, prefix=None, include_unfinished=False):
    """Unfinished worlds are skipped by default: half a world has only one model's people so far,
    which tilts every comparison (LF-15 LB-note: analysis_v2.txt of 2026-09-25 12:08 mixed one in)."""
    rows = []
    for f in sorted(glob.glob(os.path.join(WORLDS, "*", "decisions.jsonl"))):
        lab = os.path.basename(os.path.dirname(f))
        if labels and lab not in labels:
            continue
        if prefix and not lab.startswith(prefix):
            continue
        if not include_unfinished and not finished(lab):
            print(f"skipping unfinished world {lab}", file=sys.stderr)
            continue
        rows += [json.loads(l) for l in open(f) if l.strip()]
    df = pd.DataFrame(rows)
    if len(df) and not include_unfinished:
        # a post set counts only when BOTH rotation worlds are done (each person played by both models)
        full = df.groupby("seed")["world"].nunique()
        drop = sorted(full[full < 2].index)
        if drop:
            print(f"skipping post sets with only one finished world: {drop}", file=sys.stderr)
            df = df[~df["seed"].isin(drop)]
    return df


def to_long(df):
    """analyze.did/cluster_bootstrap expect: judge, author, persona, slot, post, up, down."""
    ok = df[df["outcome"] == "chose"].copy()
    ok["persona"] = ok["agent_id"]
    # post_key repeats across post sets (r0|cooking|gemma4:e2b exists in every seed); the seed makes it unique
    ok["post"] = ok["seed"].astype(str) + "|" + ok["post_key"]
    ok["up"] = (ok["action"] == "like").astype(int)
    ok["down"] = (ok["action"] == "dislike").astype(int)
    ok["nothing"] = (ok["action"] == "nothing").astype(int)
    return ok


def nothing_report(df):
    out = {}
    for j, g in df.groupby("judge"):
        n = len(g)
        acts = Counter(g["action"].fillna("FAILED"))
        oc = Counter(g["outcome"])
        chose_nothing = g[(g["outcome"] == "chose") & (g["action"] == "nothing")]
        out[j] = {
            "decisions": n,
            "like_%": round(100 * acts["like"] / n, 1), "dislike_%": round(100 * acts["dislike"] / n, 1),
            "nothing_%": round(100 * acts["nothing"] / n, 1), "failed_%": round(100 * acts["FAILED"] / n, 1),
            "outcomes": dict(oc),
            "needed_retry_%": round(100 * (g["attempts"] > 1).mean(), 1),
            "cut_off_at_token_limit": int((g["done_reason"] == "length").sum()),
            "hidden_thinking_chars": int(g["thinking_chars"].sum()),
            "mean_output_tokens": round(g["eval_tokens"].mean(), 1),
            "nothing_with_a_reason_%": round(100 * (chose_nothing["reason"].fillna("").str.len() > 3).mean(), 1)
            if len(chose_nothing) else None,
            "nothing_%_by_interest": (g.assign(n_=(g["action"] == "nothing").astype(float))
                                      .groupby("affinity")["n_"].mean().mul(100).round(1).to_dict()),
            "sample_nothing_reasons": chose_nothing["reason"].dropna().sample(
                min(6, len(chose_nothing)), random_state=0).tolist() if len(chose_nothing) else [],
        }
    return out


def analyze_worlds(df, B=2000):
    L = to_long(df)
    res = {"n_decisions": len(df), "n_valid": len(L), "judges": sorted(df["judge"].unique()),
           "authors": sorted(df["author"].unique()), "worlds": sorted(df["label"].unique()),
           "personas": int(df["agent_id"].nunique()), "posts": int((df["seed"].astype(str) + "|" + df["post_key"]).nunique())}
    for col in ("up", "down", "nothing"):
        res[f"rate_{col}"] = (L.pivot_table(index="judge", columns="author", values=col, aggfunc="mean")
                              .round(4).to_dict())
    for col in ("up", "down"):
        point = analyze.did(L, col)
        ci, p = analyze.cluster_bootstrap(L, col, B=B) if L["judge"].nunique() > 1 else ({}, None)
        res[f"sp_{col}"] = {k: {"est": v, "ci95": ci.get(k)} for k, v in point.items()}
        res[f"sp_{col}_p"] = p
    # within-persona: personas that were played by BOTH models (rotation across worlds)
    both = L.groupby("persona")["judge"].nunique()
    res["personas_played_by_both"] = int((both > 1).sum())
    res["like_by_interest"] = L.groupby(["judge", "affinity"])["up"].mean().unstack().mul(100).round(1).to_dict()
    res["like_by_topic_rank"] = L.groupby(["judge", "topic_rank"])["up"].mean().unstack().mul(100).round(1).to_dict()
    res["nothing"] = nothing_report(df)
    return res


def fmt(res):
    L = [f"worlds {res['worlds']}", f"{res['personas']} personas, {res['posts']} posts, "
         f"{res['n_valid']}/{res['n_decisions']} valid decisions",
         f"personas played by both models: {res['personas_played_by_both']}"]
    for col, name in (("up", "LIKE"), ("down", "DISLIKE"), ("nothing", "NOTHING")):
        L.append(f"\n{name} RATE (rows = model playing the persona, cols = model that wrote the post):")
        L.append((pd.DataFrame(res[f"rate_{col}"]) * 100).round(1).to_string())
    for col, name in (("up", "like"), ("down", "dislike")):
        L.append(f"\nSELF-PREFERENCE on {name} rate (double difference, percentage points):")
        for k, v in res[f"sp_{col}"].items():
            ci = v["ci95"]
            L.append(f"  {k:14s} {v['est'] * 100:+.1f}" + (f"  95% CI [{ci[0] * 100:+.1f}, {ci[1] * 100:+.1f}]" if ci else ""))
        if res.get(f"sp_{col}_p") is not None:
            L.append(f"  pooled bootstrap p = {res[f'sp_{col}_p']:.4f}")
    L.append("\nWHY 'NOTHING'? per model:")
    for j, v in res["nothing"].items():
        L.append(f"  {j}: like {v['like_%']}%  dislike {v['dislike_%']}%  nothing {v['nothing_%']}%  "
                 f"failed {v['failed_%']}% | outcomes {v['outcomes']} | retried {v['needed_retry_%']}% | "
                 f"cut off {v['cut_off_at_token_limit']} | hidden thinking chars {v['hidden_thinking_chars']} | "
                 f"'nothing' with a reason {v['nothing_with_a_reason_%']}%")
        L.append(f"     nothing % by interest (-2..+2): {v['nothing_%_by_interest']}")
        L.append(f"     sample reasons for nothing: {v['sample_nothing_reasons']}")
    L.append("\nLIKE % by persona interest in the topic:\n" + pd.DataFrame(res["like_by_interest"]).to_string())
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels")
    ap.add_argument("--prefix")
    ap.add_argument("--out")
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--include-unfinished", action="store_true")
    a = ap.parse_args()
    df = load(a.labels.split(",") if a.labels else None, a.prefix, a.include_unfinished)
    res = analyze_worlds(df, B=a.B)
    print(fmt(res))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1, default=str)


if __name__ == "__main__":
    main()
