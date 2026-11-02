"""The V3 Excel file: V3 vs V3a first, then V1 vs V3; tables with their charts next to them (log 14.62).

    python3 examples/experiment/llm_bias/v3_report_data.py data/llm_bias/v3_report.json     (first: every number)
    oasis-env/bin/python examples/experiment/llm_bias/make_v3_workbook.py <out.xlsx> data/llm_bias/v3 data/llm_bias/v3_flipped

V3 = big sim part 1 (V1's action-list order); V3a = part 2 (the same posts and users, the list ranked from V3's own
choices); V1 = round 101 (round 102 alongside where it helps). "No timeline" = tick 0 (each user's first post, nobody
has commented yet). Numbers come from v3_report.json (the same file the data page uses), the detail sheets from each
run's clean/ folder. Charts are matplotlib images placed next to their tables (as make_v3_charts.py does).
"""
import csv, io, json, os, sys
from collections import Counter, defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_v2 as R  # noqa: E402

OUT, DIRS = sys.argv[1], sys.argv[2:4]
REPORT = json.load(open(os.path.join(HERE, "../../../data/llm_bias/v3_report.json")))
USERNAME = {p["id"]: p["username"] for p in R.load_personas()[:100]}
AIS = ["gemma", "llama", "qwen"]
STANCES = ["LOVE", "LIKE", "NEUTRAL", "DISLIKE", "HATE"]
COLOR = {"V3": "#6250d6", "V3a": "#eda100", "V3 tick 0": "#6250d6", "V3a tick 0": "#eda100", "V1": "#8a8f98", "V1 r102": "#b4b2ab"}
NAME = {"V3": "V3", "V3a": "V3a (reordered)", "V3 tick 0": "V3 tick 0", "V3a tick 0": "V3a tick 0", "V1": "V1 r101", "V1 r102": "V1 r102"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
F, FB, FT = Font(name="Arial", size=10), Font(name="Arial", size=10, bold=True), Font(name="Arial", size=14, bold=True)
HEAD, BASE = PatternFill("solid", start_color="DDE3EA"), PatternFill("solid", start_color="FFF4D6")
NOTE = Font(name="Arial", size=10, italic=True, color="52514E")
NUM = lambda v: int(v) if str(v).lstrip("-").isdigit() else float(v) if str(v).replace(".", "", 1).lstrip("-").isdigit() else v  # noqa: E731
wb = Workbook()


def sheet(title, note, head, body, widths=None, base=None, chart=None):
    """A tidy table: title + one-line note, a header row, the rows; optional chart image to the right."""
    ws = wb.create_sheet(title[:31])
    ws.cell(1, 1, title).font = FT
    ws.cell(2, 1, note).font = NOTE
    for j, h in enumerate(head, 1):
        c = ws.cell(4, j, h)
        c.font, c.fill, c.alignment = FB, HEAD, Alignment(wrap_text=True, vertical="top")
    for i, row in enumerate(body, 5):
        for j, v in enumerate(row, 1):
            ws.cell(i, j, v).font = F
        if base and base(row):
            for j in range(1, len(row) + 1):
                ws.cell(i, j).fill = BASE
    for j in range(1, len(head) + 1):
        ws.column_dimensions[get_column_letter(j)].width = (widths or {}).get(j, 12)
    ws.row_dimensions[4].height = 42
    ws.freeze_panes = "A5"
    if body:
        ws.auto_filter.ref = f"A4:{get_column_letter(len(head))}{4 + len(body)}"
    if chart:
        place(ws, chart, f"{get_column_letter(len(head) + 2)}4")
    return ws


def place(ws, buf, cell):
    img = Image(buf)
    img.width, img.height = img.width * 0.5, img.height * 0.5
    ws.add_image(img, cell)


def png(fig):
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def bars(groups, runs, values, title, ylabel):
    """Grouped bars: one group per label, one bar per run, values[(group, run)]; value labels on top."""
    fig, ax = plt.subplots(figsize=(max(7.5, 0.55 * len(groups) * len(runs)), 3.6))
    w = 0.8 / len(runs)
    for k, r in enumerate(runs):
        xs = [i + (k - (len(runs) - 1) / 2) * w for i in range(len(groups))]
        vs = [values.get((g, r)) or 0 for g in groups]
        ax.bar(xs, vs, w * 0.92, color=COLOR[r], label=NAME[r])
        for x, v in zip(xs, vs):
            ax.text(x, v, f"{v:.0f}", ha="center", va="bottom", fontsize=7, color=INK2)
    ax.set_xticks(range(len(groups)), groups, fontsize=8)
    ax.set_title(title, loc="left", fontsize=10, color=INK)
    ax.set_ylabel(ylabel, fontsize=8, color=INK2)
    ax.legend(frameon=False, fontsize=8)
    style(ax)
    return png(fig)


def pick(run, ai=None, pb=None):
    return REPORT["total"][run] if ai is None else REPORT["reader"][f"{run}|{ai}"] if pb is None else REPORT["world"][f"{run}|{ai}|{pb}"]


MAIN = [("posts read", "posts read"), ("actions per 100", "total engagement: actions per 100 posts read"),
        ("% engaged", "% of posts with at least one real action"), ("% upvoted", "% upvoted"), ("% downvoted", "% downvoted"),
        ("% commented", "% commented"), ("% chose do_nothing", "% answered do_nothing only"), ("% empty answer", "% answered an empty list [] only")]


def summary(title, note, runs, chart_runs):
    head = ["reader AI", "measure"] + [NAME[r] for r in runs] + [f"change: {NAME[runs[1]]} - {NAME[runs[0]]} (points)"]
    body = []
    for ai in AIS + [None]:
        for k, label in MAIN:
            v = [pick(r, ai)[k] for r in runs]
            body.append([ai or "all three", label] + v + [None if k == "posts read" else round(v[1] - v[0], 1)])
    ws = sheet(title, note, head, body, {1: 12, 2: 44},
               chart=bars(AIS, chart_runs, {(ai, r): pick(r, ai)["actions per 100"] for ai in AIS for r in chart_runs},
                          "Total engagement (actions per 100 posts read)", "per 100"))
    place(ws, bars(AIS, chart_runs, {(ai, r): pick(r, ai)["% upvoted"] for ai in AIS for r in chart_runs}, "% of posts upvoted", "%"),
          f"{get_column_letter(len(head) + 2)}26")


def actions_sheet(title, note, runs):
    head = ["reader AI", "action"] + [f"{NAME[r]}: % of posts" for r in runs] + [f"{NAME[r]}: times per 100" for r in runs] + \
        [f"change % ({NAME[runs[1]]} - {NAME[runs[0]]}, points)"]
    body, top = [], {}
    for ai in AIS:
        acts = sorted(REPORT["actions"], key=lambda a: -sum(pick(r, ai)["actions"][a]["% of posts"] for r in runs))
        for a in acts:
            p = [pick(r, ai)["actions"][a]["% of posts"] for r in runs]
            if any(pick(r, ai)["actions"][a]["times"] for r in runs):
                body.append([ai, a] + p + [pick(r, ai)["actions"][a]["per 100"] for r in runs] + [round(p[1] - p[0], 1)])
        top[ai] = acts[:6]
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.8))
    for ax, ai in zip(axs, AIS):
        acts = top[ai]
        for k, r in enumerate(runs[:2]):
            ys = [i + (k - 0.5) * 0.4 for i in range(len(acts))]
            vs = [pick(r, ai)["actions"][a]["% of posts"] for a in acts]
            ax.barh(ys, vs, 0.37, color=COLOR[r], label=NAME[r])
            for y, v in zip(ys, vs):
                ax.text(v + 1, y, f"{v:.0f}", va="center", fontsize=6.5, color=INK2)
        ax.set_yticks(range(len(acts)), acts, fontsize=7.5)
        ax.invert_yaxis()
        ax.set_xlim(0, 110)
        ax.set_title(f"{ai} reading: top actions (% of posts)", fontsize=9, loc="left")
        style(ax)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=GRID)
    axs[0].legend(frameon=False, fontsize=7.5, loc="lower right")
    sheet(title, note, head, body, {1: 10, 2: 22}, chart=png(fig))


def worlds_sheet(title, note, runs):
    K = [("actions per 100", "actions per 100"), ("% engaged", "% engaged"), ("% upvoted", "% upvoted"), ("% downvoted", "% downvoted"),
         ("% commented", "% commented"), ("comments seen per post", "comments on screen per post")]
    head = ["reader AI", "posts by"] + [f"{NAME[r]}: {t}" for _, t in K for r in runs] + [f"change: {t}" for _, t in K]
    order = [(a, a) for a in AIS] + [(m, pb) for m in AIS for pb in AIS if m != pb]
    body = [[m, pb] + [pick(r, m, pb)[k] for k, _ in K for r in runs] + [round(pick(runs[1], m, pb)[k] - pick(runs[0], m, pb)[k], 1) for k, _ in K]
            for m, pb in order]
    labels = [f"{m}\n→{pb}" for m, pb in order]
    sheet(title, note, head, body, {1: 10, 2: 10}, base=lambda row: row[0] == row[1],
          chart=bars(labels, runs, {(f"{m}\n→{pb}", r): pick(r, m, pb)["% upvoted"] for m, pb in order for r in runs},
                     "% upvoted in each world (reader → whose posts)", "%"))


def stance_sheet(title, note, runs):
    K = ["% engaged", "% upvoted", "% downvoted", "% commented", "actions per 100"]
    head = ["reader AI", "user feels"] + [f"{NAME[r]}: posts read" for r in runs] + [f"{NAME[r]}: {k}" for k in K for r in runs] + [f"change: {k}" for k in K]
    body = []
    for ai in AIS:
        for s in STANCES:
            x = [REPORT["stance"][f"{r}|{ai}|{s}"] for r in runs]
            body.append([ai, s] + [v["posts read"] for v in x] + [v[k] for k in K for v in x] + [round(x[1][k] - x[0][k], 1) for k in K])
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.4), sharey=True)
    for ax, ai in zip(axs, AIS):
        for r in runs:
            ax.plot(STANCES, [REPORT["stance"][f"{r}|{ai}|{s}"]["% upvoted"] for s in STANCES], marker="o", color=COLOR[r], label=NAME[r], lw=2, ms=5)
        ax.set_title(f"{ai} reading: % upvoted by feeling", fontsize=9, loc="left")
        ax.set_ylim(0, 105)
        style(ax)
    axs[0].legend(frameon=False, fontsize=7.5)
    sheet(title, note, head, body, {1: 10, 2: 11}, chart=png(fig))


def bias_sheet(title, note, runs):
    head = ["run", "pair (i vs j)", "measure", "i on i's posts", "j on i's posts", "gap 1 (i on i - j on i)", "i on j's posts",
            "j on j's posts", "gap 2 (i on j - j on j)", "favouritism = gap 1 - gap 2 (points)", "95% low", "95% high", "clear?"]
    body = []
    for r in runs:
        for b in REPORT["bias"][r]:
            body.append([NAME[r], b["pair"], b["measure"], b["i on i"], b["j on i"], round(b["i on i"] - b["j on i"], 1), b["i on j"],
                         b["j on j"], round(b["i on j"] - b["j on j"], 1), b["bias"], b["low"], b["high"], "CLEAR" if b["clear"] else "no"])
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.6))
    shade = {r: c for r, c in zip(runs, ["#6250d6", "#eda100", "#a59ae8", "#f3c766"] if runs[0] == "V3" else ["#8a8f98", "#b4b2ab", "#6250d6", "#a59ae8"])}
    for ax, meas in zip(axs, ("upvoted %", "actions per 100")):
        pairs = [b["pair"] for b in REPORT["bias"][runs[0]] if b["measure"] == meas]
        for k, r in enumerate(runs):
            bs = [b for b in REPORT["bias"][r] if b["measure"] == meas]
            xs = [i + (k - (len(runs) - 1) / 2) * (0.8 / len(runs)) for i in range(len(pairs))]
            ax.errorbar(xs, [b["bias"] for b in bs], yerr=[[b["bias"] - b["low"] for b in bs], [b["high"] - b["bias"] for b in bs]],
                        fmt="o", color=shade[r], label=NAME[r], ms=5, capsize=3, lw=1.5)
        ax.axhline(0, color=INK2, lw=1)
        ax.set_xticks(range(len(pairs)), pairs, fontsize=8)
        ax.set_title(f"Own-AI favouritism, {meas} (dot = value, bar = 95% range)", fontsize=9, loc="left")
        style(ax)
    axs[0].legend(frameon=False, fontsize=7.5)
    sheet(title, note, head, body, {1: 16, 2: 16, 3: 14}, chart=png(fig))


TK = ("actions per 100", "% upvoted", "% downvoted", "% commented", "% like_comment", "comments seen per post")


def ticks_sheet(title, note):
    head = ["reader AI", "posts by", "tick", "V3: posts read", "V3a: posts read"] + [f"{run}: {k}" for k in TK for run in ("V3", "V3a")]
    body, T = [], REPORT["tick"]
    g = lambda v, k: v[k] if v else None  # noqa: E731
    for m in AIS:
        for pb in AIS:
            for t in range(140):
                x = [T.get(f"{r}|{m}|{pb}|{t}") for r in ("V3", "V3a")]
                if any(x):
                    body.append([m, pb, t, g(x[0], "posts read"), g(x[1], "posts read")] + [g(v, k) for k in TK for v in x])
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.4), sharey=True)
    for ax, m in zip(axs, AIS):
        for r in ("V3", "V3a"):
            pts = defaultdict(lambda: [0, 0])  # tick -> [upvoted posts, posts read], the 3 piles together
            for pb in AIS:
                for t in range(140):
                    x = T.get(f"{r}|{m}|{pb}|{t}")
                    if x:
                        pts[t][0] += x["% upvoted"] * x["posts read"] / 100
                        pts[t][1] += x["posts read"]
            ts = [t for t in sorted(pts) if pts[t][1] >= 150]
            ax.plot(ts, [100 * pts[t][0] / pts[t][1] for t in ts], color=COLOR[r], label=NAME[r], lw=1.8)
        ax.axhline(pick("V1", m)["% upvoted"], color=COLOR["V1"], lw=1.2, ls="--", label="V1 r101 (no ticks)")
        ax.set_title(f"{m} reading: % upvoted by tick", fontsize=9, loc="left")
        ax.set_xlabel("tick", fontsize=8, color=INK2)
        ax.set_ylim(0, 105)
        style(ax)
    axs[0].legend(frameon=False, fontsize=7.5)
    sheet(title, note, head, body, {1: 9, 2: 9, 3: 6}, base=lambda row: row[0] == row[1], chart=png(fig))


def posts_sheet(title, note, runs, fam):
    head = ["post", "pile (AI)", "writer", "community", "characters", "title"] + \
        [f"{NAME[r]}, {ai} reading: {k}" for ai in AIS for r in runs for k in ("read", "% up", "% down", "% comment", "actions per 100")]
    body = []
    for key, p in sorted(REPORT["post_info"].items()):
        if key.startswith(fam + "|"):
            k = key[len(fam) + 1:]
            row = [k, p["ai"], f"{p['user']} u/{USERNAME[p['user']]}", p["sub"], p["chars"], p["title"]]
            for ai in AIS:
                for r in runs:
                    row += REPORT["posts"].get(f"{r}|{k}|{ai}", [None] * 5)
            body.append(row)
    sheet(title, note, head, body, {1: 26, 3: 18, 4: 18, 6: 46})


def users_sheet(title, note, runs):
    head = ["user", "username"] + [f"{NAME[r]}, {ai} plays them: {k}" for ai in AIS for r in runs for k in ("posts read", "actions per 100", "% up", "% comment")]
    body = []
    for u in range(100):
        row = [u, USERNAME[u]]
        for ai in AIS:
            for r in runs:
                row += REPORT["users"].get(f"{r}|{ai}|{u}", [None] * 4)
        body.append(row)
    sheet(title, note, head, body, {1: 6, 2: 14})


def effort_sheet(title, note):
    head = ["reader AI", "level", "what it takes", "V3: chosen", "V3: % of all actions", "V3: failed %", "V3a: chosen", "V3a: % of all actions",
            "V3a: failed %", "change (points)"]
    E = {(r, x["reader"], x["tier"]): x for r in ("V3", "V3a") for x in REPORT["effort"][r]}
    body = []
    for ai in AIS:
        for t in "12345":
            a, b = E[("V3", ai, t)], E[("V3a", ai, t)]
            body.append([ai, int(t), a["what it takes"], NUM(a["chosen"]), NUM(a["% of all actions chosen"]), NUM(a["failed %"] or 0),
                         NUM(b["chosen"]), NUM(b["% of all actions chosen"]), NUM(b["failed %"] or 0),
                         round(float(b["% of all actions chosen"]) - float(a["% of all actions chosen"]), 1)])
    groups = [f"{ai} L{t}" for ai in AIS for t in "123"]
    sheet(title, note, head, body, {1: 10, 2: 6, 3: 44},
          chart=bars(groups, ["V3", "V3a"], {(f"{ai} L{t}", r): float(E[(r, ai, t)]["% of all actions chosen"]) for ai in AIS for t in "123" for r in ("V3", "V3a")},
                     "% of actions at levels 1-3 (1 one click, 2 copy an ID, 3 write text)", "%"))


def posting_sheets():
    runs = [("V1", "V1 r101"), ("V1 r102", "V1 r102"), ("V3", "V3 (= V3a's posts)")]
    head = ["AI", "run", "users with 0 posts", "1 post", "2 posts", "3+ posts", "no usable answer", "posts written", "average characters", "users"]
    body, vals = [], {}
    for ai in AIS:
        for r, rn in runs:
            us = REPORT["posting"][f"{r}|{ai}"]
            c = Counter("x" if u["outcome"] != "chose" else "3+" if u["posts"] >= 3 else str(u["posts"]) for u in us)
            ch = [x for u in us for x in u["chars"]]
            body.append([ai, rn, c["0"], c["1"], c["2"], c["3+"], c["x"], sum(u["posts"] for u in us), round(sum(ch) / len(ch)) if ch else None, len(us)])
            vals[(ai, r)] = sum(u["posts"] for u in us)
    sheet("Posting · posts per user", "The posting turn. V3a reads V3's posts (no posting turn of its own). Each AI plays 100 users, so users = % of users.",
          head, body, {1: 8, 2: 18}, chart=bars(AIS, ["V1", "V1 r102", "V3"], vals, "Posts written by each AI's 100 users", "posts"))
    body = []
    for ai in AIS:
        for r, rn in runs:
            c = Counter("no usable answer" if u["outcome"] != "chose" else " + ".join(dict.fromkeys(u["acts"])) or "empty list []"
                        for u in REPORT["posting"][f"{r}|{ai}"] if u["posts"] == 0)
            body += [[ai, rn, k, v] for k, v in c.most_common()]
    sheet("Posting · no-post answers", "An answer is never 'nothing': this is what the AI sent for users who wrote no post.",
          ["AI", "run", "their answer (actions)", "users"], body, {1: 8, 2: 18, 3: 50})
    body = []
    for ai in AIS:
        for r, rn in runs:
            c = Counter(t for u in REPORT["posting"][f"{r}|{ai}"] for t in u["topics"])
            body += [[ai, rn, k, v] for k, v in sorted(c.items(), key=lambda kv: -kv[1])]
    sheet("Posting · communities", "Which community (subreddit) each AI's posts went to.", ["AI", "run", "community", "posts"], body, {1: 8, 2: 18, 3: 22})
    body = [[ai, rn, u["user"], USERNAME[u["user"]], u["posts"], ", ".join(u["acts"]) or "empty list []", u["tries"], u["tokens"], u["raw"]]
            for ai in AIS for r, rn in runs for u in REPORT["posting"][f"{r}|{ai}"]]
    sheet("Posting · every answer", "Every user's posting answer, all 3 AIs, V1 r101, V1 r102 and V3, word for word.",
          ["AI", "run", "user", "username", "posts written", "actions in the answer", "tries", "answer tokens", "the answer, word for word"],
          body, {1: 8, 2: 18, 4: 14, 6: 30, 9: 120})


def detail():
    """Each run's clean data: cleaning reports, every world tick by tick with every action, every post read."""
    for run, d in zip(("V3", "V3a"), DIRS):
        ws = wb.create_sheet(f"Cleaning {run}")
        r = 1
        for l in open(os.path.join(d, "clean", "cleaning.md")):
            l = l.rstrip("\n")
            if l.startswith("|---"):
                continue
            cells = [c.strip() for c in l.strip("|").split("|")] if l.startswith("|") else [l.lstrip("# ")]
            for j, c in enumerate(cells, 1):
                ws.cell(r, j, NUM(c.replace(",", "")) if l.startswith("|") else c).font = FB if not l.startswith("|") else F
            r += 1
        for j, w in enumerate((70, 22, 40, 12, 12, 12), 1):
            ws.column_dimensions[get_column_letter(j)].width = w
    cols = ["posts read", "actions chosen", "actions done", "upvoted", "downvoted", "commented", "did nothing", "comments on screen",
            "follow-up screens", "engagement per 100", "done per 100", "upvoted %", "commented %"]
    for run, d in zip(("V3", "V3a"), DIRS):
        rows = [{k: NUM(v) for k, v in r.items()} for r in csv.DictReader(open(os.path.join(d, "clean", "by_cell_tick.csv")))]
        acts = sorted(set(rows[0]) - set(cols) - {"reader", "posts_by", "tick"})
        for m in AIS:
            for pb in AIS:
                rs = [r for r in rows if r["reader"] == m and r["posts_by"] == pb]
                use = [a for a in acts if any(r.get(a) for r in rs)]
                sheet(f"{run} ticks · {m} reads {pb}", f"{run}: {m} plays all 100 users reading {pb}'s posts. One row per tick (tick 0 = no "
                      "timeline yet), last row = all ticks. 'did nothing' = do_nothing only or an empty list. Action columns = times chosen on the post screen.",
                      ["tick"] + cols + use, [[r["tick"]] + [r[c] for c in cols] + [r.get(a) or 0 for a in use] for r in rs], {1: 6})
    for run, d in zip(("V3", "V3a"), DIRS):
        for name, f in (("reads", "reads.csv"), ("follow-ups", "followups.csv")):
            rs = list(csv.reader(open(os.path.join(d, "clean", f))))
            sheet(f"{run} every {name}", f"{run}: clean/{f}, one row per {'post read' if name == 'reads' else 'extra screen'}. Filter to check any number.",
                  rs[0], [[NUM(v) for v in r] for r in rs[1:]], {5: 24, 12: 30})


# ---- Read me ----
ws = wb.active
ws.title = "Read me"
TEXT = [
    ("LLM Bias V3 big sim: the numbers", ""),
    ("", ""),
    ("RUNS", ""),
    ("V3", "Big sim part 1: every AI's 100 users write posts, then every AI's users read every AI's posts in a live world. Action list in V1's order."),
    ("V3a", "Big sim part 2: the same posts, the same users, the action list in a new order (least used in V3 on top, upvote last). The only change."),
    ("V1", "Round 101 of V1 (round 102 alongside in some sheets): one post per screen, no comments, no live world, V1's order."),
    ("no timeline (tick 0)", "Each user's first post in V3/V3a, before anyone commented: the closest V3 gets to V1. 100 posts read per world."),
    ("", ""),
    ("WORDS", ""),
    ("% of posts read", "Out of every post a user read, how often the AI did this. Upvoted 60% = 60 of every 100 posts read got an upvote."),
    ("actions per 100", "Total engagement, the main measure: every action except do_nothing, per 100 posts read (one answer can hold several)."),
    ("points", "A difference of two percentages: 60% -> 50% is -10 points. The 'change' columns are points."),
    ("do_nothing / empty list", "Every answer is a list of actions. 'do_nothing only' = the AI picked the menu action do_nothing; 'empty list' = it sent [] "
                                "with only a reason. They are counted separately."),
    ("own-AI favouritism", "(i on i's posts - j on i's posts) - (i on j's posts - j on j's posts), in points; 95% range from resampling posts and users. "
                           "CLEAR = the range leaves out 0."),
    ("", ""),
    ("SHEETS (in order)", ""),
    ("V3 vs V3a · ...", "The main comparison: summary, every action, worlds, by feeling, timeline (tick by tick), no timeline, own-AI favouritism, "
                        "posts, users, easy vs hard. Charts sit to the right of each table."),
    ("V1 vs V3 · ...", "V1 next to V3 (V1 had V1's order, so it is compared with V3, not V3a): summary, actions, worlds, by feeling, "
                       "no timeline (V1 vs V3 tick 0), own-AI favouritism, V1's posts."),
    ("Posting · ...", "Posts per user, what users who wrote no post answered, communities, and every posting answer word for word."),
    ("Cleaning / ticks / every ...", "Each run's cleaning report, every world tick by tick with every action, and every post read and extra screen."),
    ("", ""),
    ("Source", "v3_report_data.py -> data/llm_bias/v3_report.json (the same numbers as the LLM Bias V3 Data page); detail sheets from "
               "data/llm_bias/v3/clean and v3_flipped/clean (v3_clean.py). Recount of 62,633 numbers from the raw files: 0 differences."),
]
for i, (a, b) in enumerate(TEXT, 1):
    ws.cell(i, 1, a).font = FT if i == 1 else FB
    ws.cell(i, 2, b).font = F
    ws.cell(i, 2).alignment = Alignment(wrap_text=True, vertical="top")
ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 26, 130

M = ["V3", "V3a"]
summary("V3 vs V3a · Summary", "Whole scroll. Each AI reading all three piles, then all AIs together.", M, M)
actions_sheet("V3 vs V3a · Actions", "Every action: % of posts read where chosen, and times per 100 posts read, per reader AI.", M)
worlds_sheet("V3 vs V3a · Worlds", "The 9 worlds (reader AI x whose posts), whole scroll. Baselines shaded.", M)
stance_sheet("V3 vs V3a · By feeling", "By how the user feels about the post's topic (LOVE ... HATE), whole scroll.", M)
ticks_sheet("V3 vs V3a · Timeline", "Every world, every tick, V3 next to V3a. Chart: each reader AI, its 3 piles together, ticks with 150+ posts read.")
summary("V3 vs V3a · No timeline", "Tick 0 only: each user's first post, before anyone commented (100 posts read per world).",
        ["V3 tick 0", "V3a tick 0"], ["V3 tick 0", "V3a tick 0"])
actions_sheet("V3 vs V3a · No-timeline actions", "Tick 0 only, every action.", ["V3 tick 0", "V3a tick 0"])
bias_sheet("V3 vs V3a · Own-AI favour", "The four percentages, the two gaps and the favouritism, whole scroll and tick 0.", ["V3", "V3a", "V3 tick 0", "V3a tick 0"])
posts_sheet("V3 vs V3a · Posts", "Each of the 320 posts, what each reader AI did with it, V3 and V3a.", M, "V3")
users_sheet("V3 vs V3a · Users", "Each user (all 3 piles together), as played by each AI, V3 and V3a.", M)
effort_sheet("V3 vs V3a · Easy vs hard", "Share of each AI's actions (all screens, do_nothing left out) at each effort level.")
V = ["V1", "V3"]
summary("V1 vs V3 · Summary", "V1 round 101 next to V3 (whole scroll); the charts add V1 round 102.", V, ["V1", "V1 r102", "V3"])
actions_sheet("V1 vs V3 · Actions", "Every action, V1 round 101 next to V3.", V)
worlds_sheet("V1 vs V3 · Worlds", "The 9 worlds, V1 round 101 next to V3.", V)
stance_sheet("V1 vs V3 · By feeling", "By feeling, V1 round 101 next to V3.", V)
summary("V1 vs V3 · No timeline", "V1 round 101 next to V3 tick 0 (each user's first post, no comments yet).", ["V1", "V3 tick 0"], ["V1", "V3 tick 0", "V3a tick 0"])
bias_sheet("V1 vs V3 · Own-AI favour", "V1 rounds 101 and 102 next to V3 and V3 tick 0.", ["V1", "V1 r102", "V3", "V3 tick 0"])
posts_sheet("V1 vs V3 · V1 posts", "V1 round 101's own posts (written without the 'posting time' line), what each reader AI did with them.", ["V1"], "V1")
posting_sheets()
detail()
wb.save(OUT)
print(f"wrote {OUT}: {len(wb.sheetnames)} sheets: {', '.join(wb.sheetnames)}")
