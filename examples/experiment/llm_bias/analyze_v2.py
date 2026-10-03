"""LLM Bias v2 results: plain tables first, derived numbers after. (Log Part 14.)

IN PLAIN WORDS
--------------
Reads every finished v2 run (data/llm_bias/v2/runs/*/decisions.jsonl) and writes data/llm_bias/v2/summary.md:

  Table 1  who played the users x who wrote the post -> upvote / downvote / none, as counts and % (pass 1, seed posts)
  Table 2  the same rows -> comment / follow / mute / share / report, % of decisions
  Table 3  stance (love .. hate) x author -> % upvoted
  Table 4  posting (did the user write a post?) and pass 2 (reactions to other users' posts) per model
  Then     own-AI boost = (model's users upvoting the model's posts) - (OTHER models' users upvoting those same posts),
           the fair test that cancels "this AI just writes better posts"; and each model's own posts vs human posts.

    python analyze_v2.py            # all real rounds (1-899)
    python analyze_v2.py --test     # the smoke-test rounds (900+)
"""
import glob, json, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "..", "data", "llm_bias", "v2")
ACTS = ["comment", "follow", "mute", "share", "report"]
STANCES = ["LOVE", "LIKE", "NEUTRAL", "DISLIKE", "HATE"]


def load(test):
    dec, wr = [], []
    for d in sorted(glob.glob(os.path.join(DATA, "runs", "v2_r*"))):
        if not os.path.exists(os.path.join(d, "manifest.json")):
            continue  # unfinished run
        rnd = json.load(open(os.path.join(d, "manifest.json")))["round"]
        if (rnd >= 900) != test:
            continue
        dec += [json.loads(l) for l in open(os.path.join(d, "decisions.jsonl"))]
        wr += [json.loads(l) for l in open(os.path.join(d, "writes.jsonl"))]
    return dec, wr


def pct(n, d):
    return f"{100 * n / d:.1f}%" if d else "-"


def main(test=False):
    dec, wr = load(test)
    if not dec:
        raise SystemExit("no finished runs")
    seed = [d for d in dec if d["pass"] == "seed" and d["outcome"] == "chose"]
    models = sorted({d["model"] for d in dec})
    authors = ["human"] + [m for m in sorted({d["author"] for d in seed}) if m != "human"]
    L = [f"# LLM Bias v2 results{' (SMOKE TEST)' if test else ''}", "",
         f"Rounds: {sorted({d['round'] for d in dec})}. Decisions: {len(dec)} "
         f"({sum(d['outcome'] != 'chose' for d in dec)} unreadable). Users' own posts: {sum(bool(w.get('post')) for w in wr)}.", "",
         "## Table 1. Seed posts: who played the users x who wrote the post", "",
         "| Users played by | Post written by | Decisions | Upvote | Downvote | None |", "|---|---|---|---|---|---|"]
    cell = defaultdict(list)
    for d in seed:
        cell[(d["model"], d["author"])].append(d)
    for m in models:
        for au in authors:
            c = cell[(m, au)]
            v = Counter(d["vote"] for d in c)
            tag = " (own)" if au == m else ""
            L.append(f"| {m} | {au}{tag} | {len(c)} | {v['upvote']} ({pct(v['upvote'], len(c))}) | "
                     f"{v['downvote']} ({pct(v['downvote'], len(c))}) | {v['none']} ({pct(v['none'], len(c))}) |")
    L += ["", "## Table 2. Seed posts: other actions (% of decisions)", "",
          "| Users played by | Post written by | " + " | ".join(ACTS) + " |", "|---|---|" + "---|" * len(ACTS)]
    for m in models:
        for au in authors:
            c = cell[(m, au)]
            L.append(f"| {m} | {au} | " + " | ".join(pct(sum(bool(d[a]) for d in c), len(c)) for a in ACTS) + " |")
    L += ["", "## Table 3. Seed posts: % upvoted, by the user's stance on the topic", "",
          "| Users played by | Post written by | " + " | ".join(STANCES) + " |", "|---|---|" + "---|" * len(STANCES)]
    for m in models:
        for au in authors:
            c = cell[(m, au)]
            L.append(f"| {m} | {au} | " + " | ".join(
                pct(sum(d["vote"] == "upvote" for d in c if d["stance"] == s), sum(d["stance"] == s for d in c)) for s in STANCES) + " |")
    L += ["", "## Table 4. Users writing their own posts, and reactions to them (pass 2)", "",
          "| Model | Users asked | Wrote a post | Pass-2 decisions | Upvote | Downvote | Comment |", "|---|---|---|---|---|---|---|"]
    for m in models:
        w = [x for x in wr if x["model"] == m]
        s2 = [d for d in dec if d["model"] == m and d["pass"] == "social" and d["outcome"] == "chose"]
        L.append(f"| {m} | {len(w)} | {sum(bool(x.get('post')) for x in w)} ({pct(sum(bool(x.get('post')) for x in w), len(w))}) | "
                 f"{len(s2)} | {pct(sum(d['vote'] == 'upvote' for d in s2), len(s2))} | "
                 f"{pct(sum(d['vote'] == 'downvote' for d in s2), len(s2))} | {pct(sum(bool(d['comment']) for d in s2), len(s2))} |")
    up = lambda m, au: (sum(d["vote"] == "upvote" for d in cell[(m, au)]) / len(cell[(m, au)])) if cell[(m, au)] else None
    L += ["", "## Own-AI boost (derived; read Table 1 first)", "",
          "Own-AI boost = how often a model's users upvote that model's posts, minus how often the OTHER models' users "
          "upvote those same posts. It cancels 'this AI just writes better posts'. Own vs human = the same model's users, "
          "its own posts minus the human posts.", "",
          "| Model | Its users upvote its posts | Other models' users upvote its posts | Own-AI boost (points per 100) | Its users upvote human posts | Own vs human |",
          "|---|---|---|---|---|---|"]
    for m in models:
        if m not in authors:
            continue
        own = up(m, m)
        others = [up(o, m) for o in models if o != m and up(o, m) is not None]
        oth = sum(others) / len(others) if others else None
        hum = up(m, "human")
        f = lambda x: f"{100 * x:.1f}%" if x is not None else "-"
        g = lambda a, b: f"{100 * (a - b):+.1f}" if a is not None and b is not None else "-"
        L.append(f"| {m} | {f(own)} | {f(oth)} | {g(own, oth)} | {f(hum)} | {g(own, hum)} |")
    out = os.path.join(DATA, "summary_test.md" if test else "summary.md")
    open(out, "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main("--test" in sys.argv)
