"""LLM Bias v2 report: one Excel workbook + every graph, built from the raw result files copied off the Spark.

    oasis-env/bin/python examples/experiment/llm_bias/make_report_v2.py data/llm_bias/v2_spark ~/Desktop/LLM_Bias_v2

IN PLAIN WORDS
--------------
Reads every real-round file (rounds 100-899) in <results>/r*/ plus <results>/night.log, and writes into <out>/:
  LLM_Bias_v2.xlsx   README, 3x3 engagement grids for every action (formulas over the Screens sheet, with a round
                     picker), all 27 actions, own-AI bias, by stance, by topic, posting turn, every post, every person,
                     noise floor, time per step, the graphs, and every screen as one row.
  graphs/*.png       the engagement grids, all 27 actions, posting, stance, topic, bias, noise, and the time graphs
                     (speed per AI with the GPU free vs shared, minutes vs screens, the round timeline, and what a
                     round would cost at 10-1,000 users).
Speeds use only steps where the GPU was free: a step counts as "shared" when its seconds per screen are more than
1.25x that AI's best real-round speed (another user's jobs slow ours 2-35x, log 14.31c/e).
"""
import glob, json, os, re, sys
from collections import Counter, defaultdict
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze_v2  # noqa: E402  (dd + boot: the double difference and its 95% range)
from run_v2 import ACTION_NAMES, TOPICS  # noqa: E402

MODELS = ["qwen3:8b", "llama3.1:8b", "gemma3:12b"]
SHORT = {"qwen3:8b": "qwen", "llama3.1:8b": "llama", "gemma3:12b": "gemma"}
COLOR = {"qwen3:8b": "#2a78d6", "llama3.1:8b": "#eb6834", "gemma3:12b": "#1baf7a"}  # dataviz slots 1-3 (all-pairs safe)
STANCES = ["LOVE", "LIKE", "NEUTRAL", "DISLIKE", "HATE"]
LABEL = {"like_post": "upvote", "dislike_post": "downvote", "create_comment": "comment", "repost": "share (repost)",
         "quote_post": "quote", "report_post": "report", "unlike_post": "take back upvote",
         "undo_dislike_post": "take back downvote"}
INK, MUTED, GRID = "#1d1d1b", "#6b6a64", "#e6e5df"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
                     "figure.dpi": 130, "savefig.bbox": "tight", "axes.titleweight": "bold", "axes.titlesize": 11})


def lbl(a):
    return LABEL.get(a, a.replace("_", " "))


# ---------------------------------------------------------------- data
def load(res):
    reads, posts_rows = [], []
    for f in sorted(glob.glob(os.path.join(res, "r*", "*.jsonl"))):
        b = os.path.basename(f)
        r = int(os.path.basename(os.path.dirname(f))[1:])
        if not 100 <= r < 900 or re.search(r"_a\d+\.jsonl$", b):  # test sizes (_a10) are not part of the study
            continue
        rows = []
        for line in open(f):
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        (posts_rows if b.startswith("posting_") else reads).extend(rows)
    return reads, posts_rows


def post_index(posts_rows):
    """Every post in every post set, keyed like run_v2.post_set()."""
    out = {}
    for d in posts_rows:
        k = 0
        for a in d["actions"]:
            if a["action"] == "create_post":
                key = f"r{d['round']}|{d['model'].replace(':', '-')}|u{d['user_id']}|{k}"
                out[key] = {"round": d["round"], "ai": d["model"], "author_id": d["user_id"], "author": d["username"],
                            "subreddit": a.get("subreddit"), "topic": analyze_topic(a.get("subreddit")),
                            "title": str(a.get("title", "")), "body": str(a.get("body", ""))}
                k += 1
    return out


def analyze_topic(sub):
    s = str(sub or "").strip().lower().lstrip("/").removeprefix("r/")
    return next((t for t, (name, _) in TOPICS.items() if name.lower().removeprefix("r/") == s), None)


def steps_from_log(path):
    """Every finished runner step: start, end, round, kind, reader AI, screens, minutes."""
    out, start = [], {}
    for line in open(path):
        m = re.match(r"(\S+ \S+) (start|end) (r\d+ .+?)(?: \(~| rc=)", line)
        if not m:
            continue
        t, kind, what = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"), m.group(2), m.group(3)
        if kind == "start":
            start[what] = t
            continue
        e = re.search(r"rc=(\d+): (\d+) screens in ([\d.]+) min", line)
        if not e or int(e.group(2)) == 0:
            continue
        rnd = int(what.split()[0][1:])
        who = re.search(r"(qwen3:8b|llama3\.1:8b|gemma3:12b)", what).group(1)
        typ = "posting" if " post " in f" {what} " else "noise floor" if "noise" in what else "baseline" if "BASELINE" in what else "cross"
        out.append({"round": rnd, "step": what, "type": typ, "ai": who, "start": start.get(what, t), "end": t,
                     "screens": int(e.group(2)), "minutes": float(e.group(3)),
                     "users": 10 if rnd >= 900 else 100})
    best = {}
    for s in out:
        if s["type"] != "posting" and s["users"] == 100 and s["screens"] >= 400:
            sp = s["minutes"] * 60 / s["screens"]
            best[s["ai"]] = min(best.get(s["ai"], 9e9), sp)
    for s in out:
        s["s_per_screen"] = s["minutes"] * 60 / s["screens"]
        s["gpu"] = "free" if s["type"] == "posting" or s["s_per_screen"] <= 1.25 * best.get(s["ai"], 9e9) else "shared"
    return out, best


# ---------------------------------------------------------------- graphs
def save(fig, out, name):
    p = os.path.join(out, "graphs", name)
    fig.savefig(p)
    plt.close(fig)
    return p


def rate(rows, f):
    return 100 * sum(f(r) for r in rows) / len(rows) if rows else float("nan")


def heat(ax, M, title, fmt="{:.1f}%", ylab=True):
    import numpy as np
    A = np.array(M, dtype=float)
    ax.imshow(A, cmap="Blues", vmin=0, vmax=max(1e-9, np.nanmax(A)) * 1.15)
    for i in range(3):
        for j in range(3):
            v = A[i, j]
            dark = v > np.nanmax(A) * 0.62
            ax.text(j, i, fmt.format(v), ha="center", va="center", fontsize=9.5,
                    color="white" if dark else INK, fontweight="bold" if i == j else "normal")
        ax.add_patch(Rectangle((i - .5, i - .5), 1, 1, fill=False, ec=INK, lw=1.6))  # baseline = diagonal
    ax.set_xticks(range(3), [SHORT[m] for m in MODELS])
    ax.set_yticks(range(3), [SHORT[m] for m in MODELS])
    ax.set_xlabel("posts written by", fontsize=8.5)
    if ylab:
        ax.set_ylabel("AI playing the users", fontsize=8.5)
    ax.grid(False)
    ax.set_title(title, fontsize=10)


def graphs(out, R, post_rows, posts, steps, best, rnd, bias, noise, label):
    os.makedirs(os.path.join(out, "graphs"), exist_ok=True)
    files = []
    cell = {(m, pb): [r for r in R if r["model"] == m and r["posts_by"] == pb] for m in MODELS for pb in MODELS}
    has = lambda a: (lambda r: any(x["action"] == a for x in r["actions"]))
    eng = lambda r: sum(x["action"] != "do_nothing" for x in r["actions"])  # LD-43: total engagement, the main measure
    engaged = lambda r: any(x["action"] != "do_nothing" for x in r["actions"])

    # G1: 3x3 grids for the main engagement measures
    meas = [("TOTAL ENGAGEMENT\n(actions per 100 screens)", eng, "{:.0f}"), ("engaged: any action (%)", engaged, "{:.1f}%"),
            ("upvote (%)", has("like_post"), "{:.1f}%"), ("downvote (%)", has("dislike_post"), "{:.1f}%"),
            ("comment (%)", has("create_comment"), "{:.1f}%"), ("report (%)", has("report_post"), "{:.1f}%"),
            ("follow (%)", has("follow"), "{:.1f}%"), ("share (repost) (%)", has("repost"), "{:.1f}%"),
            ("search posts (%)", has("search_posts"), "{:.1f}%"), ("chose 'do nothing' (%)", has("do_nothing"), "{:.1f}%")]
    fig, axs = plt.subplots(2, 5, figsize=(17, 7.6))
    for k, (ax, (t, f, fm)) in enumerate(zip(axs.flat, meas)):
        heat(ax, [[rate(cell[(m, pb)], f) for pb in MODELS] for m in MODELS], t, fmt=fm, ylab=k % 5 == 0)
    fig.subplots_adjust(wspace=0.3, hspace=0.45)
    fig.suptitle(f"{label}: AI playing the users (rows) x AI that wrote the posts (columns). First grid = total engagement "
                 f"(every action except 'do nothing'); the rest = % of screens with that action. Boxed diagonal = baseline.",
                 fontsize=11.5, x=.5, y=1.0)
    files.append(save(fig, out, "01_engagement_3x3_grids.png"))

    # G1b: one big upvote grid + did-anything grid with counts
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.8))
    for ax, (t, f, fm) in zip(axs, meas[:2]):
        heat(ax, [[rate(cell[(m, pb)], f) for pb in MODELS] for m in MODELS], t, fmt=fm)
    fig.suptitle(f"{label}: the headline - total engagement across all 27 actions", fontsize=12, y=1.04)
    files.append(save(fig, out, "02_total_engagement_grids.png"))

    # G2: all 27 actions, per reader x poster, per 100 screens
    tot = Counter(x["action"] for r in R for x in r["actions"])
    order = sorted(ACTION_NAMES, key=lambda a: -tot[a])
    fig, axs = plt.subplots(1, 3, figsize=(17, 9.5), sharey=True)
    import numpy as np
    y = np.arange(len(order))
    for ax, m in zip(axs, MODELS):
        for k, pb in enumerate(MODELS):
            rs = cell[(m, pb)]
            v = [100 * sum(sum(x["action"] == a for x in r["actions"]) for r in rs) / len(rs) for a in order]
            ax.barh(y + (k - 1) * 0.27, v, height=0.25, color=COLOR[pb], label=f"posts by {SHORT[pb]}")
        ax.set_title(f"{SHORT[m]} playing the users", color=INK)
        ax.set_xlabel("times used per 100 screens")
        ax.grid(axis="y", visible=False)
    axs[0].set_yticks(y, [f"{lbl(a)}" + ("  (never used)" if tot[a] == 0 else "") for a in order])
    axs[0].invert_yaxis()
    axs[0].legend(loc="lower right", frameon=False)
    fig.suptitle(f"{label} reading turn: every one of the 27 OASIS actions the users could take, per 100 screens",
                 fontsize=12)
    files.append(save(fig, out, "03_all_27_actions_reading.png"))

    # G3: posting turn
    fig, axs = plt.subplots(1, 3, figsize=(17, 6.8), gridspec_kw={"width_ratios": [1, 1.25, 1.6]})
    P = [d for d in post_rows if d["round"] == rnd]
    ax = axs[0]
    for k, m in enumerate(MODELS):
        rs = [d for d in P if d["model"] == m]
        wrote = sum(any(x["action"] == "create_post" for x in d["actions"]) for d in rs)
        n = sum(sum(x["action"] == "create_post" for x in d["actions"]) for d in rs)
        ax.bar([k - .18], [wrote], width=.34, color=COLOR[m])
        ax.bar([k + .18], [n], width=.34, color=COLOR[m], alpha=.55)
        ax.text(k - .18, wrote + 1.5, str(wrote), ha="center", fontsize=9, color=INK)
        ax.text(k + .18, n + 1.5, str(n), ha="center", fontsize=9, color=INK)
    ax.set_xticks(range(3), [SHORT[m] for m in MODELS])
    ax.set_title("users who posted (solid) / posts written (light)\nout of 100 users, empty feed")
    ax = axs[1]
    tops = list(TOPICS)
    for k, m in enumerate(MODELS):
        c = Counter(p["topic"] for p in posts.values() if p["round"] == rnd and p["ai"] == m)
        ax.barh(np.arange(5) + (k - 1) * .27, [c[t] for t in tops], height=.25, color=COLOR[m], label=SHORT[m])
    ax.set_yticks(range(5), [TOPICS[t][0] for t in tops])
    ax.invert_yaxis()
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("posts per subreddit")
    ax.grid(axis="y", visible=False)
    ax = axs[2]
    pt = Counter(x["action"] for d in P for x in d["actions"])
    po = sorted(ACTION_NAMES, key=lambda a: -pt[a])
    for k, m in enumerate(MODELS):
        c = Counter(x["action"] for d in P if d["model"] == m for x in d["actions"])
        ax.barh(np.arange(len(po)) + (k - 1) * .27, [c[a] for a in po], height=.25, color=COLOR[m], label=SHORT[m])
    ax.set_yticks(range(len(po)), [lbl(a) + ("  (never)" if pt[a] == 0 else "") for a in po], fontsize=8)
    ax.invert_yaxis()
    ax.set_title("every action taken in the posting turn (count)")
    ax.grid(axis="y", visible=False)
    fig.suptitle(f"Round {rnd} posting turn: each AI plays all 100 users on an empty feed; nobody is told to post",
                 fontsize=12)
    fig.subplots_adjust(wspace=0.5)
    files.append(save(fig, out, "04_posting_turn.png"))

    # G4: stance
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.8), sharey=True)
    for ax, m in zip(axs, MODELS):
        for pb in MODELS:
            rs = cell[(m, pb)]
            v = [rate([r for r in rs if r["stance"] == s], eng) for s in STANCES]
            ax.plot(range(5), v, marker="o", ms=6, lw=2, color=COLOR[pb], label=f"posts by {SHORT[pb]}")
        ax.set_xticks(range(5), [s.lower() for s in STANCES])
        ax.set_title(f"{SHORT[m]} playing the users")
        ax.set_xlabel("how the user feels about the post's topic")
    axs[0].set_ylabel("total engagement (actions per 100 screens)")
    axs[0].legend(frameon=False)
    fig.suptitle(f"{label}: total engagement by the user's stance on the post's topic", fontsize=12)
    files.append(save(fig, out, "05_engagement_by_stance.png"))

    # G5: topic grid per reader
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.6), sharey=True)
    for ax, m in zip(axs, MODELS):
        for k, pb in enumerate(MODELS):
            rs = cell[(m, pb)]
            v = [rate([r for r in rs if r.get("topic") == t], eng) for t in tops]
            ax.bar(np.arange(5) + (k - 1) * .27, v, width=.25, color=COLOR[pb], label=f"posts by {SHORT[pb]}")
        ax.set_xticks(range(5), [TOPICS[t][0].replace("r/", "") for t in tops], fontsize=8.5)
        ax.set_title(f"{SHORT[m]} playing the users")
        ax.grid(axis="x", visible=False)
    axs[0].set_ylabel("total engagement (actions per 100 screens)")
    axs[0].legend(frameon=False, fontsize=8)
    fig.suptitle(f"{label}: total engagement by the post's subreddit", fontsize=12)
    files.append(save(fig, out, "06_engagement_by_topic.png"))

    # G6: bias forest
    fig, ax = plt.subplots(figsize=(10, 4.6))
    labels = []
    for k, b in enumerate(bias):
        for off, (key, col, name) in enumerate([("tot", "#2a78d6", "TOTAL ENGAGEMENT (actions per 100 screens)"),
                                               ("any", "#4a3aa7", "engaged: any action (points)"),
                                               ("up", "#9aa3ad", "upvote (points)")]):
            v, lo, hi = b[key]
            yy = k * 1.0 + (off - 1) * .26
            ax.plot([lo, hi], [yy, yy], color=col, lw=2.6 if key == "tot" else 1.8)
            ax.plot([v], [yy], "o", color=col, ms=9 if key == "tot" else 7, mec="white", mew=1.5, label=name if k == 0 else None)
            ax.text(hi + .4, yy, f"{v:+.1f}", va="center", fontsize=9, color=INK)
        labels.append(f"{SHORT[b['i']]} vs {SHORT[b['j']]}")
    ax.axvline(0, color=INK, lw=1)
    ax.set_yticks(range(len(bias)), labels)
    ax.invert_yaxis()
    ax.set_xlabel("own-AI bias, points per 100 screens (dot = estimate, line = 95% range)")
    ax.legend(frameon=False, loc="lower left", fontsize=8.5)
    ax.grid(axis="y", visible=False)
    ax.set_title(f"{label}: own-AI bias = (i reads i - j reads i) - (i reads j - j reads j).\n"
                 "Above 0 = favours its own AI's posts; below 0 = favours the other AI's; a range crossing 0 = no clear bias")
    files.append(save(fig, out, "07_own_ai_bias.png"))

    # G7: noise floor
    fig, ax = plt.subplots(figsize=(9, 3.8))
    for k, m in enumerate(MODELS):
        if m in noise:
            n = noise[m]
            ax.barh([k - .18], [n["same_eng"]], color=COLOR[m], height=.34)
            ax.barh([k + .18], [n["same_n"]], color=COLOR[m], height=.34, alpha=.5)
            ax.text(n["same_eng"] + 1, k - .18, f"same engaged / not: {n['same_eng']:.1f}%", va="center", fontsize=8.5)
            ax.text(n["same_n"] + 1, k + .18, f"same number of actions: {n['same_n']:.1f}%   (engagement {n['ta']:.0f} -> {n['tb']:.0f} per 100)",
                    va="center", fontsize=8.5)
    ax.set_yticks(range(3), [SHORT[m] for m in MODELS])
    ax.set_xlim(0, 175)
    ax.set_xticks(range(0, 101, 20))
    ax.invert_yaxis()
    ax.set_xlabel("% of re-read screens that came out the same")
    ax.grid(axis="y", visible=False)
    ax.set_title(f"{label} noise floor: same AI, same post, same user, fresh randomness")
    files.append(save(fig, out, "08_noise_floor.png"))

    # G8: actions per screen
    fig, ax = plt.subplots(figsize=(10, 4))
    for k, m in enumerate(MODELS):
        rs = [r for pb in MODELS for r in cell[(m, pb)]]
        c = Counter(min(len(r["actions"]), 6) for r in rs)
        ax.bar(np.arange(7) + (k - 1) * .27, [100 * c[i] / len(rs) for i in range(7)], width=.25, color=COLOR[m], label=SHORT[m])
    ax.set_xticks(range(7), ["0", "1", "2", "3", "4", "5", "6+"])
    ax.set_xlabel("actions the user took on one screen")
    ax.set_ylabel("% of screens")
    ax.legend(frameon=False, title="AI playing the users")
    ax.grid(axis="x", visible=False)
    ax.set_title(f"{label}: how many actions per screen")
    files.append(save(fig, out, "09_actions_per_screen.png"))

    # ------------------------------------------------------------ time graphs (GPU-free steps only where speed matters)
    real = [s for s in steps if s["users"] == 100 and s["type"] != "posting" and s["screens"] >= 50]
    fig, ax = plt.subplots(figsize=(9, 4))
    for k, m in enumerate(MODELS):
        for off, g, a in ((-.2, "free", 1), (.2, "shared", .45)):
            ss = [s for s in real if s["ai"] == m and s["gpu"] == g]
            if ss:
                v = sum(s["minutes"] * 60 for s in ss) / sum(s["screens"] for s in ss)
                ax.bar([k + off], [v], width=.38, color=COLOR[m], alpha=a)
                ax.text(k + off, v + .05, f"{v:.2f} s\n{g}", ha="center", fontsize=8.5, color=INK)
    ax.set_xticks(range(3), [SHORT[m] for m in MODELS])
    ax.set_ylabel("seconds per screen (8 at a time)")
    ax.set_title("Speed on the DGX Spark: GPU to ourselves (solid) vs shared with another user's jobs (light)")
    ax.grid(axis="x", visible=False)
    files.append(save(fig, out, "10_time_speed_per_ai.png"))

    fig, ax = plt.subplots(figsize=(9, 5))
    for m in MODELS:
        ss = [s for s in real if s["ai"] == m and s["gpu"] == "free"]
        ax.scatter([s["screens"] for s in ss], [s["minutes"] for s in ss], color=COLOR[m], s=36, label=f"{SHORT[m]} ({best[m]:.2f}-{max(s['s_per_screen'] for s in ss):.2f} s/screen)", zorder=3)
        sl = sum(s["minutes"] for s in ss) / sum(s["screens"] for s in ss)
        xs = np.array([0, max(s["screens"] for s in ss) * 1.05])
        ax.plot(xs, xs * sl, color=COLOR[m], lw=1.5, alpha=.7)
    ax.set_xlabel("screens in the step")
    ax.set_ylabel("minutes")
    ax.legend(frameon=False)
    ax.set_title("Every real-round step with the GPU free: time grows in a straight line with the screens")
    files.append(save(fig, out, "11_time_minutes_vs_screens.png"))

    fig, ax = plt.subplots(figsize=(14, 4.8))
    rs = sorted([s for s in steps if s["users"] == 100], key=lambda s: s["end"])
    cum, t0 = 0, rs[0]["start"]
    xs, ys = [rs[0]["start"]], [0]
    for s in rs:
        xs += [s["start"], s["end"]]
        ys += [cum, cum + s["screens"]]
        cum += s["screens"]
        if s["gpu"] == "shared":
            ax.axvspan(s["start"], s["end"], color="#eda100", alpha=.18, lw=0)
    ax.plot(xs, ys, color=INK, lw=2)
    for s in rs:
        if s["type"] == "posting":
            ax.plot([s["end"]], [ys[xs.index(s["end"])]], "v", color=COLOR[s["ai"]], ms=8)
    r102 = next((s for s in rs if s["round"] == 102), None)
    if r102:
        ax.axvline(r102["start"], color=MUTED, ls="--", lw=1)
        ax.text(r102["start"], cum * .05, " round 102 starts", fontsize=9, color=MUTED)
    ax.set_ylabel("screens done (cumulative)")
    ax.set_title("Run timeline on the Spark (100-user rounds). Yellow = GPU shared with another user's jobs; triangles = posting turns.\n"
                 "Flat stretches = no progress: Mon 00:00-Tue 09:49 llama/gemma steps failed (bug LB-v2-3, fixed), "
                 "Tue 15:03-19:08 paused for the other user, Tue 22:50-Wed 10:21 run killed (watchdog added)", loc="left")
    fig.autofmt_xdate()
    files.append(save(fig, out, "12_time_timeline.png"))

    # cost of a round vs number of users, GPU free (every user reads every post: work grows with users squared)
    sps = {m: sum(s["minutes"] * 60 for s in real if s["ai"] == m and s["gpu"] == "free") /
              sum(s["screens"] for s in real if s["ai"] == m and s["gpu"] == "free") for m in MODELS}
    ppu = {m: sum(1 for p in posts.values() if p["round"] == rnd and p["ai"] == m) / 100 for m in MODELS}
    post_s = {m: sum(s["minutes"] * 60 for s in steps if s["type"] == "posting" and s["ai"] == m and s["users"] == 100) /
                 max(1, sum(s["screens"] for s in steps if s["type"] == "posting" and s["ai"] == m and s["users"] == 100)) for m in MODELS}

    def hours(U):
        h = 0
        for m in MODELS:  # reader m reads all three post sets + its noise floor; plus each AI's posting turn
            h += U * post_s[m]
            h += sum(U * max(0, U * ppu[pb] - ppu[pb]) for pb in MODELS) * sps[m] + 4 * U * sps[m]
        return h / 3600
    U = np.array([10, 25, 50, 100, 200, 300, 500, 750, 1000])
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(U, [hours(u) for u in U], color="#2a78d6", lw=2, marker="o", ms=5)
    for u in (10, 100, 1000):
        ax.annotate(f"{u} users: {hours(u):,.1f} h" if hours(u) < 100 else f"{u} users: {hours(u):,.0f} h ({hours(u) / 24:,.0f} days)",
                    (u, hours(u)), textcoords="offset points", xytext=(8, -4), fontsize=9, color=INK)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("users (log scale)")
    ax.set_ylabel("hours for one full round (log scale)")
    ax.set_title("What one full round costs vs number of users (GPU free, measured speeds, post rates of round "
                 f"{rnd}).\nEvery user reads every post, so 10x the users = ~100x the time")
    files.append(save(fig, out, "13_time_vs_users.png"))

    fig, ax = plt.subplots(figsize=(9, 4.6))
    n = np.arange(1, 11)
    ax.plot(n, n * hours(100), color="#2a78d6", lw=2, marker="o", label="100 users, GPU free")
    ax.plot(n, n * hours(50), color="#1baf7a", lw=2, marker="o", label="50 users, GPU free")
    ax.plot(n, n * hours(25), color="#eb6834", lw=2, marker="o", label="25 users, GPU free")
    ax.set_xlabel("rounds")
    ax.set_ylabel("hours")
    ax.legend(frameon=False)
    ax.set_title(f"Hours for 1-10 full rounds (one round of 100 users = {hours(100):.1f} h with the GPU free)")
    files.append(save(fig, out, "14_time_vs_rounds.png"))
    return files, sps, ppu, post_s, hours


# ---------------------------------------------------------------- workbook
def workbook(out, R_all, post_rows, posts, steps, best, rnd, bias, noise, people, gfiles, sps, hours, label, complete):
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter as L

    F = lambda **k: Font(name="Arial", **k)
    BLUE, HEAD = F(color="0000FF"), F(bold=True, color="FFFFFF")
    HFILL, YFILL, DFILL = PatternFill("solid", fgColor="2A4D69"), PatternFill("solid", fgColor="FFFF00"), PatternFill("solid", fgColor="E8EEF4")
    thin = Side(style="thin", color="BFBFBF")
    BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
    wb = Workbook()
    wb._fonts[0] = Font(name="Arial", size=10)  # every cell without its own font is Arial (80k-row sheet: no per-cell styling)

    def sheet(name, title, note):
        ws = wb.create_sheet(name)
        ws["A1"] = title
        ws["A1"].font = F(bold=True, size=14)
        ws["A2"] = note
        ws["A2"].font = F(italic=True, color="555555")
        ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells("A2:N2")
        ws.row_dimensions[2].height = 64
        return ws

    def header(ws, row, names, col=1):
        for k, n in enumerate(names):
            c = ws.cell(row, col + k, n)
            c.font, c.fill, c.alignment, c.border = HEAD, HFILL, Alignment(wrap_text=True, vertical="center"), BOX

    # ---- Screens (raw data; every formula counts this sheet)
    S = wb.create_sheet("Screens")
    cols = ["Round", "Person #", "Username", "AI playing the user", "Posts written by AI", "Own AI's post?", "Re-read (noise)?",
            "Post ID", "Post author #", "Topic", "Person's stance on topic", "Scroll position", "Outcome", "Did anything (1/0)",
            "Actions on this screen"] + [lbl(a) if a in LABEL else a for a in ACTION_NAMES] + \
           ["Comment text", "Quote text", "Report reason", "Reason given", "Seconds (one call)", "Prompt tokens", "Output tokens",
            "Total engagement (actions except 'do nothing')", "In the round picker's selection (1/0)"]
    header(S, 1, cols)
    acol = {a: 16 + k for k, a in enumerate(ACTION_NAMES)}
    R_all = sorted(R_all, key=lambda r: (r["round"], r["model"], r["posts_by"], r["draw"], r["user_id"], r["pos"]))
    sel = len(cols)
    pooled_or = ",".join(f"A{{i}}={c}" for c in complete)
    for i, r in enumerate(R_all, 2):
        c = Counter(x["action"] for x in r["actions"])
        first = lambda a, f: next((str(x.get(f, ""))[:500] for x in r["actions"] if x["action"] == a), "")
        S.append([r["round"], r["user_id"], r["username"], r["model"], r["posts_by"], "yes" if r["model"] == r["posts_by"] else "no",
                  r["draw"], r["post_key"], r.get("author_id"), TOPICS.get(r.get("topic"), ("", r.get("topic")))[1], r.get("stance"),
                  r["pos"] + 1, r["outcome"], int(any(x["action"] != "do_nothing" for x in r["actions"])), len(r["actions"])]
                 + [c[a] for a in ACTION_NAMES]
                 + [first("create_comment", "content"), first("quote_post", "content"), first("report_post", "reason"),
                    (r.get("reason") or "")[:300], r.get("latency_s"), r.get("prompt_tokens"), r.get("eval_tokens"),
                    sum(x["action"] != "do_nothing" for x in r["actions"])])
        S.cell(i, sel, f'=IF(\'Engagement 3x3\'!$B$4="pooled",IF(OR({pooled_or.format(i=i)}),1,0),IF(A{i}=\'Engagement 3x3\'!$B$4,1,0))')
    N = S.max_row
    S.freeze_panes = "D2"
    S.auto_filter.ref = f"A1:{L(len(cols))}{N}"
    for k, w in enumerate([7, 8, 13, 14, 14, 9, 8, 26, 8, 22, 12, 9, 10, 9, 9] + [8] * 27 + [40, 30, 20, 40, 9, 9, 9]):
        S.column_dimensions[L(k + 1)].width = w
    rng = lambda col: f"Screens!${col}$2:${col}${N}"
    cA, cD, cE, cG, cJ, cK, cM, cN = (rng(x) for x in "ADEGJKMN")
    cSel = rng(L(sel))
    cEng = rng(L(sel - 1))  # total engagement per screen
    base = lambda R, P, rcell: f'{cSel},1,{cD},"{R}",{cE},"{P}",{cG},0,{cM},"chose"'  # rcell kept for call sites

    # ---- README
    ws = wb.active
    ws.title = "README"
    ws.column_dimensions["A"].width = 130
    lines = [
        ("LLM Bias v2: do AIs favour posts written by their own AI?", F(bold=True, size=15)),
        (f"Built {datetime.now():%Y-%m-%d %H:%M} from the DGX Spark result files (data/llm_bias/v2_spark). Rounds in this file: "
         f"{sorted({r['round'] for r in R_all})}. Complete rounds: {complete} (graphs and bias ranges: {label}); a round still "
         "running is partial. The yellow round picker on 'Engagement 3x3' drives every grid and split table.", F()),
        ("", F()),
        ("How a round works", F(bold=True, size=12)),
        ("1. Posting turn: one AI plays all 100 pinned users. Each user opens Reddit to an EMPTY feed with all 27 OASIS actions "
         "available and may post or not (nobody is told to post). What they write is that AI's post set.", F()),
        ("2. Reading turn: one AI plays the same 100 users. Each user sees every post of a set except their own, ONE post per "
         "screen, and may take any number of actions on it. The user sees the subreddit, the author's username, the title and "
         "the body. Never which AI wrote it, never votes or comments by others, never anything from earlier screens.", F()),
        ("3. Every AI reads every AI's post set: a 3 x 3 grid. The diagonal (an AI reading its own AI's posts) is the baseline. "
         "Then the world is wiped: no memory, no follows carry over.", F()),
        ("", F()),
        ("Sheets", F(bold=True, size=12)),
        ("Engagement 3x3: for every measure (did anything, and each of the 27 actions) a grid: rows = AI playing the users, "
         "columns = AI that wrote the posts, value = % of screens with that action. Change the yellow round cell to see another "
         "round. All numbers are formulas counting the Screens sheet.", F()),
        ("All actions: the same nine cells as rows, with the count and % of screens for every one of the 27 actions.", F()),
        ("MAIN MEASURE = TOTAL ENGAGEMENT: every action a user takes on a screen except 'do nothing', counted across all 27 "
         "actions, per 100 screens (decision LD-43, Gordon 2026-10-08). 'Engaged' = % of screens with at least one action. "
         "Upvotes and the other single actions are shown too, as detail.", F(bold=True)),
        ("Own-AI bias: the double difference built from the Engagement grids (formulas), with the 95% range from resampling "
         "posts and users (analyze_v2.py, 1,000 draws; blue = computed in Python).", F()),
        ("By stance / By topic: upvote, downvote and did-anything % split by how the user feels about the topic, and by subreddit.", F()),
        ("Posting turn: every user x AI in the posting turn, what they did, and per-AI totals (formulas).", F()),
        ("Posts: every post in full, who wrote it, and how each AI's users reacted to it (formulas).", F()),
        ("People: the 100 pinned users, their stances, the exact description the AI is given, and their reactions (formulas).", F()),
        ("Noise floor: the same AI re-reading 4 posts per user with fresh randomness (how much answers wobble by chance).", F()),
        ("Time per step: every step the runner finished on the Spark (measured times in blue), seconds per screen, and whether "
         "another user's jobs were sharing the GPU (shared = more than 1.25x that AI's best speed).", F()),
        ("Graphs sit on the sheet they belong to, beside or below its table (and as PNG files in the graphs folder).", F()),
        ("Screens: one row per screen (one user, one post, one AI). Filter it like any table. 1/0 and counts per action.", F()),
        ("", F()),
        ("Words used", F(bold=True, size=12)),
        ("Screen: one user looking at one post and deciding what to do. Did anything: took at least one action other than "
         "'do nothing'. Own AI's post: the AI playing the user is the same AI that wrote the post. Re-read: the noise-floor "
         "repeat (left out of every other table). Outcome 'unreadable': the AI's answer could not be read after 3 tries (left out).", F()),
        ("AIs: qwen3:8b (Alibaba), llama3.1:8b (Meta), gemma3:12b (Google), all run on llama.cpp with identical sampling "
         "(temperature 0.7, top_k 40, top_p 0.9, min_p 0, repeat penalty 1.0, thinking off).", F()),
        ("", F()),
        ("Source: GitHub KGordo11/oasis, branch llm-bias. Made by examples/experiment/llm_bias/make_report_v2.py. Full write-up: "
         "RESEARCH_LOG.md Part 14 (14.32 handoff, 14.33 round 101 results).", F(italic=True, color="555555")),
    ]
    for k, (t, f) in enumerate(lines, 1):
        ws.cell(k, 1, t).font = f
        ws.cell(k, 1).alignment = Alignment(wrap_text=True, vertical="top")

    # ---- Engagement 3x3
    E = sheet("Engagement 3x3", "Engagement grids: % of screens with each action (AI playing the users x AI that wrote the posts)",
              "Rows = the AI playing the 100 users. Columns = the AI that wrote the posts. Diagonal (bold, shaded) = baseline: an "
              "AI reading its own AI's posts. Value = % of that cell's screens where the user took the action at least once. "
              "Counts on the right. Re-reads (noise floor) and unreadable answers are left out. Change the yellow cell to pick the round.")
    E["A4"], E["B4"] = "Round shown:", "pooled" if len(complete) > 1 else rnd
    E["C4"] = (f"'pooled' = the complete rounds {', '.join(map(str, complete))} together; or type one round number "
               f"({', '.join(map(str, sorted({r['round'] for r in R_all})))}). A round still running is partial.")
    E["C4"].font = F(italic=True, color="555555")
    from openpyxl.worksheet.datavalidation import DataValidation
    dv = DataValidation(type="list", formula1='"' + ",".join(["pooled"] + [str(x) for x in sorted({r["round"] for r in R_all})]) + '"')
    E.add_data_validation(dv)
    dv.add("B4")
    E["A4"].font, E["B4"].font, E["B4"].fill = F(bold=True), BLUE, YFILL
    RC = "'Engagement 3x3'!$B$4"
    E.column_dimensions["A"].width = 30
    for c in "BCDEFGHI":
        E.column_dimensions[c].width = 15
    measures = [("TOTAL ENGAGEMENT: actions per 100 screens (every action except 'do nothing'; the main measure)", "TOT"),
                ("Engaged: % of screens with at least one action", "N")] + [(f"{lbl(a)}  [{a}]", L(acol[a])) for a in ACTION_NAMES]
    row = 6
    grid_at = {}
    E.cell(row, 1, "Screens in each cell").font = F(bold=True, size=11)
    header(E, row + 1, ["AI playing the users ↓ / posts by →"] + [SHORT[m] for m in MODELS], 1)
    for i, m in enumerate(MODELS):
        E.cell(row + 2 + i, 1, SHORT[m]).font = F(bold=True)
        for j, pb in enumerate(MODELS):
            c = E.cell(row + 2 + i, 2 + j, f"=COUNTIFS({base(m, pb, RC)})")
            c.number_format, c.border = "#,##0", BOX
    row += 6
    for title, col in measures:
        E.cell(row, 1, title).font = F(bold=True, size=12 if col == "TOT" else 11, color="2A4D69" if col == "TOT" else None)
        header(E, row + 1, ["per 100 screens" if col == "TOT" else "% of screens"] + [SHORT[m] for m in MODELS], 1)
        header(E, row + 1, ["actions" if col == "TOT" else "count"] + [SHORT[m] for m in MODELS], 6)
        for i, m in enumerate(MODELS):
            E.cell(row + 2 + i, 1, SHORT[m]).font = F(bold=True)
            E.cell(row + 2 + i, 6, SHORT[m]).font = F(bold=True)
            for j, pb in enumerate(MODELS):
                cnt = E.cell(row + 2 + i, 7 + j, f"=SUMIFS({cEng},{base(m, pb, RC)})" if col == "TOT"
                             else f'=COUNTIFS({base(m, pb, RC)},{rng(col)},">0")')
                cnt.number_format, cnt.border = "#,##0", BOX
                tot = f"$%s$%d" % (L(2 + j), 8 + i)
                pc = E.cell(row + 2 + i, 2 + j, f"=IF({tot}=0,\"\",{'100*' if col == 'TOT' else ''}{L(7 + j)}{row + 2 + i}/{tot})")
                pc.number_format, pc.border = ("0.0" if col == "TOT" else "0.0%"), BOX
                if i == j:
                    pc.font, pc.fill = F(bold=True), DFILL
        grid_at[col] = row + 2
        row += 6
    E.freeze_panes = "A6"

    # ---- All actions
    A = sheet("All actions", "Every one of the 27 actions, for each AI-reads-AI cell", "Count and % of screens (formulas over Screens). "
              "Round = the yellow cell on 'Engagement 3x3'. An action can be used more than once on a screen; 'times used' counts every use.")
    header(A, 4, ["AI playing the users", "Posts by", "Own AI?", "Screens"] + [x for a in ACTION_NAMES for x in (f"{lbl(a)}: screens", "%", "times used")])
    for k, (m, pb) in enumerate([(m, pb) for m in MODELS for pb in MODELS]):
        r = 5 + k
        A.cell(r, 1, SHORT[m]); A.cell(r, 2, SHORT[pb]); A.cell(r, 3, "baseline" if m == pb else "cross")
        A.cell(r, 4, f"=COUNTIFS({base(m, pb, RC)})").number_format = "#,##0"
        for q, a in enumerate(ACTION_NAMES):
            c0 = 5 + 3 * q
            A.cell(r, c0, f'=COUNTIFS({base(m, pb, RC)},{rng(L(acol[a]))},">0")').number_format = "#,##0"
            A.cell(r, c0 + 1, f'=IF($D{r}=0,"",{L(c0)}{r}/$D{r})').number_format = "0.0%"
            A.cell(r, c0 + 2, f"=SUMIFS({rng(L(acol[a]))},{base(m, pb, RC)})").number_format = "#,##0"
    A.freeze_panes = "A5"  # rows only: frozen columns would cut the graphs below the table
    A.column_dimensions["A"].width = 18

    # ---- Own-AI bias
    B = sheet("Own-AI bias", "Own-AI bias (double difference)", "For AIs i and j: (i reading i's posts - j reading i's posts) - "
              "(i reading j's posts - j reading j's posts), in points per 100 screens. Positive = i favours its own AI's posts beyond "
              "simply being more generous with everyone. The estimate is a formula over the Engagement grids (round in the yellow cell); "
              f"the 95% range (blue) was computed in Python for {label} (resampling posts and users together, 1,000 draws) and does "
              "not change with the yellow cell.")
    header(B, 4, ["i", "j", "TOTAL ENGAGEMENT bias (actions per 100 screens)", f"95% range low ({label})", "95% range high",
                  "Engaged bias (points)", "95% range low", "95% range high", "Upvote bias (points)", "95% range low", "95% range high",
                  "Clear bias? (range excludes 0)"])
    ix = {m: k for k, m in enumerate(MODELS)}
    for k, b in enumerate(bias):
        r = 5 + k
        i, j = ix[b["i"]], ix[b["j"]]
        B.cell(r, 1, SHORT[b["i"]]); B.cell(r, 2, SHORT[b["j"]])
        for col, key, mult in ((3, "TOT", ""), (6, "N", "100*"), (9, L(acol["like_post"]), "100*")):
            g = grid_at[key]
            cellref = lambda a, bb: f"'Engagement 3x3'!{L(2 + bb)}{g + a}"
            c = B.cell(r, col, f"={mult}(({cellref(i, i)}-{cellref(j, i)})-({cellref(i, j)}-{cellref(j, j)}))")
            c.number_format = "+0.0;-0.0;0.0"
            if col == 3:
                c.font = F(bold=True)
        for col, v in ((4, b["tot"][1]), (5, b["tot"][2]), (7, b["any"][1]), (8, b["any"][2]), (10, b["up"][1]), (11, b["up"][2])):
            B.cell(r, col, round(v, 2)).font = BLUE
            B.cell(r, col).number_format = "+0.0;-0.0;0.0"
        verdict = lambda name, lo, hi: (f'IF(AND({lo}{r}<0,{hi}{r}>0),"{name}: no",IF({lo}{r}>0,"{name}: YES, favours own AI",'
                                        f'"{name}: YES, favours the other AI"))')
        B.cell(r, 12, "=" + verdict("TOTAL ENGAGEMENT", "D", "E") + '&" / "&' + verdict("engaged", "G", "H") + '&" / "&' + verdict("upvote", "J", "K"))
    B.column_dimensions["L"].width = 90
    for c in "ABCDEFGHIJK":
        B.column_dimensions[c].width = 15

    # ---- By stance / By topic
    def split_sheet(name, title, keycol, keys, keyname):
        W = sheet(name, title, f"Rows = AI playing the users x AI that wrote the posts. Columns = {keyname}. Value = % of those "
                  "screens. Round = the yellow cell on 'Engagement 3x3'. Formulas over Screens.")
        r = 4
        for mname, col in (("TOTAL ENGAGEMENT (actions per 100 screens)", "TOT"), ("Engaged: any action (% of screens)", "N"),
                           ("Upvoted (% of screens)", L(acol["like_post"])), ("Downvoted (% of screens)", L(acol["dislike_post"])),
                           ("Commented (% of screens)", L(acol["create_comment"]))):
            W.cell(r, 1, mname).font = F(bold=True, size=11)
            header(W, r + 1, ["AI playing the users", "Posts by"] + list(keys))
            for q, (m, pb) in enumerate([(m, pb) for m in MODELS for pb in MODELS]):
                rr = r + 2 + q
                W.cell(rr, 1, SHORT[m]); W.cell(rr, 2, SHORT[pb])
                for z, kv in enumerate(keys):
                    crit = f'{base(m, pb, RC)},{rng(keycol)},"{kv}"'
                    if col == "TOT":
                        W.cell(rr, 3 + z, f'=IFERROR(100*SUMIFS({cEng},{crit})/COUNTIFS({crit}),"")').number_format = "0.0"
                    else:
                        W.cell(rr, 3 + z, f'=IFERROR(COUNTIFS({crit},{rng(col)},">0")/COUNTIFS({crit}),"")').number_format = "0.0%"
                if m == pb:
                    for z in range(len(keys) + 2):
                        W.cell(rr, 1 + z).fill = DFILL
            r += 13
        for c in "ABCDEFG":
            W.column_dimensions[c].width = 22
    split_sheet("By stance", "Reactions by how the user feels about the post's topic", "K", STANCES, "the user's stance on the topic")
    split_sheet("By topic", "Reactions by the post's subreddit", "J", [TOPICS[t][1] for t in TOPICS], "the post's topic")

    # ---- Posting turn
    PT = sheet("Posting turn", "Posting turn: each AI plays the 100 users on an empty feed",
               "Top: totals per AI and round (formulas over the rows below). Below: one row per user per AI per round: what they did "
               "on the empty feed. Nobody is told to post.")
    prow0 = 48  # rows 13-46 hold the posting graph
    header(PT, prow0, ["Round", "AI playing the users", "Person #", "Username", "Posts written", "Actions taken", "Reason given"]
           + [lbl(a) if a in LABEL else a for a in ACTION_NAMES])
    PR = sorted([d for d in post_rows], key=lambda d: (d["round"], MODELS.index(d["model"]) if d["model"] in MODELS else 9, d["user_id"]))
    for d in PR:
        c = Counter(x["action"] for x in d["actions"])
        PT.append([d["round"], d["model"], d["user_id"], d["username"], c["create_post"],
                   ", ".join(x["action"] for x in d["actions"]) or "(nothing)", (d.get("reason") or "")[:300]] + [c[a] for a in ACTION_NAMES])
    pe = PT.max_row
    header(PT, 4, ["Round", "AI", "Users", "Users who posted", "Posts written", "Users who did nothing at all", "Most-used other action"])
    for k, (rr, m) in enumerate(sorted({(d["round"], d["model"]) for d in PR})):
        r = 5 + k
        PT.cell(r, 1, rr); PT.cell(r, 2, m)
        cr = f"$A${prow0 + 1}:$A${pe},{rr},$B${prow0 + 1}:$B${pe},\"{m}\""
        PT.cell(r, 3, f"=COUNTIFS({cr})")
        PT.cell(r, 4, f'=COUNTIFS({cr},$E${prow0 + 1}:$E${pe},">0")')
        PT.cell(r, 5, f"=SUMIFS($E${prow0 + 1}:$E${pe},{cr})")
        PT.cell(r, 6, f'=COUNTIFS({cr},$F${prow0 + 1}:$F${pe},"(nothing)")')
        oth = Counter(x["action"] for d in PR if d["round"] == rr and d["model"] == m for x in d["actions"] if x["action"] != "create_post")
        PT.cell(r, 7, ", ".join(f"{a} {n}" for a, n in oth.most_common(4)) or "-").font = BLUE
    PT.column_dimensions["B"].width = 16
    PT.column_dimensions["F"].width = 30
    PT.column_dimensions["G"].width = 50

    # ---- Posts
    PS = sheet("Posts", "Every post, in full, and how each AI's users reacted",
               "One row per post. Upvoted % / Did anything % = share of the users who saw this post (as played by that AI) who "
               "upvoted it / took any action. Formulas over Screens (all rounds; re-reads left out).")
    header(PS, 4, ["Round", "Written by AI", "Post ID", "Author #", "Author", "Subreddit", "Title", "Body", "Words"]
           + [f"{SHORT[m]} users: total engagement (actions per 100 screens)" for m in MODELS] + [f"{SHORT[m]} users: engaged %" for m in MODELS])
    for k, (key, p) in enumerate(sorted(posts.items(), key=lambda kv: (kv[1]["round"], MODELS.index(kv[1]["ai"]), kv[0]))):
        r = 5 + k
        PS.append([p["round"], p["ai"], key, p["author_id"], p["author"], p["subreddit"], p["title"], p["body"], len(p["body"].split())])
        for q, m in enumerate(MODELS):
            crit = f'{cD},"{m}",{rng("H")},$C{r},{cG},0,{cM},"chose"'
            PS.cell(r, 10 + q, f'=IFERROR(100*SUMIFS({cEng},{crit})/COUNTIFS({crit}),"")').number_format = "0.0"
            PS.cell(r, 13 + q, f'=IFERROR(COUNTIFS({crit},{cN},1)/COUNTIFS({crit}),"")').number_format = "0.0%"
    PS.column_dimensions["G"].width = 45
    PS.column_dimensions["H"].width = 80
    PS.column_dimensions["C"].width = 26
    PS.freeze_panes = "D5"

    # ---- People
    PE = sheet("People", "The 100 pinned users (the same 100 in every round, every turn, every AI)",
               "Built from Census / BLS / Pew data by build_population_v2.py (SHA ed110626). 'Description the AI is given' is "
               "pasted word for word into every prompt as the user's self-description. Reaction columns are formulas over Screens.")
    header(PE, 4, ["Person #", "Username", "Name", "Age", "Sex", "State", "Community", "Education", "Work", "Openness", "Conscientiousness",
                   "Extraversion", "Agreeableness", "Neuroticism"] + [f"Stance: {TOPICS[t][1]}" for t in TOPICS]
           + ["Description the AI is given"] + [f"{SHORT[m]} as this user: total engagement (per 100 screens)" for m in MODELS] + [f"{SHORT[m]}: engaged %" for m in MODELS])
    for p in people:
        r = PE.max_row + 1
        b5 = p["big_five"]
        PE.append([p["id"], p["username"], p["name"], p["age"], p["sex"], p["state"], p["community"], p["education"], p["work"],
                   b5["openness"], b5["conscientiousness"], b5["extraversion"], b5["agreeableness"], b5["neuroticism"]]
                  + [p["stances"][t] for t in TOPICS] + [p["persona"]])
        for q, m in enumerate(MODELS):
            crit = f'{cD},"{m}",{rng("B")},$A{r},{cG},0,{cM},"chose"'
            PE.cell(r, 21 + q, f'=IFERROR(100*SUMIFS({cEng},{crit})/COUNTIFS({crit}),"")').number_format = "0.0"
            PE.cell(r, 24 + q, f'=IFERROR(COUNTIFS({crit},{cN},1)/COUNTIFS({crit}),"")').number_format = "0.0%"
        PE.cell(r, 20).alignment = Alignment(wrap_text=True, vertical="top")
    PE.column_dimensions["T"].width = 70
    PE.freeze_panes = "C5"

    # ---- Noise floor
    NF = sheet("Noise floor", "Noise floor: the same AI re-reads 4 posts per user with fresh randomness",
               f"{label}. Same user, same post, same AI; only the random seed changes. 'Same decision' = the upvote choice came out "
               "the same both times. Computed in Python (blue). A real bias has to be bigger than this wobble.")
    header(NF, 4, ["AI", "Screens compared", "Same engaged / not decision %", "Same number of actions %",
                   "Total engagement, first read (per 100 screens)", "Total engagement, re-read", "Same upvote decision %",
                   "Upvote % first read", "Upvote % re-read"])
    for k, m in enumerate(MODELS):
        if m in noise:
            n = noise[m]
            vals = [m, n["n"], n["same_eng"] / 100, n["same_n"] / 100, n["ta"], n["tb"], n["same"] / 100, n["a"] / 100, n["b"] / 100]
            for z, v in enumerate(vals):
                c = NF.cell(5 + k, 1 + z, v)
                c.font = BLUE if z else F()
                c.number_format = "0.0" if z in (4, 5) else "0.0%" if z >= 2 else "General"
    for c in "ABCDEFGHI":
        NF.column_dimensions[c].width = 17

    # ---- Time per step
    T = sheet("Time per step", "Time: every step the runner finished on the DGX Spark",
              "Measured start/end, screens and minutes (blue) come from night.log. 8 screens run at a time. 'GPU' = shared when "
              "the step's seconds per screen were more than 1.25x that AI's best real-round speed (another user's jobs were on the GPU). "
              "Rounds 900+ are 10-user test rounds (the preflight). Summary at the right uses GPU-free reading steps only.")
    header(T, 4, ["Round", "Users", "Step", "Type", "AI", "Started", "Finished", "Screens", "Minutes", "Seconds per screen", "GPU"])
    st = sorted(steps, key=lambda s: s["end"])
    for k, s in enumerate(st):
        r = 5 + k
        for z, v in enumerate([s["round"], s["users"], s["step"], s["type"], s["ai"], s["start"], s["end"], s["screens"], round(s["minutes"], 2)]):
            c = T.cell(r, 1 + z, v)
            c.font = BLUE if z in (5, 6, 7, 8) else F()
            if z in (5, 6):
                c.number_format = "yyyy-mm-dd hh:mm"
        T.cell(r, 10, f"=I{r}*60/H{r}").number_format = "0.00"
        T.cell(r, 11, f'=IF(D{r}="posting","-",IF(J{r}>1.25*$O${7 + MODELS.index(s["ai"])},"shared","free"))')
    te = 4 + len(st)
    header(T, 6, ["", "AI", "Best real-round s/screen", "GPU-free s/screen (avg)", "GPU-shared s/screen (avg)", "Screens per hour (free)"], col=13)
    for k, m in enumerate(MODELS):
        r = 7 + k
        T.cell(r, 14, m)
        T.cell(r, 15, f'=MINIFS($J$5:$J${te},$E$5:$E${te},N{r},$B$5:$B${te},100,$D$5:$D${te},"<>posting",$H$5:$H${te},">=400")').number_format = "0.00"
        T.cell(r, 15).value = T.cell(r, 15).value.replace("=MINIFS(", "=_xlfn.MINIFS(")
        T.cell(r, 16, f'=SUMIFS($I$5:$I${te},$E$5:$E${te},N{r},$B$5:$B${te},100,$D$5:$D${te},"<>posting",$K$5:$K${te},"free")*60/'
                      f'SUMIFS($H$5:$H${te},$E$5:$E${te},N{r},$B$5:$B${te},100,$D$5:$D${te},"<>posting",$K$5:$K${te},"free")').number_format = "0.00"
        T.cell(r, 17, f'=IFERROR(SUMIFS($I$5:$I${te},$E$5:$E${te},N{r},$B$5:$B${te},100,$D$5:$D${te},"<>posting",$K$5:$K${te},"shared")*60/'
                      f'SUMIFS($H$5:$H${te},$E$5:$E${te},N{r},$B$5:$B${te},100,$D$5:$D${te},"<>posting",$K$5:$K${te},"shared"),"")').number_format = "0.00"
        T.cell(r, 18, f"=3600/P{r}").number_format = "#,##0"
    T.cell(11, 13, "Projected hours for one full round with the GPU free (Python, from the speeds above and round "
                   f"{rnd}'s post counts):").font = F(bold=True)
    for k, u in enumerate([10, 25, 50, 100, 200, 500, 1000]):
        T.cell(12 + k, 14, f"{u} users")
        c = T.cell(12 + k, 15, round(hours(u), 2))
        c.font, c.number_format = BLUE, "#,##0.0"
    for c, w in zip("ABCDEFGHIJKLMNOPQR", [7, 7, 52, 11, 12, 17, 17, 9, 9, 10, 8, 2, 2, 14, 14, 14, 14, 14]):
        T.column_dimensions[c].width = w
    T.freeze_panes = "A5"

    # ---- graphs: each on the sheet it belongs to, beside or below that sheet's table (no separate graphs tab)
    png = {os.path.basename(p)[:2]: p for p in gfiles}

    def place(ws, key, anchor, width, label):
        img = Image(png[key])
        k = width / img.width
        img.width, img.height = img.width * k, img.height * k
        col = re.match(r"[A-Z]+", anchor).group(0)
        row = int(anchor[len(col):])
        ws[f"{col}{row - 1}"] = label
        ws[f"{col}{row - 1}"].font = F(bold=True, color="2A4D69")
        ws.add_image(img, anchor)
        return row + int(img.height / 20) + 3  # next free row below the picture (default rows are 20 px)

    r = place(E, "01", "K7", 1050, f"Graph: total engagement + the 9 main actions ({label})")
    place(E, "02", f"K{r}", 760, "Graph: the headline - total engagement and % engaged")
    r = place(A, "03", "A17", 1050, "Graph: every one of the 27 actions, per 100 screens")
    place(A, "09", f"A{r}", 760, "Graph: how many actions per screen")
    place(B, "07", "A11", 900, "Graph: own-AI bias (total engagement first) with 95% ranges")
    place(wb["By stance"], "05", "J5", 1000, "Graph: total engagement by the user's stance")
    place(wb["By topic"], "06", "J5", 1000, "Graph: total engagement by subreddit")
    place(PT, "04", "A14", 1050, "Graph: the posting turn")
    place(NF, "08", "A11", 640, "Graph: how often a re-read comes out the same")
    r = place(T, "10", "T6", 760, "Graph: speed per AI, GPU free vs shared")
    r = place(T, "11", f"T{r}", 760, "Graph: minutes vs screens (GPU-free steps)")
    r = place(T, "12", f"T{r}", 1050, "Graph: the run timeline")
    r = place(T, "13", f"T{r}", 760, "Graph: hours per round vs number of users")
    place(T, "14", f"T{r}", 760, "Graph: hours vs number of rounds")

    # tabs: grouped, coloured by group, README first and the raw rows last
    groups = [("README", "7F7F7F", ["README"]),
              ("Results", "2A78D6", ["Engagement 3x3", "Own-AI bias", "All actions", "By stance", "By topic"]),
              ("Behaviour", "1BAF7A", ["Posting turn", "Noise floor"]),
              ("Who and what", "EB6834", ["People", "Posts"]),
              ("Run", "4A3AA7", ["Time per step"]),
              ("Raw data", "404040", ["Screens"])]
    order = [n for _, _, names in groups for n in names]
    wb._sheets = [wb[n] for n in order]
    for _, color, names in groups:
        for n in names:
            wb[n].sheet_properties.tabColor = color
    # README: a clickable list of the tabs, by group, with where each graph is
    where = {"Engagement 3x3": "grids for every action; graphs to the right", "Own-AI bias": "the bias; graph below",
             "All actions": "all 27 actions; graphs below", "By stance": "by stance; graph to the right",
             "By topic": "by subreddit; graph to the right", "Posting turn": "the posting turn; graph below the totals",
             "Noise floor": "re-read agreement; graph below", "People": "the 100 users", "Posts": "every post",
             "Time per step": "every step's timing; 5 time graphs to the right (column T)", "Screens": "one row per screen"}
    rr = ws.max_row + 2
    ws.cell(rr, 1, "Tabs (click to jump)").font = F(bold=True, size=12)
    for gname, color, names in groups[1:]:
        rr += 1
        ws.cell(rr, 1, gname).font = F(bold=True, color=color)
        for n in names:
            rr += 1
            c = ws.cell(rr, 1, f"   {n}: {where[n]}")
            c.hyperlink = f"#'{n}'!A1"
            c.font = F(color="0563C1", underline="single")
    wb.active = 0

    p = os.path.join(out, "LLM_Bias_v2.xlsx")
    wb.save(p)
    return p


def main(res, out):
    os.makedirs(out, exist_ok=True)
    reads, post_rows = load(res)
    posts = post_index(post_rows)
    people = json.load(open(os.path.join(HERE, "personas_v2.json")))
    steps, best = steps_from_log(os.path.join(res, "night.log"))
    full = sorted({r["round"] for r in reads})
    done = {int(x) for x in re.findall(r"checkpoint round (\d+): noise floor", open(os.path.join(res, "night.log")).read())}
    complete = sorted(done & set(full)) or [max(r for r in full if all(any(x["model"] == m and x["posts_by"] == pb and x["round"] == r
                                                                          for x in reads) for m in MODELS for pb in MODELS))]
    rnd = complete[-1]  # newest complete round: posting graph and post rates for the time projection
    label = f"Round {rnd}" if len(complete) == 1 else f"Rounds {', '.join(map(str, complete))} pooled"
    R = [r for r in reads if r["round"] in complete and r["outcome"] == "chose" and not r["draw"]]
    bias = []
    f_up = lambda r: int(any(x["action"] == "like_post" for x in r["actions"]))
    f_any = lambda r: int(any(x["action"] != "do_nothing" for x in r["actions"]))
    f_tot = lambda r: sum(x["action"] != "do_nothing" for x in r["actions"])
    for a in range(3):
        for b in range(a + 1, 3):
            i, j = MODELS[a], MODELS[b]
            e = {}
            for key, f in (("tot", f_tot), ("any", f_any), ("up", f_up)):
                v = analyze_v2.dd(R, i, j, f)
                lo, hi = analyze_v2.boot(R, i, j, f, n=1000)
                e[key] = (100 * v, 100 * lo, 100 * hi)
            bias.append({"i": i, "j": j, **e})
    first = {(r["model"], r["user_id"], r["post_key"]): r for r in R}
    noise = {}
    for m in MODELS:
        pairs = [(first.get((r["model"], r["user_id"], r["post_key"])), r) for r in reads
                 if r["round"] in complete and r["draw"] and r["model"] == m and r["outcome"] == "chose"]
        pairs = [(x, y) for x, y in pairs if x]
        if pairs:
            noise[m] = {"n": len(pairs), "same": 100 * sum(f_up(x) == f_up(y) for x, y in pairs) / len(pairs),
                        "same_eng": 100 * sum(f_any(x) == f_any(y) for x, y in pairs) / len(pairs),
                        "same_n": 100 * sum(f_tot(x) == f_tot(y) for x, y in pairs) / len(pairs),
                        "ta": 100 * sum(f_tot(x) for x, _ in pairs) / len(pairs), "tb": 100 * sum(f_tot(y) for _, y in pairs) / len(pairs),
                        "a": 100 * sum(f_up(x) for x, _ in pairs) / len(pairs), "b": 100 * sum(f_up(y) for _, y in pairs) / len(pairs)}
    gfiles, sps, ppu, post_s, hours = graphs(out, R, post_rows, posts, steps, best, rnd, bias, noise, label)
    p = workbook(out, reads, post_rows, posts, steps, best, rnd, bias, noise, people, gfiles, sps, hours, label, complete)
    grid = lambda f: {f"{m}|{pb}": round(100 * sum(f(r) for r in R if r["model"] == m and r["posts_by"] == pb) /
                                         max(1, sum(1 for r in R if r["model"] == m and r["posts_by"] == pb)), 1) for m in MODELS for pb in MODELS}
    json.dump({"label": label, "rounds": complete, "screens": len(R), "tot": grid(f_tot), "any": grid(f_any), "up": grid(f_up),
               "bias": bias, "noise": noise}, open(os.path.join(out, "results.json"), "w"), indent=1)
    print(json.dumps({"rounds": complete, "label": label, "screens_in_round": len(R), "all_screens": len(reads), "bias": bias, "noise": noise,
                      "free_s_per_screen": sps, "posts_per_user": ppu, "posting_s": post_s,
                      "hours_per_round": {u: round(hours(u), 2) for u in (10, 25, 50, 100, 1000)}, "workbook": p}, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1], os.path.expanduser(sys.argv[2]))
