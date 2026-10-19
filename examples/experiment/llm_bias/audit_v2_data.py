"""Audit of every saved answer in rounds 101-104 (log Part 14 sec. 14.42). Read-only, stdlib only: runs on the laptop or the Spark.

IN PLAIN WORDS
--------------
1. Re-reads every AI reply word for word (the "raw" field) and parses it again: do the saved actions equal what the AI
   actually wrote? Any reply without an "actions" key, any reply that isn't JSON, any mismatch is counted.
2. How each AI says "nothing": an empty list [] or the do_nothing action (both count as "did nothing" in every table).
3. How much of each AI's "total engagement" is NOT about the post on the screen (refresh, trend, search, groups).
4. The 3 x 3 grid and the own-AI bias with all actions (as published) and with post actions only.
5. The posting turn: what each AI's users did instead of posting.

Usage:  python3 examples/experiment/llm_bias/audit_v2_data.py [data folder, default = this repo's data/llm_bias/v2]
"""
import glob, json, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import llm  # noqa: E402
import run_v2 as R  # noqa: E402

D = sys.argv[1] if len(sys.argv) > 1 else R.DATA
POST = {"like_post", "unlike_post", "dislike_post", "undo_dislike_post", "create_comment", "repost", "quote_post",
        "report_post", "like_comment", "unlike_comment", "dislike_comment", "undo_dislike_comment",
        "follow", "unfollow", "mute", "unmute"}
M = [m.split(":")[0] for m in R.MODELS]
rows = []
for f in sorted(glob.glob(f"{D}/r10[1-4]/*.jsonl")):
    rows += [json.loads(l) for l in open(f)]
print(f"{len(rows):,} saved rows in {D}\n")

print("1. RAW REPLY vs SAVED ACTIONS")
chk = defaultdict(Counter)
for r in rows:
    k = (r["turn"] + ("_d1" if r["draw"] else ""), r["model"].split(":")[0])
    if r["outcome"] != "chose":
        chk[k]["unreadable (left out)"] += 1; continue
    try:
        o = llm.extract_json(r.get("raw"))
    except (ValueError, TypeError):
        chk[k]["PROBLEM: raw not JSON"] += 1; continue
    if not isinstance(o, dict) or "actions" not in o:
        chk[k]["PROBLEM: no 'actions' key"] += 1; continue
    try:
        same = R.validate(o)["actions"] == r["actions"]
    except ValueError:
        same = False
    chk[k]["ok" if same else "PROBLEM: re-parse differs"] += 1
for k in sorted(chk):
    print(f"   {k[0]:8s} {k[1]:9s}", dict(chk[k]))

reading = [r for r in rows if r["turn"] == "read" and not r["draw"] and r["outcome"] == "chose"]
print("\n2. HOW EACH AI SAYS 'NOTHING' (reading turn, % of screens)")
for m in M:
    rs = [r for r in reading if r["model"].startswith(m)]
    names = [[a["action"] for a in r["actions"]] for r in rs]
    e = sum(not n for n in names); dn = sum(set(n) == {"do_nothing"} for n in names)
    mix = sum("do_nothing" in n and len(set(n)) > 1 for n in names)
    print(f"   {m:9s} empty list {100 * e / len(rs):5.1f}%   only do_nothing {100 * dn / len(rs):5.1f}%   "
          f"do_nothing next to another action {100 * mix / len(rs):4.1f}%")

print("\n3. ACTIONS THAT ARE NOT ABOUT THE POST (reading turn, per 100 screens)")
for m in M:
    rs = [r for r in reading if r["model"].startswith(m)]
    c = Counter(a["action"] for r in rs for a in r["actions"] if a["action"] != "do_nothing")
    other = {a: v for a, v in c.items() if a not in POST}
    print(f"   {m:9s} all {100 * sum(c.values()) / len(rs):6.1f}   not about the post {100 * sum(other.values()) / len(rs):5.1f}  "
          + ", ".join(f"{a} {100 * v / len(rs):.1f}" for a, v in sorted(other.items(), key=lambda t: -t[1])[:5]))

print("\n4. GRID (actions per 100 screens: all | post actions only) AND OWN-AI BIAS")
S = defaultdict(lambda: [0, 0, 0])
for r in reading:
    s = S[("V2" if r["round"] >= R.SELF_ID_FROM_ROUND else "V1", r["model"].split(":")[0], r["posts_by"].split(":")[0])]
    s[0] += 1; s[1] += sum(a["action"] != "do_nothing" for a in r["actions"]); s[2] += sum(a["action"] in POST for a in r["actions"])
for v in ("V1", "V2"):
    g = lambda i, j, c: 100 * S[(v, i, j)][c] / S[(v, i, j)][0]
    print(f"   {v}  reader \\ posts by: " + "   ".join(f"{j:>15s}" for j in M))
    for i in M:
        print(f"   {'':4s}{i:15s}" + "   ".join(f"{g(i, j, 1):6.1f} | {g(i, j, 2):6.1f}" for j in M))
    for i, j in ((M[0], M[1]), (M[0], M[2]), (M[1], M[2])):
        b = lambda c: (g(i, i, c) - g(j, i, c)) - (g(i, j, c) - g(j, j, c))
        print(f"      bias {i}-{j}: all {b(1):+.1f}   post actions only {b(2):+.1f}")

print("\n5. POSTING TURN: what the users did (all 4 rounds, 400 user-turns per AI)")
for m in M:
    rs = [r for r in rows if r["turn"] == "post" and r["model"].startswith(m)]
    c = Counter("unreadable" if r["outcome"] != "chose" else
                "posted" if any(a["action"] == "create_post" for a in r["actions"]) else
                "empty list" if not r["actions"] else "+".join(sorted({a["action"] for a in r["actions"]})) for r in rs)
    print(f"   {m:9s}", ", ".join(f"{k} {v}" for k, v in c.most_common(6)))
