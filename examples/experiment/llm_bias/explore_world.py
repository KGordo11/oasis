"""Exploratory analysis of design-v2 worlds -- what drives each reaction, beyond the headline.

IN PLAIN WORDS
--------------
The headline test (analyze_world.py) asks one question: do people played by a
model like that model's posts more? This script looks around it, using the
per-reaction export (data/llm_bias/export/reactions.csv, posts.csv, users.csv):

  1. Self-preference topic by topic, and only where the person cares about the
     topic (interest 0..+2) versus where they don't (-2..-1).
  2. Same person, two models: every person is played by llama in one world and
     by gemma in the other, on the same posts. How often do the two versions
     react the same way, and how much of that is more than chance?
  3. Do the two models agree on which posts are good?
  4. Post length: who writes longer posts, and does length sway either model?
  5. Scroll position: do likes fade the further down the scroll a post sits?
  6. Persona traits: does "harsh" / "generous" voting style actually show up?
  7. Reasons: how specific are they, and do they mention the person's own life?

Only COMPLETE post sets are used (both rotation worlds finished) -- a
half-finished set has one model's people only and would bias every comparison.
Everything here is exploratory: none of it was pre-specified, so p-values and
intervals are descriptive, not confirmatory.

    python explore_world.py                 # prints the report
    python explore_world.py --out data/llm_bias/explore_v2.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EXPORT = os.path.join(REPO, "data", "llm_bias", "export")
WORLDS = os.path.join(REPO, "data", "llm_bias", "worlds")
SHORT = {"llama3.1:8b": "llama", "gemma4:e2b": "gemma"}


def finished(label):
    m = os.path.join(WORLDS, label, "manifest.json")
    return os.path.exists(m) and "finished_at" in json.load(open(m))


def load(sets=None):
    R = pd.read_csv(os.path.join(EXPORT, "reactions.csv"))
    P = pd.read_csv(os.path.join(EXPORT, "posts.csv"))
    U = pd.read_csv(os.path.join(EXPORT, "users.csv"))
    R = R[R["world_label"].str.startswith("v2_")]
    # keep a post set only if every one of its worlds finished
    ok = R.groupby("post_set_seed")["world_label"].agg(lambda s: all(finished(l) for l in s.unique())
                                                        and s.nunique() == 2)
    R = R[R["post_set_seed"].isin(ok[ok].index)].copy()
    if sets:
        R = R[R["post_set_seed"].isin(sets)].copy()
    R["judge"] = R["controlling_model"]
    R["author"] = R["post_author_model"]
    R["persona"] = R["user_id"]
    R["slot"] = R["post_set_seed"].astype(str) + "|" + R["post_key"].str.rsplit("|", n=1).str[0]
    R["post"] = R["post_uid"]
    R["up"] = (R["action"] == "like").astype(int)
    R["down"] = (R["action"] == "dislike").astype(int)
    R["nothing"] = (R["action"] == "nothing").astype(int)
    R["cares"] = R["user_interest_in_topic"] >= 0
    R = R.merge(P[["post_uid", "words", "post_type"]], on="post_uid", how="left")
    U1 = U.drop_duplicates("user_id")[["user_id", "age", "gender", "profession", "place", "voting_style"]]
    R = R.merge(U1, on="user_id", how="left")
    return R, P, U1


def fast_bootstrap(df, col, B=2000, seed=0, chunk=200, mode="both", sd_only=False):
    """analyze.cluster_bootstrap, vectorised: SAME random draws (same generator, same order), same pooled
    double difference, ~50x faster. Checked equal to the original in test_llm_bias.py."""
    rng = np.random.default_rng(seed)
    personas, slots = df["persona"].unique(), df["slot"].unique()
    p_idx = pd.Categorical(df["persona"], categories=personas).codes
    s_idx = pd.Categorical(df["slot"], categories=slots).codes
    judges, authors_ = sorted(df["judge"].unique()), sorted(df["author"].unique())
    cell = (pd.Categorical(df["judge"], categories=judges).codes * len(authors_)
            + pd.Categorical(df["author"], categories=authors_).codes)
    M1 = np.zeros((len(df), len(judges) * len(authors_)))
    M1[np.arange(len(df)), cell] = 1.0
    Mx = M1 * df[col].values[:, None]
    draws = []
    for start in range(0, B, chunk):
        W = []
        for _ in range(min(chunk, B - start)):
            wp = rng.multinomial(len(personas), np.ones(len(personas)) / len(personas))
            ws = rng.multinomial(len(slots), np.ones(len(slots)) / len(slots))
            if mode == "posts":
                wp = np.ones(len(personas))
            if mode == "people":
                ws = np.ones(len(slots))
            W.append(wp[p_idx] * ws[s_idx])
        W = np.asarray(W, dtype=float)
        with np.errstate(invalid="ignore", divide="ignore"):
            R = (W @ Mx) / (W @ M1)
        R = R.reshape(len(W), len(judges), len(authors_))
        for r in R:
            rel = np.array([[r[k, a] - np.mean([r[k, b] for b in range(len(authors_)) if b != a])
                             for a in range(len(authors_))] for k in range(len(judges))])
            vals = []
            for J, jn in enumerate(judges):
                if jn not in authors_:
                    continue
                a = authors_.index(jn)
                others = [rel[K, a] for K in range(len(judges)) if K != J]
                vals.append(rel[J, a] - np.mean(others))
            v = float(np.mean(vals))
            if np.isfinite(v):
                draws.append(v)
    d = np.array(draws)
    if sd_only:
        return float(np.std(d))
    ci = (float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)))
    p = float(min(1.0, 2 * min((d <= 0).mean(), (d >= 0).mean())))
    return ci, p


def sp(df, B):
    """Self-preference double difference (points) with the persona x slot cluster bootstrap."""
    out = {}
    for col in ("up", "down"):
        est = analyze.did(df, col)["_pooled"]
        ci, p = fast_bootstrap(df, col, B=B)
        ci = {"_pooled": ci}
        out[col] = {"est": round(100 * est, 1), "ci95": [round(100 * x, 1) for x in ci["_pooled"]], "p": p}
    out["n"] = len(df)
    return out


def rates(df):
    """{"<model> people": {"<model> posts": %}} -- spelled out, because pivot().to_dict() is keyed column-first."""
    out = {}
    for a in ("up", "down", "nothing"):
        m = df.groupby(["judge", "author"])[a].mean().mul(100).round(1)
        out[a] = {f"{SHORT[j]} people": {f"{SHORT[au]} posts": v for (jj, au), v in m.items() if jj == j}
                  for j in m.index.get_level_values(0).unique()}
    return out


def kappa(a, b):
    """Cohen's kappa: agreement beyond what the two sides' overall habits would give by chance."""
    cats = sorted(set(a) | set(b))
    po = float(np.mean(a == b))
    pe = sum(float(np.mean(a == c)) * float(np.mean(b == c)) for c in cats)
    return round((po - pe) / (1 - pe), 3), round(100 * po, 1), round(100 * pe, 1)


def same_person(R):
    """Pair each (person, post) as played by llama with the same pair played by gemma."""
    w = R.pivot_table(index=["persona", "post"], columns="judge", values="action", aggfunc="first").dropna()
    a, b = w["llama3.1:8b"].values, w["gemma4:e2b"].values
    out = {"pairs": len(w), "crosstab_rows_llama_cols_gemma": pd.crosstab(w["llama3.1:8b"], w["gemma4:e2b"]).to_dict(),
           "all": dict(zip(("kappa", "agree_%", "chance_%"), kappa(a, b)))}
    cares = R.drop_duplicates(["persona", "post"]).set_index(["persona", "post"])["cares"].reindex(w.index)
    for name, m in (("cares", cares.values), ("does_not_care", ~cares.values)):
        out[name] = dict(zip(("kappa", "agree_%", "chance_%"), kappa(a[m], b[m])))
    # like vs not-like only, where the person cares: is the persona adding anything beyond the post?
    return out


def post_agreement(R):
    """Per post: like rate among people who care about the topic, llama-played vs gemma-played."""
    c = R[R["cares"]]
    t = c.pivot_table(index="post", columns="judge", values="up", aggfunc="mean").dropna()
    rho = t.corr(method="spearman").iloc[0, 1]
    r = t.corr().iloc[0, 1]
    P = c.drop_duplicates("post").set_index("post")[["author", "topic", "words"]]
    t = t.join(P)
    t["gap"] = t["llama3.1:8b"] - t["gemma4:e2b"]
    return {"posts": len(t), "spearman": round(float(rho), 3), "pearson": round(float(r), 3),
            "sd_like_rate_llama": round(100 * t["llama3.1:8b"].std(), 1),
            "sd_like_rate_gemma": round(100 * t["gemma4:e2b"].std(), 1)}, t


def length_effects(R):
    """Words by author; like rate by length tercile per judge (people who care only)."""
    P = R.drop_duplicates("post")
    words = P.groupby("author")["words"].describe()[["mean", "50%", "min", "max"]].round(0)
    c = R[R["cares"]].copy()
    c["length"] = pd.qcut(c["words"], 3, labels=["short", "medium", "long"])
    by = c.pivot_table(index="judge", columns="length", values="up", aggfunc="mean", observed=True).mul(100).round(1)
    # does length explain self-preference? linear probability model with post and persona x judge fixed effects
    import statsmodels.formula.api as smf
    d = R.copy()
    d["self"] = (d["judge"] == d["author"]).astype(int)
    d["g_judge"] = (d["judge"] == "gemma4:e2b").astype(int)
    d["z_words"] = (d["words"] - d["words"].mean()) / d["words"].std()
    d["pj"] = d["persona"].astype(str) + "|" + d["judge"]
    out = {"words_by_author": words.to_dict(), "like_%_by_length_cares": by.to_dict()}
    # slot by slot: is the double difference bigger where gemma's post is much longer than llama's?
    from scipy import stats
    Lm, Gm = "llama3.1:8b", "gemma4:e2b"
    g = c.groupby(["slot", "judge", "author"])[["up", "down"]].mean().unstack(["judge", "author"])
    if all((col, j, au) in g.columns for col in ("up", "down") for j in (Lm, Gm) for au in (Lm, Gm)):
        dd = {col: (g[(col, Lm, Lm)] - g[(col, Lm, Gm)]) - (g[(col, Gm, Lm)] - g[(col, Gm, Gm)]) for col in ("up", "down")}
        w = R.drop_duplicates("post").pivot_table(index="slot", columns="author", values="words")
        gap = (w[Gm] - w[Lm]).reindex(dd["up"].index)
        q = pd.qcut(gap, 3, labels=["similar", "middle", "gemma_much_longer"])
        out["by_slot"] = {"slots": int(gap.notna().sum()), "gemma_longer_%": round(100 * float((gap > 0).mean()), 1),
                          "mean_word_gap": round(float(gap.mean()), 1)}
        for col in ("up", "down"):
            ok = dd[col].notna() & gap.notna()
            r, pv = stats.spearmanr(gap[ok], dd[col][ok])
            out["by_slot"][col] = {"spearman": round(float(r), 3), "p": round(float(pv), 4),
                                   "dd_by_gap_tercile": (100 * dd[col].groupby(q, observed=True).mean()).round(1).to_dict(),
                                   "gap_tercile_words": gap.groupby(q, observed=True).mean().round(0).to_dict()}
    for name, f in (("self_only", "up ~ self + C(post) + C(pj)"),
                    ("self_plus_judge_x_length", "up ~ self + g_judge:z_words + C(post) + C(pj)"),
                    ("dislike_self_only", "down ~ self + C(post) + C(pj)"),
                    ("dislike_self_plus_judge_x_length", "down ~ self + g_judge:z_words + C(post) + C(pj)")):
        m = smf.ols(f, data=d).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d["slot"])[0]})
        keep = [k for k in ("self", "g_judge:z_words") if k in m.params]
        out[name] = {k: {"coef_pts": round(100 * m.params[k], 2),
                         "ci95": [round(100 * x, 2) for x in m.conf_int().loc[k]]} for k in keep}
    return out


def position_effects(R):
    by_pos = R.groupby(["judge", "position_in_topic"])["up"].mean().unstack().mul(100).round(1)
    R = R.assign(scroll_decile=pd.cut(R["scroll_position"], [0, 10, 20, 30, 40, 50], labels=["1-10", "11-20", "21-30", "31-40", "41-50"]))
    c = R[R["cares"]]
    by_scroll = c.groupby(["judge", "scroll_decile"], observed=True)["up"].mean().unstack().mul(100).round(1)
    return {"like_%_by_position_in_topic": by_pos.to_dict(), "like_%_by_scroll_position_cares": by_scroll.to_dict()}


def trait_effects(R):
    out = {}
    for col in ("voting_style", "gender"):
        out[col] = {a: R.groupby(["judge", col])[a].mean().unstack().mul(100).round(1).to_dict()
                    for a in ("up", "down", "nothing")}
    R = R.assign(age_band=pd.cut(R["age"], [0, 29, 44, 59, 120], labels=["<30", "30-44", "45-59", "60+"]))
    out["age_band"] = {a: R.groupby(["judge", "age_band"], observed=True)[a].mean().unstack().mul(100).round(1).to_dict()
                       for a in ("up", "down")}
    return out


GENERIC = re.compile(r"^(good|great|nice|solid|cool|interesting|relatable|helpful|useful|love|not (really )?(my|for me)|meh|boring)\b", re.I)


def reason_effects(R):
    R = R.assign(rlen=R["reason"].fillna("").str.split().str.len(),
                 generic=R["reason"].fillna("").str.strip().str.match(GENERIC))

    def mentions_self(row):
        txt = str(row["reason"]).lower()
        hits = [str(row["profession"]).split()[-1].lower(), str(row["place"]).lower()]
        return any(h and len(h) > 3 and h in txt for h in hits) or bool(re.search(r"\b(my|i'm|i am|as a)\b", txt))
    R["personal"] = R.apply(mentions_self, axis=1)
    g = R.groupby("judge")
    out = {"mean_words": g["rlen"].mean().round(1).to_dict(),
           "generic_%": g["generic"].mean().mul(100).round(1).to_dict(),
           "mentions_own_life_%": g["personal"].mean().mul(100).round(1).to_dict(),
           "distinct_reasons_%": g["reason"].agg(lambda s: 100 * s.nunique() / len(s)).round(1).to_dict(),
           "top_reasons": {j: s["reason"].str.lower().str.strip(" .!").value_counts().head(8).to_dict()
                           for j, s in g}}
    own = R.assign(own_post=R["judge"] == R["author"]).groupby(["judge", "own_post"])[["rlen", "personal"]].mean().round(3)
    out["own_vs_other_post"] = {f"{SHORT[j]}|{'own' if s else 'other'}": v for (j, s), v in own.to_dict("index").items()}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=1000)
    ap.add_argument("--out")
    ap.add_argument("--sets", help="only these post sets, e.g. 14,15 (the held-out test, LD-12)")
    a = ap.parse_args()
    R, P, U = load([int(x) for x in a.sets.split(",")] if a.sets else None)
    res = {"post_sets": sorted(int(x) for x in R["post_set_seed"].unique()), "reactions": len(R),
           "people": int(R["persona"].nunique()), "posts": int(R["post"].nunique())}
    res["headline"] = sp(R, a.B)
    res["by_topic"] = {t: sp(g, a.B) for t, g in R.groupby("topic")}
    sets = sorted(R["post_set_seed"].unique())
    res["by_set"] = {str(k): sp(R[R["post_set_seed"] == k], a.B) for k in sets}
    res["cumulative"] = {str(k): sp(R[R["post_set_seed"] <= k], a.B) for k in sets}
    # where does the uncertainty come from? resample only people, only posts (slots), or both
    res["uncertainty_sd_points"] = {col: {m: round(100 * fast_bootstrap(R, col, B=min(a.B, 500), mode=m, sd_only=True), 2)
                                          for m in ("people", "posts", "both")} for col in ("up", "down")}
    res["by_caring"] = {("cares" if k else "does_not_care"): sp(g, a.B) for k, g in R.groupby("cares")}
    res["rates_cares"] = rates(R[R["cares"]])
    res["rates_does_not_care"] = rates(R[~R["cares"]])
    res["same_person"] = same_person(R)
    res["post_agreement"], posts = post_agreement(R)
    res["length"] = length_effects(R)
    res["position"] = position_effects(R)
    res["traits"] = trait_effects(R)
    res["reasons"] = reason_effects(R)
    txt = json.dumps(res, indent=1, default=str)
    print(txt)
    if a.out:
        open(a.out, "w").write(txt)
        posts.round(3).to_csv(a.out.replace(".json", "_posts.csv"))


if __name__ == "__main__":
    main()
