"""Exhaustive dossier for a Simulation 4 run.

`analyze.py` produces the summary ledgers. This produces the complete record:
every agent, every post, every exposure, every interaction, every
conversation thread, with full content and full provenance -- the level of
detail needed to defend a result rather than merely state it.

Sections
    0  Provenance and method      where personas, posts and feeds come from
    1  Population                 demographics, topics, persona separability
    2  Run timeline               round-by-round evolution and saturation
    3  Network                    degree, reciprocity, mutuals, hubs
    4  Agent dossiers             per agent: persona, every action, everyone
                                  they touched, everyone who touched them,
                                  everything they saw and ignored
    5  Post ledger                every post, its reach, and who engaged
    6  Conversation threads       reconstructed reply structure
    7  Interaction matrix         every ordered pair, with content
   7B  Pair chronologies          EVERY exposure one by one: which post,
                                  which round, what score, and what the
                                  viewer did at that exact moment
    8  Propagation                exposure preceding interaction, with scores
    9  Feed composition           algorithmic vs social share over time
   10  Failures                   malformed tool calls, unattributed actions

Usage:
    oasis-env/bin/python examples/experiment/social_timeline/dossier.py \
        --db data/social_timeline_full_twhin_v2.db \
        --log <run>.log --personas data/reddit/user_data_36.json
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze  # noqa: E402  (path set above)

RULE = "=" * 100
SUB = "-" * 100


def wrap(text, width=94, indent="    "):
    """Wrap without external deps, preserving readability of long content."""
    if not text:
        return indent + "(empty)"
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return "\n".join(indent + ln for ln in lines)


def build(db_path, log_path=None, personas_path=None, manifest_path=None):
    data = analyze.analyze(db_path)
    if log_path:
        data["tool_call_errors"] = analyze.parse_tool_errors(log_path)

    conn = analyze.connect(db_path)
    extra = {}
    extra["comments"] = analyze.load_comments(conn)
    extra["rounds"] = [dict(r) for r in conn.execute(
        "SELECT * FROM round_boundary ORDER BY round")]
    extra["candidates"] = conn.execute(
        "SELECT COUNT(*) FROM rec_candidates").fetchone()[0]
    conn.close()

    personas = {}
    if personas_path and os.path.exists(personas_path):
        # Route through the loader: the persona source may be the structured
        # reddit JSON or the scraped twitter CSV, and json.load() only handles
        # the first.
        from personas import load_personas
        for p in load_personas(personas_path):
            personas[p["username"]] = p

    manifest = {}
    mp = manifest_path or db_path.replace(".db", ".json")
    if os.path.exists(mp):
        manifest = json.load(open(mp))

    return data, extra, personas, manifest


def s0_provenance(L, data, manifest, personas_path, db_path):
    a = manifest.get("algorithm", {})
    c = manifest.get("config", {})
    L += [RULE, "SECTION 0 -- PROVENANCE AND METHOD", RULE, "",
          "Every number in this document traces back to one of three sources.",
          "Nothing here is seeded, scripted, or hand-authored during the run.",
          "",
          "0.1  WHERE THE PEOPLE COME FROM", ""]
    L += [f"    Persona file : {personas_path}",
          "    Origin       : ships with OASIS upstream (camel-ai/oasis), added in",
          "                   commit f659261 'add example data'. Not written by us.",
          "    Count        : 36 personas, each with 10 fields:",
          "                   realname, username, bio, persona, age, gender, mbti,",
          "                   country, profession, interested_topics",
          "",
          "    How a persona becomes an agent:",
          "      1. compose_persona() flattens the record into ONE profile string",
          "         (timeline_agent.py) -- persona text, then demographics, MBTI,",
          "         profession, and interested_topics.",
          "      2. That string is placed in profile['other_info']['user_profile'].",
          "      3. UserInfo.to_twitter_system_message() renders it as the agent's",
          "         SYSTEM PROMPT under '# SELF-DESCRIPTION'.",
          "      4. The agent's every decision is conditioned on that prompt.",
          "",
          "    Why flattened: UserInfo.to_system_message() forks on recsys_type, and",
          "    the Twitter branch renders ONLY user_profile -- it drops age, gender,",
          "    MBTI and country, which the Reddit branch keeps (config/user.py:50-111).",
          "    We need the Twitter platform for follows/reposts, so the persona is",
          "    folded into the one field that branch actually reads. Prompt STRUCTURE",
          "    is untouched; only its content is enriched.",
          "",
          "0.2  WHERE THE POSTS COME FROM", "",
          "    Nowhere but the model. There is no post corpus, no seed content, and",
          "    no ManualAction anywhere in the driver. Every post, comment and quote",
          "    in this run was generated at runtime by llama3.1:8b, in response to",
          "    that agent's system prompt plus the feed it was shown that round,",
          "    and written to the database through create_post(content=...).",
          "",
          "    Chain: persona file -> profile string -> system prompt -> llama3.1:8b",
          "           -> tool call -> platform action -> post/comment table",
          "",
          "0.3  WHERE THE FEED COMES FROM", ""]
    if a:
        L += [f"    Algorithm   : {a.get('name')}",
              f"    Score       : {a.get('formula')}",
              f"    Embedding   : {a.get('embedding')}",
              f"    Initial graph: {a.get('initial_follow_edges', 0)} follow edges "
              "(the network is NOT seeded)"]
        for d in a.get("deviations_from_upstream", []):
            L += [f"    Deviation   : {d}"]
    L += ["",
          "    A feed is the UNION of two sources, and every exposure row records",
          "    which one delivered it:",
          f"      recsys    -- up to {c.get('refresh_rec_post_count','?')} posts sampled from that agent's",
          f"                   ranked candidate pool (top {c.get('max_rec_post_len','?')} by score)",
          f"      following -- up to {c.get('following_post_count','?')} posts by people the agent follows",
          "      both      -- the post qualified through both routes",
          "",
          "0.4  RUN CONFIGURATION", ""]
    for k in ("agents", "rounds", "recsys", "model", "prompt_version",
              "semaphore", "n_actions", "max_rec_post_len",
              "refresh_rec_post_count", "following_post_count"):
        if k in c:
            L += [f"    {k:<24} {c[k]}"]
    L += [f"    {'database':<24} {os.path.basename(db_path)}",
          f"    {'wall clock (s)':<24} {manifest.get('total_seconds','?')}", ""]
    return L


def s1_population(L, personas, data):
    L += [RULE, "SECTION 1 -- POPULATION", RULE, ""]
    if not personas:
        L += ["    (persona file not supplied)", ""]
        return L
    ps = list(personas.values())
    src = ps[0].get("source", "?") if ps else "?"
    L += [f"    {len(ps)} personas available.  source: {src}", ""]

    ages = [p["age"] for p in ps if p.get("age")]
    if ages:
        L += [f"    Age      : {min(ages)}-{max(ages)} "
              f"(median {int(statistics.median(ages))})"]
    for label, key in (("Gender   ", "gender"), ("Countries", "country"),
                       ("MBTI     ", "mbti")):
        vals = [p[key] for p in ps if p.get(key)]
        if vals:
            L += [f"    {label}: " + ", ".join(f"{k} {v}" for k, v in
                                               Counter(vals).most_common())]
    profs = [p["profession"] for p in ps if p.get("profession")]
    if profs:
        L += ["", "    Professions:"]
        for k, v in Counter(profs).most_common():
            L += [f"      {v:>3}  {k}"]
    topics = Counter(t for p in ps for t in (p.get("interested_topics") or []))
    if topics:
        L += ["", "    Declared interests (an agent may hold several):"]
        for k, v in topics.most_common():
            L += [f"      {v:>3}/{len(ps)}  {k:<24} {'#' * v}"]
    else:
        L += ["", "    These personas are scraped profile text with no "
              "structured demographic fields.",
              "    They trade that structure for separability -- see below."]
    L += ["",
          "    READ THIS BEFORE INTERPRETING ANY PERSONALISATION RESULT.",
          "    The interest distribution is heavily concentrated: a large majority of",
          "    this population declares the same few topics. An interest-based feed",
          "    can only separate people to the extent they actually differ, so a",
          "    homogeneous population puts a ceiling on how distinct feeds can get.",
          "    Section 4 reports each agent's realised feed distinctness against this.",
          ""]
    return L


def s2_timeline(L, data, extra):
    L += [RULE, "SECTION 2 -- RUN TIMELINE", RULE, "",
          "    Round-by-round. 'new follows' is edges created that round;",
          "    saturation shows as new follows decaying while actions stay flat.", ""]
    per = defaultdict(Counter)
    for e in data["events"]:
        per[e["round"]][e["action"]] += 1
    follows_by_round = Counter(f["round"] for f in
                               [{"round": e["round"]} for e in data["events"]
                                if e["action"] == "follow"])
    expo = Counter(e["round"] for e in data["exposures"])
    src = defaultdict(Counter)
    for e in data["exposures"]:
        src[e["round"]][e.get("source")] += 1

    L += [f"    {'rnd':<5}{'actions':<9}{'new foll':<10}{'cum':<6}{'posts':<7}"
          f"{'comments':<10}{'likes':<7}{'exposures':<11}{'via graph'}"]
    cum = 0
    for r in sorted(set(list(per) + list(expo))):
        n = sum(per[r].values())
        f = follows_by_round.get(r, 0)
        cum += f
        likes = per[r]["like_post"] + per[r]["like_comment"]
        graph = src[r]["following"] + src[r]["both"]
        pct = f"{graph/expo[r]*100:.0f}%" if expo.get(r) else "-"
        L += [f"    {r:<5}{n:<9}{f:<10}{cum:<6}{per[r]['create_post']:<7}"
              f"{per[r]['create_comment']:<10}{likes:<7}{expo.get(r,0):<11}{pct}"]
    L += ["",
          "    'via graph' is the share of exposures delivered because the viewer",
          "    follows the author. It starts at 0% (empty network by design) and",
          "    grows as agents build connections -- the shift from algorithmic to",
          "    social discovery, measured rather than assumed.", ""]
    return L


def s3_network(L, data):
    L += [RULE, "SECTION 3 -- NETWORK STRUCTURE", RULE, ""]
    agents = data["agents"]
    edges = set()
    for a in agents.values():
        for f in a.get("following", []):
            edges.add((int(a["agent_id"]), int(f)))
    out_deg = Counter(s for s, _ in edges)
    in_deg = Counter(t for _, t in edges)
    mutual = {(s, t) for s, t in edges if (t, s) in edges}

    def name(i):
        a = agents.get(i) or agents.get(str(i)) or {}
        return a.get("username", f"agent{i}")

    L += [f"    edges                 {len(edges)}",
          f"    agents with >=1 follow {len(out_deg)} of {len(agents)}",
          f"    agents followed by >=1 {len(in_deg)} of {len(agents)}",
          f"    isolated (no edges)    "
          f"{len([a for a in agents if int(a) not in out_deg and int(a) not in in_deg])}",
          f"    mutual pairs           {len(mutual)//2}",
          f"    reciprocity            "
          f"{len(mutual)/len(edges)*100:.1f}% of edges are reciprocated"
          if edges else "    reciprocity            n/a", ""]
    L += ["    MOST FOLLOWED (hubs):"]
    for aid, n in in_deg.most_common(10):
        followers = sorted(name(s) for s, t in edges if t == aid)
        L += [f"      {n:>3}  {name(aid):<24} <- {', '.join(followers)}"]
    L += ["", "    MOST ACTIVE FOLLOWERS:"]
    for aid, n in out_deg.most_common(10):
        followees = sorted(name(t) for s, t in edges if s == aid)
        L += [f"      {n:>3}  {name(aid):<24} -> {', '.join(followees)}"]
    if mutual:
        L += ["", "    MUTUAL FOLLOWS (both directions):"]
        seen = set()
        for s, t in sorted(mutual):
            if (t, s) in seen:
                continue
            seen.add((s, t))
            L += [f"      {name(s)} <-> {name(t)}"]
    L += [""]
    return L


def s4_agents(L, data, extra, personas):
    L += [RULE, "SECTION 4 -- AGENT DOSSIERS", RULE, "",
          "    One entry per agent: who they are, everything they did, everyone",
          "    they touched, everyone who touched them, and everything they were",
          "    shown -- including what they saw and ignored.", ""]
    agents = data["agents"]
    posts = data["posts"]
    comments = extra["comments"]

    def name(i):
        a = agents.get(i) or agents.get(str(i)) or {}
        return a.get("username", f"agent{i}")

    ev_by_agent = defaultdict(list)
    for e in data["events"]:
        ev_by_agent[e["agent_id"]].append(e)
    exp_by_agent = defaultdict(list)
    for e in data["exposures"]:
        exp_by_agent[e["agent_id"]].append(e)

    for key in sorted(agents, key=lambda k: int(k)):
        a = agents[key]
        aid = int(a["agent_id"])
        p = personas.get(a["username"], {})
        L += [SUB, f"AGENT {aid} -- @{a['username']}"
                   f"{'  (' + p.get('realname', '') + ')' if p else ''}", SUB]
        if p:
            L += [f"    {p.get('age')}y {p.get('gender')}, {p.get('country')} | "
                  f"MBTI {p.get('mbti')} | {p.get('profession')}",
                  f"    declared interests: {', '.join(p.get('interested_topics', []))}",
                  "    bio:", wrap(p.get("bio")),
                  "    persona (verbatim, as given to the model):",
                  wrap(p.get("persona"))]
        L += ["",
              f"    ACTIVITY  actions={a['total_actions']}  posts={a['n_posts_authored']}"
              f"  distinct posts seen={a['distinct_posts_seen']}"
              f"  exposure events={a['exposure_events']}"
              f"  engagement={a['engagement_rate']}",
              f"    action mix: {a['action_counts'] or '(none)'}",
              f"    follows ({len(a['following'])}): "
              f"{', '.join(name(x) for x in a['following']) or '(nobody)'}",
              f"    followed by ({len(a['followers'])}): "
              f"{', '.join(name(x) for x in a['followers']) or '(nobody)'}",
              ""]

        L += ["    EVERY ACTION THIS AGENT TOOK, IN ORDER:"]
        if not ev_by_agent[aid]:
            L += ["      (none)"]
        for e in sorted(ev_by_agent[aid], key=lambda x: x["round"]):
            act, pid, info = e["action"], e.get("post_id"), e.get("info") or {}
            tgt = e.get("target_agent_id")
            head = f"      r{e['round']:<3} {act:<18}"
            if act == "create_post":
                L += [head + f"-> own post #{info.get('post_id')}",
                      wrap(info.get("content"), indent="             ")]
            elif act == "create_comment":
                cid = info.get("comment_id")
                body = (comments.get(cid) or {}).get("content") or info.get("content")
                L += [head + f"-> on post #{pid} by @{name(tgt)}",
                      wrap(body, indent="             ")]
            elif act in ("quote_post", "repost"):
                L += [head + f"-> post #{pid} by @{name(tgt)}"]
                if info.get("quote_content"):
                    L += [wrap(info["quote_content"], indent="             ")]
            elif act in ("follow", "unfollow", "mute", "unmute"):
                L += [head + f"-> @{name(tgt)}" if tgt is not None
                      else head + "-> (target unresolved)"]
            elif pid is not None:
                snippet = (posts.get(pid) or {}).get("content", "")
                L += [head + f"-> post #{pid} by @{name(tgt)}: "
                             f"\"{str(snippet)[:60]}\""]
            else:
                L += [head + (f"{info}" if info else "")]

        out_pairs = a.get("interacted_with") or {}
        in_pairs = a.get("interacted_by") or {}
        L += ["", "    WHO THIS AGENT ACTED ON:"]
        if not out_pairs:
            L += ["      (nobody)"]
        for tgt, counts in sorted(out_pairs.items(),
                                  key=lambda kv: -sum(kv[1].values())):
            seen_n = (a.get("saw_authors") or {}).get(tgt, 0)
            L += [f"      -> @{name(int(tgt)):<24} "
                  f"{', '.join(f'{k}x{v}' for k, v in counts.items()):<52}"
                  f"(had seen them {seen_n}x)"]
        L += ["", "    WHO ACTED ON THIS AGENT:"]
        if not in_pairs:
            L += ["      (nobody)"]
        for src, counts in sorted(in_pairs.items(),
                                  key=lambda kv: -sum(kv[1].values())):
            L += [f"      <- @{name(int(src)):<24} "
                  f"{', '.join(f'{k}x{v}' for k, v in counts.items())}"]

        mine = [pid for pid, p in posts.items() if p["author_id"] == aid]
        L += ["", "    THIS AGENT'S OWN POSTS, AND WHO ENGAGED WITH EACH:"]
        if not mine:
            L += ["      (never posted)"]
        for pid in mine:
            p = posts[pid]
            saw = {e["agent_id"] for e in data["exposures"]
                   if e["post_id"] == pid}
            eng = defaultdict(list)
            for e in data["events"]:
                if e.get("post_id") == pid and e["agent_id"] != aid:
                    eng[e["agent_id"]].append(e["action"])
            L += [f"      post #{pid} (round {p['round']}, likes={p['num_likes']}"
                  f" dislikes={p['num_dislikes']} shares={p['num_shares']}):",
                  wrap(p["content"], indent="          "),
                  f"          shown to {len(saw)} agents: "
                  f"{', '.join('@'+name(x) for x in sorted(saw)) or 'nobody'}"]
            if eng:
                L += ["          engaged: " + "; ".join(
                    f"@{name(k)} {','.join(v)}" for k, v in eng.items())]
            else:
                L += ["          engaged: nobody"]

        # ---- complete roster: EVERY other agent, seen or not -------------
        L += ["",
              "    COMPLETE ROSTER -- this agent's relationship with every "
              "other agent",
              "    (every one of the other agents appears below, including "
              "those never seen)",
              ""]
        L += [f"      {'other agent':<26}{'saw':>4}  {'posts of theirs seen':<28}"
              f"{'what THIS agent did to them':<40}what they did back"]
        L += ["      " + "-" * 118]

        my_exp = exp_by_agent[aid]
        seen_posts_by_author = defaultdict(list)
        seen_count_by_author = Counter()
        for e in my_exp:
            au = e.get("author_id")
            if au is None or au == aid:
                continue
            seen_count_by_author[au] += 1
            if e["post_id"] not in seen_posts_by_author[au]:
                seen_posts_by_author[au].append(e["post_id"])

        out_map = a.get("interacted_with") or {}
        in_map = a.get("interacted_by") or {}

        others = sorted((int(k) for k in agents), key=lambda x: (
            -seen_count_by_author.get(x, 0), x))
        for other in others:
            if other == aid:
                continue
            n_seen = seen_count_by_author.get(other, 0)
            posts_seen = seen_posts_by_author.get(other, [])
            did = out_map.get(str(other)) or out_map.get(other) or {}
            back = in_map.get(str(other)) or in_map.get(other) or {}

            def fit(text, width):
                """Hard-truncate so columns cannot run into each other."""
                return (text if len(text) <= width
                        else text[:width - 2] + "..")

            posts_txt = (", ".join(f"#{p}" for p in posts_seen[:5])
                         + (f" +{len(posts_seen)-5}" if len(posts_seen) > 5
                            else "")) if posts_seen else "never saw any"
            posts_txt = fit(posts_txt, 27)
            did_txt = fit(", ".join(f"{k} x{v}" for k, v in did.items())
                          or "-", 39)
            back_txt = ", ".join(f"{k} x{v}" for k, v in back.items()) or "-"
            L += [f"      @{fit(name(other), 24):<25}{n_seen:>4}  {posts_txt:<28}"
                  f"{did_txt:<40}{back_txt}"]

        never = [o for o in others
                 if o != aid and not seen_count_by_author.get(o)]
        L += ["",
              f"      Saw content from {len(seen_count_by_author)} of "
              f"{len(agents) - 1} other agents; "
              f"never saw {len(never)}.",
              f"      Acted on {len(out_map)}; was acted on by {len(in_map)}."]

        L += ["", "    EXPOSURE BY AUTHOR (how often this agent saw each person):"]
        sa = sorted((a.get("saw_authors") or {}).items(),
                    key=lambda kv: -kv[1])
        if not sa:
            L += ["      (saw nobody)"]
        else:
            L += ["      " + "  ".join(f"@{name(int(k))}x{v}" for k, v in sa)]

        acted = set(a.get("seen_and_acted") or [])
        L += ["", f"    EVERY POST SHOWN TO THIS AGENT "
                  f"({len(exp_by_agent[aid])} exposure events):",
              f"      {'rnd':<5}{'post':<7}{'author':<24}{'pos':<5}"
              f"{'source':<11}{'score':<9}outcome"]
        for e in sorted(exp_by_agent[aid], key=lambda x: (x["round"],
                                                          x.get("feed_position") or 0)):
            sc = e.get("score")
            L += [f"      r{e['round']:<4}#{e['post_id']:<6}"
                  f"{name(e.get('author_id')):<24}"
                  f"{str(e.get('feed_position','')):<5}{str(e.get('source','')):<11}"
                  f"{(f'{sc:.4f}' if isinstance(sc,(int,float)) else '-'):<9}"
                  f"{'ACTED' if e['post_id'] in acted else 'ignored'}"]
        never = a.get("never_seen") or []
        L += ["", f"    POSTS THAT EXISTED BUT THIS AGENT NEVER SAW ({len(never)}):",
              wrap(", ".join(f"#{n}" for n in never) or "(none)",
                   indent="      "), ""]
    return L


def s5_posts(L, data, extra):
    L += [RULE, "SECTION 5 -- POST LEDGER", RULE, "",
          "    Every post: who wrote it, what it said, how far it reached, and",
          "    who engaged. 'reach' counts distinct agents shown the post.", ""]
    agents, posts = data["agents"], data["posts"]

    def name(i):
        a = agents.get(i) or agents.get(str(i)) or {}
        return a.get("username", f"agent{i}")

    reach = defaultdict(set)
    for e in data["exposures"]:
        reach[e["post_id"]].add(e["agent_id"])
    engaged = defaultdict(list)
    for e in data["events"]:
        if e.get("post_id") is not None:
            engaged[e["post_id"]].append((e["agent_id"], e["action"]))

    for pid in sorted(posts):
        p = posts[pid]
        L += [f"  POST #{pid}  by @{name(p['author_id'])}  round {p['round']}"
              f"  likes={p['num_likes']} dislikes={p['num_dislikes']}"
              f" shares={p['num_shares']}",
              wrap(p["content"], indent="      ")]
        r = sorted(reach.get(pid, []))
        L += [f"      reach: {len(r)} agents "
              f"[{', '.join(name(x) for x in r) if r else 'nobody saw this'}]"]
        eng = engaged.get(pid, [])
        if eng:
            byagent = defaultdict(list)
            for aid, act in eng:
                byagent[aid].append(act)
            L += ["      engagement: " + "; ".join(
                f"@{name(k)} {','.join(v)}" for k, v in byagent.items())]
        else:
            L += ["      engagement: none"]
        L += [""]
    return L


def s6_threads(L, data, extra):
    L += [RULE, "SECTION 6 -- CONVERSATION THREADS", RULE, "",
          "    Posts that drew replies, with the full exchange in order.", ""]
    agents, posts = data["agents"], data["posts"]

    def name(i):
        a = agents.get(i) or agents.get(str(i)) or {}
        return a.get("username", f"agent{i}")

    threads = defaultdict(list)
    for cid, c in extra["comments"].items():
        threads[c["post_id"]].append(c)
    if not threads:
        L += ["    (no comments recorded)", ""]
        return L
    for pid, cs in sorted(threads.items(), key=lambda kv: -len(kv[1])):
        p = posts.get(pid, {})
        L += [f"  THREAD on post #{pid} by @{name(p.get('author_id'))}"
              f"  ({len(cs)} repl{'y' if len(cs)==1 else 'ies'})",
              wrap(p.get("content"), indent="      ")]
        for c in sorted(cs, key=lambda x: x["comment_id"]):
            L += [f"      -- @{name(c['user_id'])} (comment #{c['comment_id']}):",
                  wrap(c["content"], indent="         ")]
        L += [""]
    return L


def s7_matrix(L, data):
    L += [RULE, "SECTION 7 -- INTERACTION MATRIX", RULE, "",
          "    Every ordered pair with at least one interaction, and how often",
          "    the actor had been shown the target's content beforehand.", ""]
    agents = data["agents"]

    def name(i):
        a = agents.get(i) or agents.get(str(i)) or {}
        return a.get("username", f"agent{i}")

    rows = []
    for key, counts in data["interaction_pairs"].items():
        s, t = key.split("->")
        seen = data["exposure_pairs"].get(key, 0)
        rows.append((sum(counts.values()), int(s), int(t), counts, seen))
    rows.sort(reverse=True)
    L += [f"    {'actor':<24}{'target':<24}{'n':<4}{'seen':<6}what"]
    for n, s, t, counts, seen in rows:
        L += [f"    {name(s):<24}{name(t):<24}{n:<4}{seen:<6}"
              f"{', '.join(f'{k}x{v}' for k, v in counts.items())}"]
    L += ["", f"    {len(rows)} interacting ordered pairs out of "
              f"{len(agents)*(len(agents)-1)} possible.", ""]
    return L



def s7b_pair_chronology(L, data, extra):
    """For every pair: every exposure, in order, and what happened at each one.

    "A saw B 30 times" is a summary. This is the 30 rows behind it -- which
    post, which round, what score put it there, which route delivered it, and
    what A actually did at that moment. This is where a claim about influence
    either holds up or falls apart.
    """
    L += [RULE, "SECTION 7B -- PAIR CHRONOLOGIES (every exposure, one by one)",
          RULE, "",
          "    Read as: viewer -> author. Each row is ONE exposure event.",
          "    'did' is what the viewer did to THAT post in THAT round.",
          "    A FOLLOW line is placed in the round the edge was created.", ""]
    agents, posts = data["agents"], data["posts"]
    comments = extra["comments"]

    def name(i):
        a = agents.get(i) or agents.get(str(i)) or {}
        return a.get("username", f"agent{i}" if i is not None else "?")

    # (agent, round, post) -> [actions]; and (agent, round) -> follow targets
    acted = defaultdict(list)
    followed = defaultdict(list)
    for e in data["events"]:
        if e.get("post_id") is not None:
            acted[(e["agent_id"], e["round"], e["post_id"])].append(e)
        if e["action"] in ("follow", "unfollow", "mute") and \
                e.get("target_agent_id") is not None:
            followed[(e["agent_id"], e["round"])].append(e)

    pairs = defaultdict(list)
    for ex in data["exposures"]:
        if ex.get("author_id") is None or ex["author_id"] == ex["agent_id"]:
            continue
        pairs[(ex["agent_id"], ex["author_id"])].append(ex)

    ordered = sorted(pairs.items(), key=lambda kv: -len(kv[1]))
    L += [f"    {len(ordered)} ordered pairs had at least one exposure.", ""]

    for (viewer, author), evs in ordered:
        inter = data["interaction_pairs"].get(f"{viewer}->{author}", {})
        n_acts = sum(inter.values())
        L += [SUB,
              f"@{name(viewer)}  ->  @{name(author)}    "
              f"saw {len(evs)}x, acted {n_acts}x"
              f"{'  [' + ', '.join(f'{k}x{v}' for k, v in inter.items()) + ']' if inter else ''}"]
        for ex in sorted(evs, key=lambda x: (x["round"],
                                             x.get("feed_position") or 0)):
            pid = ex["post_id"]
            body = str((posts.get(pid) or {}).get("content", ""))[:52]
            sc = ex.get("score")
            did = acted.get((viewer, ex["round"], pid), [])
            if did:
                labels = []
                for d in did:
                    if d["action"] == "create_comment":
                        cid = (d.get("info") or {}).get("comment_id")
                        txt = (comments.get(cid) or {}).get("content", "")
                        labels.append(f'COMMENTED: "{str(txt)[:46]}"')
                    else:
                        labels.append(d["action"].upper())
                what = " + ".join(labels)
            else:
                what = "-- no action"
            L += [f"      r{ex['round']:<3} post #{pid:<5} "
                  f"{(f'{sc:.4f}' if isinstance(sc,(int,float)) else '  -   '):<8}"
                  f"via {str(ex.get('source','')):<10} \"{body}\"",
                  f"           {what}"]
        # follow events toward this author, placed in their round
        for (v, r), evl in followed.items():
            if v != viewer:
                continue
            for e in evl:
                if e["target_agent_id"] == author:
                    L += [f"      r{r:<3} >>> {e['action'].upper()} "
                          f"@{name(author)} <<<"]
        L += [""]
    return L


def s8_propagation(L, data):
    L += [RULE, "SECTION 8 -- PROPAGATION", RULE, "",
          "    Repeated exposure preceding interaction. This is the mechanism the",
          "    simulation exists to observe: A keeps being shown B's content and",
          "    eventually acts on B. Reported as evidence, not proof of causation --",
          "    exposure preceding interaction is necessary for the story, not",
          "    sufficient to establish it.", ""]
    agents = data["agents"]

    def name(i):
        a = agents.get(i) or agents.get(str(i)) or {}
        return a.get("username", f"agent{i}")

    for p in data["propagation_candidates"]:
        L += [f"    @{name(p['actor']):<24} saw @{name(p['target']):<24}"
              f"{p['times_actor_saw_target']:>3}x  ->  "
              f"{', '.join(f'{k}x{v}' for k, v in p['interactions'].items())}"]
    L += [""]
    return L


def s9_feed(L, data):
    L += [RULE, "SECTION 9 -- FEED COMPOSITION", RULE, ""]
    src = Counter(e.get("source") for e in data["exposures"])
    total = sum(src.values()) or 1
    L += ["    Where every exposure came from across the whole run:"]
    for k, v in src.most_common():
        L += [f"      {k:<12} {v:>6}  {v/total*100:5.1f}%"]
    L += ["",
          "      recsys    = the ranking algorithm chose it",
          "      following = the viewer follows the author",
          "      both      = it qualified through both routes", ""]
    per_agent_pools = defaultdict(set)
    for e in data["exposures"]:
        per_agent_pools[e["agent_id"]].add(e["post_id"])
    if per_agent_pools:
        sizes = [len(v) for v in per_agent_pools.values()]
        distinct = len({frozenset(v) for v in per_agent_pools.values()})
        L += [f"    Distinct feeds: {distinct} of {len(per_agent_pools)} agents saw a",
              f"    different set of posts.",
              f"    Posts seen per agent: min {min(sizes)}, median "
              f"{int(statistics.median(sizes))}, max {max(sizes)}",
              "",
              "    If 'distinct feeds' equals the agent count, personalisation is",
              "    real: no two people are looking at the same timeline. If it is 1,",
              "    everyone shares one global feed.", ""]
    return L


def s10_failures(L, data, manifest=None):
    L += [RULE, "SECTION 10 -- FAILURES AND LIMITS", RULE, ""]

    stats = (manifest or {}).get("platform_stats") or {}
    if stats:
        L += ["    INTEGRITY COUNTERS", "",
              "    These exist so that a degraded run cannot look like a clean",
              "    one. Every value below is a thing that would otherwise have",
              "    been invisible in the results.", ""]
        explain = {
            "blind_actions_rejected":
                "actions aimed at a post or person the agent had never been "
                "shown. Rejected: on a real platform you cannot like "
                "something you never encountered (F-19)",
            "invalid_follow_targets":
                "follows aimed at an agent id that does not exist -- the "
                "model inventing a plausible number (B-10)",
            "refresh_errors":
                "feed builds that threw. Upstream swallows these silently, so "
                "they are counted here (B-11)",
            "empty_feeds":
                "feeds that were legitimately empty -- round 0 before anyone "
                "has posted, or an agent whose only visible posts are its own",
            "recency_clamped":
                "posts older than the recency curve can express",
            "empty_candidate_pools":
                "agents with nothing rankable that round",
            "exposures_logged": "total exposure events recorded",
            "refresh_calls": "successful feed builds",
            "rounds_ranked": "rounds where ranking ran",
            "dm_joins_refused":
                "attempts to join a 2-member group, refused to keep emergent "
                "private conversation private (D-7)",
        }
        for k, v in stats.items():
            L += [f"    {k:<26} {v}"]
            if k in explain and v:
                L += [wrap(explain[k], indent="        ")]
        L += [""]
    tce = data.get("tool_call_errors")
    if tce:
        L += [f"    Malformed tool calls: {tce['total']}",
              "    These are actions the model CHOSE and then mis-called. They leave",
              "    no trace row, so without this accounting they are indistinguishable",
              "    from an agent deciding to do nothing. Every one is a lost action.",
              "", "    by action:"]
        for k, v in tce["by_action"].items():
            L += [f"      {k:<24} {v}"]
        L += ["", "    by reason:"]
        for k, v in tce["by_reason"].items():
            L += [f"      {k:<44} {v}"]
    unattributed = [e for e in data["events"]
                    if e.get("target_agent_id") is None
                    and e["action"] not in ("create_post", "do_nothing",
                                            "search_posts", "search_user",
                                            "trend", "refresh")]
    L += ["", f"    Actions with no resolvable target: {len(unattributed)}"]
    for e in unattributed[:15]:
        L += [f"      r{e['round']} agent {e['agent_id']} {e['action']} "
              f"info={e.get('info')}"]
    L += [""]
    return L


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True)
    ap.add_argument("--log", default=None)
    ap.add_argument("--personas", default="data/reddit/user_data_36.json")
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    data, extra, personas, manifest = build(args.db, args.log, args.personas,
                                            args.manifest)
    L = []
    L += ["SIMULATION 4 -- FULL DOSSIER",
          f"database: {os.path.basename(args.db)}",
          f"agents: {data['n_agents']}   rounds: {data['n_rounds']}   "
          f"posts: {data['totals']['posts']}   "
          f"actions: {data['totals']['actions_chosen']}   "
          f"exposures: {data['totals']['exposure_events']}   "
          f"follow edges: {data['totals']['follow_edges']}", ""]
    L = s0_provenance(L, data, manifest, args.personas, args.db)
    L = s1_population(L, personas, data)
    L = s2_timeline(L, data, extra)
    L = s3_network(L, data)
    L = s4_agents(L, data, extra, personas)
    L = s5_posts(L, data, extra)
    L = s6_threads(L, data, extra)
    L = s7_matrix(L, data)
    L = s7b_pair_chronology(L, data, extra)
    L = s8_propagation(L, data)
    L = s9_feed(L, data)
    L = s10_failures(L, data, manifest)

    out = args.out or args.db.replace(".db", "_DOSSIER.txt")
    text = "\n".join(L)
    with open(out, "w") as fh:
        fh.write(text)
    print(f"wrote {out}  ({len(text)/1024:.0f} KB, {len(L)} lines)")


if __name__ == "__main__":
    main()
