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
    return (f'<div class="scroll"><table class="heat"><thead><tr><th class="corner">judge (pretending) ↓ · writer →</th>'
            f'{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            f'<p class="cap">How to read it: each row is the AI doing the pretending (the <b>judge</b>); each column is the AI '
            f'that wrote the post. The number is how many times out of 100 that judge picked that writer\'s post as its '
            f'favourite. If picks were random, every box would be about {chance * 100:.0f}. Outlined boxes are an AI judging '
            f'its own posts. A whole dark column means everyone likes that writer (good posts). Cheering for itself looks '
            f'like an outlined box that is darker than the rest of its column.</p>')


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
    return "".join(parts) + f'<p class="cap">The dot is our best guess of how much extra each AI picks its own post; the ' \
        f'line is the range we are 95 % sure about. Right of the zero line = the AI picks its own post more than the other ' \
        f'AIs pick that same post. If the line crosses zero, it could be luck. (For grown-ups: {unit}, ' \
        f'difference-in-differences, two-way cluster bootstrap.)</p>'


def author_ranking(seed, res):
    """Column view: whose posts everyone likes, judged only by the OTHER models (so no self-vote counts)."""
    fm = res["favorite_matrix"]
    bank = {}
    for sd in ((1, 2) if seed == "both" else (seed,)):
        bank.update(authors.load_bank(sd))
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
    return (f"<h3>Whose posts do the other AIs like best?</h3><p>How often each writer's post was picked as the favourite, "
            f"counting only the <em>other six</em> AIs, so an AI's vote for itself never counts. Think of it as “which AI "
            f"writes the best posts, according to everyone else”. The last column is how long its posts are.</p>"
            f"<div class='scroll'><table class='plain rank'><thead><tr><th>author</th><th></th>"
            f"<th class='num'>picks per 100</th><th class='num'>words</th></tr></thead><tbody>{body}</tbody></table></div>")


def recognition_section(seed):
    p = os.path.join(DATA, f"recognition_s{seed}_summary.json")
    if not os.path.exists(p):
        return ""
    s = json.load(open(p))
    rows = "".join(
        f"<tr><td><code>{E(m)}</code></td><td class='num'>{v['n']}</td><td class='num'>{v['claims_own'] * 100:.0f}</td>"
        f"<td class='num'>{(v['others_claim_this_author'] or 0) * 100:.0f}</td>"
        f"<td class='num'>{(v['did'] or 0) * 100:+.0f}</td>"
        f"<td class='num'>{(v['did_ci95'][0] * 100):+.0f} to {(v['did_ci95'][1] * 100):+.0f}</td></tr>"
        if v.get('did_ci95') else
        f"<td class='num'>{(v['did'] or 0) * 100:+.0f}</td><td></td></tr>"
        for m, v in s["per_model"].items())
    chance = next(iter(s["per_model"].values()))["chance"]
    return f"""<section><h2>Can an AI spot its own post?</h2>
<p>A separate test with no pretend people. We showed each AI a round's seven posts, mixed up, and said “one of these is
yours: which one?”. Guessing blindly would be right about {chance * 100:.0f} times in 100. The “difference” column takes
away how often the <em>other</em> AIs point at that same post, so an AI that just points at the best post doesn't score.
The answer: the AIs mostly can't tell which post is theirs. So when they favour their own posts, it isn't on purpose. They
just like the kind of writing they themselves produce.</p>
<div class="scroll"><table class="plain"><thead><tr><th>AI</th><th class="num">tries</th><th class="num">points at its own (per 100)</th>
<th class="num">others point at it (per 100)</th><th class="num">difference</th><th class="num">95 % sure range</th></tr></thead><tbody>{rows}</tbody></table></div></section>"""


def few_rounds_note(rounds):
    if not rounds or rounds > 3:
        return ""
    return (f'<p class="cap"><b>Careful with these ranges.</b> Only {rounds} rounds means only {rounds} sets of posts. With so '
            f'few, the “95 % sure” ranges come out too narrow, because they can\'t see how much results change from one set of '
            f'posts to the next. Use this section to check which way things point, not to prove anything.</p>')


def verdict(res):
    sp = res["sp_chosen"].get("_pooled")
    if not sp or not sp.get("ci95"):
        return "Not enough judges yet to test."
    lo, hi = sp["ci95"]
    if lo > 0:
        s = "Yes: the AIs pick their own posts more often than the other AIs pick those same posts, and the whole 95 % range is above zero."
    elif hi < 0:
        s = "No, the opposite: the AIs pick their own posts LESS often than the other AIs do."
    else:
        s = "Can't tell from this much data: the 95 % range includes zero, so it could be luck."
    cc = res.get("clogit_cluster") or {}
    if "or_ci_cluster" in cc:
        pc = cc["p_cluster"]
        ptxt = f"p < {1 / cc['B']:.3f}" if pc == 0 else f"p = {pc:.2f}"
        s += (f" Another way to say it: when the judge wrote a post, that post is about {cc['odds_ratio']:.1f} times as "
              f"likely to be picked (for grown-ups: odds ratio {cc['odds_ratio']:.2f}, 95 % range "
              f"{cc['or_ci_cluster'][0]:.2f}–{cc['or_ci_cluster'][1]:.2f}, {ptxt}).")
    return s


def results_section(seed, res, mans, title, meta=None):
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
  <p class="meta">{meta or f"Post set {seed} · {n_personas} people × {rounds} rounds"} × {len(res['judges'])} AIs taking turns as judge ·
  {res['n_valid']:,} usable answers out of {res['n_decisions']:,} ({res['valid_rate'] * 100:.1f} %)</p>
  <div class="verdict"><strong>The AIs picked their own post {sp['est'] * 100:+.1f} more times in 100 than the other AIs picked it</strong>
  {f"(95 % sure range {sp['ci95'][0] * 100:+.1f} to {sp['ci95'][1] * 100:+.1f})" if sp.get('ci95') else ""}.
  {verdict(res)}</div>
  {few_rounds_note(rounds)}
  <h3>Who picked whose post as their favourite</h3>
  {heatmap(res)}
  {author_ranking(seed, res)}
  <h3>Does each AI pick its own post extra often?</h3>
  {forest(res)}
  <details><summary>The same test using thumbs-up and thumbs-down</summary>
  <p>Besides picking a favourite, every pretend person also gave each post a thumbs-up, thumbs-down or nothing. Some AIs
  give thumbs-up to almost everything, so we first compare each AI with itself (how much more it likes this writer than
  the other writers), then compare that with the other AIs. First chart: thumbs-up. Second chart: thumbs-down, where
  “kinder to its own posts” shows up as a number <em>below</em> zero.</p>
  {forest(res, "sp_up", "upvote-rate points")}
  {forest(res, "sp_down", "downvote-rate points")}
  </details>
  <details><summary>Does the pretend person matter? Thumbs-up by how much they like the topic</summary>
  <p>Each person's interest in the topic runs from −2 (really dislikes it) to +2 (loves it). If the AI is really playing
  the person, thumbs-up should go up from left to right. Numbers are thumbs-up per 100 posts.</p>
  <div class="scroll"><table class="plain"><thead><tr><th>judge</th>{aff_head if aff else ''}</tr></thead>
  <tbody>{aff_rows}</tbody></table></div>
  </details>
  <details><summary>Does it matter whether a post is shown first, second, third…?</summary>
  <p>Favourite picks per 100 at each spot on the screen. If spot didn't matter, each would be about
  {res['chance_share'] * 100:.0f}. Some AIs do prefer certain spots, but the order is shuffled for every person, so that
  habit lands on every writer equally. It makes the results noisier, not unfair.</p>
  <div class="scroll"><table class="plain"><thead><tr><th>judge</th>{pos_head if pos else ''}</tr></thead>
  <tbody>{pos_rows}</tbody></table></div>
  </details>
  <details><summary>How fast each AI is</summary>
  <p>Seconds for one pretend person to read all 7 posts and answer (4 people are handled at the same time).</p>
  <table class="plain"><thead><tr><th>AI</th><th class="num">seconds per person</th></tr></thead><tbody>{tim_rows}</tbody></table>
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
    return (f'<p class="brief"><b>The instructions every AI got:</b> kind of post “{E(b["ptype"])}”, about '
            f'“{E(b["angle"])}”, written as {E(b["voice"])}.</p><div class="posts">{cards}</div>'
            f'<p class="cap">The first round of post set {seed}. The judges saw these without the “written by” line, '
            f'mixed up in a different order for every person.</p>')


def persona_cards():
    bank = persona_mod.load_bank()
    picks = [bank[i] for i in (0, 1, 2)]
    out = []
    for p in picks:
        out.append(f'<article class="persona"><h4>{E(p["realname"])} <span>u/{E(p["username"])}</span></h4>'
                   f'<pre>{E(p["persona"])}</pre></article>')
    return "".join(out)


def bottom_line(res):
    if not res:
        return ""
    sp = res["sp_chosen"]["_pooled"]
    cc = res.get("clogit_cluster") or {}
    pos = sum(1 for k, v in res["sp_chosen"].items() if k != "_pooled" and v["est"] > 0)
    return f"""<div class="verdict"><strong>The short answer: yes, a little.</strong> When an AI pretends to be a person
and picks a favourite post, it picks its own post about {sp['est'] * 100:.0f} more times out of 100 than the other AIs pick
that same post. (With seven posts to choose from, a fair share would be about {res['chance_share'] * 100:.0f} picks in
100.) {pos} of the {len(res['judges'])} AIs lean this way. Two catches: the AIs can't
actually tell which post they wrote, so they aren't doing it on purpose (they just like writing that sounds like theirs);
and it shows up in which post they pick as a favourite more clearly than in their thumbs-up and thumbs-down.
<p class="grown">For grown-ups: pooled difference-in-differences {sp['est'] * 100:+.1f} share points (95 % range
{sp['ci95'][0] * 100:.1f} to {sp['ci95'][1] * 100:.1f}); conditional-logit odds ratio {cc.get('odds_ratio', 0):.2f}.</p></div>"""


def build(seeds):
    main_seed = seeds[0]
    sections = []
    comb = os.path.join(DATA, "analysis_combined_s1_s2.json")
    comb_res = json.load(open(comb)) if os.path.exists(comb) else None
    if comb_res:
        sections.append(results_section("both", comb_res, manifests(1) + manifests(2),
                                        "Both topics together", meta="Money posts (10 rounds) + car posts (3 rounds) · 99 people"))
    for s in seeds:
        res = load_analysis(s)
        mans = manifests(s)
        topic = TOPICS[mans[0]["config"]["topics"][0]]["name"] if mans else ""
        label = "Practice run" if s >= 100 else "Main run" if s == main_seed else "Second topic"
        sections.append(results_section(s, res, mans, f"{label}: {topic} (post set {s})"))
        if s == main_seed:
            sections.append(recognition_section(s))
    bank = persona_mod.load_bank()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    topic_list = "".join(
        f"<li><b>{E(TOPICS[t]['name'])}</b> <code>{E(TOPICS[t]['sub'])}</code>"
        + (" — <em>active now</em>" if t in DEFAULT_ACTIVE else "") + "</li>" for t in PRIMARY)
    extra = ", ".join(TOPICS[t]["name"] for t in TOPICS if t not in PRIMARY)
    model_rows = "".join(f"<tr><td><code>{E(m)}</code></td><td>{E(f)}</td></tr>" for m, f in FAMILY.items())
    return TEMPLATE.format(now=now, sections=bottom_line(comb_res) + "".join(sections), sample=sample_slot(main_seed),
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
.grown {{ color:var(--muted); font:14px/1.5 var(--sans); margin-top:6px; }}
.newer {{ background:var(--accent-soft); padding:10px 14px; border-radius:6px; }}
a {{ color:var(--accent); }}
.formula {{ font:15px/1.5 var(--mono); background:var(--paper); border:1px solid var(--rule); border-radius:6px; padding:12px 14px; overflow-x:auto; }}
.brief {{ background:var(--accent-soft); padding:10px 14px; border-radius:6px; }}
ul,ol {{ max-width:68ch; }}
table.rank td.bar {{ width:45%; min-width:80px; }}
table.rank td.bar span {{ display:block; height:12px; background:var(--accent); border-radius:2px; }}
</style>
<div class="wrap">
<p class="kicker">LLM Bias · test 1 (night 1, 23-24 Sep) · local AIs only · updated {now}</p>
<h1>Do AIs vote for themselves?</h1>
<p class="lede">Seven AI programs each wrote a pretend Reddit post about the same thing. Then each AI took a turn
pretending to be 99 different people, like Marcus, a retired mail carrier, or Priya, a store manager. Each pretend person
read all seven posts and picked a favourite. The question: when an AI is pretending to be someone, does that person
keep picking the post the AI wrote?</p>
<p>Why it matters: researchers are starting to use AIs as pretend crowds. If an AI quietly favours its own writing, a
test that uses one AI to write posts <em>and</em> play the audience is unfair. Scientists call this <em>self-preference
bias</em>.</p>
<p class="newer">This page is about our <b>first</b> test. The newer test uses two AIs and has people scroll a whole feed
instead of picking a favourite. It has its own page: <a href="https://claude.ai/artifact/PEMNidbCam72v6qKC3GNBx">Scroll Test</a>.</p>

{sections}

<h2>How one round works</h2>
<ol class="steps">
<li><b>Same instructions, seven writers.</b> Every round starts with instructions like “a 24-year-old in their first job
asks for advice about paying off a credit card”. All seven AIs get exactly those instructions and each writes one post,
60 to 120 words. Any post that mentions AI is thrown out and rewritten. Bold text, emoji and bullet points are removed, so
no AI can be recognised by its decorations.</li>
<li><b>One AI plays everybody.</b> One AI (the <em>judge</em>) pretends to be each of the 99 people in turn. It sees the
seven posts with no names and no scores, mixed into a different order for every person. For each post it gives a
thumbs-up, thumbs-down or nothing, picks the one post it most wants to read (its <em>favourite</em>), and says why in one
sentence, in character.</li>
<li><b>The votes go on a real pretend Reddit.</b> Posts and votes are made on OASIS, a program that simulates social
media, so everything is saved like a real site's records. Every answer is also saved the moment it's made.</li>
<li><b>Swap the judge and do it again.</b> The whole thing is repeated with each of the seven AIs as judge, on the same
posts, the same people and the same order. Only the judge changes.</li>
</ol>

<h3>Why swapping the judge makes the test fair</h3>
<p>Say llama's posts get picked a lot. That doesn't prove llama is cheating: maybe llama just writes good posts. Swapping
judges fixes this. If llama's posts are simply good, <em>every</em> judge picks them. If llama is cheering for itself,
llama picks them <em>more than the other judges do</em>. So we measure:</p>
<p class="formula">how often an AI picks its own post − how often the other AIs pick that same post</p>
<p>Zero means no cheering for itself. Anything above zero is the extra.</p>
<details><summary>For grown-ups: the statistics</summary>
<p>That subtraction is a <em>difference-in-differences</em>; it cancels “J writes good posts”. A second check, a
<em>conditional logit</em> (a standard model for “which of these options did someone pick?”), gives every post its own
quality score and every screen position its own pull, then asks whether being the judge's own post adds anything on top.
It reports an <em>odds ratio</em>: 1.0 means no boost, 1.5 means the odds of being picked rise by half.</p>
<p>The same person votes every round and everyone in a round sees the same posts, so answers are not independent. The
ranges use a <em>two-way cluster bootstrap</em>: the analysis is rerun 2,000 times on resampled people and rounds, which
gives honest, wider ranges.</p>
<p>Checked before any real run: on made-up data where one AI writes better posts but nobody favours themselves, the naive
“how often does J pick J” figure is fooled (over 40 % against 33 % chance) and this method is not. On made-up data with a
planted bias, it finds the planted size.</p>
</details>

<h3>What the posts look like</h3>
{sample}

<h2>The pretend people</h2>
<p>We made {n_bank:,} pretend people; the same ones are used in every run (the computer checks a fingerprint,
<code>{bank_hash}</code>, to be sure). Each has an age, a job, a hometown, how much money they have, a personality, how
much they like each of 15 topics (from −2, really dislikes, to +2, loves), what they like in a post, a pet peeve, and how
easy they are to please. Everyone loves at least one topic and dislikes at least one.</p>
<p><b>No AI wrote them.</b> If llama had written the people, their descriptions might sound like llama and nudge the
judges toward llama's posts. So each person is built by the computer from lists of ages, jobs, towns and so on, using one
fixed sentence pattern. Here are three of them, exactly as the AI sees them:</p>
{personas}

<h2>Topics</h2>
<p>Five main topics, used one at a time:</p>
<ul>{topic_list}</ul>
<p class="muted">Ten more exist only so each person can have realistic likes and dislikes: {extra}.</p>

<h2>The seven AIs</h2>
<p>All of them run on this computer through a free program called Ollama; no paid services. They come from six different
companies, so we can see whether the habit shows up everywhere. The two Llamas are siblings on purpose, to check whether an
AI also favours its family.</p>
<table class="plain"><thead><tr><th>AI</th><th>made by</th></tr></thead><tbody>{model_rows}</tbody></table>

<h2>How many pretend people can we run?</h2>
<p>The pretend people never talk to each other, so the computer doesn't run out of memory. The only limit is time. Each
person takes about 24 seconds for all seven AIs to judge once.</p>
<p class="formula">hours ≈ people × rounds × topics × 24 seconds ÷ 3,600</p>
<p>99 people × 8 rounds × 1 topic ≈ 5.3 hours. 1,000 people × 1 round ≈ 6.7 hours.</p>
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
