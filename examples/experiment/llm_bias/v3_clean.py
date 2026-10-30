"""Clean, normalize and aggregate one big-sim part (log 14.60). Run on EVERY run before any analysis. Stdlib only.

    python3 examples/experiment/llm_bias/v3_clean.py data/llm_bias/v3            (part 1; v3_flipped = part 2)

IN PLAIN WORDS
--------------
CLEAN      the raw files hold every screen the AI answered. Kept apart, never mixed into the main tables:
           noise-floor reruns (_d1 files), answers the code could not read ("unreadable"), follow-up screens
           (profiles, searches, opened posts: not a post read). A post the refresh loop brought back is merged into ONE
           post read. Each action is marked "done" (it worked in the world) or "failed" (with why: a comment ID that
           does not exist, liking a post twice, asking for a second screen at once, ...).
NORMALIZE  every count is per 100 posts read, because the cells have different numbers of posts (gemma 99, llama
           119, qwen 102 posts x 99 readers). AI names are short (gemma / llama / qwen).
AGGREGATE  start small, then merge up: each world (reader x posts_by) tick by tick (tick 0 = everyone's first post,
           nobody has commented yet = like V1), then each world all together; every action chosen and done.
GATE       posts SHOWN per cell = posts x 99 (an unreadable answer = shown, not read), and chosen engagement per cell = v3_big_summary.py's published numbers.

Writes <dir>/clean/: reads.csv (one row per post read), followups.csv (one row per follow-up screen), posts.csv (one row
per post written), actions.csv (every chosen action on every screen, with what it took), action_effort.csv
(per reader AI and action: how hard, how often picked, how often it worked), effort_tiers.csv, by_cell_action.csv, by_cell_tick.csv (each world, EVERY tick + all: counts, rates, every action), worlds.md (the
same as tables, baselines first), cleaning.md (what was removed and why, with counts).
"""
import csv, glob, json, os, statistics, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze_v2 as A  # noqa: E402
from v3_big_summary import load, gate  # noqa: E402

D = sys.argv[1]
RD, OUT = os.path.join(D, "r101"), os.path.join(D, "clean")
SHORT = {"gemma3:12b": "gemma", "llama3.1:8b": "llama", "qwen3:8b": "qwen"}
os.makedirs(OUT, exist_ok=True)
# How much an action asks of the AI, from the menu rules (run_v2.MENU) and the live world's screens (live_world.py).
# tier: 0 nothing, 1 one click, 2 pick something on the screen (copy its ID), 3 write text, 4 write a whole post,
# 5 go to another screen first, then write. The answer's optional "reason" is not counted as required text.
EFFORT = {"do_nothing": (0, "nothing")}
EFFORT.update({a: (1, "one click") for a in ("like_post", "unlike_post", "dislike_post", "undo_dislike_post", "repost",
              "refresh", "trend", "follow", "unfollow", "mute", "unmute", "open_messages", "listen_from_group", "back")})
EFFORT.update({a: (2, "pick something on the screen (copy its ID)") for a in ("like_comment", "unlike_comment",
              "dislike_comment", "undo_dislike_comment", "open_post", "join_group", "leave_group")})
EFFORT.update({a: (3, "write text") for a in ("create_comment", "quote_post", "report_post", "search_user", "search_posts",
              "create_group")})
EFFORT.update({"create_post": (4, "write a whole post (subreddit, title, body)"),
               "send_message": (5, "find the person first (a profile or your inbox), then write"),
               "send_to_group": (5, "open group chats and join or make a group first, then write")})
TEXT = ("content", "message", "title", "body", "name", "query")  # the text fields an action needs (+ report_post's reason)
acts_rows = []  # every chosen action on every screen (post screens and follow-ups) of the 9 worlds
log = Counter()  # cleaning counts
why = Counter()  # failed actions on post screens: (reader, action, error)
tries, retry_why = defaultdict(Counter), Counter()  # answers per number of tries; why a try was rejected


def write(name, rows):
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


posts = []
for f in sorted(glob.glob(os.path.join(RD, "posting_*.jsonl"))):
    for r in map(json.loads, filter(str.strip, open(f))):
        for k, a in enumerate(x for x in r["actions"] if x["action"] == "create_post"):
            posts.append({"ai": SHORT[r["model"]], "post_key": f"r101|{r['model'].replace(':', '-')}|u{r['user_id']}|{k}",
                          "user_id": r["user_id"], "topic": r.get("topic", ""), "stance": r.get("stance", ""),
                          "chars": len(a.get("title") or "") + len(a.get("body") or a.get("content") or "")})

reads, follow = [], []
for f in sorted(glob.glob(os.path.join(RD, "reading_*.jsonl"))):
    name = os.path.basename(f)
    rs = [json.loads(l) for l in open(f) if l.strip()]
    if "_d" in name.split("__")[1]:
        log["noise-floor screens (kept out, _d files)"] += len(rs); continue
    com = defaultdict(list)  # this cell's world: post id -> (tick, user) of each comment that worked
    for r in rs:
        for a, e in zip(r["actions"], r.get("executed") or []):
            if a["action"] == "create_comment" and e["ok"]:
                com[e["target"]].append((r["tick"], r["user_id"]))
    visits, fu, at = {}, Counter(), {}
    for r in rs:
        reader, pb = SHORT[r["model"]], SHORT[r["posts_by"]]
        log["raw screens in the 9 world files"] += 1
        tries[reader][r.get("attempts", 1)] += 1
        for e in r.get("errors") or []:
            retry_why[(reader, e.split(" (")[0][:80])] += 1
        if r["outcome"] != "chose":
            where = "post screen" if r.get("screen", "post") == "post" else "follow-up screen"
            log[f"unreadable answers on a {where} (kept out): {reader} reads {pb}"] += 1; continue
        ok = [e["ok"] for e in r["executed"]]
        for x, e in zip(r["actions"], r["executed"]):
            t, _ = EFFORT[x["action"]]  # KeyError = an action missing from EFFORT
            need = TEXT + (("reason",) if x["action"] == "report_post" else ())
            acts_rows.append({"reader": reader, "posts_by": pb, "user_id": r["user_id"], "tick": r["tick"],
                              "screen": r.get("screen", "post"), "step": r.get("step", 0), "action": x["action"], "tier": t,
                              "ok": int(e["ok"]), "why_failed": e.get("error") or "",
                              "text_chars": sum(len(str(x.get(k) or "")) for k in need),
                              "reason_chars": 0 if x["action"] == "report_post" else len(str(x.get("reason") or "")),
                              "actions_in_answer": len(r["actions"]), "answer_tokens": r.get("eval_tokens") or 0,
                              "answer_seconds": r.get("call_latency_s") or r.get("latency_s") or 0})
        if r.get("screen", "post") != "post":
            fu[(r["user_id"], r["tick"])] += 1
            follow.append({"reader": reader, "posts_by": pb, "user_id": r["user_id"], "tick": r["tick"],
                           "screen": r["screen"], "actions": ";".join(a["action"] for a in r["actions"]),
                           "n_chosen": A.n_engage(r), "n_done": sum(o and a["action"] != "do_nothing" for a, o in zip(r["actions"], ok))})
            continue
        for a, e in zip(r["actions"], r["executed"]):
            if not e["ok"]:
                why[(reader, a["action"], e.get("error") or "")] += 1
        k = (r["user_id"], r["post_key"])
        at[(r["user_id"], r["tick"])] = k  # every view, so follow-ups after a refresh return find their post
        if k in visits:
            log["refresh returns merged into the first view"] += 1
            v = visits[k]; v["views"] += 1
        else:
            seen = sum(t < r["tick"] and u != r["user_id"] for t, u in com[r["ctx"]["post"]])
            v = visits[k] = {"reader": reader, "posts_by": pb, "own_ai": int(reader == pb), "user_id": r["user_id"],
                             "post_key": r["post_key"], "author_id": r["author_id"], "topic": r.get("topic", ""),
                             "stance": r.get("stance", ""), "tick": r["tick"], "views": 1, "comments_seen": seen,
                             "followup_screens": 0, "chosen": [], "done": []}
        v["chosen"] += [a["action"] for a in r["actions"]]
        v["done"] += [a["action"] for a, o in zip(r["actions"], ok) if o]
    for (u, t), n in fu.items():
        visits[at[(u, t)]]["followup_screens"] += n  # KeyError = a follow-up screen with no post screen at its tick
    for v in visits.values():
        ch, dn = v.pop("chosen"), v.pop("done")
        v.update({"actions_chosen": ";".join(ch), "actions_failed": ";".join((Counter(ch) - Counter(dn)).elements()),
                  "n_chosen": sum(a != "do_nothing" for a in ch), "n_done": sum(a != "do_nothing" for a in dn),
                  "upvoted": int("like_post" in ch), "upvoted_done": int("like_post" in dn),
                  "downvoted": int("dislike_post" in ch), "commented": int("create_comment" in ch),
                  "did_nothing": int(not any(a != "do_nothing" for a in ch))})
        v["followup_screens"] = v.pop("followup_screens")  # keep it as the last column
        reads.append(v)

# GATE (B-34): reproduce the published numbers before anything new
rows, extra = load(D)
gate(rows, extra)
pub = defaultdict(list)
for r in rows:
    if r["turn"] == "read" and r["outcome"] == "chose" and not r["draw"]:
        pub[(SHORT[r["model"]], SHORT[r["posts_by"]])].append(A.n_engage(r))
cell = defaultdict(list)
for v in reads:
    cell[(v["reader"], v["posts_by"])].append(v)
for c, vs in cell.items():
    assert len(vs) == len(pub[c]) and sum(v["n_chosen"] for v in vs) == sum(pub[c]), f"{c}: clean != published"
    assert sum(v["followup_screens"] for v in vs) == sum(1 for x in follow if (x["reader"], x["posts_by"]) == c), c

topic = {v["post_key"]: v["topic"] for v in reads}  # posting rows carry no topic; the read rows do
for p in posts:
    p["topic"] = topic.get(p["post_key"], "")
    del p["stance"]
write("reads.csv", reads); write("followups.csv", follow); write("posts.csv", posts)
write("actions.csv", acts_rows)

# effort per action, per reader AI (its 3 worlds together): how hard, how often picked, how often it worked
med = lambda xs: round(float(statistics.median(xs)), 1) if xs else ""  # noqa: E731
eff = []
for m in sorted({x["reader"] for x in acts_rows}):
    n = sum(len(vs) for (mm, _), vs in cell.items() if mm == m)
    mine = [x for x in acts_rows if x["reader"] == m]
    for a in sorted({x["action"] for x in mine}, key=lambda a: (EFFORT[a][0], a)):
        xs = [x for x in mine if x["action"] == a]
        solo = [x for x in xs if x["actions_in_answer"] == 1]
        ok = [x for x in xs if x["ok"]]
        eff.append({"reader": m, "action": a, "tier": EFFORT[a][0], "what it takes": EFFORT[a][1], "posts read": n,
                    "chosen": len(xs), "done": len(ok), "failed %": round(100 * (len(xs) - len(ok)) / len(xs), 1),
                    "chosen per 100 posts read": round(100 * len(xs) / n, 2),
                    "% chosen on the post screen": round(100 * sum(x["screen"] == "post" for x in xs) / len(xs), 1),
                    "median screens in (0 = post screen)": med([x["step"] for x in ok]),
                    "median text written (chars)": med([x["text_chars"] for x in xs]),
                    "answers with only this action": len(solo),
                    "median answer tokens (only this action)": med([x["answer_tokens"] for x in solo]),
                    "median answer seconds (only this action)": med([x["answer_seconds"] for x in solo])})
write("action_effort.csv", eff)
tiers = []
for m in sorted({x["reader"] for x in acts_rows}):
    mine = [x for x in acts_rows if x["reader"] == m and x["tier"] > 0]
    for t in range(1, 6):
        xs = [x for x in mine if x["tier"] == t]
        tiers.append({"reader": m, "tier": t, "what it takes": next(w for tt, w in EFFORT.values() if tt == t),
                      "chosen": len(xs), "% of all actions chosen": round(100 * len(xs) / len(mine), 1),
                      "done": sum(x["ok"] for x in xs), "failed %": round(100 * sum(not x["ok"] for x in xs) / len(xs), 1) if xs else ""})
write("effort_tiers.csv", tiers)
acts = sorted({a for v in reads for a in v["actions_chosen"].split(";") if a})
agg = []
for (m, pb), vs in sorted(cell.items()):
    ch = Counter(a for v in vs for a in v["actions_chosen"].split(";") if a)
    dn = Counter(ch) - Counter(a for v in vs for a in v["actions_failed"].split(";") if a)
    agg += [{"reader": m, "posts_by": pb, "action": a, "posts_read": len(vs), "chosen": ch[a], "done": dn[a],
             "chosen_per_100": round(100 * ch[a] / len(vs), 2), "done_per_100": round(100 * dn[a] / len(vs), 2)} for a in acts]
write("by_cell_action.csv", agg)
COLS = [("posts read", None), ("actions chosen", "n_chosen"), ("actions done", "n_done"), ("upvoted", "upvoted"),
        ("downvoted", "downvoted"), ("commented", "commented"), ("did nothing", "did_nothing"),
        ("comments on screen", "comments_seen"), ("follow-up screens", "followup_screens")]


def tally(s):
    """Raw counts for a group of posts read, then the main rates (per 100 posts read / % of posts read)."""
    t = {c: (len(s) if k is None else sum(v[k] for v in s)) for c, k in COLS}
    n = len(s)
    t.update({"engagement per 100": round(100 * t["actions chosen"] / n, 1), "done per 100": round(100 * t["actions done"] / n, 1),
              "upvoted %": round(100 * t["upvoted"] / n, 1), "commented %": round(100 * t["commented"] / n, 1)})
    return t


WORLDS = sorted(cell, key=lambda c: (c[0] != c[1], c))  # the 3 baselines (an AI reading its own AI's posts) first
agg = []
for m, pb in WORLDS:
    vs = cell[(m, pb)]
    for t in sorted({v["tick"] for v in vs}) + ["all"]:
        s = vs if t == "all" else [v for v in vs if v["tick"] == t]
        agg.append({"reader": m, "posts_by": pb, "tick": t, **tally(s),
                     **Counter(a for v in s for a in v["actions_chosen"].split(";") if a)})
keys = list(agg[0]) + sorted({k for r in agg for k in r} - set(agg[0]))
agg = [{k: r.get(k, 0) for k in keys} for r in agg]
write("by_cell_tick.csv", agg)  # one row per world per tick, plus "all"; every action as its own count column

with open(os.path.join(OUT, "worlds.md"), "w") as f:
    f.write(f"# Every world, tick by tick: {D}\n\nA world = one reader AI playing all 100 users, reading one AI's posts. "
            "Tick 0 = each user's first post (no comments anywhere yet, like V1); one tick = every user reads one more post. "
            "Counts first, then rates. Baselines (an AI reading its own AI's posts) first.\n")
    head = [c for c, _ in COLS] + ["engagement per 100", "done per 100", "upvoted %", "commented %"]
    for m, pb in WORLDS:
        f.write(f"\n## {m} reads {pb}'s posts" + (" (baseline)" if m == pb else "") + "\n\n| tick | " + " | ".join(head)
                + " |\n" + "|---" * (len(head) + 1) + "|\n")
        for r in agg:
            if (r["reader"], r["posts_by"]) == (m, pb):
                f.write(f"| {'**all**' if r['tick'] == 'all' else r['tick']} | " + " | ".join(f"{r[h]:,}" for h in head) + " |\n")

with open(os.path.join(OUT, "cleaning.md"), "w") as f:
    f.write(f"# Cleaning report: {D}\n\nGATE OK: posts shown per cell = posts x 99 (unreadable answers count as shown, not read); chosen engagement = v3_big_summary.py.\n\n")
    f.write("| step | screens |\n|---|---|\n" + "".join(f"| {k} | {v:,} |\n" for k, v in log.items()))
    f.write(f"| follow-up screens (kept apart: followups.csv) | {len(follow):,} |\n| posts read (reads.csv) | {len(reads):,} |\n\n"
            f"Check: raw screens = posts read + refresh returns + unreadable + follow-up screens: {log['raw screens in the 9 world files']:,} = "
            f"{len(reads):,} + {log['refresh returns merged into the first view']:,} + "
            f"{sum(v for k, v in log.items() if k.startswith('unreadable')):,} + {len(follow):,}\n\n")
    assert log["raw screens in the 9 world files"] == len(reads) + log["refresh returns merged into the first view"] + len(follow) + sum(
        v for k, v in log.items() if k.startswith("unreadable")), "screens lost in cleaning"
    f.write("## Answers that needed more than one try (the first answer broke a rule, so the AI was asked again with a new "
            "seed; after 3 tries it counts as unreadable)\n\n| reader | answers | 1 try | 2 tries | 3 tries | % retried |\n|---|---|---|---|---|---|\n")
    for m in sorted(tries):
        t = tries[m]; n = sum(t.values())
        f.write(f"| {m} | {n:,} | {t[1]:,} | {t[2]:,} | {t[3]:,} | {100 * (n - t[1]) / n:.1f} |\n")
    f.write("\n| reader | why a try was rejected | times |\n|---|---|---|\n")
    f.write("".join(f"| {m} | {e} | {n:,} |\n" for (m, e), n in sorted(retry_why.items(), key=lambda kv: (kv[0][0], -kv[1])) if n >= 5))
    f.write("\n")
    f.write("## Actions on post screens that failed in the world (chosen, not done)\n\n| reader | action | why | count |\n|---|---|---|---|\n")
    f.write("".join(f"| {m} | {a} | {e} | {n:,} |\n" for (m, a, e), n in why.most_common()))
    f.write("\n## Engagement per 100 posts read: chosen (every action the AI gave) vs done (only actions that worked)\n\n"
            "| reader | posts by | posts read | chosen | done | % failed |\n|---|---|---|---|---|---|\n")
    for (m, pb), vs in sorted(cell.items()):
        c, d = sum(v["n_chosen"] for v in vs), sum(v["n_done"] for v in vs)
        f.write(f"| {m} | {pb} | {len(vs):,} | {100 * c / len(vs):.1f} | {100 * d / len(vs):.1f} | {100 * (c - d) / c:.1f} |\n")
print(open(os.path.join(OUT, "cleaning.md")).read())
print(f"wrote {OUT}/: reads.csv ({len(reads):,}), followups.csv ({len(follow):,}), posts.csv ({len(posts)}), "
      "by_cell_action.csv, by_cell_tick.csv, worlds.md, cleaning.md, actions.csv "
      f"({len(acts_rows):,}), action_effort.csv, effort_tiers.csv")
