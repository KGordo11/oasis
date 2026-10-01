"""Build the LD-18 results page (paper-style) from analyze_two_ai.py's output.

    python make_two_ai_page.py <out_dir>     # writes <out_dir>/two_ai.html and <out_dir>/two_ai_posts.js

two_ai_posts.js holds every post with its full text and both crowds' vote counts (for the post browser);
it is published next to the page.
"""

import ast
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors  # noqa: E402
from topics import TOPICS  # noqa: E402

D = os.path.join(authors.DATA, "two_ai")
GH = "https://github.com/KGordo11/oasis/blob/llm-bias/"


def main(out):
    os.makedirs(out, exist_ok=True)
    res = json.load(open(os.path.join(D, "analysis.json")))
    R = pd.read_csv(os.path.join(D, "reactions.csv"))
    P = pd.read_csv(os.path.join(D, "posts.csv"))
    P = P[P["ok"]]
    c = R[R.outcome == "chose"].groupby(["seed", "post_key", "played_by", "action"]).size().unstack(fill_value=0)
    posts = []
    for p in P.itertuples():
        row = {"r": int(p.round), "t": p.topic, "a": p.author, "s": int(p.slot_in_topic), "ti": p.title, "b": p.body,
               "w": int(p.words), "br": ast.literal_eval(p.brief), "v": {}}
        for j in (res["ai_a"], res["ai_b"]):
            k = (p.seed, p.key, j)
            if k in c.index:
                x = c.loc[k]
                row["v"][j] = [int(x.get("like", 0)), int(x.get("dislike", 0)), int(x.get("nothing", 0))]
        if row["v"]:
            posts.append(row)
    with open(os.path.join(out, "two_ai_posts.js"), "w") as f:
        f.write("window.POSTS=" + json.dumps(posts, separators=(",", ":")) + ";")
    topics = {t: TOPICS[t]["sub"] for t in sorted({p["t"] for p in posts})}
    html = open(os.path.join(HERE, "two_ai_page_template.html")).read()
    html = html.replace("/*RES*/null", json.dumps(res, default=str)).replace("/*TOPICS*/null", json.dumps(topics))
    html = html.replace("{GH}", GH)
    open(os.path.join(out, "two_ai.html"), "w").write(html)
    print(f"wrote {out}/two_ai.html ({len(html) // 1024} KB) and two_ai_posts.js ({len(posts)} posts)")


if __name__ == "__main__":
    main(sys.argv[1])
