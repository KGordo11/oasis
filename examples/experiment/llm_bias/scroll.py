"""Scrolling: one persona meets one post at a time and likes, dislikes, or keeps scrolling.

IN PLAIN WORDS
--------------
Design v2 (Gordon, 2026-09-24). There is no "pick your favourite" any more. A
persona scrolls through EVERY post in the world, one at a time, the way you
scroll a feed:

* Topics come in order of how much the persona cares: its best-loved topic
  first, then the next, down to the one it dislikes most. Ties are broken by a
  fixed per-persona coin flip, so the order is the same in every run.
* Within a topic, the posts come in a shuffled order that is fixed per persona
  (again, the same in every run and for every model playing that persona).
* For each post the model answers: "like", "dislike" or "nothing" (keep
  scrolling), with a few words of reason.

Each post is a separate call with no memory of the previous posts, so a post
is judged on its own, not against its neighbours -- "a post on a topic, like,
dislike or nothing, scroll", not a this-or-that comparison. Author names and
vote counts are never shown (vote counts hidden: Gordon, 2026-09-24).

"Nothing" is a real choice, but it is also what a broken answer looks like. So
every call records what happened: a valid answer with a reason, an answer that
could not be read, a timeout, or a reply cut off at the token limit. See
`outcome()`.
"""

from __future__ import annotations

import random

from camel.prompts import TextPrompt

from topics import TOPICS

SYSTEM_TEMPLATE = TextPrompt(
    "# OBJECTIVE\n"
    "You're a Reddit user scrolling your feed. You'll see one post at a time and decide what to do with it.\n\n"
    "# SELF-DESCRIPTION\n"
    "Your actions should be consistent with your self-description and personality.\n"
    "{persona}\n\n"
    "# RESPONSE METHOD\n"
    "Reply with a single JSON object and nothing else."
)

USER_TEMPLATE = """You are scrolling {sub} ({topic_name}). The next post in your feed:

Title: {title}
{body}

What do you do, as yourself? Choose exactly one:
- "like" (upvote it)
- "dislike" (downvote it)
- "nothing" (no vote, keep scrolling)

Reply with JSON only: {{"action": "like|dislike|nothing", "reason": "<a few words, in your own voice>"}}"""

LIKE = {"like", "upvote", "up", "+1", "liked"}
DISLIKE = {"dislike", "downvote", "down", "-1", "disliked"}
NOTHING = {"nothing", "none", "skip", "scroll", "no vote", "keep scrolling", "ignore", "pass"}


def topic_order(persona, topics):
    """Best-loved topic first. Ties broken by a fixed per-persona draw."""
    rng = random.Random(f"{persona['id']}|topic-order")
    tie = {t: rng.random() for t in sorted(topics)}
    return sorted(topics, key=lambda t: (-persona["topic_affinity"][t], tie[t]))


def feed(persona, posts_by_topic, seed):
    """The persona's whole scroll: list of (topic_rank, topic, pos_in_topic, post)."""
    out = []
    for rank, t in enumerate(topic_order(persona, list(posts_by_topic))):
        posts = sorted(posts_by_topic[t], key=lambda p: p["key"])
        random.Random(f"{seed}|{persona['id']}|{t}|scroll").shuffle(posts)
        out.extend((rank, t, i, p) for i, p in enumerate(posts))
    return out


def render_user(topic, post):
    return USER_TEMPLATE.format(sub=TOPICS[topic]["sub"], topic_name=TOPICS[topic]["name"],
                                title=post["title"], body=post["body"])


def validate(obj):
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    a = str(obj.get("action", "")).strip().lower().strip(".!\"'")
    if a in LIKE:
        act = "like"
    elif a in DISLIKE:
        act = "dislike"
    elif a in NOTHING:
        act = "nothing"
    else:
        raise ValueError(f"unknown action {a!r}")
    return {"action": act, "reason": str(obj.get("reason", ""))[:300]}


def outcome(obj, meta):
    """Why a decision ended the way it did -- the tool for 'why so much nothing?'.

    chose       a readable answer (like, dislike, or a deliberate nothing)
    timeout     the request never came back
    cut_off     the reply hit the token limit (e.g. rambling / hidden thinking)
    unreadable  a reply came back but was not a valid answer
    """
    if obj is not None:
        return "chose"
    if meta.get("timeouts") and not meta.get("raw"):
        return "timeout"
    if meta.get("done_reason") == "length":
        return "cut_off"
    return "unreadable"
