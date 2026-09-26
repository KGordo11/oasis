"""LD-13 A/B: does showing the two posts side by side create self-preference that scrolling does not?

IN PLAIN WORDS
--------------
Same length-matched posts, same 50 people, two formats:
  scroll  one post per call: like / dislike / nothing (design v2)
  pair    the two posts of one brief together: like / dislike / nothing on each, plus a favourite
For each format we compute the usual fair-comparison number (double difference) on likes and dislikes, and for
the pair format also on favourites (like night 1). Then the FORMAT EFFECT: pair minus scroll. All intervals come
from one bootstrap that resamples people and briefs (slots) together for both formats, because both formats
share the same people and the same briefs.

Only post sets where all four worlds (2 formats x 2 rotations) finished are used.

    python analyze_ab.py --out data/llm_bias/analysis_ab.json
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
WORLDS = os.path.join(REPO, "data", "llm_bias", "worlds")
FORMATS = ("scroll", "pair")


def load():
    rows, fin = [], {}
    for m in sorted(glob.glob(os.path.join(WORLDS, "ab_s*", "manifest.json"))):
        lab = os.path.basename(os.path.dirname(m))
        j = json.load(open(m))
        if "finished_at" not in j:
            continue
        fin.setdefault(j["config"]["seed"], set()).add((j["config"]["format"], j["config"]["world"]))
        rows += [json.loads(x) for x in open(os.path.join(os.path.dirname(m), "decisions.jsonl")) if x.strip()]
    df = pd.DataFrame(rows)
    full = [s for s, v in fin.items() if len(v) == 4]
    if not len(df) or not full:
        return df.iloc[0:0], []
    df = df[df["seed"].isin(full) & (df["outcome"] == "chose")].copy()
    df["persona"] = df["agent_id"]
    df["up"] = (df["action"] == "like").astype(int)
    df["down"] = (df["action"] == "dislike").astype(int)
    df["nothing"] = (df["action"] == "nothing").astype(int)
    if "chosen" not in df:
        df["chosen"] = np.nan
    return df, sorted(full)


def dd(r, judges, authors, centre=True):
    """Pooled double difference from a judges x authors rate matrix (same formula as analyze.did)."""
    def rel(k, a):
        if not centre:
            return r[k, a]
        return r[k, a] - np.mean([r[k, b] for b in range(len(authors)) if b != a])
    vals = []
    for J, jn in enumerate(judges):
        if jn not in authors:
            continue
        a = authors.index(jn)
        vals.append(rel(J, a) - np.mean([rel(K, a) for K in range(len(judges)) if K != J]))
    return float(np.mean(vals))


def analyze_ab(df, B=2000, seed=0, chunk=200):
    judges, authors = sorted(df["judge"].unique()), sorted(df["author"].unique())
    personas, slots = df["persona"].unique(), df["slot"].unique()
    p_idx = pd.Categorical(df["persona"], categories=personas).codes
    s_idx = pd.Categorical(df["slot"], categories=slots).codes
    nc = len(judges) * len(authors)
    cell = (pd.Categorical(df["judge"], categories=judges).codes * len(authors)
            + pd.Categorical(df["author"], categories=authors).codes)
    measures = [("scroll", "up"), ("scroll", "down"), ("pair", "up"), ("pair", "down"), ("pair", "chosen")]
    mats = {}
    for f, col in measures:
        m = (df["format"] == f).values
        if col == "chosen":
            m = m & df["chosen"].notna().values
        M1 = np.zeros((len(df), nc))
        M1[np.flatnonzero(m), cell[m]] = 1.0
        mats[(f, col)] = (M1, M1 * np.nan_to_num(df[col].values.astype(float))[:, None])

    def point(W):
        out = {}
        for f, col in measures:
            M1, Mx = mats[(f, col)]
            with np.errstate(invalid="ignore", divide="ignore"):
                r = ((W @ Mx) / (W @ M1)).reshape(len(judges), len(authors))
            out[f"{f}_{col}"] = dd(r, judges, authors, centre=(col != "chosen"))
        out["format_effect_up"] = out["pair_up"] - out["scroll_up"]
        out["format_effect_down"] = out["pair_down"] - out["scroll_down"]
        return out
    est = point(np.ones(len(df)))
    rng = np.random.default_rng(seed)
    draws = {k: [] for k in est}
    for start in range(0, B, chunk):
        for _ in range(min(chunk, B - start)):
            wp = rng.multinomial(len(personas), np.ones(len(personas)) / len(personas))
            ws = rng.multinomial(len(slots), np.ones(len(slots)) / len(slots))
            for k, v in point((wp[p_idx] * ws[s_idx]).astype(float)).items():
                if np.isfinite(v):
                    draws[k].append(v)
    res = {}
    for k, v in est.items():
        d = np.array(draws[k])
        res[k] = {"est": round(100 * v, 2), "ci95": [round(100 * float(np.percentile(d, q)), 2) for q in (2.5, 97.5)],
                  "p": round(float(min(1.0, 2 * min((d <= 0).mean(), (d >= 0).mean()))), 4)}
    return res


def describe(df):
    out = {"reactions": int(len(df)), "people": int(df["persona"].nunique()), "slots": int(df["slot"].nunique())}
    for f, g in df.groupby("format"):
        out[f] = {"rates_%": {f"{j} people": {f"{a} posts": {c: round(100 * float(x[c].mean()), 1) for c in ("up", "down", "nothing")}
                                               for a, x in gj.groupby("author")} for j, gj in g.groupby("judge")}}
        if f == "pair":
            out[f]["favourite_share_%"] = {f"{j} people": {f"{a} posts": round(100 * float(x["chosen"].mean()), 1)
                                                           for a, x in gj.groupby("author")} for j, gj in g.groupby("judge")}
            out[f]["position_1_picked_%"] = round(100 * float(g[g["pair_pos"] == 1]["chosen"].mean()), 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--out")
    a = ap.parse_args()
    df, sets = load()
    if not sets:
        print("no complete A/B post set yet")
        return
    res = {"post_sets": sets, **describe(df), "effects_points": analyze_ab(df, B=a.B)}
    print(json.dumps(res, indent=1))
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
