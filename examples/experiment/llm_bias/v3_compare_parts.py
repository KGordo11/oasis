"""Big sim part 1 vs part 2 (log 14.49, 14.57): the same posts read with the V1 menu order (part 1) and with the menu
ranked from part 1's data, least-used actions on top (part 2). Read-only, stdlib only.

IN PLAIN WORDS
--------------
Every number is per 100 posts read (one post read = one user x one post, all its refresh views together), part 1 -> part 2:
  1. what each reader AI did (its 3 post sets together): total engagement (every action except do_nothing) and each action
  2. reader AI x whose posts: total engagement and % of posts upvoted
  3. own-AI bias (double difference, 95% range from resampling posts and users): does the menu order change it?
  4. follow-up screens of the live world (search, profiles, messages)
Both parts must pass the B-34 gate (same post counts, every cell = posts x 99 readers) before anything is printed.

    python3 examples/experiment/llm_bias/v3_compare_parts.py data/llm_bias/v3 data/llm_bias/v3_flipped   (~6 min)
"""
import os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze_v2 as A  # noqa: E402
from v3_big_summary import load, gate  # noqa: E402

AIS = ["gemma3:12b", "llama3.1:8b", "qwen3:8b"]
parts = []
for d in sys.argv[1:3]:
    rows, extra = load(d)
    gate(rows, extra)
    parts.append(([r for r in rows if r["turn"] == "read" and r["outcome"] == "chose" and not r["draw"]], extra))
(r1, x1), (r2, x2) = parts
print(f"# Part 1 ({sys.argv[1]}) -> part 2 ({sys.argv[2]})\n\nGATE OK on both parts. Every number is per 100 posts read.\n")


def per100(rs):
    c = Counter(a["action"] for r in rs for a in r["actions"])
    return {k: 100 * v / len(rs) for k, v in c.items()}, 100 * sum(map(A.n_engage, rs)) / len(rs)


arrow = lambda a, b: f"{a:.1f} -> {b:.1f}"
print("## 1. What each reader AI did (its 3 post sets together)\n")
for m in AIS:
    (c1, e1), (c2, e2) = (per100([r for r in rs if r["model"] == m]) for rs in (r1, r2))
    print(f"**{m}**: total engagement {arrow(e1, e2)}\n\n| action | part 1 -> part 2 |\n|---|---|")
    for k in sorted(set(c1) | set(c2), key=lambda k: -max(c1.get(k, 0), c2.get(k, 0))):
        if max(c1.get(k, 0), c2.get(k, 0)) >= 0.5:
            print(f"| {k} | {arrow(c1.get(k, 0), c2.get(k, 0))} |")
    print()

print("## 2. Reader AI x whose posts\n\n| reader | posts by | total engagement | % upvoted |\n|---|---|---|---|")
for m in AIS:
    for pb in AIS:
        a, b = ([r for r in rs if r["model"] == m and r["posts_by"] == pb] for rs in (r1, r2))
        upp = lambda c: 100 * sum(A.has(r, "like_post") for r in c) / len(c)
        print(f"| {m} | {pb}{' (own)' if m == pb else ''} | {arrow(per100(a)[1], per100(b)[1])} | {arrow(upp(a), upp(b))} |")

print("\n## 3. Own-AI bias (double difference; 95% range)\n\n| pair | total engagement part 1 | part 2 | upvote part 1 | part 2 |\n|---|---|---|---|---|")
for i in range(3):
    for j in range(i + 1, 3):
        cells = []
        for f in (A.n_engage, lambda r: int(A.has(r, "like_post"))):
            for rs in (r1, r2):
                v, (lo, hi) = A.dd(rs, AIS[i], AIS[j], f), A.boot(rs, AIS[i], AIS[j], f, 500)
                cells.append(f"{100 * v:+.1f} ({100 * lo:+.1f} to {100 * hi:+.1f})")
        print(f"| {AIS[i]} - {AIS[j]} | " + " | ".join(cells) + " |", flush=True)

print("\n## 4. Live world follow-up screens\n\n| reader | posts by | follow-up screens | actions on them |\n|---|---|---|---|")
for k in sorted(x1):
    e1, e2 = x1[k], x2[k]
    f = lambda e, s: 100 * e[s] / e["posts read"]
    print(f"| {k[0]} | {k[1]} | {arrow(f(e1, 'follow-up screens'), f(e2, 'follow-up screens'))} | "
          f"{arrow(f(e1, 'follow-up actions'), f(e2, 'follow-up actions'))} |")
