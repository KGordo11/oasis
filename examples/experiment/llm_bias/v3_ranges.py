"""V3 reading tests vs V1, with 95% ranges and the rerun noise (log 14.45). Read-only, stdlib only, laptop.

    python3 examples/experiment/llm_bias/v3_ranges.py

1. Same screen + same seed, same answer? % of first-view screens whose set of actions is identical to the V1 rerun's
   (first column: the ORIGINAL V1 round 101 vs the rerun = what rerunning alone changes).
2. Refresh-only screens (refresh with no reaction to the post), the only screens r_refresh can change.
3. Pair results (double difference of total engagement per 100 screens) and each reader's change vs V1, with 95%
   ranges from resampling the 30 users (4000 draws); CLEAR = the range leaves out 0.
4. Noise reference: the ORIGINAL V1 round 101 vs the V1 rerun, same users, screens and seeds.
"""
import json, os, random
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "..", "..", "..", "data", "llm_bias")
V3, OLD = os.path.join(B, "v3_tests"), os.path.join(B, "v1_v2_spark", "r101")
M = ["gemma3-12b", "llama3.1-8b", "qwen3-8b"]
TESTS = ["r_think", "r_refresh", "r_json", "r_menu"]
ON = {"like_post", "dislike_post", "create_comment", "repost", "quote_post", "report_post", "unlike_post",
      "undo_dislike_post"}
load = lambda f: [json.loads(l) for l in open(f) if l.strip()]
acts = lambda r: frozenset(a["action"] for a in r["actions"])
rows = lambda t, p, r: load(f"{V3}/{t}/r101/reading_{p}__{r}_a30.jsonl")
old_rows = lambda p, r: [x for x in load(f"{OLD}/reading_{p}__{r}.jsonl") if x["user_id"] < 30]
first = lambda rs: {(x["user_id"], x["post_key"]): x for x in rs if x.get("view", 1) == 1}

print("1. same answer as the V1 rerun (% of screens, identical set of actions)")
print(f"   {'posts by -> reader':28s}" + "".join(f"{t:>11s}" for t in ["V1 orig"] + TESTS))
for p in M:
    for r in M:
        v1, cols = first(rows("v1", p, r)), [first(old_rows(p, r))] + [first(rows(t, p, r)) for t in TESTS]
        print(f"   {p + ' -> ' + r:28s}" + "".join(f"{100 * sum(acts(c[k]) == acts(v1[k]) for k in v1) / len(v1):11.1f}"
                                               for c in cols))

print("\n2. refresh-only screens (first views, all 9 cells)")
for t in ["v1", "r_refresh"]:
    fs = [x for p in M for r in M for x in first(rows(t, p, r)).values()]
    print(f"   {t:10s} {sum('refresh' in acts(x) and not acts(x) & ON for x in fs)} of {len(fs)} "
          f"(any refresh: {sum('refresh' in acts(x) for x in fs)})")


def per_user(get):  # (posts_by, reader) -> user -> [actions except do_nothing, first-view screens]
    D = {}
    for p in M:
        for r in M:
            D[(p, r)] = u = defaultdict(lambda: [0, 0])
            for x in get(p, r):
                u[x["user_id"]][0] += sum(a["action"] != "do_nothing" for a in x["actions"])
                u[x["user_id"]][1] += x.get("view", 1) == 1
    return D


def eng(D, us, cells):
    return 100 * sum(D[c][u][0] for c in cells for u in us) / sum(D[c][u][1] for c in cells for u in us)


def pairs(D, us):
    E = {(p, r): eng(D, us, [(p, r)]) for p in M for r in M}
    return [(E[(x, x)] - E[(y, x)]) - (E[(x, y)] - E[(y, y)]) for i, x in enumerate(M) for y in M[i + 1:]]


random.seed(1)
U = list(range(30))
DRAWS = [[random.choice(U) for _ in U] for _ in range(4000)]
rng = lambda v: (sorted(v)[100], sorted(v)[3899])
tag = lambda lo, hi: "CLEAR" if lo > 0 or hi < 0 else "unclear"
NAMES = [f"{x[:5]}-{y[:5]}" for i, x in enumerate(M) for y in M[i + 1:]]
base = per_user(lambda p, r: rows("v1", p, r))
reader = lambda D, us, r: eng(D, us, [(p, r) for p in M])
for t in ["v1"] + TESTS:
    D = per_user(lambda p, r: rows(t, p, r))
    print(f"\n3. {t}: pair results (- = the two AIs engage more with each other's posts)")
    pt, bs = pairs(D, U), [pairs(D, d) for d in DRAWS]
    for k, n in enumerate(NAMES):
        lo, hi = rng([b[k] for b in bs])
        print(f"   {n}  {pt[k]:+6.1f}  [{lo:+6.1f}, {hi:+6.1f}] {tag(lo, hi)}")
    if t != "v1":
        print("   total engagement per 100 screens, by reader (all posts), V1 -> test")
        for r in M:
            lo, hi = rng([reader(D, d, r) - reader(base, d, r) for d in DRAWS])
            print(f"     {r:12s} {reader(base, U, r):6.1f} -> {reader(D, U, r):6.1f}  "
                  f"{reader(D, U, r) - reader(base, U, r):+6.1f} [{lo:+6.1f}, {hi:+6.1f}] {tag(lo, hi)}")

O = per_user(old_rows)
print("\n4. noise reference: V1 original -> V1 rerun (same users, screens, seeds)")
for r in M:
    print(f"     {r:12s} {reader(O, U, r):6.1f} -> {reader(base, U, r):6.1f}  {reader(base, U, r) - reader(O, U, r):+6.1f}")
print("   pairs, V1 original: " + "  ".join(f"{n} {v:+.1f}" for n, v in zip(NAMES, pairs(O, U))))
