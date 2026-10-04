"""LLM Bias v2: one round, one model playing all 100 pinned users, every action available. (Part 14 of the log.)

IN PLAIN WORDS
--------------
Every round is a fresh world (LD-25: no follow graph, no memory, vote counts hidden).

1. Seed posts (identical for every model). The round takes 2 real Reddit posts per subreddit from the human pool
   (human_pool_v2.py; never reused in a later round). For each one, every AI in --authors writes its own post on
   the same subject (the human post's title), using Test 6's natural-post prompt: no length or style rules. So each
   subject has 4 versions -- human, qwen, gemma, llama -- that differ only in who wrote them. Saved once per round
   in data/llm_bias/v2/seedbank_rNN.jsonl and reused by every model.
2. Who sees what. The 100 users split into two halves that are identical on topic stances (each half holds 2 of the
   4 copies of every stance pattern). Each round, one half sees subject 0 of every subreddit and the other half
   subject 1, alternating by round. A user sees all 4 versions of their 5 subjects: 20 posts.
3. Pass 1 (scroll). One post per call, no memory. Shown as "posted by u/<account>" -- 20 neutral accounts carry
   the seed posts, so an account name says nothing about the author. The user may do any combination of: upvote /
   downvote, comment, follow or mute the poster, share, report -- or nothing.
4. Posting. One call per user: write a post of your own in any of the 5 subreddits, or don't.
5. Pass 2 (social, on by default). Each user meets up to --social-n posts that OTHER users wrote in step 4, with
   the same choices as pass 1.
6. Everything is replayed into a standard OASIS reddit database (create_post, like_post, dislike_post,
   create_comment, follow, mute, repost, report_post) in a fixed order.

Every call is appended to decisions.jsonl as it happens; re-running the same command resumes.

    python run_v2.py --round 1 --model qwen3:4b              # the real thing: 100 users
    python run_v2.py --round 900 --model qwen3:4b --agents 10 # smoke test (round 900+ = test rounds)
"""
from __future__ import annotations

import argparse, asyncio, hashlib, json, os, random, re, subprocess, sys, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors  # noqa: E402  (Test 6's natural-post prompt and validator, unchanged)
import llm  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(REPO, "data", "llm_bias", "v2")
SRC = os.path.join(REPO, "data", "llm_bias", "v2_sources")
PERSONAS = os.path.join(HERE, "personas_v2.json")
PINNED_PERSONAS = "11ac527c6351e054dc2e054f3de892893404d58df1eb7eb32a0104a36a2f6383"  # build_population_v2.py
SEED = 20261002
AUTHORS = ["qwen3:4b", "gemma4:e2b", "llama3.1:8b"]  # LD-24 + LD-27: Alibaba, Google, Meta
TOPICS = {"personal_finance": ("r/personalfinance", "Personal finance & money"),
          "cooking": ("r/EatCheapAndHealthy", "Cooking & eating cheap and healthy"),
          "gardening": ("r/gardening", "Gardening & growing plants"),
          "travel": ("r/travel", "Travel"),
          "fitness": ("r/Fitness", "Fitness & exercise")}
SLOTS_PER_TOPIC, N_ACCOUNTS = 2, 20

AUTHOR_USER = """Write one new post for {sub} ({topic_name}).

Subject: {subject}

Write it however you naturally would. Do not mention AI or language models, and do not sign the post.

Reply with JSON only: {{"title": "...", "body": "..."}}"""

SYSTEM = ("# OBJECTIVE\n"
          "You're a Reddit user. You'll be shown what's on your screen and decide what, if anything, to do -- "
          "exactly as you would on the real app.\n\n"
          "# SELF-DESCRIPTION\n"
          "Your actions should be consistent with your self-description and personality.\n"
          "{persona}\n\n"
          "# RESPONSE METHOD\n"
          "Reply with a single JSON object and nothing else.")

POST_USER = """You are scrolling {sub} ({topic_name}). Next in your feed, posted by u/{account}:

Title: {title}
{body}

Do whatever you would really do. You can do any of these, as many or as few as you like (doing nothing is fine):
- vote: "upvote", "downvote" or "none"
- comment: write a comment, or leave it empty
- follow: follow u/{account}
- mute: mute u/{account} so you stop seeing their posts
- share: share this post
- report: report this post to the moderators

Reply with JSON only:
{{"vote": "upvote|downvote|none", "comment": "<your comment, or empty>", "follow": true|false, "mute": true|false, "share": true|false, "report": true|false, "reason": "<a few words, in your own voice>"}}"""

WRITE_USER = """You're on Reddit. You can post in any of these subreddits:
{subs}

Would you like to write a post of your own right now? Post about whatever you like, the way you really would -- or don't post at all.

Reply with JSON only:
{{"post": true|false, "subreddit": "<one of the subreddits above, or empty>", "title": "<or empty>", "body": "<or empty>", "reason": "<a few words, in your own voice>"}}"""

UP, DOWN, NONE = {"upvote", "like", "up", "+1"}, {"downvote", "dislike", "down", "-1"}, {"none", "nothing", "", "no vote", "skip"}
LEAK = authors.LEAK


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def load_personas():
    p = json.load(open(PERSONAS))
    if sha(p) != PINNED_PERSONAS:
        raise SystemExit(f"personas_v2.json changed ({sha(p)[:12]} != pinned {PINNED_PERSONAS[:12]}); refusing to run")
    return p


def halves(people):
    """Two halves identical on stances: users with the same stance pattern (4 each) split 2 + 2 by id."""
    groups = {}
    for p in people:
        groups.setdefault(tuple(p["stances"][t] for t in TOPICS), []).append(p["id"])
    half = {}
    for ids in groups.values():
        for n, i in enumerate(sorted(ids)):
            half[i] = n % 2
    return half


def _bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "yes", "1", "y")


def validate_action(obj):
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    v = str(obj.get("vote", "")).strip().lower().strip(".!\"'")
    vote = "upvote" if v in UP else "downvote" if v in DOWN else "none" if v in NONE else None
    if vote is None:
        raise ValueError(f"unknown vote {v!r}")
    c = obj.get("comment") or ""
    return {"vote": vote, "comment": str(c).strip() if str(c).strip().lower() not in ("none", "null", "empty") else "",
            "follow": _bool(obj.get("follow")), "mute": _bool(obj.get("mute")), "share": _bool(obj.get("share")),
            "report": _bool(obj.get("report")), "reason": str(obj.get("reason", ""))[:300]}


def validate_write(obj):
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    if not _bool(obj.get("post")):
        return {"post": False, "reason": str(obj.get("reason", ""))[:300]}
    sub = str(obj.get("subreddit", "")).strip().lower().lstrip("/").removeprefix("r/")
    topic = next((t for t, (s, _) in TOPICS.items() if s.lower().removeprefix("r/") == sub), None)
    title, body = str(obj.get("title") or "").strip(), str(obj.get("body") or "").strip()
    if topic is None or not title or not body:
        raise ValueError(f"post=true but subreddit/title/body missing or unknown ({sub!r})")
    return {"post": True, "topic": topic, "title": title, "body": body, "reason": str(obj.get("reason", ""))[:300]}


def accounts():
    """20 neutral poster handles drawn from the Census name lists (same every round)."""
    rng = random.Random(f"{SEED}|accounts")
    names = [l.split()[0].lower() for f in ("dist.male.first", "dist.female.first") for l in open(os.path.join(SRC, f))][:2000]
    return [f"{rng.choice(names)}_{rng.randint(100, 999)}" for _ in range(N_ACCOUNTS)]


def human_slots(round_no):
    """The human posts of this round: a fixed shuffle of each subreddit's pool, consumed in order, never reused."""
    pool = [json.loads(l) for l in open(os.path.join(SRC, "human_pool.jsonl"))]
    out = {}
    for t in TOPICS:
        posts = sorted([p for p in pool if p["topic"] == t], key=lambda p: p["id"])
        random.Random(f"{SEED}|{t}|order").shuffle(posts)
        idx = (round_no - 1) * SLOTS_PER_TOPIC if round_no < 900 else 300 + (round_no - 900) * SLOTS_PER_TOPIC
        out[t] = posts[idx: idx + SLOTS_PER_TOPIC]
    return out


def seed_bank(round_no, authors_, log):
    """All seed posts of a round, generated once and shared by every model's run."""
    path = os.path.join(DATA, f"seedbank_r{round_no:03d}.jsonl")
    bank = {json.loads(l)["key"]: json.loads(l) for l in open(path)} if os.path.exists(path) else {}
    f = open(path, "a")
    for t, hs in human_slots(round_no).items():
        for k, h in enumerate(hs):
            key = f"r{round_no}|{t}|{k}|human"
            if key not in bank:
                bank[key] = {"key": key, "round": round_no, "topic": t, "slot": k, "author": "human", "title": h["title"],
                             "body": h["body"], "human_id": h["id"], "subject": h["title"], "ok": True}
                f.write(json.dumps(bank[key]) + "\n")
    for au in authors_:
        todo = [(t, k, h) for t, hs in human_slots(round_no).items() for k, h in enumerate(hs)
                if f"r{round_no}|{t}|{k}|{au}" not in bank]
        if not todo:
            continue
        llm.warm(au)
        for t, k, h in todo:
            key = f"r{round_no}|{t}|{k}|{au}"
            sub, name = TOPICS[t]
            obj, meta = llm.chat_json(au, authors.NATURAL_SYSTEM, AUTHOR_USER.format(sub=sub, topic_name=name, subject=h["title"]),
                                      seed=llm.stable_seed(SEED, key), temperature=0.8, num_predict=2000,
                                      validate=authors.validate_natural, retries=4)
            bank[key] = {"key": key, "round": round_no, "topic": t, "slot": k, "author": au, "subject": h["title"],
                         "ok": obj is not None, **(obj or {}), "attempts": meta["attempts"],
                         "latency_s": round(meta["latency_s"], 2), "errors": meta["errors"][-2:]}
            f.write(json.dumps(bank[key]) + "\n"); f.flush()
        log(f"seed posts: {au} wrote {len(todo)}")
    f.close()
    return bank


def git_commit():
    try:
        return subprocess.check_output(["git", "-C", REPO, "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


async def replay(out, people, posts, decisions, writes, model):
    """Rebuild the round as a standard OASIS reddit database, in a fixed order (no LLM calls)."""
    import oasis
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType
    from oasis import DefaultPlatformType
    from oasis.social_agent.agent import SocialAgent
    from oasis.social_agent.agent_graph import AgentGraph
    from oasis.social_platform.config import UserInfo
    from oasis.social_platform.typing import ActionType as A

    db = os.path.join(out, "oasis.db")
    if os.path.exists(db):
        os.remove(db)
    backend = ModelFactory.create(model_platform=ModelPlatformType.OLLAMA, model_type=model, url=llm.OLLAMA_URL + "/v1")
    g, agents = AgentGraph(), {}
    accts = accounts()
    for p in people:
        ui = UserInfo(user_name=p["username"], name=p["name"], description="", profile={"persona": p["persona"]},
                      recsys_type="reddit")
        agents[p["id"]] = SocialAgent(agent_id=p["id"], user_info=ui, model=backend, agent_graph=g)
        g.add_agent(agents[p["id"]])
    acct_agent = {}
    for n, handle in enumerate(accts):
        aid = len(people) + n  # accounts take the ids right after the users (as in Test 6)
        ui = UserInfo(user_name=handle, name=handle, description="", profile={"persona": ""}, recsys_type="reddit")
        acct_agent[handle] = SocialAgent(agent_id=aid, user_info=ui, model=backend, agent_graph=g)
        g.add_agent(acct_agent[handle])
    env = oasis.make(agent_graph=g, platform=DefaultPlatformType.REDDIT, database_path=db)
    await env.reset()
    pid, owner = {}, {}
    for p in sorted((p for p in posts.values() if "writer" not in p), key=lambda p: p["key"]):  # seed posts only
        r = await acct_agent[p["account"]].perform_action_by_data(A.CREATE_POST, content=f"{p['title']}\n\n{p['body']}")
        pid[p["key"]], owner[p["key"]] = r.get("post_id"), acct_agent[p["account"]].social_agent_id
    for w in sorted(writes, key=lambda w: w["user_id"]):
        if w.get("post"):
            r = await agents[w["user_id"]].perform_action_by_data(A.CREATE_POST, content=f"{w['title']}\n\n{w['body']}")
            pid[w["post_key"]], owner[w["post_key"]] = r.get("post_id"), w["user_id"]
    for d in sorted(decisions, key=lambda d: (d["pass"], d["user_id"], d["post_key"])):
        if d["outcome"] != "chose":
            continue
        a, i = agents[d["user_id"]], pid[d["post_key"]]
        if d["vote"] != "none":
            await a.perform_action_by_data(A.LIKE_POST if d["vote"] == "upvote" else A.DISLIKE_POST, post_id=i)
        if d["comment"]:
            await a.perform_action_by_data(A.CREATE_COMMENT, post_id=i, content=d["comment"])
        if d["follow"]:
            await a.perform_action_by_data(A.FOLLOW, followee_id=owner[d["post_key"]])
        if d["mute"]:
            await a.perform_action_by_data(A.MUTE, mutee_id=owner[d["post_key"]])
        if d["share"]:
            await a.perform_action_by_data(A.REPOST, post_id=i)
        if d["report"]:
            await a.perform_action_by_data(A.REPORT_POST, post_id=i, report_reason=d["reason"] or "reported")
    await env.close()


def run(a):
    if not llm.server_up():
        raise SystemExit("Ollama is not running. Start it with:\n  OLLAMA_FLASH_ATTENTION=1 OLLAMA_NUM_PARALLEL=4 "
                         "OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=24h ollama serve > /tmp/ollama_serve.log 2>&1 &")
    authors_ = a.authors.split(",")
    for m in set(authors_ + [a.model]):
        if m not in llm.available_models():
            raise SystemExit(f"model {m} is not pulled (ollama pull {m})")
    people = load_personas()[: a.agents]
    label = f"v2_r{a.round:03d}_{a.model.replace(':', '-')}" + (f"_a{a.agents}" if a.agents < 100 else "")
    out = os.path.join(DATA, "runs", label)
    os.makedirs(out, exist_ok=True)
    logf = open(os.path.join(out, "run.log"), "a")

    def log(msg):
        line = f"{datetime.now():%H:%M:%S} {msg}"
        print(line, flush=True); logf.write(line + "\n"); logf.flush()

    t0 = time.time()
    bank = seed_bank(a.round, authors_, log)
    gen_s = time.time() - t0
    accts = accounts()
    seeds = sorted([p for p in bank.values() if p["ok"]], key=lambda p: p["key"])
    rng = random.Random(f"{SEED}|r{a.round}|accounts")
    shuffled = seeds[:]
    rng.shuffle(shuffled)
    for n, p in enumerate(shuffled):
        p["account"] = accts[n % N_ACCOUNTS]
    posts = {p["key"]: p for p in seeds}
    half = halves(load_personas())

    dec_path, wr_path = os.path.join(out, "decisions.jsonl"), os.path.join(out, "writes.jsonl")
    decisions = [json.loads(l) for l in open(dec_path)] if os.path.exists(dec_path) else []
    writes = [json.loads(l) for l in open(wr_path)] if os.path.exists(wr_path) else []
    done = {(d["pass"], d["user_id"], d["post_key"]) for d in decisions}
    wrote = {w["user_id"] for w in writes}
    pool = ThreadPoolExecutor(a.parallel)

    def scroll(p):
        k = (half[p["id"]] + a.round) % SLOTS_PER_TOPIC
        rng = random.Random(f"{SEED}|r{a.round}|{p['id']}|order")
        order = sorted(TOPICS, key=lambda t: (-["HATE", "DISLIKE", "NEUTRAL", "LIKE", "LOVE"].index(p["stances"][t]), rng.random()))
        feed = []
        for t in order:
            versions = [q for q in seeds if q["topic"] == t and q["slot"] == k]
            rng.shuffle(versions)
            feed += versions
        return feed

    def decide(pss, p, post, pos):
        sub, name = TOPICS[post["topic"]]
        user = POST_USER.format(sub=sub, topic_name=name, account=post["account"], title=post["title"], body=post["body"])
        obj, meta = llm.chat_json(a.model, SYSTEM.format(persona=p["persona"]), user,
                                  seed=llm.stable_seed(SEED, a.round, pss, p["id"], post["key"]), temperature=a.temperature,
                                  num_predict=600, validate=validate_action, retries=2)
        o = obj or {"vote": None, "comment": "", "follow": False, "mute": False, "share": False, "report": False, "reason": None}
        return {"round": a.round, "model": a.model, "pass": pss, "user_id": p["id"], "username": p["username"],
                "topic": post["topic"], "stance": p["stances"][post["topic"]], "pos": pos, "post_key": post["key"],
                "slot": post.get("slot"), "author": post["author"], "account": post["account"],
                "own": int(post["author"] == a.model), "human": int(post["author"] == "human"), **o,
                "post_words": len(post["body"].split()),
                "outcome": "chose" if obj else ("cut_off" if meta["done_reason"] == "length" else "unreadable"),
                "attempts": meta["attempts"], "latency_s": round(meta["latency_s"], 2), "prompt_tokens": meta["prompt_tokens"],
                "eval_tokens": meta["eval_tokens"], "thinking_chars": meta["thinking_chars"],
                "truncation_risk": meta["truncation_risk"], "raw": meta.get("raw")}

    def write_call(p):
        subs = "\n".join(f"- {s} ({n})" for s, n in TOPICS.values())
        obj, meta = llm.chat_json(a.model, SYSTEM.format(persona=p["persona"]), WRITE_USER.format(subs=subs),
                                  seed=llm.stable_seed(SEED, a.round, "write", p["id"]), temperature=a.temperature,
                                  num_predict=1500, validate=validate_write, retries=2)
        o = obj or {"post": False, "reason": None}
        w = {"round": a.round, "model": a.model, "user_id": p["id"], "username": p["username"], **o,
             "outcome": "chose" if obj else "unreadable", "latency_s": round(meta["latency_s"], 2),
             "eval_tokens": meta["eval_tokens"], "raw": meta.get("raw")}
        if w.get("post"):
            w.update({"post_key": f"r{a.round}|user{p['id']}|{a.model}", "author": a.model, "account": p["username"],
                      "leak": bool(LEAK.search(w["title"] + " " + w["body"]))})
        return w

    def gather(jobs, fn, path, sink, what):
        if not jobs:
            return
        llm.warm(a.model)  # only when there is work: a --replay-only pass must not load a model
        t, n, c = time.time(), 0, Counter()
        with open(path, "a") as f:
            for r in pool.map(lambda j: fn(*j), jobs):
                f.write(json.dumps(r) + "\n"); f.flush()
                sink.append(r); n += 1
                c[r.get("vote") or ("post" if r.get("post") else r["outcome"])] += 1
                if n % a.log_every == 0 or n == len(jobs):
                    el = time.time() - t
                    log(f"  {what}: {n}/{len(jobs)} ({el / n:.2f} s each, ETA {(len(jobs) - n) * el / n / 60:.0f} min) {dict(c)}")

    t1 = time.time()
    jobs = [("seed", p, post, i) for p in people for i, post in enumerate(scroll(p)) if ("seed", p["id"], post["key"]) not in done]
    log(f"{a.model} round {a.round}: {len(people)} users, {len(seeds)} seed posts; pass 1: {len(jobs)} decisions to make")
    gather(jobs, decide, dec_path, decisions, "pass 1")
    t2 = time.time()
    gather([(p,) for p in people if p["id"] not in wrote], write_call, wr_path, writes, "posting")
    t3 = time.time()
    organic = {w["post_key"]: {"key": w["post_key"], "topic": w["topic"], "author": w["author"], "account": w["account"],
                               "title": w["title"], "body": w["body"], "writer": w["user_id"]}
               for w in writes if w.get("post")}
    if a.social_n:
        jobs = []
        for p in people:
            others = sorted([q for q in organic.values() if q["writer"] != p["id"]], key=lambda q: q["key"])
            random.Random(f"{SEED}|r{a.round}|{p['id']}|social").shuffle(others)
            jobs += [("social", p, q, i) for i, q in enumerate(others[: a.social_n]) if ("social", p["id"], q["key"]) not in done]
        log(f"pass 2: {len(organic)} user posts, {len(jobs)} decisions to make")
        gather(jobs, decide, dec_path, decisions, "pass 2")
    t4 = time.time()
    if a.replay_only or not a.no_replay:
        asyncio.run(replay(out, people, {**posts, **organic}, decisions, writes, a.model))
    if a.replay_only:
        log(f"replayed {label} into oasis.db in {time.time() - t4:.0f}s")
        return
    man = {"label": label, "design": "v2 (log Part 14)", "round": a.round, "model": a.model, "authors": authors_,
           "agents": len(people), "finished_at": datetime.now().isoformat(), "git_commit": git_commit(),
           "personas_sha256": PINNED_PERSONAS, "human_pool_sha256": hashlib.sha256(open(os.path.join(SRC, "human_pool.jsonl"), "rb").read()).hexdigest(),
           "seedbank_sha256": sha(sorted(bank.values(), key=lambda p: p["key"])),
           "prompts_sha256": sha([SYSTEM, POST_USER, WRITE_USER, AUTHOR_USER, authors.NATURAL_SYSTEM]),
           "config": {"temperature": a.temperature, "author_temperature": 0.8, "num_ctx": llm.NUM_CTX, "think": False,
                      "parallel": a.parallel, "social_n": a.social_n, "slots_per_topic": SLOTS_PER_TOPIC,
                      "accounts": N_ACCOUNTS, "memory": False, "follow_graph": "empty", "vote_counts": "hidden"},
           "ollama_server": llm.server_config(), "ollama_models": llm.model_digests(sorted(set(authors_ + [a.model]))),
           "seconds": {"seed_posts": round(gen_s, 1), "pass1": round(t2 - t1, 1), "posting": round(t3 - t2, 1),
                       "pass2": round(t4 - t3, 1), "replay": round(time.time() - t4, 1)},
           "counts": {"decisions": len(decisions), "writes": len(writes), "user_posts": len(organic),
                      "unreadable": sum(d["outcome"] != "chose" for d in decisions)}}
    json.dump(man, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    log(f"done {label}: {man['seconds']} {man['counts']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--authors", default=",".join(AUTHORS))
    ap.add_argument("--agents", type=int, default=100)
    ap.add_argument("--social-n", type=int, default=10, help="pass 2: user posts each user meets (0 = skip pass 2)")
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--log-every", type=int, default=50)
    ap.add_argument("--no-replay", action="store_true", help="skip building oasis.db (do it later with --replay-only)")
    ap.add_argument("--replay-only", action="store_true", help="only rebuild oasis.db from a finished run's records")
    run(ap.parse_args())
