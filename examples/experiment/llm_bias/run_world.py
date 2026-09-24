"""Run one SHARED WORLD (design v2): every post live, every persona scrolls everything.

IN PLAIN WORDS
--------------
1. Post bank: every author model writes `--posts-per-topic` posts on every topic
   (default 5 topics x 5 posts). Posts in the same slot share one brief, so they
   differ only by which model wrote them (authors.py, unchanged).
2. One OASIS reddit world: the personas, plus one poster account per author
   model. All posts are published up front through OASIS `create_post`.
3. Each persona is played by ONE judge model, on a fixed rotation:
       persona i  ->  judges[(i + world) % len(judges)]
   With judges = [llama, gemma]: world 0 gives even personas to llama and odd to
   gemma; world 1 swaps them. Over len(judges) worlds on the same post bank,
   every persona is played by every judge exactly once, so "which model got
   which people" cannot masquerade as bias.
4. Each persona scrolls every post (scroll.py): best-loved topic first, one post
   per call, like / dislike / nothing. Likes and dislikes are executed as OASIS
   `like_post` / `dislike_post`. Vote counts are never shown, so the order in
   which personas take their turn cannot matter -- which is what lets the run
   take the judge models one at a time (only one model in memory).
5. Every call is appended to decisions.jsonl as it happens. `--resume` rebuilds
   the OASIS world from scratch, replays the recorded votes, and carries on.

    python run_world.py --label w_test --seed 10 --world 0 \
        --judges llama3.1:8b,gemma4:e2b --agents 10
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
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors  # noqa: E402
import llm  # noqa: E402
import personas as persona_mod  # noqa: E402
import scroll  # noqa: E402
from topics import PRIMARY, TOPICS  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
RUNS = os.path.join(REPO, "data", "llm_bias", "worlds")
DEFAULT_AUTHORS = ["llama3.1:8b", "gemma4:e2b"]  # Gordon 2026-09-24: two models, write AND judge


def assign(persona_id, judges, world):
    return judges[(persona_id + world) % len(judges)]


async def build_world(bank_personas, author_list, judges, world, db_path):
    import oasis
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType
    from oasis import DefaultPlatformType
    from oasis.social_agent.agent import SocialAgent
    from oasis.social_agent.agent_graph import AgentGraph
    from oasis.social_platform.config import UserInfo
    from oasis.social_platform.typing import ActionType

    # One backend object per judge so each OASIS agent records the model that plays it.
    # Decisions go through llm.py, not this backend.
    backends = {j: ModelFactory.create(model_platform=ModelPlatformType.OLLAMA, model_type=j,
                                       url=llm.OLLAMA_URL + "/v1",
                                       model_config_dict={"temperature": 0.7, "max_tokens": 4096})
                for j in judges}
    g = AgentGraph()
    agents = {}
    for p in bank_personas:
        ui = UserInfo(user_name=p["username"], name=p["realname"], description=p["bio"],
                      profile={"persona": p["persona"]}, recsys_type="reddit")
        a = SocialAgent(agent_id=p["id"], user_info=ui, user_info_template=scroll.SYSTEM_TEMPLATE,
                        model=backends[assign(p["id"], judges, world)], agent_graph=g,
                        available_actions=[ActionType.LIKE_POST, ActionType.DISLIKE_POST,
                                           ActionType.DO_NOTHING])
        g.add_agent(a)
        agents[p["id"]] = a
    base = max(p["id"] for p in bank_personas) + 1
    posters = {}
    for k, author in enumerate(author_list):
        ui = UserInfo(user_name=f"poster_{k:02d}", name=f"Poster {k}", description="",
                      profile={"persona": ""}, recsys_type="reddit")
        a = SocialAgent(agent_id=base + k, user_info=ui, user_info_template=scroll.SYSTEM_TEMPLATE,
                        model=backends[judges[0]], agent_graph=g, available_actions=[ActionType.CREATE_POST])
        g.add_agent(a)
        posters[author] = a
    env = oasis.make(agent_graph=g, platform=DefaultPlatformType.REDDIT, database_path=db_path)
    await env.reset()
    return env, agents, posters


async def run(a):
    from oasis.social_platform.typing import ActionType

    if not llm.server_up():
        raise SystemExit("Ollama is not running. Start it with:\n  OLLAMA_NUM_PARALLEL=4 "
                         "OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=24h ollama serve")
    judges, author_list, topics = a.judges.split(","), a.authors.split(","), a.topics.split(",")
    have = set(llm.available_models())
    for m in judges + author_list:
        if m not in have:
            raise SystemExit(f"model {m} is not pulled (ollama pull {m})")

    out = os.path.join(RUNS, a.label)
    dec_path = os.path.join(out, "decisions.jsonl")
    if os.path.exists(out) and not a.resume:
        if not a.overwrite:
            raise SystemExit(f"{out} exists; pass --resume to continue it or --overwrite to replace it")
        shutil.rmtree(out)
    os.makedirs(out, exist_ok=True)
    log_f = open(os.path.join(out, "run.log"), "a")

    def log(msg):
        line = f"{datetime.now():%H:%M:%S} {msg}"
        print(line, flush=True)
        log_f.write(line + "\n")
        log_f.flush()

    # 1. posts (incremental; shared by every world on this seed)
    t0 = time.time()
    pbank = authors.generate(a.seed, a.posts_per_topic, topics, author_list, log=log)
    gen_s = time.time() - t0
    posts = [pbank[authors.key(k, t, au)] for t in topics for k in range(a.posts_per_topic)
             for au in author_list]
    bad = [p["key"] for p in posts if not p.get("ok")]
    posts = [p for p in posts if p.get("ok")]
    if bad:
        log(f"WARNING {len(bad)} posts failed generation and are left out: {bad[:5]}")

    # 2. world
    # The SAME 99 hard-coded personas every run (pinned fingerprint; refuses to run if changed).
    # A smaller --agents takes the first N of those same 99, never different people.
    if a.agents > persona_mod.CORE_N:
        raise SystemExit(f"--agents {a.agents}: the standard population is the {persona_mod.CORE_N} pinned personas")
    bank = persona_mod.core99()[:a.agents]
    db_path = os.path.join(out, "oasis.db")
    if os.path.exists(db_path):
        os.remove(db_path)  # rebuilt from scratch on resume; votes are replayed below
    env, agents, posters = await build_world(bank, author_list, judges, a.world, db_path)
    post_id = {}
    for p in posts:  # sequential, so ids are stable across resumes
        r = await posters[p["author"]].perform_action_by_data(
            ActionType.CREATE_POST, content=f"{p['title']}\n\n{p['body']}")
        post_id[p["key"]] = r.get("post_id")
    by_topic = {t: [p for p in posts if p["topic"] == t] for t in topics}
    log(f"world {a.world}: {len(bank)} personas, {len(posts)} posts, judges {judges}")

    # resume: replay recorded votes into the fresh OASIS db
    done = set()
    if a.resume and os.path.exists(dec_path):
        replay = []
        for line in open(dec_path):
            if not line.strip():
                continue
            d = json.loads(line)
            done.add((d["agent_id"], d["post_key"]))
            if d.get("action") in ("like", "dislike"):
                act = ActionType.LIKE_POST if d["action"] == "like" else ActionType.DISLIKE_POST
                replay.append(agents[d["agent_id"]].perform_action_by_data(act, post_id=post_id[d["post_key"]]))
        await asyncio.gather(*replay)
        log(f"resumed: {len(done)} decisions already done, {len(replay)} votes replayed")

    manifest_path = os.path.join(out, "manifest.json")
    manifest = json.load(open(manifest_path)) if a.resume and os.path.exists(manifest_path) else {
        "label": a.label, "design": "v2-scroll-shared-world", "started_at": datetime.now().isoformat(),
        "config": {"seed": a.seed, "world": a.world, "judges": judges, "authors": author_list,
                   "topics": topics, "posts_per_topic": a.posts_per_topic, "agents": a.agents,
                   "parallel": a.parallel, "temperature": a.temperature, "num_ctx": llm.NUM_CTX,
                   "think": False, "show_author": False, "show_scores": False,
                   "assignment": "persona i -> judges[(i + world) % len(judges)]"},
        "persona_bank_hash": persona_mod.PINNED_BANK_HASH,
        "core99_hash": persona_mod.PINNED_CORE99_HASH,
        "persona_ids": [p["id"] for p in bank],
        "post_generation_s": round(gen_s, 1),
        "machine": {"platform": _platform.platform(),
                    "ollama_env": {k: v for k, v in os.environ.items() if k.startswith("OLLAMA_")}},
        "judges": {}}
    manifest["n_posts"] = len(posts)

    dec_f = open(dec_path, "a")
    pool = ThreadPoolExecutor(max_workers=a.parallel)
    loop = asyncio.get_running_loop()

    # 3. one judge model at a time (vote counts are hidden, so turn order cannot matter)
    for judge in judges:
        mine = [p for p in bank if assign(p["id"], judges, a.world) == judge]
        jobs = [(p, item) for p in mine for item in scroll.feed(p, by_topic, a.seed)
                if (p["id"], item[3]["key"]) not in done]
        if not jobs:
            continue
        llm.warm(judge)
        log(f"{judge}: {len(mine)} personas, {len(jobs)} decisions to make")
        t_j = time.time()
        counts = Counter()
        sem = asyncio.Semaphore(a.parallel * 2)
        n_done = 0

        async def decide(p, item):
            nonlocal n_done
            rank, t, pos, post = item
            async with sem:
                system = agents[p["id"]].system_message.content
                user = scroll.render_user(t, post)
                obj, meta = await loop.run_in_executor(pool, lambda: llm.chat_json(
                    judge, system, user, seed=llm.stable_seed(a.seed, p["id"], post["key"], "scroll"),
                    temperature=a.temperature, num_predict=a.num_predict, validate=scroll.validate,
                    retries=2))
            oc = scroll.outcome(obj, meta)
            act = obj["action"] if obj else None
            d = {"label": a.label, "seed": a.seed, "world": a.world, "judge": judge, "agent_id": p["id"],
                 "voting_style": p["voting"], "affinity": p["topic_affinity"][t], "topic": t,
                 "topic_rank": rank, "pos_in_topic": pos, "post_key": post["key"], "author": post["author"],
                 "slot": f"{a.seed}|{post['round']}|{t}", "self": int(post["author"] == judge),
                 "action": act, "outcome": oc, "reason": obj["reason"] if obj else None,
                 "attempts": meta["attempts"], "errors": meta["errors"], "done_reason": meta["done_reason"],
                 "thinking_chars": meta["thinking_chars"], "latency_s": round(meta["latency_s"], 2),
                 "prompt_tokens": meta["prompt_tokens"], "eval_tokens": meta["eval_tokens"],
                 "truncation_risk": meta["truncation_risk"], "raw": meta.get("raw")}
            if act in ("like", "dislike"):
                at = ActionType.LIKE_POST if act == "like" else ActionType.DISLIKE_POST
                await agents[p["id"]].perform_action_by_data(at, post_id=post_id[post["key"]])
            dec_f.write(json.dumps(d) + "\n")
            dec_f.flush()
            counts[act or oc] += 1
            n_done += 1
            if n_done % a.log_every == 0:
                el = time.time() - t_j
                log(f"  {judge}: {n_done}/{len(jobs)} ({el / n_done:.2f} s/decision, "
                    f"ETA {(len(jobs) - n_done) * el / n_done / 60:.0f} min) {dict(counts)}")

        await asyncio.gather(*[decide(p, item) for p, item in jobs])
        wall = time.time() - t_j
        prev = manifest["judges"].get(judge, {"decisions": 0, "wall_s": 0.0, "counts": {}})
        prev["decisions"] += len(jobs)
        prev["wall_s"] = round(prev["wall_s"] + wall, 1)
        prev["counts"] = dict(Counter(prev["counts"]) + counts)
        prev["s_per_decision"] = round(prev["wall_s"] / max(1, prev["decisions"]), 3)
        manifest["judges"][judge] = prev
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=1)
        log(f"{judge}: done {len(jobs)} in {wall / 60:.1f} min ({wall / len(jobs):.2f} s/decision) {dict(counts)}")

    manifest["finished_at"] = datetime.now().isoformat()
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=1)
    await env.close()
    pool.shutdown()
    log(f"done: {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--seed", type=int, required=True, help="post bank")
    ap.add_argument("--world", type=int, default=0, help="rotation index for persona -> judge")
    ap.add_argument("--judges", default="llama3.1:8b,gemma4:e2b")
    ap.add_argument("--authors", default=",".join(DEFAULT_AUTHORS))
    ap.add_argument("--topics", default=",".join(PRIMARY))
    ap.add_argument("--posts-per-topic", type=int, default=5)
    ap.add_argument("--agents", type=int, default=99)
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--num-predict", type=int, default=80)
    ap.add_argument("--log-every", type=int, default=250)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
