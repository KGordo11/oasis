"""What is the "taste"? (LD-16 item 2; exploratory, existing data only.)

IN PLAIN WORDS
--------------
Each AI likes its own AI's posts more (LF-41), but can't tell which post is its own (LF-42), so it must like
something about how its own posts are written. This measures simple, checkable features of every post
(length, paragraphs, questions, exclamations, "I/my" words, numbers, formatting, sentence length, happy/sad
words), then asks three things:
  1. Fingerprint: does each AI write with its own style? (average of each feature by author)
  2. Taste: which features make each AI's people click like? (one regression per AI, same person held fixed)
  3. Explanation: if we let each AI have its own taste for every feature, how much of the own-post boost is left?

    python taste.py --prefix v3_ --out data/llm_bias/taste_v3.json
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
import analyze_world  # noqa: E402

DATA = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..", "..")), "data", "llm_bias")
POS = set("great good love happy glad thanks thank awesome amazing excited proud grateful helpful best nice "
          "wonderful fantastic appreciate enjoy relief finally success".split())
NEG = set("bad hate frustrated frustrating angry sad worst terrible annoying annoyed stressed stress worried "
          "worry problem struggle struggling disappointed awful tired scared confused broke".split())


def features(title, body):
    words = re.findall(r"[A-Za-z']+", body.lower())
    n = max(1, len(words))
    sents = [s for s in re.split(r"[.!?]+", body) if s.strip()]
    return {
        "words": len(body.split()),
        "paragraphs": len([p for p in re.split(r"\n\s*\n", body) if p.strip()]),
        "questions": body.count("?"),
        "title_is_question": int(title.strip().endswith("?")),
        "exclamations": body.count("!"),
        "first_person_per_100": 100 * sum(w in ("i", "i'm", "i've", "my", "me", "mine") for w in words) / n,
        "numbers": len(re.findall(r"\d[\d,.]*", body)),
        "formatting": int(bool(re.search(r"(^|\n)\s*([-*•]|\d+[.)])\s|\*\*|#", body))),
        "words_per_sentence": len(body.split()) / max(1, len(sents)),
        "happy_words_per_100": 100 * sum(w in POS for w in words) / n,
        "sad_words_per_100": 100 * sum(w in NEG for w in words) / n,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="v3_")
    ap.add_argument("--out")
    a = ap.parse_args()
    import statsmodels.formula.api as smf
    L = analyze_world.to_long(analyze_world.load(prefix=a.prefix))
    bank = {}
    for s in L["seed"].unique():
        for line in open(os.path.join(DATA, f"postbank_s{s}.jsonl")):
            r = json.loads(line)
            if r.get("ok"):
                bank[f"{s}|{r['key']}"] = features(r["title"], r["body"]) | {"author": r["author"]}
    F = pd.DataFrame.from_dict(bank, orient="index")
    feats = [c for c in F.columns if c != "author"]
    res = {"post_sets": sorted(int(x) for x in L["seed"].unique()), "posts": len(F),
           "fingerprint": F.groupby("author")[feats].mean().round(2).to_dict("index")}
    # standardise features over posts, attach to reactions
    Z = (F[feats] - F[feats].mean()) / F[feats].std().replace(0, 1)
    L = L.join(Z, on="post")
    L["pj"] = L["persona"].astype(str) + "|" + L["judge"]
    judges = sorted(L["judge"].unique())
    # 2. each AI's taste: like ~ features + person FE (within that AI's people), clustered by brief
    taste = {}
    for j in judges:
        g = L[L["judge"] == j]
        m = smf.ols("up ~ " + " + ".join(feats) + " + C(persona) + C(topic)", data=g).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(g["slot"])[0]})
        taste[j] = {f: {"pts_per_sd": round(100 * m.params[f], 2),
                        "ci95": [round(100 * x, 2) for x in m.conf_int().loc[f]]} for f in feats}
    res["taste"] = taste
    # does each AI reward what its own posts have more of? correlation of taste with (own fingerprint - others)
    fp = F.groupby("author")[feats].mean()
    zfp = (fp - F[feats].mean()) / F[feats].std().replace(0, 1)
    match = {}
    for j in judges:
        own_minus_others = zfp.loc[j] - zfp.drop(j).mean()
        t = pd.Series({f: taste[j][f]["pts_per_sd"] for f in feats})
        match[j] = round(float(np.corrcoef(own_minus_others, t)[0, 1]), 2)
    res["taste_matches_own_style_r"] = match
    # 3. how much of the own-post boost do judge-specific feature tastes explain?
    ref = judges[0]
    inter = []
    for j in judges[1:]:
        for f in feats:
            col = f"x_{j.split(':')[0].replace('.', '')}_{f}"
            L[col] = (L["judge"] == j) * L[f]
            inter.append(col)
    base = smf.ols("up ~ self + C(post) + C(pj)", data=L).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(L["slot"])[0]})
    full = smf.ols("up ~ self + " + " + ".join(inter) + " + C(post) + C(pj)", data=L).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(L["slot"])[0]})
    res["own_post_term"] = {"before": [round(100 * base.params["self"], 2), [round(100 * x, 2) for x in base.conf_int().loc["self"]]],
                            "after_all_feature_tastes": [round(100 * full.params["self"], 2),
                                                         [round(100 * x, 2) for x in full.conf_int().loc["self"]]],
                            "reference_judge": ref}
    res["own_post_term"]["share_explained_%"] = round(100 * (1 - full.params["self"] / base.params["self"]), 1)
    print(json.dumps(res, indent=1))
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
