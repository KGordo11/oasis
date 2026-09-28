"""What does self-preference do to a real feed? (LD-16 item 4, design LD-17.)

IN PLAIN WORDS
--------------
In most AI simulations ONE AI plays the whole crowd. Here one AI (the "crowd") plays all the people, and the posts
are the natural three-AI posts already written for a post set (llama, gemma, mistral; nothing new is written).
People arrive one at a time in a fixed random order. Each sees a feed of K posts and likes, dislikes or skips each:
  visible  the feed is the current top K by score (likes - dislikes), with the counts shown ("12 likes, 3 dislikes");
           counts update after each person, so early reactions can snowball
  hidden   K posts drawn at random for that person, no counts (the no-herding baseline)
At the end every post has a score; the leaderboard shows whose posts reached the top. Comparing crowds on the same
posts: when llama runs the crowd, do llama's posts take more of the top 10 than when gemma or mistral run it?

Same people, same persona prompt and same answer format as the scroll runs (scroll.py).

    python run_feed.py --seed 40 --crowd llama3.1:8b --mode visible --label feed_s40_llama_vis
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors  # noqa: E402
import llm  # noqa: E402
import personas as persona_mod  # noqa: E402
import scroll  # noqa: E402
from topics import PRIMARY, TOPICS  # noqa: E402

OUT = os.path.join(authors.DATA, "feeds")
AUTHORS3 = ["llama3.1:8b", "gemma4:e2b", "mistral:7b"]

VISIBLE_USER = """You are scrolling {sub} ({topic_name}). The next post in your feed:

Title: {title}
{body}

Votes so far: {likes} likes, {dislikes} dislikes.

What do you do, as yourself? Choose exactly one:
- "like" (upvote it)
- "dislike" (downvote it)
- "nothing" (no vote, keep scrolling)

Reply with JSON only: {{"action": "like|dislike|nothing", "reason": "<a few words, in your own voice>"}}"""


def load_posts(seed):
    """The post set's natural posts, complete briefs only (every author present), as in the v3 runs."""
    bank = [r for r in authors.load_bank(seed).values() if r.get("ok") and r["topic"] in PRIMARY]
    by_slot = {}
    for r in bank:
        by_slot.setdefault((r["topic"], r["round"]), {})[r["author"]] = r
    return [p for s in by_slot.values() if set(s) >= set(AUTHORS3) for p in s.values() if p["author"] in AUTHORS3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--crowd", required=True, help="the one AI that plays every person")
    ap.add_argument("--mode", choices=["visible", "hidden"], required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--agents", type=int, default=50)
    ap.add_argument("--k", type=int, default=15, help="posts in each person's feed")
    ap.add_argument("--order", type=int, default=0, help="arrival-order draw")
    ap.add_argument("--parallel", type=int, default=4)
    a = ap.parse_args()
    posts = load_posts(a.seed)
    if not posts:
        raise SystemExit(f"no complete post set for seed {a.seed}")
    out = os.path.join(OUT, a.label)
    os.makedirs(out, exist_ok=True)
    people = persona_mod.core99()[:a.agents]
    arrival = list(range(len(people)))
    random.Random(f"{a.seed}|{a.order}|arrival").shuffle(arrival)
    score = {p["key"]: {"like": 0, "dislike": 0, "nothing": 0} for p in posts}
    tie = {p["key"]: random.Random(f"{a.seed}|{p['key']}|tie").random() for p in posts}
    llm.warm(a.crowd)
    t0 = time.time()
    dec = open(os.path.join(out, "decisions.jsonl"), "w")
    pool = ThreadPoolExecutor(max_workers=a.parallel)
    for turn, i in enumerate(arrival):
        p = people[i]
        if a.mode == "visible":
            ranked = sorted(posts, key=lambda q: (-(score[q["key"]]["like"] - score[q["key"]]["dislike"]), tie[q["key"]]))
            feed = ranked[:a.k]
        else:
            feed = random.Random(f"{a.seed}|{a.order}|{p['id']}|feed").sample(posts, a.k)
        system = scroll.SYSTEM_TEMPLATE.format(persona=p["persona"])
        shown = {q["key"]: dict(score[q["key"]]) for q in feed}

        def decide(q, pos):
            t = q["topic"]
            if a.mode == "visible":
                user = VISIBLE_USER.format(sub=TOPICS[t]["sub"], topic_name=TOPICS[t]["name"], title=q["title"], body=q["body"],
                                           likes=shown[q["key"]]["like"], dislikes=shown[q["key"]]["dislike"])
            else:
                user = scroll.render_user(t, q)
            obj, meta = llm.chat_json(a.crowd, system, user, seed=llm.stable_seed(a.seed, p["id"], q["key"], "feed", a.order),
                                      temperature=0.7, num_predict=120, validate=scroll.validate, retries=2)
            return {"turn": turn, "agent_id": p["id"], "post_key": q["key"], "author": q["author"], "topic": t,
                    "feed_pos": pos, "shown_likes": shown[q["key"]]["like"], "shown_dislikes": shown[q["key"]]["dislike"],
                    "affinity": p["topic_affinity"][t], "action": obj["action"] if obj else None,
                    "reason": obj["reason"] if obj else None, "outcome": scroll.outcome(obj, meta),
                    "latency_s": round(meta["latency_s"], 2)}
        rows = list(pool.map(lambda x: decide(*x), [(q, n) for n, q in enumerate(feed)]))
        for d in rows:  # counts update only after the whole person has scrolled
            if d["action"]:
                score[d["post_key"]][d["action"]] += 1
            dec.write(json.dumps(d) + "\n")
        dec.flush()
    wall = time.time() - t0
    board = sorted(({"key": q["key"], "author": q["author"], "topic": q["topic"], "title": q["title"], "words": q["words"],
                     **score[q["key"]], "score": score[q["key"]]["like"] - score[q["key"]]["dislike"]} for q in posts),
                   key=lambda r: (-r["score"], tie[r["key"]]))
    for n, r in enumerate(board):
        r["rank"] = n + 1
    top10 = {au: sum(1 for r in board[:10] if r["author"] == au) for au in AUTHORS3}
    json.dump(board, open(os.path.join(out, "leaderboard.json"), "w"), indent=1)
    json.dump({"label": a.label, "seed": a.seed, "crowd": a.crowd, "mode": a.mode, "agents": a.agents, "k": a.k,
               "order": a.order, "posts": len(posts), "wall_s": round(wall, 1), "top10_by_author": top10,
               "ollama_models": llm.model_digests([a.crowd]), "ollama_server": llm.server_config(),
               "finished_at": datetime.now().isoformat()}, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(f"{a.label}: {wall / 60:.1f} min, top 10 by author {top10}")


if __name__ == "__main__":
    main()
