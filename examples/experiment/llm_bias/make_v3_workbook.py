"""One Excel workbook for the V3 big sim, built from the cleaned data (v3_clean.py; log 14.60).

    oasis-env/bin/python examples/experiment/llm_bias/make_v3_workbook.py <out.xlsx> data/llm_bias/v3 [data/llm_bias/v3_flipped]

Part 1 alone now; give part 2's folder too (after `v3_clean.py data/llm_bias/v3_flipped`) and every summary sheet gets
part 2's numbers next to part 1's plus the change. Sheets, small to big: Read me, Cleaning, one sheet per world tick by
tick (baselines first), Worlds (each world all together), Actions (every action per world), Posts (each post), Users
(each reader user per world), Reads (every post read, one row each) and Follow-ups (every follow-up screen) for part 1
(and part 2). Numbers are plain values computed from the clean CSVs; filter the Reads sheet to check any of them.
"""
import csv, os, sys
from collections import Counter, defaultdict

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

OUT, DIRS = sys.argv[1], sys.argv[2:]
PART = ["part 1", "part 2"][:len(DIRS)]
F, FB = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True)
HEAD, BASE = PatternFill("solid", start_color="DDE3EA"), PatternFill("solid", start_color="FFF4D6")
NUM = lambda v: int(v) if str(v).lstrip("-").isdigit() else float(v) if v.replace(".", "", 1).lstrip("-").isdigit() else v  # noqa: E731


def rows(d, name):
    return [{k: NUM(v) for k, v in r.items()} for r in csv.DictReader(open(os.path.join(d, "clean", name)))]


data = [{n: rows(d, n + ".csv") for n in ("reads", "followups", "posts", "by_cell_tick", "by_cell_action", "action_effort",
                                          "effort_tiers")} for d in DIRS]
WORLDS = sorted({(r["reader"], r["posts_by"]) for r in data[0]["reads"]}, key=lambda c: (c[0] != c[1], c))
wb = Workbook()


def sheet(title, head, body, widths=None, note=None, base_col=None):
    ws = wb.create_sheet(title)
    r0 = 1
    if note:
        ws.cell(1, 1, note).font = FB
        r0 = 3
    for j, h in enumerate(head, 1):
        c = ws.cell(r0, j, h)
        c.font, c.fill, c.alignment = FB, HEAD, Alignment(wrap_text=True, vertical="top")
    for i, row in enumerate(body, r0 + 1):
        for j, v in enumerate(row, 1):
            ws.cell(i, j, v).font = F
        if base_col is not None and row[base_col[0]] == row[base_col[1]]:
            for j in range(1, len(row) + 1):
                ws.cell(i, j).fill = BASE
    for j in range(1, len(head) + 1):
        ws.column_dimensions[get_column_letter(j)].width = (widths or {}).get(j, 12)
    ws.freeze_panes = ws.cell(r0 + 1, 2)
    ws.auto_filter.ref = f"A{r0}:{get_column_letter(len(head))}{r0 + len(body)}"
    return ws


# Read me
ws = wb.active
ws.title = "Read me"
TEXT = [
    ("V3 big sim, cleaned data", ""),
    ("Parts in this file", ", ".join(f"{p} = {d}" for p, d in zip(PART, DIRS))),
    ("", ""),
    ("WORDS", ""),
    ("world", "One reader AI playing all 100 users, reading the posts one AI wrote. 3 reader AIs x 3 post writers = 9 worlds. "
              "Each world is separate: nothing in one world is seen in another."),
    ("baseline", "A world where the AI reads posts its own AI wrote (gemma reads gemma's posts, ...). Shaded yellow."),
    ("tick", "Everyone scrolls at the same pace. At tick 0 each user reads the first post of their own scroll, at tick 1 the "
             "second, and so on. Users see comments other users left in EARLIER ticks. Tick 0 = nobody has commented yet, like V1."),
    ("post read", "One user reading one post. If the user pressed refresh and the post came back, both looks count as ONE post read."),
    ("actions chosen", "Every action the AI gave in its answer, except 'do nothing'. This is total engagement, the main measure."),
    ("actions done", "Only the chosen actions that worked in the world. An action fails when, e.g., it likes a comment ID that does "
                     "not exist, likes the same post twice, or asks to open a second screen while one is open."),
    ("upvoted / downvoted / commented", "Number of posts read where the AI upvoted (like_post) / downvoted / wrote a comment."),
    ("did nothing", "Posts read where the AI's only answer was 'do nothing'."),
    ("comments on screen", "Comments by other users that were on the screen when the post was read (added up over the posts read)."),
    ("follow-up screen", "A screen the user opened from the post: a profile, a search, an opened post, messages. Not a post read; "
                         "kept apart (Follow-ups sheet)."),
    ("per 100 / %", "Divided by posts read. The worlds have different numbers of posts (gemma 99, llama 119, qwen 102 posts, each "
                    "read by 99 users), so compare rates between worlds, counts within one world."),
    ("", ""),
    ("SHEETS, SMALL TO BIG", ""),
    ("Cleaning", "What was kept out of the main tables and why, with counts; every failed action and why it failed."),
    ("one sheet per world", "Tick by tick, then 'all' (the whole world). Counts first, then rates."
                            + (" Part 2 next to part 1, then the change (part 2 minus part 1)." if len(DIRS) > 1 else "")),
    ("Worlds", "Each world all together (the 'all' rows of the world sheets side by side)."),
    ("Actions", "Every action, per world: how many times chosen and done, and per 100 posts read."),
    ("Effort tiers / Action effort", "How much each action asks of the AI (one click, copy an ID, write text, write a post, "
                                     "go to another screen first) and how often each AI picks it, how often it fails, how "
                                     "long the answer is and how long it takes. Every chosen action on every screen is in "
                                     "clean/actions.csv (too big for this file)."),
    ("Posts", "Each post: who wrote it, topic, length, and in each world that read it: times read, upvoted, downvoted, commented."),
    ("Users", "Each user in each world: posts read, actions, upvotes, comments, follow-up screens."),
    ("Reads / Follow-ups", "Every post read and every follow-up screen, one row each. Filter these to check any number in the file."),
    ("", ""),
    ("Source", "v3_clean.py writes <part>/clean/*.csv from the raw files in <part>/r101/; make_v3_workbook.py builds this file. "
               "v3_clean.py checks its numbers against the published ones before writing (log 14.53, 14.60)."),
]
for i, (a, b) in enumerate(TEXT, 1):
    ws.cell(i, 1, a).font = Font(name="Arial", size=13, bold=True) if i == 1 else FB
    ws.cell(i, 2, b).font = F
    ws.cell(i, 2).alignment = Alignment(wrap_text=True, vertical="top")
ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 28, 120

# Cleaning (the markdown report, table by table)
for p, d in zip(PART, DIRS):
    lines = [l.rstrip("\n") for l in open(os.path.join(d, "clean", "cleaning.md"))]
    ws = wb.create_sheet(f"Cleaning {p}" if len(DIRS) > 1 else "Cleaning")
    r = 1
    for l in lines:
        if l.startswith("|---"):
            continue
        cells = [c.strip() for c in l.strip("|").split("|")] if l.startswith("|") else [l.lstrip("# ")]
        for j, c in enumerate(cells, 1):
            ws.cell(r, j, NUM(c.replace(",", "")) if l.startswith("|") else c).font = FB if not l.startswith("|") or r == 1 else F
        r += 1
    for j, w in enumerate((70, 22, 40, 12, 12, 12), 1):
        ws.column_dimensions[get_column_letter(j)].width = w

# one sheet per world, tick by tick
COUNTS = ["posts read", "actions chosen", "actions done", "upvoted", "downvoted", "commented", "did nothing",
          "comments on screen", "follow-up screens"]
RATES = ["engagement per 100", "done per 100", "upvoted %", "commented %"]
tick = [{(r["reader"], r["posts_by"], r["tick"]): r for r in x["by_cell_tick"]} for x in data]
for m, pb in WORLDS:
    ticks = sorted({t for tk in tick for (a, b, t) in tk if (a, b) == (m, pb) and t != "all"}) + ["all"]
    head = ["tick"] + [f"{p}: {c}" for p in PART for c in COUNTS + RATES]
    if len(DIRS) > 1:
        head += [f"change: {c}" for c in RATES]
    body = []
    for t in ticks:
        got = [tk.get((m, pb, t)) for tk in tick]
        row = [t] + [g[c] if g else None for g in got for c in COUNTS + RATES]
        if len(DIRS) > 1:
            row += [round(got[1][c] - got[0][c], 1) if all(got) else None for c in RATES]
        body.append(row)
    title = f"{m} reads {pb}" + (" (base)" if m == pb else "")
    sheet(title, head, body, {1: 8},
          note=f"{m} plays all 100 users, reading the {sum(1 for x in data[0]['posts'] if x['ai'] == pb)} posts {pb} wrote"
               + (" (baseline: its own AI's posts)" if m == pb else "") + ". One row per tick; last row = the whole world.")

# Worlds: each world all together
head = ["reader", "posts by"] + [f"{p}: {c}" for p in PART for c in COUNTS + RATES]
if len(DIRS) > 1:
    head += [f"change: {c}" for c in RATES]
body = []
for m, pb in WORLDS:
    got = [tk[(m, pb, "all")] for tk in tick]
    row = [m, pb] + [g[c] for g in got for c in COUNTS + RATES]
    if len(DIRS) > 1:
        row += [round(got[1][c] - got[0][c], 1) for c in RATES]
    body.append(row)
sheet("Worlds", head, body, {1: 9, 2: 9}, note="Each world all together (baselines first, shaded).", base_col=(0, 1))

# Actions
acts = sorted({r["action"] for x in data for r in x["by_cell_action"]})
act = [{(r["reader"], r["posts_by"], r["action"]): r for r in x["by_cell_action"]} for x in data]
head = ["reader", "posts by", "action"] + [f"{p}: {c}" for p in PART for c in ("chosen", "done", "failed", "chosen per 100", "done per 100")]
body = []
for m, pb in WORLDS:
    for a in acts:
        row = [m, pb, a]
        for ak in act:
            r = ak.get((m, pb, a), {"chosen": 0, "done": 0, "chosen_per_100": 0, "done_per_100": 0})
            row += [r["chosen"], r["done"], r["chosen"] - r["done"], r["chosen_per_100"], r["done_per_100"]]
        body.append(row)
sheet("Actions", head, body, {1: 9, 2: 9, 3: 22}, note="Every action in every world. Filter 'action' to compare one action across worlds.",
      base_col=(0, 1))

# How hard each action is, and how often each AI picks it (per reader AI, its 3 worlds together)
for p, x in zip(PART, data):
    t = x["effort_tiers"]
    sheet("Effort tiers" + (f" {p}" if len(DIRS) > 1 else ""), list(t[0]), [list(r.values()) for r in t], {3: 50},
          note="Each AI's actions (do nothing left out) by how much the action asks: 1 one click ... 5 go to another "
               "screen first, then write. Do the AIs pick the easy ones?")
    e = x["action_effort"]
    sheet("Action effort" + (f" {p}" if len(DIRS) > 1 else ""), list(e[0]), [list(r.values()) for r in e], {2: 20, 4: 40},
          note="Every action each AI chose, on every screen. Answer tokens / seconds: answers that held only this "
               "action (seconds = time for one answer while 8 run at once; compare within one AI).")

# Posts: each post, and what each world did with it
for p, x in zip(PART, data):
    by = defaultdict(Counter)
    for r in x["reads"]:
        c = by[(r["post_key"], r["reader"])]
        c["read"] += 1; c["up"] += r["upvoted"]; c["down"] += r["downvoted"]; c["com"] += r["commented"]; c["act"] += r["n_chosen"]
    readers = sorted({r["reader"] for r in x["reads"]})
    head = ["post", "written by AI", "writer user", "topic", "characters"] + [
        f"{m}: {c}" for m in readers for c in ("times read", "upvoted", "downvoted", "commented", "actions", "upvoted %")]
    body = []
    for q in x["posts"]:
        row = [q["post_key"], q["ai"], q["user_id"], q["topic"], q["chars"]]
        for m in readers:
            c = by[(q["post_key"], m)]
            row += [c["read"], c["up"], c["down"], c["com"], c["act"], round(100 * c["up"] / c["read"], 1) if c["read"] else None]
        body.append(row)
    sheet("Posts" + (f" {p}" if len(DIRS) > 1 else ""), head, body, {1: 24, 4: 16},
          note="Each post (the same posts in both parts). Every post is read by 99 users in each of the 3 reader worlds.")

# Users: each reader user in each world
for p, x in zip(PART, data):
    by = defaultdict(Counter)
    for r in x["reads"]:
        c = by[(r["reader"], r["posts_by"], r["user_id"])]
        c["read"] += 1; c["act"] += r["n_chosen"]; c["done"] += r["n_done"]; c["up"] += r["upvoted"]; c["down"] += r["downvoted"]
        c["com"] += r["commented"]; c["fu"] += r["followup_screens"]
    head = ["reader", "posts by", "user", "posts read", "actions chosen", "actions done", "upvoted", "downvoted", "commented",
            "follow-up screens", "engagement per 100", "upvoted %"]
    body = [[m, pb, u, c["read"], c["act"], c["done"], c["up"], c["down"], c["com"], c["fu"],
             round(100 * c["act"] / c["read"], 1), round(100 * c["up"] / c["read"], 1)]
            for (m, pb, u), c in sorted(by.items(), key=lambda kv: (WORLDS.index(kv[0][:2]), kv[0][2]))]
    sheet("Users" + (f" {p}" if len(DIRS) > 1 else ""), head, body, {1: 9, 2: 9}, base_col=(0, 1),
          note="Each user (the same 100 people in every world, each played by the world's reader AI).")

# every row
for p, x in zip(PART, data):
    for name, key in (("Reads", "reads"), ("Follow-ups", "followups")):
        rs = x[key]
        sheet(name + (f" {p}" if len(DIRS) > 1 else ""), list(rs[0]), [list(r.values()) for r in rs], {5: 24, 12: 30, 13: 20})

wb.save(OUT)
print(f"wrote {OUT}: {len(wb.sheetnames)} sheets: {', '.join(wb.sheetnames)}")
