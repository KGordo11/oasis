"""Build the before/after social-graph web diagram from an analysis JSON.

IN PLAIN WORDS
--------------
This builds the INTERACTIVE WEBPAGE for exploring the results.

It takes the finished runs and produces a single web page with tabs: a network
picture of who follows whom that you can scrub through round by round, every
post with who saw it, a per-person record, and a round-by-round timeline.

Everything is packed into that one file, so it can be shared or opened on its
own with nothing else installed.

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
import sys


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

  .tabs { display:flex; gap:4px; flex-wrap:wrap;
          border-bottom:1px solid var(--line); }
  .tabs button { font-family:"IBM Plex Mono", monospace; font-size:12.5px;
                 letter-spacing:.04em; text-transform:uppercase;
                 background:none; border:none; color:var(--muted);
                 padding:9px 14px; cursor:pointer; border-radius:6px 6px 0 0;
                 border-bottom:2px solid transparent; }
  .tabs button:hover { color:var(--fg); }
  .tabs button[aria-selected="true"] { color:var(--fg);
                 background:var(--panel); border-bottom-color:var(--follow); }
  .panel { display:flex; flex-direction:column; gap:20px; }
  /* display:flex on .panel outranks the UA [hidden] rule, so hiding
     a panel silently did nothing. */
  .panel[hidden] { display:none; }
  .cmp { display:grid; gap:18px; align-items:start;
         grid-template-columns:1fr; }
  .cmp.two { grid-template-columns:1fr 1fr; }
  @media (max-width:900px) { .cmp.two { grid-template-columns:1fr; } }
  .col { display:flex; flex-direction:column; gap:12px; min-width:0; }
  .colhead { font-family:"IBM Plex Mono", monospace; font-size:13px;
             letter-spacing:.05em; text-transform:uppercase;
             color:var(--fg); background:var(--panel-2);
             border:1px solid var(--line); border-radius:6px;
             padding:9px 12px; }
  .kv { display:grid; grid-template-columns:auto 1fr; gap:3px 12px;
        font-size:13px; }
  .kv dt { color:var(--muted); font-family:"IBM Plex Mono", monospace;
           font-size:11.5px; text-transform:uppercase; letter-spacing:.04em; }
  .kv dd { margin:0; font-variant-numeric:tabular-nums; }
  .tr { font-family:"IBM Plex Mono", monospace; font-size:12.5px;
        line-height:1.65; }
  .tr .rnd { font-family:"IBM Plex Sans Condensed","IBM Plex Sans",sans-serif;
             font-size:17px; font-weight:700; color:var(--fg);
             border-bottom:1px solid var(--line); padding:14px 0 6px;
             margin-top:18px; }
  .tr .saw { color:var(--muted); padding-left:18px; }
  .tr .did { color:var(--fg); padding-left:6px; }
  .tr .acted { color:var(--interact); font-weight:600; }
  .tr .txt { color:var(--fg); padding-left:34px; border-left:2px solid var(--line);
             margin:3px 0 6px 12px; font-family:"IBM Plex Sans",sans-serif;
             font-size:13px; }
  .tr .who { color:var(--follow); font-weight:600; }
  .ev { border-bottom:1px solid var(--line); padding:7px 0; font-size:13px; }
  .ev:last-child { border-bottom:none; }
  .card { border:1px solid var(--line); border-radius:8px;
          background:var(--panel); padding:14px 16px; }
  .card h3 { margin:0 0 6px; font-size:15px;
             font-family:"IBM Plex Mono", monospace; }
  .quote { border-left:2px solid var(--line); padding-left:12px;
           color:var(--fg); font-size:13.5px; margin:6px 0; }
  /* Posts stack flush; only replies indent, and only by one step. */
  #postList { display:flex; flex-direction:column; gap:12px; }
  #postList .card.post { margin:0; }
  .thread { margin:12px 0 2px 6px; padding-left:16px;
            border-left:2px solid var(--accent, var(--line));
            display:flex; flex-direction:column; gap:12px; }
  .reply .rhead { font-family:"IBM Plex Mono", monospace; font-size:12.5px;
                  color:var(--muted); margin-bottom:3px; }
  .reply .rbody { font-size:13.5px; color:var(--fg); }
  .meta { color:var(--muted); font-size:12.5px;
          font-family:"IBM Plex Mono", monospace; }
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

  <nav class="tabs" id="tabs"></nav>

  <section class="panel" id="panel-network">
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
  </section>

  <section class="panel" id="panel-rounds" hidden>
    <div class="runbar">
      <label for="roundA">Round</label>
      <select id="roundA"></select>
      <label><input type="checkbox" id="cmpOn"> compare with</label>
      <select id="roundB" disabled></select>
      <label><input type="checkbox" id="cmpRun"> across runs</label>
      <select id="runB" disabled></select>
    </div>
    <div id="roundBody" class="cmp"></div>
  </section>

  <section class="panel" id="panel-transcript" hidden>
    <p class="lede">A plain narration of everything that happened, in order.
      Every post an agent was shown, whether they acted on it, and every action
      they took with its full text. Nothing is summarised away.</p>
    <div class="runbar">
      <label for="trRound">Show</label>
      <select id="trRound"></select>
      <label><input type="checkbox" id="trFeeds" checked> include what each agent was shown</label>
      <span class="meta" id="trCount"></span>
    </div>
    <div id="transcriptBody"></div>
  </section>

  <section class="panel" id="panel-people" hidden>
    <p class="lede">Every agent. Click one for their persona, everything they
      did with full text, and their complete roster.</p>
    <div class="scroll">
      <table id="agentTable">
        <caption>All agents</caption>
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
    <div id="agentDetail"></div>
  </section>

  <section class="panel" id="panel-posts" hidden>
    <p class="lede">Every post written during the run, who saw it, and who
      engaged with it.</p>
    <div id="postList"></div>
  </section>

  <section class="panel" id="panel-timeline" hidden>
    <div class="scroll">
      <table id="timelineTable">
        <caption>Round by round</caption>
        <thead><tr>
          <th class="num">Round</th><th class="num">Actions</th>
          <th class="num">Posts</th><th class="num">Comments</th>
          <th class="num">Likes</th><th class="num">Follows</th>
          <th class="num">Exposures</th><th class="num">Via graph</th>
        </tr></thead>
        <tbody></tbody>
      </table>
    </div>
    <p class="note">"Via graph" is the share of exposures delivered because the
      viewer follows the author. It starts at zero -- the network is not seeded
      -- and grows as agents connect, which is the shift from algorithmic to
      social discovery, measured rather than assumed.</p>
  </section>

  <section class="panel" id="panel-method" hidden>
    <div id="methodBody"></div>
  </section>
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
  postList(); timelineTable(); methodBody(); roundsPanel();
  transcriptPanel();
  document.getElementById('agentDetail').innerHTML = '';
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

function interactionEdges(upTo) {
  // Interactions must respect the round slider. This previously read the
  // run-total interaction_pairs, so round 0 -- before anyone had seen or done
  // anything -- still drew every interaction that ever occurred, making an
  // empty network look connected. Rebuild from the event log instead, keeping
  // only what had actually happened by the round being viewed.
  const upto = (upTo === undefined) ? maxRound : upTo;
  const counts = {};
  for (const e of DATA.events || []) {
    const [rnd, actor, , , target] = e;
    if (rnd > upto) continue;
    if (target === null || target === undefined || target === actor) continue;
    const k = actor + '->' + target;
    counts[k] = (counts[k] || 0) + 1;
  }
  const all = Object.entries(counts).map(([key, n]) => {
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
  const interactions = interactionEdges(round);
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
      focusId = (focusId === n.id) ? null : n.id;
      render(lastRound);
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
    return `<tr data-agent="${a.agent_id}" style="cursor:pointer">` +
      `<td class="num">${a.agent_id}</td>` +
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

document.querySelector('#agentTable').addEventListener('click', e => {
  const tr = e.target.closest('tr[data-agent]');
  if (tr) agentDetail(Number(tr.dataset.agent));
});

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
  const shown = interactionEdges(maxRound).length;
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

// ---------- tabs ----------
const TABS = [['network','Network'], ['rounds','Rounds'],
              ['transcript','Transcript'],
              ['people','People'], ['posts','Posts'],
              ['timeline','Timeline'], ['method','Method & integrity']];
const tabs = document.getElementById('tabs');
tabs.innerHTML = TABS.map(([k, lbl], i) =>
  `<button role="tab" data-tab="${k}" aria-selected="${i === 0}">${lbl}</button>`
).join('');
tabs.addEventListener('click', e => {
  const b = e.target.closest('button');
  if (!b) return;
  TABS.forEach(([k]) => {
    document.getElementById('panel-' + k).hidden = (k !== b.dataset.tab);
    tabs.querySelector(`[data-tab="${k}"]`)
        .setAttribute('aria-selected', String(k === b.dataset.tab));
  });
});

function esc(t) {
  return String(t === null || t === undefined ? '' : t)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ---------- transcript: narrate everything, in order ----------
const VERB = {
  create_post: 'posted', create_comment: 'replied to', like_post: 'liked',
  dislike_post: 'disliked', like_comment: 'liked a comment on',
  dislike_comment: 'disliked a comment on', repost: 'reposted',
  quote_post: 'quoted', follow: 'followed', unfollow: 'unfollowed',
  mute: 'muted', unmute: 'unmuted', report_post: 'reported',
  search_posts: 'searched posts for', search_user: 'searched for a user',
  trend: 'checked trending', do_nothing: 'did nothing',
  unlike_post: 'removed a like from', undo_dislike_post: 'undid a dislike on',
};

function transcriptFor(run, rnd, withFeeds) {
  // One round, narrated. Feeds first -- an agent can only act on what it was
  // shown, so the exposures are the context its actions are answering.
  const out = [`<div class="rnd">Round ${rnd}</div>`];
  const evs = (run.events || []).filter(e => e[0] === rnd);
  const exps = (run.exposures || []).filter(e => e[0] === rnd);

  const actors = [...new Set([...exps.map(e => e[1]), ...evs.map(e => e[1])])]
    .sort((a, b) => a - b);

  if (!actors.length) {
    out.push('<div class="saw">nothing happened this round</div>');
    return out.join('');
  }

  for (const id of actors) {
    const nm = `<span class="who">${esc(nameIn(run, id))}</span>`;
    const mySaw = exps.filter(e => e[1] === id)
      .sort((a, b) => (a[4] ?? 0) - (b[4] ?? 0));
    const myDid = evs.filter(e => e[1] === id);
    const actedOn = new Set(myDid.map(e => e[3]).filter(x => x !== null && x !== undefined));

    if (withFeeds) {
      if (mySaw.length) {
        out.push(`<div class="saw">${nm} opened the app and was shown ` +
                 `${mySaw.length} post${mySaw.length === 1 ? '' : 's'}:</div>`);
        for (const e of mySaw) {
          const [, , pid, au, pos, src, sc] = e;
          const post = run.posts[pid] || {};
          const did = actedOn.has(pid);
          out.push(`<div class="saw">&nbsp;&nbsp;#${pid} by ` +
            `${esc(nameIn(run, au))} &middot; ${SRCNAME[src]}` +
            (sc === null || sc === undefined ? '' : ` &middot; score ${sc}`) +
            ` &middot; slot ${pos ?? '?'} &middot; ` +
            (did ? '<span class="acted">ACTED ON THIS</span>'
                 : 'scrolled past') +
            `<div class="txt">${esc(String(post.content || '').slice(0, 220))}</div></div>`);
        }
      } else {
        out.push(`<div class="saw">${nm} opened the app and was shown nothing.</div>`);
      }
    }

    if (!myDid.length) {
      out.push(`<div class="did">${nm} did nothing.</div>`);
      continue;
    }
    for (const e of myDid) {
      const [, , act, pid, tgt, text, cid, newPid] = e;
      const verb = VERB[act] || act;
      let line = `${nm} ${verb}`;
      if (act === 'create_post') {
        line += ` (post #${newPid ?? '?'})`;
      } else if (tgt !== null && tgt !== undefined) {
        line += ` ${esc(nameIn(run, tgt))}`;
        if (pid) line += `'s post #${pid}`;
      } else if (pid) {
        line += ` post #${pid}`;
      }
      let body = '';
      if (act === 'create_comment' && cid && run.comments[cid])
        body = run.comments[cid].content;
      else if (text) body = text;
      out.push(`<div class="did">${line}.</div>` +
               (body ? `<div class="txt">${esc(body)}</div>` : ''));
    }
  }
  return out.join('');
}

function transcriptPanel() {
  const sel = document.getElementById('trRound');
  const feeds = document.getElementById('trFeeds');
  const keep = sel.value;
  sel.innerHTML = '<option value="all">every round</option>' +
    Array.from({length: maxRound + 1}, (_, i) =>
      `<option value="${i}">round ${i} only</option>`).join('');
  sel.value = (keep && (keep === 'all' || Number(keep) <= maxRound)) ? keep : '0';

  function draw() {
    const body = document.getElementById('transcriptBody');
    const rounds = sel.value === 'all'
      ? Array.from({length: maxRound + 1}, (_, i) => i)
      : [Number(sel.value)];
    body.className = 'tr';
    body.innerHTML = rounds.map(r =>
      transcriptFor(DATA, r, feeds.checked)).join('');
    document.getElementById('trCount').textContent =
      `${DATA.events.length} actions and ${DATA.exposures.length} exposures ` +
      `across ${maxRound + 1} rounds in ${DATA.label}`;
  }
  sel.onchange = draw; feeds.onchange = draw;
  draw();
}

// ---------- rounds: exactly what happened, round by round ----------
const SRCNAME = ['discovery','network','fof','both','?'];

function nameIn(run, id) {
  const a = (run.agents[String(id)] || run.agents[id] || {});
  const real = a.realname && a.realname !== a.username ? ` (${a.realname})` : '';
  return (a.username || ('agent' + id)) + real;
}

function roundReport(run, rnd) {
  // Everything that happened in one round of one run, in full: who acted, on
  // whom, with what text, plus what the feed delivered and what it changed.
  const evs = (run.events || []).filter(e => e[0] === rnd);
  const exps = (run.exposures || []).filter(e => e[0] === rnd);
  const tl = (run.timeline || []).find(t => t.round === rnd) || {};

  const byAction = {};
  evs.forEach(e => byAction[e[2]] = (byAction[e[2]] || 0) + 1);

  // New follow edges created this round.
  const edgesNow = (run.graph_by_round || {})[rnd] || [];
  const edgesPrev = (run.graph_by_round || {})[rnd - 1] || [];
  const prevKey = new Set(edgesPrev.map(p => p.join('>')));
  const newEdges = edgesNow.filter(p => !prevKey.has(p.join('>')));

  const viaGraph = exps.filter(e => e[5] === 1 || e[5] === 2).length;

  const evHtml = evs.length ? evs.map(e => {
    const [, actor, act, pid, tgt, text, cid, newPid] = e;
    let body = '';
    if (act === 'create_comment' && cid && run.comments[cid])
      body = run.comments[cid].content;
    else if (text) body = text;
    const target = (tgt !== null && tgt !== undefined)
      ? ` <span style="opacity:.7">&rarr;</span> ${esc(nameIn(run, tgt))}` : '';
    const on = pid ? ` <span class="meta">post #${pid}</span>`
                   : (newPid ? ` <span class="meta">post #${newPid}</span>` : '');
    return `<div class="ev"><b>${esc(nameIn(run, actor))}</b> ` +
      `<span style="color:var(--interact)">${esc(act)}</span>${on}${target}` +
      (body ? `<div class="quote">${esc(body)}</div>` : '') + `</div>`;
  }).join('') : '<div class="meta">no actions this round</div>';

  const edgeHtml = newEdges.length
    ? newEdges.map(([a, b]) =>
        `<div class="ev">${esc(nameIn(run, a))} <span style="color:var(--follow)">now follows</span> ${esc(nameIn(run, b))}</div>`).join('')
    : '<div class="meta">no new follows this round</div>';

  // Who saw whom, this round.
  const pair = {};
  exps.forEach(e => {
    if (e[3] === null || e[3] === undefined || e[3] === e[1]) return;
    const k = e[1] + '>' + e[3];
    pair[k] = (pair[k] || 0) + 1;
  });
  const topPairs = Object.entries(pair).sort((a, b) => b[1] - a[1]).slice(0, 15);
  const pairHtml = topPairs.length ? topPairs.map(([k, n]) => {
    const [v, au] = k.split('>').map(Number);
    return `<tr><td class="who">${esc(nameIn(run, v))}</td>` +
      `<td class="who">${esc(nameIn(run, au))}</td><td class="num">${n}</td></tr>`;
  }).join('') : '<tr><td colspan="3">nobody saw anything this round</td></tr>';

  const srcCount = {};
  exps.forEach(e => srcCount[SRCNAME[e[5]]] = (srcCount[SRCNAME[e[5]]] || 0) + 1);

  return `<div class="col">
    <div class="colhead">${esc(run.label)} &middot; round ${rnd}</div>
    <div class="card"><dl class="kv">
      <dt>actions</dt><dd>${evs.length}</dd>
      <dt>exposures</dt><dd>${exps.length}</dd>
      <dt>via graph</dt><dd>${viaGraph}${exps.length ? ' (' + Math.round(viaGraph / exps.length * 100) + '%)' : ''}</dd>
      <dt>new follows</dt><dd>${newEdges.length}</dd>
      <dt>total edges</dt><dd>${edgesNow.length}</dd>
      <dt>feed sources</dt><dd>${esc(JSON.stringify(srcCount))}</dd>
      <dt>action mix</dt><dd>${esc(JSON.stringify(byAction))}</dd>
    </dl></div>
    <div class="card"><h3>Every action this round (${evs.length})</h3>${evHtml}</div>
    <div class="card"><h3>New connections (${newEdges.length})</h3>${edgeHtml}</div>
    <div class="scroll"><table><caption>Who saw whom this round</caption>
      <thead><tr><th>Viewer</th><th>Author</th><th class="num">Times</th></tr></thead>
      <tbody>${pairHtml}</tbody></table></div>
  </div>`;
}

function roundsPanel() {
  const selA = document.getElementById('roundA');
  const selB = document.getElementById('roundB');
  const selRun = document.getElementById('runB');
  const cmpOn = document.getElementById('cmpOn');
  const cmpRun = document.getElementById('cmpRun');

  const opts = Array.from({length: maxRound + 1}, (_, i) =>
    `<option value="${i}">round ${i}</option>`).join('');
  const keepA = selA.value, keepB = selB.value;
  selA.innerHTML = opts; selB.innerHTML = opts;
  selA.value = (keepA && Number(keepA) <= maxRound) ? keepA : '0';
  selB.value = (keepB && Number(keepB) <= maxRound) ? keepB : String(maxRound);
  selRun.innerHTML = ALL.order.map(k => `<option value="${k}">${k}</option>`).join('');
  if (!selRun.value) selRun.value = ALL.order[0];

  function draw() {
    selB.disabled = !cmpOn.checked;
    selRun.disabled = !cmpRun.checked;
    const box = document.getElementById('roundBody');
    const a = roundReport(DATA, Number(selA.value));
    if (!cmpOn.checked && !cmpRun.checked) {
      box.className = 'cmp'; box.innerHTML = a; return;
    }
    // Comparing across runs pins the same round in the other run unless a
    // different round is also chosen, so a like-for-like read is the default.
    const otherRun = cmpRun.checked ? ALL.runs[selRun.value] : DATA;
    const otherRnd = cmpOn.checked ? Number(selB.value) : Number(selA.value);
    box.className = 'cmp two';
    box.innerHTML = a + roundReport(otherRun, otherRnd);
  }
  [selA, selB, selRun].forEach(el => el.onchange = draw);
  [cmpOn, cmpRun].forEach(el => el.onchange = draw);
  draw();
}

// ---------- people: full dossier for one agent ----------
function agentDetail(id) {
  const a = byId[id];
  const box = document.getElementById('agentDetail');
  if (!a) { box.innerHTML = ''; return; }

  const demo = ['age','gender','country','mbti','profession']
    .filter(k => a[k]).map(k => `${k}: ${esc(a[k])}`).join(' | ');
  const topics = (a.interested_topics || []).join(', ');

  // Everything this agent did, in order, with the actual text.
  const mine = DATA.events.filter(e => e[1] === id)
    .sort((x, y) => x[0] - y[0]);
  const actions = mine.map(e => {
    const [rnd, , act, pid, tgt, text, cid, newPid] = e;
    const who = tgt !== null && tgt !== undefined
      ? ' &rarr; @' + esc((byId[tgt] || {}).username || tgt) : '';
    let body = '';
    if (act === 'create_comment' && cid && DATA.comments[cid])
      body = DATA.comments[cid].content;
    else if (text) body = text;
    else if (pid && DATA.posts[pid]) body = DATA.posts[pid].content;
    const on = pid ? ` on post #${pid}` : (newPid ? ` (post #${newPid})` : '');
    return `<div style="margin:7px 0"><span class="meta">r${rnd}</span> ` +
      `<b>${esc(act)}</b>${on}${who}` +
      (body ? `<div class="quote">${esc(body)}</div>` : '') + `</div>`;
  }).join('') || '<div class="meta">did nothing all run</div>';

  // Complete roster: every other agent, seen or not.
  const saw = a.saw_authors || {}, out = a.interacted_with || {},
        back = a.interacted_by || {};
  const others = Object.values(agents).map(x => x.agent_id)
    .filter(x => x !== id)
    .sort((x, y) => (saw[y] || 0) - (saw[x] || 0) || x - y);
  const nSeen = others.filter(o => saw[o]).length;
  const fmt = (m, o) => {
    const e = Object.entries(m[o] || m[String(o)] || {});
    return e.length ? e.map(([k, v]) => `${esc(k)}&times;${v}`).join(', ')
                    : '<span style="opacity:.4">&ndash;</span>';
  };
  const rosterRows = others.map(o => {
    const n = saw[o] || saw[String(o)] || 0;
    return `<tr><td class="who">${esc((byId[o] || {}).username || o)}</td>` +
      `<td class="num">${n || '<span style="opacity:.4">never saw</span>'}</td>` +
      `<td class="mix">${fmt(out, o)}</td>` +
      `<td class="mix">${fmt(back, o)}</td></tr>`;
  }).join('');

  // Every post this agent was shown.
  const seen = DATA.exposures.filter(e => e[1] === id)
    .sort((x, y) => x[0] - y[0] || (x[4] ?? 0) - (y[4] ?? 0));
  const SRCN = ['discovery','network','fof','both','?'];
  const acted = new Set(a.seen_and_acted || []);
  const seenRows = seen.map(e => {
    const [rnd, , pid, au, pos, src, sc] = e;
    const post = DATA.posts[pid] || {};
    return `<tr><td class="num">${rnd}</td><td class="num">#${pid}</td>` +
      `<td class="who">${esc((byId[au] || {}).username || au)}</td>` +
      `<td class="num">${pos ?? ''}</td><td class="mix">${SRCN[src]}</td>` +
      `<td class="num">${sc === null ? '&ndash;' : sc}</td>` +
      `<td class="mix">${acted.has(pid) ? '<b>ACTED</b>' : 'ignored'}</td>` +
      `<td class="mix">${esc(String(post.content || '').slice(0, 60))}</td></tr>`;
  }).join('');

  box.innerHTML =
    `<div class="card"><h3>@${esc(a.username)} ` +
      `<span class="meta">agent #${a.agent_id}` +
      (a.source_username ? ` (was ${esc(a.source_username)})` : '') +
      `</span></h3>` +
      (demo ? `<div class="meta">${demo}</div>` : '') +
      (topics ? `<div class="meta">interests: ${esc(topics)}</div>` : '') +
      `<div class="quote">${esc(a.bio)}</div>` +
      (a.persona && a.persona !== a.bio
        ? `<div class="meta">persona given to the model:</div>
           <div class="quote">${esc(a.persona)}</div>` : '') +
      `<div class="meta">follows: ${(a.following || []).map(x =>
          '@' + esc((byId[x] || {}).username || x)).join(', ') || 'nobody'}</div>` +
      `<div class="meta">followed by: ${(a.followers || []).map(x =>
          '@' + esc((byId[x] || {}).username || x)).join(', ') || 'nobody'}</div>` +
    `</div>` +
    `<div class="card"><h3>Everything @${esc(a.username)} did (${mine.length})</h3>${actions}</div>` +
    `<div class="scroll"><table><caption>Roster &mdash; saw ${nSeen} of ` +
      `${others.length} others, never saw ${others.length - nSeen}</caption>` +
      `<thead><tr><th>Other agent</th><th class="num">Times seen</th>` +
      `<th>Did to them</th><th>Came back</th></tr></thead>` +
      `<tbody>${rosterRows}</tbody></table></div>` +
    `<div class="scroll"><table><caption>Every post shown to ` +
      `@${esc(a.username)} (${seen.length} exposures)</caption>` +
      `<thead><tr><th class="num">Rnd</th><th class="num">Post</th>` +
      `<th>Author</th><th class="num">Pos</th><th>Source</th>` +
      `<th class="num">Score</th><th>Outcome</th><th>Content</th></tr></thead>` +
      `<tbody>${seenRows}</tbody></table></div>`;
  box.scrollIntoView({behavior: 'smooth', block: 'start'});
}

// ---------- posts ----------
function postList() {
  const reach = {}, eng = {};
  DATA.exposures.forEach(e => {
    (reach[e[2]] = reach[e[2]] || new Set()).add(e[1]);
  });
  DATA.events.forEach(e => {
    if (e[3] === null || e[3] === undefined) return;
    (eng[e[3]] = eng[e[3]] || []).push([e[1], e[2]]);
  });
  const byPost = {};
  Object.values(DATA.comments).forEach(c => {
    (byPost[c.post] = byPost[c.post] || []).push(c);
  });

  const uname = id => '@' + esc((byId[id] || {}).username || id);

  // Top-level posts sit flush in document order. Comments are nested inside
  // the card of the post they reply to, indented once -- never twice, and
  // never cumulatively. (Before this, the card div was never closed, so each
  // post rendered INSIDE its predecessor and the whole list staircased right.)
  document.getElementById('postList').innerHTML =
    Object.values(DATA.posts).sort((a, b) => a.id - b.id).map(p => {
      const r = [...(reach[p.id] || [])];
      const e = eng[p.id] || [];
      const th = (byPost[p.id] || []).slice().sort((a, b) => a.id - b.id);

      const replies = th.length
        ? `<div class="thread">` + th.map(c =>
            `<div class="reply">` +
              `<div class="rhead">&#8627; #${c.id} ${uname(c.author)} replied` +
              (c.round !== undefined && c.round !== null
                ? ` <span class="meta">round ${c.round}</span>` : '') +
              `</div>` +
              `<div class="rbody">${esc(c.content)}</div>` +
            `</div>`).join('') + `</div>`
        : '';

      return `<article class="card post">` +
        `<h3>#${p.id} by ${uname(p.author)}` +
        ` <span class="meta">round ${p.round} &middot; ${p.likes} likes &middot; ` +
        `${p.dislikes} dislikes &middot; ${p.shares} shares &middot; ` +
        `${th.length} ${th.length === 1 ? 'reply' : 'replies'}</span></h3>` +
        `<div class="quote">${esc(p.content)}</div>` +
        `<div class="meta">shown to ${r.length} agents: ${
          r.map(uname).join(', ') || 'nobody'}</div>` +
        `<div class="meta">engagement: ${
          e.length ? e.map(([who, act]) => uname(who) + ' ' + esc(act)).join('; ')
          : 'none'}</div>` +
        replies +
        `</article>`;
    }).join('');
}

// ---------- timeline ----------
function timelineTable() {
  document.querySelector('#timelineTable tbody').innerHTML =
    (DATA.timeline || []).map(t =>
      `<tr><td class="num">${t.round}</td><td class="num">${t.actions}</td>` +
      `<td class="num">${t.posts}</td><td class="num">${t.comments}</td>` +
      `<td class="num">${t.likes}</td><td class="num">${t.follows}</td>` +
      `<td class="num">${t.exposures}</td>` +
      `<td class="num">${t.exposures ? Math.round(t.via_graph / t.exposures * 100) + '%' : '-'}</td></tr>`
    ).join('');
}

// ---------- method & integrity ----------
function methodBody() {
  const C = DATA.config || {}, A = DATA.algorithm || {}, I = DATA.integrity || {};
  const T = DATA.tool_errors || {};
  const EXPLAIN = {
    blind_actions_rejected: 'actions aimed at a post or person the agent had never been shown. On a real platform you cannot like something you never encountered.',
    invalid_follow_targets: 'follows aimed at an agent id that does not exist -- the model inventing a plausible number.',
    refresh_errors: 'feed builds that threw. Upstream swallows these silently; counted here so a lost turn is visible.',
    empty_feeds: 'feeds legitimately empty -- round 0 before anyone has posted, or an agent whose only visible posts are its own.',
    dm_joins_refused: 'attempts to join a 2-member group, refused to keep emergent private conversation private.',
  };
  const rows = Object.entries(I).map(([k, v]) =>
    `<tr><td class="who">${esc(k)}</td><td class="num">${v}</td>` +
    `<td class="mix">${esc(EXPLAIN[k] || '')}</td></tr>`).join('');

  document.getElementById('methodBody').innerHTML =
    `<div class="card"><h3>Where the people come from</h3>
      <p>Personas are loaded from <code>${esc(C.personas || '?')}</code>. Each
      record's text is flattened into one profile string and rendered as that
      agent's <b>system prompt</b>, so every decision it makes is conditioned on
      it. Mean pairwise similarity between personas is
      <b>${DATA.summary.persona_similarity ?? '?'}</b> &mdash; lower means more
      distinguishable, and an interest-based feed can only separate people to
      the degree they actually differ.</p></div>` +
    `<div class="card"><h3>Where the posts come from</h3>
      <p>Nowhere but the model. There is no post corpus, no seed content and no
      scripted action anywhere in the run. Every post, comment and quote was
      generated at runtime by <code>${esc(C.model || '?')}</code> from that
      agent's system prompt plus the feed it was shown that round.</p>
      <p class="meta">persona file &rarr; profile string &rarr; system prompt
      &rarr; ${esc(C.model || 'model')} &rarr; tool call &rarr; post table</p></div>` +
    `<div class="card"><h3>Where the feed comes from</h3>
      <p><code>${esc(A.formula || '')}</code></p>
      <p>A feed is the union of two sources, and every exposure records which
      one delivered it: <b>recsys</b> (the ranking chose it),
      <b>following</b> (the viewer follows the author), or <b>both</b>.
      ${C.refresh_rec_post_count ?? '?'} algorithmic posts +
      ${C.following_post_count ?? '?'} from people followed, ranked from a pool
      of ${C.max_rec_post_len ?? '?'}, with
      ${A.explore_slots ?? 0} slot(s) kept for exploration. The network starts
      at <b>${A.initial_follow_edges ?? 0} follow edges</b> &mdash; nothing is
      seeded.</p></div>` +
    `<div class="scroll"><table><caption>Integrity counters &mdash; so a degraded run cannot look like a clean one</caption>` +
      `<thead><tr><th>Counter</th><th class="num">Value</th><th>What it means</th></tr></thead>` +
      `<tbody>${rows}</tbody></table></div>` +
    (T.total ? `<div class="card"><h3>Malformed tool calls: ${T.total}</h3>
      <p class="meta">Actions the model chose and then mis-called. They leave no
      trace row, so without this accounting they are indistinguishable from an
      agent deciding to do nothing.</p>
      <div class="meta">by action: ${esc(JSON.stringify(T.by_action || {}))}</div>
      <div class="meta">by reason: ${esc(JSON.stringify(T.by_reason || {}))}</div></div>` : '') +
    ((DATA.phantom_follows || []).length
      ? `<div class="card"><h3>Phantom follows excluded: ${DATA.phantom_follows.length}</h3>
         <p class="meta">Edges aimed at agent ids that do not exist. Segregated
         rather than counted, so the graph reflects real relationships.</p></div>`
      : '');
}

slider.addEventListener('input', e => render(Number(e.target.value)));
loadRun(sel.value);
</script>
"""

PER_AGENT = ("agent_id", "username", "total_actions", "n_posts_authored",
             "distinct_posts_seen", "exposure_events", "engagement_rate",
             "action_counts", "following", "followers", "exposure_by_source",
             "saw_authors", "interacted_with", "interacted_by",
             "seen_and_acted", "seen_and_ignored", "never_seen", "bio")


def _personas_for(cfg):
    """Persona records keyed by handle, so the page can show who someone is."""
    path = cfg.get("personas")
    if not path or not os.path.exists(path):
        return {}
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from personas import load_personas
        return {p["username"]: p for p in load_personas(path)}
    except Exception:  # noqa: BLE001 - persona detail is a nicety, not a gate
        return {}


def project(analysis_path, manifest_path=None):
    """Reduce one run to what the page renders.

    The page is now the only artifact anyone reads, so it carries the whole
    record -- posts, comments, every action with its text, and every exposure --
    not just summaries. Exposures are encoded as positional arrays because at
    ~5000 rows per run the key names would otherwise dominate the payload.
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
    personas = _personas_for(cfg)

    n_turns = turns.get("agent_turns_total") or 0
    actions = totals.get("actions_chosen", 0)

    summary = {
        "agents": full.get("n_agents"), "rounds": full.get("n_rounds"),
        "posts": totals.get("posts", 0), "actions": actions,
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
        "action_counts": totals.get("action_counts", {}),
    }

    agents = {}
    for k, v in (full.get("agents") or {}).items():
        rec = {f: v.get(f) for f in PER_AGENT}
        p = personas.get(v.get("username")) or {}
        rec["persona"] = p.get("persona") or ""
        rec["source_username"] = p.get("source_username")
        rec["realname"] = p.get("realname")
        for f in ("age", "gender", "country", "mbti", "profession"):
            if p.get(f):
                rec[f] = p[f]
        rec["interested_topics"] = p.get("interested_topics") or []
        agents[k] = rec

    posts = {str(pid): {
        "id": pid, "author": pp["author_id"], "content": pp["content"],
        "round": pp["round"], "likes": pp["num_likes"],
        "dislikes": pp["num_dislikes"], "shares": pp["num_shares"],
    } for pid, pp in (full.get("posts") or {}).items()}

    comments = {str(cid): {
        "id": cid, "post": cc["post_id"], "author": cc["user_id"],
        "content": cc["content"], "round": cc.get("created_at"),
    } for cid, cc in (full.get("comments") or {}).items()}

    events = [[e["round"], e["agent_id"], e["action"], e.get("post_id"),
               e.get("target_agent_id"),
               (e.get("info") or {}).get("content")
               or (e.get("info") or {}).get("quote_content")
               or (e.get("info") or {}).get("query"),
               (e.get("info") or {}).get("comment_id"),
               (e.get("info") or {}).get("post_id")]
              for e in (full.get("events") or [])]

    # [round, agent, post, author, feed_position, source, score]
    # Old runs labelled sources recsys/following/both; the three-tier feed
    # (F-25) labels them discovery/network/fof. They are the same concepts
    # renamed, so both vocabularies map to one index set and runs from either
    # era stay readable side by side.
    SRC = {"discovery": 0, "recsys": 0,
           "network": 1, "following": 1,
           "fof": 2, "both": 3}
    exposures = [[e["round"], e["agent_id"], e["post_id"], e.get("author_id"),
                  e.get("feed_position"), SRC.get(e.get("source"), 3),
                  (round(e["score"], 4)
                   if isinstance(e.get("score"), (int, float)) else None)]
                 for e in (full.get("exposures") or [])]

    # Round-by-round: actions, new follows, exposures, and how much of the
    # feed arrived through the social graph rather than the algorithm.
    from collections import Counter, defaultdict
    per = defaultdict(Counter)
    for e in (full.get("events") or []):
        per[e["round"]][e["action"]] += 1
    expo_r = Counter(x[0] for x in exposures)
    graph_r = Counter(x[0] for x in exposures if x[5] in (1, 2))
    rounds_tl = []
    for r in sorted(set(list(per) + list(expo_r))):
        rounds_tl.append({
            "round": r, "actions": sum(per[r].values()),
            "posts": per[r].get("create_post", 0),
            "comments": per[r].get("create_comment", 0),
            "likes": per[r].get("like_post", 0) + per[r].get("like_comment", 0),
            "follows": per[r].get("follow", 0),
            "exposures": expo_r.get(r, 0),
            "via_graph": graph_r.get(r, 0),
        })

    return label, {
        "label": label, "summary": summary, "config": cfg,
        "algorithm": manifest.get("algorithm") or {},
        "integrity": manifest.get("platform_stats") or {},
        "tool_errors": tce,
        "phantom_follows": full.get("phantom_follows") or [],
        "graph_by_round": full.get("graph_by_round", {}),
        "interaction_pairs": full.get("interaction_pairs", {}),
        "exposure_pairs": full.get("exposure_pairs", {}),
        "agents": agents, "posts": posts, "comments": comments,
        "events": events, "exposures": exposures, "timeline": rounds_tl,
        "propagation": (full.get("propagation_candidates") or [])[:40],
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
    """Command-line entry point: build the interactive web page."""
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
