"""Build the LD-18 results page ('The Two-AI Feed') from analyze_two_ai.py and analyze_deep.py output.

    python make_two_ai_page.py <out_dir> [inside_url]
        writes <out_dir>/two_ai.html, posts_data.js (every post, both crowds' votes, sample reasons)
        and users_data.js (every user, every vote); the two .js files are published next to the page.

Run analyze_two_ai.py and analyze_deep.py first.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors  # noqa: E402
from topics import PRIMARY, TOPICS  # noqa: E402

D = os.path.join(authors.DATA, "two_ai")
GH = "https://github.com/KGordo11/oasis/blob/llm-bias/"


def main(out, inside_url="#"):
    os.makedirs(out, exist_ok=True)
    res = json.load(open(os.path.join(D, "analysis.json")))
    deep = json.load(open(os.path.join(D, "deep.json")))
    posts = json.load(open(os.path.join(D, "deep_posts.json")))
    users = json.load(open(os.path.join(D, "deep_users.json")))
    with open(os.path.join(out, "posts_data.js"), "w") as f:
        f.write("window.POSTS=" + json.dumps(posts, separators=(",", ":")) + ";")
    with open(os.path.join(out, "users_data.js"), "w") as f:
        f.write("window.USERS=" + json.dumps(users, separators=(",", ":")) + ";")
    topics = {t: TOPICS[t]["sub"] for t in PRIMARY}
    html = open(os.path.join(HERE, "results_template.html")).read()
    html = (html.replace("/*RES*/null", json.dumps(res, default=str)).replace("/*DEEP*/null", json.dumps(deep, default=str))
            .replace("/*TOPICS*/null", json.dumps(topics)).replace("{GH}", GH).replace("{INSIDE}", inside_url))
    open(os.path.join(out, "two_ai.html"), "w").write(html)
    print(f"wrote {out}/two_ai.html ({len(html) // 1024} KB), posts_data.js ({len(posts)} posts), users_data.js ({len(users)} users)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "#")
