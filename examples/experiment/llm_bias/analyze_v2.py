"""LLM Bias v2 results (two-turn design, log Part 14 sec. 14.11). Plain tables first, derived numbers after.

IN PLAIN WORDS
--------------
Reads every finished turn in data/llm_bias/v2/r*/ and writes data/llm_bias/v2/summary.md (or summary_test.md):

  Table 1  posting turn: per AI, how many users posted, how many posts, which topics
  Table 2  reading turn: reader AI x whose posts -> % of screens with each action (upvote, downvote, comment, ...)
           and % where the user did nothing. The diagonal (same AI posted and read) is the baseline.
  Table 3  % upvoted by the reader's stance on the post's topic (love .. hate): does the AI play the person?
  Bias     for every pair of AIs i, j (upvote rate, and "did anything" rate):
             (i reading i's posts - j reading i's posts) - (i reading j's posts - j reading j's posts)
           The first bracket is i's edge on its own posts, the second removes i simply being more generous.
           95% range from resampling posts and users together (1,000 draws).
  Noise    stage 1b: the same AI re-reading the same posts with fresh randomness -> how often the same screen got
           the same upvote decision, and how far the rates moved. A real bias has to be bigger than this.

    python analyze_v2.py          # real rounds (< 900)
    python analyze_v2.py --test   # smoke-test rounds (>= 900)
"""
import glob, json, os, random, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "..", "data", "llm_bias", "v2")
SHOW = ["like_post", "dislike_post", "create_comment", "repost", "quote_post", "follow", "mute", "report_post",
        "create_post", "search_posts", "do_nothing"]
STANCES = ["LOVE", "LIKE", "NEUTRAL", "DISLIKE", "HATE"]


def load(test):
    rows = []
    for m in sorted(glob.glob(os.path.join(DATA, "r*", "*.manifest.json"))):
        man = json.load(open(m))
        if (man["round"] >= 900) != test:
            continue
        f = m.replace(".manifest.json", ".jsonl")
        rows += [json.loads(l) for l in open(f)] if os.path.exists(f) else []  # a turn with 0 screens writes no file
    return rows


def has(r, act):
    return any(x["action"] == act for x in r["actions"])


def did_anything(r):
    return any(x["action"] != "do_nothing" for x in r["actions"])


def pct(n, d):
    return f"{100 * n / d:.1f}%" if d else "-"


def dd(rows, i, j, f):
    """Double difference for AIs i, j on measure f (1/0 per screen)."""
    m = defaultdict(list)
    for r in rows:
        m[(r["model"], r["posts_by"])].append(f(r))
    mean = lambda k: sum(m[k]) / len(m[k]) if m[k] else None
    v = [mean((i, i)), mean((j, i)), mean((i, j)), mean((j, j))]
    return None if None in v else (v[0] - v[1]) - (v[2] - v[3])


def boot(rows, i, j, f, n=1000):
    """95% range: resample posts and users together (both are 'clusters' -- the same post/user recurs)."""
    rows = [r for r in rows if r["model"] in (i, j) and r["posts_by"] in (i, j)]
    posts, users = sorted({r["post_key"] for r in rows}), sorted({r["user_id"] for r in rows})
    by = defaultdict(list)
    for r in rows:
        by[(r["post_key"], r["user_id"])].append(r)
    rng, est = random.Random(7), []
    for _ in range(n):
        ps, us = Counter(rng.choices(posts, k=len(posts))), Counter(rng.choices(users, k=len(users)))
        sample = [r for (p, u), rs in by.items() if p in ps and u in us for r in rs for _ in range(ps[p] * us[u])]
        v = dd(sample, i, j, f)
        if v is not None:
            est.append(v)
    est.sort()
    return (est[int(0.025 * len(est))], est[int(0.975 * len(est)) - 1]) if len(est) > 20 else (None, None)


def main(test):
    rows = load(test)
    if not rows:
        raise SystemExit("no finished turns")
    post = [r for r in rows if r["turn"] == "post"]
    read = [r for r in rows if r["turn"] == "read" and r["outcome"] == "chose" and not r["draw"]]
    models = sorted({r["model"] for r in rows})
    L = [f"# LLM Bias v2 results{' (SMOKE TEST)' if test else ''}", "",
         f"Rounds: {sorted({r['round'] for r in rows})}. Screens: {len(rows)} "
         f"({sum(r['outcome'] != 'chose' for r in rows)} unreadable).", "",
         "## Table 1. Posting turn (empty feed, every action available, nobody told to post)", "",
         "| AI playing the users | Users | Users who posted | Posts written | Posts by topic | Other actions taken |",
         "|---|---|---|---|---|---|"]
    for m in models:
        ps = [r for r in post if r["model"] == m]
        wrote = [x for r in ps for x in r["actions"] if x["action"] == "create_post"]
        other = Counter(x["action"] for r in ps for x in r["actions"] if x["action"] != "create_post")
        topics = Counter(str(x.get("subreddit", "?")).lower() for x in wrote)
        L.append(f"| {m} | {len(ps)} | {sum(has(r, 'create_post') for r in ps)} | {len(wrote)} | "
                 f"{', '.join(f'{k} {v}' for k, v in topics.most_common())} | {', '.join(f'{k} {v}' for k, v in other.most_common(6))} |")
    L += ["", "## Table 2. Reading turn: reader AI x whose posts -> % of screens with each action", "",
          "| Reader AI | Posts by | Screens | Did nothing | " + " | ".join(SHOW) + " |",
          "|---|---|---|---|" + "---|" * len(SHOW)]
    cell = defaultdict(list)
    for r in read:
        cell[(r["model"], r["posts_by"])].append(r)
    for m in models:
        for pb in models:
            c = cell[(m, pb)]
            if not c:
                continue
            tag = " (baseline)" if m == pb else ""
            L.append(f"| {m} | {pb}{tag} | {len(c)} | {pct(sum(not did_anything(r) for r in c), len(c))} | "
                     + " | ".join(pct(sum(has(r, a) for r in c), len(c)) for a in SHOW) + " |")
    L += ["", "## Table 3. Reading turn: % upvoted by the reader's stance on the post's topic", "",
          "| Reader AI | Posts by | " + " | ".join(STANCES) + " |", "|---|---|" + "---|" * len(STANCES)]
    for m in models:
        for pb in models:
            c = cell[(m, pb)]
            if c:
                L.append(f"| {m} | {pb} | " + " | ".join(
                    pct(sum(has(r, 'like_post') for r in c if r['stance'] == s), sum(r['stance'] == s for r in c))
                    for s in STANCES) + " |")
    L += ["", "## Own-AI bias (derived; read Table 2 first)", "",
          "For AIs i and j: (i reading i's posts - j reading i's posts) - (i reading j's posts - j reading j's posts). "
          "Positive = i favours its own AI's posts beyond simply being more generous. Points per 100 screens.", "",
          "| i | j | Upvote: bias (95% range) | Did anything: bias (95% range) |", "|---|---|---|---|"]
    for a in range(len(models)):
        for b in range(a + 1, len(models)):
            i, j = models[a], models[b]
            cells = []
            for f in (lambda r: int(has(r, "like_post")), lambda r: int(did_anything(r))):
                v = dd(read, i, j, f)
                lo, hi = boot(read, i, j, f, n=300 if test else 1000) if v is not None else (None, None)
                cells.append("-" if v is None else f"{100 * v:+.1f}" + (f" ({100 * lo:+.1f} to {100 * hi:+.1f})" if lo is not None else ""))
            L.append(f"| {i} | {j} | {cells[0]} | {cells[1]} |")
    redo = [r for r in rows if r["turn"] == "read" and r["draw"] and r["outcome"] == "chose"]
    if redo:
        first = {(r["model"], r["posts_by"], r["user_id"], r["post_key"]): r for r in read}
        L += ["", "## Noise floor (stage 1b): same AI, same posts, re-read with fresh randomness", "",
              "| AI | Screens compared | Same upvote decision | Upvote rate first / re-read |", "|---|---|---|---|"]
        for m in models:
            pairs = [(first.get((r["model"], r["posts_by"], r["user_id"], r["post_key"])), r) for r in redo if r["model"] == m]
            pairs = [(x, y) for x, y in pairs if x]
            if pairs:
                same = sum(has(x, "like_post") == has(y, "like_post") for x, y in pairs)
                L.append(f"| {m} | {len(pairs)} | {pct(same, len(pairs))} | "
                         f"{pct(sum(has(x, 'like_post') for x, _ in pairs), len(pairs))} / {pct(sum(has(y, 'like_post') for _, y in pairs), len(pairs))} |")
    out = os.path.join(DATA, "summary_test.md" if test else "summary.md")
    open(out, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main("--test" in sys.argv)
