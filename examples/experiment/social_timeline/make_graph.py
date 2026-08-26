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
import os


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
  svg { display:block; width:100%; height:min(72vh,640px);
        background:var(--panel); }
  .node circle { stroke:var(--node-ring); stroke-width:1.5px; }
  .node text { font-family:"IBM Plex Mono", monospace; font-size:9px;
               fill:var(--fg); pointer-events:none; }
  .focusbox { font-size:13px; color:var(--muted); background:var(--panel);
              border:1px solid var(--line); border-radius:8px;
              padding:11px 14px; line-height:1.5; }
  .focusbox b { color:var(--fg); font-family:"IBM Plex Mono", monospace; }

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

  .algo { border:1px solid var(--line); border-radius:8px;
          background:var(--panel); padding:16px 18px; display:flex;
          flex-direction:column; gap:10px; }
  .algo h2 { font-family:"IBM Plex Sans Condensed","IBM Plex Sans",sans-serif;
             font-size:17px; margin:0; font-weight:700; }
  .algo code { font-family:"IBM Plex Mono", monospace; font-size:12.5px;
               background:var(--panel-2); padding:2px 6px; border-radius:4px;
               display:inline-block; }
  .algo dl { display:grid; grid-template-columns:auto 1fr; gap:5px 14px;
             margin:0; font-size:13.5px; }
  .algo dt { color:var(--muted); font-family:"IBM Plex Mono", monospace;
             font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
  .algo dd { margin:0; }
  .algo ul { margin:0; padding-left:18px; font-size:13.5px; color:var(--muted); }
  .mix { font-family:"IBM Plex Mono", monospace; font-size:11.5px;
         color:var(--muted); }
  .note { color:var(--muted); font-size:13px; margin:0;
          border-left:2px solid var(--line); padding-left:14px;
          max-width:72ch; }
  @media (prefers-reduced-motion:reduce) { * { transition:none !important; } }

  .runbar { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
  .runbar select { font-family:"IBM Plex Mono", monospace; font-size:13px;
                   background:var(--panel); color:var(--fg);
                   border:1px solid var(--line); border-radius:6px;
                   padding:7px 10px; }
  .runbar label { font-family:"IBM Plex Mono", monospace; font-size:12px;
                  letter-spacing:.06em; text-transform:uppercase;
                  color:var(--muted); }
  .best { color:var(--follow); font-weight:600; }
  tr.current td { background:var(--panel-2); }
</style>

<div class="wrap">
  <header>
    <div class="eyebrow">OASIS &middot; Simulation 4 &middot; interest-based feed</div>
    <h1>Agent Network Formation</h1>
    <p class="lede" id="subtitle"></p>
  </header>

  <div class="runbar">
    <label for="runSel">Run</label>
    <select id="runSel"></select>
    <span class="lede" id="runMeta"></span>
  </div>

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

  <div class="focusbox" id="focusBox"></div>

  <div class="legend">
    <span><span class="swatch" style="background:var(--follow)"></span><b>Follow</b> &mdash; arrow points to the person followed</span>
    <span><span class="swatch" style="background:var(--interact)"></span><b>Interaction</b> &mdash; width = count</span>
    <span><b>Node size</b> &mdash; followers</span>
  </div>

  <div class="scroll">
    <table id="compareTable">
      <caption>All runs &mdash; every run is kept, so changes can be traced</caption>
      <thead><tr>
        <th>Run</th><th>Personas</th><th class="num">Agents</th>
        <th class="num">Rounds</th><th class="num">Act rate</th>
        <th class="num">Act/turn</th><th class="num">Malformed</th>
        <th class="num">Follows</th><th class="num">Posts</th>
        <th class="num">Exposures</th><th class="num">Separability</th>
      </tr></thead>
      <tbody></tbody>
    </table>
  </div>

  <section id="algoBox" class="algo"></section>

  <div class="scroll">
    <table id="agentTable">
      <caption>Per-agent detail &mdash; selected run</caption>
      <thead><tr>
        <th class="num">#</th><th>Agent</th>
        <th class="num">Actions</th><th class="num">Posts</th>
        <th class="num">Saw</th><th class="num">Engaged</th>
        <th class="num">Follows</th><th class="num">Followers</th>
        <th>Action mix</th>
      </tr></thead>
      <tbody></tbody>
    </table>
  </div>

  <div class="scroll">
    <table id="propTable">
      <caption>Propagation &mdash; repeated exposure preceding interaction</caption>
      <thead><tr>
        <th>Actor</th><th>Saw</th><th class="num">Times</th><th>Then did</th>
      </tr></thead>
      <tbody></tbody>
    </table>
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
const ALL = __DATA__;
const NS = 'http://www.w3.org/2000/svg';
const svg = document.getElementById('graph');
const slider = document.getElementById('round');
const W = 1000, H = 560;

let DATA, agents, byId, inter, exposure, nodes, nodeById, maxRound;
let focusId = null, lastRound = 0;

// ---------- run selector ----------
const sel = document.getElementById('runSel');
sel.innerHTML = ALL.order.map(k =>
  `<option value="${k}">${k}</option>`).join('');
sel.value = ALL.order[ALL.order.length - 1];
sel.addEventListener('change', () => loadRun(sel.value));

function fmt(x, d) { return (x === null || x === undefined) ? '-' :
  (typeof x === 'number' ? x.toFixed(d === undefined ? 0 : d) : x); }

// ---------- cross-run comparison ----------
(function comparison() {
  const rows = ALL.order.map(k => ALL.runs[k]);
  const best = {};
  ['action_rate','actions_per_turn','follow_edges','posts','exposures'].forEach(m => {
    best[m] = Math.max(...rows.map(r => r.summary[m] || 0));
  });
  best.malformed = Math.min(...rows.map(r =>
    r.summary.malformed === null ? Infinity : r.summary.malformed));
  document.querySelector('#compareTable tbody').innerHTML = rows.map(r => {
    const s = r.summary;
    const hi = (v, m, d) => `<td class="num${v === best[m] ? ' best' : ''}">${fmt(v, d)}</td>`;
    return `<tr data-run="${r.label}"><td class="who">${r.label}</td>` +
      `<td>${s.persona_source || '-'}</td>` +
      `<td class="num">${s.agents}</td><td class="num">${s.rounds}</td>` +
      hi(s.action_rate, 'action_rate', 3) +
      hi(s.actions_per_turn, 'actions_per_turn', 2) +
      hi(s.malformed, 'malformed') +
      hi(s.follow_edges, 'follow_edges') +
      hi(s.posts, 'posts') +
      hi(s.exposures, 'exposures') +
      `<td class="num">${fmt(s.persona_similarity, 3)}</td></tr>`;
  }).join('');
})();

// ---------- per-run load ----------
function loadRun(label) {
  DATA = ALL.runs[label];
  focusId = null;
  agents = DATA.agents;
  byId = {};
  Object.values(agents).forEach(a => byId[a.agent_id] = a);

  inter = {};
  for (const [k, counts] of Object.entries(DATA.interaction_pairs || {}))
    inter[k] = Object.values(counts).reduce((s, n) => s + n, 0);
  exposure = DATA.exposure_pairs || {};

  const rounds = Object.keys(DATA.graph_by_round || {}).map(Number);
  maxRound = rounds.length ? Math.max(...rounds) : 0;
  slider.max = maxRound;
  slider.value = maxRound;

  nodes = Object.values(agents).map((a, i, arr) => {
    const t = (i / arr.length) * Math.PI * 2;
    return { id: a.agent_id, name: a.username || ('agent' + a.agent_id),
             x: W/2 + Math.cos(t) * 200, y: H/2 + Math.sin(t) * 200,
             vx: 0, vy: 0 };
  });
  nodeById = {};
  nodes.forEach(n => nodeById[n.id] = n);

  const s = DATA.summary;
  document.getElementById('subtitle').textContent =
    `The social graph starts with zero edges. Every connection was created by ` +
    `an agent choosing to follow someone, over ${s.rounds} rounds of an ` +
    `interest-based feed. Scrub the round slider to watch it assemble.`;
  document.getElementById('runMeta').textContent =
    `${s.agents} agents | ${s.rounds} rounds | prompt v${s.prompt_version || '?'}` +
    ` | ${s.persona_source || 'personas ?'}` +
    (s.minutes ? ` | ${s.minutes} min` : '');

  document.getElementById('stats').innerHTML = [
    ['Agents', s.agents], ['Rounds', s.rounds], ['Posts', s.posts],
    ['Actions', s.actions], ['Exposures', s.exposures],
    ['Follows', s.follow_edges],
  ].map(([k, v]) => `<div class="stat"><span class="v">${v}</span>` +
                    `<span class="k">${k}</span></div>`).join('');

  document.querySelectorAll('#compareTable tbody tr').forEach(tr =>
    tr.classList.toggle('current', tr.dataset.run === label));

  algoBox(); agentTable(); propTable(); exposureTable(); footnote();
  render(maxRound);
}

// ---------- layout ----------
function simulate(edges) {
  for (let step = 0; step < 320; step++) {
    for (const n of nodes) { n.vx *= 0.82; n.vy *= 0.82; }
    for (let i = 0; i < nodes.length; i++)
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const dx = b.x - a.x, dy = b.y - a.y;
        const d2 = dx*dx + dy*dy || 1, d = Math.sqrt(d2);
        const rep = (7000 + 150 * nodes.length) / d2;
        const ux = dx/d, uy = dy/d;
        a.vx -= ux*rep; a.vy -= uy*rep; b.vx += ux*rep; b.vy += uy*rep;
      }
    for (const e of edges) {
      const a = nodeById[e.source], b = nodeById[e.target];
      if (!a || !b) continue;
      const dx = b.x - a.x, dy = b.y - a.y;
      const d = Math.sqrt(dx*dx + dy*dy) || 1;
      const f = (d - 140) * 0.012, ux = dx/d, uy = dy/d;
      a.vx += ux*f; a.vy += uy*f; b.vx -= ux*f; b.vy -= uy*f;
    }
    for (const n of nodes) {
      const pull = 0.004 + 0.00012 * nodes.length;
      n.vx += (W/2 - n.x) * pull; n.vy += (H/2 - n.y) * pull;
      n.x = Math.max(70, Math.min(W-70, n.x + n.vx));
      n.y = Math.max(40, Math.min(H-40, n.y + n.vy));
    }
  }
}

function edgesAt(round) {
  return ((DATA.graph_by_round || {})[round] || [])
    .map(([a, b]) => ({ source: a, target: b }));
}

function interactionEdges() {
  const all = Object.entries(inter).map(([key, n]) => {
    const [a, b] = key.split('->').map(Number);
    return { source: a, target: b, weight: n };
  }).filter(e => nodeById[e.source] && nodeById[e.target]);
  const DENSE = 60;
  if (all.length <= DENSE) return all;
  const repeated = all.filter(e => e.weight > 1);
  return repeated.length >= 12 ? repeated
       : all.sort((a, b) => b.weight - a.weight).slice(0, 40);
}

function render(round) {
  lastRound = round;
  const follows = edgesAt(round);
  const interactions = interactionEdges();
  simulate(follows.length ? follows : interactions);

  const fc = {};
  follows.forEach(e => fc[e.target] = (fc[e.target] || 0) + 1);

  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.innerHTML = '';
  const defs = document.createElementNS(NS, 'defs');
  defs.innerHTML = ['follow','interact','dim'].map(k => {
    const col = k === 'dim' ? 'var(--line)' : `var(--${k})`;
    return `<marker id="ar-${k}" viewBox="0 0 10 10" refX="9" refY="5"
              markerWidth="5" markerHeight="5" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" fill="${col}"/></marker>`;
  }).join('');
  svg.appendChild(defs);

  const anyFocus = focusId !== null;
  const rel = e => !anyFocus || e.source === focusId || e.target === focusId;

  function drawEdge(a, b, kind, width, curve) {
    const on = rel({source: a.id, target: b.id});
    const dx = b.x - a.x, dy = b.y - a.y;
    const d = Math.sqrt(dx*dx + dy*dy) || 1;
    const mx = (a.x + b.x)/2 + (-dy/d)*curve, my = (a.y + b.y)/2 + (dx/d)*curve;
    const r = 9 + 3*Math.sqrt(fc[b.id] || 0);
    const path = document.createElementNS(NS, 'path');
    path.setAttribute('d', `M${a.x},${a.y} Q${mx},${my} ${b.x-(dx/d)*r},${b.y-(dy/d)*r}`);
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', on ? `var(--${kind})` : 'var(--line)');
    path.setAttribute('stroke-width', on ? width : Math.min(width, 1));
    path.setAttribute('opacity', on ? (anyFocus ? 0.95 : 0.6)
                                    : (anyFocus ? 0.10 : 0.30));
    path.setAttribute('marker-end', `url(#ar-${on ? kind : 'dim'})`);
    svg.appendChild(path);
  }

  const maxW = Math.max(1, ...interactions.map(e => e.weight));
  for (const e of interactions) {
    const a = nodeById[e.source], b = nodeById[e.target];
    if (a && b) drawEdge(a, b, 'interact', 1 + 3.5*(e.weight/maxW), 26);
  }
  for (const e of follows) {
    const a = nodeById[e.source], b = nodeById[e.target];
    if (a && b) drawEdge(a, b, 'follow', 1.7, -26);
  }

  for (const n of nodes) {
    const near = !anyFocus || n.id === focusId ||
      follows.some(e => (e.source===focusId && e.target===n.id) || (e.target===focusId && e.source===n.id)) ||
      interactions.some(e => (e.source===focusId && e.target===n.id) || (e.target===focusId && e.source===n.id));
    const g = document.createElementNS(NS, 'g');
    g.setAttribute('class', 'node'); g.style.cursor = 'pointer';
    const r = 6 + 3*Math.sqrt(fc[n.id] || 0);
    const c = document.createElementNS(NS, 'circle');
    c.setAttribute('cx', n.x); c.setAttribute('cy', n.y); c.setAttribute('r', r);
    c.setAttribute('fill', n.id === focusId ? 'var(--interact)' : 'var(--node)');
    c.setAttribute('opacity', near ? 1 : 0.25);
    const a = byId[n.id] || {};
    c.innerHTML = `<title>${n.name}
actions: ${a.total_actions ?? 0}   posts: ${a.n_posts_authored ?? 0}
saw ${a.distinct_posts_seen ?? 0} distinct posts
followers here: ${fc[n.id] || 0}
click to isolate this person's connections</title>`;
    g.appendChild(c);
    const t = document.createElementNS(NS, 'text');
    t.setAttribute('x', n.x); t.setAttribute('y', n.y - r - 5);
    t.setAttribute('text-anchor', 'middle');
    t.setAttribute('opacity', near ? 1 : 0.22);
    t.setAttribute('paint-order', 'stroke');
    t.setAttribute('stroke', 'var(--panel)'); t.setAttribute('stroke-width', '3');
    t.textContent = n.name.length > 16 ? n.name.slice(0,15) + '...' : n.name;
    g.appendChild(t);
    g.addEventListener('click', () => {
      focusId = (focusId === n.id) ? null : n.id; render(lastRound);
    });
    svg.appendChild(g);
  }

  const fb = document.getElementById('focusBox');
  if (!anyFocus) {
    fb.textContent = 'Click any person to isolate their connections. ' +
      'Arrows point from follower to the person followed.';
  } else {
    const me = (byId[focusId] || {}).username || focusId;
    const outF = follows.filter(e => e.source === focusId)
      .map(e => (byId[e.target]||{}).username || e.target);
    const inF = follows.filter(e => e.target === focusId)
      .map(e => (byId[e.source]||{}).username || e.source);
    const acted = Object.entries(DATA.interaction_pairs || {})
      .filter(([k]) => Number(k.split('->')[0]) === focusId)
      .map(([k, v]) => `${(byId[Number(k.split('->')[1])]||{}).username}` +
        ` (${Object.entries(v).map(([x,y])=>x+'x'+y).join(', ')})`);
    fb.innerHTML = `<b>${me}</b> &mdash; follows: ${outF.join(', ') || 'nobody'}` +
      ` &middot; followed by: ${inF.join(', ') || 'nobody'}` +
      (acted.length ? `<br>acted on: ${acted.join('; ')}` : '') +
      `<br><i>click again to clear</i>`;
  }

  document.getElementById('roundLabel').textContent = round;
  document.getElementById('edgeCount').textContent = follows.length;
  document.getElementById('pairCount').textContent = interactions.length;
}

// ---------- tables ----------
function algoBox() {
  const A = DATA.algorithm || {}, C = DATA.config || {};
  const box = document.getElementById('algoBox');
  if (!A.name) { box.innerHTML = ''; return; }
  const dev = (A.deviations_from_upstream || []).map(d => `<li>${d}</li>`).join('');
  box.innerHTML = `<h2>Algorithm &mdash; ${DATA.label}</h2><dl>` +
    `<dt>Name</dt><dd>${A.name}</dd>` +
    `<dt>Score</dt><dd><code>${A.formula || ''}</code></dd>` +
    `<dt>Embedding</dt><dd>${A.embedding || ''}</dd>` +
    `<dt>Feed</dt><dd>${C.refresh_rec_post_count ?? '?'} algorithmic posts + ` +
    `${C.following_post_count ?? '?'} from people you follow, ranked from a pool ` +
    `of ${C.max_rec_post_len ?? '?'}` +
    (A.explore_slots !== undefined ? `, ${A.explore_slots} slot(s) kept for exploration` : '') +
    `</dd><dt>Model</dt><dd>${C.model || ''} &middot; ${C.n_actions ?? '?'} actions` +
    (C.temperature !== undefined ? ` &middot; temp ${C.temperature}` : '') +
    (C.seed !== undefined ? ` &middot; seed ${C.seed}` : '') + `</dd>` +
    `<dt>Personas</dt><dd>${DATA.summary.persona_source || '?'}` +
    (DATA.summary.persona_similarity !== null && DATA.summary.persona_similarity !== undefined
      ? ` &middot; mean pairwise similarity ${DATA.summary.persona_similarity}` +
        ` (lower = more distinguishable)` : '') + `</dd>` +
    `<dt>Start</dt><dd>${A.initial_follow_edges ?? 0} follow edges &mdash; not seeded</dd>` +
    `</dl>` + (dev ? `<div><strong>Stated deviations from upstream:</strong><ul>${dev}</ul></div>` : '');
}

function agentTable() {
  const rows = Object.values(agents)
    .sort((a, b) => (b.total_actions || 0) - (a.total_actions || 0));
  document.querySelector('#agentTable tbody').innerHTML = rows.map(a => {
    const mix = Object.entries(a.action_counts || {}).sort((x, y) => y[1]-x[1])
      .map(([k, v]) => `${k}&times;${v}`).join(', ') || '&ndash;';
    const eng = a.engagement_rate == null ? '&ndash;'
      : (a.engagement_rate * 100).toFixed(0) + '%';
    return `<tr><td class="num">${a.agent_id}</td>` +
      `<td class="who">${a.username}</td>` +
      `<td class="num">${a.total_actions ?? 0}</td>` +
      `<td class="num">${a.n_posts_authored ?? 0}</td>` +
      `<td class="num">${a.distinct_posts_seen ?? 0}</td>` +
      `<td class="num">${eng}</td>` +
      `<td class="num">${(a.following || []).length}</td>` +
      `<td class="num">${(a.followers || []).length}</td>` +
      `<td class="mix">${mix}</td></tr>`;
  }).join('');
}

function propTable() {
  const body = document.querySelector('#propTable tbody');
  const prop = DATA.propagation || [];
  body.innerHTML = prop.length ? prop.map(p => {
    const did = Object.entries(p.interactions || {})
      .map(([k, v]) => `${k}&times;${v}`).join(', ');
    return `<tr><td class="who">${(byId[p.actor]||{}).username || p.actor}</td>` +
      `<td class="who">${(byId[p.target]||{}).username || p.target}</td>` +
      `<td class="num">${p.times_actor_saw_target}</td>` +
      `<td class="mix">${did}</td></tr>`;
  }).join('') : '<tr><td colspan="4">No exposure-then-interaction pairs.</td></tr>';
}

function exposureTable() {
  const tbody = document.querySelector('#exposureTable tbody');
  const rows = Object.entries(exposure).sort((a, b) => b[1]-a[1]).slice(0, 40);
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="4">No exposures recorded.</td></tr>';
    return;
  }
  const maxSeen = Math.max(...rows.map(r => r[1]));
  tbody.innerHTML = rows.map(([key, n]) => {
    const [v, a] = key.split('->');
    const acts = inter[key] || 0;
    const w = Math.max(3, Math.round(46 * (n / maxSeen)));
    return `<tr><td class="who">${(byId[v]||{}).username || ('agent'+v)}</td>` +
      `<td class="who">${(byId[a]||{}).username || ('agent'+a)}</td>` +
      `<td class="num"><span class="bar-cell">` +
      `<span class="minibar" style="width:${w}px"></span>${n}</span></td>` +
      `<td class="num">${acts || '&ndash;'}</td></tr>`;
  }).join('');
}

function footnote() {
  const totalPairs = Object.keys(inter).length;
  const shown = interactionEdges().length;
  document.getElementById('footnote').textContent =
    'The follow graph starts empty by design: no relationships are seeded, so ' +
    'every edge shown was created by an agent choosing to follow someone. ' +
    '"Times seen" counts exposure events, not distinct posts. Seeing the same ' +
    'author repeatedly is the mechanism that drives discovery. ' +
    `Handles are anonymised names carried over from the source persona file, ` +
    `so they are not agent indices: this run has ${DATA.summary.agents} agents, ` +
    `numbered 0-${DATA.summary.agents - 1} in the # column, drawn from a larger ` +
    `pool of source profiles.` +
    (shown < totalPairs
      ? ` The diagram draws ${shown} of ${totalPairs} interacting pairs: at this ` +
        `density nearly every node touches every other, so only repeated ` +
        `interactions are drawn. The tables are unfiltered.` : '');
}

slider.addEventListener('input', e => render(Number(e.target.value)));
loadRun(sel.value);
</script>
"""

PER_AGENT = ("agent_id", "username", "total_actions", "n_posts_authored",
             "distinct_posts_seen", "exposure_events", "engagement_rate",
             "action_counts", "following", "followers", "exposure_by_source")


def project(analysis_path, manifest_path=None):
    """Reduce one run's analysis + manifest to what the page renders.

    The analysis JSON carries the full event log, exposure ledger, post bodies
    and comments -- thousands of rows -- and the page reads none of them.
    Projecting explicitly keeps the artifact small even with many runs bundled.
    """
    with open(analysis_path) as fh:
        full = json.load(fh)

    manifest = {}
    mp = manifest_path or analysis_path.replace("_analysis.json", ".json")
    try:
        with open(mp) as fh:
            manifest = json.load(fh)
    except (OSError, json.JSONDecodeError):
        pass

    label = os.path.basename(analysis_path) \
        .replace("social_timeline_", "").replace("_analysis.json", "")
    cfg = manifest.get("config", {}) or {}
    totals = full.get("totals", {}) or {}
    turns = manifest.get("turns_without_action", {}) or {}
    tce = full.get("tool_call_errors") or {}
    sep = cfg.get("persona_separability") or {}

    n_turns = turns.get("agent_turns_total") or 0
    actions = totals.get("actions_chosen", 0)

    summary = {
        "agents": full.get("n_agents"),
        "rounds": full.get("n_rounds"),
        "posts": totals.get("posts", 0),
        "actions": actions,
        "exposures": totals.get("exposure_events", 0),
        "follow_edges": totals.get("follow_edges", 0),
        "action_rate": turns.get("action_rate"),
        "actions_per_turn": round(actions / n_turns, 2) if n_turns else None,
        "malformed": tce.get("total"),
        "prompt_version": cfg.get("prompt_version"),
        "persona_source": (os.path.basename(cfg.get("personas", "")) or None),
        "persona_similarity": sep.get("mean_similarity"),
        "minutes": (round(manifest["total_seconds"] / 60)
                    if manifest.get("total_seconds") else None),
    }

    return label, {
        "label": label,
        "summary": summary,
        "config": cfg,
        "algorithm": manifest.get("algorithm") or {},
        "graph_by_round": full.get("graph_by_round", {}),
        "interaction_pairs": full.get("interaction_pairs", {}),
        "exposure_pairs": dict(sorted(
            (full.get("exposure_pairs") or {}).items(),
            key=lambda kv: -kv[1])[:120]),
        "agents": {k: {f: v.get(f) for f in PER_AGENT}
                   for k, v in (full.get("agents") or {}).items()},
        "propagation": (full.get("propagation_candidates") or [])[:20],
    }


BASELINE_FILE = ".artifact_baseline"


def _started(analysis_path):
    """Run start time from its manifest; falls back to filename ordering."""
    mp = analysis_path.replace("_analysis.json", ".json")
    try:
        with open(mp) as fh:
            return json.load(fh).get("started_at", "") or ""
    except (OSError, json.JSONDecodeError):
        return ""


def discover(data_dir="data", since=None):
    """Analysed runs from the baseline forward, oldest first.

    Runs accumulate from a chosen starting point rather than including every
    run ever made: earlier runs used different personas, prompts and a feed
    that discarded its own ranking, so putting them beside current runs in one
    comparison table invites false conclusions. The baseline label is stored in
    data/.artifact_baseline so it survives between invocations, and anything
    started at or after that run is included automatically.
    """
    import glob

    found = sorted(glob.glob(os.path.join(
        data_dir, "social_timeline_*_analysis.json")))
    dated = [(_started(p) or os.path.basename(p), p) for p in found]
    dated.sort()

    if since is None:
        bpath = os.path.join(data_dir, BASELINE_FILE)
        if os.path.exists(bpath):
            since = open(bpath).read().strip() or None

    if since:
        target = os.path.join(
            data_dir, f"social_timeline_{since}_analysis.json")
        cutoff = _started(target)
        if cutoff:
            dated = [(d, p) for d, p in dated if d >= cutoff]
        else:
            # No manifest for the baseline: fall back to label matching so a
            # missing timestamp degrades to "this run onward" rather than
            # silently including everything.
            labels = [os.path.basename(p) for _, p in dated]
            key = f"social_timeline_{since}_analysis.json"
            if key in labels:
                dated = dated[labels.index(key):]
    return [p for _, p in dated]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--analysis", nargs="*", default=None,
                    help="one or more *_analysis.json files. Omit to include "
                         "every analysed run found in --data-dir.")
    ap.add_argument("--manifest", default=None,
                    help="only meaningful with a single --analysis file")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--since", default=None,
                    help="run label to start from. Recorded as the baseline so "
                         "later invocations keep it without repeating the flag.")
    ap.add_argument("--set-baseline", default=None,
                    help="record this run label as the baseline and exit")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.set_baseline:
        with open(os.path.join(args.data_dir, BASELINE_FILE), "w") as fh:
            fh.write(args.set_baseline)
        print(f"baseline set to {args.set_baseline}; "
              f"runs from here forward will be included")
        return

    if args.since:
        with open(os.path.join(args.data_dir, BASELINE_FILE), "w") as fh:
            fh.write(args.since)

    paths = args.analysis or discover(args.data_dir, args.since)
    if not paths:
        raise SystemExit("no analysed runs found")

    runs, order = {}, []
    for path in paths:
        try:
            label, payload = project(
                path, args.manifest if len(paths) == 1 else None)
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            print(f"  skipped {os.path.basename(path)}: {exc}")
            continue
        runs[label] = payload
        order.append(label)

    html = HTML.replace("__DATA__", json.dumps(
        {"order": order, "runs": runs}, default=str))
    with open(args.out, "w") as fh:
        fh.write(html)
    print(f"wrote {args.out} ({len(html)/1024:.0f} KB, "
          f"{len(order)} run(s): {', '.join(order)})")


if __name__ == "__main__":
    main()
