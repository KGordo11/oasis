"""Why does gemma upvote gemma's posts in V3 part 1 (log 14.53)? Read-only, stdlib only (log 14.57).

IN PLAIN WORDS
--------------
Part 1 found one clear own-AI lean: gemma, playing the readers, upvotes posts that gemma wrote more often than posts that
llama or qwen wrote, and llama and qwen (as readers) don't rate gemma's posts higher. This script asks whether the lean is
something about WHICH posts gemma writes (topic, length, questions, who wrote them) or about the posts in general:

  * the same lean measure (double difference, per 100 posts read, 95% range from resampling posts and users) INSIDE
    groups of posts: each topic, short/medium/long posts, posts that ask a question or not, reader and author with the
    same stance on the topic or not, early in the scroll (few comments yet) or later. If the lean is there in every
    group, none of those things explains it.
  * post by post: gemma's upvote % on the post minus the other two readers' average ("gemma's extra"). Is the extra
    spread over most of gemma's posts, or a few posts?
  * the live world: a post screen shows the comments earlier readers left (in a cell every reader is the same AI). Each
    comment's writer also voted on the post on that screen, so the comments a reader sees lean up, down, even, or there
    are none yet. Upvote % by that tone, and how often each post set shows each tone.

    python3 examples/experiment/llm_bias/check_gemma_own.py data/llm_bias/v3        (~5 min)
"""
import json, os, statistics as st, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze_v2 as A  # noqa: E402
from v3_big_summary import load, gate  # noqa: E402

G, LL, Q = "gemma3:12b", "llama3.1:8b", "qwen3:8b"
D = sys.argv[1]
rows, extra = load(D)
gate(rows, extra)
STANCE = {p["id"]: p["stances"] for p in json.load(open(os.path.join(HERE, "personas_v2.json")))}

post = {}  # post_key -> title, body
for r in rows:
    if r["turn"] == "post":
        k = 0
        for a in r["actions"]:
            if a["action"] == "create_post":
                post[f"r101|{r['model'].replace(':', '-')}|u{r['user_id']}|{k}"] = (a.get("title") or "", a.get("body") or a.get("content") or "")
                k += 1
read = [r for r in rows if r["turn"] == "read" and r["outcome"] == "chose" and not r["draw"]]
assert all(r["post_key"] in post for r in read), "a read post has no posting row"
up = lambda r: int(A.has(r, "like_post"))
chars = {k: len(t) + len(b) for k, (t, b) in post.items()}
cut = sorted(chars.values())
c1, c2 = cut[len(cut) // 3], cut[2 * len(cut) // 3]
last = max(r["tick"] for r in read)


def lean(sub, n=500):
    out = []
    for j in (LL, Q):
        v = A.dd(sub, G, j, up)
        lo, hi = A.boot(sub, G, j, up, n) if v is not None else (None, None)
        out.append("-" if v is None else f"{100 * v:+.1f} ({100 * lo:+.1f} to {100 * hi:+.1f})" if lo is not None else f"{100 * v:+.1f}")
    return out


def upv(sub, m, pb):
    c = [r for r in sub if r["model"] == m and r["posts_by"] == pb]
    return f"{100 * sum(map(up, c)) / len(c):.1f}" if c else "-"


groups = [("all posts", lambda r: True)]
groups += [(f"topic {t}", lambda r, t=t: r["topic"] == t) for t in sorted({r["topic"] for r in read})]
groups += [(f"short post (< {c1} chars)", lambda r: chars[r["post_key"]] < c1),
           (f"medium ({c1}-{c2 - 1})", lambda r: c1 <= chars[r["post_key"]] < c2),
           (f"long (>= {c2})", lambda r: chars[r["post_key"]] >= c2),
           ("post asks a question (?)", lambda r: "?" in "".join(post[r["post_key"]])),
           ("no question", lambda r: "?" not in "".join(post[r["post_key"]])),
           ("reader + author same stance on the topic", lambda r: r["stance"] == STANCE[r["author_id"]][r["topic"]]),
           ("different stance", lambda r: r["stance"] != STANCE[r["author_id"]][r["topic"]]),
           (f"early: first 10% of the scroll (tick < {last // 10 + 1})", lambda r: r["tick"] <= last // 10),
           ("rest of the scroll", lambda r: r["tick"] > last // 10)]

print(f"# Gemma's own-AI upvote lean, part 1 ({D})\n")
print("Upvote % = % of posts read that got an upvote. Lean = (gemma on gemma's - other on gemma's) - (gemma on other's - other on other's), "
      "per 100 posts read; range = 95% from resampling posts and users (500 draws).\n")
print("| group | posts gemma / llama / qwen | gemma reader: upvote % on gemma / llama / qwen posts | llama reader | qwen reader | "
      "lean gemma-llama | lean gemma-qwen |")
print("|---|---|---|---|---|---|---|")
for name, f in groups:
    sub = [r for r in read if f(r)]
    n = {pb: len({r["post_key"] for r in sub if r["posts_by"] == pb}) for pb in (G, LL, Q)}
    cells = [" / ".join(upv(sub, m, pb) for pb in (G, LL, Q)) for m in (G, LL, Q)]
    print(f"| {name} | {n[G]} / {n[LL]} / {n[Q]} | " + " | ".join(cells) + " | " + " | ".join(lean(sub)) + " |", flush=True)

# post by post: gemma's upvote % minus the mean of llama's and qwen's
rate = defaultdict(lambda: [0, 0])
for r in read:
    x = rate[(r["post_key"], r["model"])]
    x[0] += up(r); x[1] += 1
pr = lambda k, m: 100 * rate[(k, m)][0] / rate[(k, m)][1]
print("\n## Post by post: gemma's extra = gemma's upvote % on the post - mean of llama's and qwen's upvote % on it\n")
print("| posts by | posts | mean extra | median extra | % of posts with extra > 0 | gemma's % vs the others' % on the same post (correlation) |")
print("|---|---|---|---|---|---|")
ex = {}
for pb in (G, LL, Q):
    ks = sorted({r["post_key"] for r in read if r["posts_by"] == pb})
    e = [pr(k, G) - (pr(k, LL) + pr(k, Q)) / 2 for k in ks]
    ex.update(zip(ks, e))
    cor = st.correlation([pr(k, G) for k in ks], [(pr(k, LL) + pr(k, Q)) / 2 for k in ks])
    print(f"| {pb} | {len(ks)} | {st.mean(e):+.1f} | {st.median(e):+.1f} | {100 * sum(x > 0 for x in e) / len(e):.0f}% | {cor:.2f} |")
gk = sorted((k for k in ex if "|gemma3-12b|" in k), key=ex.get)
for label, ks in (("most extra", gk[::-1][:5]), ("least extra", gk[:5])):
    print(f"\nGemma's posts with the {label} (gemma % / llama % / qwen %, title):")
    for k in ks:
        print(f"  {pr(k, G):5.1f} / {pr(k, LL):5.1f} / {pr(k, Q):5.1f}  {post[k][0][:90]}")

# the live world: tone of the comments on screen (each comment's writer upvoted / downvoted the post on that screen)
print("\n## Comments on screen: upvote % by what the earlier commenters did to the post\n")
print("Tone = commenters who upvoted minus commenters who downvoted the post, over the comments other users wrote in "
      "earlier ticks. Each cell: % of posts read with that tone, then % upvoted.\n")
print("| reader | posts by | comments per post | none yet | mostly up | even | mostly down |\n|---|---|---|---|---|---|---|")
for m in (G, LL, Q):
    for pb in (G, LL, Q):
        f = os.path.join(D, "r101", f"reading_{pb.replace(':', '-')}__{m.replace(':', '-')}.jsonl")
        rs = [json.loads(l) for l in open(f) if l.strip()]
        assert rs[0]["model"] == m and rs[0]["posts_by"] == pb, f
        com = defaultdict(list)
        for r in rs:
            v = A.has(r, "like_post") - A.has(r, "dislike_post") if r["screen"] in ("post", "open_post") else 0
            for a, e in zip(r["actions"], r["executed"]):
                if a["action"] == "create_comment" and e["ok"]:
                    com[e["target"]].append((r["tick"], r["user_id"], v))
        seen = {}
        for r in rs:
            if r["screen"] != "post" or r["outcome"] != "chose":
                continue
            k = (r["user_id"], r["post_key"])
            if k in seen:
                seen[k][1] |= A.has(r, "like_post")
                continue
            vis = [v for t, u, v in com[r["ctx"]["post"]] if t < r["tick"] and u != r["user_id"]]
            seen[k] = ["none" if not vis else "up" if sum(vis) > 0 else "down" if sum(vis) < 0 else "even", A.has(r, "like_post")]
        cells = []
        for b in ("none", "up", "even", "down"):
            x = [u for t, u in seen.values() if t == b]
            cells.append(f"{100 * len(x) / len(seen):.1f}% of reads, {100 * sum(x) / len(x):.1f}% up" if x else "-")
        print(f"| {m} | {pb} | {sum(map(len, com.values())) / len(com):.1f} | " + " | ".join(cells) + " |")
