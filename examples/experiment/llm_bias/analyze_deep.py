"""LD-18 deep results: every breakdown behind the results page (run after analyze_two_ai.py).

IN PLAIN WORDS
--------------
analyze_two_ai.py gives the headline. This digs into WHO, WHERE and WHY:
  * the own-AI boost (double difference) inside every subgroup -- subreddit, the user's interest, the user's voting
    habit, how far down the scroll the post sat, first vs second half of the rounds -- each with a 95 % interval from
    the same two-way user x slot bootstrap as the headline (1,000 draws);
  * leave-one-round-out and leave-one-subreddit-out (does any single piece drive the answer?);
  * every one of the 100 users' own boost (is it a few users or most of them?);
  * what the two AIs' posts look like (length, sentences, questions, "I", formatting...) and what each crowd
    rewards; then how much of the own-AI boost those visible features explain;
  * the words each crowd uses when it explains a vote, and which words it uses more for its own AI's posts;
  * the most loved, most hated and most disputed posts; agreement between the AIs; "nothing" choices; timing;
  * per-post and per-user data for the page's browsers.

    python analyze_deep.py        # writes data/llm_bias/two_ai/deep.json and the page data files
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from collections import Counter

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors  # noqa: E402

D = os.path.join(authors.DATA, "two_ai")
A, B = "gemma4:e2b", "gemma3:1b"
CELLS = [(A, A), (A, B), (B, A), (B, B)]  # (played_by, written_by)
STOP = set("""a an the and or but if of to in on for with at by from as is are was were be been it its this that these
those i me my we our you your he she they them his her their not no so too very just also than then there here what
which who how why when about into out up down over more most some any all can could would should will do does did
have has had i'm it's don't im dont post posts like really seems seem one get got much make makes""".split())


def dd(df, col):
    r = df.groupby(["played_by", "written_by"])[col].mean()
    try:
        return float((r[(A, A)] - r[(A, B)]) - (r[(B, A)] - r[(B, B)]))
    except KeyError:
        return float("nan")


class Boot:
    """Two-way (user x slot) cluster bootstrap of the double difference, vectorised: one weight per user and per slot,
    multiplied, then the four cell rates come from weighted sums. Same scheme as analyze.cluster_bootstrap."""

    def __init__(self, df, B=1000, seed=0):
        self.df = df.reset_index(drop=True)
        rng = np.random.default_rng(seed)
        users, slots = self.df["user_id"].unique(), self.df["slot"].unique()
        self.ui = pd.Categorical(self.df["user_id"], categories=users).codes
        self.si = pd.Categorical(self.df["slot"], categories=slots).codes
        self.cell = np.select([(self.df.played_by == j) & (self.df.written_by == a) for j, a in CELLS], range(4), -1)
        self.WU = rng.multinomial(len(users), np.ones(len(users)) / len(users), size=B)
        self.WS = rng.multinomial(len(slots), np.ones(len(slots)) / len(slots), size=B)

    def ci(self, col, mask=None):
        y = self.df[col].to_numpy(float)
        m = np.ones(len(y), bool) if mask is None else np.asarray(mask)
        cell, ui, si, y = self.cell[m], self.ui[m], self.si[m], y[m]
        draws = []
        for wu, ws in zip(self.WU, self.WS):
            w = wu[ui] * ws[si]
            num = np.bincount(cell, w * y, 4)
            den = np.bincount(cell, w, 4)
            if (den == 0).any():
                continue
            r = num / den
            draws.append((r[0] - r[1]) - (r[2] - r[3]))
        d = np.array(draws)
        p = float(min(1, 2 * min((d <= 0).mean(), (d >= 0).mean())))
        return [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))], p


def pct(x):
    return round(float(x) * 100, 4)  # kept precise: the page subtracts these, so rounding happens only at display


def features(title, body):
    words = re.findall(r"[A-Za-z']+", body)
    n = max(1, len(words))
    sents = [s for s in re.split(r"[.!?]+(?:\s|$)", body) if s.strip()]
    lw = [w.lower() for w in words]
    return {
        "words": len(words),
        "sentences": len(sents),
        "words_per_sentence": len(words) / max(1, len(sents)),
        "paragraphs": len([p for p in re.split(r"\n\s*\n", body) if p.strip()]),
        "exclamations_per_100w": 100 * body.count("!") / n,
        "questions_per_100w": 100 * body.count("?") / n,
        "first_person_per_100w": 100 * sum(w in ("i", "i'm", "i've", "i'd", "i'll", "my", "me", "mine") for w in lw) / n,
        "you_per_100w": 100 * sum(w in ("you", "your", "you're", "you've") for w in lw) / n,
        "uses_markdown": int(bool(re.search(r"\*\*|\*[^*\s][^*]*\*|^#+ |^\s*[-*] ", body, re.M))),
        "list_lines": len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", body)),
        "title_words": len(title.split()),
        "title_is_question": int(title.strip().endswith("?")),
        "opens_casually": int(bool(re.match(r"\s*(okay|ok|so|hey|alright|well|honestly|seriously)\b", body, re.I))),
        "long_words_share": sum(len(w) >= 8 for w in words) / n,
    }


FEATURE_LABELS = {
    "words": "words in the post", "sentences": "sentences", "words_per_sentence": "words per sentence",
    "paragraphs": "paragraphs", "exclamations_per_100w": "exclamation marks per 100 words",
    "questions_per_100w": "question marks per 100 words", "first_person_per_100w": "I / me / my per 100 words",
    "you_per_100w": "you / your per 100 words", "uses_markdown": "uses bold, headings or bullet formatting",
    "list_lines": "list lines", "title_words": "words in the title", "title_is_question": "title is a question",
    "opens_casually": "opens with okay / so / hey / honestly", "long_words_share": "share of long words (8+ letters)",
}


def main(nboot=1000):
    R = pd.read_csv(os.path.join(D, "reactions.csv"))
    P = pd.read_csv(os.path.join(D, "posts.csv"))
    U = pd.read_csv(os.path.join(D, "users.csv"))
    base = json.load(open(os.path.join(D, "analysis.json")))
    ok = R[R.outcome == "chose"].copy()
    ok["up"] = (ok.action == "like").astype(int)
    ok["down"] = (ok.action == "dislike").astype(int)
    ok["none"] = (ok.action == "nothing").astype(int)
    ok["post"] = ok.seed.astype(str) + "|" + ok.post_key
    ok["slot_in_topic"] = ok.post_key.str.split("|").str[0].str[1:].astype(int)
    ok["slot"] = ok.seed.astype(str) + "|" + ok.slot_in_topic.astype(str) + "|" + ok.topic
    P = P[P.ok].copy()
    P["post"] = P.seed.astype(str) + "|" + P.key
    P = P[P.post.isin(set(ok.post))]  # drop the partners of the 6 failed posts (never shown)
    out = {"n_votes": int(len(R)), "n_valid": int(len(ok)), "n_posts": int(P.post.nunique()),
           "n_slots": int(ok.slot.nunique()), "n_users": int(ok.user_id.nunique()),
           "rounds": sorted(int(x) for x in ok["round"].unique())}
    boot = Boot(ok, nboot)

    def block(mask, label):
        sub = ok[mask]
        res = {"label": label, "n": int(len(sub))}
        for col in ("up", "down"):
            ci, p = boot.ci(col, mask)
            res[col] = {"est": pct(dd(sub, col)), "ci": [pct(ci[0]), pct(ci[1])], "p": p}
        rates = sub.groupby(["played_by", "written_by"])[["up", "down", "none"]].mean()
        res["rates"] = {f"{j.split(':')[0]}|{a.split(':')[0]}": {c: pct(rates.loc[(j, a), c]) for c in ("up", "down", "none")}
                        for j, a in CELLS if (j, a) in rates.index}
        return res

    out["overall"] = block(np.ones(len(ok), bool), "all")
    out["by_topic"] = [block((ok.topic == t).to_numpy(), t) for t in sorted(ok.topic.unique())]
    out["by_interest"] = [block((ok.affinity == a).to_numpy(), int(a)) for a in sorted(ok.affinity.unique())]
    out["by_voting"] = [block((ok.voting_style == v).to_numpy(), v) for v in ("generous", "typical", "harsh")]
    out["by_scroll_rank"] = [block((ok.topic_rank == k).to_numpy(), int(k)) for k in sorted(ok.topic_rank.unique())]
    out["by_half"] = [block((ok["round"] <= 7).to_numpy(), "rounds 1-7"), block((ok["round"] >= 8).to_numpy(), "rounds 8-15")]
    out["leave_one_round_out"] = [{"left_out": int(r), "up": pct(dd(ok[ok["round"] != r], "up")),
                                   "down": pct(dd(ok[ok["round"] != r], "down"))} for r in out["rounds"]]
    out["leave_one_topic_out"] = [{"left_out": t, "up": pct(dd(ok[ok.topic != t], "up")),
                                   "down": pct(dd(ok[ok.topic != t], "down"))} for t in sorted(ok.topic.unique())]

    # every user's own boost
    users = []
    for u, g in ok.groupby("user_id"):
        users.append({"user_id": int(u), "up": pct(dd(g, "up")), "down": pct(dd(g, "down")),
                      "agree": pct((g.pivot_table(index="post", columns="played_by", values="action", aggfunc="first")
                                    .dropna().pipe(lambda w: (w[A] == w[B]).mean())))})
    Uu = pd.DataFrame(users)
    out["per_user"] = {"up_positive": int((Uu.up > 0).sum()), "up_negative": int((Uu.up < 0).sum()),
                       "up_zero": int((Uu.up == 0).sum()), "up_mean": round(Uu.up.mean(), 2),
                       "up_median": round(Uu.up.median(), 2), "up_sd": round(Uu.up.std(), 2),
                       "down_negative": int((Uu.down < 0).sum()), "down_positive": int((Uu.down > 0).sum()),
                       "hist_up": np.histogram(Uu.up, bins=np.arange(-30, 32.5, 2.5))[0].tolist(),
                       "hist_edges": np.arange(-30, 32.5, 2.5).tolist(),
                       "values": Uu[["user_id", "up", "down", "agree"]].to_dict(orient="records")}
    # sign test: if no own-AI effect, a user's boost is as likely below 0 as above
    from math import comb
    n_pos, n_neg = out["per_user"]["up_positive"], out["per_user"]["up_negative"]
    n = n_pos + n_neg
    out["per_user"]["sign_test_p"] = float(min(1, 2 * sum(comb(n, k) for k in range(max(n_pos, n_neg), n + 1)) / 2 ** n))

    # scroll position
    out["by_position"] = {"rank": {j: ok[ok.played_by == j].groupby("topic_rank").up.mean().mul(100).round(1).to_dict() for j in (A, B)},
                          "pos": {j: ok[ok.played_by == j].groupby("pos_in_topic").up.mean().mul(100).round(1).to_dict() for j in (A, B)}}

    # "nothing" and interest
    out["nothing_by_interest"] = {j: ok[ok.played_by == j].groupby("affinity").none.mean().mul(100).round(1).to_dict() for j in (A, B)}
    out["down_by_interest"] = {j: ok[ok.played_by == j].groupby("affinity").down.mean().mul(100).round(1).to_dict() for j in (A, B)}
    out["up_by_interest"] = {j: ok[ok.played_by == j].groupby("affinity").up.mean().mul(100).round(1).to_dict() for j in (A, B)}

    # agreement
    w = ok.pivot_table(index=["user_id", "post"], columns="played_by", values="action", aggfunc="first").dropna()
    out["agreement"] = {"pairs": int(len(w)), "same_pct": pct((w[A] == w[B]).mean()),
                        "kappa": base["agreement"]["kappa"],
                        "crosstab": {a: {b: int(((w[A] == a) & (w[B] == b)).sum()) for b in ("like", "dislike", "nothing")}
                                     for a in ("like", "dislike", "nothing")}}
    tw = w.reset_index().merge(ok[["post", "topic"]].drop_duplicates(), on="post")
    out["agreement"]["by_topic"] = {t: pct((g[A] == g[B]).mean()) for t, g in tw.groupby("topic")}
    out["agreement"]["per_user_hist"] = np.histogram(Uu.agree, bins=np.arange(40, 101, 5))[0].tolist()

    # post features, what each crowd rewards, and how much of the boost they explain
    F = pd.DataFrame([{"post": r.post, "author": r.author, "round": r.round, **features(r.title, r.body)} for r in P.itertuples()])
    out["features_by_author"] = {f: {a.split(":")[0]: round(float(F[F.author == a][f].mean()), 2) for a in (A, B)} for f in FEATURE_LABELS}
    out["feature_labels"] = FEATURE_LABELS
    out["words_hist"] = {a.split(":")[0]: np.histogram(F[F.author == a].words, bins=np.arange(0, 525, 25))[0].tolist() for a in (A, B)}
    out["words_hist_edges"] = np.arange(0, 525, 25).tolist()
    pr = ok.groupby(["post", "played_by"]).agg(up=("up", "mean"), down=("down", "mean")).reset_index()
    pr = pr.merge(F, on="post")
    feats = list(FEATURE_LABELS)
    Z = (pr[feats] - F[feats].mean()) / F[feats].std().replace(0, 1)
    import statsmodels.api as sm
    rewards, resid_parts = {}, []
    for j in (A, B):
        m = (pr.played_by == j).to_numpy()
        X = sm.add_constant(pd.concat([Z[m], pd.get_dummies(pr.loc[m, "round"], prefix="r", drop_first=True, dtype=float)], axis=1))
        fit = sm.OLS(pr.loc[m, "up"], X).fit(cov_type="cluster", cov_kwds={"groups": pr.loc[m, "round"]})
        ci = fit.conf_int()
        rewards[j.split(":")[0]] = {f: {"coef": pct(fit.params[f]), "lo": pct(ci.loc[f, 0]), "hi": pct(ci.loc[f, 1])} for f in feats}
        rewards[j.split(":")[0]]["_r2"] = round(float(fit.rsquared), 3)
        part = pr.loc[m, ["post", "played_by", "author", "up"]].copy()
        part["pred"] = fit.fittedvalues
        resid_parts.append(part)
    out["what_each_crowd_rewards"] = rewards
    RP = pd.concat(resid_parts)
    RP["resid"] = RP.up - RP.pred

    def cell_dd(df, col):
        r = df.groupby(["played_by", "author"])[col].mean()
        return float((r[(A, A)] - r[(A, B)]) - (r[(B, A)] - r[(B, B)]))
    raw_post = cell_dd(RP, "up")
    explained = cell_dd(RP, "pred")
    left = cell_dd(RP, "resid")
    out["style_explains"] = {"post_level_dd": pct(raw_post), "explained_by_features": pct(explained),
                             "left_after_features": pct(left), "share_explained": round(explained / raw_post, 3)}

    # words in the reasons
    def toks(s):
        return [t for t in re.findall(r"[a-z']+", str(s).lower()) if t not in STOP and len(t) > 2]
    reasons = {}
    for j in (A, B):
        g = ok[ok.played_by == j]
        reasons[j.split(":")[0]] = {
            "mean_words": round(float(g.reason.fillna("").str.split().str.len().mean()), 1),
            **{act: [w for w, _ in Counter(t for s in g[g.action == act].reason for t in toks(s)).most_common(15)]
               for act in ("like", "dislike", "nothing")}}
        # words over-used in like-reasons for OWN posts vs like-reasons for the OTHER AI's posts (smoothed log ratio)
        own = Counter(t for s in g[(g.action == "like") & (g.written_by == j)].reason for t in toks(s))
        oth = Counter(t for s in g[(g.action == "like") & (g.written_by != j)].reason for t in toks(s))
        no, nt = sum(own.values()), sum(oth.values())
        lr = {t: np.log(((own[t] + 1) / (no + 1)) / ((oth[t] + 1) / (nt + 1))) for t in set(own) | set(oth) if own[t] + oth[t] >= 40}
        reasons[j.split(":")[0]]["own_vs_other_like_words"] = [[t, round(float(v), 2), own[t], oth[t]] for t, v in sorted(lr.items(), key=lambda x: -x[1])[:12]]
        reasons[j.split(":")[0]]["other_vs_own_like_words"] = [[t, round(float(-v), 2), own[t], oth[t]] for t, v in sorted(lr.items(), key=lambda x: x[1])[:12]]
    out["reasons"] = reasons

    # posts: scores per crowd, loved / hated / disputed, sample reasons
    sc = ok.groupby(["post", "played_by"]).agg(up=("up", "sum"), down=("down", "sum"), none=("none", "sum")).reset_index()
    piv = sc.pivot(index="post", columns="played_by", values=["up", "down", "none"])
    rng = np.random.default_rng(1)
    plist = []
    for r in P.sort_values(["round", "topic", "slot_in_topic", "author"]).itertuples():
        e = {"id": r.post, "r": int(r.round), "t": r.topic, "s": int(r.slot_in_topic), "a": r.author.split(":")[0],
             "ti": r.title, "b": r.body, "w": int(r.words), "br": ast.literal_eval(r.brief), "v": {}, "rs": {}}
        for j in (A, B):
            if (("up", j) in piv.columns) and r.post in piv.index:
                e["v"][j.split(":")[0]] = [int(piv.loc[r.post, ("up", j)]), int(piv.loc[r.post, ("down", j)]), int(piv.loc[r.post, ("none", j)])]
            g = ok[(ok.post == r.post) & (ok.played_by == j)]
            picks = []
            for act in ("like", "dislike", "nothing"):
                gg = g[g.action == act]
                if len(gg):
                    row = gg.iloc[int(rng.integers(len(gg)))]
                    picks.append([act[0], int(row.user_id), str(row.reason)[:220]])
            e["rs"][j.split(":")[0]] = picks
        plist.append(e)
    PL = pd.DataFrame([{"id": e["id"], "a": e["a"], "t": e["t"], "r": e["r"], "ti": e["ti"],
                        "g4": (e["v"]["gemma4"][0] - e["v"]["gemma4"][1]) if "gemma4" in e["v"] else None,
                        "g3": (e["v"]["gemma3"][0] - e["v"]["gemma3"][1]) if "gemma3" in e["v"] else None} for e in plist]).dropna()
    PL["gap"] = PL.g4 - PL.g3
    out["posts_loved"] = {"gemma4": PL.nlargest(8, "g4").to_dict(orient="records"), "gemma3": PL.nlargest(8, "g3").to_dict(orient="records")}
    out["posts_hated"] = {"gemma4": PL.nsmallest(8, "g4").to_dict(orient="records"), "gemma3": PL.nsmallest(8, "g3").to_dict(orient="records")}
    out["posts_disputed"] = {"gemma4_more": PL.nlargest(8, "gap").to_dict(orient="records"),
                             "gemma3_more": PL.nsmallest(8, "gap").to_dict(orient="records")}
    out["net_score_corr_between_crowds"] = round(float(np.corrcoef(PL.g4, PL.g3)[0, 1]), 3)

    # timing
    out["latency"] = {j.split(":")[0]: {q: round(float(R[R.played_by == j].latency_s.quantile(q / 100)), 2) for q in (5, 25, 50, 75, 95, 99)} for j in (A, B)}
    out["post_seconds"] = {a.split(":")[0]: {q: round(float(P[P.author == a].latency_s.quantile(q / 100)), 2) for q in (5, 50, 95)} for a in (A, B)}
    out["post_attempts"] = {a.split(":")[0]: P[P.author == a].attempts.value_counts().sort_index().to_dict() for a in (A, B)}

    # the 100 users
    aff = U.topic_affinity.apply(ast.literal_eval)
    TOP = ["personal_finance", "cars", "farming", "cooking", "tech"]
    out["users"] = {"age_hist": np.histogram(U.age, bins=range(15, 85, 5))[0].tolist(), "age_edges": list(range(15, 85, 5)),
                    "gender": U.gender.value_counts().to_dict(), "voting": U.voting.value_counts().to_dict(),
                    "interest": {t: aff.apply(lambda d: d[t]).value_counts().sort_index().to_dict() for t in TOP},
                    "professions": U.profession.value_counts().head(12).to_dict(),
                    "countries": U.country.value_counts().to_dict()}
    # per-user browser: profile, both crowds' action strings over every post (post order = plist order)
    order = {e["id"]: i for i, e in enumerate(plist)}
    code = {"like": "u", "dislike": "d", "nothing": "n"}
    ub = []
    for u in U.itertuples():
        g = ok[ok.user_id == u.id]
        acts = {}
        for j in (A, B):
            s = ["."] * len(plist)
            for row in g[g.played_by == j][["post", "action"]].itertuples():
                if row.post in order:
                    s[order[row.post]] = code[row.action]
            acts[j.split(":")[0]] = "".join(s)
        rec = next(x for x in users if x["user_id"] == u.id)
        ub.append({"id": int(u.id), "name": u.realname, "user": u.username, "age": int(u.age), "gender": u.gender,
                   "place": u.place, "job": u.profession, "voting": u.voting, "aff": {t: aff[u.Index][t] for t in TOP},
                   "persona": u.persona, "boost_up": rec["up"], "boost_down": rec["down"], "agree": rec["agree"], "acts": acts})

    json.dump(out, open(os.path.join(D, "deep.json"), "w"), indent=1, default=str)
    json.dump(plist, open(os.path.join(D, "deep_posts.json"), "w"), separators=(",", ":"))
    json.dump(ub, open(os.path.join(D, "deep_users.json"), "w"), separators=(",", ":"))
    return out, plist, ub


if __name__ == "__main__":
    out, plist, ub = main()
    o = out["overall"]
    print("overall up", o["up"], "down", o["down"])
    for k in ("by_topic", "by_interest", "by_voting", "by_scroll_rank", "by_half"):
        print(k, [(x["label"], x["up"]["est"], x["up"]["ci"]) for x in out[k]])
    print("LORO up range", min(x["up"] for x in out["leave_one_round_out"]), max(x["up"] for x in out["leave_one_round_out"]))
    print("per user", {k: v for k, v in out["per_user"].items() if k not in ("values", "hist_up", "hist_edges")})
    print("style explains", out["style_explains"])
    print("features", {k: v for k, v in out["features_by_author"].items()})
    print("rewards g4", {k: v["coef"] for k, v in out["what_each_crowd_rewards"]["gemma4"].items() if k != "_r2"})
    print("rewards g3", {k: v["coef"] for k, v in out["what_each_crowd_rewards"]["gemma3"].items() if k != "_r2"})
    print("reasons", json.dumps(out["reasons"])[:1500])
    print("corr crowds", out["net_score_corr_between_crowds"], "agree by topic", out["agreement"]["by_topic"])
    print("posts", len(plist), "users", len(ub))
