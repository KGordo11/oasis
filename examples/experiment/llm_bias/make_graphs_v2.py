"""Graphs for LLM Bias v2: one folder per round, plus all rounds together (log Part 14).

IN PLAIN WORDS
--------------
Reads <folder>/export/*.csv (made by export_v2.py) and writes <folder>/graphs/round_NNN/ and graphs/all_rounds/:

  1_posting.png          how many posts each AI's users wrote, by subreddit (and how many users posted at all)
  2_upvote_table.png     reader AI x whose posts -> % upvoted; the diagonal is the baseline (same AI both sides)
  3_actions.png          every main action (upvote, downvote, comment, share, report, follow, did nothing), each
                         split by reader AI and whose posts
  4_stance.png           % upvoted from users who LOVE the topic down to users who HATE it: does the AI play the person?
  5_own_vs_others.png    for each reader AI: its own AI's posts next to the other AIs' posts
  6_bias.png             the fair test per pair of AIs (double difference) with a 95% range; 0 = no own-AI favouritism
  7_noise.png            same AI, same posts, re-read: how often the decision repeats (only if noise re-reads exist)
  8_bias_by_round.png    (all_rounds only) the fair test in each round and pooled: does it repeat?

Each AI has one colour everywhere: qwen blue, llama orange, gemma green (mistral yellow in the laptop round).

    python make_graphs_v2.py                      # data/llm_bias/v2
    python make_graphs_v2.py data/llm_bias/v2_spark
"""
import os, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
COLOR = {"qwen3:8b": "#2a78d6", "llama3.1:8b": "#eb6834", "gemma3:12b": "#1baf7a", "mistral:7b": "#eda100"}
SHORT = {"qwen3:8b": "qwen", "llama3.1:8b": "llama", "gemma3:12b": "gemma", "mistral:7b": "mistral"}
STANCES = ["LOVE", "LIKE", "NEUTRAL", "DISLIKE", "HATE"]
ACTIONS = [("upvote", "Upvoted"), ("downvote", "Downvoted"), ("comment", "Commented"), ("share", "Shared"),
           ("report", "Reported"), ("follow", "Followed the poster"), ("nothing", "Did nothing")]
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e3dd"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "figure.dpi": 150, "savefig.bbox": "tight"})


def short(m):
    return SHORT.get(m, m)


def ais(df):
    order = [m for m in COLOR if m in set(df.reader_ai) | set(df.posts_by_ai)]
    return order + sorted((set(df.reader_ai) | set(df.posts_by_ai)) - set(order))


def save(fig, path, note):
    fig.text(0.0, -0.02, note, fontsize=8.5, color=MUTED, ha="left", va="top", wrap=True)
    fig.savefig(path)
    plt.close(fig)


def bootstrap_dd(d, i, j, col, n=1000, seed=7):
    """Double difference for AIs i, j on column col, and a 95% range from resampling posts and users together."""
    d = d[d.reader_ai.isin([i, j]) & d.posts_by_ai.isin([i, j])]
    if d.empty or d.groupby(["reader_ai", "posts_by_ai"]).ngroups < 4:
        return None, None, None
    pk, pidx = np.unique(d.post_key, return_inverse=True)
    uk, uidx = np.unique(d.user_id, return_inverse=True)
    cell = (d.reader_ai == i).astype(int).values * 2 + (d.posts_by_ai == i).astype(int).values  # 3=ii 2=ij 1=ji 0=jj
    y = d[col].values.astype(float)

    def est(w):
        m = [np.sum(w[cell == c] * y[cell == c]) / max(np.sum(w[cell == c]), 1e-9) for c in (3, 1, 2, 0)]
        return (m[0] - m[1]) - (m[2] - m[3])  # (i on i - j on i) - (i on j - j on j)

    point = est(np.ones(len(y)))
    rng, draws = np.random.default_rng(seed), []
    for _ in range(n):
        cp = np.bincount(rng.integers(0, len(pk), len(pk)), minlength=len(pk))
        cu = np.bincount(rng.integers(0, len(uk), len(uk)), minlength=len(uk))
        draws.append(est(cp[pidx] * cu[uidx]))
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return point * 100, lo * 100, hi * 100


def round_graphs(R, P, PT, out, label):
    os.makedirs(out, exist_ok=True)
    M = ais(R)
    R = R.assign(nothing=1 - R.did_anything)
    main = R[(R.draw == 0) & (R.outcome == "chose")]
    # 1 posting
    fig, axes = plt.subplots(1, len(M), figsize=(4 * len(M), 3.2), sharey=True, squeeze=False)
    for ax, m in zip(axes[0], M):
        p = P[P.written_by_ai == m]
        sub = p.subreddit.astype(str).str.lower().str.replace("r/", "", regex=False).value_counts()
        ax.bar(sub.index, sub.values, color=COLOR.get(m, MUTED), width=0.6)
        for x, v in zip(sub.index, sub.values):
            ax.text(x, v, str(v), ha="center", va="bottom", color=INK, fontsize=9)
        users = PT[PT.ai_playing_users == m]
        ax.set_title(f"{short(m)}: {len(p)} posts, {int((users.posts_written > 0).sum())} of {len(users)} users posted",
                     fontsize=10, color=INK)
        ax.tick_params(axis="x", rotation=30)
    axes[0][0].set_ylabel("posts written")
    save(fig, os.path.join(out, "1_posting.png"), f"{label}. Posting turn: each user opened an empty feed with every "
         "action available; nobody was told to post. These posts are what every AI then read.")
    # 2 upvote table
    T = main.pivot_table(index="reader_ai", columns="posts_by_ai", values="upvote", aggfunc="mean").reindex(index=M, columns=M) * 100
    N = main.pivot_table(index="reader_ai", columns="posts_by_ai", values="upvote", aggfunc="size").reindex(index=M, columns=M)
    fig, ax = plt.subplots(figsize=(1.9 * len(M) + 1.5, 1.4 * len(M) + 1))
    ax.imshow(T.values, cmap="Blues", vmin=0, vmax=100)
    ax.grid(False)
    for a in range(len(M)):
        for b in range(len(M)):
            v = T.values[a, b]
            if not np.isnan(v):
                ax.text(b, a, f"{v:.1f}%\n(n={int(N.values[a, b])})", ha="center", va="center",
                        color="white" if v > 60 else INK, fontweight="bold" if a == b else "normal")
                if a == b:
                    ax.add_patch(plt.Rectangle((b - .5, a - .5), 1, 1, fill=False, ec=INK, lw=2))
    ax.set_xticks(range(len(M)), [f"posts by\n{short(m)}" for m in M])
    ax.set_yticks(range(len(M)), [f"{short(m)} reads" for m in M])
    ax.set_title("How often a post was upvoted", color=INK)
    save(fig, os.path.join(out, "2_upvote_table.png"), f"{label}. Each box: of the posts in that column, the share the "
         "users played by that row's AI upvoted. Outlined boxes = baseline (the same AI wrote and read). "
         "Compare down a column: same posts, only the reader changes.")
    # 3 actions
    fig, axes = plt.subplots(2, 4, figsize=(16, 7), squeeze=False)
    w = 0.8 / len(M)
    for ax, (col, name) in zip(axes.flat, ACTIONS):
        for k, pb in enumerate(M):
            vals = [100 * main[(main.reader_ai == r) & (main.posts_by_ai == pb)][col].mean() for r in M]
            xs = np.arange(len(M)) + (k - (len(M) - 1) / 2) * w
            ax.bar(xs, vals, w * 0.92, color=COLOR.get(pb, MUTED), label=f"posts by {short(pb)}")
            for x, v in zip(xs, vals):
                if not np.isnan(v):
                    ax.text(x, v, f"{v:.0f}", ha="center", va="bottom", fontsize=7.5, color=INK)
        ax.set_xticks(range(len(M)), [f"{short(r)} reads" for r in M])
        ax.set_title(f"{name} (% of posts seen)", color=INK, fontsize=10)
        ax.set_ylim(0, 105)
    axes.flat[-1].axis("off")
    h, l = axes.flat[0].get_legend_handles_labels()
    axes.flat[-1].legend(h, l, loc="center", frameon=False, title="bar colour = who wrote the post")
    save(fig, os.path.join(out, "3_actions.png"), f"{label}. Every screen showed one post; users could take any number "
         "of actions. Each bar: % of posts seen where that action was taken.")
    # 4 stance
    fig, axes = plt.subplots(1, len(M), figsize=(4.3 * len(M), 3.4), sharey=True, squeeze=False)
    for ax, r in zip(axes[0], M):
        for pb in M:
            d = main[(main.reader_ai == r) & (main.posts_by_ai == pb)]
            vals = [100 * d[d.user_stance_on_topic == s].upvote.mean() for s in STANCES]
            ax.plot(STANCES, vals, marker="o", lw=2, ms=6, color=COLOR.get(pb, MUTED), label=f"posts by {short(pb)}")
        ax.set_title(f"users played by {short(r)}", color=INK, fontsize=10)
        ax.set_ylim(0, 102)
    axes[0][0].set_ylabel("% upvoted")
    axes[0][-1].legend(frameon=False, fontsize=8)
    save(fig, os.path.join(out, "4_stance.png"), f"{label}. Each user has a fixed feeling about each topic (20 users "
         "per feeling per topic). A line falling from LOVE to HATE means the AI is playing the person.")
    # 5 own vs others
    fig, axes = plt.subplots(1, len(M), figsize=(4 * len(M), 3.3), sharey=True, squeeze=False)
    for ax, r in zip(axes[0], M):
        vals = [100 * main[(main.reader_ai == r) & (main.posts_by_ai == pb)].upvote.mean() for pb in M]
        names = [("its OWN AI" if pb == r else short(pb)) for pb in M]
        ax.bar(names, vals, color=[COLOR.get(pb, MUTED) for pb in M], width=0.6,
               edgecolor=[INK if pb == r else "none" for pb in M], linewidth=2)
        for x, v in zip(names, vals):
            if not np.isnan(v):
                ax.text(x, v, f"{v:.1f}%", ha="center", va="bottom", fontsize=9, color=INK)
        ax.set_title(f"users played by {short(r)}: % upvoted", color=INK, fontsize=10)
        ax.set_ylim(0, 105)
    save(fig, os.path.join(out, "5_own_vs_others.png"), f"{label}. For each AI playing the users: how often they upvoted "
         "posts written by their own AI (outlined) versus by the other AIs. A higher outlined bar alone is not proof: "
         "the AI may just like everything more or the posts may differ. The fair test is graph 6.")
    # 6 bias
    pairs = [(M[a], M[b]) for a in range(len(M)) for b in range(a + 1, len(M))]
    rows = []
    for i, j in pairs:
        for col, name in (("upvote", "upvotes"), ("did_anything", "did anything")):
            pt, lo, hi = bootstrap_dd(main, i, j, col)
            if pt is not None:
                rows.append((f"{short(i)} vs {short(j)}", name, pt, lo, hi))
    if rows:
        B = pd.DataFrame(rows, columns=["pair", "measure", "bias", "lo", "hi"])
        fig, axes = plt.subplots(1, 2, figsize=(11, 0.9 * len(pairs) + 1.6), sharey=True)
        for ax, name in zip(axes, ("upvotes", "did anything")):
            b = B[B.measure == name]
            ys = np.arange(len(b))
            ax.errorbar(b.bias, ys, xerr=[b.bias - b.lo, b.hi - b.bias], fmt="o", color=INK, ms=7, capsize=4, lw=1.5)
            for y, (_, x) in zip(ys, b.iterrows()):
                ax.text(x.bias, y + 0.18, f"{x.bias:+.1f}  ({x.lo:+.1f} to {x.hi:+.1f})", ha="center", fontsize=8.5, color=INK)
            ax.axvline(0, color=MUTED, lw=1)
            ax.set_ylim(-0.6, len(b) - 0.2)  # fixed room so the value label sits just above its dot
            ax.set_yticks(ys, b.pair)
            ax.set_title(f"Own-AI favouritism: {name}", color=INK, fontsize=10)
            ax.set_xlabel("points per 100 posts seen (right of 0 = favours own AI)")
        save(fig, os.path.join(out, "6_bias.png"), f"{label}. For AIs i and j: (i reading i's posts - j reading i's posts) "
             "- (i reading j's posts - j reading j's posts). This cancels 'one AI writes better posts' and 'one AI likes "
             "everything more'. Lines = 95% range from resampling posts and users; a range crossing 0 is not clear.")
        B.to_csv(os.path.join(out, "6_bias.csv"), index=False)
    # 7 noise
    redo = R[(R.draw != 0) & (R.outcome == "chose")]
    if len(redo):
        first = R[(R.draw == 0)].set_index(["reader_ai", "posts_by_ai", "user_id", "post_key"]).upvote
        redo = redo.join(first.rename("first_upvote"), on=["reader_ai", "posts_by_ai", "user_id", "post_key"]).dropna(subset=["first_upvote"])
        if len(redo):
            g = redo.groupby("reader_ai")
            same = 100 * (redo.upvote == redo.first_upvote).groupby(redo.reader_ai).mean()
            fig, ax = plt.subplots(figsize=(4 + len(same), 3))
            ax.bar([short(m) for m in same.index], same.values, color=[COLOR.get(m, MUTED) for m in same.index], width=0.55)
            for x, v, m in zip([short(m) for m in same.index], same.values, same.index):
                n = len(redo[redo.reader_ai == m])
                ax.text(x, v, f"{v:.1f}%\n(n={n})", ha="center", va="bottom", fontsize=9, color=INK)
            ax.set_ylim(0, 110)
            ax.set_title("Same AI, same post, asked again: same upvote decision", color=INK, fontsize=10)
            save(fig, os.path.join(out, "7_noise.png"), f"{label}. Noise check: each AI re-read some of its own posts "
                 "with fresh randomness. This is how much answers change by pure chance.")


def main(folder):
    ex = os.path.join(folder, "export")
    R, P, PT = (pd.read_csv(os.path.join(ex, f)) for f in ("reactions.csv", "posts.csv", "posting_turn.csv"))
    gdir = os.path.join(folder, "graphs")
    for r in sorted(R["round"].unique()):
        round_graphs(R[R["round"] == r], P[P["round"] == r], PT[PT["round"] == r],
                     os.path.join(gdir, f"round_{r:03d}"), f"Round {r}")
        print("graphs for round", r)
    if R["round"].nunique() > 1:
        round_graphs(R, P, PT, os.path.join(gdir, "all_rounds"), "All rounds pooled")
        main_ = R[(R.draw == 0) & (R.outcome == "chose")]
        M = ais(main_)
        pairs = [(M[a], M[b]) for a in range(len(M)) for b in range(a + 1, len(M))]
        rows = []
        for i, j in pairs:
            for r in sorted(main_["round"].unique()) + ["pooled"]:
                d = main_ if r == "pooled" else main_[main_["round"] == r]
                pt, lo, hi = bootstrap_dd(d, i, j, "upvote")
                if pt is not None:
                    rows.append((f"{short(i)} vs {short(j)}", str(r), pt, lo, hi))
        if rows:
            B = pd.DataFrame(rows, columns=["pair", "round", "bias", "lo", "hi"])
            fig, ax = plt.subplots(figsize=(8, 0.45 * len(B) + 1.5))
            ys = np.arange(len(B))[::-1]
            ax.errorbar(B.bias, ys, xerr=[B.bias - B.lo, B.hi - B.bias], fmt="o", color=INK, capsize=3)
            ax.set_yticks(ys, [f"{p}  ·  round {r}" for p, r in zip(B.pair, B["round"])])
            ax.axvline(0, color=MUTED, lw=1)
            ax.set_xlabel("own-AI favouritism in upvotes, points per 100 posts seen (right of 0 = favours own AI)")
            ax.set_title("Does it repeat? The fair test in each round, and all rounds pooled", color=INK, fontsize=10)
            save(fig, os.path.join(gdir, "all_rounds", "8_bias_by_round.png"), "Each dot: the double difference for "
                 "that pair of AIs in that round; lines = 95% range. If a pair's dots sit on the same side of 0 every "
                 "round, the result repeats.")
            B.to_csv(os.path.join(gdir, "all_rounds", "8_bias_by_round.csv"), index=False)
    print("graphs in", gdir)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(os.path.join(REPO, args[0]) if args else os.path.join(REPO, "data", "llm_bias", "v2"))
