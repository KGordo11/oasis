"""Big-sim summary (log 14.49, 14.53): analyze_v2's tables (posting, reader x whose posts, stance, own-AI bias with
ranges, noise floor) on one big-sim part, plus what the live world added. Read-only, stdlib only.

    python3 examples/experiment/llm_bias/v3_big_summary.py data/llm_bias/v3            (part 1)
    python3 examples/experiment/llm_bias/v3_big_summary.py data/llm_bias/v1_v2_spark r101   (V1 round 101, same tables)

One row per POST READ (user x post): the actions on every view of that post screen together (the refresh loop can bring
a post back). Live follow-up screens (search, profiles, messages, ...) are not posts read; their actions are counted
in the extra table only. Writes <dir>/summary.md (analyze_v2's tables).
"""
import glob, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze_v2 as A  # noqa: E402

D = sys.argv[1]
RD = sys.argv[2] if len(sys.argv) > 2 else "r101"
GATE = {"gemma3:12b": 99, "llama3.1:8b": 119, "qwen3:8b": 102} if os.path.basename(os.path.normpath(D)) == "v3" else None


def load(_test=False):
    rows, extra = [], {}
    for f in sorted(glob.glob(os.path.join(D, RD, "*.jsonl"))):
        rs = [json.loads(l) for l in open(f) if l.strip()]
        if os.path.basename(f).startswith("posting_"):
            rows += rs
            continue
        visits, follow = {}, [r for r in rs if r.get("screen", "post") != "post"]
        for r in rs:
            if r.get("screen", "post") == "post":
                v = visits.setdefault((r["user_id"], r["post_key"]), dict(r, actions=[], views=0))
                v["actions"] += r["actions"]; v["views"] += 1
        rows += visits.values()
        if visits and not rs[0]["draw"]:
            e = extra[(rs[0]["model"], rs[0]["posts_by"])] = {"posts read": len(visits)}
            e["returns"] = sum(v["views"] - 1 for v in visits.values())
            e["follow-up screens"] = len(follow)
            e["follow-up actions"] = sum(a["action"] != "do_nothing" for r in follow for a in r["actions"])
            e["unreadable"] = sum(r["outcome"] != "chose" for r in rs)
            e["screens"] = len(rs)
    return rows, extra


rows, extra = load()
if not rows:
    sys.exit(f"no data in {D}/{RD}")
if GATE:  # B-34 gate: reproduce the Spark's own numbers (posts per AI, screens = posts x 99 readers) before anything new
    posts = {m: sum(a["action"] == "create_post" for r in rows if r["turn"] == "post" and r["model"] == m for a in r["actions"])
             for m in GATE}
    assert posts == GATE, f"posts per AI {posts} != published {GATE}"
    for (m, pb), e in extra.items():
        assert e["posts read"] == GATE[pb] * 99, f"{m} reads {pb}: {e['posts read']} posts read != {GATE[pb]} x 99"
    print(f"GATE OK: posts per AI {posts}; every cell = posts x 99 readers\n")
A.DATA, A.load = D, lambda test: rows
A.main(False)
print("\n## Extra: refresh returns and the live world's follow-up screens, per 100 posts read (reader AI x whose posts)\n")
print("| Reader AI | Posts by | Posts read | Refresh returns | Follow-up screens | Actions on follow-up screens | Unreadable (% of all screens) |")
print("|---|---|---|---|---|---|---|")
for (m, pb), e in sorted(extra.items()):
    n = e["posts read"]
    print(f"| {m} | {pb} | {n} | {100 * e['returns'] / n:.1f} | {100 * e['follow-up screens'] / n:.1f} | "
          f"{100 * e['follow-up actions'] / n:.1f} | {100 * e['unreadable'] / e['screens']:.2f}% |")
