"""LD-18 two-AI rounds: the full analysis and the export (one command, re-run after every round).

IN PLAIN WORDS
--------------
Every round both AIs write 25 new posts (5 per topic). Then AI A plays all 100 users through all posts, and AI B
plays the same 100 users through the same posts. So for every post we know how 100 users reacted when played by A
and when played by B. Questions:

1. Own-post boost: do users played by an AI upvote that AI's posts more than users played by the other AI do?
   The fair number is the double difference (same as every earlier test):
       (A-users' like rate on A posts - on B posts) - (B-users' like rate on A posts - on B posts)
   "A's posts are just better" and "A-users like everything" both cancel; what is left is the own-AI boost.
   Same for downvotes (where an own-AI boost shows as a NEGATIVE number).
2. Is it steady? The same number round by round, and a 95 % interval that resamples whole rounds (the strictest:
   ~94 % of the uncertainty in earlier tests came from which posts got written), plus the usual two-way
   user x slot bootstrap.
3. Is it just length? In each slot both AIs wrote from the same brief; regress the slot's double difference on the
   word gap between the two posts. The intercept is the boost when both posts are the same length.
4. Who plays the users matters how much? Same user, same post, two AIs: how often do they make the same choice?
5. Leaderboard: which AI's posts end up in each crowd's top 10 (score = upvotes - downvotes over 100 users)?
6. Timing, failures, post lengths, duplicate check (no post body may repeat across rounds).

    python analyze_two_ai.py            # writes data/llm_bias/two_ai/{analysis.json, *.csv}
"""

from __future__ import annotations

import glob
import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze  # noqa: E402
import analyze_world  # noqa: E402
import authors  # noqa: E402
import personas  # noqa: E402

OUT = os.path.join(authors.DATA, "two_ai")
PREFIX = "two_r"


def kappa(a, b):
    """Cohen's kappa for two lists of labels (agreement beyond chance)."""
    a, b = np.asarray(a), np.asarray(b)
    po = (a == b).mean()
    pe = sum((a == k).mean() * (b == k).mean() for k in set(a) | set(b))
    return float((po - pe) / (1 - pe)) if pe < 1 else 1.0


def slot_table(L, col):
    """One row per slot: rate[judge][author] over the 100 users, the double difference, and the word gap."""
    r = L.groupby(["slot", "judge", "author"])[col].mean().unstack(["judge", "author"])
    return r


def main(B=2000):
    os.makedirs(OUT, exist_ok=True)
    df = analyze_world.load(prefix=PREFIX)
    if df.empty:
        raise SystemExit("no finished rounds yet")
    df["round"] = df["seed"] - 200
    A, Bm = sorted(df["judge"].unique(), reverse=True)  # gemma4:e2b, gemma3:1b
    L = analyze_world.to_long(df)
    posts = pd.DataFrame([r for s in sorted(df["seed"].unique()) for r in authors.load_bank(int(s)).values()])
    posts["round_n"] = posts["seed"] - 200
    words = {(f"{r.seed}|{r.round}|{r.topic}", r.author): r.words for r in posts.itertuples() if r.ok}
    res = {"generated_at": datetime.now().isoformat(timespec="seconds"), "ai_a": A, "ai_b": Bm,
           "rounds": sorted(int(x) for x in df["round"].unique()), "users": int(df["agent_id"].nunique()),
           "posts_shown": int(L["post"].nunique()), "decisions": len(df), "valid": len(L),
           "failed": int((df["outcome"] != "chose").sum())}

    # 1. pooled double difference (the earlier tests' helper) + two-way user x slot bootstrap
    base = analyze_world.analyze_worlds(df, B=B)
    for k in ("rate_up", "rate_down", "rate_nothing", "sp_up", "sp_down", "sp_up_p", "sp_down_p",
              "like_by_interest", "like_by_topic_rank", "nothing", "personas_played_by_both"):
        res[k] = base[k]

    # 2. per round, and a bootstrap over whole rounds
    def dd(sub, col):
        r = sub.groupby(["judge", "author"])[col].mean()
        return float((r[(A, A)] - r[(A, Bm)]) - (r[(Bm, A)] - r[(Bm, Bm)]))
    per_round = []
    for rnd, g in L.groupby("round"):
        rates = g.groupby(["judge", "author"])[["up", "down", "nothing"]].mean()
        per_round.append({"round": int(rnd), "like_dd": dd(g, "up"), "dislike_dd": dd(g, "down"),
                          "posts": int(g["post"].nunique()),
                          **{f"{c}_{j.split(':')[0]}_on_{a.split(':')[0]}": float(rates.loc[(j, a), c])
                             for c in ("up", "down", "nothing") for j in (A, Bm) for a in (A, Bm)}})
    res["per_round"] = per_round
    rng = np.random.default_rng(0)
    rounds = sorted(L["round"].unique())
    by_r = {r: g for r, g in L.groupby("round")}
    for col in ("up", "down"):
        draws = []
        if len(rounds) > 1:
            for _ in range(B):
                pick = rng.choice(rounds, len(rounds))
                draws.append(dd(pd.concat([by_r[r] for r in pick]), col))
        res[f"round_boot_{col}"] = {"est": dd(L, col),
                                    "ci95": [float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))]
                                    if draws else None,
                                    "p": float(min(1, 2 * min(np.mean(np.array(draws) <= 0), np.mean(np.array(draws) >= 0))))
                                    if draws else None,
                                    "rounds_positive": int(sum(x[f"{'like' if col == 'up' else 'dislike'}_dd"] > 0 for x in per_round))}

    # 3. length: slot-level double difference vs word gap (A's post words - B's post words)
    import statsmodels.formula.api as smf
    rows = []
    for slot, g in L.groupby("slot"):
        r = g.groupby(["judge", "author"])[["up", "down"]].mean()
        if len(r) < 4:
            continue
        rows.append({"slot": slot, "round": int(g["round"].iloc[0]), "topic": g["topic"].iloc[0],
                     "like_dd": (r.loc[(A, A), "up"] - r.loc[(A, Bm), "up"]) - (r.loc[(Bm, A), "up"] - r.loc[(Bm, Bm), "up"]),
                     "dislike_dd": (r.loc[(A, A), "down"] - r.loc[(A, Bm), "down"]) - (r.loc[(Bm, A), "down"] - r.loc[(Bm, Bm), "down"]),
                     "words_a": words.get((slot, A)), "words_b": words.get((slot, Bm))})
    S = pd.DataFrame(rows)
    S["gap100"] = (S["words_a"] - S["words_b"]) / 100
    res["length"] = {}
    for col in ("like_dd", "dislike_dd"):
        m = smf.ols(f"{col} ~ gap100", S).fit(cov_type="cluster", cov_kwds={"groups": S["round"]}) if S["round"].nunique() > 1 \
            else smf.ols(f"{col} ~ gap100", S).fit()
        ci = m.conf_int()
        res["length"][col] = {"raw_mean": float(S[col].mean()),
                              "at_equal_length": float(m.params["Intercept"]),
                              "at_equal_length_ci95": [float(ci.loc["Intercept", 0]), float(ci.loc["Intercept", 1])],
                              "per_100_words_gap": float(m.params["gap100"]),
                              "per_100_words_gap_ci95": [float(ci.loc["gap100", 0]), float(ci.loc["gap100", 1])],
                              "r2": float(m.rsquared), "slots": len(S)}
    # length taste per AI: post-level upvote rate vs words (per 100), author held fixed, clustered by round
    pl = L.groupby(["round", "post", "judge", "author"])["up"].mean().reset_index()
    pk = posts[posts.ok].assign(post=lambda d: d["seed"].astype(str) + "|" + d["key"])[["post", "words"]]
    pl = pl.merge(pk, on="post")
    pl["w100"] = pl["words"] / 100
    res["length_taste"] = {}
    for j, g in pl.groupby("judge"):
        m = smf.ols("up ~ w100 + C(author)", g).fit(cov_type="cluster", cov_kwds={"groups": g["round"]}) if g["round"].nunique() > 1 \
            else smf.ols("up ~ w100 + C(author)", g).fit()
        res["length_taste"][j] = {"per_100_words": float(m.params["w100"]),
                                  "ci95": [float(m.conf_int().loc["w100", 0]), float(m.conf_int().loc["w100", 1])]}
    res["slots"] = S[["round", "topic", "like_dd", "dislike_dd", "words_a", "words_b"]].round(4).to_dict(orient="records")
    res["by_topic"] = {t: {"like_dd": float(g["like_dd"].mean()), "dislike_dd": float(g["dislike_dd"].mean()),
                           "slots": len(g)} for t, g in S.groupby("topic")}

    # 4. same user, same post, two AIs
    w = L.pivot_table(index=["persona", "post"], columns="judge", values="action", aggfunc="first").dropna()
    res["agreement"] = {"pairs": len(w), "same_choice_%": float((w[A] == w[Bm]).mean() * 100),
                        "kappa": kappa(w[A], w[Bm]),
                        "crosstab": pd.crosstab(w[A], w[Bm]).to_dict()}
    # each AI's like rate by the user's interest in the topic, both AIs
    res["like_by_interest_pct"] = (L.groupby(["judge", "affinity"])["up"].mean().mul(100).round(1)
                                   .unstack().to_dict(orient="index"))

    # 5. leaderboard per crowd per round: share of the top 10 by author
    sc = L.assign(score=L["up"] - L["down"]).groupby(["round", "judge", "post", "author"])["score"].sum().reset_index()
    top = []
    for (rnd, j), g in sc.groupby(["round", "judge"]):
        g = g.sort_values(["score", "post"], ascending=[False, True]).head(10)
        top.append({"round": int(rnd), "crowd": j, **{a: int((g["author"] == a).sum()) for a in (A, Bm)}})
    T = pd.DataFrame(top)
    res["top10"] = {"per_round": top,
                    "mean_own_share": {j: float(T[T.crowd == j][j].mean()) for j in (A, Bm)},
                    "mean_other_share": {j: float(T[T.crowd == j][Bm if j == A else A].mean()) for j in (A, Bm)}}

    # 6. timing, failures, posts
    tim = []
    for m in sorted(glob.glob(os.path.join(analyze_world.WORLDS, PREFIX + "*", "manifest.json"))):
        j = json.load(open(m))
        if "finished_at" not in j:
            continue
        for judge, v in j["judges"].items():
            tim.append({"world": j["label"], "round": j["config"]["seed"] - 200, "judge": judge,
                        "decisions": v["decisions"], "vote_wall_min": round(v["wall_s"] / 60, 2),
                        "s_per_vote": v["s_per_decision"], "post_writing_min": round(j["post_generation_s"] / 60, 2),
                        "started": j["started_at"], "finished": j["finished_at"],
                        "world_wall_min": round((datetime.fromisoformat(j["finished_at"]) -
                                                 datetime.fromisoformat(j["started_at"])).total_seconds() / 60, 2)})
    Tm = pd.DataFrame(tim)
    rt = Tm.groupby("round").agg(start=("started", "min"), end=("finished", "max"))
    rt["round_min"] = [(datetime.fromisoformat(e) - datetime.fromisoformat(s)).total_seconds() / 60
                       for s, e in zip(rt["start"], rt["end"])]
    res["timing"] = {"per_world": tim, "round_min": rt["round_min"].round(1).to_dict(),
                     "s_per_vote": Tm.groupby("judge")["s_per_vote"].median().to_dict(),
                     "post_s": posts[posts.ok].groupby("author")["latency_s"].median().to_dict()}
    ok = posts[posts.ok]
    res["posts"] = {"written": int(len(ok)), "failed": int((~posts.ok).sum()),
                    "unique_bodies": int(ok["body"].nunique()), "duplicate_bodies": int(len(ok) - ok["body"].nunique()),
                    "unique_titles": int(ok["title"].nunique()),
                    "words_mean": ok.groupby("author")["words"].mean().round(1).to_dict(),
                    "words_median": ok.groupby("author")["words"].median().to_dict(),
                    "needed_retry_%": ok.assign(r=ok["attempts"] > 1).groupby("author")["r"].mean().mul(100).round(1).to_dict(),
                    "slots_dropped": int(len(posts.groupby(["seed", "round", "topic"])) - len(S))}

    dpath = os.path.join(OUT, "drift_check.jsonl")
    res["drift"] = [json.loads(l) for l in open(dpath)] if os.path.exists(dpath) else []
    # exports: every vote, every post, the 100 users, timing, slot table
    users = pd.DataFrame(personas.core100())
    uname = users.set_index("id")["username"].to_dict()
    ex = df.assign(username=df["agent_id"].map(uname))[
        ["round", "seed", "label", "judge", "agent_id", "username", "voting_style", "affinity", "topic", "topic_rank",
         "pos_in_topic", "post_key", "author", "self", "action", "reason", "outcome", "attempts", "latency_s",
         "prompt_tokens", "eval_tokens"]].rename(columns={"judge": "played_by", "author": "written_by",
                                                          "agent_id": "user_id", "self": "own_ai_post"})
    ex.to_csv(os.path.join(OUT, "reactions.csv"), index=False)
    posts[["round_n", "seed", "round", "topic", "author", "key", "ok", "brief", "title", "body", "words", "attempts",
           "latency_s", "eval_tokens"]].rename(columns={"round_n": "round", "round": "slot_in_topic"}) \
        .to_csv(os.path.join(OUT, "posts.csv"), index=False)
    users.to_csv(os.path.join(OUT, "users.csv"), index=False)
    Tm.to_csv(os.path.join(OUT, "timing.csv"), index=False)
    S.to_csv(os.path.join(OUT, "slots.csv"), index=False)
    json.dump(res, open(os.path.join(OUT, "analysis.json"), "w"), indent=1, default=str)

    p = lambda x: f"{x * 100:+.1f}"  # noqa: E731
    lb, db = res["round_boot_up"], res["round_boot_down"]
    print(f"rounds {res['rounds']}, {res['valid']}/{res['decisions']} valid votes, {res['posts']['written']} posts "
          f"({res['posts']['duplicate_bodies']} duplicate bodies), {res['posts']['slots_dropped']} slots dropped")
    print(f"OWN-AI LIKE boost {p(lb['est'])} pts" + (f" [{p(lb['ci95'][0])}, {p(lb['ci95'][1])}] rounds-bootstrap, "
          f"{lb['rounds_positive']}/{len(per_round)} rounds positive" if lb["ci95"] else ""))
    print(f"   user x slot bootstrap: {res['sp_up']['_pooled']}")
    print(f"OWN-AI DISLIKE {p(db['est'])} pts" + (f" [{p(db['ci95'][0])}, {p(db['ci95'][1])}]" if db["ci95"] else ""))
    print(f"at equal length: like {p(res['length']['like_dd']['at_equal_length'])}, "
          f"slope per 100 words {p(res['length']['like_dd']['per_100_words_gap'])}")
    print(f"same user same post, two AIs: same choice {res['agreement']['same_choice_%']:.1f}%, "
          f"kappa {res['agreement']['kappa']:.2f}")
    print("like rate (rows played by, cols written by):\n" + (pd.DataFrame(res["rate_up"]) * 100).round(1).to_string())
    print("length taste (upvote change per +100 words):", {k: round(v["per_100_words"] * 100, 1) for k, v in res["length_taste"].items()})
    print("top-10 own share:", res["top10"]["mean_own_share"], "round minutes:", res["timing"]["round_min"])


if __name__ == "__main__":
    main(B=int(sys.argv[1]) if len(sys.argv) > 1 else 2000)
