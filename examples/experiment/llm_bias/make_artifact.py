"""Build the LLM Bias explainer + results page from data on disk.

Everything on the page is read from files -- analysis_s<seed>.json, run
manifests, the post bank and the persona bank -- so re-running this after a
campaign lands updates every number. Nothing is typed in by hand except prose.

    python make_artifact.py --seeds 1,101 --out /path/llm_bias.html
"""

from __future__ import annotations

import argparse
import glob
import html
import json
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors  # noqa: E402
import personas as persona_mod  # noqa: E402
from topics import DEFAULT_ACTIVE, PRIMARY, TOPICS  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(REPO, "data", "llm_bias")
FAMILY = {"llama3.1:8b": "Meta", "llama3.2:3b": "Meta", "gemma4:e2b": "Google", "granite4.1:3b": "IBM",
          "qwen2.5:7b": "Alibaba", "mistral:7b": "Mistral AI", "phi4-mini:3.8b": "Microsoft"}
E = html.escape


def short(m):
    return m.split(":")[0].replace("-mini", "-mini") + (":" + m.split(":")[1] if ":" in m else "")


def load_analysis(seed):
    p = os.path.join(DATA, f"analysis_s{seed}.json")
    return json.load(open(p)) if os.path.exists(p) else None


def manifests(seed):
    out = []
    for m in sorted(glob.glob(os.path.join(DATA, "runs", "*", "manifest.json"))):
        j = json.load(open(m))
        if j["config"]["seed"] == seed and not j["label"].startswith("smoke"):
            out.append(j)
    return out


def heatmap(res):
    fm = res["favorite_matrix"]  # {author: {judge: share}}
    judges, auth = res["judges"], res["authors"]
    chance = res["chance_share"]
    vmax = max(max(fm[a].get(j, 0) for a in auth) for j in judges) or 1
    head = "".join(f'<th scope="col"><span>{E(short(a))}</span></th>' for a in auth)
    rows = []
    for j in judges:
        cells = []
        for a in auth:
            v = fm[a].get(j)
            if v is None:
                cells.append("<td></td>")
                continue
            pct = int(round(100 * v / vmax))
            cls = ' class="diag"' if a == j else ""
            cells.append(f'<td{cls} style="--p:{pct}%"><b>{v * 100:.0f}</b></td>')
        rows.append(f'<tr><th scope="row">{E(short(j))}</th>{"".join(cells)}</tr>')
    return (f'<div class="scroll"><table class="heat"><thead><tr><th class="corner">judge ↓ · author →</th>'
            f'{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            f'<p class="cap">Each cell: percent of that judge\'s favourite picks that went to that author\'s post. '
            f'Chance is {chance * 100:.1f} % (one in {len(auth)}). Outlined cells are the diagonal: a model judging its own '
            f'posts. A whole column running dark means everyone likes that model\'s posts (quality). Self-preference is '
            f'an outlined cell darker than the rest of its column.</p>')


def forest(res, key="sp_chosen", unit="share points"):
    sp = res[key]
    items = [(k, v) for k, v in sp.items()]
    items.sort(key=lambda kv: (kv[0] == "_pooled", kv[0]))
    lo = min([v["ci95"][0] for _, v in items if v.get("ci95")] + [v["est"] for _, v in items] + [-0.05])
    hi = max([v["ci95"][1] for _, v in items if v.get("ci95")] + [v["est"] for _, v in items] + [0.05])
    pad = 0.1 * (hi - lo)
    lo, hi = lo - pad, hi + pad
    W, L, R, rowh = 640, 150, 20, 30
    H = rowh * len(items) + 40

    def x(v):
        return L + (v - lo) / (hi - lo) * (W - L - R)
    parts = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Self-preference estimates with 95% intervals">']
    # ticks
    step = 0.05 if hi - lo < 0.5 else 0.1
    t = step * round(lo / step)
    while t <= hi:
        parts.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="10" y2="{H - 24}" class="grid"/>'
                     f'<text x="{x(t):.1f}" y="{H - 8}" class="tick" text-anchor="middle">{t * 100:+.0f}</text>')
        t += step
    parts.append(f'<line x1="{x(0):.1f}" x2="{x(0):.1f}" y1="6" y2="{H - 24}" class="zero"/>')
    for i, (k, v) in enumerate(items):
        y = 24 + i * rowh
        name = "all judges pooled" if k == "_pooled" else short(k)
        cls = "pooled" if k == "_pooled" else "pt"
        if v.get("ci95"):
            a, b = v["ci95"]
            parts.append(f'<line x1="{x(a):.1f}" x2="{x(b):.1f}" y1="{y}" y2="{y}" class="whisk {cls}"/>')
        parts.append(f'<circle cx="{x(v["est"]):.1f}" cy="{y}" r="{6 if k == "_pooled" else 4.5}" class="{cls}"/>'
                     f'<text x="{L - 10}" y="{y + 4}" text-anchor="end" class="lab {cls}">{E(name)}</text>')
    parts.append("</svg>")
    return "".join(parts) + f'<p class="cap">Dot: self-preference estimate in {unit} (difference-in-differences). ' \
        f'Line: 95 % interval from the two-way cluster bootstrap. Right of the zero line means the judge favours its ' \
        f'own posts beyond what the other judges think they deserve.</p>'


def author_ranking(seed, res):
    """Column view: whose posts everyone likes, judged only by the OTHER models (so no self-vote counts)."""
    fm = res["favorite_matrix"]
    bank = authors.load_bank(seed)
    rows = []
    for a in res["authors"]:
        others = [fm[a][j] for j in res["judges"] if j != a and fm[a].get(j) is not None]
        words = [r["words"] for r in bank.values() if r["author"] == a and r["ok"]]
        rows.append((a, sum(others) / len(others) if others else 0, sum(words) / len(words) if words else 0))
    rows.sort(key=lambda r: -r[1])
    mx = max(r[1] for r in rows) or 1
    body = "".join(
        f"<tr><td><code>{E(a)}</code></td><td class='bar'><span style='width:{100 * v / mx:.0f}%'></span></td>"
        f"<td class='num'>{v * 100:.1f}</td><td class='num'>{w:.0f}</td></tr>" for a, v, w in rows)
    return (f"<h3>Whose posts do the other models like?</h3><p>Average favourite share each author gets from the "
            f"<em>other six</em> judges, so a model's vote for itself never counts. This is post quality as the models "
            f"see it. The last column is the author's average post length.</p>"
            f"<div class='scroll'><table class='plain rank'><thead><tr><th>author</th><th></th>"
            f"<th class='num'>% of picks</th><th class='num'>words</th></tr></thead><tbody>{body}</tbody></table></div>")


def recognition_section(seed):
    p = os.path.join(DATA, f"recognition_s{seed}_summary.json")
    if not os.path.exists(p):
        return ""
    s = json.load(open(p))
    rows = "".join(
        f"<tr><td><code>{E(m)}</code></td><td class='num'>{v['n']}</td><td class='num'>{v['claims_own'] * 100:.0f}</td>"
        f"<td class='num'>{(v['others_claim_this_author'] or 0) * 100:.0f}</td>"
        f"<td class='num'>{(v['did'] or 0) * 100:+.0f}</td></tr>" for m, v in s["per_model"].items())
    chance = next(iter(s["per_model"].values()))["chance"]
    return f"""<section><h2>Can a model spot its own post?</h2>
<p>A separate test with no personas. Each model was shown one round's posts, shuffled, and told “one of these is yours:
which?”. Guessing would be right {chance * 100:.0f} % of the time. The last column subtracts how often the <em>other</em>
models claim that same author's post, so a model that just claims the best-written post does not score. If a model prefers
its own posts but cannot pick them out, it likes a style it shares rather than knowingly favouring itself.</p>
<div class="scroll"><table class="plain"><thead><tr><th>model</th><th class="num">tries</th><th class="num">% claims own</th>
<th class="num">% others claim it</th><th class="num">difference</th></tr></thead><tbody>{rows}</tbody></table></div></section>"""


def verdict(res):
    sp = res["sp_chosen"].get("_pooled")
    cl = res.get("clogit", {})
    if not sp or not sp.get("ci95"):
        return "Not enough judges yet to test."
    lo, hi = sp["ci95"]
    if lo > 0:
        s = "Supported: judges pick their own posts more than other judges do, and the interval excludes zero."
    elif hi < 0:
        s = "Reversed: judges pick their own posts LESS than other judges do."
    else:
        s = "Not supported at this sample size: the pooled interval includes zero."
    if "odds_ratio" in cl:
        s += (f" The choice model agrees on direction if its odds ratio is on the same side of 1: "
              f"{cl['odds_ratio']:.2f} (95 % {cl['or_ci'][0]:.2f}–{cl['or_ci'][1]:.2f}, p = {cl['p']:.3g}).")
    return s


def results_section(seed, res, mans, title):
    if not res:
        return f'<section><h2>{E(title)}</h2><p class="muted">No analysis for seed {seed} yet.</p></section>'
    cfg = mans[0]["config"] if mans else {}
    n_personas = cfg.get("agents")
    rounds = cfg.get("rounds")
    sp = res["sp_chosen"]["_pooled"]
    tims = sorted(((m["config"]["judge"], sum(r["wall_s"] for r in m["rounds"]) /
                    max(1, sum(r["decisions"] for r in m["rounds"]))) for m in mans if m.get("rounds")),
                  key=lambda t: t[1])
    tim_rows = "".join(f"<tr><td>{E(short(j))}</td><td class='num'>{s:.2f}</td></tr>" for j, s in tims)
    pos = res.get("favorite_by_position", {})
    pos_rows = ""
    if pos:
        ps = sorted(pos, key=lambda k: int(k))
        pos_rows = "".join(
            f"<tr><td>{E(short(j))}</td>" + "".join(
                f"<td class='num'>{pos[p].get(j, 0) * 100:.0f}</td>" for p in ps) + "</tr>"
            for j in res["judges"])
        pos_head = "".join(f"<th class='num'>{int(p) + 1}</th>" for p in ps)
    aff = res.get("up_by_affinity", {})
    aff_rows = ""
    if aff:
        ks = sorted(aff, key=lambda k: int(k))
        aff_head = "".join(f"<th class='num'>{int(k):+d}</th>" for k in ks)
        aff_rows = "".join(
            f"<tr><td>{E(short(j))}</td>" + "".join(
                f"<td class='num'>{(aff[k].get(j) or 0) * 100:.0f}</td>" for k in ks) + "</tr>"
            for j in res["judges"])
    return f"""
<section id="results-{seed}">
  <h2>{E(title)}</h2>
  <p class="meta">Seed {seed} · {n_personas} personas × {rounds} rounds × {len(res['judges'])} judge models ·
  {res['n_valid']:,} valid decisions of {res['n_decisions']:,} ({res['valid_rate'] * 100:.1f} %)</p>
  <div class="verdict"><strong>Pooled self-preference: {sp['est'] * 100:+.1f} share points</strong>
  {f"(95 % interval {sp['ci95'][0] * 100:+.1f} to {sp['ci95'][1] * 100:+.1f})" if sp.get('ci95') else ""}.
  {E(verdict(res))}</div>
  <h3>Who picked whose post</h3>
  {heatmap(res)}
  {author_ranking(seed, res)}
  <h3>Self-preference, judge by judge</h3>
  {forest(res)}
  <details><summary>Same test on upvotes and downvotes</summary>
  <p>These use a double difference: each judge's rate for an author is first compared with that judge's own rate for the
  other authors, so a judge that upvotes everything does not look self-preferring.</p>
  {forest(res, "sp_up", "upvote-rate points")}
  {forest(res, "sp_down", "downvote-rate points")}
  </details>
  <details><summary>Does the persona matter? Upvote rate by interest in the topic</summary>
  <p>Interest runs from −2 (dislikes the topic) to +2 (loves it). If personas are doing their job, upvote rates
  should climb from left to right. Values are percent of posts upvoted.</p>
  <div class="scroll"><table class="plain"><thead><tr><th>judge</th>{aff_head if aff else ''}</tr></thead>
  <tbody>{aff_rows}</tbody></table></div>
  </details>
  <details><summary>Screen position: how often the post shown first, second… is picked</summary>
  <p>Percent of favourite picks at each position. An even spread is {res['chance_share'] * 100:.0f} %. Order is shuffled
  per persona, so a position habit spreads evenly over all authors: it adds noise, not bias.</p>
  <div class="scroll"><table class="plain"><thead><tr><th>judge</th>{pos_head if pos else ''}</tr></thead>
  <tbody>{pos_rows}</tbody></table></div>
  </details>
  <details><summary>Speed per judge</summary>
  <p>Wall-clock seconds per persona decision (7 posts on screen, 4 requests in parallel).</p>
  <table class="plain"><thead><tr><th>judge</th><th class="num">s / decision</th></tr></thead><tbody>{tim_rows}</tbody></table>
  </details>
</section>"""


def sample_slot(seed):
    bank = authors.load_bank(seed)
    recs = [r for r in bank.values() if r["round"] == 0 and r["topic"] == DEFAULT_ACTIVE[0] and r["ok"]]
    if not recs:
        return ""
    b = recs[0]["brief"]
    cards = "".join(
        f'<article class="post"><h4>{E(r["title"])}</h4><p>{E(r["body"])}</p>'
        f'<footer>written by <code>{E(r["author"])}</code> · {r["words"]} words</footer></article>'
        for r in sorted(recs, key=lambda r: r["author"]))
    return (f'<p class="brief"><b>The brief every model got:</b> post type “{E(b["ptype"])}”, subject '
            f'“{E(b["angle"])}”, posting as {E(b["voice"])}.</p><div class="posts">{cards}</div>'
            f'<p class="cap">Round 0 of seed {seed}. The judges saw these without the “written by” line and in a '
            f'shuffled order.</p>')


def persona_cards():
    bank = persona_mod.load_bank()
    picks = [bank[i] for i in (0, 1, 2)]
    out = []
    for p in picks:
        out.append(f'<article class="persona"><h4>{E(p["realname"])} <span>u/{E(p["username"])}</span></h4>'
                   f'<pre>{E(p["persona"])}</pre></article>')
    return "".join(out)


def build(seeds):
    main_seed = seeds[0]
    sections = []
    for s in seeds:
        res = load_analysis(s)
        mans = manifests(s)
        topic = TOPICS[mans[0]["config"]["topics"][0]]["name"] if mans else ""
        label = "Pilot" if s >= 100 else "Main run" if s == main_seed else "Second topic"
        sections.append(results_section(s, res, mans, f"{label}: {topic} (seed {s})"))
        if s == main_seed:
            sections.append(recognition_section(s))
    bank = persona_mod.load_bank()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    topic_list = "".join(
        f"<li><b>{E(TOPICS[t]['name'])}</b> <code>{E(TOPICS[t]['sub'])}</code>"
        + (" — <em>active now</em>" if t in DEFAULT_ACTIVE else "") + "</li>" for t in PRIMARY)
    extra = ", ".join(TOPICS[t]["name"] for t in TOPICS if t not in PRIMARY)
    model_rows = "".join(f"<tr><td><code>{E(m)}</code></td><td>{E(f)}</td></tr>" for m, f in FAMILY.items())
    return TEMPLATE.format(now=now, sections="".join(sections), sample=sample_slot(main_seed),
                           personas=persona_cards(), n_bank=len(bank), topic_list=topic_list, extra=E(extra),
                           model_rows=model_rows, bank_hash=persona_mod.bank_hash(bank))


TEMPLATE = """<title>Do Models Vote for Themselves?</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;700;800&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root {{
  --ground:#F2F4F6; --paper:#FFFFFF; --ink:#18202B; --muted:#5A6573; --rule:#D5DBE2;
  --accent:#1F6F8B; --accent-soft:#D6E8EF; --diag:#B7791F;
  --sans:"Archivo","Helvetica Neue",Arial,sans-serif; --serif:"Source Serif 4",Georgia,serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{ --ground:#11161C; --paper:#18202A; --ink:#E4E9EF; --muted:#9AA6B4;
    --rule:#2C3643; --accent:#63B4D1; --accent-soft:#1D3A47; --diag:#E2A948; color-scheme:dark; }}
}}
:root[data-theme="dark"] {{ --ground:#11161C; --paper:#18202A; --ink:#E4E9EF; --muted:#9AA6B4;
  --rule:#2C3643; --accent:#63B4D1; --accent-soft:#1D3A47; --diag:#E2A948; color-scheme:dark; }}
body {{ background:var(--ground); color:var(--ink); font:17px/1.6 var(--serif); padding-inline:16px; }}
.wrap {{ max-width:760px; margin:0 auto; padding-block:40px 80px; display:grid; gap:8px; }}
h1,h2,h3,h4 {{ font-family:var(--sans); line-height:1.2; text-wrap:balance; margin:0; }}
h1 {{ font-size:clamp(30px,6vw,46px); font-weight:800; letter-spacing:-0.01em; }}
h2 {{ font-size:26px; font-weight:800; margin-top:40px; padding-top:18px; border-top:2px solid var(--ink); }}
h3 {{ font-size:18px; font-weight:700; margin-top:26px; }}
h4 {{ font-size:16px; font-weight:700; }}
p {{ margin:8px 0; max-width:68ch; }}
.kicker {{ font:500 13px/1 var(--mono); letter-spacing:.08em; text-transform:uppercase; color:var(--accent); }}
.lede {{ font-size:20px; }}
.meta,.cap,.muted {{ color:var(--muted); font-size:14.5px; }}
code,pre {{ font-family:var(--mono); font-size:13.5px; }}
.scroll {{ overflow-x:auto; }}
table {{ border-collapse:collapse; font-family:var(--sans); font-size:14px; font-variant-numeric:tabular-nums; }}
table.plain th, table.plain td {{ padding:5px 10px; border-bottom:1px solid var(--rule); text-align:left; }}
.num {{ text-align:right !important; }}
table.heat {{ margin-top:10px; }}
table.heat th {{ font-weight:500; color:var(--muted); padding:4px 6px; }}
table.heat thead th span {{ display:inline-block; writing-mode:vertical-rl; transform:rotate(180deg); white-space:nowrap; font-family:var(--mono); font-size:12.5px; }}
table.heat tbody th {{ text-align:right; font-family:var(--mono); font-size:12.5px; white-space:nowrap; }}
table.heat .corner {{ text-align:left; vertical-align:bottom; font-size:12px; }}
table.heat td {{ width:52px; height:44px; text-align:center; border:2px solid var(--ground);
  background:color-mix(in srgb, var(--accent) var(--p), var(--paper)); }}
table.heat td b {{ font-weight:600; font-size:14px; background:var(--paper); color:var(--ink); padding:0 4px; border-radius:3px; }}
table.heat td.diag {{ outline:3px solid var(--diag); outline-offset:-3px; }}
.verdict {{ background:var(--paper); border-left:4px solid var(--diag); padding:12px 16px; margin:12px 0; }}
svg {{ width:100%; height:auto; max-width:680px; margin-top:8px; }}
svg .grid {{ stroke:var(--rule); stroke-width:1; }} svg .zero {{ stroke:var(--ink); stroke-width:1.5; }}
svg .tick,svg .lab {{ fill:var(--muted); font:12px var(--mono); }} svg .lab.pooled {{ fill:var(--ink); font-weight:600; }}
svg .whisk {{ stroke:var(--accent); stroke-width:2.5; }} svg .whisk.pooled {{ stroke:var(--diag); stroke-width:4; }}
svg circle.pt {{ fill:var(--accent); }} svg circle.pooled {{ fill:var(--diag); }}
details {{ background:var(--paper); border:1px solid var(--rule); border-radius:6px; padding:10px 14px; margin-top:12px; }}
summary {{ font-family:var(--sans); font-weight:600; cursor:pointer; }}
summary:focus-visible {{ outline:2px solid var(--accent); }}
.steps {{ display:grid; gap:10px; counter-reset:s; padding:0; list-style:none; }}
.steps li {{ background:var(--paper); border:1px solid var(--rule); border-radius:6px; padding:12px 16px 12px 52px; position:relative; }}
.steps li::before {{ counter-increment:s; content:counter(s); position:absolute; left:14px; top:12px; width:26px; height:26px;
  border-radius:50%; background:var(--accent); color:var(--paper); font:700 14px/26px var(--sans); text-align:center; }}
.posts {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:10px; margin-top:10px; }}
.post {{ background:var(--paper); border:1px solid var(--rule); border-radius:6px; padding:12px; font-size:15px; display:grid; gap:6px; align-content:start; }}
.post p {{ margin:0; }} .post footer {{ font:12.5px var(--mono); color:var(--muted); }}
.persona {{ background:var(--paper); border:1px solid var(--rule); border-radius:6px; padding:12px 14px; margin-top:10px; }}
.persona h4 span {{ font:400 13px var(--mono); color:var(--muted); }}
.persona pre {{ white-space:pre-wrap; margin:6px 0 0; font-size:13px; line-height:1.5; }}
.formula {{ font:15px/1.5 var(--mono); background:var(--paper); border:1px solid var(--rule); border-radius:6px; padding:12px 14px; overflow-x:auto; }}
.brief {{ background:var(--accent-soft); padding:10px 14px; border-radius:6px; }}
ul,ol {{ max-width:68ch; }}
table.rank td.bar {{ width:45%; min-width:80px; }}
table.rank td.bar span {{ display:block; height:12px; background:var(--accent); border-radius:2px; }}
</style>
<div class="wrap">
<p class="kicker">LLM Bias · OASIS · local models only · updated {now}</p>
<h1>Do models vote for themselves?</h1>
<p class="lede">Seven local AI models each write a Reddit post on the same subject. Then each model pretends to be
hundreds of different people and votes on all seven posts. The question: when a model is playing a person, does that
person keep choosing the post the model wrote?</p>
<p>If the answer is yes, any simulation that uses one model both to write content and to play the audience is tilted
toward that model's own writing. The effect has a name in the research literature, <em>self-preference bias</em>:
a model judging text rates its own higher.</p>

{sections}

<h2>How one round works</h2>
<ol class="steps">
<li><b>One brief, seven writers.</b> Each round has a subject (for example “paying off credit card debt”), a post type
(“asking for advice”) and a poster (“a 24-year-old in their first full-time job”). All seven models get exactly that brief
and each writes one post, 60–120 words, plain text. Any post that mentions AI or a model name is thrown out and rewritten.
Formatting such as bold text, emoji and bullet lists is stripped, so style tics are not a free giveaway.</li>
<li><b>One model plays everyone.</b> A single model (the <em>judge</em>) takes on each persona in turn. It sees the seven
posts with no author names, no vote counts and in its own shuffled order, then answers in a fixed format: up, down or
no vote on each post, the one post it most wants to read (its <em>favourite</em>), and one sentence of reasoning in character.</li>
<li><b>Votes land on a real OASIS platform.</b> Posts and votes are made through OASIS's own reddit actions
(<code>create_post</code>, <code>like_post</code>, <code>dislike_post</code>), so the database is a standard OASIS record.
Every decision is also written to a log the moment it is made.</li>
<li><b>Swap the judge, repeat.</b> The whole thing runs again with each of the seven models as judge, over the same posts,
the same personas and the same shuffled orders. Only the judge changes.</li>
</ol>

<h3>Why swapping the judge makes the test fair</h3>
<p>Suppose llama's posts get picked a lot. That alone proves nothing, because llama might just write better posts.
The swap fixes this. If llama's posts are simply good, every judge picks them. If llama is biased toward itself, llama
picks them <em>more than the other judges do</em>. So the measure is</p>
<p class="formula">self-preference(J) = how often judge J picks J's post − how often the other judges pick J's post</p>
<p>This subtraction is called a <em>difference-in-differences</em>. It cancels out “J writes good posts”. Zero means
no bias. A second check, a <em>conditional logit</em> (a standard model for “which of these options did someone pick?”),
gives every individual post its own quality score and every screen position its own pull. It then asks whether being the judge's
own post adds anything on top. Its answer is an <em>odds ratio</em>: 1.0 means no boost; 1.5 means a post's odds of
being picked rise by half when the judge wrote it.</p>
<p>The uncertainty bands use a <em>cluster bootstrap</em>. The same persona votes every round, and everyone in a round sees the same posts,
so votes are not independent. The bootstrap reruns the analysis 2,000 times on resampled personas and rounds, which gives
honest, wider intervals.</p>
<p>This was tested before any real run. On made-up data where one model writes better posts but nobody favours
themselves, the naive “how often does J pick J” figure is fooled (over 40 % against 33 % chance) and this method is not.
On made-up data with a planted bias, it recovers the planted size.</p>

<h3>What the posts look like</h3>
{sample}

<h2>The people</h2>
<p>{n_bank:,} fixed personas, the same ones in every run (file hash <code>{bank_hash}</code>). Each has an age,
job, home, money situation, a Big Five personality score (openness, conscientiousness, extraversion, agreeableness,
neuroticism, each 1–10), a signed interest in each of 15 topics from −2 (dislikes) to +2 (loves), what they value in a
post, a pet peeve, and a voting habit (generous, typical or harsh). Everyone loves at least one topic and dislikes at
least one.</p>
<p><b>No AI wrote them.</b> If llama had written the personas, llama-flavoured descriptions could nudge judges toward
llama-flavoured posts, and that could never be untangled afterwards. Each persona is built from lists of attributes with
a fixed random seed and one fixed sentence template. The layout follows OASIS's own reddit profile format, plus the
Big Five format of the two reference simulations.</p>
{personas}

<h2>Topics</h2>
<p>Five planned topics, switched on one at a time:</p>
<ul>{topic_list}</ul>
<p class="muted">Ten more are defined so each persona can have realistic likes and dislikes: {extra}.</p>

<h2>Models</h2>
<p>Local only: everything runs on the Mac through Ollama, with no paid services. Seven models from six makers, so the
bias can be checked across very different training. The two Llamas are siblings on purpose, to show whether a model
also favours its family.</p>
<table class="plain"><thead><tr><th>model</th><th>maker</th></tr></thead><tbody>{model_rows}</tbody></table>

<h2>How many agents can run</h2>
<p>Agents never talk to each other here, so there is no memory ceiling, only time. Sim 4 stopped at 99 because its
persona file had only 99 usable people; this bank has 1,000.</p>
<p class="formula">hours ≈ agents × rounds × topics × 24 s ÷ 3600<br>(24 s = one decision by each of the 7 judges, back to back)</p>
<p>99 agents × 8 rounds × 1 topic ≈ 5.3 hours. 1,000 agents × 1 round ≈ 6.7 hours.</p>
</div>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="1")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    seeds = [int(s) for s in a.seeds.split(",")]
    with open(a.out, "w") as f:
        f.write(build(seeds))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
