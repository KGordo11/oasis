"""Person vs AI: where does the variation in reactions come from? (LD-16 item 5; existing data only.)

IN PLAIN WORDS
--------------
In the three-AI test every person meets every post once with EACH AI. That lets us split the ups and downs in
"did they click like?" into pieces, exactly like splitting a pie:
  AI              some AIs like more than others (mistral likes ~95 % of everything)
  person          some people like more than others, whoever plays them (e.g. "easy to please")
  post            some posts are liked more by everyone
  person x post   this person, this post: mostly whether the post's topic is one the description says they like
  AI x person     the same person played differently by different AIs
  AI x post       the same post treated differently by different AIs (self-preference lives here)
  leftover        everything else, including plain dice-rolling
The retest (same AI, same person, same post, new dice) tells us how much of "leftover" is just dice.

The design is fully crossed (AI x person x post, one reaction each), so the classic sums of squares split
exactly. Reported as a share of the total variance.

    python variance.py --prefix v3_ --out data/llm_bias/variance_v3.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze_world  # noqa: E402

WORLDS = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..", "..")), "data", "llm_bias", "worlds")


def decompose(d, y="up"):
    """Exact three-way ANOVA sums of squares for a balanced AI x person x post table (one reaction per cell)."""
    g = d[y].mean()
    tot = ((d[y] - g) ** 2).sum()
    m = {k: d.groupby(k)[y].transform("mean") for k in ("judge", "persona", "post")}
    m2 = {k: d.groupby(list(k))[y].transform("mean") for k in (("judge", "persona"), ("judge", "post"), ("persona", "post"))}
    ss = {
        "AI": ((m["judge"] - g) ** 2).sum(),
        "person": ((m["persona"] - g) ** 2).sum(),
        "post": ((m["post"] - g) ** 2).sum(),
        "AI x person": ((m2[("judge", "persona")] - m["judge"] - m["persona"] + g) ** 2).sum(),
        "AI x post": ((m2[("judge", "post")] - m["judge"] - m["post"] + g) ** 2).sum(),
        "person x post": ((m2[("persona", "post")] - m["persona"] - m["post"] + g) ** 2).sum(),
    }
    ss["leftover"] = tot - sum(ss.values())
    return {k: round(100 * v / tot, 1) for k, v in ss.items()}, float(tot / len(d))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="v3_")
    ap.add_argument("--retest", default="rt3_s40_w0,rt3_s40_w1,rt3_s40_w2")
    ap.add_argument("--orig", default="v3_s40_w0,v3_s40_w1,v3_s40_w2")
    ap.add_argument("--out")
    a = ap.parse_args()
    L = analyze_world.to_long(analyze_world.load(prefix=a.prefix))
    # keep only complete person x post cells (all AIs answered), so the table is balanced
    n_j = L["judge"].nunique()
    full = L.groupby(["persona", "post"])["judge"].transform("nunique") == n_j
    D = L[full]
    res = {"post_sets": sorted(int(x) for x in D["seed"].unique()), "reactions": len(D),
           "people": int(D["persona"].nunique()), "posts": int(D["post"].nunique()), "AIs": sorted(D["judge"].unique())}
    res["like_share_%"], var_up = decompose(D, "up")
    res["dislike_share_%"], _ = decompose(D, "down")
    # dice: same AI, same person, same post, new draw -> within-cell variance = mean((y1-y2)^2)/2
    def load(labels):
        return pd.DataFrame([json.loads(x) for l in labels.split(",")
                             for x in open(os.path.join(WORLDS, l, "decisions.jsonl")) if x.strip()])
    O, T = load(a.orig), load(a.retest)
    O, T = O[O["outcome"] == "chose"], T[T["outcome"] == "chose"]
    m = O.merge(T, on=["agent_id", "post_key", "judge"], suffixes=("_1", "_2"))
    dice = float((((m["action_1"] == "like").astype(int) - (m["action_2"] == "like").astype(int)) ** 2).mean() / 2)
    res["dice_share_of_like_variance_%"] = round(100 * dice / var_up, 1)
    res["retest_pairs"] = len(m)
    # the persona description's part: person + person x post; the AI's part: AI + AI x person + AI x post
    s = res["like_share_%"]
    res["summary_like_%"] = {"from the person's description (person + person x post)": round(s["person"] + s["person x post"], 1),
                             "from which AI plays them (AI + AI x person + AI x post)": round(s["AI"] + s["AI x person"] + s["AI x post"], 1),
                             "from the post itself": s["post"],
                             "dice (from the retest)": res["dice_share_of_like_variance_%"],
                             "other leftover": round(s["leftover"] - res["dice_share_of_like_variance_%"], 1)}
    print(json.dumps(res, indent=1))
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
