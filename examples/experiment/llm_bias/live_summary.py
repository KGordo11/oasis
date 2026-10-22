"""Plain tables for a live-world run (log 14.47): what users did, what worked, and how many steps each thing took.

    python3 examples/experiment/llm_bias/live_summary.py <results folder>      (e.g. data/llm_bias/v3_live)

"Steps" = which screen of a visit the action happened on: 1 = right on the post, 2 = one follow-up screen later
(e.g. search_user -> the profile -> send_message), and so on. Words typed = length of the comment / message.
Stdlib only (runs on the Spark).
"""
import glob, json, os, sys
from collections import Counter, defaultdict

d = sys.argv[1]
by_reader = defaultdict(list)
for f in sorted(glob.glob(os.path.join(d, "r*", "reading_*.jsonl"))):
    if "_d1" in os.path.basename(f):
        continue
    reader = os.path.basename(f).split("__")[1].split("_a")[0].replace(".jsonl", "")
    by_reader[reader] += [json.loads(l) for l in open(f) if l.strip() and '"screen"' in l]
if not by_reader:
    sys.exit(f"no live reading files in {d}")
print("SCREENS: what kind of screen each AI's users were on (% of all screens)")
kinds = ["post", "open_post", "search_posts", "search_user", "trend", "listen_from_group", "open_messages"]
print("| reader | screens | " + " | ".join(kinds) + " |")
print("|---" * (len(kinds) + 2) + "|")
for r, rows in by_reader.items():
    c = Counter(x["screen"] for x in rows)
    print(f"| {r} | {len(rows)} | " + " | ".join(f"{100 * c[k] / len(rows):.1f}" for k in kinds) + " |")

print("\nSTEPS: each action, how often it worked, and on which screen of the visit it happened")
print("| reader | action | done | failed (top reason) | on step 1 / 2 / 3+ | words typed (median) |")
print("|---|---|---|---|---|---|")
for r, rows in by_reader.items():
    ok, bad, why, steps, words = Counter(), Counter(), defaultdict(Counter), defaultdict(Counter), defaultdict(list)
    for x in rows:
        for a, e in zip(x["actions"], x["executed"]):
            n = a["action"]
            if e["ok"]:
                ok[n] += 1; steps[n][min(3, x["step"] + 1)] += 1
                t = a.get("content") or a.get("message")
                if t:
                    words[n].append(len(str(t).split()))
            else:
                bad[n] += 1; why[n][e["error"]] += 1
    for n in sorted(set(ok) | set(bad), key=lambda k: -(ok[k] + bad[k])):
        s = steps[n]; tot = sum(s.values()) or 1
        w = sorted(words[n])
        print(f"| {r} | {n} | {ok[n]} | {bad[n]}" + (f" ({why[n].most_common(1)[0][0]})" if bad[n] else "") +
              f" | {100 * s[1] / tot:.0f} / {100 * s[2] / tot:.0f} / {100 * s[3] / tot:.0f} % | {w[len(w) // 2] if w else '-'} |")

print("\nSOCIAL: private messages and group chats")
print("| reader | messages sent | users who sent one | conversations | replies (answered a message) | groups made | joins | group messages |")
print("|---|---|---|---|---|---|---|---|")
for r, rows in by_reader.items():
    sent = [(x["user_id"], e["target"], x["tick"]) for x in rows for a, e in zip(x["actions"], x["executed"])
            if a["action"] == "send_message" and e["ok"]]
    pairs = {tuple(sorted((a, b))) for a, b, _ in sent}
    replies = sum(1 for a, b, t in sent if any(a2 == b and b2 == a and t2 < t for a2, b2, t2 in sent))
    c = Counter(a["action"] for x in rows for a, e in zip(x["actions"], x["executed"]) if e["ok"])
    print(f"| {r} | {len(sent)} | {len({a for a, _, _ in sent})} | {len(pairs)} | {replies} | {c['create_group']} | "
          f"{c['join_group']} | {c['send_to_group']} |")
