"""Plain-percentage summary of one V3 test (log 14.43). Read-only, stdlib only.

    python3 examples/experiment/llm_bias/v3_summary.py 0        (or check, 1, 2a, 2b, 2c, 3, 4)

POSTING: % of users per AI who posted / only refreshed / sent an empty list / only do_nothing / did something else.
READING: per post a user read (all views of it together, since a refreshed post comes back): % with an upvote,
downvote, comment, nothing at all; refresh returns per 100 posts; posts dropped after 5 refreshes in a row.
Also unreadable answers, qwen's thinking length and seconds per screen.
"""
import glob, json, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_v2 as R  # noqa: E402

T = sys.argv[1] if len(sys.argv) > 1 else "0"
D = os.path.join(os.environ.get("V3_DIR", os.path.join(HERE, "..", "..", "..", "data", "llm_bias", "v3_tests")), f"t{T}", "r200")
load = lambda f: [json.loads(l) for l in open(f) if l.strip()]
pct = lambda a, b: f"{100 * a / b:5.1f}" if b else "    -"

print(f"V3 test {T}  ({os.path.abspath(D)})")
print("\nPOSTING TURN  (% of users)")
for f in sorted(glob.glob(f"{D}/posting_*.jsonl")):
    rs, c = load(f), Counter()
    for r in rs:
        n = {a["action"] for a in r["actions"]}
        c["unreadable" if r["outcome"] != "chose" else "posted" if "create_post" in n else "empty list" if not n
          else "only refresh" if n == {"refresh"} else "only do_nothing" if n == {"do_nothing"} else "other"] += 1
    th = [len(r.get("thinking") or "") for r in rs]
    per = Counter(min(sum(a["action"] == "create_post" for a in r["actions"]), 2) for r in rs)
    print(f"  {os.path.basename(f)[8:-6]:16s}" + "".join(f"  {k} {pct(c[k], len(rs))}" for k in
          ("posted", "only refresh", "empty list", "only do_nothing", "other", "unreadable"))
          + f"   posts {sum(a['action'] == 'create_post' for r in rs for a in r['actions'])}"
          + f"   users with 0/1/2+ posts {per[0]}/{per[1]}/{per[2]}"
          + (f"   thinking {sum(th) // len(th)} chars" if any(th) else ""))

print("\nREADING TURN  (% of posts read, all views of a post together; noise-floor files left out)")
by = defaultdict(list)
for f in glob.glob(f"{D}/reading_*.jsonl"):
    if "_d" not in os.path.basename(f).split("__")[1]:
        for r in load(f):
            by[r["model"]].append(r)
for m, rs in sorted(by.items()):
    pairs = defaultdict(list)
    for r in rs:
        pairs[(r["posts_by"], r["user_id"], r["post_key"])].append(r)
    c = Counter()
    for views in pairs.values():
        n = {a["action"] for r in views for a in r["actions"]}
        c["up"] += "like_post" in n; c["down"] += "dislike_post" in n; c["comment"] += "create_comment" in n
        c["nothing"] += not (n - {"do_nothing", "refresh"})
        last = {a["action"] for a in max(views, key=lambda r: r.get("view", 1))["actions"]}
        c["dropped"] += len(views) == R.REFRESH_MAX and "refresh" in last and not last & R.ON_POST
    th = [len(r.get("thinking") or "") for r in rs]
    acts = sum(a["action"] != "do_nothing" for r in rs for a in r["actions"])
    print(f"  {m:12s} posts {len(pairs):6d}  actions/100 {100 * acts / len(pairs):6.1f}  up {pct(c['up'], len(pairs))}"
          f"  down {pct(c['down'], len(pairs))}  comment {pct(c['comment'], len(pairs))}  nothing {pct(c['nothing'], len(pairs))}"
          f"  returns/100 {100 * (len(rs) - len(pairs)) / len(pairs):5.1f}  dropped {c['dropped']}"
          f"  unreadable {pct(sum(r['outcome'] != 'chose' for r in rs), len(rs))}"
          + (f"  thinking {sum(th) // len(th)} chars" if any(th) else ""))

print("\nSPEED  (wall-clock seconds per screen with 8 at once, from the manifests)")
sp = defaultdict(lambda: [0.0, 0])
for f in glob.glob(f"{D}/*.manifest.json"):
    m = json.load(open(f))
    sp[(m["turn"], m["model"])][0] += m["seconds_llm"]; sp[(m["turn"], m["model"])][1] += m["screens"]
for (t, m), (s, n) in sorted(sp.items()):
    print(f"  {t:5s} {m:12s} {s / max(n, 1):5.2f} s/screen  ({n} screens, {s / 3600:.1f} h)")

# CHECKS: the data obeys the V3 rules (every post read once, no own post, refresh returns only as designed)
R.DATA = os.path.dirname(D)
problems = []
for f in sorted(glob.glob(f"{D}/*.manifest.json")):
    m = json.load(open(f))
    v = m.get("v3_test") or {}
    if not (v.get("v1") and v.get("think") and v.get("refresh_loop")):
        problems.append(f"{os.path.basename(f)}: not run with the V3 baseline options ({v})")
for f in sorted(glob.glob(f"{D}/reading_*.jsonl")):
    rs, name = load(f), os.path.basename(f)
    agents = 100 if "_a" not in name else int(name.split("_a")[-1][:-6])
    noise = "_d" in name.split("__")[1]
    posts = {q["key"]: q for q in R.post_set(200, rs[0]["posts_by"], agents)[0]} if rs else {}
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
            back = "refresh" in n and not n & R.ON_POST and w < R.REFRESH_MAX
            j = at.get((r["post_key"], w + 1))
            if back != (j is not None) or (j is not None and j - i not in (1, 2)) or w > R.REFRESH_MAX:
                problems.append(f"{name}: user {u} post {r['post_key']} view {w}: refresh return not as designed"); break
print("\nCHECKS: " + ("ALL CHECKS PASS" if not problems else f"{len(problems)} PROBLEM(S)"))
for p in problems[:30]:
    print("   PROBLEM:", p)
