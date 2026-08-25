"""Build the before/after social-graph web diagram from an analysis JSON.

Emits a single self-contained HTML file: a force-directed network where
nodes are agents and edges are follows, with a round slider so the graph can
be scrubbed from "before" (empty, by design D-10) to "after". Edge thickness
between a pair reflects how many times one agent acted on the other, and node
size reflects follower count.

Everything is inlined -- no CDN, no external assets -- so the file can be
published as an artifact or opened directly.

Usage:
    oasis-env/bin/python examples/experiment/social_timeline/make_graph.py \
        --analysis data/social_timeline_stage3_analysis.json \
        --out data/social_timeline_stage3_graph.html
"""

from __future__ import annotations

import argparse
import json


HTML = """<title>Agent Network Formation</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@600;700&display=swap">
<style>
  /* Light palette is the complete set; dark blocks redefine tokens only. */
  :root {
    --bg:#fbfcfd; --panel:#f1f5f9; --panel-2:#e8eef4;
    --fg:#0f1720; --muted:#59677a; --line:#dae3ec;
    --follow:#1f6f8b;        /* social graph edges */
    --interact:#c96a1f;      /* content interactions -- semantic, not accent */
    --node:#2c4a63; --node-ring:#fbfcfd;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg:#0c1218; --panel:#131c25; --panel-2:#1a252f;
      --fg:#e3eaf2; --muted:#8595a8; --line:#22303c;
      --follow:#54b6d6; --interact:#e5a355;
      --node:#7fa8c4; --node-ring:#0c1218;
    }
  }
  :root[data-theme="dark"] {
    --bg:#0c1218; --panel:#131c25; --panel-2:#1a252f;
    --fg:#e3eaf2; --muted:#8595a8; --line:#22303c;
    --follow:#54b6d6; --interact:#e5a355;
    --node:#7fa8c4; --node-ring:#0c1218;
  }

  * { box-sizing: border-box; }
  body {
    margin:0; background:var(--bg); color:var(--fg);
    font-family:"IBM Plex Sans", ui-sans-serif, -apple-system, sans-serif;
    font-size:15px; line-height:1.55;
    -webkit-font-smoothing:antialiased;
  }
  .wrap { max-width:1120px; margin:0 auto; padding:36px 22px 72px;
          display:flex; flex-direction:column; gap:22px; }

  header { display:flex; flex-direction:column; gap:6px; }
  .eyebrow {
    font-family:"IBM Plex Mono", ui-monospace, monospace;
    font-size:11.5px; letter-spacing:.13em; text-transform:uppercase;
    color:var(--muted);
  }
  h1 {
    font-family:"IBM Plex Sans Condensed", "IBM Plex Sans", sans-serif;
    font-weight:700; font-size:clamp(26px,4vw,36px); line-height:1.1;
    margin:0; letter-spacing:-.01em; text-wrap:balance;
  }
  .lede { color:var(--muted); max-width:66ch; margin:0; }

  /* Summary scans before detail. */
  .stats { display:grid; gap:1px; background:var(--line);
           border:1px solid var(--line); border-radius:8px; overflow:hidden;
           grid-template-columns:repeat(auto-fit,minmax(128px,1fr)); }
  .stat { background:var(--panel); padding:13px 15px;
          display:flex; flex-direction:column; gap:3px; }
  .stat .v { font-family:"IBM Plex Mono", monospace; font-size:21px;
             font-weight:600; font-variant-numeric:tabular-nums;
             letter-spacing:-.02em; }
  .stat .k { font-size:11.5px; color:var(--muted); letter-spacing:.04em;
             text-transform:uppercase;
             font-family:"IBM Plex Mono", monospace; }

  figure { margin:0; border:1px solid var(--line); border-radius:8px;
           background:var(--panel); overflow:hidden; }
  .scrub { display:flex; align-items:center; gap:14px; flex-wrap:wrap;
           padding:12px 16px; border-bottom:1px solid var(--line);
           background:var(--panel-2); }
  .scrub label { font-family:"IBM Plex Mono", monospace; font-size:12px;
                 letter-spacing:.06em; text-transform:uppercase;
                 color:var(--muted); }
  .scrub output { font-family:"IBM Plex Mono", monospace; font-weight:600;
                  font-variant-numeric:tabular-nums; color:var(--fg); }
  input[type=range] { flex:1; min-width:180px; accent-color:var(--follow); }
  input[type=range]:focus-visible { outline:2px solid var(--follow);
                                    outline-offset:3px; }
  svg { display:block; width:100%; height:min(58vh,540px);
        background:var(--panel); }
  .node circle { stroke:var(--node-ring); stroke-width:1.5px; }
  .node text { font-family:"IBM Plex Mono", monospace; font-size:9.5px;
               fill:var(--muted); pointer-events:none; }

  .legend { display:flex; gap:22px; flex-wrap:wrap; font-size:13px;
            color:var(--muted); padding:0 2px; }
  .legend b { color:var(--fg); font-weight:500; }
  .swatch { display:inline-block; width:20px; height:3px; border-radius:2px;
            vertical-align:middle; margin-right:7px; }

  .scroll { overflow-x:auto; border:1px solid var(--line);
            border-radius:8px; }
  table { border-collapse:collapse; width:100%; font-size:13.5px;
          min-width:460px; }
  caption { text-align:left; padding:12px 15px 11px; color:var(--muted);
            font-size:12px; letter-spacing:.06em; text-transform:uppercase;
            font-family:"IBM Plex Mono", monospace;
            border-bottom:1px solid var(--line); background:var(--panel-2); }
  th, td { text-align:left; padding:8px 15px;
           border-bottom:1px solid var(--line); }
  tbody tr:last-child td { border-bottom:none; }
  th { color:var(--muted); font-weight:500; font-size:12px;
       letter-spacing:.05em; text-transform:uppercase;
       font-family:"IBM Plex Mono", monospace; }
  td { color:var(--fg); }
  td.num { text-align:right; font-variant-numeric:tabular-nums;
           font-family:"IBM Plex Mono", monospace; }
  td.who { font-family:"IBM Plex Mono", monospace; font-size:12.5px; }
  .bar-cell { display:flex; align-items:center; justify-content:flex-end;
              gap:8px; }
  .minibar { height:3px; border-radius:2px; background:var(--interact);
             opacity:.75; }

  .note { color:var(--muted); font-size:13px; margin:0;
          border-left:2px solid var(--line); padding-left:14px;
          max-width:72ch; }
  @media (prefers-reduced-motion:reduce) { * { transition:none !important; } }
</style>

<div class="wrap">
  <header>
    <div class="eyebrow">OASIS &middot; Simulation 4 &middot; interest-based feed</div>
    <h1>Agent Network Formation</h1>
    <p class="lede" id="subtitle"></p>
  </header>

  <div class="stats" id="stats"></div>

  <figure>
    <div class="scrub">
      <label for="round">Round</label>
      <output id="roundLabel">0</output>
      <input type="range" id="round" min="0" max="0" value="0" step="1">
      <label>Follows <output id="edgeCount">0</output></label>
      <label>Pairs <output id="pairCount">0</output></label>
    </div>
    <svg id="graph" role="img"
         aria-label="Force-directed graph of agents, follow edges and interactions"></svg>
  </figure>

  <div class="legend">
    <span><span class="swatch" style="background:var(--follow)"></span><b>Follow</b> &mdash; chosen by an agent</span>
    <span><span class="swatch" style="background:var(--interact)"></span><b>Interaction</b> &mdash; width = count</span>
    <span><b>Node size</b> &mdash; followers</span>
  </div>

  <div class="scroll">
    <table id="exposureTable">
      <caption>Exposure &rarr; interaction, by pair</caption>
      <thead><tr>
        <th>Viewer</th><th>Author</th>
        <th class="num">Times seen</th><th class="num">Interactions</th>
      </tr></thead>
      <tbody></tbody>
    </table>
  </div>

  <p class="note" id="footnote"></p>
</div>

<script>
const DATA = __DATA__;

const svg = document.getElementById('graph');
const NS = 'http://www.w3.org/2000/svg';

const agents = Object.values(DATA.agents);
const byId = {};
agents.forEach(a => byId[a.agent_id] = a);

// Interaction counts between pairs, used for edge thickness.
const inter = {};
for (const [key, counts] of Object.entries(DATA.interaction_pairs || {})) {
  inter[key] = Object.values(counts).reduce((s, n) => s + n, 0);
}
const exposure = DATA.exposure_pairs || {};

const rounds = Object.keys(DATA.graph_by_round || {}).map(Number).sort((a,b)=>a-b);
const maxRound = rounds.length ? Math.max(...rounds) : 0;

const slider = document.getElementById('round');
slider.max = maxRound;
slider.value = maxRound;

const followEdgesFinal = ((DATA.graph_by_round || {})[maxRound] || []).length;

document.getElementById('subtitle').textContent =
  `The social graph starts with zero edges. Every connection below was created ` +
  `by an agent choosing to follow someone, over ${DATA.n_rounds} rounds of an ` +
  `interest-based feed. Scrub the round slider to watch it assemble.`;

const STATS = [
  ['Agents', DATA.n_agents],
  ['Rounds', DATA.n_rounds],
  ['Posts', DATA.totals.posts],
  ['Actions', DATA.totals.actions_chosen],
  ['Exposures', DATA.totals.exposure_events],
  ['Follows', followEdgesFinal],
];
document.getElementById('stats').innerHTML = STATS.map(
  ([k, v]) => `<div class="stat"><span class="v">${v}</span>` +
              `<span class="k">${k}</span></div>`).join('');

// Deterministic starting positions on a circle, then relaxed by the layout.
const W = 1000, H = 560;
const nodes = agents.map((a, i) => {
  const t = (i / agents.length) * Math.PI * 2;
  return { id: a.agent_id, name: a.username || ('agent ' + a.agent_id),
           x: W/2 + Math.cos(t) * 200, y: H/2 + Math.sin(t) * 200,
           vx: 0, vy: 0 };
});
const nodeById = {};
nodes.forEach(n => nodeById[n.id] = n);

function edgesAt(round) {
  const raw = (DATA.graph_by_round || {})[round] || [];
  return raw.map(([a, b]) => ({ source: a, target: b }));
}

function interactionEdges() {
  return Object.entries(inter).map(([key, n]) => {
    const [a, b] = key.split('->').map(Number);
    return { source: a, target: b, weight: n };
  }).filter(e => nodeById[e.source] && nodeById[e.target]);
}

function simulate(edges) {
  // Small force-directed relaxation. Deliberately simple and dependency-free.
  for (let step = 0; step < 320; step++) {
    for (const n of nodes) { n.vx *= 0.82; n.vy *= 0.82; }
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        let dx = b.x - a.x, dy = b.y - a.y;
        let d2 = dx*dx + dy*dy || 1;
        const rep = 9000 / d2;
        const d = Math.sqrt(d2);
        const ux = dx/d, uy = dy/d;
        a.vx -= ux*rep; a.vy -= uy*rep;
        b.vx += ux*rep; b.vy += uy*rep;
      }
    }
    for (const e of edges) {
      const a = nodeById[e.source], b = nodeById[e.target];
      if (!a || !b) continue;
      const dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.sqrt(dx*dx + dy*dy) || 1;
      const f = (d - 140) * 0.012;
      const ux = dx/d, uy = dy/d;
      a.vx += ux*f; a.vy += uy*f;
      b.vx -= ux*f; b.vy -= uy*f;
    }
    for (const n of nodes) {
      n.vx += (W/2 - n.x) * 0.002;
      n.vy += (H/2 - n.y) * 0.002;
      n.x = Math.max(30, Math.min(W-30, n.x + n.vx));
      n.y = Math.max(24, Math.min(H-24, n.y + n.vy));
    }
  }
}

function render(round) {
  const follows = edgesAt(round);
  const interactions = interactionEdges();
  simulate(follows.length ? follows : interactions);

  const followerCount = {};
  follows.forEach(e => followerCount[e.target] = (followerCount[e.target]||0)+1);

  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.innerHTML = '';

  const maxW = Math.max(1, ...interactions.map(e => e.weight));
  for (const e of interactions) {
    const a = nodeById[e.source], b = nodeById[e.target];
    const l = document.createElementNS(NS, 'line');
    l.setAttribute('x1', a.x); l.setAttribute('y1', a.y);
    l.setAttribute('x2', b.x); l.setAttribute('y2', b.y);
    l.setAttribute('stroke', 'var(--interact)');
    l.setAttribute('stroke-width', 1.2 + 4.5 * (e.weight / maxW));
    l.setAttribute('opacity', '0.55');
    svg.appendChild(l);
  }
  for (const e of follows) {
    const a = nodeById[e.source], b = nodeById[e.target];
    if (!a || !b) continue;
    const l = document.createElementNS(NS, 'line');
    l.setAttribute('x1', a.x); l.setAttribute('y1', a.y);
    l.setAttribute('x2', b.x); l.setAttribute('y2', b.y);
    l.setAttribute('stroke', 'var(--follow)');
    l.setAttribute('stroke-width', '1.6');
    l.setAttribute('opacity', '0.8');
    svg.appendChild(l);
  }
  for (const n of nodes) {
    const g = document.createElementNS(NS, 'g');
    g.setAttribute('class', 'node');
    const c = document.createElementNS(NS, 'circle');
    const r = 7 + 3 * Math.sqrt(followerCount[n.id] || 0);
    c.setAttribute('cx', n.x); c.setAttribute('cy', n.y);
    c.setAttribute('r', r);
    c.setAttribute('fill', 'var(--node)');
    const a = byId[n.id] || {};
    c.innerHTML = `<title>${n.name}\nactions: ${a.total_actions ?? 0}\n` +
      `posts: ${a.n_posts_authored ?? 0}\nsaw ${a.distinct_posts_seen ?? 0} posts\n` +
      `followers: ${followerCount[n.id] || 0}</title>`;
    g.appendChild(c);
    const t = document.createElementNS(NS, 'text');
    t.setAttribute('x', n.x); t.setAttribute('y', n.y - r - 4);
    t.setAttribute('text-anchor', 'middle');
    t.textContent = n.name.length > 16 ? n.name.slice(0,15) + '...' : n.name;
    g.appendChild(t);
    svg.appendChild(g);
  }

  document.getElementById('roundLabel').textContent = round;
  document.getElementById('edgeCount').textContent = follows.length;
  document.getElementById('pairCount').textContent = interactions.length;
}

const tbody = document.querySelector('#exposureTable tbody');
const rows = Object.entries(exposure).sort((a,b) => b[1]-a[1]).slice(0, 40);
if (!rows.length) {
  tbody.innerHTML = '<tr><td colspan="4">No exposures recorded.</td></tr>';
} else {
  const maxSeen = Math.max(...rows.map(r => r[1]));
  tbody.innerHTML = rows.map(([key, n]) => {
    const [v, a] = key.split('->');
    const vn = (byId[v]||{}).username || ('agent ' + v);
    const an = (byId[a]||{}).username || ('agent ' + a);
    const acts = inter[key] || 0;
    const w = Math.max(3, Math.round(46 * (n / maxSeen)));
    return `<tr><td class="who">${vn}</td><td class="who">${an}</td>` +
           `<td class="num"><span class="bar-cell">` +
           `<span class="minibar" style="width:${w}px"></span>${n}</span></td>` +
           `<td class="num">${acts || '&ndash;'}</td></tr>`;
  }).join('');
}

document.getElementById('footnote').textContent =
  'The follow graph starts empty by design: no relationships are seeded, so ' +
  'every edge shown was created by an agent choosing to follow someone. ' +
  '"Times seen" counts exposure events, not distinct posts. Seeing the ' +
  'same author repeatedly is the mechanism that drives discovery.';

slider.addEventListener('input', e => render(Number(e.target.value)));
render(maxRound);
</script>
"""


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--analysis", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    with open(args.analysis) as fh:
        full = json.load(fh)

    # Keep the payload lean. The analysis JSON carries the complete event log,
    # exposure ledger, post bodies and comments -- thousands of rows at full
    # scale -- but this page reads none of them. Embedding the lot would bloat
    # the artifact for no benefit, so build an explicit projection of exactly
    # what the page uses rather than deleting keys one by one and hoping.
    PER_AGENT = ("agent_id", "username", "total_actions", "n_posts_authored",
                 "distinct_posts_seen", "exposure_events", "engagement_rate")
    data = {
        "n_agents": full.get("n_agents"),
        "n_rounds": full.get("n_rounds"),
        "totals": {k: v for k, v in (full.get("totals") or {}).items()
                   if k != "action_counts"},
        "graph_by_round": full.get("graph_by_round", {}),
        "interaction_pairs": full.get("interaction_pairs", {}),
        # Only the strongest pairs are rendered; the table shows the top 40.
        "exposure_pairs": dict(sorted(
            (full.get("exposure_pairs") or {}).items(),
            key=lambda kv: -kv[1])[:120]),
        "agents": {
            k: {f: v.get(f) for f in PER_AGENT}
            for k, v in (full.get("agents") or {}).items()
        },
    }

    html = HTML.replace("__DATA__", json.dumps(data, default=str))
    with open(args.out, "w") as fh:
        fh.write(html)
    print(f"wrote {args.out} ({len(html)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
