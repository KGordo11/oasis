"""Test the hypothesis: does a model playing a persona prefer posts that model wrote?

IN PLAIN WORDS
--------------
Every judge run on the same seed saw the SAME posts in the SAME order for the
same personas. So we can build a table: rows = judge model, columns = author
model, cell = how often that judge's personas picked that author's post as
their favourite.

A model's posts being picked a lot is NOT evidence of self-preference -- they
might just be better posts, and then every judge picks them. Self-preference is
the DIAGONAL standing out:

    SP(J) = [how often judge J picks J's posts]
          - [how often the OTHER judges pick J's posts]

That is a difference-in-differences: the second term removes "J writes good
posts". SP > 0 means J favours its own writing beyond what other models think it
deserves. Chance is 1 / (number of authors) for the raw share, 0 for SP.

Uncertainty: a two-way cluster bootstrap. Decisions are not independent -- the
same persona votes every round, and every persona sees the same posts in a round
-- so we resample PERSONAS and SLOTS (round x topic) together, 2000 times.

Second, independent check: a conditional logit (McFadden choice model). Each
favourite pick is one choice among the posts shown. Predictors: `self` (post
written by the judge model), a fixed effect for every individual post (absorbs
post quality completely), and screen position. The `self` odds ratio is the
multiplicative boost a post gets from being the judge's own writing.

The same difference-in-differences is reported for upvote and downvote rates.

Manipulation checks (does the persona matter at all?): upvote rate by the
persona's interest in the topic, and favourite rate by screen position.

    python analyze.py --seed 1            # all runs on seed 1
    python analyze.py --runs a,b,c        # explicit run labels
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RUNS = os.path.join(REPO, "data", "llm_bias", "runs")


def load_decisions(labels=None, seed=None, exclude_prefix=("smoke",)):
    rows = []
    for d in sorted(glob.glob(os.path.join(RUNS, "*", "decisions.jsonl"))):
        label = os.path.basename(os.path.dirname(d))
        if labels and label not in labels:
            continue
        if not labels and label.startswith(exclude_prefix):
            continue
        for line in open(d):
            if line.strip():
                r = json.loads(line)
                if seed is not None and r["seed"] != seed:
                    continue
                rows.append(r)
    return rows


def long_table(decisions):
    """One row per (decision, post shown)."""
    out = []
    for i, d in enumerate(decisions):
        if not d["ok"]:
            continue
        slot = f"{d['seed']}|{d['round']}|{d['topic']}"
        for pos, (k, a) in enumerate(zip(d["shown_keys"], d["shown_authors"])):
            v = d["votes"].get(k, "none")
            out.append({"dec": i, "label": d["label"], "judge": d["judge"], "author": a, "post": k,
                        "slot": slot, "persona": d["agent_id"], "pos": pos, "n_posts": d["n_posts"],
                        "chosen": int(d["favorite_key"] == k), "up": int(v == "up"), "down": int(v == "down"),
                        "affinity": d["affinity"], "self": int(a == d["judge"])})
    return pd.DataFrame(out)


def matrix(df, col):
    return df.pivot_table(index="judge", columns="author", values=col, aggfunc="mean")


def did(df, col, weights=None):
    """SP(J) for every judge J that is also an author. Returns {J: value} plus pooled mean."""
    w = np.ones(len(df)) if weights is None else weights
    tmp = df.assign(_w=w, _x=df[col] * w)
    g = tmp.groupby(["judge", "author"])[["_x", "_w"]].sum()
    rate = (g["_x"] / g["_w"]).to_dict()
    judges = sorted(df["judge"].unique())
    authors_ = sorted(df["author"].unique())
    # Favourite shares sum to 1 per judge, so a judge's overall generosity cannot
    # leak in and the simple difference is enough (and reads in share points).
    # Up/down RATES do not: a judge that upvotes 80 % of everything would look
    # "self-preferring" next to one that upvotes 20 %. For those, centre each
    # judge's rate on its own mean for the OTHER authors first (double difference).
    centre = col != "chosen"

    def rel(K, A):
        if not centre:
            return rate[(K, A)]
        rest = [rate[(K, B)] for B in authors_ if B != A and (K, B) in rate]
        return rate[(K, A)] - float(np.mean(rest))

    out = {}
    for J in judges:
        if (J, J) not in rate:
            continue
        others = [rel(K, J) for K in judges if K != J and (K, J) in rate]
        if others:
            out[J] = rel(J, J) - float(np.mean(others))
    if out:
        out["_pooled"] = float(np.mean([v for k, v in out.items()]))
    return out


def cluster_bootstrap(df, col, B=2000, seed=0):
    """Two-way (persona x slot) cluster bootstrap of did(). Returns {key: (lo, hi)} and bootstrap p for pooled."""
    rng = np.random.default_rng(seed)
    personas = df["persona"].unique()
    slots = df["slot"].unique()
    p_idx = pd.Categorical(df["persona"], categories=personas).codes
    s_idx = pd.Categorical(df["slot"], categories=slots).codes
    draws = defaultdict(list)
    for _ in range(B):
        wp = rng.multinomial(len(personas), np.ones(len(personas)) / len(personas))
        ws = rng.multinomial(len(slots), np.ones(len(slots)) / len(slots))
        w = wp[p_idx] * ws[s_idx]
        if w.sum() == 0:
            continue
        for k, v in did(df, col, w.astype(float)).items():
            if np.isfinite(v):
                draws[k].append(v)
    ci = {k: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) for k, v in draws.items()}
    pooled = np.array(draws.get("_pooled", [np.nan]))
    # two-sided bootstrap p: how often the resampled pooled effect crosses zero
    p = float(min(1.0, 2 * min((pooled <= 0).mean(), (pooled >= 0).mean()))) if len(pooled) > 1 else None
    return ci, p


def clogit_self(df):
    """Conditional logit: chosen ~ self + post FE + position FE, one choice set per decision."""
    try:
        from statsmodels.discrete.conditional_models import ConditionalLogit
    except ImportError:
        return {"error": "statsmodels missing"}
    if df["self"].sum() == 0 or df["judge"].nunique() < 2:
        return {"error": "needs >=2 judges that are also authors"}
    # Every choice set holds one post per author of ONE slot, so that slot's post
    # dummies sum to 1 inside the set -- collinear with the set itself. Drop one
    # reference post per slot (not one overall) to identify the rest.
    ref = set(df.groupby("slot")["post"].min())
    X = pd.get_dummies(df["post"].astype(str), prefix="post", dtype=float)
    X = X.drop(columns=[f"post_{p}" for p in ref])
    X = X.join(pd.get_dummies(df["pos"].astype(str), prefix="pos", drop_first=True, dtype=float))
    X.insert(0, "self", df["self"].astype(float))
    X = X.loc[:, X.std() > 0]
    try:
        res = ConditionalLogit(df["chosen"].values, X.values, groups=df["dec"].values).fit(disp=0, maxiter=200)
    except Exception as e:  # singular designs on tiny smoke data
        return {"error": str(e)[:200]}
    b, se = float(res.params[0]), float(res.bse[0])
    return {"beta_self": b, "se": se, "odds_ratio": float(np.exp(b)),
            "or_ci": [float(np.exp(b - 1.96 * se)), float(np.exp(b + 1.96 * se))],
            "p": float(res.pvalues[0]), "n_choices": int(df["dec"].nunique())}


def _clogit_design(df):
    """Dense design for the fast conditional logit: rows grouped by decision, K options each."""
    df = df.sort_values(["dec", "pos"])
    K = df.groupby("dec").size()
    if K.nunique() != 1:
        raise ValueError("fast clogit needs equal-size choice sets")
    k = int(K.iloc[0])
    ref = set(df.groupby("slot")["post"].min())
    posts = sorted(p for p in df["post"].unique() if p not in ref)
    pidx = {p: i for i, p in enumerate(posts)}
    n = len(df)
    D = np.zeros((n, 1 + len(posts) + (k - 1)))
    D[:, 0] = df["self"].values
    for r, p in enumerate(df["post"].values):
        if p in pidx:
            D[r, 1 + pidx[p]] = 1.0
    pos = df["pos"].values
    for r, q in enumerate(pos):
        if q > 0:
            D[r, 1 + len(posts) + q - 1] = 1.0
    decs = df["dec"].values.reshape(-1, k)[:, 0]
    return D, df["chosen"].values.reshape(-1, k), k, decs, df


def fast_clogit(D, Y, k, w=None, ridge=1e-4):
    """Weighted conditional logit by L-BFGS. Returns beta vector (beta[0] = self)."""
    from scipy.optimize import minimize
    n = Y.shape[0]
    w = np.ones(n) if w is None else w
    pen = np.full(D.shape[1], ridge)
    pen[0] = 0.0

    def f(theta):
        U = (D @ theta).reshape(n, k)
        U = U - U.max(axis=1, keepdims=True)
        lse = np.log(np.exp(U).sum(axis=1, keepdims=True))
        logp = U - lse
        ll = (w[:, None] * Y * logp).sum()
        P = np.exp(logp)
        G = (w[:, None] * (Y - P)).reshape(-1)
        grad = D.T @ G
        return -ll + 0.5 * (pen * theta ** 2).sum(), -grad + pen * theta
    res = minimize(f, np.zeros(D.shape[1]), jac=True, method="L-BFGS-B", options={"maxiter": 500})
    return res.x


def clogit_cluster_bootstrap(df, B=300, seed=1):
    """Two-way (persona x slot) cluster bootstrap of the conditional-logit self coefficient.

    The plain clogit standard error treats every pick as independent; picks share
    personas and posts, so that p-value is too small. This one is not.
    """
    try:
        D, Y, k, decs, sdf = _clogit_design(df)
    except ValueError as e:
        return {"error": str(e)}
    first = sdf.groupby("dec").first()
    per = first.loc[decs, "persona"].values
    slo = first.loc[decs, "slot"].values
    pc = pd.Categorical(per).codes
    sc = pd.Categorical(slo).codes
    npers, nslot = pc.max() + 1, sc.max() + 1
    rng = np.random.default_rng(seed)
    beta0 = fast_clogit(D, Y, k)[0]
    bs = []
    for _ in range(B):
        wp = rng.multinomial(npers, np.ones(npers) / npers)
        ws = rng.multinomial(nslot, np.ones(nslot) / nslot)
        w = (wp[pc] * ws[sc]).astype(float)
        if w.sum() == 0:
            continue
        bs.append(fast_clogit(D, Y, k, w)[0])
    bs = np.array(bs)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    p = float(min(1.0, 2 * min((bs <= 0).mean(), (bs >= 0).mean())))
    return {"beta_self": float(beta0), "odds_ratio": float(np.exp(beta0)),
            "or_ci_cluster": [float(np.exp(lo)), float(np.exp(hi))], "p_cluster": p, "B": len(bs)}


def family_preference(df):
    """LQ-1: does a judge favour its SIBLING model's posts? (llama3.1 <-> llama3.2)"""
    fam = {"llama3.1:8b": "llama", "llama3.2:3b": "llama"}
    out = {}
    judges = sorted(df["judge"].unique())
    rate = df.groupby(["judge", "author"])["chosen"].mean().to_dict()
    for J in judges:
        sibs = [A for A in judges if A != J and fam.get(A) and fam.get(A) == fam.get(J)]
        for S in sibs:
            others = [rate[(K, S)] for K in judges if K not in (J, S) and (K, S) in rate]
            if (J, S) in rate and others:
                out[f"{J} -> {S}"] = rate[(J, S)] - float(np.mean(others))
    return out


def analyze(decisions, B=2000):
    df = long_table(decisions)
    n_dec = len(decisions)
    ok = sum(d["ok"] for d in decisions)
    res = {"n_decisions": n_dec, "n_valid": ok,
           "valid_rate": ok / n_dec if n_dec else None,
           "judges": sorted(df["judge"].unique().tolist()) if len(df) else [],
           "authors": sorted(df["author"].unique().tolist()) if len(df) else []}
    if not len(df):
        return res, df
    A = df["author"].nunique()
    res["chance_share"] = 1 / A
    res["favorite_matrix"] = matrix(df, "chosen").round(4).to_dict()
    res["up_matrix"] = matrix(df, "up").round(4).to_dict()
    res["down_matrix"] = matrix(df, "down").round(4).to_dict()
    res["raw_self_share"] = {J: float(df[(df.judge == J) & (df.author == J)]["chosen"].mean())
                             for J in res["judges"] if J in res["authors"]}
    for col in ("chosen", "up", "down"):
        point = did(df, col)
        ci, p = cluster_bootstrap(df, col, B=B) if df["judge"].nunique() > 1 else ({}, None)
        res[f"sp_{col}"] = {k: {"est": v, "ci95": ci.get(k)} for k, v in point.items()}
        res[f"sp_{col}_pooled_p"] = p
    res["clogit"] = clogit_self(df)
    res["clogit_cluster"] = clogit_cluster_bootstrap(df, B=min(B, 300)) if res["clogit"].get("odds_ratio") else {}
    res["family"] = family_preference(df)
    res["up_by_affinity"] = df.groupby(["judge", "affinity"])["up"].mean().unstack().round(3).to_dict()
    res["down_by_affinity"] = df.groupby(["judge", "affinity"])["down"].mean().unstack().round(3).to_dict()
    res["favorite_by_position"] = df.groupby(["judge", "pos"])["chosen"].mean().unstack().round(3).to_dict()
    res["author_word_counts"] = {}
    return res, df


def fmt(res):
    L = [f"decisions {res['n_decisions']}, valid {res['n_valid']} ({(res['valid_rate'] or 0):.1%})",
         f"judges {res['judges']}", f"authors {res['authors']}"]
    if "favorite_matrix" not in res:
        return "\n".join(L)
    L.append(f"chance share per author = {res['chance_share']:.3f}")
    fm = pd.DataFrame(res["favorite_matrix"])
    L.append("\nFAVOURITE SHARE (rows judge, cols author):\n" + fm.to_string(float_format=lambda x: f"{x:.3f}"))
    for col, name in (("chosen", "favourite"), ("up", "upvote"), ("down", "downvote")):
        L.append(f"\nSELF-PREFERENCE (diff-in-diff) on {name} rate:")
        for k, v in res[f"sp_{col}"].items():
            ci = v["ci95"]
            L.append(f"  {k:16s} {v['est']:+.4f}" + (f"  95% CI [{ci[0]:+.4f}, {ci[1]:+.4f}]" if ci else ""))
        if res.get(f"sp_{col}_pooled_p") is not None:
            L.append(f"  pooled bootstrap p = {res[f'sp_{col}_pooled_p']:.4f}")
    L.append(f"\nCONDITIONAL LOGIT (post + position fixed effects): {res['clogit']}")
    L.append(f"  with two-way cluster bootstrap: {res.get('clogit_cluster')}")
    L.append(f"\nFAMILY (judge -> sibling author, diff-in-diff on favourite share): {res.get('family')}")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int)
    ap.add_argument("--runs")
    ap.add_argument("--out")
    ap.add_argument("--B", type=int, default=2000)
    a = ap.parse_args()
    labels = a.runs.split(",") if a.runs else None
    decisions = load_decisions(labels, a.seed)
    res, _ = analyze(decisions, B=a.B)
    print(fmt(res))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1, default=str)


if __name__ == "__main__":
    sys.exit(main())
