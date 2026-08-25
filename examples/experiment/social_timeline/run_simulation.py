"""Simulation 4 driver: a multi-round, fully-instrumented social timeline.

Every agent acts every round via LLMAction only -- no ManualAction anywhere,
no scripted posts, no staged relationships (decisions D-6 and D-10). The
social graph starts empty and assembles itself out of agent choices.

Usage (start small -- decision D-11, no full runs until small ones are clean):

    oasis-env/bin/python examples/experiment/social_timeline/run_simulation.py \
        --agents 4 --rounds 2 --label stage1-plumbing

Writes:
    data/social_timeline_<label>.db    simulation + instrumentation tables
    data/social_timeline_<label>.json  run manifest (exact config, versions,
                                       timings, counters, action tallies)

The manifest exists so that every run is self-describing after the fact and
no result has to be reconstructed from memory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import platform as py_platform
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("social_timeline.run")


# ---------------------------------------------------------------- action set

def build_action_set(include_groups: bool = True):
    """The action set agents may choose from (decision D-4).

    `include_groups=False` drops the 5 group-chat actions, leaving 22.

    Why that switch exists: `SocialEnvironment.env_template` places
    `$groups_env` BEFORE `$posts_env`, and the group block is a wall of
    imperative instructions ("You can join the groups you are interested...",
    "You must make sure..."). `to_text_prompt()` renders it on every turn
    regardless of available_actions (agent_environment.py:118-135). Once any
    group exists, every agent's prompt opens with group instructions and group
    messages, burying the feed -- and each new group message makes the next
    prompt more group-heavy still. Measured in R-5; see SIM4_BUILD_LOG.md F-14.

    ActionType has 30 members. Excluded, with cause:
      EXIT, SIGNUP, UPDATE_REC_TABLE -- internal plumbing, not user behaviour.
      PURCHASE_PRODUCT              -- needs the e-commerce product table.
      INTERVIEW                     -- an externally injected researcher
                                       probe; including it would contaminate
                                       the free-behaviour requirement (D-6).
    """
    from oasis.social_platform.typing import ActionType

    social = [
        ActionType.CREATE_POST, ActionType.CREATE_COMMENT,
        ActionType.LIKE_POST, ActionType.UNLIKE_POST,
        ActionType.DISLIKE_POST, ActionType.UNDO_DISLIKE_POST,
        ActionType.LIKE_COMMENT, ActionType.UNLIKE_COMMENT,
        ActionType.DISLIKE_COMMENT, ActionType.UNDO_DISLIKE_COMMENT,
        ActionType.REPOST, ActionType.QUOTE_POST, ActionType.REPORT_POST,
        ActionType.FOLLOW, ActionType.UNFOLLOW,
        ActionType.MUTE, ActionType.UNMUTE,
        ActionType.SEARCH_USER, ActionType.SEARCH_POSTS,
        ActionType.TREND, ActionType.REFRESH, ActionType.DO_NOTHING,
    ]
    group = [
        ActionType.CREATE_GROUP, ActionType.JOIN_GROUP,
        ActionType.LEAVE_GROUP, ActionType.SEND_TO_GROUP,
        ActionType.LISTEN_FROM_GROUP,
    ]
    actions = social + group if include_groups else social
    expected = 27 if include_groups else 22
    assert len(actions) == expected, \
        f"expected {expected} actions, got {len(actions)}"
    return actions


# --------------------------------------------------------------------- main

async def run(args):
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType

    import oasis
    from oasis import LLMAction
    from oasis.social_platform.channel import Channel

    from timeline_agent import generate_timeline_agents
    from timeline_platform import TimelinePlatform

    db_path = os.path.join(REPO_ROOT, "data",
                           f"social_timeline_{args.label}.db")
    manifest_path = db_path.replace(".db", ".json")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        log.info("removing previous database %s", db_path)
        os.remove(db_path)
    os.environ["OASIS_DB_PATH"] = db_path

    # Local Ollama. llama3.1:8b is required specifically for native
    # tool-calling -- OASIS agents act by emitting tool calls, not free text.
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OLLAMA,
        model_type=args.model,
        url=args.ollama_url,
    )

    actions = build_action_set(include_groups=not args.no_groups)
    agent_graph = await generate_timeline_agents(
        profile_path=os.path.join(REPO_ROOT, args.personas),
        model=model,
        available_actions=actions,
        limit=args.agents,
    )
    n_agents = len(list(agent_graph.get_agents()))
    log.info("built %d agents with %d available actions", n_agents,
             len(actions))

    sim_platform = TimelinePlatform(
        db_path=db_path,
        channel=Channel(),
        recsys_type=args.recsys,
        # Raised well above the ~5-post upstream default (finding F-5), but
        # kept moderate: the feed dominates the prompt, and Sim 1 showed 8B
        # tool-calling degrades as prompts grow.
        max_rec_post_len=args.max_rec_post_len,
        refresh_rec_post_count=args.refresh_rec_post_count,
        following_post_count=args.following_post_count,
        allow_self_rating=False,
        show_score=False,
    )

    env = oasis.make(
        agent_graph=agent_graph,
        platform=sim_platform,
        database_path=db_path,
        # Local Ollama serialises anyway; high concurrency mainly produces
        # timeouts, which is how Sim 3 lost a run.
        semaphore=args.semaphore,
    )

    manifest = {
        "label": args.label,
        "started_at": datetime.now().isoformat(),
        "config": {
            "agents": n_agents,
            "rounds": args.rounds,
            "recsys": args.recsys,
            "model": args.model,
            "semaphore": args.semaphore,
            "max_rec_post_len": args.max_rec_post_len,
            "refresh_rec_post_count": args.refresh_rec_post_count,
            "following_post_count": args.following_post_count,
            "personas": args.personas,
            "n_actions": len(actions),
            "actions": [a.value for a in actions],
        },
        "algorithm": {
            "name": "TWHIN interest-based (TimelinePlatform implementation)",
            "formula": ("score(u,p) = cosine(embed(profile_u), "
                        "embed(content_p)) * log((271.8 - age_p)/100)"),
            "embedding": "Twitter/twhin-bert-base, mean-pooled "
                         "last_hidden_state",
            "deviations_from_upstream": [
                "mean-pooled last_hidden_state instead of pooler_output "
                "(bugs B-1/B-2: upstream pooler weights are randomly "
                "re-initialised every process, making runs unreplicable "
                "and near-non-discriminative)",
                "per-(user,post) scores captured for rec_history",
            ],
            "initial_follow_edges": 0,
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": py_platform.platform(),
            "ollama_keep_alive": os.environ.get("OLLAMA_KEEP_ALIVE",
                                                "(unset)"),
        },
        "rounds": [],
    }

    log.info("resetting environment (signing up %d agents)", n_agents)
    await env.reset()

    t_start = time.time()
    try:
        for round_no in range(args.rounds):
            t_round = time.time()
            actions_map = {
                agent: LLMAction()
                for _, agent in env.agent_graph.get_agents()
            }
            await env.step(actions_map)
            elapsed = time.time() - t_round

            counts = snapshot_counts(sim_platform)
            failures = sum(getattr(a, "action_failures", 0)
                           for _, a in env.agent_graph.get_agents())
            manifest["rounds"].append({
                "round": round_no,
                "seconds": round(elapsed, 1),
                "cumulative_agent_failures": failures,
                **counts,
            })
            log.info("round %d done in %.1fs | %s | agent failures: %d",
                     round_no, elapsed,
                     " ".join(f"{k}={v}" for k, v in counts.items()),
                     failures)

        # Bug B-3: these MUST be read before env.close(), which closes the
        # database cursor (platform.py:143-144 on ActionType.EXIT). Reading
        # them afterwards silently yielded None and "Cannot operate on a
        # closed cursor" instead of failing.
        manifest["final_counts"] = snapshot_counts(sim_platform)
        manifest["action_tally"] = action_tally(sim_platform)
        manifest["turns_without_action"] = turns_without_action(
            sim_platform, n_agents, args.rounds)
    finally:
        await env.close()

    manifest["total_seconds"] = round(time.time() - t_start, 1)
    manifest["platform_stats"] = sim_platform.stats
    manifest["finished_at"] = datetime.now().isoformat()

    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)

    log.info("=" * 66)
    log.info("run complete in %.1fs", manifest["total_seconds"])
    log.info("database: %s", db_path)
    log.info("manifest: %s", manifest_path)
    log.info("platform stats: %s", sim_platform.stats)
    log.info("final counts: %s", manifest["final_counts"])
    log.info("actions performed: %s", manifest["action_tally"])
    log.info("=" * 66)


def snapshot_counts(sim_platform):
    """Row counts for the tables that matter, straight from the database."""
    cur = sim_platform.db_cursor
    out = {}
    for table in ("post", "comment", "follow", "like", "dislike",
                  "rec_history", "rec_candidates", "chat_group",
                  "group_members", "group_messages"):
        try:
            cur.execute(f"SELECT COUNT(*) FROM `{table}`")
            out[table] = cur.fetchone()[0]
        except Exception:
            out[table] = None
    return out


def action_tally(sim_platform):
    """How many times each action actually succeeded, from the trace table.

    This is the headline health metric: if agents are only doing one or two
    action types, the 27-action set is not really being exercised.
    """
    cur = sim_platform.db_cursor
    try:
        cur.execute("SELECT action, COUNT(*) FROM trace "
                    "GROUP BY action ORDER BY COUNT(*) DESC")
        return {row[0]: row[1] for row in cur.fetchall()}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def turns_without_action(sim_platform, n_agents, n_rounds):
    """Tool-calling health: agent-turns that produced no action at all.

    Sim 1's baseline for comparison was ~32/36 agents performing a real
    action per round (~89%). A sharp drop here would indicate the 27-action
    set is overloading the 8B model's tool-calling (question Q-2).

    `sign_up` and `refresh` are excluded because they are automatic --
    refresh is invoked by get_posts_env() on every turn regardless of what
    the agent decides. Caveat: an agent that deliberately chooses REFRESH as
    its action is therefore counted as having done nothing, which slightly
    over-reports the miss rate.

    Note that `do_nothing` DOES leave a trace row (platform.py:1332-1344), so
    an agent choosing to do nothing is correctly distinguished here from an
    agent that failed to emit a tool call at all.
    """
    cur = sim_platform.db_cursor
    try:
        cur.execute(
            "SELECT COUNT(DISTINCT created_at || '|' || user_id) FROM trace "
            "WHERE action NOT IN ('sign_up', 'refresh')")
        acted = cur.fetchone()[0]
        total = n_agents * n_rounds
        return {
            "agent_turns_total": total,
            "turns_with_action": acted,
            "turns_without_action": total - acted,
            "action_rate": round(acted / total, 3) if total else None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--agents", type=int, default=4,
                   help="number of agents (default 4 -- start small)")
    p.add_argument("--rounds", type=int, default=2,
                   help="simulation rounds (default 2)")
    p.add_argument("--label", default="smoke",
                   help="run label; names the db and manifest")
    p.add_argument("--recsys", default="twhin-bert",
                   choices=["twhin-bert", "reddit", "random"],
                   help="recommendation algorithm (default twhin-bert, "
                        "the interest-based one)")
    p.add_argument("--model", default="llama3.1:8b")
    p.add_argument("--ollama-url", default="http://localhost:11434/v1")
    p.add_argument("--personas", default="data/reddit/user_data_36.json")
    p.add_argument("--no-groups", action="store_true",
                   help="drop the 5 group-chat actions (22 instead of 27). "
                        "Group instructions are injected into every prompt "
                        "ahead of the feed and crowd out content engagement "
                        "-- see finding F-14.")
    p.add_argument("--semaphore", type=int, default=4,
                   help="max concurrent LLM calls (default 4; local Ollama "
                        "serialises and high concurrency causes timeouts)")
    p.add_argument("--max-rec-post-len", type=int, default=30,
                   dest="max_rec_post_len")
    p.add_argument("--refresh-rec-post-count", type=int, default=8,
                   dest="refresh_rec_post_count")
    p.add_argument("--following-post-count", type=int, default=4,
                   dest="following_post_count")
    args = p.parse_args()

    if "OLLAMA_KEEP_ALIVE" not in os.environ:
        log.warning("OLLAMA_KEEP_ALIVE is unset. Runs have multi-minute gaps "
                    "between LLM bursts and the default 5m unload made "
                    "earlier simulations 3-4x slower. Consider "
                    "OLLAMA_KEEP_ALIVE=60m (decision D-5).")

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
