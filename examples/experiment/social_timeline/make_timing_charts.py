"""Render the two cost charts as theme-aware inline SVG.

IN PLAIN WORDS
--------------
Two questions a reader asks about a simulation: how long does a round take,
and what happens if I add more people. This draws both, from measured runs
only, and writes SVG that can be pasted straight into the scaling artifact.

Re-run it whenever new runs land. It reads `data/sim4_package/` -- which means
it reads the CORRECTED round timings (B-27), sourced from each run's manifest
rather than scraped from a log.

    oasis-env/bin/python examples/experiment/social_timeline/make_timing_charts.py

Writes charts.svg fragments to data/charts/.
"""
from __future__ import annotations
import csv, collections, os, statistics as st

PKG = "data/sim4_package"
OUT = "data/charts"
W, H = 720, 380
PAD = dict(l=68, r=22, t=22, b=52)


def load():
    idx = {r["run"]: r for r in csv.DictReader(open(f"{PKG}/runs_index.csv"))}
    t = collections.defaultdict(dict)
    for r in csv.DictReader(open(f"{PKG}/round_timings.csv")):
        t[r["run"]][int(r["round"])] = float(r["wall_seconds"])
    return idx, t


def agents_of(idx, run):
    try:
        return int(idx[run]["agents"])
    except (KeyError, ValueError, TypeError):
        return None


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;")


def frame(title, sub, xlab, ylab, xs, ys, body, xticks, yticks):
    """Shared chart chrome. xs/ys are pixel-mapping closures."""
    p = []
    p.append(f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(title)}" '
             f'style="width:100%;height:auto;max-width:100%">')
    p.append(f'<title>{esc(title)}</title>')
    # horizontal gridlines
    for v in yticks:
        y = ys(v)
        p.append(f'<line x1="{PAD["l"]}" y1="{y:.1f}" x2="{W-PAD["r"]}" y2="{y:.1f}" '
                 f'stroke="var(--rule)" stroke-width="1"/>')
        p.append(f'<text x="{PAD["l"]-10}" y="{y+4:.1f}" text-anchor="end" '
                 f'font-size="11" font-family="var(--mono)" fill="var(--muted)">{v:,}</text>')
    for v, lab in xticks:
        x = xs(v)
        p.append(f'<text x="{x:.1f}" y="{H-PAD["b"]+18}" text-anchor="middle" '
                 f'font-size="11" font-family="var(--mono)" fill="var(--muted)">{esc(lab)}</text>')
    p.append(f'<line x1="{PAD["l"]}" y1="{H-PAD["b"]}" x2="{W-PAD["r"]}" y2="{H-PAD["b"]}" '
             f'stroke="var(--ink)" stroke-width="1.5"/>')
    p.extend(body)
    p.append(f'<text x="{PAD["l"]}" y="{H-10}" font-size="11.5" '
             f'font-family="var(--sans)" fill="var(--muted)">{esc(xlab)}</text>')
    p.append(f'<text transform="translate(16,{(H-PAD["b"])/2+PAD["t"]}) rotate(-90)" '
             f'text-anchor="middle" font-size="11.5" font-family="var(--sans)" '
             f'fill="var(--muted)">{esc(ylab)}</text>')
    p.append("</svg>")
    return "\n".join(p)


def chart_rounds(idx, t):
    """Cost per round: the 36-agent replicate band, and the 99-agent run."""
    ctrl = [r for r in t if r.startswith(("bank_r", "np4_val"))]
    rounds = sorted({rd for r in ctrl for rd in t[r]})
    mean = {rd: st.mean([t[r][rd] for r in ctrl if rd in t[r]]) for rd in rounds}
    sd = {rd: (st.stdev([t[r][rd] for r in ctrl if rd in t[r]])
               if len([1 for r in ctrl if rd in t[r]]) > 1 else 0.0) for rd in rounds}
    big = t.get("scale99_full", {})
    ymax = max(max(mean.values()), max(big.values(), default=0)) * 1.12
    xmax = max(rounds)
    xs = lambda v: PAD["l"] + (v / xmax) * (W - PAD["l"] - PAD["r"])
    ys = lambda v: (H - PAD["b"]) - (v / ymax) * (H - PAD["b"] - PAD["t"])

    b = []
    band_top = " ".join(f"{xs(r):.1f},{ys(mean[r]+sd[r]):.1f}" for r in rounds)
    band_bot = " ".join(f"{xs(r):.1f},{ys(mean[r]-sd[r]):.1f}" for r in reversed(rounds))
    b.append(f'<polygon points="{band_top} {band_bot}" fill="var(--measured)" '
             f'opacity="0.14" stroke="none"/>')
    line = " ".join(f"{xs(r):.1f},{ys(mean[r]):.1f}" for r in rounds)
    b.append(f'<polyline points="{line}" fill="none" stroke="var(--measured)" stroke-width="2.5"/>')
    for r in rounds:
        b.append(f'<circle cx="{xs(r):.1f}" cy="{ys(mean[r]):.1f}" r="3" fill="var(--measured)"/>')
    if big:
        br = sorted(big)
        bl = " ".join(f"{xs(r):.1f},{ys(big[r]):.1f}" for r in br)
        b.append(f'<polyline points="{bl}" fill="none" stroke="var(--corrected)" '
                 f'stroke-width="2.5" stroke-dasharray="6 4"/>')
        for r in br:
            b.append(f'<circle cx="{xs(r):.1f}" cy="{ys(big[r]):.1f}" r="3" fill="var(--corrected)"/>')
        b.append(f'<text x="{xs(br[-1])-6:.1f}" y="{ys(big[br[-1]])-12:.1f}" text-anchor="end" '
                 f'font-size="12" font-weight="600" font-family="var(--sans)" '
                 f'fill="var(--corrected)">99 agents</text>')
    # plateau marker
    pl = st.mean([mean[r] for r in rounds if r >= 4])
    b.append(f'<line x1="{xs(4):.1f}" y1="{ys(pl):.1f}" x2="{xs(xmax):.1f}" y2="{ys(pl):.1f}" '
             f'stroke="var(--measured)" stroke-width="1" stroke-dasharray="3 3" opacity="0.7"/>')
    b.append(f'<text x="{xs(xmax):.1f}" y="{ys(pl)-10:.1f}" text-anchor="end" font-size="12" '
             f'font-weight="600" font-family="var(--sans)" fill="var(--measured)">'
             f'36 agents &#183; plateau {pl:.0f}s</text>')
    yt = [v for v in range(0, int(ymax) + 1, 500)]
    xt = [(r, str(r)) for r in rounds if r % 2 == 0]
    return frame("Cost per round", "", "round", "seconds per round", xs, ys, b, xt, yt)


def comparable(idx, run):
    """Only runs at the validated prompt configuration are on one cost curve.

    Mixing configurations here is how the first version of this chart put the
    36-agent plateau at 572s: it averaged the fresh-context arm (~235s) and the
    old full-docstring runs (~500s) into the same point as the control bank
    (~765s). Those are three different simulations, not three replicates.
    """
    r = idx.get(run, {})
    return r.get("terse_tools") == "True" and r.get("arm") != "fresh_context"


MIN_CONTEXT = 8192
TRUNCATED = {"sweep_a12", "sweep_a24", "sweep_a36", "sweep_a50", "sweep_a75",
             "sweep_a99", "sweep_a36_reddit", "sweep_smoke"}


def verified_server(idx, run):
    """Did this run have a context window big enough to hold its own prompt?

    B-28: the 2026-09-11 sweep ran at Ollama's 4,096-token default. Prompts were
    truncated, the feed was the part cut, and the runs came in at a THIRD of the
    real cost -- so mixing them into this curve measures neither configuration.
    An earlier date-based version of this filter was written to exclude the
    OPPOSITE set, on the since-withdrawn F-97.

    Runs made after the guard landed record `server_context_length` in their own
    manifest, so they can answer for themselves. The named set below is the
    truncated sweep, which predates the guard and cannot.
    """
    if run in TRUNCATED:
        return False
    ctx = (idx.get(run, {}) or {}).get("server_context_length")
    try:
        return int(float(ctx)) >= MIN_CONTEXT
    except (TypeError, ValueError):
        # No recorded window. Historical runs predate the guard; they are kept
        # because B-28's re-run shows they were correct, but they are marked.
        return True


def persona_set(idx, run):
    """reddit or twitter. These are NOT one cost curve either.

    The reddit file carries age, gender, MBTI, country, profession and interests;
    the twitter file is scraped biographies with none of them. Different persona
    text is different prompt length is different cost per turn, so a point from
    one set cannot be read against a point from the other. The 36-agent control
    bank is reddit; every run above 36 agents is twitter.
    """
    p = (idx.get(run, {}) or {}).get("personas") or ""
    return "twitter" if "twitter" in p else ("reddit" if "reddit" in p else "?")


def chart_agents(idx, t):
    """Plateau cost against agent count. Measured points, one configuration."""
    pts = []
    for run, rd in t.items():
        n = agents_of(idx, run)
        if not n or not comparable(idx, run) or not verified_server(idx, run):
            continue
        plateau = [v for k, v in rd.items() if k >= 4]
        # A plateau needs more than one round. `scale99_full` has exactly one
        # round at or past 4 and F-91's own table shows it still climbing 8 %
        # into it, so its "plateau" is a ramp round and plotting it puts a point
        # at 2,086 s on a curve whose other points are settled means.
        if len(plateau) >= 3:
            pts.append((n, st.mean(plateau), run))
    # Split by persona source; the twitter set is the sweep and is the curve.
    groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for n, v, run in pts:
        groups[persona_set(idx, run)][n].append(v)
    agg = groups.get("twitter") or {}
    other = {n: st.mean(v) for n, v in groups.get("reddit", {}).items()}
    xsv = sorted(agg)
    if len(xsv) < 2:
        # not enough sweep points yet; fall back to whatever set has the most
        best = max(groups.items(), key=lambda kv: len(kv[1]))
        agg, other, xsv = best[1], {}, sorted(best[1])
    if not xsv:
        return None
    means = {n: st.mean(agg[n]) for n in xsv}
    xmax, ymax = max(xsv) * 1.08, max(means.values()) * 1.15
    xs = lambda v: PAD["l"] + (v / xmax) * (W - PAD["l"] - PAD["r"])
    ys = lambda v: (H - PAD["b"]) - (v / ymax) * (H - PAD["b"] - PAD["t"])

    b = []
    # proportional reference through the smallest measured point
    n0 = xsv[0]
    rate = means[n0] / n0
    b.append(f'<line x1="{xs(0):.1f}" y1="{ys(0):.1f}" x2="{xs(xmax):.1f}" '
             f'y2="{ys(rate*xmax):.1f}" stroke="var(--muted)" stroke-width="1.2" '
             f'stroke-dasharray="5 5" opacity="0.75"/>')
    b.append(f'<text x="{xs(xmax)-4:.1f}" y="{ys(rate*xmax)+16:.1f}" text-anchor="end" '
             f'font-size="11.5" font-family="var(--sans)" fill="var(--muted)">'
             f'exactly proportional ({rate:.1f}s per agent)</text>')
    line = " ".join(f"{xs(n):.1f},{ys(means[n]):.1f}" for n in xsv)
    b.append(f'<polyline points="{line}" fill="none" stroke="var(--measured)" stroke-width="2.5"/>')
    for n, v in sorted(other.items()):
        if v <= ymax and n <= xmax:
            b.append(f'<circle cx="{xs(n):.1f}" cy="{ys(v):.1f}" r="4.5" '
                     f'fill="none" stroke="var(--corrected)" stroke-width="2"/>')
            b.append(f'<text x="{xs(n)+9:.1f}" y="{ys(v)+4:.1f}" font-size="11" '
                     f'font-family="var(--sans)" fill="var(--corrected)">'
                     f'reddit personas, {v:.0f}s</text>')
    for n in xsv:
        b.append(f'<circle cx="{xs(n):.1f}" cy="{ys(means[n]):.1f}" r="4.5" '
                 f'fill="var(--measured)"/>')
        b.append(f'<text x="{xs(n):.1f}" y="{ys(means[n])-13:.1f}" text-anchor="middle" '
                 f'font-size="11" font-family="var(--mono)" font-weight="600" '
                 f'fill="var(--ink)">{means[n]:.0f}s</text>')
    step = 500 if ymax > 2000 else 250
    yt = [v for v in range(0, int(ymax) + 1, step)]
    xt = [(n, str(n)) for n in xsv]
    return frame("Plateau cost by world size", "", "agents", "seconds per round",
                 xs, ys, b, xt, yt)


def chart_rounds_by_agents(idx, t):
    """Per-round cost, one line per world size. The third chart Gordon asked for.

    `chart_rounds` shows the SHAPE for one configuration. This shows how that
    shape changes with world size: whether bigger worlds ramp for longer, or
    just sit higher. They sit higher -- the ramp takes the same three rounds at
    every size, which is what a context window filling at a fixed rate predicts.
    """
    runs = []
    for run, rd in t.items():
        n = agents_of(idx, run)
        if not n or not comparable(idx, run) or not verified_server(idx, run):
            continue
        if len(rd) >= 6 and run.startswith("ctx8192_a") and "reddit" not in run:
            runs.append((n, rd, run))
    if len(runs) < 2:
        return None
    runs.sort()
    xmax = max(max(rd) for _, rd, _ in runs)
    ymax = max(max(rd.values()) for _, rd, _ in runs) * 1.15
    xs = lambda v: PAD["l"] + (v / xmax) * (W - PAD["l"] - PAD["r"])
    ys = lambda v: (H - PAD["b"]) - (v / ymax) * (H - PAD["b"] - PAD["t"])

    b = []
    # One hue, varied by opacity: these are the same measurement at different
    # sizes, not different quantities, so they should not read as a categorical
    # palette.
    for k, (n, rd, _) in enumerate(runs):
        op = 0.45 + 0.55 * (k / max(len(runs) - 1, 1))
        pts = sorted(rd)
        line = " ".join(f"{xs(r):.1f},{ys(rd[r]):.1f}" for r in pts)
        b.append(f'<polyline points="{line}" fill="none" stroke="var(--measured)" '
                 f'stroke-width="2.5" opacity="{op:.2f}"/>')
        for r in pts:
            b.append(f'<circle cx="{xs(r):.1f}" cy="{ys(rd[r]):.1f}" r="3" '
                     f'fill="var(--measured)" opacity="{op:.2f}"/>')
        last = pts[-1]
        b.append(f'<text x="{xs(last)+8:.1f}" y="{ys(rd[last])+4:.1f}" '
                 f'font-size="12" font-weight="600" font-family="var(--sans)" '
                 f'fill="var(--measured)" opacity="{op:.2f}">{n} agents</text>')
    step = 200 if ymax > 600 else 100
    yt = [v for v in range(0, int(ymax) + 1, step)]
    xt = [(r, str(r)) for r in range(0, xmax + 1)]
    return frame("Cost per round by world size", "", "round",
                 "seconds per round", xs, ys, b, xt, yt)


def main():
    idx, t = load()
    os.makedirs(OUT, exist_ok=True)
    for name, svg in (("rounds", chart_rounds(idx, t)),
                      ("agents", chart_agents(idx, t)),
                      ("rounds_by_agents", chart_rounds_by_agents(idx, t))):
        if svg is None:
            print(f"  {name}: no data yet")
            continue
        p = os.path.join(OUT, f"cost_by_{name}.svg")
        open(p, "w").write(svg)
        print(f"  wrote {p}  ({len(svg):,} bytes)")


if __name__ == "__main__":
    main()
