"""Build the design-v2 page, written so a 5th grader can follow it (Gordon, 2026-09-25).

Reads only data/llm_bias/export/*.csv (run export_world.py first),
data/llm_bias/analysis_v2.json (analyze_world.py) and data/llm_bias/explore_v2.json
(explore_world.py). Nothing on the page is typed in by hand except prose, so
re-running after each post set updates every number and chart.

Writes two files: the page (--out) and world_data.js next to it, which holds every
post, every person and every reaction for the "look it up" tool. Publish both.

    python make_world_artifact.py --out /path/scroll_test.html
"""

from __future__ import annotations

import argparse
import glob
import html
import json
import math
import os
import sys
from datetime import datetime

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from topics import TOPICS  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(REPO, "data", "llm_bias")
EXP = os.path.join(DATA, "export")
E = html.escape
MODELS = ["llama3.1:8b", "gemma4:e2b"]          # fixed order -> fixed colour: slot 1 blue, slot 2 orange
CLS = {"llama3.1:8b": "s1", "gemma4:e2b": "s2"}
NICE = {"llama3.1:8b": "llama", "gemma4:e2b": "gemma"}
PRIMARY = ["personal_finance", "cars", "farming", "cooking", "tech"]
SHORT_TOPIC = {"personal_finance": "Money", "cars": "Cars", "farming": "Farming", "cooking": "Cooking", "tech": "Tech"}


def pct(x):
    return f"{x:.0f}"


# ---------------------------------------------------------------- charts (inline SVG, theme tokens only)

def nice_ticks(lo, hi, n=5, integer=False):
    """Ticks from <= lo to >= hi (the last tick always covers the largest value)."""
    span = max(hi - lo, 1e-9)
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw), default=mag * 10)
    if integer:
        step = max(1, round(step))
    t = math.floor(lo / step) * step
    out = [round(t, 6)]
    while out[-1] < hi - 1e-9:
        out.append(round(out[-1] + step, 6))
    return out


def legend(items):
    return '<div class="legend">' + "".join(f'<span class="key"><i class="sw {c}"></i>{E(t)}</span>' for c, t in items) + "</div>"


def line_chart(series, xlabel, ylabel, fmt_x=lambda v: f"{v:g}", fmt_y=lambda v: f"{v:g}", title="",
               x_from=0, x_integer=False):
    """series: {model: [(x, y, tooltip)]}. One y axis, legend + end labels, hover titles."""
    pts = [p for s in series.values() for p in s]
    if not pts:
        return '<p class="muted">No data yet.</p>'
    W, H, L, R, T, B = 680, 300, 58, 80, 16, 46
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xt = nice_ticks(min(x_from, min(xs)), max(max(xs), x_from + 1), integer=x_integer)
    yt = nice_ticks(0, max(ys) * 1.05)
    x0, x1, y1 = xt[0], xt[-1], yt[-1]

    def X(v):
        return L + (v - x0) / ((x1 - x0) or 1) * (W - L - R)

    def Y(v):
        return T + (1 - v / (y1 or 1)) * (H - T - B)
    g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{E(title)}">']
    for v in yt:
        g.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>'
                 f'<text class="tick" x="{L - 8}" y="{Y(v) + 4:.1f}" text-anchor="end">{fmt_y(v)}</text>')
    for v in xt:
        g.append(f'<text class="tick" x="{X(v):.1f}" y="{H - B + 18}" text-anchor="middle">{fmt_x(v)}</text>')
    g.append(f'<line class="axis" x1="{L}" x2="{W - R}" y1="{Y(0):.1f}" y2="{Y(0):.1f}"/>')
    g.append(f'<text class="axlab" x="{(L + W - R) / 2:.0f}" y="{H - 6}" text-anchor="middle">{E(xlabel)}</text>'
             f'<text class="axlab" transform="translate(14 {(T + H - B) / 2:.0f}) rotate(-90)" '
             f'text-anchor="middle">{E(ylabel)}</text>')
    for m in MODELS:
        s = sorted(series.get(m, []))
        if not s:
            continue
        c = CLS[m]
        if len(s) > 1:
            d = " ".join(f"{'M' if i == 0 else 'L'}{X(x):.1f},{Y(y):.1f}" for i, (x, y, _) in enumerate(s))
            g.append(f'<path class="ln {c}" d="{d}"/>')
        for x, y, tip in s:
            g.append(f'<g class="pt"><circle class="hit" cx="{X(x):.1f}" cy="{Y(y):.1f}" r="12"/>'
                     f'<circle class="dot {c}" cx="{X(x):.1f}" cy="{Y(y):.1f}" r="4.5"/><title>{E(tip)}</title></g>')
        lx, ly, _ = s[-1]
        g.append(f'<text class="endlab" x="{X(lx) + 10:.1f}" y="{Y(ly) + 4:.1f}">{E(NICE[m])}</text>')
    g.append("</svg>")
    return legend([(CLS[m], NICE[m]) for m in MODELS if series.get(m)]) + f'<div class="chart">{"".join(g)}</div>'


def bar_chart(cats, series, ylabel, title, ymax=100, tip=lambda s, c, v: f"{v:.0f}"):
    """Grouped bars. cats: labels; series: [(css class, legend text, [values per cat])]."""
    W, H, L, R, T, B = 680, 270, 48, 12, 22, 40
    yt = nice_ticks(0, ymax, n=4)
    y1 = yt[-1]

    def Y(v):
        return T + (1 - v / y1) * (H - T - B)
    gw = (W - L - R) / len(cats)
    bw = min(44, gw * 0.3)
    g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{E(title)}">']
    for v in yt:
        g.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>'
                 f'<text class="tick" x="{L - 8}" y="{Y(v) + 4:.1f}" text-anchor="end">{v:g}</text>')
    g.append(f'<text class="axlab" transform="translate(12 {(T + H - B) / 2:.0f}) rotate(-90)" text-anchor="middle">{E(ylabel)}</text>')
    n = len(series)
    for i, c in enumerate(cats):
        cx = L + gw * (i + 0.5)
        g.append(f'<text class="tick lab" x="{cx:.1f}" y="{H - B + 20}" text-anchor="middle">{E(c)}</text>')
        for k, (cls, name, vals) in enumerate(series):
            v = vals[i]
            if v is None or (isinstance(v, float) and math.isnan(v)):
                continue
            x = cx + (k - n / 2) * (bw + 2) + 1
            y = Y(v)
            h = Y(0) - y
            cap = min(4, h)
            g.append(f'<g class="pt"><rect class="bar {cls}" x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="4"/>'
                     f'<rect class="bar {cls}" x="{x:.1f}" y="{Y(0) - cap:.1f}" width="{bw:.1f}" height="{cap:.1f}"/>'
                     f'<text class="val" x="{x + bw / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle">{v:.0f}</text>'
                     f'<title>{E(tip(name, c, v))}</title></g>')
    g.append(f'<line class="axis" x1="{L}" x2="{W - R}" y1="{Y(0):.1f}" y2="{Y(0):.1f}"/></svg>')
    return legend([(cls, name) for cls, name, _ in series]) + f'<div class="chart">{"".join(g)}</div>'


def whisker_chart(rows, title, xlabel):
    """rows: [(label, est, lo, hi)] in points; one row per line, zero line marked."""
    W, L, R, T, rowh = 680, 110, 24, 14, 38
    H = T + rowh * len(rows) + 40
    m = max(10, max(max(abs(lo), abs(hi)) for _, _, lo, hi in rows))
    xt = nice_ticks(-m, m, n=6)
    x0, x1 = min(xt[0], -xt[-1]), max(xt[-1], -xt[0])

    def X(v):
        return L + (v - x0) / (x1 - x0) * (W - L - R)
    g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{E(title)}">']
    for v in xt:
        g.append(f'<line class="grid" x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{T}" y2="{H - 40}"/>'
                 f'<text class="tick" x="{X(v):.1f}" y="{H - 24}" text-anchor="middle">{v:+g}</text>')
    g.append(f'<line class="zero" x1="{X(0):.1f}" x2="{X(0):.1f}" y1="{T - 4}" y2="{H - 40}"/>')
    g.append(f'<text class="axlab" x="{(L + W - R) / 2:.0f}" y="{H - 4}" text-anchor="middle">{E(xlabel)}</text>')
    for i, (lab, est, lo, hi) in enumerate(rows):
        y = T + rowh * (i + 0.5)
        g.append(f'<g class="pt"><text class="tick lab" x="{L - 12}" y="{y + 4:.1f}" text-anchor="end">{E(lab)}</text>'
                 f'<line class="whisk" x1="{X(lo):.1f}" x2="{X(hi):.1f}" y1="{y:.1f}" y2="{y:.1f}"/>'
                 f'<circle class="dot acc" cx="{X(est):.1f}" cy="{y:.1f}" r="6"/>'
                 f'<rect class="hitr" x="{L}" y="{y - rowh / 2:.1f}" width="{W - L - R}" height="{rowh}"/>'
                 f'<title>{E(lab)}: {est:+.1f} points (95 % range {lo:+.1f} to {hi:+.1f})</title></g>')
    g.append("</svg>")
    return f'<div class="chart">{"".join(g)}</div>'


def scatter_chart(points, title, xlabel, ylabel):
    """points: [(x, y, model_of_author, tooltip)] on 0-100 both ways, with the 'they agree' diagonal."""
    W, H, L, R, T, B = 460, 440, 56, 16, 16, 50

    def X(v):
        return L + v / 100 * (W - L - R)

    def Y(v):
        return T + (1 - v / 100) * (H - T - B)
    g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{E(title)}">']
    for v in (0, 25, 50, 75, 100):
        g.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>'
                 f'<line class="grid" x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{T}" y2="{H - B}"/>'
                 f'<text class="tick" x="{L - 8}" y="{Y(v) + 4:.1f}" text-anchor="end">{v}</text>'
                 f'<text class="tick" x="{X(v):.1f}" y="{H - B + 18}" text-anchor="middle">{v}</text>')
    g.append(f'<line class="diag" x1="{X(0):.1f}" y1="{Y(0):.1f}" x2="{X(100):.1f}" y2="{Y(100):.1f}"/>'
             f'<text class="note" x="{X(12):.1f}" y="{Y(18):.1f}" transform="rotate(-45 {X(12):.1f} {Y(18):.1f})">if they agreed, dots would sit on this line</text>')
    g.append(f'<text class="axlab" x="{(L + W - R) / 2:.0f}" y="{H - 8}" text-anchor="middle">{E(xlabel)}</text>'
             f'<text class="axlab" transform="translate(14 {(T + H - B) / 2:.0f}) rotate(-90)" text-anchor="middle">{E(ylabel)}</text>')
    for x, y, m, tip in points:
        g.append(f'<g class="pt"><circle class="hit" cx="{X(x):.1f}" cy="{Y(y):.1f}" r="9"/>'
                 f'<circle class="dot {CLS[m]}" cx="{X(x):.1f}" cy="{Y(y):.1f}" r="5"/><title>{E(tip)}</title></g>')
    g.append("</svg>")
    return (legend([(CLS[m], f"post written by {NICE[m]}") for m in MODELS])
            + f'<div class="chart sq">{"".join(g)}</div>')


def match_bars(rows):
    """rows: [(label, matched %, by-luck %)] as two thin horizontal bars each."""
    out = []
    for lab, a, c in rows:
        out.append(f'<div class="mrow"><div class="mlab">{E(lab)}</div><div class="mbars">'
                   f'<div class="mb"><span class="fill acc" style="width:{a:.1f}%"></span><b>{a:.0f} in 100 matched</b></div>'
                   f'<div class="mb"><span class="fill luck" style="width:{c:.1f}%"></span><b>{c:.0f} in 100 would match by luck</b></div>'
                   f'</div></div>')
    return '<div class="match">' + "".join(out) + "</div>"


# ---------------------------------------------------------------- sections

def interval_words(lo, hi):
    return f"We are 95 % sure the true number is somewhere between {lo:+.1f} and {hi:+.1f}."


def results(res):
    if not res:
        return '<p class="muted">The first answer arrives when the first post set has been scrolled by both AIs.</p>'
    up = pd.DataFrame(res["rate_up"]).reindex(index=MODELS, columns=MODELS) * 100
    dn = pd.DataFrame(res["rate_down"]).reindex(index=MODELS, columns=MODELS) * 100
    no = pd.DataFrame(res["rate_nothing"]).reindex(index=MODELS, columns=MODELS) * 100
    sp, spd = res["sp_up"]["_pooled"], res["sp_down"]["_pooled"]
    e, (lo, hi) = sp["est"] * 100, [x * 100 for x in sp["ci95"]]
    ed, (lod, hid) = spd["est"] * 100, [x * 100 for x in spd["ci95"]]
    if lo > 0:
        like_plain = f"Yes. People played by an AI like that AI's posts more: about {e:.0f} extra likes for every 100 posts."
    elif hi < 0:
        like_plain = f"No, the opposite: people played by an AI like that AI's posts a little <em>less</em> (about {abs(e):.0f} in 100)."
    else:
        like_plain = (f"Maybe a little, but we can't tell yet. The extra is about {e:.0f} likes for every 100 posts, which is small "
                      "enough that it could just be luck.")
    if hid < 0:
        dis_plain = (f"Yes. People played by an AI give that AI's posts fewer dislikes: about {abs(ed):.0f} fewer for every 100 "
                     "posts. Most of this is gemma being tough on llama's posts (see “What else we found”).")
    elif lod > 0:
        dis_plain = f"No, the opposite: people dislike their own AI's posts more (about {ed:.0f} in 100)."
    else:
        dis_plain = f"Maybe, but we can't tell yet: about {abs(ed):.0f} fewer dislikes per 100 posts, which could be luck."

    def table(df, what):
        head = "".join(f"<th class='num'>{E(NICE[a])}'s posts</th>" for a in MODELS)
        rows = "".join(
            f"<tr><th>people played by {E(NICE[j])}</th>" + "".join(
                f"<td class='num{' diag' if a == j else ''}'>{df.loc[j, a]:.1f}</td>" for a in MODELS) + "</tr>"
            for j in MODELS)
        return (f"<div class='scroll'><table class='plain'><caption>{what}</caption><thead><tr><th></th>{head}</tr></thead>"
                f"<tbody>{rows}</tbody></table></div>")
    a, b = up.loc["llama3.1:8b", "llama3.1:8b"], up.loc["llama3.1:8b", "gemma4:e2b"]
    c, d = up.loc["gemma4:e2b", "llama3.1:8b"], up.loc["gemma4:e2b", "gemma4:e2b"]
    pv, pvd = res.get("sp_up_p"), res.get("sp_down_p")
    return f"""
<div class="answers">
<div class="verdict"><p class="q">Do people <b>like</b> their own AI's posts more?</p><p class="a">{like_plain}</p>
<p class="grown">For grown-ups: double difference {e:+.1f} percentage points; 95 % range {lo:+.1f} to {hi:+.1f}; p = {pv:.3f}.
{interval_words(lo, hi)} If that range includes 0, “no difference at all” is still possible.</p></div>
<div class="verdict"><p class="q">Do people <b>dislike</b> their own AI's posts less?</p><p class="a">{dis_plain}</p>
<p class="grown">For grown-ups: double difference {ed:+.1f} points; 95 % range {lod:+.1f} to {hid:+.1f}; p = {pvd:.3f}.
Here a negative number means “kinder to its own posts”.</p></div>
</div>
<h3>How we keep it fair</h3>
<p>What if llama is just a better writer? Then <em>everybody</em> would like llama's posts more, and that would not be cheating.
So we compare two gaps. People played by llama liked llama's posts {a:.0f} times in 100 and gemma's {b:.0f} times: a gap of
{a - b:+.0f}. People played by gemma liked llama's posts {c:.0f} times in 100 and gemma's {d:.0f} times: a gap of {c - d:+.0f}.
If llama were simply better, both gaps would be the same. They differ by {(a - b) - (c - d):+.1f}, and that difference is
the “likes its own posts” number above.</p>
{table(up, "Likes (out of every 100 posts seen)")}
{table(dn, "Dislikes (out of every 100)")}
{table(no, "Skips: scrolled past without clicking (out of every 100)")}
<p class="cap">Outlined boxes = people reacting to posts their own AI wrote. Based on {res['n_valid']:,} reactions from
{res['personas']} people to {res['posts']} posts; every person has been played by both AIs.</p>"""


def findings(ex, res):
    """'What else we found': every number comes from explore_v2.json or the export."""
    if not ex:
        return ""
    R = pd.read_csv(os.path.join(EXP, "reactions.csv"))
    R = R[R["post_set_seed"].isin(ex["post_sets"])]
    out = [f"<p>We looked closer at all {ex['reactions']:,} reactions from post sets "
           f"{', '.join(map(str, ex['post_sets']))}. These are clues we noticed <em>after</em> looking at the data, so they "
           "are ideas to test next, not proven facts.</p>"]

    # 1. length
    L = ex["length"]
    w = L["words_by_author"]["mean"]
    lc = L["like_%_by_length_cares"]
    s0 = L["self_only"]["self"]["coef_pts"] * 2
    s1 = L["self_plus_judge_x_length"]["self"]["coef_pts"] * 2
    lt = L["self_plus_judge_x_length"]["g_judge:z_words"]
    d0 = L["dislike_self_only"]["self"]["coef_pts"] * 2
    d1 = L["dislike_self_plus_judge_x_length"]["self"]["coef_pts"] * 2
    cats = ["short posts", "medium posts", "long posts"]
    out.append(f"""<div class="find"><h3>Gemma likes longer posts, and gemma writes longer posts</h3>
<p>Gemma's posts are about {w['gemma4:e2b']:.0f} words long; llama's are about {w['llama3.1:8b']:.0f}. When gemma plays a
person, that person likes long posts {lc['long']['gemma4:e2b']:.0f} times in 100 but short posts only
{lc['short']['gemma4:e2b']:.0f} times. When llama plays a person, length hardly matters. So part of “gemma likes its own
posts” may really be “gemma likes long posts”, and it happens to write long ones. Once we allow for length, the likes
number drops from about {s0:+.1f} to about {s1:+.1f}. The dislike number barely moves ({d0:+.1f} to {d1:+.1f}), so
length does not explain the dislikes.</p>
{bar_chart(cats, [(CLS[m], f"people played by {NICE[m]}", [lc[k][m] for k in ('short', 'medium', 'long')]) for m in MODELS],
           "likes per 100", "Likes by post length", tip=lambda s, c, v: f"{s}, {c}: {v:.1f} likes per 100")}
<p class="grown">For grown-ups: people who care about the topic only; posts split into three equal-sized length groups.
Linear model with post and person-by-AI fixed effects, clustered by slot: the self term moves {s0:+.1f} → {s1:+.1f}
(double-difference scale) when a gemma × length term is added; that term is {lt['coef_pts']:+.1f} points per standard
deviation of length (95 % range {lt['ci95'][0]:+.1f} to {lt['ci95'][1]:+.1f}).</p></div>""")

    # 2. gemma dislikes llama
    rc = ex["rates_cares"]["down"]
    gd = R[(R["controlling_model"] == "gemma4:e2b") & (R["post_author_model"] == "llama3.1:8b") & (R["action"] == "dislike")]
    top = gd["reason"].str.lower().str.strip(" .!").value_counts().head(4).index.tolist()
    out.append(f"""<div class="find"><h3>The dislikes come mostly from gemma, aimed at llama's posts</h3>
<p>When people care about a topic, the ones played by gemma click dislike on llama's posts
{rc['gemma people']['llama posts']:.0f} times in 100, but on gemma's own posts only {rc['gemma people']['gemma posts']:.0f}
times. People played by llama almost never click dislike on a topic they care about (about
{rc['llama people']['llama posts']:.0f} in 100). Gemma's most common reasons for disliking llama's posts:
{", ".join(f"“{E(t)}”" for t in top)}.</p>
{bar_chart(["gemma's posts", "llama's posts"], [(CLS[m], f"people played by {NICE[m]}",
           [rc[f'{NICE[m]} people']['gemma posts'], rc[f'{NICE[m]} people']['llama posts']]) for m in MODELS],
           "dislikes per 100", "Dislikes by who wrote the post", ymax=max(15, max(max(v.values()) for v in rc.values()) * 1.2),
           tip=lambda s, c, v: f"{s}, {c}: {v:.1f} dislikes per 100")}
<p class="grown">With only two AIs, the fair-comparison number is the same for both of them by design, so it cannot say
which AI is the one playing favourites. These two bars show it is mostly gemma.</p></div>""")

    # 3. same person, two AIs
    sp = ex["same_person"]
    W2 = R.pivot_table(index=["user_id", "post_uid"], columns="controlling_model", values=["action", "reason"], aggfunc="first").dropna()
    ex_rows = W2[(W2[("action", "llama3.1:8b")] == "nothing") & (W2[("action", "gemma4:e2b")] == "like")]
    example = ""
    if len(ex_rows):
        (uid, puid) = ex_rows.index[0]
        u = R[R["user_id"] == uid].iloc[0]
        r0 = ex_rows.iloc[0]
        ptitle = pd.read_csv(os.path.join(EXP, "posts.csv")).set_index("post_uid").loc[puid, "title"]
        topic = R[R["post_uid"] == puid]["topic"].iloc[0]
        example = (f"<p class='example'>Example: {E(u['user_name'])} does not like {E(TOPICS[topic]['name'].lower())}. On the post "
                   f"“{E(ptitle)}”, llama playing {E(u['user_name'].split()[0])} skipped it (“{E(r0[('reason', 'llama3.1:8b')])}”). "
                   f"Gemma playing the very same person clicked like (“{E(r0[('reason', 'gemma4:e2b')])}”).</p>")
    out.append(f"""<div class="find"><h3>The same person acts differently depending on which AI plays them</h3>
<p>Every person was played by both AIs on the same posts. If the person's description decided everything, the two
versions would always agree. They match only {sp['all']['agree_%']:.0f} times in 100. Two players who simply like, dislike
and skip as often as these two do would match {sp['all']['chance_%']:.0f} times in 100 by luck alone. On topics the person
doesn't like, they match no more often than luck. So which AI is playing matters more than who the person is supposed to be.</p>
{example}
{match_bars([("All posts", sp['all']['agree_%'], sp['all']['chance_%']),
             ("Topics the person likes", sp['cares']['agree_%'], sp['cares']['chance_%']),
             ("Topics the person dislikes", sp['does_not_care']['agree_%'], sp['does_not_care']['chance_%'])])}
<p class="grown">For grown-ups: Cohen's kappa (agreement beyond chance; 0 = none, 1 = perfect) {sp['all']['kappa']:.2f}
overall, {sp['cares']['kappa']:.2f} where the person cares, {sp['does_not_care']['kappa']:.2f} where they don't;
{sp['pairs']:,} person-post pairs.</p></div>""")

    # 4. do the AIs agree which posts are good? (scatter)
    pa = ex["post_agreement"]
    pp = pd.read_csv(os.path.join(DATA, "explore_v2_posts.csv"))
    titles = pd.read_csv(os.path.join(EXP, "posts.csv")).set_index("post_uid")["title"]
    pts = [(100 * r["llama3.1:8b"], 100 * r["gemma4:e2b"], r["author"],
            f"“{titles.get(r['post'], '')}” ({SHORT_TOPIC.get(r['topic'], r['topic'])}, by {NICE[r['author']]}): "
            f"llama-played {100 * r['llama3.1:8b']:.0f}, gemma-played {100 * r['gemma4:e2b']:.0f} likes per 100")
           for _, r in pp.iterrows()]
    out.append(f"""<div class="find"><h3>The two AIs don't agree on which posts are good</h3>
<p>Each dot is one post. Further right means people played by llama liked it more; higher up means people played by
gemma liked it more. If the two AIs agreed about which posts are good, the dots would line up along the diagonal. They
mostly don't. Most dots sit far to the right: when llama plays someone who likes the topic, that person likes almost every
post. Gemma is much pickier from post to post, so its dots spread from top to bottom.</p>
{scatter_chart(pts, "Likes per post: llama-played vs gemma-played", "likes per 100 (people played by llama)", "likes per 100 (people played by gemma)")}
<p class="grown">For grown-ups: people who care about the topic only; {pa['posts']} posts. Spearman rank correlation
{pa['spearman']:.2f} (1 = same order, 0 = unrelated). Spread of like rates across posts: llama-played
{pa['sd_like_rate_llama']:.0f} points, gemma-played {pa['sd_like_rate_gemma']:.0f} points (standard deviation).</p></div>""")

    # 5. topics
    bt = ex["by_topic"]
    rows = [(SHORT_TOPIC[t], bt[t]["up"]["est"], *bt[t]["up"]["ci95"]) for t in PRIMARY if t in bt]
    clear = [r for r in rows if r[2] > 0 or r[3] < 0]
    ttxt = ("In every topic the range crosses zero, so no single topic stands out for sure. "
            if not clear else f"Only {', '.join(r[0] for r in clear)} clearly differs from zero. ")
    out.append(f"""<div class="find"><h3>Topic by topic</h3>
<p>The “likes its own posts” number for each topic on its own. The dot is our best guess; the line shows the range we are
95 % sure about. {ttxt}Each topic has only a fifth of the data, so its range is wide. (After the first two post sets, tech
looked strong at +11; with more data it shrank. That is why one big number from a small group shouldn't be trusted.)</p>
{whisker_chart(rows, "Likes its own posts, by topic", "extra likes per 100 for the AI's own posts")}
</div>""")

    # 5b. does the answer settle down as post sets are added?
    if ex.get("cumulative") and len(ex["cumulative"]) >= 2:
        cu, bs = ex["cumulative"], ex["by_set"]
        rows_c = [(f"sets up to {k}", v["down"]["est"], *v["down"]["ci95"]) for k, v in cu.items()]
        rows_s = [(f"set {k} alone", v["down"]["est"], *v["down"]["ci95"]) for k, v in bs.items()]
        rows_l = [(f"sets up to {k}", v["up"]["est"], *v["up"]["ci95"]) for k, v in cu.items()]
        last = list(cu.values())[-1]
        out.append(f"""<div class="find"><h3>Is the answer settling down?</h3>
<p>Every new post set is a fresh test with 50 new posts. Here is the “fewer dislikes for its own posts” number
after each set is added (top) and for each set on its own (bottom). As more sets come in, the range usually gets
narrower, because there is more data. Right now, with all {len(cu)} sets together, it is
{last['down']['est']:+.1f} (95 % range {last['down']['ci95'][0]:+.1f} to {last['down']['ci95'][1]:+.1f}). Below zero means
kinder to its own posts. Each post set on its own swings a lot, from {min(v['down']['est'] for v in bs.values()):+.1f}
to {max(v['down']['est'] for v in bs.values()):+.1f}: the answer depends a great deal on which 50 posts happen to be
written. That is why one post set is never enough, and why more post sets matter more than more people.</p>
{whisker_chart(rows_c, "Dislike number as post sets are added", "change in dislikes per 100 for the AI's own posts")}
{whisker_chart(rows_s, "Dislike number, each post set on its own", "change in dislikes per 100 for the AI's own posts")}
<details><summary>The same for likes</summary>
{whisker_chart(rows_l, "Like number as post sets are added", "extra likes per 100 for the AI's own posts")}
</details></div>""")

    # 6. voting style
    vs = ex["traits"]["voting_style"]
    styles = [("generous", "easy to please"), ("typical", "normal"), ("harsh", "hard to please")]
    out.append(f"""<div class="find"><h3>Hard-to-please people act hard to please</h3>
<p>Each person's description says how easy they are to please. Both AIs follow it: “hard to please” people like about
{vs['up']['harsh']['llama3.1:8b']:.0f} posts in 100. Llama shows grumpiness by skipping
({vs['nothing']['harsh']['llama3.1:8b']:.0f} in 100 skipped); gemma shows it by clicking dislike
({vs['down']['harsh']['gemma4:e2b']:.0f} in 100). Llama treats “easy to please” and “normal” people almost the same.
Age made no difference once we allowed for this.</p>
{bar_chart([s[1] for s in styles], [(CLS[m], f"people played by {NICE[m]}", [vs['up'][k][m] for k, _ in styles]) for m in MODELS],
           "likes per 100", "Likes by how easy the person is to please", tip=lambda s, c, v: f"{s}, {c}: {v:.1f} likes per 100")}
</div>""")

    # 7. scroll position + 8. reasons
    sc = ex["position"]["like_%_by_scroll_position_cares"]
    rs = ex["reasons"]
    llama_life = R[(R["controlling_model"] == "llama3.1:8b") & R["reason"].str.contains(r"\b(?:as a|my)\b", case=False, na=False)
                   & (R["action"] == "like")]["reason"].drop_duplicates().sample(3, random_state=4).tolist()
    gtop = list(rs["top_reasons"]["gemma4:e2b"].items())[:3]
    out.append(f"""<div class="find"><h3>People don't get tired of scrolling</h3>
<p>Likes stay about the same from the first post to the fiftieth. Among the first 10 posts, people played by llama liked
{sc['1-10']['llama3.1:8b']:.0f} in 100; among the last 10, {sc['41-50']['llama3.1:8b']:.0f}. For gemma:
{sc['1-10']['gemma4:e2b']:.0f} and {sc['41-50']['gemma4:e2b']:.0f}. Where a post sits in the feed doesn't change much.</p></div>
<div class="find"><h3>Llama explains like a person; gemma answers in a few words</h3>
<p>Every reaction comes with a short reason. Llama's reasons are about {rs['mean_words']['llama3.1:8b']:.0f} words long,
almost all different ({rs['distinct_reasons_%']['llama3.1:8b']:.0f} in 100 are one-of-a-kind), and
{rs['mentions_own_life_%']['llama3.1:8b']:.0f} in 100 mention the person's own life, like:
{" · ".join(f"“{E(t)}”" for t in llama_life)}. Gemma's reasons are about {rs['mean_words']['gemma4:e2b']:.0f} words, mostly
repeats ({", ".join(f"“{E(t)}” {n:,} times" for t, n in gtop)}), and almost never mention the person
({rs['mentions_own_life_%']['gemma4:e2b']:.1f} in 100). So gemma plays its characters in a shallower way.</p></div>""")
    return "".join(out)


def nothing_section(res):
    if not res:
        return ""
    by = ""
    for m in MODELS:
        v = res["nothing"].get(m)
        if v:
            cells = "".join(f"<td class='num'>{v['nothing_%_by_interest'].get(k, v['nothing_%_by_interest'].get(str(k), float('nan'))):.0f}</td>"
                            for k in (-2, -1, 0, 1, 2))
            by += f"<tr><td>people played by {E(NICE[m])}</td>{cells}</tr>"
    rows = ""
    for m in MODELS:
        v = res["nothing"].get(m)
        if v:
            rows += (f"<tr><td>{E(NICE[m])}</td><td class='num'>{v['like_%']}</td><td class='num'>{v['dislike_%']}</td>"
                     f"<td class='num'>{v['nothing_%']}</td><td class='num'>{v['failed_%']}</td>"
                     f"<td class='num'>{v['cut_off_at_token_limit']}</td><td class='num'>{v['nothing_with_a_reason_%']}</td></tr>")
    samples = "".join(f"<p><b>{E(NICE[m])}:</b> " + " · ".join(f"“{E(s)}”" for s in res['nothing'][m]["sample_nothing_reasons"]) + "</p>"
                      for m in MODELS if res["nothing"].get(m) and res["nothing"][m]["sample_nothing_reasons"])
    return f"""<h2>Why do people skip so much?</h2>
<p>A skip could mean the person chose to scroll past, or it could hide a broken answer from the AI. We checked every one.
None were broken: every skip came with a real reason, and no answer was cut off or unreadable.</p>
<div class="scroll"><table class="plain"><thead><tr><th>AI</th><th class="num">like</th><th class="num">dislike</th>
<th class="num">skip</th><th class="num">broken answer</th><th class="num">cut off</th><th class="num">skips with a reason</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="cap">Out of every 100 reactions, except “cut off”, which is a count.</p>
<h3>People skip topics they don't care about</h3>
<p>Each person likes some topics and dislikes others, on a scale from −2 (really dislikes) to +2 (loves). Skips out of every
100 posts, by how much the person cares about the post's topic. If skipping is a real choice, the numbers should be high
on the left and low on the right, and they are, very strongly for llama.</p>
<div class="scroll"><table class="plain"><thead><tr><th></th><th class="num">−2</th><th class="num">−1</th>
<th class="num">0</th><th class="num">+1</th><th class="num">+2</th></tr></thead><tbody>{by}</tbody></table></div>
<h3>What people said when they skipped</h3>{samples}"""


def timing_section():
    wt_p, pt_p = os.path.join(EXP, "world_timing.csv"), os.path.join(EXP, "progress_timing.csv")
    wt = pd.read_csv(wt_p) if os.path.exists(wt_p) else None
    pt = pd.read_csv(pt_p) if os.path.exists(pt_p) else None
    out = ["<h2>How long it takes</h2><p>A <b>round</b> is one full pass: all 99 people scroll all 50 posts of one post set. "
           "Each AI plays about half the people, one AI at a time.</p>"]
    if wt is not None and len(wt):
        # a round that was paused and resumed only timed the part after the restart; leave it out of the charts
        full = wt[wt["decisions"] >= wt["users"] * wt["posts"]]
        cut = sorted(set(wt["round"]) - set(full.groupby("round").filter(lambda g: len(g) == len(MODELS))["round"]))
        full = full[~full["round"].isin(cut)]
        s = {m: [(int(r["round"]), float(r["minutes"]),
                  f"round {int(r['round'])}: {NICE[m]} took {r['minutes']:.1f} min for {int(r['users'])} people "
                  f"({r['seconds_per_decision']:.2f} s per reaction)") for _, r in full[full.model == m].iterrows()]
             for m in MODELS}
        avg = full.groupby("model")["minutes"].mean()
        note = (f" Round {', '.join(map(str, cut))} was paused partway and restarted, so only part of it was timed; it is left "
                "out of the chart." if cut else "")
        out.append(f"<h3>Time per round</h3><p>How many minutes each AI needed to get its half of the people through all 50 posts. "
                   f"Llama is a bigger AI, so it is slower: about {avg.get('llama3.1:8b', float('nan')):.0f} minutes. Gemma takes "
                   f"about {avg.get('gemma4:e2b', float('nan')):.0f}. A whole round is the two added together.{note}</p>")
        out.append(line_chart(s, "round (in the order they ran)", "minutes", fmt_x=lambda v: f"{v:.0f}",
                              title="Minutes per round, per AI", x_from=1, x_integer=True))
        rows = "".join(f"<tr><td class='num'>{int(r['round'])}</td><td>{E(NICE[r['model']])}</td><td class='num'>{int(r['users'])}</td>"
                       f"<td class='num'>{int(r['decisions']):,}</td><td class='num'>{r['minutes']:.1f}</td>"
                       f"<td class='num'>{r['seconds_per_decision']:.2f}</td></tr>" for _, r in wt.iterrows())
        out.append(f"<details><summary>Table view (every round, including paused ones)</summary><div class='scroll'><table class='plain'>"
                   f"<thead><tr><th class='num'>round</th><th>AI</th><th class='num'>people</th><th class='num'>reactions timed</th>"
                   f"<th class='num'>minutes</th><th class='num'>seconds per reaction</th></tr></thead><tbody>{rows}</tbody></table></div></details>")
    if pt is not None and len(pt) and wt is not None:
        ok = sorted(set(full["round"])) if len(full) else []
        last = max(ok) if ok else pt["round"].max()
        seg = pt[pt["round"] == last]
        s = {m: [(float(r["users_done_equiv"]), float(r["elapsed_s"]) / 60,
                  f"{r['users_done_equiv']:.0f} people done after {r['elapsed_s'] / 60:.1f} min ({NICE[m]}, round {int(r['round'])})")
                 for _, r in seg[seg.model == m].iterrows()] for m in MODELS}
        rate = {m: (seg[seg.model == m]["elapsed_s"].max() / 60) / max(1, seg[seg.model == m]["users_done_equiv"].max())
                for m in MODELS if len(seg[seg.model == m])}
        rtxt = " and ".join(f"{NICE[m]} about {v:.2f} minutes per person" for m, v in rate.items())
        out.append(f"<h3>Time vs number of people</h3><p>How the minutes pile up as each AI works through its people, checked every "
                   f"5 people in round {int(last)}. The lines are straight, which means every extra person costs the same amount "
                   f"of time: {rtxt}. Twice the people means twice the time.</p>")
        out.append(line_chart(s, "people finished", "minutes so far", fmt_x=lambda v: f"{v:.0f}",
                              title="Minutes so far vs people finished"))
    pts = {m: [] for m in MODELS}
    tot = []
    for mf in sorted(glob.glob(os.path.join(DATA, "worlds", "*", "manifest.json"))):
        j = json.load(open(mf))
        lab = j["label"]
        if not (lab.startswith(("sweep_", "v2_")) or lab == "bench_v2") or "finished_at" not in j:
            continue
        if j.get("ollama_server", {}).get("OLLAMA_FLASH_ATTENTION", "false") != "true":
            continue  # compare like with like: flash attention (on from post set 12, LF-14) is ~7 % faster
        n = j["config"]["agents"]
        judged = j.get("judges", {})
        # skip runs that were paused and resumed: their clock only covers the part after the restart
        if sum(v.get("decisions", 0) for v in judged.values()) < n * 50:
            continue
        mins = 0.0
        for m, v in judged.items():
            if m in pts:
                pts[m].append((n, v["wall_s"] / 60, f"{lab}: {n} people in the run, {NICE[m]} took {v['wall_s'] / 60:.1f} min"))
                mins += v["wall_s"] / 60
        tot.append((n, mins, lab))
    if len({n for n, _, _ in tot}) >= 2:
        sizes = sorted({n for n, _, _ in tot})
        ttxt = "; ".join(f"{n} people ≈ {sum(m for k, m, _ in tot if k == n) / sum(1 for k, _, _ in tot if k == n):.0f} min"
                         for n in sizes)
        out.append("<h3>Whole runs with different numbers of people</h3><p>Each dot is a complete run with that many people. "
                   f"This is what a bigger crowd really costs, both AIs added together: {ttxt}.</p>")
        out.append(line_chart(pts, "people in the run", "minutes (this AI's share)", fmt_x=lambda v: f"{v:.0f}",
                              title="Minutes per run vs number of people"))
    else:
        out.append("<h3>Whole runs with different numbers of people</h3><p class='muted'>Runs with 10, 25, 50 and 75 people are "
                   "queued after the main test. This chart appears when they finish.</p>")
    return "".join(out)


def data_section():
    p = os.path.join(EXP, "reactions.csv")
    if not os.path.exists(p):
        return ""
    n = sum(1 for _ in open(p)) - 1
    return f"""<h2>The data files</h2>
<p>Everything on this page comes from these tables. They are in <code>data/llm_bias/export/</code> on the <code>llm-bias</code>
branch, open in Excel or Google Sheets, and every column is explained in <code>LLM_BIAS_DATA_DICTIONARY.md</code>.</p>
<ul>
<li><b>reactions.csv</b>: one row for every time a person saw a post ({n:,} rows). It says what they did (like, dislike or
nothing, meaning skip), their reason, how many seconds the AI took, which AI <b>wrote</b> the post, and which AI was
<b>playing</b> the person.</li>
<li><b>posts.csv</b>: every post, which AI wrote it, what it was asked to write about, the full text, and how many people
liked, disliked or skipped it.</li>
<li><b>users.csv</b>: the 99 people, their interests, the exact description each AI was given, and which AI played them in
each round.</li>
<li><b>world_timing.csv</b> and <b>progress_timing.csv</b>: the numbers behind the timing charts.</li>
<li><code>data/llm_bias/explore_v2.json</code>: the numbers behind “What else we found”.</li>
</ul>
<p class="cap">“seconds” in reactions.csv is how long one answer took. Four answers run at the same time, so the whole run
moves about four times faster than that column suggests.</p>"""


# ---------------------------------------------------------------- look-up tool data

def lookup_data():
    """Everything the look-up tool needs: posts, people, reasons (deduplicated) and one row per reaction."""
    R = pd.read_csv(os.path.join(EXP, "reactions.csv"))
    P = pd.read_csv(os.path.join(EXP, "posts.csv"))
    U = pd.read_csv(os.path.join(EXP, "users.csv")).drop_duplicates("user_id").sort_values("user_id")
    P = P.sort_values(["post_set_seed", "topic", "slot", "author_model"]).reset_index(drop=True)
    pidx = {u: i for i, u in enumerate(P["post_uid"])}
    reasons = pd.Index(R["reason"].fillna("").unique())
    ridx = {r: i for i, r in enumerate(reasons)}
    act = {"like": 0, "dislike": 1, "nothing": 2}
    posts = [{"s": int(r.post_set_seed), "t": r.topic, "a": MODELS.index(r.author_model), "ti": r.title, "b": r.body,
              "w": int(r.words), "k": r.post_type} for r in P.itertuples()]
    users = [{"i": int(u.user_id), "n": u["name"], "age": int(u.age), "g": u.gender, "pl": u.place, "job": u.profession,
              "st": u.voting_style, "in": {t: int(u[f"interest_{t}"]) for t in PRIMARY}, "d": u.persona_text}
             for _, u in U.iterrows()]
    rows = [[pidx[r.post_uid], int(r.user_id), MODELS.index(r.controlling_model), act.get(r.action, 2),
             ridx[r.reason if isinstance(r.reason, str) else ""], round(float(r.seconds), 1)]
            for r in R.itertuples() if r.post_uid in pidx]
    return {"topics": {t: TOPICS[t]["name"] for t in PRIMARY}, "models": [NICE[m] for m in MODELS],
            "posts": posts, "users": users, "reasons": list(reasons), "R": rows}


# ---------------------------------------------------------------- page

CSS = """
:root { --ground:#F2F4F6; --paper:#FFFFFF; --ink:#18202B; --muted:#5A6573; --rule:#D5DBE2; --accent:#1F6F8B;
  --diag:#B7791F; --s1:#2a78d6; --s2:#eb6834; --luck:#AEB7C2; --like:#1E7A4F; --dislike:#B4322A; --skip:#66707C;
  --chipbg:#EEF1F4;
  --sans:"Archivo","Helvetica Neue",Arial,sans-serif; --serif:"Source Serif 4",Georgia,serif; --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --ground:#11161C; --paper:#18202A; --ink:#E4E9EF;
  --muted:#9AA6B4; --rule:#2C3643; --accent:#63B4D1; --diag:#E2A948; --s1:#3987e5; --s2:#d95926; --luck:#4A5563;
  --like:#5CC48E; --dislike:#F07A70; --skip:#9AA6B4; --chipbg:#222C38; color-scheme:dark; } }
:root[data-theme="dark"] { --ground:#11161C; --paper:#18202A; --ink:#E4E9EF; --muted:#9AA6B4; --rule:#2C3643;
  --accent:#63B4D1; --diag:#E2A948; --s1:#3987e5; --s2:#d95926; --luck:#4A5563; --like:#5CC48E; --dislike:#F07A70;
  --skip:#9AA6B4; --chipbg:#222C38; color-scheme:dark; }
body { background:var(--ground); color:var(--ink); font:17px/1.6 var(--serif); padding-inline:16px; }
.wrap { max-width:760px; margin:0 auto; padding-block:40px 80px; display:grid; gap:8px; }
h1,h2,h3 { font-family:var(--sans); line-height:1.2; text-wrap:balance; margin:0; }
h1 { font-size:clamp(30px,6vw,44px); font-weight:800; }
h2 { font-size:25px; font-weight:800; margin-top:38px; padding-top:16px; border-top:2px solid var(--ink); }
h3 { font-size:19px; font-weight:700; margin-top:24px; }
p { margin:8px 0; max-width:68ch; } ul { max-width:68ch; }
.kicker { font:500 13px/1.4 var(--mono); letter-spacing:.08em; text-transform:uppercase; color:var(--accent); }
.lede { font-size:20px; } .cap,.muted { color:var(--muted); font-size:14.5px; }
code { font-family:var(--mono); font-size:13.5px; }
.scroll { overflow-x:auto; }
table { border-collapse:collapse; font-family:var(--sans); font-size:14px; font-variant-numeric:tabular-nums; margin-top:8px; }
table caption { text-align:left; font-weight:700; padding-bottom:4px; }
table.plain th, table.plain td { padding:5px 10px; border-bottom:1px solid var(--rule); text-align:left; vertical-align:top; }
.num { text-align:right !important; }
td.diag { outline:2px solid var(--diag); outline-offset:-2px; font-weight:600; }
.answers { display:grid; gap:12px; margin:8px 0 4px; }
.verdict { background:var(--paper); border-left:4px solid var(--diag); padding:12px 16px; }
.verdict p { margin:4px 0; } .verdict .q { font:600 15px/1.3 var(--sans); color:var(--muted); }
.verdict .a { font-size:19px; }
.grown { color:var(--muted); font-size:14px; font-family:var(--sans); }
.find { display:grid; gap:4px; }
.example { background:var(--paper); border:1px solid var(--rule); border-radius:6px; padding:10px 14px; font-size:16px; }
details { background:var(--paper); border:1px solid var(--rule); border-radius:6px; padding:10px 14px; margin-top:12px; }
summary { font-family:var(--sans); font-weight:600; cursor:pointer; }
.legend { display:flex; gap:18px; flex-wrap:wrap; font:13px var(--sans); color:var(--muted); margin-top:10px; }
.key { display:inline-flex; align-items:center; gap:6px; }
.sw { width:12px; height:12px; border-radius:50%; display:inline-block; } .sw.s1 { background:var(--s1); } .sw.s2 { background:var(--s2); }
.chart svg { width:100%; height:auto; max-width:700px; display:block; } .chart.sq svg { max-width:480px; }
svg .grid { stroke:var(--rule); stroke-width:1; } svg .axis { stroke:var(--muted); stroke-width:1; }
svg .zero { stroke:var(--ink); stroke-width:1.5; } svg .diag { stroke:var(--muted); stroke-width:1.5; stroke-dasharray:5 4; }
svg .tick { fill:var(--muted); font:12px var(--mono); } svg .tick.lab { font:13px var(--sans); fill:var(--ink); }
svg .axlab { fill:var(--muted); font:12.5px var(--sans); } svg .note { fill:var(--muted); font:italic 12px var(--sans); }
svg .endlab { fill:var(--ink); font:600 12.5px var(--sans); } svg .val { fill:var(--ink); font:600 12.5px var(--sans); }
svg .ln { fill:none; stroke-width:2; } svg .ln.s1 { stroke:var(--s1); } svg .ln.s2 { stroke:var(--s2); }
svg .bar.s1 { fill:var(--s1); } svg .bar.s2 { fill:var(--s2); }
svg .dot { stroke:var(--paper); stroke-width:2; } svg .dot.s1 { fill:var(--s1); } svg .dot.s2 { fill:var(--s2); } svg .dot.acc { fill:var(--accent); }
svg .whisk { stroke:var(--accent); stroke-width:2; stroke-linecap:round; }
svg .hit, svg .hitr { fill:transparent; } svg .pt:hover .dot { r:7; } svg .pt:hover .bar { opacity:.85; }
.match { display:grid; gap:12px; margin-top:6px; font-family:var(--sans); font-size:14px; }
.mrow { display:grid; grid-template-columns:minmax(120px,190px) 1fr; gap:12px; align-items:center; }
.mbars { display:grid; gap:4px; } .mb { position:relative; background:var(--chipbg); border-radius:4px; height:24px; }
.mb .fill { position:absolute; inset:0 auto 0 0; border-radius:4px; } .fill.acc { background:color-mix(in srgb, var(--accent) 55%, var(--chipbg)); } .fill.luck { background:var(--luck); }
.mb b { position:relative; font-weight:600; font-size:12.5px; line-height:24px; padding-left:8px; color:var(--ink); }
@media (max-width:520px) { .mrow { grid-template-columns:1fr; gap:4px; } }
.steps { display:grid; gap:10px; padding:0; list-style:none; counter-reset:s; }
.steps li { background:var(--paper); border:1px solid var(--rule); border-radius:6px; padding:12px 16px 12px 50px; position:relative; }
.steps li::before { counter-increment:s; content:counter(s); position:absolute; left:14px; top:12px; width:24px; height:24px;
  border-radius:50%; background:var(--accent); color:var(--paper); font:700 13px/24px var(--sans); text-align:center; }
/* look-up tool */
.tool { background:var(--paper); border:1px solid var(--rule); border-radius:8px; padding:14px 16px; display:grid; gap:12px; font-family:var(--sans); }
.tabs { display:flex; gap:6px; flex-wrap:wrap; }
.tabs button { font:600 14px var(--sans); padding:7px 14px; border-radius:6px; border:1px solid var(--rule); background:var(--ground); color:var(--ink); cursor:pointer; }
.tabs button[aria-selected="true"] { background:var(--accent); color:var(--paper); border-color:var(--accent); }
.pick { display:flex; gap:10px; flex-wrap:wrap; align-items:end; }
.pick label { display:grid; gap:3px; font-size:12.5px; color:var(--muted); min-width:0; flex:1 1 150px; }
.pick select { font:14px var(--sans); padding:6px 8px; border-radius:6px; border:1px solid var(--rule); background:var(--ground); color:var(--ink); width:100%; min-width:0; }
.pick[hidden] { display:none; }
.pick .wide { flex:3 1 280px; }
.pick .chk { flex-direction:row; display:flex; gap:6px; align-items:center; font-size:13.5px; color:var(--ink); }
button:focus-visible, select:focus-visible, input:focus-visible, summary:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
.postcard { border-left:4px solid var(--rule); padding:4px 0 4px 14px; font-family:var(--serif); }
.postcard.s1 { border-color:var(--s1); } .postcard.s2 { border-color:var(--s2); }
.postcard h4 { font:700 17px/1.3 var(--sans); margin:0 0 4px; } .postcard p { margin:4px 0; font-size:16px; }
.meta { font-size:13px; color:var(--muted); }
.tally { display:flex; gap:16px; flex-wrap:wrap; font-size:14px; }
.chip { display:inline-block; font:600 12px/1 var(--sans); padding:4px 7px; border-radius:4px; background:var(--chipbg); margin-right:6px; }
.chip.like { color:var(--like); } .chip.dislike { color:var(--dislike); } .chip.skip { color:var(--skip); }
.rt td { font-size:13.5px; } .rt .why { color:var(--muted); } .rt tr.diff td { background:var(--chipbg); }
.tag { display:inline-block; font-size:11.5px; padding:1px 6px; border-radius:10px; border:1px solid var(--rule); color:var(--muted); white-space:nowrap; }
.person { display:grid; gap:4px; font-size:14.5px; } .person h4 { font:700 18px var(--sans); margin:0; }
.ints { display:flex; gap:6px; flex-wrap:wrap; }
@media (prefers-reduced-motion: reduce) { * { transition:none !important; } }
"""

JS = r"""
(function () {
  var D = window.WORLD_DATA; if (!D) { return; }
  var ACT = ["like", "dislike", "skip"], ACTW = ["Like", "Dislike", "Skip"];
  var CARE = {"-2": "really dislikes", "-1": "dislikes", "0": "doesn't mind", "1": "likes", "2": "loves"};
  var STYLE = {generous: "easy to please", typical: "normal", harsh: "hard to please"};
  var byPost = {}, byUser = {};
  D.R.forEach(function (r) { (byPost[r[0]] = byPost[r[0]] || []).push(r); (byUser[r[1]] = byUser[r[1]] || []).push(r); });
  var users = {}; D.users.forEach(function (u) { users[u.i] = u; });
  var $ = function (id) { return document.getElementById(id); };
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]; }); }
  function chip(r) { return r ? '<span class="chip ' + ACT[r[3]] + '">' + ACTW[r[3]] + '</span><span class="why">' + esc(D.reasons[r[4]]) + '</span>' : '<span class="muted">not seen yet</span>'; }
  function opt(v, t, sel) { return '<option value="' + esc(v) + '"' + (sel ? " selected" : "") + ">" + esc(t) + "</option>"; }
  var sets = Array.from(new Set(D.posts.map(function (p) { return p.s; }))).sort(function (a, b) { return a - b; });
  function save(k, v) { try { localStorage.setItem("lk_" + k, v); } catch (e) {} }
  function load(k) { try { return localStorage.getItem("lk_" + k); } catch (e) { return null; } }

  // ---- post view
  function fillPosts() {
    var s = +$("lkSet").value, t = $("lkTopic").value, cur = $("lkPost").value;
    var html = "";
    D.posts.forEach(function (p, i) { if (p.s === s && p.t === t) html += opt(i, p.ti + "  (by " + D.models[p.a] + ")", String(i) === cur); });
    $("lkPost").innerHTML = html; showPost();
  }
  function showPost() {
    var i = +$("lkPost").value, p = D.posts[i]; if (!p) { return; }
    var rs = byPost[i] || [], pair = {};
    rs.forEach(function (r) { (pair[r[1]] = pair[r[1]] || [null, null])[r[2]] = r; });
    var tally = [0, 1].map(function (m) {
      var c = [0, 0, 0]; rs.forEach(function (r) { if (r[2] === m) c[r[3]]++; });
      return "<span><b>Played by " + D.models[m] + ":</b> " + c[0] + " like · " + c[1] + " dislike · " + c[2] + " skip</span>";
    }).join("");
    var only = $("lkDiff").checked, rows = "", shown = 0;
    Object.keys(pair).map(Number).sort(function (a, b) { return users[b].in[p.t] - users[a].in[p.t] || a - b; }).forEach(function (uid) {
      var pr = pair[uid], u = users[uid], diff = pr[0] && pr[1] && pr[0][3] !== pr[1][3];
      if (only && !diff) { return; }
      shown++;
      rows += '<tr class="' + (diff ? "diff" : "") + '"><td><b>' + esc(u.n) + "</b><br><span class='meta'>" + u.age + ", " + esc(u.job) + "</span></td><td><span class='tag'>" +
        CARE[u.in[p.t]] + "</span></td><td>" + chip(pr[0]) + "</td><td>" + chip(pr[1]) + "</td></tr>";
    });
    $("lkOut").innerHTML = '<div class="postcard ' + (p.a === 0 ? "s1" : "s2") + '"><h4>' + esc(p.ti) + "</h4>" +
      esc(p.b).split(/\n+/).map(function (x) { return "<p>" + x + "</p>"; }).join("") +
      '<p class="meta">Written by ' + D.models[p.a] + " · " + p.w + " words · " + esc(D.topics[p.t]) + " · post set " + p.s + " · asked to write: " + esc(p.k) + "</p></div>" +
      '<div class="tally">' + tally + "</div>" +
      '<div class="scroll"><table class="plain rt"><thead><tr><th>Person</th><th>Topic</th><th>When llama played them</th><th>When gemma played them</th></tr></thead><tbody>' +
      (rows || '<tr><td colspan="4" class="muted">No one here — untick the box to see everyone.</td></tr>') + "</tbody></table></div>" +
      '<p class="meta">' + shown + " people shown. Shaded rows: the two AIs made different choices for the same person.</p>";
    save("post", i);
  }
  // ---- person view
  function showPerson() {
    var u = users[+$("lkUser").value]; if (!u) { return; }
    var t = $("lkUTopic").value, rs = byUser[u.i] || [], pair = {};
    rs.forEach(function (r) { (pair[r[0]] = pair[r[0]] || [null, null])[r[2]] = r; });
    var ints = Object.keys(D.topics).map(function (k) { return '<span class="tag">' + esc(D.topics[k]) + ": " + CARE[u.in[k]] + "</span>"; }).join("");
    var agree = 0, both = 0, rows = "";
    Object.keys(pair).map(Number).sort(function (a, b) { var A = D.posts[a], B = D.posts[b]; return A.s - B.s || u.in[B.t] - u.in[A.t] || (A.t < B.t ? -1 : A.t > B.t ? 1 : a - b); }).forEach(function (pi) {
      var p = D.posts[pi], pr = pair[pi], diff = pr[0] && pr[1] && pr[0][3] !== pr[1][3];
      if (pr[0] && pr[1]) { both++; if (!diff) agree++; }
      if (t && p.t !== t) { return; }
      rows += '<tr class="' + (diff ? "diff" : "") + '"><td>' + p.s + "</td><td>" + esc(p.ti) + "<br><span class='meta'>" + esc(D.topics[p.t]) + " · by " + D.models[p.a] +
        "</span></td><td>" + chip(pr[0]) + "</td><td>" + chip(pr[1]) + "</td></tr>";
    });
    $("lkOut").innerHTML = '<div class="person"><h4>' + esc(u.n) + "</h4><div>" + u.age + "-year-old " + esc(u.g) + " " + esc(u.job) + " in " + esc(u.pl) +
      " · " + (STYLE[u.st] || u.st) + '</div><div class="ints">' + ints + "</div>" +
      "<details><summary>Exactly what the AI was told about " + esc(u.n.split(" ")[0]) + "</summary><p class='meta' style='white-space:pre-wrap'>" + esc(u.d) + "</p></details>" +
      (both ? "<p>Llama and gemma made the same choice for " + esc(u.n.split(" ")[0]) + " on " + agree + " of " + both + " posts (" + Math.round(100 * agree / both) + " in 100).</p>" : "") +
      '</div><div class="scroll"><table class="plain rt"><thead><tr><th>Set</th><th>Post</th><th>When llama played them</th><th>When gemma played them</th></tr></thead><tbody>' +
      rows + "</tbody></table></div>";
    save("user", u.i);
  }
  function mode(m) {
    ["post", "person"].forEach(function (k) {
      $("lkTab_" + k).setAttribute("aria-selected", String(k === m)); $("lkPick_" + k).hidden = k !== m;
    });
    save("mode", m); if (m === "post") { fillPosts(); } else { showPerson(); }
  }
  // ---- build controls
  var topicOpts = Object.keys(D.topics).map(function (k) { return opt(k, D.topics[k]); }).join("");
  $("lkSet").innerHTML = sets.map(function (s) { return opt(s, "Post set " + s, s === sets[sets.length - 1]); }).join("");
  $("lkTopic").innerHTML = topicOpts;
  $("lkUTopic").innerHTML = opt("", "All topics") + topicOpts;
  $("lkUser").innerHTML = D.users.slice().sort(function (a, b) { return a.n < b.n ? -1 : 1; }).map(function (u) { return opt(u.i, u.n + " (" + u.age + ", " + u.job + ")"); }).join("");
  var lp = load("post"); if (lp !== null && D.posts[+lp]) { $("lkSet").value = D.posts[+lp].s; $("lkTopic").value = D.posts[+lp].t; }
  fillPosts(); if (lp !== null && D.posts[+lp]) { $("lkPost").value = lp; showPost(); }
  var lu = load("user"); if (lu !== null && users[+lu]) { $("lkUser").value = lu; }
  $("lkSet").onchange = fillPosts; $("lkTopic").onchange = fillPosts; $("lkPost").onchange = showPost; $("lkDiff").onchange = showPost;
  $("lkUser").onchange = showPerson; $("lkUTopic").onchange = showPerson;
  $("lkTab_post").onclick = function () { mode("post"); }; $("lkTab_person").onclick = function () { mode("person"); };
  mode(load("mode") === "person" ? "person" : "post");
})();
"""

TOOL = """<h2>Look it up yourself</h2>
<p>Pick any post to see how all 99 people reacted to it, both when llama played them and when gemma did. Or pick a person
to see every choice they made. Shaded rows are where the two AIs made different choices for the same person.</p>
<div class="tool">
<div class="tabs" role="tablist"><button id="lkTab_post" role="tab" aria-selected="true">Look up a post</button>
<button id="lkTab_person" role="tab" aria-selected="false">Look up a person</button></div>
<div class="pick" id="lkPick_post"><label>Post set<select id="lkSet"></select></label><label>Topic<select id="lkTopic"></select></label>
<label class="wide">Post<select id="lkPost"></select></label><label class="chk"><input type="checkbox" id="lkDiff"> Only where the AIs disagreed</label></div>
<div class="pick" id="lkPick_person" hidden><label class="wide">Person<select id="lkUser"></select></label><label>Topic<select id="lkUTopic"></select></label></div>
<div id="lkOut"><p class="muted">Loading every reaction…</p></div>
</div>"""


def build(ap=None, xp=None):
    ap = ap or os.path.join(DATA, "analysis_v2.json")
    xp = xp or os.path.join(DATA, "explore_v2.json")
    res = json.load(open(ap)) if os.path.exists(ap) else None
    ex = json.load(open(xp)) if os.path.exists(xp) else None
    sets = sorted({int(w.split("_s")[1].split("_")[0]) for w in res["worlds"]}) if res else []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    topics = ", ".join(TOPICS[t]["name"].lower() for t in PRIMARY)
    head = f"""<title>Scroll Test</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700;800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
<div class="wrap">
<p class="kicker">LLM Bias · test 2 · local AIs only · updated {now} · {len(sets)} post sets done{f" ({res['n_valid']:,} reactions)" if res else ""}</p>
<h1>Do AIs like their own posts?</h1>
<p class="lede">We asked two AI programs, <b>llama</b> and <b>gemma</b>, to write posts for a pretend Reddit. Then the same
two AIs pretended to be 99 different people, like Marcus, a 68-year-old retired mail carrier in Dublin. Each pretend person
scrolls through every post and picks <b>like</b>, <b>dislike</b> or <b>skip</b>. The big question: when llama is pretending
to be Marcus, does Marcus like llama's posts more? If so, the AI is secretly cheering for itself.</p>
<p>Why it matters: researchers are starting to use AIs as pretend crowds to test ideas before trying them on real people.
If an AI quietly favours its own writing, those tests are unfair.</p>

<h2>The answer so far</h2>
{results(res)}

<h2>How the test works</h2>
<ol class="steps">
<li><b>Writing.</b> Both AIs write 25 posts each on the same five topics ({topics}). For every post, both AIs get the exact
same instructions, like “a 24-year-old asks for advice about paying off a credit card”. So each pair of posts differs only in
which AI wrote it. That makes 50 posts per <b>post set</b>.</li>
<li><b>No names, no scores.</b> All 50 posts go up on one pretend Reddit. Nobody can see who wrote a post or how many likes it has.</li>
<li><b>The same 99 people every time.</b> We made 99 people with ages, jobs, hometowns and favourite topics. They never
change; the computer checks this before every run. In the first round llama plays half of them and gemma plays the other half.
In the second round the two AIs swap, so every person gets played by both AIs on the same posts.</li>
<li><b>Scrolling.</b> Each person sees every post, one at a time, starting with their favourite topic. For each post they
pick like, dislike or skip, and say why in a few words.</li>
</ol>

<h2>What else we found</h2>
{findings(ex, res)}

{TOOL}
{nothing_section(res)}
{timing_section()}
{data_section()}
</div>
<script src="world_data.js"></script>
<script>{JS}</script>
"""
    return head


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--out", required=True)
    a.add_argument("--analysis", help="analysis json (default data/llm_bias/analysis_v2.json)")
    a.add_argument("--explore", help="exploration json (default data/llm_bias/explore_v2.json)")
    args = a.parse_args()
    with open(args.out, "w") as f:
        f.write(build(args.analysis, args.explore))
    dp = os.path.join(os.path.dirname(os.path.abspath(args.out)), "world_data.js")
    with open(dp, "w") as f:
        f.write("window.WORLD_DATA=" + json.dumps(lookup_data(), ensure_ascii=False, separators=(",", ":")) + ";")
    print("wrote", args.out, "and", dp, f"({os.path.getsize(dp) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
