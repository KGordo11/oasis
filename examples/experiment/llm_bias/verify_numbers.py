"""Independent check of the numbers on the LD-18 pages (2026-10-02).

Recomputes every headline and breakdown straight from the raw files (reactions.csv, posts.csv, users.csv) with plain
pandas, WITHOUT the analysis code that produced analysis.json / deep.json, and compares. Prints one line per check:
OK when the two agree to the shown precision, MISMATCH otherwise.

    python verify_numbers.py
"""

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors  # noqa: E402

D = os.path.join(authors.DATA, "two_ai")
A, B = "gemma4:e2b", "gemma3:1b"
R = pd.read_csv(os.path.join(D, "reactions.csv"))
P = pd.read_csv(os.path.join(D, "posts.csv"))
U = pd.read_csv(os.path.join(D, "users.csv"))
RES = json.load(open(os.path.join(D, "analysis.json")))
DEEP = json.load(open(os.path.join(D, "deep.json")))
bad = 0


def check(name, mine, theirs, tol=0.05):
    global bad
    ok = (mine == theirs) if isinstance(mine, (str, int)) and isinstance(theirs, (str, int)) else abs(float(mine) - float(theirs)) <= tol
    bad += not ok
    print(f"{'OK      ' if ok else 'MISMATCH'} {name}: recomputed {mine}  page data {theirs}")


V = R[R.outcome == "chose"].copy()
V["up"], V["down"], V["none"] = (V.action == "like") * 100.0, (V.action == "dislike") * 100.0, (V.action == "nothing") * 100.0
rate = V.groupby(["played_by", "written_by"])[["up", "down", "none"]].mean()


def dd(df, col):
    r = df.groupby(["played_by", "written_by"])[col].mean()
    return (r[(A, A)] - r[(A, B)]) - (r[(B, A)] - r[(B, B)])


print("== counts")
check("votes", len(R), RES["decisions"])
check("valid votes", len(V), RES["valid"])
check("rounds", R["round"].nunique(), len(RES["rounds"]))
check("users", V.user_id.nunique(), 100)
check("posts written", int(P.ok.sum()), RES["posts"]["written"])
check("posts failed", int((~P.ok).sum()), RES["posts"]["failed"])
check("duplicate bodies", int(P[P.ok].body.duplicated().sum()), RES["posts"]["duplicate_bodies"])
check("posts shown", V.seed.astype(str).add(V.post_key).nunique(), DEEP["n_posts"])
print("== the four boxes (percent)")
for j, a in [(A, A), (A, B), (B, A), (B, B)]:
    for c, k in (("up", "up"), ("down", "down")):
        check(f"{k} {j.split(':')[0]} users on {a.split(':')[0]} posts", round(rate.loc[(j, a), c], 2),
              round(RES[f"rate_{k}"][a][j] * 100, 2), 0.01)
print("== headline")
check("own-AI upvote boost", round(dd(V, "up"), 2), round(RES["sp_up"]["_pooled"]["est"] * 100, 2), 0.01)
check("own-AI downvote change", round(dd(V, "down"), 2), round(RES["sp_down"]["_pooled"]["est"] * 100, 2), 0.01)
g4 = rate.loc[(A, A), "up"] - rate.loc[(A, B), "up"]
g3 = rate.loc[(B, B), "up"] - rate.loc[(B, A), "up"]
check("gemma4 crowd: own minus other (up)", round(g4, 2), round((RES["rate_up"][A][A] - RES["rate_up"][B][A]) * 100, 2), 0.02)
check("gemma3 crowd: own minus other (up)", round(g3, 2), round((RES["rate_up"][B][B] - RES["rate_up"][A][B]) * 100, 2), 0.02)
print("== per round")
for r, g in V.groupby("round"):
    pr = next(x for x in RES["per_round"] if x["round"] == r)
    check(f"round {r} upvote boost", round(dd(g, "up"), 2), round(pr["like_dd"] * 100, 2), 0.011)
pos = sum(dd(g, "up") > 0 for _, g in V.groupby("round"))
check("rounds with upvote boost > 0", int(pos), RES["round_boot_up"]["rounds_positive"])
print("== per user")
pu = pd.Series({u: dd(g, "up") for u, g in V.groupby("user_id")}).round(9)  # float noise: exact ties must count as 0
check("users with boost > 0", int((pu > 0).sum()), DEEP["per_user"]["up_positive"])
check("users with boost < 0", int((pu < 0).sum()), DEEP["per_user"]["up_negative"])
check("users with boost = 0", int((pu == 0).sum()), DEEP["per_user"]["up_zero"])
check("user 0 boost", round(pu[0], 1), round(next(x for x in DEEP["per_user"]["values"] if x["user_id"] == 0)["up"], 1), 0.06)
print("== breakdowns")
for t, g in V.groupby("topic"):
    check(f"subreddit {t}", round(dd(g, "up"), 2), next(x for x in DEEP["by_topic"] if x["label"] == t)["up"]["est"], 0.01)
for v, g in V.groupby("voting_style"):
    check(f"voting {v}", round(dd(g, "up"), 2), next(x for x in DEEP["by_voting"] if x["label"] == v)["up"]["est"], 0.01)
for a, g in V.groupby("affinity"):
    check(f"interest {a}", round(dd(g, "up"), 2), next(x for x in DEEP["by_interest"] if x["label"] == a)["up"]["est"], 0.01)
gen = V[V.voting_style == "generous"].groupby("played_by").up.mean()
print(f"         (generous voters upvote overall: {gen.round(1).to_dict()})")
check("rounds 1-7", round(dd(V[V["round"] <= 7], "up"), 2), DEEP["by_half"][0]["up"]["est"], 0.01)
check("rounds 8-15", round(dd(V[V["round"] >= 8], "up"), 2), DEEP["by_half"][1]["up"]["est"], 0.01)
print("== agreement")
w = V.assign(post=V.seed.astype(str) + V.post_key).pivot_table(index=["user_id", "post"], columns="played_by", values="action", aggfunc="first").dropna()
same = (w[A] == w[B]).mean() * 100
pe = sum((w[A] == k).mean() * (w[B] == k).mean() for k in ("like", "dislike", "nothing"))
kap = ((same / 100) - pe) / (1 - pe)
check("same choice %", round(same, 1), round(DEEP["agreement"]["same_pct"], 1), 0.06)
check("kappa", round(kap, 3), round(RES["agreement"]["kappa"], 3), 0.002)
print("== top 10")
sc = V.assign(post=V.seed.astype(str) + V.post_key, s=(V.action == "like").astype(int) - (V.action == "dislike").astype(int))
sc = sc.groupby(["round", "played_by", "post", "written_by"]).s.sum().reset_index()
own = {j: np.mean([(g.sort_values(["s", "post"], ascending=[False, True]).head(10).written_by == j).sum()
                   for _, g in sc[sc.played_by == j].groupby("round")]) for j in (A, B)}
check("gemma4 crowd: own posts in top 10", round(own[A], 2), round(RES["top10"]["mean_own_share"][A], 2), 0.01)
check("gemma3 crowd: own posts in top 10", round(own[B], 2), round(RES["top10"]["mean_own_share"][B], 2), 0.01)
print("== posts and length")
ok = P[P.ok]
for a in (A, B):
    check(f"{a} mean words", round(ok[ok.author == a].words.mean(), 1), RES["posts"]["words_mean"][a], 0.06)
print("== interest (upvote % at -2 and +2)")
for j in (A, B):
    s = V[V.played_by == j].groupby("affinity").up.mean()
    check(f"{j} at -2", round(s[-2], 1), DEEP["up_by_interest"][j]["-2"], 0.06)
    check(f"{j} at +2", round(s[2], 1), DEEP["up_by_interest"][j]["2"], 0.06)
print("== timing")
check("votes failed", int((R.outcome != "chose").sum()), RES["decisions"] - RES["valid"])
print(f"\n{bad} mismatches")
