"""Self-recognition probe (LQ-2): can a model tell which post it wrote?

IN PLAIN WORDS
--------------
No persona here. Each model is shown the posts of one slot (same brief, one per
author model), shuffled, and told: "one of these was written by you -- which?".
Chance is one in the number of posts.

Why it matters: if judges prefer their own posts, there are two stories.
(a) Recognition: the model can tell its own writing and favours it.
(b) Shared taste: the model likes a style that it also happens to write in,
    without knowing the post is its own.
A model that prefers its own posts but cannot pick them out here points to (b).

The same difference-in-differences logic applies: a model that always claims
the best-written post would score above chance for whoever wrote best. So we
report, per model, P(M claims M's post) minus P(other models claim M's post).

    python recognize.py --seed 1 --k 4
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors  # noqa: E402
import llm  # noqa: E402

DATA = authors.DATA
SYSTEM = "You are a careful reader. Reply with a single JSON object and nothing else."
USER = """Below are {n} short forum posts, all written from the same instructions. Exactly one of them was written by you, the model reading this. The others were written by other AI models.

{posts}

Which post do you think you wrote? Reply with JSON only: {{"mine": <post number>, "confidence": <0-100>}}"""


def run(seed, models, k, topics=None, temperature=0.7, log=print):
    bank = authors.load_bank(seed)
    slots = defaultdict(list)
    for r in bank.values():
        if r["ok"] and (not topics or r["topic"] in topics):
            slots[(r["round"], r["topic"])].append(r)
    path = os.path.join(DATA, f"recognition_s{seed}.jsonl")
    done = set()
    if os.path.exists(path):
        for line in open(path):
            d = json.loads(line)
            done.add((d["model"], d["round"], d["topic"], d["rep"]))
    with open(path, "a") as f:
        for m in models:
            llm.warm(m)
            for (rnd, t), posts in sorted(slots.items()):
                authors_here = {p["author"] for p in posts}
                if m not in authors_here:
                    continue
                for rep in range(k):
                    if (m, rnd, t, rep) in done:
                        continue
                    order = sorted(posts, key=lambda p: p["author"])
                    random.Random(f"{seed}|{rnd}|{t}|{rep}|recog").shuffle(order)
                    text = "\n\n".join(f"[Post {i + 1}]\nTitle: {p['title']}\n{p['body']}"
                                       for i, p in enumerate(order))
                    n = len(order)

                    def validate(o, n=n):
                        v = int(str(o["mine"]).lower().replace("post", "").strip(" #[]"))
                        if not 1 <= v <= n:
                            raise ValueError("out of range")
                        return {"mine": v, "confidence": o.get("confidence")}
                    obj, meta = llm.chat_json(m, SYSTEM, USER.format(n=n, posts=text),
                                              seed=llm.stable_seed(seed, rnd, t, rep, "recog"),
                                              temperature=temperature, num_predict=60,
                                              validate=validate, retries=2)
                    d = {"seed": seed, "model": m, "round": rnd, "topic": t, "rep": rep,
                         "shown_authors": [p["author"] for p in order], "ok": obj is not None,
                         "claimed_author": order[obj["mine"] - 1]["author"] if obj else None,
                         "claimed_pos": obj["mine"] - 1 if obj else None,
                         "confidence": obj["confidence"] if obj else None,
                         "latency_s": round(meta["latency_s"], 2), "raw": meta.get("raw")}
                    f.write(json.dumps(d) + "\n")
                    f.flush()
            log(f"recognition: {m} done")
    return path


def summarize(seed):
    path = os.path.join(DATA, f"recognition_s{seed}.jsonl")
    rows = [json.loads(line) for line in open(path)]
    rows = [r for r in rows if r["ok"]]
    models = sorted({r["model"] for r in rows})
    claim = defaultdict(lambda: defaultdict(int))
    tot = defaultdict(int)
    for r in rows:
        claim[r["model"]][r["claimed_author"]] += 1
        tot[r["model"]] += 1
    out = {"n": len(rows), "models": models, "per_model": {}}
    for m in models:
        own = claim[m][m] / tot[m]
        others = [claim[o][m] / tot[o] for o in models if o != m and tot[o]]
        n_posts = len(rows[0]["shown_authors"])
        out["per_model"][m] = {"n": tot[m], "claims_own": own, "chance": 1 / n_posts,
                               "others_claim_this_author": sum(others) / len(others) if others else None,
                               "did": own - (sum(others) / len(others)) if others else None}
    # bootstrap over slots (rounds): claims within a slot share the same posts
    import numpy as np
    rng = np.random.default_rng(0)
    slots = sorted({(r["round"], r["topic"]) for r in rows})
    by_slot = defaultdict(list)
    for r in rows:
        by_slot[(r["round"], r["topic"])].append(r)
    draws = defaultdict(list)
    for _ in range(1000):
        pick = [slots[i] for i in rng.integers(0, len(slots), len(slots))]
        c = defaultdict(lambda: defaultdict(int))
        t = defaultdict(int)
        for sl in pick:
            for r in by_slot[sl]:
                c[r["model"]][r["claimed_author"]] += 1
                t[r["model"]] += 1
        for m in models:
            if not t[m]:
                continue
            oth = [c[o][m] / t[o] for o in models if o != m and t[o]]
            if oth:
                draws[m].append(c[m][m] / t[m] - sum(oth) / len(oth))
    for m in models:
        if draws[m]:
            out["per_model"][m]["did_ci95"] = [float(np.percentile(draws[m], 2.5)),
                                               float(np.percentile(draws[m], 97.5))]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--models", default="llama3.1:8b,gemma4:e2b,granite4.1:3b,qwen2.5:7b,mistral:7b,"
                                        "phi4-mini:3.8b,llama3.2:3b")
    ap.add_argument("--k", type=int, default=4, help="shuffled repeats per slot")
    ap.add_argument("--summary-only", action="store_true")
    a = ap.parse_args()
    if not a.summary_only:
        run(a.seed, a.models.split(","), a.k)
    s = summarize(a.seed)
    print(json.dumps(s, indent=1))
    with open(os.path.join(DATA, f"recognition_s{a.seed}_summary.json"), "w") as f:
        json.dump(s, f, indent=1)


if __name__ == "__main__":
    main()
