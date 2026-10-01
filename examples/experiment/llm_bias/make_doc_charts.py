"""Widget code for the report doc's Test 6 tab, built from data/llm_bias/two_ai/analysis.json.

    python make_doc_charts.py      # prints {"rounds": code, "rates": code, "length": code} as JSON

Each chart is one <claude.Visualize> module with its rows inline, so a redraw after more rounds is one call.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors  # noqa: E402

R = json.load(open(os.path.join(authors.DATA, "two_ai", "analysis.json")))
A, B = R["ai_a"], R["ai_b"]
pts = lambda x: round(x * 100, 1)  # noqa: E731


def wider(a, b):
    a, b = a or b, b or a
    return a if (a[1] - a[0]) >= (b[1] - b[0]) else b


def rounds_chart():
    rows = [{"round": f"Round {r['round']}", "measure": m, "boost": pts(r[k])}
            for r in R["per_round"] for m, k in (("Upvotes", "like_dd"), ("Downvotes", "dislike_dd"))]
    pooled = []
    for m, rb, sp in (("Upvotes", R["round_boot_up"], R["sp_up"]["_pooled"]),
                      ("Downvotes", R["round_boot_down"], R["sp_down"]["_pooled"])):
        lo, hi = wider(rb["ci95"], sp["ci95"])
        pooled.append({"measure": m, "est": pts(rb["est"]), "lo": pts(lo), "hi": pts(hi)})
    n = len(R["per_round"])
    title = f"Own-AI boost, {n} rounds: upvotes {pooled[0]['est']:+} points, downvotes {pooled[1]['est']:+}"
    return ("export default () => <claude.Visualize data-claude-component='two-ai-boost-by-round' sources={{rows:{kind:'data', data:"
            + json.dumps(rows) + "}, pooled:{kind:'data', data:" + json.dumps(pooled) + "}}}>{({rows, pooled, datum}) => { "
            "const vals = rows.map(r => r.boost).concat(pooled.map(p => p.lo), pooled.map(p => p.hi), [0]); "
            "const lo = Math.floor(Math.min(...vals) / 5) * 5, hi = Math.ceil(Math.max(...vals) / 5) * 5; "
            "const left = 110, right = 630, x = v => left + (v - lo) / (hi - lo) * (right - left); "
            "const rounds = [...new Set(rows.map(r => r.round))]; const step = 20, panel = rounds.length * step + 60, y0 = 88; "
            "const ticks = []; for (let t = lo; t <= hi; t += 5) ticks.push(t); "
            "const H = y0 + 2 * panel + 20; "
            "return <svg viewBox={`0 0 760 ${H}`} role='img' aria-label='" + title + "' fontSize='12'>"
            "<text data-claude-text-id='title' x='0' y='22' fontSize='16' fill='var(--cds-text-primary)'>" + title + "</text>"
            "<text data-claude-text-id='sub' x='0' y='44' fill='var(--cds-text-secondary)'>Points. One dot per round; black bar = all rounds pooled, shaded = the wider 95% interval.</text><text data-claude-text-id='sub2' x='0' y='62' fill='var(--cds-text-secondary)'>Upvotes: right of 0 = own AI favoured. Downvotes: left of 0 = own AI favoured.</text>"
            "{pooled.map((p, k) => { const py = y0 + k * panel; const mine = rows.filter(r => r.measure === p.measure); "
            "return <g key={p.measure} data-claude-anchor={`panel-${p.measure}`}>"
            "<text x='0' y={py + 12} fontSize='13' fontWeight='600' fill='var(--cds-text-primary)'>{p.measure}</text>"
            "{ticks.map(t => <g key={t}><line x1={x(t)} x2={x(t)} y1={py + 20} y2={py + panel - 20} stroke={t === 0 ? 'var(--cds-chart-axis)' : 'var(--cds-chart-grid)'} strokeDasharray={t === 0 ? '4 3' : ''}/><text x={x(t)} y={py + panel - 6} textAnchor='middle' fill='var(--cds-text-secondary)'>{t > 0 ? `+${t}` : `${t}`}</text></g>)}"
            "{mine.map((r, i) => <g key={r.round}><text x={left - 10} y={py + 32 + i * step} textAnchor='end' fill='var(--cds-text-secondary)'>{r.round}</text>"
            "<circle cx={x(r.boost)} cy={py + 28 + i * step} r='5' fill='var(--cds-chart-muted)' {...datum(r, 'boost')}><title>{`${r.round}, ${r.measure}: ${r.boost > 0 ? '+' : ''}${r.boost} points`}</title></circle></g>)}"
            "<g {...datum(p)}><rect x={x(p.lo)} y={py + 28 + mine.length * step - 7} width={x(p.hi) - x(p.lo)} height='14' fill='var(--cds-chart-categorical-1)' fillOpacity='0.25'><title>{`${p.measure}, all rounds: ${p.est > 0 ? '+' : ''}${p.est} points, 95% interval ${p.lo} to ${p.hi}`}</title></rect>"
            "<rect x={x(p.est) - 2} y={py + 28 + mine.length * step - 11} width='4' height='22' fill='var(--cds-text-primary)'/>"
            "<text x={left - 10} y={py + 32 + mine.length * step} textAnchor='end' fontWeight='600' fill='var(--cds-text-primary)'>All rounds</text>"
            "<text x={x(p.hi) + 8} y={py + 32 + mine.length * step} fill='var(--cds-text-primary)'>{`${p.est > 0 ? '+' : ''}${p.est.toFixed(1)} [${p.lo.toFixed(1)}, ${p.hi.toFixed(1)}]`}</text></g></g>; })}"
            "</svg>; }}</claude.Visualize>;")


def rates_chart():
    rows = []
    for j in (A, B):
        for au in (A, B):
            rows.append({"crowd": f"{j.split(':')[0]}-played users", "author": f"{au.split(':')[0]} posts",
                         "own": int(au == j), "up": pts(R["rate_up"][au][j])})
    a, b = A.split(":")[0], B.split(":")[0]
    ga = pts(R["rate_up"][A][A] - R["rate_up"][B][A])  # A-users: own minus other
    gb = pts(R["rate_up"][B][B] - R["rate_up"][A][B])  # B-users: own minus other
    title = f"{a}-played users upvote {a} posts {ga:+} points more"
    title2 = f"{b}-played users upvote {b} posts {gb:+} points more"
    return ("export default () => <claude.Visualize data-claude-component='two-ai-upvote-rates' sources={{rows:{kind:'data', data:"
            + json.dumps(rows) + "}}}>{({rows, datum}) => { "
            "const crowds = [...new Set(rows.map(r => r.crowd))]; const lo = 50, hi = 90; "
            "const left = 130, right = 680, x = v => left + (v - lo) / (hi - lo) * (right - left), y0 = 112; "
            "return <svg viewBox='0 0 760 340' role='img' aria-label='" + title + "; " + title2 + "' fontSize='12'>"
            "<text data-claude-text-id='title' x='0' y='22' fontSize='16' fill='var(--cds-text-primary)'>" + title + "</text>"
            "<text data-claude-text-id='title2' x='0' y='44' fontSize='16' fill='var(--cds-text-primary)'>" + title2 + "</text>"
            "<text data-claude-text-id='sub' x='0' y='66' fill='var(--cds-text-secondary)'>Upvote rate (%) over all rounds. Blue = the post was written by the AI playing the users. Axis starts at 50%.</text>"
            "{[50, 60, 70, 80, 90].map(t => <g key={t}><line x1={x(t)} x2={x(t)} y1={y0 - 24} y2='300' stroke='var(--cds-chart-grid)'/><text x={x(t)} y='318' textAnchor='middle' fill='var(--cds-text-secondary)'>{`${t}%`}</text></g>)}"
            "{crowds.map((c, k) => <g key={c} data-claude-anchor={`crowd-${k}`}><text x='0' y={y0 + k * 100 - 8} fontWeight='600' fill='var(--cds-text-primary)'>{c}</text>"
            "{rows.filter(r => r.crowd === c).map((r, i) => <g key={r.author}><text x={left - 10} y={y0 + k * 100 + i * 30 + 14} textAnchor='end' fill='var(--cds-text-secondary)'>{r.author}</text>"
            "<rect x={left} y={y0 + k * 100 + i * 30} width={x(r.up) - left} height='20' fill={r.own ? 'var(--cds-chart-categorical-1)' : 'var(--cds-chart-muted)'} {...datum(r, 'up')}><title>{`${r.crowd}, ${r.author}: ${r.up}% upvoted`}</title></rect>"
            "<text x={x(r.up) + 6} y={y0 + k * 100 + i * 30 + 14} fill='var(--cds-text-primary)' {...datum(r, 'up')}>{`${r.up}%`}</text></g>)}</g>)}"
            "</svg>; }}</claude.Visualize>;")


def length_chart():
    rows = [{"crowd": f"{j.split(':')[0]}-played users", "est": pts(v["per_100_words"]), "lo": pts(v["ci95"][0]),
             "hi": pts(v["ci95"][1])} for j, v in R["length_taste"].items()]
    rows.sort(key=lambda r: r["est"])
    title = "The two AIs play the same users with opposite tastes for post length"
    return ("export default () => <claude.Visualize data-claude-component='two-ai-length-taste' sources={{rows:{kind:'data', data:"
            + json.dumps(rows) + "}}}>{({rows, datum}) => { "
            "const vals = rows.flatMap(r => [r.lo, r.hi]).concat([0]); const lo = Math.floor(Math.min(...vals) / 10) * 10, hi = Math.ceil(Math.max(...vals) / 10) * 10; "
            "const left = 190, right = 720, x = v => left + (v - lo) / (hi - lo) * (right - left), y0 = 90; "
            "const ticks = []; for (let t = lo; t <= hi; t += 10) ticks.push(t); "
            "return <svg viewBox='0 0 760 220' role='img' aria-label='" + title + "' fontSize='12'>"
            "<text data-claude-text-id='title' x='0' y='22' fontSize='16' fill='var(--cds-text-primary)'>" + title + "</text>"
            "<text data-claude-text-id='sub' x='0' y='44' fill='var(--cds-text-secondary)'>Change in upvote rate (points) for every extra 100 words, author held fixed; whiskers = 95% interval.</text>"
            "{ticks.map(t => <g key={t}><line x1={x(t)} x2={x(t)} y1='70' y2='180' stroke={t === 0 ? 'var(--cds-chart-axis)' : 'var(--cds-chart-grid)'} strokeDasharray={t === 0 ? '4 3' : ''}/><text x={x(t)} y='198' textAnchor='middle' fill='var(--cds-text-secondary)'>{t > 0 ? `+${t}` : `${t}`}</text></g>)}"
            "{rows.map((r, i) => <g key={r.crowd} {...datum(r)}><text x={left - 10} y={y0 + i * 50 + 4} textAnchor='end' fill='var(--cds-text-primary)'>{r.crowd}</text>"
            "<line x1={x(r.lo)} x2={x(r.hi)} y1={y0 + i * 50} y2={y0 + i * 50} stroke='var(--cds-text-secondary)' strokeWidth='2'/>"
            "<circle cx={x(r.est)} cy={y0 + i * 50} r='6' fill='var(--cds-chart-categorical-1)' {...datum(r, 'est')}><title>{`${r.crowd}: ${r.est > 0 ? '+' : ''}${r.est} points per 100 words [${r.lo}, ${r.hi}]`}</title></circle>"
            "<text x={x(r.est)} y={y0 + i * 50 - 12} textAnchor='middle' fill='var(--cds-text-primary)'>{`${r.est > 0 ? '+' : ''}${r.est.toFixed(1)}`}</text></g>)}"
            "</svg>; }}</claude.Visualize>;")


if __name__ == "__main__":
    print(json.dumps({"rounds": rounds_chart(), "rates": rates_chart(), "length": length_chart()}))
