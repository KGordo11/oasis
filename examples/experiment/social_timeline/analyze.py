"""Analysis for Simulation 4: the micro-detail ledger.

Answers, for every agent and every pair of agents:

  * exactly what each agent did, how many times, and to whom
  * which posts each agent SAW, and by which mechanism they arrived
  * which seen posts they acted on, and which they saw and ignored
  * which posts they never saw at all
  * how OFTEN each agent was exposed to each other agent's content
  * who followed whom, and when the edge appeared
  * the follow graph before and after, and at every round between

Reads only the database written by run_simulation.py. Emits a JSON blob
(everything, for the graph artifact and further analysis) and a readable text
report.

Usage:
    oasis-env/bin/python examples/experiment/social_timeline/analyze.py \
        --db data/social_timeline_stage2.db
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from collections import Counter, defaultdict

# Actions that are automatic rather than chosen, excluded from behaviour
# tallies. `refresh` is invoked by get_posts_env() on every turn regardless of
# what the agent decides; `sign_up` happens once at reset.
AUTOMATIC = {"sign_up", "refresh"}

# Where in a trace `info` payload a target post/user id may appear.
#
# Bug B-4: these payloads are NOT uniform across action types, and assuming
# they were silently dropped real engagement from the ledger:
#   create_comment -> {"content", "comment_id"}   -- no post_id at all; the
#                     post is only reachable via the comment table
#   quote_post     -> {"quoted_id": "1", ...}     -- a STRING, not an int
#   repost         -> {"original_post_id", ...}
# Hence the numeric-string coercion below and the comment_id back-reference.
POST_KEYS = ("post_id", "original_post_id", "quoted_id", "quoted_post_id")
USER_KEYS = ("followee_id", "target_id")


def coerce_int(value):
    """Return an int for 3 or "3", else None. Trace payloads mix both."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def load_agents(conn):
    """agent_id -> identity. Note user.user_id is NOT agent_id (finding F-13);
    every other table keys on agent_id."""
    out = {}
    for row in conn.execute(
            "SELECT user_id, agent_id, user_name, name, bio FROM user"):
        out[row["agent_id"]] = {
            "agent_id": row["agent_id"],
            "db_user_id": row["user_id"],
            "username": row["user_name"] or row["name"],
            "bio": row["bio"],
        }
    return out


def load_posts(conn):
    out = {}
    for row in conn.execute(
            "SELECT post_id, user_id, original_post_id, content, "
            "quote_content, created_at, num_likes, num_dislikes, num_shares "
            "FROM post"):
        out[row["post_id"]] = {
            "post_id": row["post_id"],
            "author_id": row["user_id"],          # agent_id, per F-13
            "original_post_id": row["original_post_id"],
            "content": row["content"],
            "quote_content": row["quote_content"],
            "round": safe_int(row["created_at"]),
            "num_likes": row["num_likes"],
            "num_dislikes": row["num_dislikes"],
            "num_shares": row["num_shares"],
        }
    return out


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_comment_targets(conn):
    """comment_id -> post_id.

    Needed because a create_comment trace records only `comment_id`, so the
    post that was actually commented on can be recovered only through the
    comment table (bug B-4).
    """
    out = {}
    for row in conn.execute("SELECT comment_id, post_id FROM comment"):
        out[row["comment_id"]] = row["post_id"]
    return out


def load_actions(conn, posts):
    """Every chosen action, with its target resolved where one exists.

    Targets are pulled from the trace `info` JSON generically so this covers
    all action types, with the per-action irregularities documented at
    POST_KEYS handled explicitly.
    """
    comment_targets = load_comment_targets(conn)
    actions = []
    for row in conn.execute(
            "SELECT user_id, created_at, action, info FROM trace "
            "ORDER BY created_at, user_id"):
        if row["action"] in AUTOMATIC:
            continue
        try:
            info = json.loads(row["info"]) if row["info"] else {}
        except (json.JSONDecodeError, TypeError):
            info = {}
        if not isinstance(info, dict):
            info = {}

        post_id = next(
            (coerce_int(info[k]) for k in POST_KEYS
             if coerce_int(info.get(k)) is not None), None)

        # A comment names only its own comment_id, so the commented-on post
        # has to be looked up (B-4).
        if post_id is None and row["action"] == "create_comment":
            post_id = comment_targets.get(coerce_int(info.get("comment_id")))

        target_user = next(
            (coerce_int(info[k]) for k in USER_KEYS
             if coerce_int(info.get(k)) is not None), None)
        # Acting on a post is implicitly an interaction with its author.
        if target_user is None and post_id in posts:
            target_user = posts[post_id]["author_id"]

        actions.append({
            "agent_id": row["user_id"],
            "round": safe_int(row["created_at"]),
            "action": row["action"],
            "post_id": post_id,
            "target_agent_id": target_user,
            "info": info,
        })
    return actions


def load_exposures(conn):
    rows = []
    try:
        cur = conn.execute(
            "SELECT round, agent_id, post_id, author_id, feed_position, "
            "source, score FROM rec_history ORDER BY round, agent_id, "
            "feed_position")
    except sqlite3.OperationalError:
        return rows
    for row in cur:
        rows.append(dict(row))
    return rows


def load_follow_timeline(conn):
    """Follow edges with the round they appeared, so the graph can be
    reconstructed at any point in time. `follow.created_at` holds the round."""
    edges = []
    for row in conn.execute(
            "SELECT follower_id, followee_id, created_at FROM follow"):
        edges.append({
            "follower": row["follower_id"],
            "followee": row["followee_id"],
            "round": safe_int(row["created_at"]),
        })
    return edges


def analyze(db_path):
    conn = connect(db_path)
    agents = load_agents(conn)
    posts = load_posts(conn)
    actions = load_actions(conn, posts)
    exposures = load_exposures(conn)
    follows = load_follow_timeline(conn)

    rounds = [r["round"] for r in conn.execute(
        "SELECT round FROM round_boundary ORDER BY round")] or [0]
    max_round = max(rounds)

    # ---- what each agent saw, and whether they acted on it ---------------
    # (agent, post) -> list of exposure events. Repeat exposures are kept
    # separate because how OFTEN someone sees content is the mechanism this
    # simulation exists to study.
    seen = defaultdict(list)
    for e in exposures:
        seen[(e["agent_id"], e["post_id"])].append(e)

    acted_on = defaultdict(set)   # agent -> {post_id}
    for a in actions:
        if a["post_id"] is not None:
            acted_on[a["agent_id"]].add(a["post_id"])

    # ---- pairwise ledgers -------------------------------------------------
    exposure_pairs = Counter()    # (viewer, author) -> times viewer saw author
    for e in exposures:
        if e["author_id"] is not None and e["author_id"] != e["agent_id"]:
            exposure_pairs[(e["agent_id"], e["author_id"])] += 1

    interaction_pairs = defaultdict(Counter)  # (actor, target) -> {action: n}
    for a in actions:
        tgt = a["target_agent_id"]
        if tgt is not None and tgt != a["agent_id"]:
            interaction_pairs[(a["agent_id"], tgt)][a["action"]] += 1

    # ---- per-agent detail -------------------------------------------------
    per_agent = {}
    for agent_id, identity in sorted(agents.items()):
        own_posts = [p for p in posts.values() if p["author_id"] == agent_id]
        my_exposures = [e for e in exposures if e["agent_id"] == agent_id]
        seen_post_ids = {e["post_id"] for e in my_exposures}
        acted = acted_on.get(agent_id, set())

        seen_and_acted = sorted(seen_post_ids & acted)
        seen_and_ignored = sorted(seen_post_ids - acted)
        # "Never seen" counts only posts that existed and were not their own.
        never_seen = sorted(
            pid for pid, p in posts.items()
            if pid not in seen_post_ids and p["author_id"] != agent_id)

        my_actions = [a for a in actions if a["agent_id"] == agent_id]
        by_round = defaultdict(list)
        for a in my_actions:
            by_round[a["round"]].append(a["action"])

        per_agent[agent_id] = {
            **identity,
            "action_counts": dict(Counter(a["action"] for a in my_actions)),
            "total_actions": len(my_actions),
            "actions_by_round": {r: sorted(v) for r, v in sorted(by_round.items())},
            "posts_authored": [p["post_id"] for p in own_posts],
            "n_posts_authored": len(own_posts),
            "exposure_events": len(my_exposures),
            "distinct_posts_seen": len(seen_post_ids),
            "seen_and_acted": seen_and_acted,
            "seen_and_ignored": seen_and_ignored,
            "never_seen": never_seen,
            "engagement_rate": (round(len(seen_and_acted) / len(seen_post_ids), 3)
                                if seen_post_ids else None),
            "exposure_by_source": dict(Counter(
                e["source"] for e in my_exposures)),
            "following": sorted({f["followee"] for f in follows
                                 if f["follower"] == agent_id}),
            "followers": sorted({f["follower"] for f in follows
                                 if f["followee"] == agent_id}),
            "saw_authors": {str(author): n for (v, author), n
                            in exposure_pairs.items() if v == agent_id},
            "interacted_with": {
                str(tgt): dict(counts)
                for (actor, tgt), counts in interaction_pairs.items()
                if actor == agent_id},
            "interacted_by": {
                str(actor): dict(counts)
                for (actor, tgt), counts in interaction_pairs.items()
                if tgt == agent_id},
        }

    # ---- graph snapshots, before and after --------------------------------
    snapshots = {}
    for r in range(max_round + 1):
        snapshots[r] = sorted(
            [f["follower"], f["followee"]] for f in follows if f["round"] <= r)

    result = {
        "database": os.path.basename(db_path),
        "n_agents": len(agents),
        "n_rounds": max_round + 1,
        "totals": {
            "posts": len(posts),
            "actions_chosen": len(actions),
            "exposure_events": len(exposures),
            "follow_edges": len(follows),
            "action_counts": dict(Counter(a["action"] for a in actions)),
        },
        "graph_before": snapshots.get(0, []),
        "graph_after": snapshots.get(max_round, []),
        "graph_by_round": snapshots,
        "agents": per_agent,
        "posts": posts,
        "exposure_pairs": {f"{v}->{a}": n
                           for (v, a), n in exposure_pairs.most_common()},
        "interaction_pairs": {f"{a}->{t}": dict(c)
                              for (a, t), c in interaction_pairs.items()},
        "propagation_candidates": find_propagation(exposure_pairs,
                                                   interaction_pairs),
    }
    conn.close()
    return result


def find_propagation(exposure_pairs, interaction_pairs):
    """Cases where repeated exposure preceded an interaction.

    This is the mechanism the simulation was built to observe: A keeps seeing
    B's content, and eventually acts on B. Reported as *candidates* and not as
    proven causation -- exposure preceding interaction is necessary evidence
    for the story, not sufficient proof of it.
    """
    out = []
    for (actor, target), counts in interaction_pairs.items():
        exposures = exposure_pairs.get((actor, target), 0)
        if exposures > 0:
            out.append({
                "actor": actor,
                "target": target,
                "times_actor_saw_target": exposures,
                "interactions": dict(counts),
                "total_interactions": sum(counts.values()),
            })
    out.sort(key=lambda d: (-d["times_actor_saw_target"],
                            -d["total_interactions"]))
    return out


def render_report(data):
    L = []
    add = L.append
    add("=" * 74)
    add(f"SIMULATION 4 ANALYSIS -- {data['database']}")
    add("=" * 74)
    t = data["totals"]
    add(f"agents={data['n_agents']}  rounds={data['n_rounds']}  "
        f"posts={t['posts']}  chosen actions={t['actions_chosen']}  "
        f"exposure events={t['exposure_events']}  "
        f"follow edges={t['follow_edges']}")
    add("")
    add("ACTION MIX (chosen actions only; refresh/sign_up excluded)")
    if t["action_counts"]:
        for action, n in sorted(t["action_counts"].items(),
                                key=lambda kv: -kv[1]):
            add(f"  {action:<24} {n}")
    else:
        add("  (none)")
    add("")
    add(f"SOCIAL GRAPH: {len(data['graph_before'])} edges before -> "
        f"{len(data['graph_after'])} edges after")
    add("")

    add("-" * 74)
    add("PER-AGENT DETAIL")
    add("-" * 74)
    for agent_id, a in sorted(data["agents"].items(),
                              key=lambda kv: int(kv[0])):
        add(f"\n[agent {agent_id}] @{a['username']}")
        add(f"  bio: {(a['bio'] or '')[:88]}")
        add(f"  actions ({a['total_actions']}): "
            f"{a['action_counts'] or '(none)'}")
        add(f"  authored {a['n_posts_authored']} posts: {a['posts_authored']}")
        add(f"  saw {a['distinct_posts_seen']} distinct posts across "
            f"{a['exposure_events']} exposure events "
            f"(by source: {a['exposure_by_source'] or '{}'})")
        add(f"    acted on : {a['seen_and_acted']}")
        add(f"    ignored  : {a['seen_and_ignored']}")
        add(f"    never saw: {a['never_seen']}")
        add(f"  engagement rate (acted / seen): {a['engagement_rate']}")
        add(f"  follows {a['following']} | followed by {a['followers']}")
        if a["saw_authors"]:
            top = sorted(a["saw_authors"].items(), key=lambda kv: -kv[1])
            add("  exposure to others: "
                + ", ".join(f"agent {k} x{v}" for k, v in top))
        if a["interacted_with"]:
            add(f"  acted on others: {a['interacted_with']}")
        if a["interacted_by"]:
            add(f"  acted on by    : {a['interacted_by']}")

    add("")
    add("-" * 74)
    add("PROPAGATION CANDIDATES (repeated exposure preceding interaction)")
    add("-" * 74)
    if data["propagation_candidates"]:
        for p in data["propagation_candidates"][:25]:
            add(f"  agent {p['actor']} saw agent {p['target']} "
                f"x{p['times_actor_saw_target']} -> {p['interactions']}")
    else:
        add("  (none observed)")
    add("")
    return "\n".join(L)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", required=True)
    p.add_argument("--out", default=None,
                   help="JSON output path (default: alongside the db)")
    args = p.parse_args()

    data = analyze(args.db)
    out = args.out or args.db.replace(".db", "_analysis.json")
    with open(out, "w") as fh:
        json.dump(data, fh, indent=2, default=str)

    report = render_report(data)
    print(report)
    with open(out.replace(".json", ".txt"), "w") as fh:
        fh.write(report)
    print(f"\nwrote {out}")
    print(f"wrote {out.replace('.json', '.txt')}")


if __name__ == "__main__":
    main()
