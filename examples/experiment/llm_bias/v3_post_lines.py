"""What did posting lines 2a / 2b / 2c change in the posts themselves? (log 14.45). Read-only, stdlib only.

    python3 examples/experiment/llm_bias/v3_post_lines.py

Per AI and test (v1 = same users and seeds, no line): posts, median body words, title words, % question titles,
% of posts / of posters' reasons that talk about the site itself ("new Reddit", "kick things off", "first post" ...),
the subreddit split, and how often a user who posted in v1 picked the same subreddit again.
"""
import json, os, re, statistics as st
from collections import Counter

V3 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data", "llm_bias", "v3_tests")
M = {"gemma3-12b": "gemma", "llama3.1-8b": "llama", "qwen3-8b": "qwen"}
T = ["v1", "p_2a", "p_2b", "p_2c"]
TOP = ["politics", "technology", "business", "sports", "entertainment"]
SITE = re.compile(r"new reddit|brand[- ]new (reddit|sub|feed|platform|site|community)|this (new )?reddit\b|reddit thing|"
                  r"first (post|feed|thread|posts)\b|kick (things|it|this|the feed|this feed) off|start(ing)? (fresh|from scratch)|"
                  r"new (platform|feed)|this feed|get (the|this) ball rolling|(get|getting) (things|this) started|"
                  r"be part of (it|this)|build (this|the) (feed|community)", re.I)
load = lambda t, m: [json.loads(l) for l in open(f"{V3}/{t}/r101/posting_{m}.jsonl") if l.strip()]
posts = lambda rs: [(r["user_id"], a) for r in rs for a in r["actions"] if a["action"] == "create_post"]
sub = lambda a: str(a.get("subreddit", "")).lower().replace("r/", "")
words = lambda s: len(str(s).split())
text = lambda a: f"{a.get('title', '')} {a.get('body', '')}"
pct = lambda k, n: f"{100 * k / n:.0f}" if n else "-"

print("| test | AI | posts | body words | title words | ? titles % | site talk: posts % | site talk: reasons % | "
      + " | ".join(TOP) + " | same subreddit as v1 |")
print("|---" * (10 + len(TOP)) + "|")
for m, n in M.items():
    first = {u: sub(a) for u, a in reversed(posts(load("v1", m)))}  # each user's first v1 post
    for t in T:
        rs = load(t, m)
        ps = [a for _, a in posts(rs)]
        posters = [r for r in rs if any(a["action"] == "create_post" for a in r["actions"])]
        c = Counter(sub(a) for a in ps)
        both = [(u, sub(a)) for u, a in posts(rs) if u in first]
        print(f"| {t} | {n} | {len(ps)} | {st.median(words(a.get('body', '')) for a in ps):.0f} | "
              f"{st.mean(words(a.get('title', '')) for a in ps):.1f} | "
              f"{pct(sum(str(a.get('title', '')).strip().endswith('?') for a in ps), len(ps))} | "
              f"{pct(sum(bool(SITE.search(text(a))) for a in ps), len(ps))} | "
              f"{pct(sum(bool(SITE.search(r.get('reason') or '')) for r in posters), len(posters))} | "
              + " | ".join(pct(c[k], len(ps)) for k in TOP)
              + f" | {'-' if t == 'v1' else pct(sum(first[u] == s for u, s in both), len(both))} |")
