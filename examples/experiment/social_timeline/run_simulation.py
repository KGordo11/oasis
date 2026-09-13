"""Simulation 4 driver: a multi-round, fully-instrumented social timeline.

IN PLAIN WORDS
--------------
This is the START BUTTON for the whole simulation.

You run this file and it does everything: it wakes up 36 pretend people, gives
each one a personality, builds them a social media feed, lets them take turns
posting and reading for 15 rounds, and saves everything that happened into one
file so it can be studied afterwards.

Think of it as the director of a play. It does not act; it tells everyone else
when to go.

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

def build_action_set(include_groups: bool = True, lean: bool = False):
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
    if lean:
        # Q-21. F-48 established that eight of the 22 never fire in any of the
        # nine analysed runs -- every one a mute, a trend lookup, or an undo.
        # Their schemas still cost ~980 prompt tokens on every single turn, and
        # F-55 measured prefill at ~25% of a turn, so this is the one prompt
        # reduction that should cost nothing behaviourally.
        #
        # "Should" is doing work in that sentence. An agent that COULD have
        # muted and now cannot is a different agent, and "never observed in
        # nine runs" is not "impossible". This flag exists to MEASURE the
        # difference, not to become the default.
        never_fired = {
            ActionType.MUTE, ActionType.UNMUTE, ActionType.TREND,
            ActionType.DISLIKE_COMMENT, ActionType.UNLIKE_POST,
            ActionType.UNLIKE_COMMENT, ActionType.UNDO_DISLIKE_POST,
            ActionType.UNDO_DISLIKE_COMMENT,
        }
        social = [a for a in social if a not in never_fired]

    actions = social + group if include_groups else social
    expected = (27 if include_groups else 22) - (8 if lean else 0)
    assert len(actions) == expected, \
        f"expected {expected} actions, got {len(actions)}"
    return actions


# --------------------------------------------------------------------- main

async def run(args):
    """Run the whole simulation: build the world, then step it round by round."""
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType

    import oasis
    from oasis import LLMAction
    from oasis.social_platform.channel import Channel

    import server_state

    from timeline_agent import PROMPT_VERSION, generate_timeline_agents
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
    # Reproducibility. Nothing in this project had ever set a sampling
    # temperature, so run-to-run variation came from an unstated source. It is
    # now explicit and recorded in the manifest. Seeding Python's RNG also
    # pins the feed's exploration slots (F-17); the model's own sampling stays
    # stochastic, which is why replication still means repeating a run rather
    # than expecting identical output.
    import random as _random
    _random.seed(args.seed)
    # B-22: a per-request timeout. Without one, a single request that never
    # returns blocks the whole run forever -- measured on 2026-09-05, when the
    # `full_3b` run hung at 18:52:43 and sat at 0.2% CPU for TWENTY-FOUR HOURS
    # waiting on a socket, having completed only round 0. Nothing detected it;
    # the process was alive, the server was responsive, and the run was simply
    # never going to finish.
    #
    # This is the same failure class as B-12 and B-15: a silent stall is
    # indistinguishable from slow progress unless something is watching. A
    # timeout converts it into a counted agent failure, which the round loop
    # already handles and reports.
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OLLAMA,
        model_type=args.model,
        url=args.ollama_url,
        model_config_dict={"temperature": args.temperature,
                           "timeout": args.request_timeout,
                           # Q-22. camel defaults max_tokens to 999_999_999,
                           # i.e. no cap. Decode is ~96% of a turn (F-55) and a
                           # real action carries a median 48 tokens of content,
                           # so a runaway generation is pure loss with no
                           # experimental value. Capping bounds the worst case;
                           # it is a condition, not a free win, so it is
                           # recorded in the manifest and screened before use.
                           "max_tokens": args.max_tokens},
    )

    actions = build_action_set(include_groups=not args.no_groups,
                               lean=getattr(args, 'lean_actions', False))
    agent_graph = await generate_timeline_agents(
        terse_tools=getattr(args, "terse_tools", True),
        shared_prefix=getattr(args, "shared_prefix", True),
        max_tool_rounds=getattr(args, "max_tool_rounds", None),
        smart_tool_loop=getattr(args, "smart_tool_loop", False),
        fresh_context=getattr(args, "fresh_context", False),
        profile_path=os.path.join(REPO_ROOT, args.personas),
        model=model,
        available_actions=actions,
        limit=args.agents,
        include_groups=not args.no_groups,
        diverse=not args.no_diverse_personas,
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
        # Stretch the freshness curve across the run (F-16), so a
        # round-0 post does not dominate every feed forever.
        recency_span_rounds=(None if args.no_recency_scaling
                             else args.rounds),
        # F-17: show best-ranked posts, keeping a couple of slots for
        # exploration rather than sampling the pool at random.
        explore_slots=args.explore_slots,
        # F-25: reach flows through the graph, not a global pool.
        network_slots=args.network_slots,
        fof_slots=args.fof_slots,
        discovery_slots=args.discovery_slots,
        feed_size=args.feed_size,
        shuffle_feed=args.shuffle_feed,
        shuffle_seed=args.seed,
    )

    env = oasis.make(
        agent_graph=agent_graph,
        platform=sim_platform,
        database_path=db_path,
        # Local Ollama serialises anyway; high concurrency mainly produces
        # timeouts, which is how Sim 3 lost a run.
        semaphore=args.semaphore,
    )

    # B-28: ask the server what window it actually has, and refuse to run when
    # it cannot hold the prompt we are about to send. This check exists because
    # a truncated run does not fail -- it gets FASTER and quietly stops being
    # the experiment. Set OASIS_ALLOW_SMALL_CONTEXT=1 to override deliberately.
    srv = server_state.probe(args.ollama_url or server_state.DEFAULT_URL)
    ok, why = server_state.verify(srv)
    if ok:
        log.info("server context: %s", why)
    elif os.environ.get("OASIS_ALLOW_SMALL_CONTEXT"):
        log.warning("CONTEXT CHECK OVERRIDDEN -- %s", why)
    else:
        log.error("%s", why)
        raise SystemExit(2)

    manifest = {
        "label": args.label,
        "started_at": datetime.now().isoformat(),
        "config": {
            "agents": n_agents,
            "rounds": args.rounds,
            "recsys": args.recsys,
            "shuffle_feed": args.shuffle_feed,
            "model": args.model,
            "semaphore": args.semaphore,
            # F-53: the client semaphore is meaningless without the server
            # setting, and the server setting was silently 1 for R-1..R-24.
            # Recording it makes a run's real concurrency reconstructable
            # instead of assumed.
            # F-76/F-77: reading our OWN env records what we intended, not what
            # the server does. The sweep_* runs recorded "(unset)" while a server
            # at NP=1 served them, and that is how contaminated data looked
            # legitimate for months. Probe the server and record both.
            "ollama_num_parallel_client_env": os.environ.get(
                "OLLAMA_NUM_PARALLEL", "(unset)"),
            "ollama_server_state": _probe_ollama_server(),
            "max_rec_post_len": args.max_rec_post_len,
            "refresh_rec_post_count": args.refresh_rec_post_count,
            "following_post_count": args.following_post_count,
            "personas": args.personas,
            "persona_separability": getattr(
                agent_graph, "persona_separability", None),
            "prompt_version": PROMPT_VERSION,
            "seed": args.seed,
            "temperature": args.temperature,
            "n_actions": len(actions),
            "lean_actions": getattr(args, "lean_actions", False),
            "request_timeout": getattr(args, "request_timeout", None),
            "max_tokens": getattr(args, "max_tokens", None),
            "terse_tools": getattr(args, "terse_tools", True),
            "shared_prefix": getattr(args, "shared_prefix", True),
            "max_tool_rounds": getattr(args, "max_tool_rounds", None),
            "smart_tool_loop": getattr(args, "smart_tool_loop", False),
            "fresh_context": getattr(args, "fresh_context", False),
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
            "recency_span_rounds": (None if args.no_recency_scaling
                                   else args.rounds),
            "explore_slots": args.explore_slots,
            "network_slots": args.network_slots,
            "fof_slots": args.fof_slots,
            "discovery_slots": args.discovery_slots,
            "feed_size": args.feed_size,
            "feed_model": "three-tier: network > friend-of-friend > "
                          "discovery; social ties are not interest-filtered",
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": py_platform.platform(),
            "ollama_keep_alive": os.environ.get("OLLAMA_KEEP_ALIVE",
                                                "(unset)"),
            # B-28: what the SERVER reports, not what we asked for. An entire
            # six-run sweep was made at a 4,096-token window because nothing
            # here recorded the real one; prompts were silently truncated, the
            # feed was the part cut, and engagement fell 2.5x while the clock
            # said the run had got faster.
            **server_state.manifest_block(srv),
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

            # Q-16. Everything the platform did NOT account for is time spent
            # waiting on the model. F-50 inferred that split; this measures it.
            phases = sim_platform.take_phase_seconds()
            accounted = sum(phases.values())
            phases["llm_wait"] = round(max(0.0, elapsed - accounted), 3)

            manifest["rounds"].append({
                "round": round_no,
                "seconds": round(elapsed, 1),
                "cumulative_agent_failures": failures,
                "phase_seconds": phases,
                **counts,
            })
            log.info("round %d done in %.1fs | %s | agent failures: %d",
                     round_no, elapsed,
                     " ".join(f"{k}={v}" for k, v in counts.items()),
                     failures)
            log.info("  phases: %s  (llm %.0f%% of round)",
                     " ".join(f"{k}={v}s" for k, v in sorted(
                         phases.items(), key=lambda kv: -kv[1])),
                     100 * phases["llm_wait"] / elapsed if elapsed else 0)

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

    # Whole-run phase totals, so a reader does not have to sum the rounds.
    totals = {}
    for r in manifest["rounds"]:
        for k, v in (r.get("phase_seconds") or {}).items():
            totals[k] = round(totals.get(k, 0.0) + v, 2)
    manifest["phase_totals"] = dict(
        sorted(totals.items(), key=lambda kv: -kv[1]))
    if manifest["total_seconds"]:
        manifest["phase_share"] = {
            k: round(100 * v / manifest["total_seconds"], 1)
            for k, v in manifest["phase_totals"].items()}

    # F-83 telemetry. A flag that silently no-ops looks exactly like a flag
    # that works and buys nothing, and this project cannot tell those apart
    # from wall clock alone. Count the follow-up calls actually skipped.
    try:
        sc = sum(getattr(a, "short_circuits", 0)
                 for _, a in env.agent_graph.get_agents())
        manifest["context_resets"] = sum(
            getattr(a, "context_resets", 0)
            for _, a in env.agent_graph.get_agents())
        manifest["tool_loop_short_circuits"] = sc
        manifest["short_circuits_per_turn"] = (
            round(sc / (n_agents * args.rounds), 3) if args.rounds else None)
    except Exception as exc:  # noqa: BLE001 - telemetry must never fail a run
        manifest["tool_loop_short_circuits"] = f"unavailable: {exc}"

    manifest["platform_stats"] = sim_platform.stats
    manifest["finished_at"] = datetime.now().isoformat()

    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)

    log.info("=" * 66)
    log.info("run complete in %.1fs", manifest["total_seconds"])
    log.info("database: %s", db_path)
    log.info("manifest: %s", manifest_path)
    log.info("phase totals (s): %s", manifest.get("phase_totals"))
    log.info("phase share (%%):   %s", manifest.get("phase_share"))
    log.info("platform stats: %s", sim_platform.stats)
    log.info("final counts: %s", manifest["final_counts"])
    log.info("actions performed: %s", manifest["action_tally"])
    log.info("tool-loop short-circuits: %s (%s per agent-turn)",
             manifest.get("tool_loop_short_circuits"),
             manifest.get("short_circuits_per_turn"))
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


def _probe_ollama_server():
    """What the SERVER is actually doing, not what we asked for.

    Ollama exposes no direct NUM_PARALLEL reading, but the loaded model's VRAM
    footprint gives it away: F-77 measured `4.9 GB + ~1.55 GB per slot` for an
    8B Q4 model at ctx 8192, linear across NP=1..32. Recording the raw figures
    keeps a run reconstructable even if that formula is later refined.
    """
    try:
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/ps",
                                    timeout=5) as r:
            models = json.loads(r.read()).get("models") or []
    except Exception as exc:  # noqa: BLE001 - a probe must never fail a run
        return {"error": str(exc)[:80]}
    out = []
    for m in models:
        vram = m.get("size_vram") or 0
        out.append({
            "name": m.get("name"),
            "size_vram_gb": round(vram / 1e9, 2),
            "context_length": (m.get("context_length")
                               or (m.get("details") or {}).get("context_length")),
            # inverse of F-77's formula; indicative, not authoritative
            "implied_slots": (round((vram / 1e9 - 4.9) / 1.55)
                              if vram and vram / 1e9 > 4.9 else None),
        })
    return out or [{"note": "no model resident at manifest time"}]


def _check_server_keep_alive(ollama_url: str):
    """Return a warning string if the Ollama SERVER will unload between bursts.

    D-5: a 5-minute default unload made earlier simulations 3-4x slower,
    because a round's LLM burst is followed by minutes of scoring and I/O.
    The setting lives on the server, so this asks the server rather than
    inspecting our own environment (which was the old, wrong, check).

    Returns None when the server looks correctly configured, or when it cannot
    be interrogated -- an unreachable server is check_deps.py's problem, not a
    reason to emit a misleading warning here.
    """
    import urllib.request

    base = (ollama_url or "").rstrip("/")
    for suffix in ("/v1", "/api"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    if not base:
        return None

    # A loaded model reports when it will be evicted. That is the ground truth
    # for whether keep-alive is long enough, and it needs no env var at all.
    try:
        with urllib.request.urlopen(base + "/api/ps", timeout=3) as resp:
            models = json.loads(resp.read()).get("models") or []
    except Exception:  # noqa: BLE001
        return None

    if not models:
        # Nothing resident yet: fall back to our own environment, which is at
        # least a signal when the run and the server share a shell.
        if "OLLAMA_KEEP_ALIVE" not in os.environ:
            return ("Could not confirm the Ollama server's keep-alive (no "
                    "model loaded yet). If the server was started without "
                    "OLLAMA_KEEP_ALIVE=60m, it unloads after 5 minutes idle "
                    "and the run gets 3-4x slower (D-5).")
        return None

    from datetime import datetime, timezone
    for m in models:
        raw = (m.get("expires_at") or "").replace("Z", "+00:00")
        try:
            expires = datetime.fromisoformat(raw)
        except ValueError:
            continue
        minutes = (expires - datetime.now(timezone.utc)).total_seconds() / 60
        if minutes < 15:
            return (f"Ollama will unload {m.get('name')} in ~{minutes:.0f} min. "
                    f"A round's LLM burst is followed by minutes of scoring, so "
                    f"the model gets evicted mid-run and every round pays a "
                    f"reload -- 3-4x slower (D-5). Restart the server with "
                    f"OLLAMA_KEEP_ALIVE=60m.")
    return None


def main():
    """Command-line entry point: read the settings and start the run."""
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
    p.add_argument("--no-diverse-personas", action="store_true",
                   help="take the first N personas instead of a "
                        "maximally-separated subset")
    p.add_argument("--seed", type=int, default=0,
                   help="seeds feed exploration and any other Python RNG "
                        "use, so that component is reproducible")
    p.add_argument("--temperature", type=float, default=0.9,
                   help="LLM sampling temperature. Previously unset and "
                        "therefore unstated; now explicit and recorded")
    p.add_argument("--shuffle-feed", action="store_true",
                   help="F-94's experimental arm: rank and select the feed "
                        "exactly as normal, then PERMUTE the order before the "
                        "agent sees it. Same posts, same tiers, position "
                        "assigned rather than observed. Engagement flattening "
                        "across slots with total engagement HELD means the "
                        "ranker's ordering was worth nothing; total engagement "
                        "FALLING means it carried real information.")
    p.add_argument("--feed-size", type=int, default=12,
                   dest="feed_size",
                   help="total posts per feed. Discovery backfills "
                        "what the graph did not supply, so size is "
                        "constant and only composition varies")
    p.add_argument("--network-slots", type=int, default=5,
                   dest="network_slots",
                   help="feed slots for people you follow. Not "
                        "interest-filtered: following someone means "
                        "you see them (F-25)")
    p.add_argument("--fof-slots", type=int, default=3,
                   dest="fof_slots",
                   help="slots for friends-of-friends, interest ranked")
    p.add_argument("--discovery-slots", type=int, default=4,
                   dest="discovery_slots",
                   help="global discovery slots. The only source an "
                        "unconnected agent has, so isolation limits "
                        "reach on its own")
    p.add_argument("--explore-slots", type=int, default=2,
                   dest="explore_slots",
                   help="feed slots given to exploration instead of the "
                        "top-ranked posts (default 2 of 8). 0 = pure "
                        "exploitation (finding F-17)")
    p.add_argument("--no-recency-scaling", action="store_true",
                   help="keep upstream's raw recency curve, which over a "
                        "short run is nearly flat and lets round-0 posts "
                        "dominate permanently (finding F-16)")
    p.add_argument("--no-groups", action="store_true",
                   help="drop the 5 group-chat actions (22 instead of 27). "
                        "Group instructions are injected into every prompt "
                        "ahead of the feed and crowd out content engagement "
                        "-- see finding F-14.")
    p.add_argument("--max-tool-rounds", type=int, default=None,
                   dest="max_tool_rounds",
                   help="cap camel's tool loop at N model calls per turn "
                        "(Q-23). Default None = camel's unlimited. Measured "
                        "1.31 calls/turn, so --max-tool-rounds 1 removes ~24%% "
                        "of all LLM work -- but an agent wanting a second "
                        "action in a second round-trip would lose it. A/B it.")
    p.add_argument("--persona-in-system", action="store_false",
                   dest="shared_prefix",
                   help="keep the persona in the system message, as upstream "
                        "does. F-66: that gives every agent a different prompt "
                        "prefix, so Ollama's prefix cache never hits and each "
                        "agent pays ~5.5s to re-read the same tool block. "
                        "Hoisting it into the user turn is the default.")
    p.add_argument("--fresh-context", action="store_true",
                   help="clear each agent's conversation memory between rounds. "
                        "F-86: camel appends every message, reply and tool "
                        "result to agent memory and re-prefills all of it next "
                        "turn. Measured request latency runs 10.1s at round 0, "
                        "86.2s by round 4, then flat as the 8192-token context "
                        "fills and truncates. Round 0 costs 94s of wall clock; "
                        "rounds 4+ cost ~790s. With this on every round should "
                        "cost about what round 0 costs -- of order 6x. OFF by "
                        "default: the behavioural effect is UNTESTED, though "
                        "note agents already lose most history to truncation.")
    p.add_argument("--smart-tool-loop", action="store_true",
                   help="stop the tool loop after a TERMINAL action (a like, a "
                        "follow, a post) but keep going after an informational "
                        "one (search, trend, refresh). F-83: in a 504-turn run, "
                        "99%% of turns took 0 or 1 action and 0 of 431 actions "
                        "returned anything the model needed to read, so the "
                        "follow-up call -- about 46%% of all LLM work -- buys a "
                        "second action once in a hundred turns. Unlike "
                        "--lean-actions this removes no action, and unlike "
                        "--max-tool-rounds 1 it preserves search->read->act. "
                        "OFF by default: it must be A/B'd, not assumed.")
    p.add_argument("--verbose-tools", action="store_false", dest="terse_tools",
                   help="ship each action's full docstring as its tool "
                        "description, as upstream does. F-64: that is ~3,000 "
                        "prompt tokens of API documentation per turn, 1.54x "
                        "slower, and tool-call reliability drops from 5/6 to "
                        "1/6. The terse descriptions are the default.")
    p.add_argument("--max-tokens", type=int, default=999_999_999,
                   dest="max_tokens",
                   help="cap on generated tokens per turn. DEFAULT IS NO CAP, "
                        "and F-63 is why: capping at 512 -- with every other "
                        "setting identical -- took engagement with shown posts "
                        "from 4.31%% to 0.36%%. Agents kept posting and stopped "
                        "reacting, which answers no research question. The "
                        "mechanism is still unexplained (Q-22), so the flag "
                        "exists to record that no cap was applied.")
    p.add_argument("--request-timeout", type=float, default=300.0,
                   dest="request_timeout",
                   help="seconds before a single LLM request is abandoned "
                        "(default 300). B-22: without this a hung request "
                        "blocks the entire run indefinitely -- one cost 24 "
                        "hours on 2026-09-05. A turn that exceeds it is "
                        "counted as an agent failure and the round continues.")
    p.add_argument("--lean-actions", action="store_true", dest="lean_actions",
                   help="Q-21: drop the 8 actions F-48 found never fire, "
                        "cutting ~980 prompt tokens per turn. A DIFFERENT "
                        "CONDITION, not an optimisation -- the action surface "
                        "is an experimental variable. Recorded in the manifest.")
    p.add_argument("--semaphore", type=int, default=4,
                   help="max concurrent LLM calls (default 4). NOTE F-53: "
                        "this only does anything if the Ollama SERVER is "
                        "started with OLLAMA_NUM_PARALLEL>1. It was 1 for all "
                        "of R-1..R-24, so every turn queued and this flag "
                        "merely filled the queue -- at Parallel:1, "
                        "--semaphore 4 is 19%% SLOWER than --semaphore 1. "
                        "With OLLAMA_NUM_PARALLEL=8, --semaphore 8 measured "
                        "1.9x. check_deps.py gates this.")
    p.add_argument("--max-rec-post-len", type=int, default=30,
                   dest="max_rec_post_len")
    p.add_argument("--refresh-rec-post-count", type=int, default=8,
                   dest="refresh_rec_post_count")
    p.add_argument("--following-post-count", type=int, default=4,
                   dest="following_post_count")
    args = p.parse_args()

    # D-5. Keep-alive is a SERVER setting: it governs how long Ollama holds the
    # model in memory, and it is read by `ollama serve`, not by this process.
    # Checking our own environment cried wolf at anyone who set it correctly on
    # the server and launched the run from a different shell -- which is the
    # normal way to do it. Ask the server what it is actually using instead.
    # F-63 guard. A cap here silently voids the study rather than failing --
    # agents keep posting and stop reacting to their feed -- and seven full
    # runs were spent before anyone noticed. Make it loud.
    if args.max_tokens < 100_000:
        log.warning(
            "--max-tokens=%s. F-63: capping generated tokens took engagement "
            "with shown posts from 4.31%% to 0.36%% with every other setting "
            "held fixed. Unless you are deliberately reproducing that, leave "
            "it uncapped.", args.max_tokens)

    _keep_alive_note = _check_server_keep_alive(args.ollama_url)
    if _keep_alive_note:
        log.warning("%s", _keep_alive_note)

    asyncio.run(run(args))


if __name__ == "__main__":
    main()
