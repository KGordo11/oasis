"""Build the design-v2 page (results, 'nothing' diagnosis, timing charts, data guide).

Reads only data/llm_bias/export/*.csv (run export_world.py first) and
data/llm_bias/analysis_v2.json. Nothing on the page is typed in by hand except
prose, so re-running after each round updates every number and chart.

    python make_world_artifact.py --out /path/scroll_test.html
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from datetime import datetime

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from topics import TOPICS  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EXP = os.path.join(REPO, "data", "llm_bias", "export")
E = html.escape
MODELS = ["llama3.1:8b", "gemma4:e2b"]          # fixed order -> fixed colour: slot 1 blue, slot 2 orange
CLS = {"llama3.1:8b": "s1", "gemma4:e2b": "s2"}
NICE = {"llama3.1:8b": "llama3.1", "gemma4:e2b": "gemma4"}


def nice_ticks(lo, hi, n=5, integer=False):
    """Ticks from <= lo to >= hi (the last tick always covers the largest value)."""
    import math
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


def line_chart(series, xlabel, ylabel, fmt_x=lambda v: f"{v:g}", fmt_y=lambda v: f"{v:g}", title="",
               x_from=0, x_integer=False):
    """series: {model: [(x, y, tooltip)]}. Theme-aware SVG, one y axis, legend + end labels, hover titles."""
    pts = [p for s in series.values() for p in s]
    if not pts:
        return '<p class="muted">No data yet.</p>'
    W, H, L, R, T, B = 680, 300, 58, 96, 16, 46
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
    legend = "".join(f'<span class="key"><i class="sw {CLS[m]}"></i>{E(m)}</span>' for m in MODELS if series.get(m))
    return f'<div class="legend">{legend}</div><div class="chart">{"".join(g)}</div>'


def results(res):
    if not res:
        return '<p class="muted">The first full result arrives when round 2 (the swapped world) finishes.</p>'
    up = pd.DataFrame(res["rate_up"]).reindex(index=MODELS, columns=MODELS) * 100
    dn = pd.DataFrame(res["rate_down"]).reindex(index=MODELS, columns=MODELS) * 100
    no = pd.DataFrame(res["rate_nothing"]).reindex(index=MODELS, columns=MODELS) * 100

    def table(df, what):
        head = "".join(f"<th class='num'>posts by {E(NICE[a])}</th>" for a in MODELS)
        rows = "".join(
            f"<tr><th>users controlled by {E(NICE[j])}</th>" + "".join(
                f"<td class='num{' diag' if a == j else ''}'>{df.loc[j, a]:.1f} %</td>" for a in MODELS) + "</tr>"
            for j in MODELS)
        return f"<div class='scroll'><table class='plain'><caption>{what}</caption><thead><tr><th></th>{head}</tr></thead><tbody>{rows}</tbody></table></div>"
    sp = res["sp_up"].get("_pooled", {})
    spd = res["sp_down"].get("_pooled", {})
    ci = sp.get("ci95")
    if ci and ci[0] > 0:
        verdict = "Supported so far: users like posts written by their own controlling model more, and the 95 % range stays above zero."
    elif ci and ci[1] < 0:
        verdict = "Reversed so far: users like their own model's posts LESS."
    else:
        verdict = "Not shown yet: the 95 % range still includes zero. More rounds narrow it."
    pv = res.get("sp_up_p")
    return f"""
<div class="verdict"><strong>Own-model like boost: {sp.get('est', 0) * 100:+.1f} percentage points</strong>
{f"(95 % range {ci[0] * 100:+.1f} to {ci[1] * 100:+.1f}{f', p = {pv:.3f}' if pv is not None else ''})" if ci else ""}. {E(verdict)}</div>
<p>How to read it: take how much more llama-controlled users like llama's posts than gemma's posts, subtract the same gap for
gemma-controlled users, and split the difference between the two models. If one model simply writes better posts, both
groups of users like those posts more and the gap cancels. Only a preference that depends on <em>who is controlling the user</em>
survives. The dislike version is {spd.get('est', 0) * 100:+.1f} points
{f"(95 % range {spd['ci95'][0] * 100:+.1f} to {spd['ci95'][1] * 100:+.1f})" if spd.get('ci95') else ""}; there, self-preference shows up as a negative number.</p>
{table(up, "Like rate")}
{table(dn, "Dislike rate")}
{table(no, "Nothing rate (no vote, kept scrolling)")}
<p class="cap">Outlined cells are users reacting to posts written by the model controlling them. {res['n_valid']:,} valid decisions of
{res['n_decisions']:,}; {res['personas']} users; {res['posts']} posts; {res['personas_played_by_both']} users have been played by both models so far.</p>"""


def nothing_section(res):
    if not res:
        return ""
    rows = ""
    for m in MODELS:
        v = res["nothing"].get(m)
        if not v:
            continue
        rows += (f"<tr><td>{E(NICE[m])}</td><td class='num'>{v['like_%']}</td><td class='num'>{v['dislike_%']}</td>"
                 f"<td class='num'>{v['nothing_%']}</td><td class='num'>{v['failed_%']}</td>"
                 f"<td class='num'>{v['cut_off_at_token_limit']}</td><td class='num'>{v['hidden_thinking_chars']}</td>"
                 f"<td class='num'>{v['nothing_with_a_reason_%']}</td></tr>")
    by = ""
    for m in MODELS:
        v = res["nothing"].get(m)
        if v:
            cells = "".join(f"<td class='num'>{v['nothing_%_by_interest'].get(k, v['nothing_%_by_interest'].get(str(k), float('nan'))):.0f}</td>"
                            for k in (-2, -1, 0, 1, 2))
            by += f"<tr><td>{E(NICE[m])}</td>{cells}</tr>"
    samples = ""
    for m in MODELS:
        v = res["nothing"].get(m)
        if v and v["sample_nothing_reasons"]:
            samples += f"<p><b>{E(NICE[m])}:</b> " + " · ".join(f"“{E(s)}”" for s in v["sample_nothing_reasons"]) + "</p>"
    return f"""<h2>Why so many “nothing” answers?</h2>
<p>A “nothing” could mean the user decided to scroll past, or it could hide a broken answer. Every decision records which it
was. Failed means no readable answer after three tries. Cut off means the answer hit its length limit. Hidden thinking is
reasoning a model does before answering, which is switched off here.</p>
<div class="scroll"><table class="plain"><thead><tr><th>model</th><th class="num">like %</th><th class="num">dislike %</th>
<th class="num">nothing %</th><th class="num">failed %</th><th class="num">cut off</th><th class="num">hidden thinking</th>
<th class="num">“nothing” with a reason %</th></tr></thead><tbody>{rows}</tbody></table></div>
<h3>“Nothing” follows the user's interest</h3>
<p>Percent of posts a user scrolled past, by how much that user cares about the post's topic, from −2 (dislikes it) to +2
(loves it). If “nothing” is a real choice, it should be high on the left and low on the right.</p>
<div class="scroll"><table class="plain"><thead><tr><th>model</th><th class="num">−2</th><th class="num">−1</th>
<th class="num">0</th><th class="num">+1</th><th class="num">+2</th></tr></thead><tbody>{by}</tbody></table></div>
<h3>What users said when they scrolled past</h3>{samples}"""


def timing_section():
    wt = pd.read_csv(os.path.join(EXP, "world_timing.csv")) if os.path.exists(os.path.join(EXP, "world_timing.csv")) else None
    pt = pd.read_csv(os.path.join(EXP, "progress_timing.csv")) if os.path.exists(os.path.join(EXP, "progress_timing.csv")) else None
    out = ["<h2>How long it takes</h2>"]
    if wt is not None and len(wt):
        s = {m: [(int(r["round"]), float(r["minutes"]),
                  f"round {int(r['round'])}: {NICE[m]} took {r['minutes']:.1f} min for {int(r['users'])} users "
                  f"({r['seconds_per_decision']:.2f} s per decision)") for _, r in wt[wt.model == m].iterrows()]
             for m in MODELS}
        tot = wt.groupby("round")["minutes"].sum()
        out.append("<h3>Time per round</h3><p>Minutes each model spent getting its users through one round "
                   "(one world: its ~50 users each scrolling all 50 posts). The two models take turns, so a round's "
                   f"total is the sum: so far {tot.mean():.0f} minutes on average.</p>")
        out.append(line_chart(s, "round (in the order they ran)", "minutes", fmt_x=lambda v: f"{v:.0f}",
                              title="Minutes per round, per model", x_from=1, x_integer=True))
        rows = "".join(f"<tr><td class='num'>{int(r['round'])}</td><td>{E(NICE[r['model']])}</td><td class='num'>{int(r['users'])}</td>"
                       f"<td class='num'>{int(r['decisions']):,}</td><td class='num'>{r['minutes']:.1f}</td>"
                       f"<td class='num'>{r['seconds_per_decision']:.2f}</td></tr>" for _, r in wt.iterrows())
        out.append(f"<details><summary>Table view</summary><table class='plain'><thead><tr><th class='num'>round</th><th>model</th>"
                   f"<th class='num'>users</th><th class='num'>decisions</th><th class='num'>minutes</th>"
                   f"<th class='num'>s / decision</th></tr></thead><tbody>{rows}</tbody></table></details>")
    if pt is not None and len(pt):
        last = pt["round"].max()
        full = pt[pt["round"] == last]
        s = {m: [(float(r["users_done_equiv"]), float(r["elapsed_s"]) / 60,
                  f"{r['users_done_equiv']:.0f} users done after {r['elapsed_s'] / 60:.1f} min ({NICE[m]}, round {int(r['round'])})")
                 for _, r in full[full.model == m].iterrows()] for m in MODELS}
        rate = {m: (full[full.model == m]["elapsed_s"].max() / 60) / max(1, full[full.model == m]["users_done_equiv"].max())
                for m in MODELS if len(full[full.model == m])}
        rtxt = "; ".join(f"{NICE[m]} ≈ {v:.2f} min per user" for m, v in rate.items())
        out.append(f"<h3>Time vs agents</h3><p>Elapsed time as each model works through its users, measured every 5 users "
                   f"within round {int(last)}. A straight line means every extra agent costs the same: {rtxt}. Adding users adds "
                   f"time in direct proportion; nothing else runs out.</p>")
        out.append(line_chart(s, "users (agents) finished", "minutes elapsed", fmt_x=lambda v: f"{v:.0f}",
                              title="Minutes elapsed vs users finished"))
    # whole runs at different sizes: the agent sweep + the benchmark + every 99-user round
    import glob
    pts = {m: [] for m in MODELS}
    tot = []
    for mf in sorted(glob.glob(os.path.join(REPO, "data", "llm_bias", "worlds", "*", "manifest.json"))):
        j = json.load(open(mf))
        lab = j["label"]
        if not (lab.startswith(("sweep_", "v2_")) or lab == "bench_v2") or "finished_at" not in j:
            continue
        # compare like with like: flash attention (on from post set 12, LF-14) is ~7 % faster
        if j.get("ollama_server", {}).get("OLLAMA_FLASH_ATTENTION", "false") != "true":
            continue
        n = j["config"]["agents"]
        mins = 0.0
        for m, v in j.get("judges", {}).items():
            if m in pts:
                pts[m].append((n, v["wall_s"] / 60, f"{lab}: {n} users in the run, {NICE[m]} took {v['wall_s'] / 60:.1f} min"))
                mins += v["wall_s"] / 60
        tot.append((n, mins, lab))
    if sum(len(v) for v in pts.values()) >= 2:
        sizes = sorted({n for n, _, _ in tot})
        ttxt = "; ".join(f"{n} users ≈ {sum(m for k, m, _ in tot if k == n) / sum(1 for k, _, _ in tot if k == n):.0f} min"
                         for n in sizes)
        out.append("<h3>Whole runs at different sizes</h3><p>Each point is a complete run with that many users, split between the "
                   "two models, each user scrolling all 50 posts. This shows what a bigger population actually costs: "
                   f"{ttxt} in total (both models together). Only runs with flash attention on are compared here (on since "
                   "post set 12; it makes runs about 7 % faster), so the sizes are measured under the same settings.</p>")
        out.append(line_chart(pts, "users (agents) in the run", "minutes (this model's share)", fmt_x=lambda v: f"{v:.0f}",
                              title="Minutes per run vs number of users"))
    return "".join(out)


def data_section():
    p = os.path.join(EXP, "reactions.csv")
    if not os.path.exists(p):
        return ""
    r = pd.read_csv(p)
    cols = ["round", "user_name", "controlling_model", "post_author_model", "topic", "scroll_position", "action", "reason", "seconds"]
    prev = r[cols].head(10)
    head = "".join(f"<th>{E(c)}</th>" for c in cols)
    body = "".join("<tr>" + "".join(f"<td>{E(str(v))}</td>" for v in row) + "</tr>" for row in prev.itertuples(index=False))
    return f"""<h2>The data</h2>
<p>Every reaction is kept. The tables live in <code>data/llm_bias/export/</code> on the <code>llm-bias</code> branch, and every
column is explained in <code>LLM_BIAS_DATA_DICTIONARY.md</code>. They open in Excel or Google Sheets.</p>
<ul>
<li><b>reactions.csv</b>: one row per user per post ({len(r):,} rows so far). Shows what the user did (like, dislike or nothing) and
their reason, how many seconds the decision took, the model that <b>wrote</b> the post, and the model <b>controlling</b> the user.</li>
<li><b>posts.csv</b>: every post, its author model, the brief, the full text, and how many users of each model liked, disliked or
ignored it.</li>
<li><b>users.csv</b>: the 99 fixed users, their interests, the exact personality text, and which model controlled them in each round.</li>
<li><b>world_timing.csv</b> and <b>progress_timing.csv</b>: the numbers behind the two timing charts.</li>
</ul>
<p>The first rows of reactions.csv, as they are:</p>
<div class="scroll"><table class="plain small"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>
<p class="cap">“seconds” is how long that one answer took. Four answers run at once on the chip, so the run as a whole moves
about four times faster than this column alone suggests; the throughput is in world_timing.csv.</p>"""


def build(ap=None):
    ap = ap or os.path.join(REPO, "data", "llm_bias", "analysis_v2.json")
    res = json.load(open(ap)) if os.path.exists(ap) else None
    wt = pd.read_csv(os.path.join(EXP, "world_timing.csv")) if os.path.exists(os.path.join(EXP, "world_timing.csv")) else None
    rounds = int(wt["round"].max()) if wt is not None and len(wt) else 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return PAGE.format(now=now, rounds=rounds, results=results(res), nothing=nothing_section(res),
                       timing=timing_section(), data=data_section(),
                       topics=", ".join(TOPICS[t]["name"] for t in ("personal_finance", "cars", "farming", "cooking", "tech")))


PAGE = """<title>Scroll Test</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{ --ground:#F2F4F6; --paper:#FFFFFF; --ink:#18202B; --muted:#5A6573; --rule:#D5DBE2; --accent:#1F6F8B;
  --diag:#B7791F; --s1:#2a78d6; --s2:#eb6834;
  --sans:"Archivo","Helvetica Neue",Arial,sans-serif; --serif:"Source Serif 4",Georgia,serif; --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace; }}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --ground:#11161C; --paper:#18202A; --ink:#E4E9EF;
  --muted:#9AA6B4; --rule:#2C3643; --accent:#63B4D1; --diag:#E2A948; --s1:#3987e5; --s2:#d95926; color-scheme:dark; }} }}
:root[data-theme="dark"] {{ --ground:#11161C; --paper:#18202A; --ink:#E4E9EF; --muted:#9AA6B4; --rule:#2C3643;
  --accent:#63B4D1; --diag:#E2A948; --s1:#3987e5; --s2:#d95926; color-scheme:dark; }}
body {{ background:var(--ground); color:var(--ink); font:17px/1.6 var(--serif); padding-inline:16px; }}
.wrap {{ max-width:760px; margin:0 auto; padding-block:40px 80px; display:grid; gap:8px; }}
h1,h2,h3 {{ font-family:var(--sans); line-height:1.2; text-wrap:balance; margin:0; }}
h1 {{ font-size:clamp(30px,6vw,44px); font-weight:800; }}
h2 {{ font-size:25px; font-weight:800; margin-top:38px; padding-top:16px; border-top:2px solid var(--ink); }}
h3 {{ font-size:18px; font-weight:700; margin-top:24px; }}
p {{ margin:8px 0; max-width:68ch; }} ul {{ max-width:68ch; }}
.kicker {{ font:500 13px/1 var(--mono); letter-spacing:.08em; text-transform:uppercase; color:var(--accent); }}
.lede {{ font-size:20px; }} .cap,.muted {{ color:var(--muted); font-size:14.5px; }}
code {{ font-family:var(--mono); font-size:13.5px; }}
.scroll {{ overflow-x:auto; }}
table {{ border-collapse:collapse; font-family:var(--sans); font-size:14px; font-variant-numeric:tabular-nums; margin-top:8px; }}
table caption {{ text-align:left; font-weight:700; padding-bottom:4px; }}
table.plain th, table.plain td {{ padding:5px 10px; border-bottom:1px solid var(--rule); text-align:left; }}
table.small td, table.small th {{ font-size:12.5px; padding:4px 7px; }}
.num {{ text-align:right !important; }}
td.diag {{ outline:2px solid var(--diag); outline-offset:-2px; font-weight:600; }}
.verdict {{ background:var(--paper); border-left:4px solid var(--diag); padding:12px 16px; margin:12px 0; }}
details {{ background:var(--paper); border:1px solid var(--rule); border-radius:6px; padding:10px 14px; margin-top:12px; }}
summary {{ font-family:var(--sans); font-weight:600; cursor:pointer; }}
.legend {{ display:flex; gap:18px; flex-wrap:wrap; font:13px var(--sans); color:var(--muted); margin-top:10px; }}
.key {{ display:inline-flex; align-items:center; gap:6px; }}
.sw {{ width:12px; height:12px; border-radius:50%; display:inline-block; }} .sw.s1 {{ background:var(--s1); }} .sw.s2 {{ background:var(--s2); }}
.chart svg {{ width:100%; height:auto; max-width:700px; }}
svg .grid {{ stroke:var(--rule); stroke-width:1; }} svg .axis {{ stroke:var(--muted); stroke-width:1; }}
svg .tick {{ fill:var(--muted); font:12px var(--mono); }} svg .axlab {{ fill:var(--muted); font:12.5px var(--sans); }}
svg .endlab {{ fill:var(--ink); font:600 12.5px var(--sans); }}
svg .ln {{ fill:none; stroke-width:2; }} svg .ln.s1 {{ stroke:var(--s1); }} svg .ln.s2 {{ stroke:var(--s2); }}
svg .dot {{ stroke:var(--paper); stroke-width:2; }} svg .dot.s1 {{ fill:var(--s1); }} svg .dot.s2 {{ fill:var(--s2); }}
svg .hit {{ fill:transparent; }} svg .pt:hover .dot {{ r:7; }}
.steps {{ display:grid; gap:10px; padding:0; list-style:none; counter-reset:s; }}
.steps li {{ background:var(--paper); border:1px solid var(--rule); border-radius:6px; padding:12px 16px 12px 50px; position:relative; }}
.steps li::before {{ counter-increment:s; content:counter(s); position:absolute; left:14px; top:12px; width:24px; height:24px;
  border-radius:50%; background:var(--accent); color:var(--paper); font:700 13px/24px var(--sans); text-align:center; }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition:none !important; }} }}
</style>
<div class="wrap">
<p class="kicker">LLM Bias · design 2 · local models only · updated {now} · {rounds} rounds done</p>
<h1>Do users like their own model's posts?</h1>
<p class="lede">Two AI models, llama3.1 and gemma4, each write Reddit posts. The same two models then take control of 99 fixed users,
who scroll every post and like it, dislike it, or keep scrolling. The question: does a user controlled by llama like llama's
posts more than a user controlled by gemma does?</p>

<h2>Result so far</h2>
{results}

<h2>How one round works</h2>
<ol class="steps">
<li><b>50 posts.</b> Both models write 5 posts on each of five topics ({topics}). Each of the five slots per topic has one brief
(a subject, a kind of post and a poster), and both models write from that same brief. So each pair of posts differs only by
which model wrote it.</li>
<li><b>One shared world.</b> All 50 posts go live on one OASIS reddit platform. No author names and no vote counts are shown.</li>
<li><b>99 fixed users, split between the models.</b> These are the same 99 people in every run, checked by fingerprint before
anything starts. In one world, even-numbered users are controlled by llama and odd-numbered users by gemma. The next world uses
the same posts with the split swapped, so every user is played by both models.</li>
<li><b>Scrolling.</b> Each user sees every post, one at a time, starting with the topic they love most and ending with the one they
like least. For each post they like it, dislike it, or do nothing and keep scrolling, and give a few words of reason. Likes and
dislikes are real OASIS actions.</li>
</ol>

{nothing}
{timing}
{data}
</div>
"""


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--out", required=True)
    a.add_argument("--analysis", help="analysis json (default data/llm_bias/analysis_v2.json)")
    args = a.parse_args()
    with open(args.out, "w") as f:
        f.write(build(args.analysis))
    print("wrote", args.out)


if __name__ == "__main__":
    main()
