"""Big-sim part, tick by tick (log 14.60). Read-only, stdlib only.

IN PLAIN WORDS
--------------
In the live world every user scrolls at the same pace: at tick 0 each of the 100 users reads the first post of their
own scroll, at tick 1 the second, and so on. A user sees the comments other users left in EARLIER ticks. So tick 0 is
like V1: one look at a post, nobody has commented on anything yet. Each tick later, more comments are on screen.
This script splits a big-sim part by tick: tick 0 alone, then groups of ticks, next to V1 round 101 and the whole part.
Only the post screen counts (one row per post read; follow-up screens such as profiles are left out, as in
v3_big_summary.py).

    python3 examples/experiment/llm_bias/v3_by_tick.py data/llm_bias/v3            (part 1; v3_flipped = part 2)
"""
import json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze_v2 as A  # noqa: E402
from v3_big_summary import load, gate  # noqa: E402

D = sys.argv[1]
V1 = os.path.join(HERE, "../../../data/llm_bias/v1_v2_spark")
MODELS = ["gemma3:12b", "llama3.1:8b", "qwen3:8b"]
SHORT = {m: m.split(":")[0].rstrip("0123456789.") for m in MODELS}
BANDS = [("tick 0", 0, 0), ("ticks 1-9", 1, 9), ("ticks 10-29", 10, 29), ("ticks 30-59", 30, 59), ("ticks 60+", 60, 999)]
up = lambda r: int(A.has(r, "like_post"))  # noqa: E731

rows, extra = load(D)
gate(rows, extra)
read = [r for r in rows if r["turn"] == "read" and r["outcome"] == "chose" and not r["draw"]]
v1 = [r for r in load(V1)[0] if r["turn"] == "read" and r["outcome"] == "chose" and not r["draw"]]

# comments other users left in earlier ticks, per post; each cell is its own world, so key by reader AND posts_by
com = defaultdict(list)
for f in os.listdir(os.path.join(D, "r101")):
    if f.startswith("reading_") and f.endswith(".jsonl") and "_d" not in f and "_a" not in f.split("__")[1]:
        for l in open(os.path.join(D, "r101", f)):
            r = json.loads(l)
            for a, e in zip(r["actions"], r.get("executed") or []):
                if a["action"] == "create_comment" and e["ok"]:
                    com[(r["model"], r["posts_by"], e["target"])].append((r["tick"], r["user_id"]))
seen = lambda r: sum(t < r["tick"] and u != r["user_id"] for t, u in com[(r["model"], r["posts_by"], r["ctx"]["post"])])  # noqa: E731


def cells(sub, f, k=100):
    by = defaultdict(list)
    for r in sub:
        by[(r["model"], r["posts_by"])].append(f(r))
    return {c: k * sum(v) / len(v) for c, v in by.items()}


def band(lo, hi):
    return [r for r in read if lo <= r["tick"] <= hi]


cols = [("V1 round 101", v1)] + [(n, band(lo, hi)) for n, lo, hi in BANDS] + [("whole part", read)]
print(f"# {D} tick by tick\n")
print("Posts read per reader at each column (per cell): " + ", ".join(f"{n} {len(s) // 9}" for n, s in cols[1:]) + "\n")
for title, f, k in [("Total engagement (every action except do_nothing) per 100 posts read", A.n_engage, 100),
                    ("% of posts upvoted", up, 100),
                    ("Comments by other users on screen, per post read", seen, 1)]:
    print(f"## {title}\n\n| reader | posts by | " + " | ".join(n for n, _ in cols) + " |\n|---|---|" + "---|" * len(cols))
    got = [cells(s, f, k) if f is not seen or n != "V1 round 101" else {} for n, s in cols]
    for m in MODELS:
        for pb in MODELS:
            print(f"| {SHORT[m]} | {SHORT[pb]} | " + " | ".join(f"{g[(m, pb)]:.1f}" if (m, pb) in g else "-" for g in got) + " |")
    print()

print("## Own-AI bias (double difference, per 100 posts read; 95% range from resampling posts and users)\n")
pairs = [(i, j) for n, i in enumerate(MODELS) for j in MODELS[n + 1:]]
for name, f in [("total engagement", A.n_engage), ("upvote", up)]:
    print(f"**{name}**\n\n| pair | " + " | ".join(n for n, _ in cols) + " |\n|---|" + "---|" * len(cols))
    for i, j in pairs:
        out = []
        for _, s in cols:
            v = A.dd(s, i, j, f)
            lo, hi = A.boot(s, i, j, f, 500)
            star = "**" if lo > 0 or hi < 0 else ""
            out.append(f"{star}{100 * v:+.1f} ({100 * lo:+.1f} to {100 * hi:+.1f}){star}")
        print(f"| {SHORT[i]}-{SHORT[j]} | " + " | ".join(out) + " |")
    print()
