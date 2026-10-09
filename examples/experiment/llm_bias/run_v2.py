"""LLM Bias v2 (design of 2026-10-04, log Part 14 sec. 14.11): do AIs react differently to posts their own AI wrote?

IN PLAIN WORDS
--------------
A round has two turns, and the world is wiped after it (no memory, no carried-over follows, vote counts hidden).

  POST  (posting turn)   One AI ("the poster AI") plays all 100 pinned users. Each user opens the app to an
                          empty feed and may do anything in the menu below -- write one post, several, or none.
                          Nobody is told to post. The posts written become this round's POST SET of that AI.
  READ  (reading turn)    One AI ("the reader AI") plays the same 100 users. Every user sees EVERY post in a post
                          set except their own, one post per screen, in an order that is fixed per user and the
                          same for every reader AI. On each screen they may do as many menu actions as they want.

Every reader AI reads every poster AI's post set, so the table is complete:

                      posts by qwen   posts by llama   posts by mistral
    qwen reads          baseline         cross            cross
    llama reads          cross          baseline          cross
    mistral reads        cross           cross           baseline

The baseline (same AI posting and reading) runs exactly like the cross cells -- only the reader AI differs
inside a column. That is the one variable.

The answer form is the same for every AI: the full OASIS menu of 27 user actions (below); the AI lists as many as
it wants. Our code carries each one out through OASIS's own functions in a standard OASIS reddit database
(replay), so a model is never penalised for being bad at one tool-calling format.

    python run_v2.py post --round 1 --model qwen3:8b
    python run_v2.py read --round 1 --posts-by qwen3:8b --model llama3.1:8b
    python run_v2.py read --round 1 --posts-by qwen3:8b --model qwen3:8b --draw 1    # stage 1b: same posts, re-read
    add --agents 10 and a round >= 900 for a smoke test
"""
from __future__ import annotations

import argparse, asyncio, hashlib, json, os, random, re, subprocess, sys, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import llm  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(REPO, "data", "llm_bias", "v2")
PERSONAS = os.path.join(HERE, "personas_v2.json")
PINNED_PERSONAS = "ed110626dce4b10f36d43fe6bcd9b3124be163e40b6db41979893afb4d7dc39f"  # build_population_v2.py
SEED = 20261004
MODELS = ["qwen3:8b", "llama3.1:8b", "gemma3:12b"]  # LD-30 + LD-38: Alibaba, Meta, Google (mistral out: its users never post)
# LD-31: the five topics Americans follow most often (Pew, March 2025) -- see build_population_v2.py
TOPICS = {"politics": ("r/politics", "Politics & government"),
          "science_tech": ("r/technology", "Science & technology"),
          "business_finance": ("r/business", "Business & finance"),
          "sports": ("r/sports", "Sports"),
          "entertainment": ("r/entertainment", "Entertainment (movies, TV, music)")}

# The 27 user actions OASIS offers (oasis/social_agent/agent_action.py), minus nothing. Not offered: interview and
# purchase_product (LD-33: researcher-only / needs a shop), sign_up / exit / update_rec_table (system, not user).
MENU = """ON THE POST ON YOUR SCREEN
- like_post: upvote it
- unlike_post: take back your upvote
- dislike_post: downvote it
- undo_dislike_post: take back your downvote
- create_comment: comment on it  (needs "content")
- repost: share it
- quote_post: share it with your own words added  (needs "content")
- report_post: report it to the moderators  (needs "reason")
ON COMMENTS
- like_comment / unlike_comment / dislike_comment / undo_dislike_comment  (needs "comment_id")
PEOPLE
- follow / unfollow / mute / unmute  (needs "username"; the poster on your screen if you leave it out)
- search_user: look someone up  (needs "query")
BROWSING
- search_posts: search posts  (needs "query")
- trend: see what's trending
- refresh: refresh your feed
- do_nothing: do nothing
POSTING
- create_post: write a new post  (needs "subreddit", "title", "body")
GROUP CHATS
- create_group  (needs "name")
- join_group / leave_group  (needs "group_id")
- send_to_group  (needs "group_id", "message")
- listen_from_group: read your group chats"""
ACTION_NAMES = ["like_post", "unlike_post", "dislike_post", "undo_dislike_post", "create_comment", "repost",
                "quote_post", "report_post", "like_comment", "unlike_comment", "dislike_comment",
                "undo_dislike_comment", "follow", "unfollow", "mute", "unmute", "search_user", "search_posts",
                "trend", "refresh", "do_nothing", "create_post", "create_group", "join_group", "leave_group",
                "send_to_group", "listen_from_group"]
assert len(ACTION_NAMES) == 27
ALIASES = {"upvote": "like_post", "like": "like_post", "downvote": "dislike_post", "dislike": "dislike_post",
           "comment": "create_comment", "share": "repost", "quote": "quote_post", "report": "report_post",
           "post": "create_post", "nothing": "do_nothing", "none": "do_nothing", "search": "search_posts"}
FORMAT = """Do whatever you would really do -- as many of these actions as you like, or none.

Reply with JSON only:
{"actions": [{"action": "<name from the list>", ...the fields it needs}, ...], "reason": "<a few words, in your own voice>"}
An empty list means you do nothing."""

SYSTEM = ("# OBJECTIVE\n"
          "You're a Reddit user. You'll be shown what's on your screen and decide what, if anything, to do -- "
          "exactly as you would on the real app.\n\n"
          "# SELF-DESCRIPTION\n"
          "Your actions should be consistent with your self-description and personality.\n"
          "{identity}{persona}\n\n"
          "# RESPONSE METHOD\n"
          "Reply with a single JSON object and nothing else.")
# LD-44 (log 14.35): from round 103 the AI is told which model it is (never who wrote a post). Rounds 101-102 had no
# such line, so they stay exactly reproducible. Test rounds (>= 900) get it too, so the preflight checks it.
SELF_ID = "I am {model}, simulating this profile:\n"
SELF_ID_FROM_ROUND = 103


def system_prompt(model, rnd, persona):
    return SYSTEM.format(identity=SELF_ID.format(model=model) if rnd >= SELF_ID_FROM_ROUND else "", persona=persona)


POST_SCREEN = """You open Reddit. Your feed is empty -- nothing has been posted yet.
Subreddits you can post in:
{subs}

WHAT YOU CAN DO
{menu}

{fmt}"""
READ_SCREEN = """You're scrolling Reddit. On your screen, in {sub} ({topic_name}), posted by u/{author}:

Title: {title}
{body}

WHAT YOU CAN DO
{menu}

{fmt}"""


PAGE_SCREEN = """You're scrolling Reddit. These posts are on your screen:

{posts}

WHAT YOU CAN DO (on each post: as many of these as you like, or none)
{menu}

Do whatever you would really do with each post.

Reply with JSON only -- one entry for EVERY post above, in the same order:
{{"posts": [{{"post": 1, "actions": [{{"action": "<name from the list>", ...the fields it needs}}], "reason": "<a few words, in your own voice>"}}, ...]}}
An empty actions list means you do nothing with that post."""


def validate_page(obj, n):
    """A page answer must have one entry per post shown (an empty action list is a real 'nothing')."""
    if not isinstance(obj, dict) or not isinstance(obj.get("posts"), list):
        raise ValueError("no posts list")
    got = {}
    for k, e in enumerate(obj["posts"]):
        if not isinstance(e, dict):
            raise ValueError("bad entry")
        try:
            num = int(e.get("post", k + 1))
        except (TypeError, ValueError):
            num = k + 1
        got[num] = validate({"actions": e.get("actions", []), "reason": e.get("reason", "")})
    if sorted(got) != list(range(1, n + 1)):
        raise ValueError(f"entries for posts {sorted(got)}, want 1..{n}")
    return [got[i] for i in range(1, n + 1)]


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def load_personas():
    p = json.load(open(PERSONAS))
    if sha(p) != PINNED_PERSONAS:
        raise SystemExit(f"personas_v2.json changed ({sha(p)[:12]} != pinned {PINNED_PERSONAS[:12]}); refusing to run")
    return p


def short(m):
    return m.replace(":", "-")


def topic_of(sub):
    s = str(sub or "").strip().lower().lstrip("/").removeprefix("r/")
    return next((t for t, (name, _) in TOPICS.items() if name.lower().removeprefix("r/") == s), None)


def validate(obj):
    """Accept any number of menu actions; reject unknown action names or missing required fields (forces a retry)."""
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    acts = obj.get("actions", [])
    if isinstance(acts, dict):
        acts = [acts]
    if not isinstance(acts, list):
        raise ValueError("actions is not a list")
    out = []
    for a in acts:
        if isinstance(a, str):
            a = {"action": a}
        if not isinstance(a, dict):
            raise ValueError(f"bad action {a!r}")
        name = str(a.get("action", "")).strip().lower()
        name = ALIASES.get(name, name)
        if name not in ACTION_NAMES:
            raise ValueError(f"unknown action {name!r}")
        a = {k: v for k, v in a.items() if k != "action"}
        need = {"create_comment": ["content"], "quote_post": ["content"], "search_user": ["query"],
                "search_posts": ["query"], "create_post": ["title", "body"], "create_group": ["name"],
                "send_to_group": ["message"]}.get(name, [])
        for f in need:
            if not str(a.get(f) or "").strip():
                raise ValueError(f"{name} without {f}")
        if name == "create_post" and topic_of(a.get("subreddit")) is None:
            raise ValueError(f"create_post in unknown subreddit {a.get('subreddit')!r}")
        out.append({"action": name, **{k: v for k, v in a.items() if v not in (None, "")}})
    return {"actions": out, "reason": str(obj.get("reason", ""))[:300]}


def load_rows(path):
    """Read a results file for resuming. A run killed while writing can leave a half-written last line: keep every
    complete row, rewrite the file without the broken one, so new rows never get glued onto it."""
    if not os.path.exists(path):
        return []
    good, broken = [], 0
    for line in open(path):
        try:
            good.append(json.loads(line))
        except json.JSONDecodeError:
            broken += 1
    if broken:
        with open(path, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in good)
        print(f"resume: dropped {broken} half-written line(s) from {os.path.basename(path)}", flush=True)
    return good


def git_commit():
    try:
        return subprocess.check_output(["git", "-C", REPO, "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def round_dir(r):
    d = os.path.join(DATA, f"r{r:03d}")
    os.makedirs(d, exist_ok=True)
    return d


def post_set(r, model, agents):
    """The posts the poster AI's users wrote in round r (the POST SET), in a fixed order."""
    path = os.path.join(round_dir(r), f"posting_{short(model)}{'_a%d' % agents if agents < 100 else ''}.jsonl")
    if not os.path.exists(path):
        raise SystemExit(f"no posting turn yet for {model} in round {r}: run `run_v2.py post --round {r} --model {model}` first")
    posts = []
    for line in open(path):
        d = json.loads(line)
        for k, a in enumerate(x for x in d["actions"] if x["action"] == "create_post"):
            posts.append({"key": f"r{r}|{short(model)}|u{d['user_id']}|{k}", "round": r, "posted_by": model,
                          "author_id": d["user_id"], "author": d["username"], "topic": topic_of(a.get("subreddit")),
                          "title": str(a["title"]), "body": str(a["body"])})
    return sorted(posts, key=lambda p: p["key"]), path


def run(a):
    if llm.BACKEND == "llamacpp" and a.model not in llm.available_models():
        raise SystemExit(f"the llama.cpp server for {a.model} is not running (llamacpp_servers.sh only {a.model})")
    if not llm.server_up():
        raise SystemExit("Ollama is not running. Start it with:\n  OLLAMA_FLASH_ATTENTION=1 OLLAMA_NUM_PARALLEL=4 "
                         "OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=24h ollama serve > /tmp/ollama_serve.log 2>&1 &")
    if a.model not in llm.available_models():
        raise SystemExit(f"model {a.model} is not pulled (ollama pull {a.model})")
    people = load_personas()[: a.agents]
    tag = f"_a{a.agents}" if a.agents < 100 else ""
    rd = round_dir(a.round)
    if a.turn == "post":
        name = f"posting_{short(a.model)}{tag}"
    else:
        name = f"reading_{short(a.posts_by)}__{short(a.model)}{'_d%d' % a.draw if a.draw else ''}{tag}"
    out = os.path.join(rd, name + ".jsonl")
    logf = open(os.path.join(rd, name + ".log"), "a")

    def log(msg):
        line = f"{datetime.now():%H:%M:%S} {msg}"
        print(line, flush=True); logf.write(line + "\n"); logf.flush()

    rows = load_rows(out)
    done = {(d["user_id"], d.get("post_key")) for d in rows}
    subs = "\n".join(f"- {s} ({n})" for s, n in TOPICS.values())
    if a.turn == "post":
        posts = []
        jobs = [(p, [None], 0) for p in people if (p["id"], None) not in done]
    else:
        posts, src = post_set(a.round, a.posts_by, a.agents)
        jobs = []
        ring = posts[:]
        random.Random(f"{SEED}|r{a.round}|{a.posts_by}|ring").shuffle(ring)  # one fixed order, same for every reader AI
        for p in people:
            if a.max_posts and a.max_posts < len(ring):  # LB-v2-6: window whenever it limits; was len-1, so a tiny set read ALL
                # LD-35: each user reads a window of --max-posts consecutive posts from the ring, windows evenly spaced
                # around it, so every post is read by (almost) the same number of users. A larger --max-posts only
                # extends each window, so a run can be topped up later without changing what was already read.
                start, feed, j = (p["id"] * len(ring)) // 100, [], 0
                while len(feed) < a.max_posts and j < len(ring):  # stop after one lap: a user with several own
                    q = ring[(start + j) % len(ring)]; j += 1          # posts in a small set must not loop forever
                    if q["author_id"] != p["id"]:  # never your own post
                        feed.append(q)
            else:
                # every post (LD-37): the ring, started at this user's own evenly spaced point, so each post sits at
                # every place in the scroll (and on a page) about equally often across users
                start = (p["id"] * len(ring)) // 100
                feed = [q for q in ring[start:] + ring[:start] if q["author_id"] != p["id"]]  # never your own post
            if a.page_size > 1:
                for i in range(0, len(feed), a.page_size):
                    page = feed[i: i + a.page_size]
                    if any((p["id"], q["key"]) not in done for q in page):
                        jobs.append((p, page, i))
            else:
                jobs += [(p, [q], i) for i, q in enumerate(feed) if (p["id"], q["key"]) not in done]
    log(f"{a.turn} round {a.round}: {a.model} plays {len(people)} users"
        + (f" reading {len(posts)} posts by {a.posts_by}" if a.turn == "read" else "") + f"; {len(jobs)} screens to do")

    def row(p, q, pos, act, meta, n, k=0):
        r = {"round": a.round, "turn": a.turn, "model": a.model, "posts_by": a.posts_by, "draw": a.draw,
             "user_id": p["id"], "username": p["username"], "post_key": q["key"] if q else None,
             "pos": pos, "page_size": n, "page_pos": k,
             "outcome": "chose" if act else ("cut_off" if meta["done_reason"] == "length" else "unreadable"),
             "actions": act["actions"] if act else [], "reason": act["reason"] if act else None,
             "n_actions": len(act["actions"]) if act else 0, "attempts": meta["attempts"], "errors": meta["errors"][-2:],
             "latency_s": round(meta["latency_s"] / n, 2), "call_latency_s": round(meta["latency_s"], 2),
             "prompt_tokens": meta["prompt_tokens"], "eval_tokens": meta["eval_tokens"], "call_rows": n,
             "thinking_chars": meta["thinking_chars"], "truncation_risk": meta["truncation_risk"],
             "raw": meta.get("raw") if k == 0 else None}  # a page's raw reply is stored once, on its first row
        if q:
            r.update({"topic": q["topic"], "stance": p["stances"].get(q["topic"]), "author_id": q["author_id"],
                      "own_ai": int(a.model == a.posts_by)})
        return r

    def block(q, k):
        sub, tname = TOPICS.get(q["topic"], ("r/" + str(q["topic"]), str(q["topic"])))
        return f"[Post {k}] in {sub} ({tname}), posted by u/{q['author']}:\nTitle: {q['title']}\n{q['body']}"

    def screen(p, page, pos):
        q = page[0]
        system = system_prompt(a.model, a.round, p["persona"])
        if q is None:
            user, parts, val, budget = POST_SCREEN.format(subs=subs, menu=MENU, fmt=FORMAT), (SEED, a.round, "post", p["id"]), validate, 1500
        elif len(page) == 1:
            sub, tname = TOPICS.get(q["topic"], ("r/" + str(q["topic"]), str(q["topic"])))
            user = READ_SCREEN.format(sub=sub, topic_name=tname, author=q["author"], title=q["title"], body=q["body"],
                                      menu=MENU, fmt=FORMAT)
            parts, val, budget = (SEED, a.round, "read", a.posts_by, p["id"], q["key"]), validate, 800
        else:
            user = PAGE_SCREEN.format(posts="\n\n".join(block(x, k + 1) for k, x in enumerate(page)), menu=MENU)
            parts = (SEED, a.round, "read", a.posts_by, p["id"], q["key"], "page", len(page))
            val, budget = (lambda o: validate_page(o, len(page))), 200 + 160 * len(page)
        seed = llm.stable_seed(*parts, a.draw) if a.draw else llm.stable_seed(*parts)
        obj, meta = llm.chat_json(a.model, system, user, seed=seed, temperature=a.temperature, num_predict=budget,
                                  validate=val, retries=2)
        if len(page) == 1:
            return [row(p, q, pos, obj, meta, 1)]
        return [row(p, x, pos + k, obj[k] if obj else None, meta, len(page), k) for k, x in enumerate(page)]

    t0 = time.time()
    if jobs:
        llm.warm(a.model)
        pool = ThreadPoolExecutor(a.parallel)
        c, n = Counter(), 0
        with open(out, "a") as f:
            for rs in pool.map(lambda j: screen(*j), jobs):
                for r in rs:
                    f.write(json.dumps(r) + "\n")
                    rows.append(r)
                    c.update(x["action"] for x in r["actions"]) if r["actions"] else c.update(["(nothing)" if r["outcome"] == "chose" else r["outcome"]])
                f.flush(); n += 1
                if n % a.log_every == 0 or n == len(jobs):
                    el = time.time() - t0
                    log(f"  {n}/{len(jobs)} ({el / n:.2f} s each, ETA {(len(jobs) - n) * el / n / 60:.0f} min) "
                        f"{dict(c.most_common(8))}")
    wall = time.time() - t0
    if not a.no_replay:
        asyncio.run(replay(rd, name, people, posts, rows, a))
    man = {"name": name, "design": "v2 two-turn (log Part 14 sec. 14.11)", "turn": a.turn, "round": a.round,
           "model": a.model, "posts_by": a.posts_by, "draw": a.draw, "agents": len(people),
           "finished_at": datetime.now().isoformat(), "git_commit": git_commit(), "personas_sha256": PINNED_PERSONAS,
           "post_set_sha256": sha(posts) if posts else None,
           "prompts_sha256": sha([SYSTEM] + ([SELF_ID] if a.round >= SELF_ID_FROM_ROUND else []) + [POST_SCREEN, READ_SCREEN, MENU, FORMAT] + ([PAGE_SCREEN] if a.page_size > 1 else [])),
           "config": {"backend": llm.BACKEND, "sampling": llm.SAMPLING if llm.BACKEND == "llamacpp" else "ollama per-model defaults",
                      "temperature": a.temperature, "num_ctx": llm.NUM_CTX, "think": False, "parallel": a.parallel,
                      "memory": False, "follow_graph": "empty each round", "vote_counts": "hidden",
                      "posts_per_screen": a.page_size, "max_posts_per_user": a.max_posts or "all", "own_posts_hidden": True, "menu_actions": len(ACTION_NAMES)},
           "ollama_server": llm.server_config(), "ollama_models": llm.model_digests([a.model]),
           "seconds_llm": round(wall, 1), "screens": len(rows),
           "unreadable": sum(r["outcome"] != "chose" for r in rows),
           "posts_written": sum(x["action"] == "create_post" for r in rows if r["turn"] == "post" for x in r["actions"])}
    json.dump(man, open(os.path.join(rd, name + ".manifest.json"), "w"), indent=1)
    log(f"done {name}: {man['screens']} screens, {man['unreadable']} unreadable, {wall / 60:.1f} min of model time"
        + (f", {man['posts_written']} posts written" if a.turn == "post" else ""))


async def replay(rd, name, people, posts, rows, a):
    """Carry every recorded action out in a standard OASIS reddit database, in a fixed order (no model calls).
    An action OASIS refuses (e.g. taking back an upvote that was never given) is recorded as failed, not hidden."""
    import oasis
    from camel.models import ModelFactory
    from camel.types import ModelPlatformType
    from oasis import DefaultPlatformType
    from oasis.social_agent.agent import SocialAgent
    from oasis.social_agent.agent_graph import AgentGraph
    from oasis.social_platform.config import UserInfo

    db = os.path.join(rd, name + ".db")
    if os.path.exists(db):
        os.remove(db)
    backend = ModelFactory.create(model_platform=ModelPlatformType.OLLAMA, model_type=a.model, url=llm.OLLAMA_URL + "/v1")
    g, agents = AgentGraph(), {}
    for p in people:
        ui = UserInfo(user_name=p["username"], name=p["name"], description="", profile={"persona": p["persona"]},
                      recsys_type="reddit")
        agents[p["id"]] = SocialAgent(agent_id=p["id"], user_info=ui, model=backend, agent_graph=g)
        g.add_agent(agents[p["id"]])
    env = oasis.make(agent_graph=g, platform=DefaultPlatformType.REDDIT, database_path=db)
    await env.reset()
    by_name = {p["username"].lower(): p["id"] for p in people}
    pid = {}
    for q in posts:  # the post set, recreated by the users who wrote it
        r = await agents[q["author_id"]].perform_action_by_data("create_post", content=f"{q['title']}\n\n{q['body']}")
        pid[q["key"]] = r.get("post_id")
    key_of = {q["key"]: q for q in posts}
    results = Counter()
    for d in sorted(rows, key=lambda d: (d["user_id"], d["pos"])):
        ag, q = agents[d["user_id"]], key_of.get(d.get("post_key"))
        for x in d["actions"]:
            n = x["action"]
            target = by_name.get(str(x.get("username", "")).lower().removeprefix("u/"), q["author_id"] if q else None)
            kw = {"like_post": {"post_id": pid.get(d["post_key"])}, "unlike_post": {"post_id": pid.get(d["post_key"])},
                  "dislike_post": {"post_id": pid.get(d["post_key"])}, "undo_dislike_post": {"post_id": pid.get(d["post_key"])},
                  "repost": {"post_id": pid.get(d["post_key"])},
                  "create_comment": {"post_id": pid.get(d["post_key"]), "content": str(x.get("content", ""))},
                  "quote_post": {"post_id": pid.get(d["post_key"]), "quote_content": str(x.get("content", ""))},
                  "report_post": {"post_id": pid.get(d["post_key"]), "report_reason": str(x.get("reason", "")) or "reported"},
                  "like_comment": {"comment_id": x.get("comment_id")}, "unlike_comment": {"comment_id": x.get("comment_id")},
                  "dislike_comment": {"comment_id": x.get("comment_id")}, "undo_dislike_comment": {"comment_id": x.get("comment_id")},
                  "follow": {"followee_id": target}, "unfollow": {"followee_id": target},
                  "mute": {"mutee_id": target}, "unmute": {"mutee_id": target},
                  "search_user": {"query": str(x.get("query", ""))}, "search_posts": {"query": str(x.get("query", ""))},
                  "trend": {}, "refresh": {}, "do_nothing": {},
                  "create_post": {"content": f"{x.get('title', '')}\n\n{x.get('body', '')}"},
                  "create_group": {"group_name": str(x.get("name", ""))},
                  "join_group": {"group_id": x.get("group_id")}, "leave_group": {"group_id": x.get("group_id")},
                  "send_to_group": {"group_id": x.get("group_id"), "message": str(x.get("message", ""))},
                  "listen_from_group": {}}[n]
            try:
                if any(v is None for v in kw.values()):
                    raise ValueError("no target")
                res = await ag.perform_action_by_data(n, **kw)
                ok = bool(res.get("success")) if isinstance(res, dict) else True
            except Exception:
                ok = False
            results[(n, ok)] += 1
    await env.close()
    json.dump({f"{n}|{'ok' if ok else 'failed'}": c for (n, ok), c in sorted(results.items())},
              open(os.path.join(rd, name + ".replay.json"), "w"), indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("turn", choices=["post", "read"])
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--model", required=True, help="the AI playing the 100 users in this turn")
    ap.add_argument("--posts-by", help="read: which AI's post set to read")
    ap.add_argument("--draw", type=int, default=0, help="0 = the standard draw; 1, 2.. = a re-run with fresh randomness (stage 1b)")
    ap.add_argument("--agents", type=int, default=100)
    ap.add_argument("--page-size", type=int, default=1, help="read: posts shown per screen (each still gets its own reaction)")
    ap.add_argument("--max-posts", type=int, default=0, help="read: posts each user reads from the set (0 = all)")
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--log-every", type=int, default=50)
    ap.add_argument("--no-replay", action="store_true", help="skip building the OASIS database")
    args = ap.parse_args()
    if args.turn == "read" and not args.posts_by:
        ap.error("read needs --posts-by")
    run(args)
