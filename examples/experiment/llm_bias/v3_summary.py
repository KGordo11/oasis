"""Plain-percentage summary of one V3 test, next to the V1 run (log 14.43). Read-only, stdlib only.

    python3 examples/experiment/llm_bias/v3_summary.py p_menu        (or v1, p_think, ..., r_menu)

Every test = V1 + ONE addition, so every number is printed as "V1 -> test" for the same users and the same posts.
POSTING: % of users who posted / only refreshed / sent an empty list / only do_nothing / did something else, and users
with 0 / 1 / 2+ posts. READING: per post a user read (all views of it together, since a refreshed post comes back):
% with an upvote, downvote, comment, nothing at all; refresh returns per 100 posts; posts dropped after 5 refreshes.
CHECKS: every step made with exactly the test's one change, every post read once, no own post, refresh as designed.
"""
import glob, json, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_v2 as R  # noqa: E402

T = sys.argv[1] if len(sys.argv) > 1 else "v1"
BASE = os.environ.get("V3_DIR", os.path.join(HERE, "..", "..", "..", "data", "llm_bias", "v3_tests"))
D, V1 = os.path.join(BASE, T, "r101"), os.path.join(BASE, "v1", "r101")
WANT = {"v1": [], "p_think": ["think"], "r_think": ["think"], "p_menu": ["post_menu"], "p_2a": ["post_line"],
        "p_2b": ["post_line"], "p_2c": ["post_line"], "p_screen": ["post_screen"], "r_refresh": ["refresh_loop"],
        "r_json": ["free_text"], "r_menu": ["menu_order"]}[T]
load = lambda f: [json.loads(l) for l in open(f) if l.strip()]
pct = lambda a, b: 100 * a / b if b else float("nan")


def posting(d):
    out = {}
    for f in sorted(glob.glob(f"{d}/posting_*.jsonl")):
        if "_a30" in f:
            continue  # V1's own posts, copied in for the reading tests
        rs, c = load(f), Counter()
        for r in rs:
            n = [a["action"] for a in r["actions"]]
            s = set(n)
            c["unreadable" if r["outcome"] != "chose" else "posted" if "create_post" in s else "empty list" if not s
              else "only refresh" if s == {"refresh"} else "only do_nothing" if s == {"do_nothing"} else "other"] += 1
            c[f"{min(n.count('create_post'), 2)} posts"] += 1
            c["posts"] += n.count("create_post")
        th = [len(r.get("thinking") or "") for r in rs]
        out[os.path.basename(f)[8:-6]] = {**{k: pct(c[k], len(rs)) for k in ("posted", "only refresh", "empty list",
                                          "only do_nothing", "other", "unreadable", "0 posts", "1 posts", "2 posts")},
                                          "posts": c["posts"], "thinking": sum(th) / len(th) if any(th) else 0}
    return out


def reading(d):
    by, out = defaultdict(list), {}
    for f in glob.glob(f"{d}/reading_*.jsonl"):
        if "_d" not in os.path.basename(f).split("__")[1]:
            by[os.path.basename(f)[8:-6]] += load(f)
    for cell, rs in sorted(by.items()):
        pairs = defaultdict(list)
        for r in rs:
            pairs[(r["user_id"], r["post_key"])].append(r)
        c = Counter()
        for views in pairs.values():
            n = {a["action"] for r in views for a in r["actions"]}
            c["up"] += "like_post" in n; c["down"] += "dislike_post" in n; c["comment"] += "create_comment" in n
            c["nothing"] += not (n - {"do_nothing", "refresh"})
            last = {a["action"] for a in max(views, key=lambda r: r.get("view", 1))["actions"]}
            c["dropped"] += len(views) == R.REFRESH_MAX and "refresh" in last and not last & R.ON_POST
        th = [len(r.get("thinking") or "") for r in rs]
        acts = sum(a["action"] != "do_nothing" for r in rs for a in r["actions"])
        out[cell] = {"posts": len(pairs), "actions/100": pct(acts, len(pairs)), **{k: pct(c[k], len(pairs)) for k in
                     ("up", "down", "comment", "nothing")}, "returns/100": pct(len(rs) - len(pairs), len(pairs)),
                     "dropped": c["dropped"], "unreadable": pct(sum(r["outcome"] != "chose" for r in rs), len(rs)),
                     "thinking": sum(th) / len(th) if any(th) else 0}
    return out


def show(title, test, base, keys):
    if not test:
        return
    print(f"\n{title}  (V1 -> {T})" if T != "v1" else f"\n{title}")
    for name, t in test.items():
        b = base.get(name, {})
        cells = [f"{k} {b[k]:5.1f} -> {t[k]:5.1f}" if T != "v1" and k in b else f"{k} {t[k]:5.1f}" for k in keys]
        print(f"  {name:28s} " + "  ".join(cells))


print(f"V3 test {T} = V1 + {WANT or 'nothing'}   ({os.path.abspath(D)})")
show("POSTING TURN, 100 users (% of users; 'N posts' = % of users who wrote N, 2 = 2 or more)", posting(D), posting(V1),
     ["posted", "only refresh", "empty list", "only do_nothing", "other", "unreadable", "0 posts", "1 posts", "2 posts",
      "posts", "thinking"])
show("READING TURN, 30 users, V1's posts (% of posts read; reading_<posts by>__<reader>)", reading(D), reading(V1),
     ["posts", "actions/100", "up", "down", "comment", "nothing", "returns/100", "dropped", "unreadable", "thinking"])

# CHECKS
problems = []
for f in sorted(glob.glob(f"{D}/*.manifest.json")):
    m, name = json.load(open(f)), os.path.basename(f)
    got = m.get("changes_from_v1", [] if not m.get("v3_test") else None)
    want = [] if "_a30" in name and name.startswith("posting_") else WANT  # V1's own posts, copied in
    if got != want:
        problems.append(f"{name}: changes from V1 {got}, this test needs exactly {want}")
R.DATA = os.path.dirname(D)
for f in sorted(glob.glob(f"{D}/reading_*.jsonl")):
    rs, name = load(f), os.path.basename(f)
    agents = 100 if "_a" not in name else int(name.split("_a")[-1][:-6])
    noise = "_d" in name.split("__")[1]
    posts = {q["key"]: q for q in R.post_set(101, rs[0]["posts_by"], agents)[0]} if rs else {}
    seen = Counter((r["user_id"], r["post_key"], r.get("view", 1)) for r in rs)
    if max(seen.values(), default=1) > 1:
        problems.append(f"{name}: {sum(c > 1 for c in seen.values())} duplicate screens")
    first = {(u, k) for u, k, w in seen if w == 1}
    want = {(u, k) for u in range(agents) for k, q in posts.items() if q["author_id"] != u}
    if not noise and first != want:
        problems.append(f"{name}: {len(want - first)} posts never read, {len(first - want)} extra (own post or unknown)")
    if any(posts.get(k, {}).get("author_id") == u for u, k, _ in seen):
        problems.append(f"{name}: a user read their own post")
    by_user = defaultdict(list)
    for r in rs:
        by_user[r["user_id"]].append(r)
    for u, s in by_user.items():
        s.sort(key=lambda r: r["pos"])
        at = {(r["post_key"], r.get("view", 1)): i for i, r in enumerate(s)}
        for i, r in enumerate(s):
            n, w = {x["action"] for x in r["actions"]}, r.get("view", 1)
            back = T == "r_refresh" and "refresh" in n and not n & R.ON_POST and w < R.REFRESH_MAX
            j = at.get((r["post_key"], w + 1))
            if back != (j is not None) or (j is not None and j - i not in (1, 2)) or w > R.REFRESH_MAX:
                problems.append(f"{name}: user {u} post {r['post_key']} view {w}: refresh return not as designed"); break
print("\nCHECKS: " + ("ALL CHECKS PASS" if not problems else f"{len(problems)} PROBLEM(S)"))
for p in problems[:30]:
    print("   PROBLEM:", p)
