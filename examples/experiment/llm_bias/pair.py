"""Side-by-side: one persona sees BOTH versions of a post (llama's and gemma's, written from the same brief) at once.

IN PLAIN WORDS
--------------
The A/B test (LD-13, Gordon 2026-09-26). Night 1 showed the posts side by side and asked for a favourite, and
found a clear own-post boost (+5.6). The scroll design shows one post at a time and finds about zero. Is it the
FORMAT that makes the difference? Here the same people meet the same posts as in the scroll arm, but the two
posts written from one brief appear together:

* Topics come in the persona's order (best-loved first), exactly like scrolling.
* Within a topic, the persona's slots come in a fixed per-persona shuffle, and within a slot the two posts are
  in a fixed per-persona order (the same for whichever model plays that persona), so a "Post 1" habit spreads
  evenly over both authors.
* For EACH of the two posts the answer is like / dislike / nothing, the same three choices as scrolling, and
  then the ONE post the persona would most want to open (its favourite), plus a few words of reason.

So the scroll arm and this arm differ only in whether the two sibling posts are seen together.
"""

from __future__ import annotations

import random

from camel.prompts import TextPrompt

import scroll
from topics import TOPICS

SYSTEM_TEMPLATE = TextPrompt(
    "# OBJECTIVE\n"
    "You're a Reddit user scrolling your feed. You'll see two posts at a time and decide what to do with each.\n\n"
    "# SELF-DESCRIPTION\n"
    "Your actions should be consistent with your self-description and personality.\n"
    "{persona}\n\n"
    "# RESPONSE METHOD\n"
    "Reply with a single JSON object and nothing else."
)

USER_TEMPLATE = """You are scrolling {sub} ({topic_name}). The next two posts in your feed:

[Post 1]
Title: {title1}
{body1}

[Post 2]
Title: {title2}
{body2}

What do you do, as yourself? For EACH post choose exactly one:
- "like" (upvote it)
- "dislike" (downvote it)
- "nothing" (no vote, keep scrolling)
Then pick the ONE of the two posts you would most want to open and read (you must pick one).

Reply with JSON only: {{"post_1": "like|dislike|nothing", "post_2": "like|dislike|nothing", "favorite": 1 or 2, "reason": "<a few words, in your own voice>"}}"""


def feed(persona, posts_by_topic, seed):
    """The persona's side-by-side feed: list of (topic_rank, topic, pos_in_topic, [post_a, post_b]).

    Posts are grouped into slots by (round) within a topic; each slot holds one post per author."""
    out = []
    for rank, t in enumerate(scroll.topic_order(persona, list(posts_by_topic))):
        slots = {}
        for p in posts_by_topic[t]:
            slots.setdefault(p["round"], []).append(p)
        keys = sorted(slots)
        random.Random(f"{seed}|{persona['id']}|{t}|pairfeed").shuffle(keys)
        for i, k in enumerate(keys):
            two = sorted(slots[k], key=lambda p: p["author"])
            random.Random(f"{seed}|{persona['id']}|{t}|{k}|pairorder").shuffle(two)
            out.append((rank, t, i, two))
    return out


def render_user(topic, two):
    a, b = two
    return USER_TEMPLATE.format(sub=TOPICS[topic]["sub"], topic_name=TOPICS[topic]["name"],
                                title1=a["title"], body1=a["body"], title2=b["title"], body2=b["body"])


def _act(v):
    a = str(v).strip().lower().strip(".!\"'")
    if a in scroll.LIKE:
        return "like"
    if a in scroll.DISLIKE:
        return "dislike"
    if a in scroll.NOTHING:
        return "nothing"
    raise ValueError(f"unknown action {a!r}")


def validate(obj):
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    acts = [_act(obj.get("post_1", obj.get("1"))), _act(obj.get("post_2", obj.get("2")))]
    fav = str(obj.get("favorite", "")).strip().lower().replace("post", "").strip(" _#")
    if fav not in ("1", "2"):
        raise ValueError(f"favorite {obj.get('favorite')!r}")
    return {"actions": acts, "favorite": int(fav), "reason": str(obj.get("reason", ""))[:300]}
