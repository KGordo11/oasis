"""The judge: one persona, played by one local model, votes on one topic's posts.

IN PLAIN WORDS
--------------
The model is told who it is (the persona paragraph, in OASIS's reddit system-
message layout) and shown the round's new posts on one topic. For every post it
says up, down or none, and it must name ONE favourite -- the post it would most
want to open. It also gives a one-sentence reason, in character.

What the judge is NOT shown, deliberately:
* who wrote a post (no usernames, no model names -- posts are anonymous);
* vote counts (Sim 2 and Sim 3 showed visible scores drive herding, which would
  swamp the effect we are looking for);
* a fixed order. Every (persona, round, topic) gets its own shuffled order, so a
  model that always picks "Post 1" spreads that bias evenly over all authors.
  The shuffle depends on persona, round, topic and seed -- NOT on the judge
  model -- so every judge model sees each persona's feed in the SAME order.
  That pairing is what makes judge models directly comparable.

Why a JSON answer and not OASIS tool calls: the forced choice needs one
structured answer per persona per topic, and several local models tool-call
unreliably or not at all. The votes are still executed on the OASIS platform as
`like_post` / `dislike_post` actions (see run_bias.py), so the platform record
is standard OASIS.
"""

from __future__ import annotations

import random

from camel.prompts import TextPrompt

from topics import TOPICS

# OASIS's reddit system message (user.py to_reddit_system_message), same three
# headings, with the tool-calling instruction replaced by a JSON one.
SYSTEM_TEMPLATE = TextPrompt(
    "# OBJECTIVE\n"
    "You're a Reddit user. I'll show you some new posts, and you decide how to vote on each one.\n\n"
    "# SELF-DESCRIPTION\n"
    "Your actions should be consistent with your self-description and personality.\n"
    "{persona}\n\n"
    "# RESPONSE METHOD\n"
    "Reply with a single JSON object and nothing else."
)

USER_TEMPLATE = """New posts in {sub} ({topic_name}):

{posts}

Stay in character as yourself. For EVERY post, decide your vote: "up", "down" or "none" (no vote).
Then pick the ONE post you would most want to open and read. You must pick exactly one, even if none of them appeal to you.

Reply with JSON only, in this shape:
{{"votes": {{{vote_shape}}}, "favorite": <post number>, "reason": "<one short sentence, in your own voice>"}}"""

UP = {"up", "upvote", "+1", "1", "like", "yes"}
DOWN = {"down", "downvote", "-1", "dislike", "no"}


def display_order(n_posts, seed, persona_id, rnd, topic):
    order = list(range(n_posts))
    random.Random(f"{seed}|{persona_id}|{rnd}|{topic}|order").shuffle(order)
    return order


def render_user(topic, posts_in_order):
    blocks = [f"[Post {i + 1}]\nTitle: {p['title']}\n{p['body']}" for i, p in enumerate(posts_in_order)]
    shape = ", ".join(f'"{i + 1}": "up|down|none"' for i in range(len(posts_in_order)))
    return USER_TEMPLATE.format(sub=TOPICS[topic]["sub"], topic_name=TOPICS[topic]["name"],
                                posts="\n\n".join(blocks), vote_shape=shape)


def _norm_vote(v):
    s = str(v).strip().lower()
    if s in UP:
        return "up"
    if s in DOWN:
        return "down"
    return "none"


def _post_number(v):
    s = str(v).strip().lower().replace("post", "").strip(" #[]")
    return int(s)


def make_validator(n):
    """Returns validate(obj) -> normalised {votes: {1..n: up|down|none}, favorite: 1..n, reason, missing_votes}."""
    def validate(obj):
        if not isinstance(obj, dict):
            raise ValueError("not an object")
        try:
            fav = _post_number(obj.get("favorite"))
        except (TypeError, ValueError):
            raise ValueError(f"favorite not a number: {obj.get('favorite')!r}")
        if not 1 <= fav <= n:
            raise ValueError(f"favorite {fav} out of range 1..{n}")
        raw_votes = obj.get("votes") or {}
        if isinstance(raw_votes, list):
            raw_votes = {str(i + 1): v for i, v in enumerate(raw_votes)}
        votes, missing = {}, 0
        for i in range(1, n + 1):
            v = raw_votes.get(str(i), raw_votes.get(f"Post {i}", raw_votes.get(i)))
            if v is None:
                missing += 1
            votes[i] = _norm_vote(v) if v is not None else "none"
        if missing > n // 2:
            raise ValueError(f"{missing}/{n} votes missing")
        return {"votes": votes, "favorite": fav, "reason": str(obj.get("reason", ""))[:400],
                "missing_votes": missing}
    return validate
