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
NAME = {"V3": "V3", "V3a": "V3a (reordered)", "V3 tick 0": "V3, first post only", "V3a tick 0": "V3a (reordered), first post only", "V1": "V1 r101", "V1 r102": "V1 r102"}
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
    ws.row_dimensions[4].height = 58
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
    fig.tight_layout(rect=(0, 0, 1, 0.96) if fig._suptitle else None)  # leave room for the chart's own title
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


WORLDS = [(m, pb) for m in AIS for pb in AIS]  # gemma reads gemma's, gemma reads llama's, gemma reads qwen's, then llama, then qwen
W = lambda run, m, pb: REPORT["world"][f"{run}|{m}|{pb}"]  # noqa: E731
OWN = lambda pb, m: f"{pb} (own AI)" if pb == m else pb  # noqa: E731
LEAD = ["reading AI (plays the 100 users)", "posts written by (that AI's users)"]
MEAS = [("posts read", "posts read"), ("actions per 100", "actions per 100 posts read"), ("% engaged", "% with a real action"),
        ("% upvoted", "% upvoted"), ("% downvoted", "% downvoted"), ("% commented", "% commented"),
        ("% chose do_nothing", "% do_nothing only"), ("% empty answer", "% empty list [] only")]


def grid(fig_rows, fig_cols, h=3.2):
    fig, axs = plt.subplots(fig_rows, fig_cols, figsize=(11, h * fig_rows), squeeze=False)
    return fig, axs


def world_bars(runs, key, title, ylabel, ymax=None):
    """One panel per reading AI (same y scale); inside it one group per 'posts written by' AI; one bar per run.
    key = a measure name, or a function (run, reading AI, posts by) -> value."""
    get = key if callable(key) else (lambda r, m, pb: W(r, m, pb)[key])
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True)
    top = max(get(r, m, pb) for r in runs for m in AIS for pb in AIS)
    for ax, m in zip(axs, AIS):
        w = 0.8 / len(runs)
        for k, r in enumerate(runs):
            xs = [i + (k - (len(runs) - 1) / 2) * w for i in range(3)]
            vs = [get(r, m, pb) for pb in AIS]
            ax.bar(xs, vs, w * 0.92, color=COLOR[r], label=NAME[r])
            for x, v in zip(xs, vs):
                ax.text(x, v, f"{v:.0f}", ha="center", va="bottom", fontsize=7, color=INK2)
        ax.set_xticks(range(3), [f"{pb}'s posts" + ("\n(own AI)" if pb == m else "") for pb in AIS], fontsize=7.5)
        ax.set_title(f"{m} reads ...", fontsize=9.5, loc="left")
        ax.set_ylim(0, ymax or top * 1.12 + 1)
        style(ax)
    axs[0].set_ylabel(ylabel, fontsize=8, color=INK2)
    fig.suptitle(title, x=0.01, ha="left", fontsize=10.5)
    fig.legend(*axs[0].get_legend_handles_labels(), loc="upper right", frameon=False, fontsize=8, ncol=len(runs))
    return png(fig)


def action_charts(title, note, runs):
    """The actions, front and centre: a table of every action in every world, then one chart per action
    (each world, both runs) and one chart per world (every action it used, both runs)."""
    used = [a for a in REPORT["actions"] if any(W(r, m, pb)["actions"][a]["times"] for r in runs for m, pb in WORLDS)]
    used.sort(key=lambda a: -sum(W(r, m, pb)["actions"][a]["% of posts"] for r in runs for m, pb in WORLDS))
    head = ["action"] + [f"{m} reads {pb}'s posts{' (own)' if m == pb else ''}: {NAME[r]}" for m, pb in WORLDS for r in runs]
    body = [[a] + [W(r, m, pb)["actions"][a]["% of posts"] for m, pb in WORLDS for r in runs] for a in used] + \
        [[a] + [0.0] * (len(head) - 1) for a in REPORT["actions"] if a not in used]  # never chosen in these runs: 0 everywhere
    ws = sheet(title, note, head, body, {1: 22})
    col, row = get_column_letter(len(head) + 2), 4
    for a in used:
        place(ws, world_bars(runs, lambda r, m, pb, a=a: W(r, m, pb)["actions"][a]["% of posts"],
                             f"{a}: % of posts read where the reading AI chose it", "%", 105), f"{col}{row}")
        row += 21
    col2 = get_column_letter(len(head) + 14)
    for i, (m, pb) in enumerate(WORLDS):
        acts = [a for a in used if any(W(r, m, pb)["actions"][a]["times"] for r in runs)]
        fig, ax = plt.subplots(figsize=(7, 0.32 * len(acts) + 1.2))
        for k, r in enumerate(runs):
            ys = [j + (k - 0.5) * 0.4 for j in range(len(acts))]
            vs = [W(r, m, pb)["actions"][a]["% of posts"] for a in acts]
            ax.barh(ys, vs, 0.37, color=COLOR[r], label=NAME[r])
            for y, v in zip(ys, vs):
                ax.text(v + 0.8, y, f"{v:.1f}", va="center", fontsize=6.5, color=INK2)
        ax.set_yticks(range(len(acts)), acts, fontsize=7.5)
        ax.invert_yaxis()
        ax.set_xlim(0, 110)
        ax.set_title(f"{m} reads {pb}'s posts{' (own AI)' if m == pb else ''}: every action, % of posts read", fontsize=9, loc="left")
        ax.legend(frameon=False, fontsize=7.5, loc="lower right")
        style(ax)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=GRID)
        place(ws, png(fig), f"{col2}{4 + i * 24}")


def worlds_main(title, note, runs):
    head = LEAD + [f"{NAME[r]}: {t}" for k, t in MEAS for r in runs] + [f"change, points: {t}" for k, t in MEAS[1:]]
    body = [[m, OWN(pb, m)] + [W(r, m, pb)[k] for k, _ in MEAS for r in runs] + [round(W(runs[1], m, pb)[k] - W(runs[0], m, pb)[k], 1) for k, _ in MEAS[1:]]
            for m, pb in WORLDS]
    ws = sheet(title, note, head, body, {1: 16, 2: 16}, base=lambda row: "own" in str(row[1]),
               chart=world_bars(runs, "% upvoted", "% of posts upvoted, each world", "%", 105))
    place(ws, world_bars(runs, "actions per 100", "Total engagement: actions per 100 posts read, each world", "per 100"), f"{get_column_letter(len(head) + 2)}25")
    place(ws, world_bars(runs, "% commented", "% of posts commented on, each world", "%", 105), f"{get_column_letter(len(head) + 2)}46")


def worlds_actions(title, note, runs):
    head = LEAD + ["action"] + [f"{NAME[r]}: % of posts" for r in runs] + [f"{NAME[r]}: times per 100 posts" for r in runs] + \
        [f"change, points ({NAME[runs[1]]} - {NAME[runs[0]]})"]
    body = []
    fig, axs = grid(3, 3, 5.2)
    for (m, pb), ax in zip(WORLDS, [a for row in axs for a in row]):
        acts = sorted(REPORT["actions"], key=lambda a: -sum(W(r, m, pb)["actions"][a]["% of posts"] for r in runs))
        for a in acts:  # all 28 post-screen actions in every world, 0 where nobody chose it
            p = [W(r, m, pb)["actions"][a]["% of posts"] for r in runs]
            body.append([m, OWN(pb, m), a] + p + [W(r, m, pb)["actions"][a]["per 100"] for r in runs] + [round(p[1] - p[0], 1)])
        top = [a for a in acts if any(W(r, m, pb)["actions"][a]["times"] for r in runs)]  # every action chosen in either run
        for k, r in enumerate(runs):
            ys = [i + (k - (len(runs) - 1) / 2) * (0.8 / len(runs)) for i in range(len(top))]
            ax.barh(ys, [W(r, m, pb)["actions"][a]["% of posts"] for a in top], 0.8 / len(runs) * 0.92, color=COLOR[r], label=NAME[r])
        ax.set_yticks(range(len(top)), top, fontsize=6.5)
        ax.invert_yaxis()
        ax.set_xlim(0, 105)
        ax.set_title(f"{m} reads {pb}'s posts" + (" (own)" if m == pb else ""), fontsize=8.5, loc="left")
        style(ax)
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color=GRID)
    axs[0][0].legend(frameon=False, fontsize=7)
    fig.suptitle("Every action chosen in each world, % of posts read", x=0.01, ha="left", fontsize=10.5)
    sheet(title, note, head, body, {1: 16, 2: 16, 3: 22}, base=lambda row: "own" in str(row[1]), chart=png(fig))


def worlds_stance(title, note, runs):
    K = ["% engaged", "% upvoted", "% downvoted", "% commented", "actions per 100"]
    head = LEAD + ["the reading user feels about the topic"] + [f"{NAME[r]}: posts read" for r in runs] + [f"{NAME[r]}: {k}" for k in K for r in runs] + \
        [f"change: {k}" for k in K]
    SW = REPORT["stance_w"]
    body = []
    for m, pb in WORLDS:
        for s in STANCES:
            x = [SW.get(f"{r}|{m}|{pb}|{s}") for r in runs]
            if all(x):
                body.append([m, OWN(pb, m), s] + [v["posts read"] for v in x] + [v[k] for k in K for v in x] + [round(x[1][k] - x[0][k], 1) for k in K])
    fig, axs = grid(3, 3, 2.7)
    for (m, pb), ax in zip(WORLDS, [a for row in axs for a in row]):
        for r in runs:
            ys = [SW.get(f"{r}|{m}|{pb}|{s}", {}).get("% upvoted") for s in STANCES]
            ax.plot(STANCES, ys, marker="o", color=COLOR[r], label=NAME[r], lw=1.8, ms=4)
        ax.set_ylim(0, 105)
        ax.set_title(f"{m} reads {pb}'s posts" + (" (own)" if m == pb else ""), fontsize=8.5, loc="left")
        ax.tick_params(axis="x", labelsize=6.5)
        style(ax)
    axs[0][0].legend(frameon=False, fontsize=7)
    fig.suptitle("% upvoted by how the reading user feels about the topic, each world", x=0.01, ha="left", fontsize=10.5)
    sheet(title, note, head, body, {1: 16, 2: 16, 3: 14}, base=lambda row: "own" in str(row[1]), chart=png(fig))


def bias_sheet(title, note, runs):
    head = ["run", "pair (i vs j)", "measure", "i reads i's posts", "j reads i's posts", "gap 1 (i reads i's - j reads i's)", "i reads j's posts",
            "j reads j's posts", "gap 2 (i reads j's - j reads j's)", "favouritism = gap 1 - gap 2 (points)", "95% low", "95% high", "clear?"]
    body = []
    for r in runs:
        for b in REPORT["bias"][r]:
            body.append([NAME[r], b["pair"], b["measure"], b["i on i"], b["j on i"], round(b["i on i"] - b["j on i"], 1), b["i on j"],
                         b["j on j"], round(b["i on j"] - b["j on j"], 1), b["bias"], b["low"], b["high"], "CLEAR" if b["clear"] else "no"])
    shade = {r: c for r, c in zip(runs, ["#6250d6", "#eda100", "#8a8f98", "#b4b2ab"])}
    fig, axs = grid(1, 2, 3.6)
    for ax, meas in zip(axs[0], ("upvoted %", "actions per 100")):
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
    axs[0][0].legend(frameon=False, fontsize=7.5)
    sheet(title, note, head, body, {1: 16, 2: 16, 3: 14}, chart=png(fig))


TK = ("actions per 100", "% upvoted", "% downvoted", "% commented", "% like_comment", "comments seen per post")


def ticks_sheet(title, note):
    head = LEAD + ["tick", "V3: posts read", "V3a: posts read"] + [f"{run}: {k}" for k in TK for run in ("V3", "V3a")]
    body, T = [], REPORT["tick"]
    g = lambda v, k: v[k] if v else None  # noqa: E731
    fig, axs = grid(3, 3, 2.7)
    for (m, pb), ax in zip(WORLDS, [a for row in axs for a in row]):
        for t in range(140):
            x = [T.get(f"{r}|{m}|{pb}|{t}") for r in ("V3", "V3a")]
            if any(x):
                body.append([m, OWN(pb, m), t, g(x[0], "posts read"), g(x[1], "posts read")] + [g(v, k) for k in TK for v in x])
        for r in ("V3", "V3a"):
            pts = [(t, T[f"{r}|{m}|{pb}|{t}"]["% upvoted"]) for t in range(140) if T.get(f"{r}|{m}|{pb}|{t}", {}).get("posts read", 0) >= 50]
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=COLOR[r], label=NAME[r], lw=1.4)
        ax.axhline(W("V1", m, pb)["% upvoted"], color=COLOR["V1"], lw=1, ls="--", label="V1 r101 (no ticks)")
        ax.set_ylim(0, 105)
        ax.set_title(f"{m} reads {pb}'s posts" + (" (own)" if m == pb else ""), fontsize=8.5, loc="left")
        style(ax)
    axs[0][0].legend(frameon=False, fontsize=7)
    fig.suptitle("% upvoted at each tick, each world (tick 0 = no timeline yet)", x=0.01, ha="left", fontsize=10.5)
    sheet(title, note, head, body, {1: 16, 2: 16, 3: 6}, base=lambda row: "own" in str(row[1]), chart=png(fig))


def posts_sheet(title, note, runs, fam):
    head = ["post", "posts written by (AI)", "writer (user)", "community", "characters", "title"] + \
        [f"{NAME[r]}, read by {ai}: {k}" for ai in AIS for r in runs for k in ("times read", "% up", "% down", "% comment", "actions per 100")]
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
    head = LEAD + ["user", "username"] + [f"{NAME[r]}: {k}" for r in runs for k in ("posts read", "actions per 100", "% up", "% comment")]
    body = []
    for m, pb in WORLDS:
        for u in range(100):
            row = [m, OWN(pb, m), u, USERNAME[u]]
            for r in runs:
                row += REPORT["users_w"].get(f"{r}|{m}|{pb}|{u}", [None] * 4)
            body.append(row)
    sheet(title, note, head, body, {1: 16, 2: 16, 3: 6, 4: 14}, base=lambda row: "own" in str(row[1]))


def effort_sheet(title, note, runs):
    TXT = {"1": "one click", "2": "copy an ID from the screen", "3": "write text", "4": "write a whole post", "5": "go to another screen first, then write"}
    head = LEAD + ["level", "what it takes"] + [f"{NAME[r]}: {k}" for r in runs for k in ("chosen", "% of its actions", "failed %")] + ["change, points"]
    E = REPORT["effort_w"]
    body = []
    for m, pb in WORLDS:
        for t in "12345":
            x = [E[f"{r}|{m}|{pb}"][t] for r in runs]
            body.append([m, OWN(pb, m), int(t), TXT[t]] + [v for e in x for v in (e["chosen"], e["%"], e["failed %"])] + [round(x[1]["%"] - x[0]["%"], 1)])
    fig, axs = grid(1, 3, 3.4)
    for ax, m in zip(axs[0], AIS):
        labels = [f"{pb}'s\nL{t}" for pb in AIS for t in "123"]
        for k, r in enumerate(runs):
            xs = [i + (k - 0.5) * 0.4 for i in range(len(labels))]
            ax.bar(xs, [E[f"{r}|{m}|{pb}"][t]["%"] for pb in AIS for t in "123"], 0.37, color=COLOR[r], label=NAME[r])
        ax.set_xticks(range(len(labels)), labels, fontsize=6.5)
        ax.set_ylim(0, 105)
        ax.set_title(f"{m} reads ...: % of its actions at levels 1-3", fontsize=8.5, loc="left")
        style(ax)
    axs[0][0].legend(frameon=False, fontsize=7)
    sheet(title, note, head, body, {1: 16, 2: 16, 3: 6, 4: 32}, base=lambda row: "own" in str(row[1]), chart=png(fig))


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
    ("LLM Bias V3 big sim: every world, without and with the timeline", ""),
    ("", ""),
    ("HOW THIS FILE IS LAID OUT", ""),
    ("No totals", "Every table is broken down by WORLD: one reading AI reacting to the posts one AI's users wrote. gemma reads gemma's "
                  "posts, gemma reads llama's, gemma reads qwen's, then llama reads each, then qwen reads each (9 rows). Own-AI rows are shaded."),
    ("1. No timeline first", "The 'No timeline' sheets use only data from before any timeline existed: each user's FIRST post, before "
                             "anyone had commented on anything. That is 100 posts read in each world (one per user), the same kind of screen as V1."),
    ("Actions first", "Each half opens with 'action charts': every action in every world, V3 next to V3a, with one chart per action and "
                      "one chart per world."),
    ("2. Timeline second", "The 'Timeline' sheets use the whole scroll: every post each user read, with comments piling up tick by tick."),
    ("3. Posting, then detail", "The posting turn (what each AI's users wrote), each run's cleaning report, every world tick by tick, every row."),
    ("", ""),
    ("RUNS", ""),
    ("V3", "Big sim part 1: action list in V1's order."),
    ("V3a", "Big sim part 2: the same posts and users, the action list in a new order (least used in V3 on top, upvote last). The only change."),
    ("V1", "V1 round 101 (round 102 in the favouritism sheets): one post per screen, no comments, no timeline at all, V1's order."),
    ("", ""),
    ("WORDS", ""),
    ("reading AI", "The AI playing the 100 users who read and react. 'posts written by' = the AI whose users wrote the posts."),
    ("% of posts read", "Out of every post read in that world, how often the reading AI did this. Upvoted 60% = 60 of every 100 posts read got an upvote."),
    ("actions per 100", "Total engagement: every action except do_nothing, per 100 posts read (one answer can hold several actions)."),
    ("points", "A difference of two percentages: 60% -> 50% is -10 points. The 'change' columns are points."),
    ("do_nothing only / empty list", "Every answer is a list of actions: 'do_nothing only' = it picked the menu action do_nothing; 'empty list' = it sent [] "
                                     "with only a reason. Counted separately."),
    ("own-AI favouritism", "(i reads i's posts - j reads i's posts) - (i reads j's posts - j reads j's posts), in points; 95% range from resampling "
                           "posts and users. CLEAR = the range leaves out 0."),
    ("", ""),
    ("Source", "v3_report_data.py -> data/llm_bias/v3_report.json (the same numbers as the LLM Bias V3 Data page); recounted from the raw "
               "files: 30,083 numbers, 0 differences."),
]
for i, (a, b) in enumerate(TEXT, 1):
    ws.cell(i, 1, a).font = FT if i == 1 else FB
    ws.cell(i, 2, b).font = F
    ws.cell(i, 2).alignment = Alignment(wrap_text=True, vertical="top")
ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 28, 130

T0, M, V0, V = ["V3 tick 0", "V3a tick 0"], ["V3", "V3a"], ["V1", "V3 tick 0"], ["V1", "V3"]
NT = "NO TIMELINE: each user's first post only, before anyone had commented on anything (100 posts read per world). "
TL = "WITH THE TIMELINE: the whole scroll, comments piling up. "
action_charts("No timeline · action charts", NT + "Every action in every world, V3 vs V3a. Charts: one per action, then one per world.", T0)
worlds_main("No timeline · V3 vs V3a", NT + "Each world on its own row.", T0)
worlds_actions("No timeline · V3 vs V3a actions", NT + "All 28 actions on the post screen, in every world (0 = nobody chose it). send_message, open_post and back exist only on extra screens.", T0)
worlds_stance("No timeline · V3 vs V3a feeling", NT + "By how the reading user feels about the post's topic (about 20 posts per feeling per world).", T0)
effort_sheet("No timeline · V3 vs V3a effort", NT + "Easy vs hard actions in every world.", T0)
worlds_main("No timeline · V1 vs V3", NT + "V1 round 101 (no timeline at all) next to V3's tick 0. V1 had V1's order, so it is compared with V3, not V3a.", V0)
worlds_actions("No timeline · V1 vs V3 actions", NT + "All 28 post-screen actions in every world, V1 round 101 next to V3's first post only (0 = nobody chose it).", V0)
worlds_stance("No timeline · V1 vs V3 feeling", NT + "By feeling, V1 round 101 next to V3's tick 0.", V0)
bias_sheet("No timeline · own-AI favour", NT + "Own-AI favouritism from the worlds above (V1 rounds 101 and 102 alongside).", ["V3 tick 0", "V3a tick 0", "V1", "V1 r102"])
action_charts("Timeline · action charts", TL + "Every action in every world, V3 vs V3a. Charts: one per action, then one per world.", M)
worlds_main("Timeline · V3 vs V3a", TL + "Each world on its own row.", M)
worlds_actions("Timeline · V3 vs V3a actions", TL + "All 28 actions on the post screen, in every world (0 = nobody chose it). send_message, open_post and back exist only on extra screens.", M)
worlds_stance("Timeline · V3 vs V3a feeling", TL + "By how the reading user feels about the post's topic.", M)
ticks_sheet("Timeline · tick by tick", TL + "Every world, every tick, V3 next to V3a (the dashed line in the charts is V1, which has no ticks).")
effort_sheet("Timeline · V3 vs V3a effort", TL + "Easy vs hard actions in every world (all screens, do_nothing left out).", M)
bias_sheet("Timeline · own-AI favour", TL + "Own-AI favouritism, whole scroll (V1 rounds 101 and 102 alongside).", ["V3", "V3a", "V1", "V1 r102"])
posts_sheet("Timeline · V3 vs V3a posts", TL + "Each of the 320 posts and what each reading AI did with it.", M, "V3")
users_sheet("Timeline · V3 vs V3a users", TL + "Each user in each world.", M)
worlds_main("Timeline · V1 vs V3", TL + "V1 round 101 (no timeline) next to V3's whole scroll.", V)
worlds_actions("Timeline · V1 vs V3 actions", TL + "All 28 post-screen actions in every world, V1 round 101 next to V3's whole scroll (0 = nobody chose it).", V)
posts_sheet("V1 · posts", "V1 round 101's own posts (written without the 'posting time' line), what each reading AI did with them.", ["V1"], "V1")
posting_sheets()
detail()
wb.save(OUT)
print(f"wrote {OUT}: {len(wb.sheetnames)} sheets: {', '.join(wb.sheetnames)}")
