"""Run one LLM Bias simulation: one judge model plays N personas for R rounds.

IN PLAIN WORDS
--------------
1. Make sure the post bank has every post this run needs (authors.py writes any
   that are missing -- every author model, every round, every active topic).
2. Build an OASIS reddit world: N persona users + one poster account per author
   model. Posts are published by the poster accounts through OASIS's own
   `create_post` action.
3. Each round: publish that round's posts; then every persona, played by the
   JUDGE model, sees each topic's posts (anonymous, shuffled, no vote counts),
   votes up/down/none on each and picks one favourite. The votes are executed on
   the OASIS platform as `like_post` / `dislike_post`.
4. Every decision is appended to `decisions.jsonl` the moment it is made, so a
   crash loses at most the calls in flight.

The run answers one cell-row of the crossover: "what does judge J pick, given
posts by authors A1..Ak?". Running every judge model over the SAME seed gives
the full judge x author matrix that analyze.py tests.

    python run_bias.py --label smoke --judge llama3.1:8b --agents 5 --rounds 2 \
        --authors llama3.1:8b,gemma4:e2b,granite4.1:3b
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform as _platform
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors  # noqa: E402
import judge  # noqa: E402
import llm  # noqa: E402
import personas as persona_mod  # noqa: E402
from topics import DEFAULT_ACTIVE, TOPICS  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RUNS = os.path.join(REPO, "data", "llm_bias", "runs")

DEFAULT_AUTHORS = ["llama3.1:8b", "gemma4:e2b", "granite4.1:3b", "qwen2.5:7b", "mistral:7b",
                   "phi4-mini:3.8b", "llama3.2:3b"]


def decision_seed(seed, agent_id, rnd, topic):
    return llm.stable_seed(seed, agent_id, rnd, topic, "judge")


def build_world(bank, n_agents, author_list, judge_model, db_path):
    """OASIS reddit world. Returns (env, persona_agents, poster_agents)."""
    import oasis
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType
    from oasis import DefaultPlatformType
    from oasis.social_agent.agent import SocialAgent
    from oasis.social_agent.agent_graph import AgentGraph
    from oasis.social_platform.config import UserInfo
    from oasis.social_platform.typing import ActionType

    # The agents never call this backend (decisions go through judge.py); OASIS
    # needs one to construct a SocialAgent, and it records which model plays them.
    model = ModelFactory.create(model_platform=ModelPlatformType.OLLAMA, model_type=judge_model,
                                url=llm.OLLAMA_URL + "/v1", model_config_dict={"temperature": 0.7, "max_tokens": 4096})
    g = AgentGraph()
    personas_ = []
    for p in bank[:n_agents]:
        ui = UserInfo(user_name=p["username"], name=p["realname"], description=p["bio"],
                      profile={"persona": p["persona"]}, recsys_type="reddit")
        a = SocialAgent(agent_id=p["id"], user_info=ui, user_info_template=judge.SYSTEM_TEMPLATE,
                        model=model, agent_graph=g,
                        available_actions=[ActionType.LIKE_POST, ActionType.DISLIKE_POST,
                                           ActionType.DO_NOTHING])
        g.add_agent(a)
        personas_.append(a)
    posters = {}
    for k, author in enumerate(author_list):
        aid = n_agents + k
        # neutral handle: judges never see usernames, and the handle does not name the model anyway
        ui = UserInfo(user_name=f"poster_{k:02d}", name=f"Poster {k}", description="",
                      profile={"persona": ""}, recsys_type="reddit")
        a = SocialAgent(agent_id=aid, user_info=ui, user_info_template=judge.SYSTEM_TEMPLATE,
                        model=model, agent_graph=g, available_actions=[ActionType.CREATE_POST])
        g.add_agent(a)
        posters[author] = a
    env = oasis.make(agent_graph=g, platform=DefaultPlatformType.REDDIT, database_path=db_path)
    return env, personas_, posters


async def run(args):
    from oasis.social_platform.typing import ActionType

    if not llm.server_up():
        raise SystemExit("Ollama is not running. Start it with:\n  OLLAMA_NUM_PARALLEL=4 "
                         "OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=24h ollama serve")
    have = set(llm.available_models())
    author_list = args.authors.split(",")
    topics = args.topics.split(",")
    for m in author_list + [args.judge]:
        if m not in have:
            raise SystemExit(f"model {m} is not pulled (ollama pull {m})")
    for t in topics:
        if t not in TOPICS:
            raise SystemExit(f"unknown topic {t}")

    out = os.path.join(RUNS, args.label)
    if os.path.exists(out):
        if not args.overwrite:
            raise SystemExit(f"{out} exists; pass --overwrite to replace it")
        shutil.rmtree(out)
    os.makedirs(out)
    log_f = open(os.path.join(out, "run.log"), "a")

    def log(msg):
        line = f"{datetime.now():%H:%M:%S} {msg}"
        print(line, flush=True)
        log_f.write(line + "\n")
        log_f.flush()

    # 1. posts
    t_gen = time.time()
    pbank = authors.generate(args.seed, args.rounds, topics, author_list, log=log)
    gen_s = time.time() - t_gen
    missing = [authors.key(r, t, a) for r in range(args.rounds) for t in topics for a in author_list
               if not pbank.get(authors.key(r, t, a), {}).get("ok")]
    if missing:
        log(f"WARNING {len(missing)} posts failed generation and are left out: {missing[:5]}")

    # 2. world
    bank = persona_mod.load_bank()
    if args.agents > len(bank):
        raise SystemExit(f"only {len(bank)} personas in the bank")
    db_path = os.path.join(out, "oasis.db")
    env, persona_agents, posters = build_world(bank, args.agents, author_list, args.judge, db_path)
    await env.reset()
    llm.warm(args.judge)
    log(f"world: {len(persona_agents)} personas + {len(posters)} posters; judge={args.judge}")

    manifest = {
        "label": args.label, "started_at": datetime.now().isoformat(),
        "config": {"judge": args.judge, "authors": author_list, "topics": topics, "seed": args.seed,
                   "agents": args.agents, "rounds": args.rounds, "parallel": args.parallel,
                   "temperature": args.temperature, "num_ctx": llm.NUM_CTX, "think": False,
                   "show_author": False, "show_scores": False, "order": "shuffled per persona/round/topic"},
        "persona_bank_hash": persona_mod.bank_hash(bank),
        "machine": {"platform": _platform.platform(), "python": sys.version.split()[0],
                    "ollama_env": {k: v for k, v in os.environ.items() if k.startswith("OLLAMA_")}},
        "post_generation_s": round(gen_s, 1), "rounds": [],
    }
    dec_f = open(os.path.join(out, "decisions.jsonl"), "a")
    pool = ThreadPoolExecutor(max_workers=args.parallel)
    loop = asyncio.get_running_loop()
    t_run = time.time()

    for r in range(args.rounds):
        t_round = time.time()
        # 3a. publish this round's posts through OASIS
        round_posts = {t: [] for t in topics}
        pubs = []
        for t in topics:
            for a in author_list:
                rec = pbank.get(authors.key(r, t, a))
                if rec and rec["ok"]:
                    pubs.append((t, rec))
        results = await asyncio.gather(*[
            posters[rec["author"]].perform_action_by_data(
                ActionType.CREATE_POST, content=f"{rec['title']}\n\n{rec['body']}")
            for _, rec in pubs])
        for (t, rec), res in zip(pubs, results):
            round_posts[t].append({**rec, "post_id": res.get("post_id")})

        # 3b. judge
        async def decide(agent, persona, t):
            posts = round_posts[t]
            order = judge.display_order(len(posts), args.seed, persona["id"], r, t)
            shown = [posts[i] for i in order]
            user = judge.render_user(t, shown)
            system = agent.system_message.content
            obj, meta = await loop.run_in_executor(pool, lambda: llm.chat_json(
                args.judge, system, user, seed=decision_seed(args.seed, persona["id"], r, t),
                temperature=args.temperature, num_predict=300,
                validate=judge.make_validator(len(shown)), retries=2))
            d = {"label": args.label, "judge": args.judge, "seed": args.seed, "round": r, "topic": t,
                 "agent_id": persona["id"], "affinity": persona["topic_affinity"][t],
                 "voting_style": persona["voting"], "n_posts": len(shown),
                 "shown_keys": [p["key"] for p in shown], "shown_authors": [p["author"] for p in shown],
                 "shown_post_ids": [p["post_id"] for p in shown], "ok": obj is not None,
                 "attempts": meta["attempts"], "errors": meta["errors"],
                 "latency_s": round(meta["latency_s"], 2), "prompt_tokens": meta["prompt_tokens"],
                 "eval_tokens": meta["eval_tokens"], "truncation_risk": meta["truncation_risk"],
                 "raw": meta.get("raw")}
            if obj:
                fp = obj["favorite"] - 1
                d.update({"favorite_pos": fp, "favorite_key": shown[fp]["key"],
                          "favorite_author": shown[fp]["author"],
                          "votes": {shown[i - 1]["key"]: v for i, v in obj["votes"].items()},
                          "missing_votes": obj["missing_votes"], "reason": obj["reason"]})
                acts = []
                for i, v in obj["votes"].items():
                    pid = shown[i - 1]["post_id"]
                    if v == "up":
                        acts.append(agent.perform_action_by_data(ActionType.LIKE_POST, post_id=pid))
                    elif v == "down":
                        acts.append(agent.perform_action_by_data(ActionType.DISLIKE_POST, post_id=pid))
                if acts:
                    await asyncio.gather(*acts)
            dec_f.write(json.dumps(d) + "\n")
            dec_f.flush()
            return d

        tasks = [decide(agent, bank[agent.social_agent_id], t) for agent in persona_agents for t in topics]
        ds = await asyncio.gather(*tasks)
        n_ok = sum(d["ok"] for d in ds)
        n_self = sum(1 for d in ds if d.get("favorite_author") == args.judge)
        n_trunc = sum(d["truncation_risk"] for d in ds)
        wall = time.time() - t_round
        manifest["rounds"].append({"round": r, "decisions": len(ds), "ok": n_ok, "wall_s": round(wall, 1),
                                   "s_per_decision": round(wall / max(1, len(ds)), 2),
                                   "self_favorites": n_self, "truncation_risk": n_trunc})
        log(f"round {r}: {n_ok}/{len(ds)} valid, {wall:.0f}s ({wall / max(1, len(ds)):.2f} s/decision), "
            f"judge picked its own post {n_self}x (chance {len(ds) / max(1, len(author_list)):.1f})"
            + (f", TRUNCATION RISK {n_trunc}" if n_trunc else ""))
        with open(os.path.join(out, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=1)

    manifest["finished_at"] = datetime.now().isoformat()
    manifest["judge_wall_s"] = round(time.time() - t_run, 1)
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    await env.close()
    pool.shutdown()
    log(f"done: {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--judge", required=True)
    ap.add_argument("--authors", default=",".join(DEFAULT_AUTHORS))
    ap.add_argument("--topics", default=",".join(DEFAULT_ACTIVE))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--agents", type=int, default=99)
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--overwrite", action="store_true")
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
