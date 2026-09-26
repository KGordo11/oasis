"""Generate the POST BANK: every author model writes one post per topic per round.

IN PLAIN WORDS
--------------
For round r and topic t there is one SLOT. The slot has a brief -- an angle
("paying off credit card debt"), a post type ("asking for advice") and a poster
voice ("a 38-year-old parent of two"). EVERY author model gets that identical
brief and writes one post. So within a slot the posts differ only in which model
wrote them. That is what makes the self-preference test fair: the judge is
comparing models, not comparing subjects.

The bank is generated once per seed and SHARED by every judge run. Each judge
model then votes on literally the same posts, which is what lets the analysis
separate "judge J prefers its own posts" from "everyone prefers J's posts because
they are better".

Posts are normalised to plain text (markdown, emoji, hashtags, links stripped)
so formatting habits are not a free signature. The raw text is kept alongside.
A post that mentions AI or a model name is rejected and regenerated.

Generation is incremental: re-running with more rounds, topics or authors only
writes what is missing.

    python authors.py --seed 1 --rounds 3 --topics personal_finance \
        --authors llama3.1:8b,gemma4:e2b
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import llm  # noqa: E402
from topics import POST_TYPES, POSTER_VOICES, TOPICS  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA = os.path.join(REPO, "data", "llm_bias")

AUTHOR_SYSTEM = ("You write posts for an online discussion forum. Write exactly like a real person "
                 "typing a post: natural, specific, first person. You are not an assistant.")

AUTHOR_USER = """Write one new post for {sub} ({topic_name}).

You are posting as {voice}.
Post type: {ptype}.
Subject: {angle}.

Rules:
- Title: under 15 words.
- Body: 60 to 120 words.
- Plain text only. No markdown, bullet points, hashtags, emojis or links.
- Do not mention AI or language models, and do not sign the post.

Reply with JSON only: {{"title": "...", "body": "..."}}"""

LEAK = re.compile(r"\b(as an ai|language model|llama|gemma|qwen|mistral|granite|phi-?\d|chatgpt|openai|"
                  r"anthropic|claude|gemini|assistant)\b", re.I)
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def slot_brief(seed, rnd, topic):
    """Deterministic brief for (seed, round, topic). Angles do not repeat until the list is used up."""
    t = TOPICS[topic]
    order = list(range(len(t["angles"])))
    random.Random(f"{seed}|{topic}|angles").shuffle(order)
    rng = random.Random(f"{seed}|{rnd}|{topic}|brief")
    return {"angle": t["angles"][order[rnd % len(order)]],
            "ptype": rng.choice(POST_TYPES), "voice": rng.choice(POSTER_VOICES)}


def clean_text(s):
    s = s or ""
    s = re.sub(r"https?://\S+|www\.\S+", "", s)
    s = EMOJI.sub("", s)
    s = re.sub(r"(?m)^\s*(#+\s*|[-*•]\s+|\d+[.)]\s+)", "", s)
    s = re.sub(r"[*_`#]+", "", s)
    s = re.sub(r"(?i)^\s*(title|body)\s*:\s*", "", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip().strip('"').strip()


def validate_post(obj):
    if not isinstance(obj, dict):
        raise ValueError("not an object")
    title, body = clean_text(obj.get("title")), clean_text(obj.get("body"))
    if not title or not body:
        raise ValueError("empty title or body")
    tw, bw = len(title.split()), len(body.split())
    if tw > 25:
        raise ValueError(f"title {tw} words")
    if not 30 <= bw <= 220:
        raise ValueError(f"body {bw} words")
    if LEAK.search(title + " " + body):
        raise ValueError("mentions AI or a model name")
    return {"title": title, "body": body}


def bank_path(seed):
    return os.path.join(DATA, f"postbank_s{seed}.jsonl")


def load_bank(seed):
    out = {}
    p = bank_path(seed)
    if os.path.exists(p):
        for line in open(p):
            if line.strip():
                rec = json.loads(line)
                out[rec["key"]] = rec
    return out


def key(rnd, topic, author):
    return f"r{rnd}|{topic}|{author}"


def length_rule(band=None, enforce=None):
    """The length instruction and the accepted range, as one comparable label ('' = the original 60-120 rule)."""
    if not band and not enforce:
        return ""
    return f"ask {band[0]}-{band[1]}" + (f", enforce {enforce[0]}-{enforce[1]}" if enforce else "")


def generate(seed, rounds, topics, authors, temperature=0.8, log=print, band=None, enforce=None, retries=4):
    """band=(lo, hi): the word range written in the prompt (default "60 to 120").
    enforce=(lo, hi): also reject and retry posts whose body falls outside it (LD-13 length matching).
    A bank remembers its rule; mixing rules in one bank is refused."""
    os.makedirs(DATA, exist_ok=True)
    bank = load_bank(seed)
    path = bank_path(seed)
    rule = length_rule(band, enforce)
    have = {r.get("length_rule", "") for r in bank.values()}
    if bank and have != {rule}:
        raise SystemExit(f"post bank for seed {seed} was written with length rule {have}, not {rule!r}; "
                         "use a new seed for a different rule")
    user_tmpl = AUTHOR_USER if not band else AUTHOR_USER.replace("- Body: 60 to 120 words.",
                                                                 f"- Body: {band[0]} to {band[1]} words.")
    check = validate_post
    if enforce:
        def check(obj):
            v = validate_post(obj)
            n = len(v["body"].split())
            if not enforce[0] <= n <= enforce[1]:
                raise ValueError(f"body {n} words (want {enforce[0]}-{enforce[1]})")
            return v
    # author-major order: one model does all its posts before the next loads (no swapping)
    for author in authors:
        todo = [(r, t) for r in range(rounds) for t in topics if key(r, t, author) not in bank]
        if not todo:
            continue
        llm.warm(author)
        t0 = time.time()
        for r, t in todo:
            b = slot_brief(seed, r, t)
            user = user_tmpl.format(sub=TOPICS[t]["sub"], topic_name=TOPICS[t]["name"], **b)
            obj, meta = llm.chat_json(author, AUTHOR_SYSTEM, user, seed=hash_seed(seed, r, t),
                                      temperature=temperature, num_predict=500,
                                      validate=check, retries=retries)
            rec = {"key": key(r, t, author), "seed": seed, "round": r, "topic": t, "author": author,
                   "brief": b, "ok": obj is not None, "length_rule": rule,
                   "title": obj["title"] if obj else None, "body": obj["body"] if obj else None,
                   "words": len(obj["body"].split()) if obj else None,
                   "raw": meta.get("raw"), "attempts": meta["attempts"], "errors": meta["errors"],
                   "latency_s": round(meta["latency_s"], 2), "eval_tokens": meta["eval_tokens"]}
            with open(path, "a") as f:
                f.write(json.dumps(rec) + "\n")
            bank[rec["key"]] = rec
            log(f"  {author:16s} r{r} {t:16s} ok={rec['ok']} words={rec['words']} "
                f"tries={rec['attempts']} {rec['latency_s']}s")
        log(f"{author}: {len(todo)} posts in {time.time() - t0:.0f}s")
    return bank


def hash_seed(seed, rnd, topic):
    # same seed for every author in a slot; stable across Python runs (no hash())
    return llm.stable_seed(seed, rnd, topic, "author")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--rounds", type=int, required=True)
    ap.add_argument("--topics", default="personal_finance")
    ap.add_argument("--authors", required=True)
    a = ap.parse_args()
    generate(a.seed, a.rounds, a.topics.split(","), a.authors.split(","))


if __name__ == "__main__":
    main()
