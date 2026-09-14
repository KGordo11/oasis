"""F-105 charts: engagement falls with world size, and why it is a denominator.

WHY A SEPARATE SCRIPT
---------------------
`make_timing_charts.py` answers "what does a run cost". This answers "what does a
run measure", and the two have different filters: a cost chart must exclude runs
whose server was misconfigured (B-28), while an engagement chart must exclude
runs on a different PROMPT, because F-93 showed the prompt moves engagement by
3x. Folding both sets of rules into one module would make each harder to read
and would invite exactly the mistake the charts exist to prevent.

WHAT IT DRAWS
-------------
1. `engagement_by_agents.svg` -- observed engagement against agent count, with
   the one-parameter constant-budget prediction overlaid. The point of drawing
   the model is that it has NO fitted shape: K is a single average, and the curve
   is K divided by an independently measured quantity.

2. `engagement_decomposition.svg` -- the two series that produce it. Feed actions
   per agent-turn is flat across a 5x range of world size; distinct posts shown
   per agent-turn nearly doubles. Both are normalised to their value at 18 agents
   so they share an axis and the divergence is the whole story.

READ WITH THE CAVEAT IN F-105. The model's error (10.2%) sits inside the
run-to-run noise (~12%, measured from the s43 replicate), so these charts show
that the denominator accounts for the decline. They do NOT show that agent
propensity is exactly constant -- five points and one replicate cannot separate
"flat" from "mildly declining", and the chart must not be read as if they could.
"""
from __future__ import annotations
import json
import os
import statistics as st

import pandas as pd

import make_timing_charts as mtc

OUT = "data/charts"
PKG = "data/sim4_package"
RUNS = [(18, "sweep18_a18"), (36, "sweep18_a36"), (54, "sweep18_a54"),
        (72, "sweep18_a72"), (90, "sweep18_a90")]
REPLICATES = [(18, "sweep18_s43_a18")]


def series():
    """Per run: agents, turns, distinct-per-turn, hits-per-turn, engagement."""
    ex = pd.read_parquet(f"{PKG}/exposures.parquet")
    rows = []
    for n, lbl in RUNS + REPLICATES:
        p = f"data/social_timeline_{lbl}_analysis.json"
        if not os.path.exists(p):
            continue
        agents = (json.load(open(p)).get("agents") or {})
        distinct = sum(len(a.get("seen_and_acted") or [])
                       + len(a.get("seen_and_ignored") or []) for a in agents.values())
        hits = sum(len(a.get("seen_and_acted") or []) for a in agents.values())
        d = ex[ex.run == lbl]
        if not len(d) or not distinct:
            continue
        # Round 0 has no feed by construction, so turns are counted over the
        # rounds that actually produced exposures rather than over args.rounds.
        turns = n * d["round"].nunique()
        rows.append({"agents": n, "run": lbl, "turns": turns,
                     "distinct_per_turn": distinct / turns,
                     "hits_per_turn": hits / turns,
                     "engagement": 100 * hits / distinct,
                     "replicate": lbl.startswith("sweep18_s")})
    return rows


def chart_engagement(rows):
    main = [r for r in rows if not r["replicate"]]
    if len(main) < 3:
        return None
    K = st.mean(r["hits_per_turn"] for r in rows)     # the whole model
    xs_v = [r["agents"] for r in rows]
    ys_v = [r["engagement"] for r in rows] + [100 * K / r["distinct_per_turn"] for r in rows]
    x0, x1 = 0, max(xs_v) * 1.08
    y0, y1 = 0, max(ys_v) * 1.15
    L, R, T, B = mtc.PAD["l"], mtc.PAD["r"], mtc.PAD["t"], mtc.PAD["b"]
    xs = lambda v: L + (v - x0) / (x1 - x0) * (mtc.W - L - R)
    ys = lambda v: (mtc.H - B) - (v - y0) / (y1 - y0) * (mtc.H - B - T)

    body = []
    pred = sorted(((r["agents"], 100 * K / r["distinct_per_turn"]) for r in main))
    body.append('<polyline fill="none" stroke="var(--muted)" stroke-width="2" '
                'stroke-dasharray="6 4" points="'
                + " ".join(f"{xs(a):.1f},{ys(v):.1f}" for a, v in pred) + '"/>')
    obs = sorted(((r["agents"], r["engagement"]) for r in main))
    body.append('<polyline fill="none" stroke="var(--accent)" stroke-width="2.5" points="'
                + " ".join(f"{xs(a):.1f},{ys(v):.1f}" for a, v in obs) + '"/>')
    for a, v in obs:
        body.append(f'<circle cx="{xs(a):.1f}" cy="{ys(v):.1f}" r="4.5" fill="var(--accent)"/>')
        body.append(f'<text x="{xs(a):.1f}" y="{ys(v)-12:.1f}" text-anchor="middle" '
                    f'font-size="11" font-family="var(--mono)" fill="var(--ink)">{v:.1f}%</text>')
    for r in rows:
        if r["replicate"]:
            body.append(f'<circle cx="{xs(r["agents"]):.1f}" cy="{ys(r["engagement"]):.1f}" '
                        f'r="4" fill="none" stroke="var(--accent)" stroke-width="1.5"/>')
            body.append(f'<text x="{xs(r["agents"])+10:.1f}" y="{ys(r["engagement"])+4:.1f}" '
                        f'font-size="10" font-family="var(--mono)" fill="var(--muted)">'
                        f'replicate {r["engagement"]:.1f}%</text>')
    body.append(f'<text x="{mtc.W-R-6:.1f}" y="{ys(pred[-1][1])-10:.1f}" text-anchor="end" '
                f'font-size="11" font-family="var(--sans)" fill="var(--muted)">'
                f'constant-budget model (K={K:.3f})</text>')

    yt = [v for v in range(0, int(y1) + 2, 2)]
    xt = [(r["agents"], str(r["agents"])) for r in main]
    return mtc.frame(
        "Engagement falls as the population grows (F-105)",
        "one configuration, 7 rounds, seed 42 - the dashed line is K / distinct-posts-per-turn, "
        "with K a single constant and no fitted shape",
        "agents", "engagement, % of distinct posts seen", xs, ys, body, xt, yt)


def chart_decomposition(rows):
    main = sorted([r for r in rows if not r["replicate"]], key=lambda r: r["agents"])
    if len(main) < 3:
        return None
    base = main[0]
    L, R, T, B = mtc.PAD["l"], mtc.PAD["r"], mtc.PAD["t"], mtc.PAD["b"]
    x0, x1 = 0, max(r["agents"] for r in main) * 1.08
    y0, y1 = 0, 2.4
    xs = lambda v: L + (v - x0) / (x1 - x0) * (mtc.W - L - R)
    ys = lambda v: (mtc.H - B) - (v - y0) / (y1 - y0) * (mtc.H - B - T)

    body = []
    for key, colour, label in (("distinct_per_turn", "var(--accent)", "distinct posts shown per turn"),
                               ("hits_per_turn", "var(--muted)", "feed actions per turn")):
        pts = [(r["agents"], r[key] / base[key]) for r in main]
        body.append(f'<polyline fill="none" stroke="{colour}" stroke-width="2.5" points="'
                    + " ".join(f"{xs(a):.1f},{ys(v):.1f}" for a, v in pts) + '"/>')
        for a, v in pts:
            body.append(f'<circle cx="{xs(a):.1f}" cy="{ys(v):.1f}" r="4" fill="{colour}"/>')
        a, v = pts[-1]
        body.append(f'<text x="{xs(a)-8:.1f}" y="{ys(v)-10:.1f}" text-anchor="end" '
                    f'font-size="11.5" font-family="var(--sans)" fill="{colour}">'
                    f'{mtc.esc(label)} ({v:.2f}x)</text>')
    body.append(f'<line x1="{L}" y1="{ys(1.0):.1f}" x2="{mtc.W-R}" y2="{ys(1.0):.1f}" '
                f'stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 3" opacity="0.5"/>')

    yt = [0, 1, 2]
    xt = [(r["agents"], str(r["agents"])) for r in main]
    return mtc.frame(
        "Why it falls: the denominator grows, the numerator does not (F-105)",
        "both series relative to their value at 18 agents - the feed is capped at 12 slots, "
        "so what changes is how many of those twelve are new",
        "agents", "relative to 18 agents", xs, ys, body, xt, yt)


def main():
    rows = series()
    if not rows:
        print("  no engagement data found -- is the package built?")
        return 1
    os.makedirs(OUT, exist_ok=True)
    for name, svg in (("engagement_by_agents", chart_engagement(rows)),
                      ("engagement_decomposition", chart_decomposition(rows))):
        if svg is None:
            print(f"  {name}: not enough runs yet")
            continue
        p = os.path.join(OUT, f"{name}.svg")
        open(p, "w").write(svg)
        print(f"  wrote {p}  ({len(svg):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
