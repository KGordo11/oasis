"""Export design-v2 worlds as plain tables anyone can open (CSV).

IN PLAIN WORDS
--------------
Writes data/llm_bias/export/:

  reactions.csv   ONE ROW PER USER PER POST: what the user did (like / dislike /
                  nothing), why, how many seconds that decision took, which model
                  WROTE the post, and which model was CONTROLLING the user.
  posts.csv       every post: who wrote it, its topic, the brief, full text, and
                  how the users reacted to it (likes / dislikes / nothing, split by
                  controlling model).
  users.csv       every user (the 99 pinned personas): who they are, their interest
                  in each topic, and which model controlled them in each world.
  world_timing.csv  one row per world per model: users, decisions, minutes,
                  seconds per decision, start and finish.
  progress_timing.csv  elapsed time as each run worked through its users
                  (read from run.log every 250 decisions) -- the time-vs-agents data.

A "round" is one pass of all 99 users over one fresh set of 50 posts (one world).
Rounds are numbered in the order they ran.

Every column is described in LLM_BIAS_DATA_DICTIONARY.md. Re-run any time; it
rebuilds everything from the run records (decisions.jsonl, manifest.json,
run.log, oasis.db, the post bank and the persona bank).

    python export_world.py              # all worlds whose label starts with v2_
    python export_world.py --prefix v2_ --include bench_v2
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sqlite3
import sys
from datetime import datetime

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors  # noqa: E402
import personas as persona_mod  # noqa: E402
from run_world import assign  # noqa: E402
from topics import TOPICS  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
WORLDS = os.path.join(REPO, "data", "llm_bias", "worlds")
OUT = os.path.join(REPO, "data", "llm_bias", "export")
PROGRESS = re.compile(r"^(\d\d:\d\d:\d\d)\s+(\S+): (\d+)/(\d+) \(")
DONE = re.compile(r"^(\d\d:\d\d:\d\d) (\S+): done (\d+) in")
START = re.compile(r"^(\d\d:\d\d:\d\d) (\S+): (\d+) personas, (\d+) decisions to make")


def worlds(prefix, include):
    out = []
    for m in sorted(glob.glob(os.path.join(WORLDS, "*", "manifest.json"))):
        lab = os.path.basename(os.path.dirname(m))
        if lab.startswith(prefix) or lab in include:
            j = json.load(open(m))
            out.append((j.get("started_at", ""), lab, j))
    out.sort()
    return [(i + 1, lab, j) for i, (_, lab, j) in enumerate(out)]


def oasis_post_ids(db, bank_by_text):
    if not os.path.exists(db):
        return {}
    c = sqlite3.connect(db)
    ids = {}
    for pid, content in c.execute("select post_id, content from post"):
        k = bank_by_text.get(content)
        if k:
            ids[k] = pid
    return ids


def parse_log(path, day):
    """Progress lines -> rows of (model, decisions_done, elapsed_s). Handles a run crossing midnight."""
    rows, t0 = [], {}
    if not os.path.exists(path):
        return rows

    def ts(h):
        return datetime.strptime(f"{day} {h}", "%Y-%m-%d %H:%M:%S")
    last = None
    for line in open(path):
        m = START.match(line)
        if m:
            t = ts(m.group(1))
            t0[m.group(2)] = (t, int(m.group(3)), int(m.group(4)))
            rows.append({"model": m.group(2), "decisions_done": 0, "elapsed_s": 0.0,
                         "personas_in_run": int(m.group(3))})
            last = t
            continue
        m = PROGRESS.match(line) or DONE.match(line)
        if m and m.group(2) in t0:
            t = ts(m.group(1))
            if last and t < last:  # crossed midnight
                t = t.replace(day=t.day + 1)
            last = t
            start, n_p, n_d = t0[m.group(2)]
            rows.append({"model": m.group(2), "decisions_done": int(m.group(3)),
                         "elapsed_s": (t - start).total_seconds(), "personas_in_run": n_p})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="v2_")
    ap.add_argument("--include", default="")
    a = ap.parse_args()
    include = set(filter(None, a.include.split(",")))
    os.makedirs(OUT, exist_ok=True)
    W = worlds(a.prefix, include)
    if not W:
        raise SystemExit("no worlds found")
    people = {p["id"]: p for p in persona_mod.core99()}

    reactions, posts, timing, progress = [], {}, [], []
    for rnd, lab, man in W:
        cfg = man["config"]
        seed = cfg["seed"]
        pbank = authors.load_bank(seed)
        by_text = {f"{r['title']}\n\n{r['body']}": k for k, r in pbank.items() if r.get("ok")}
        pid = oasis_post_ids(os.path.join(WORLDS, lab, "oasis.db"), by_text)
        for line in open(os.path.join(WORLDS, lab, "decisions.jsonl")):
            if not line.strip():
                continue
            d = json.loads(line)
            u = people.get(d["agent_id"], {})
            reactions.append({
                "round": rnd, "world_label": lab, "post_set_seed": seed, "world": d["world"],
                "user_id": d["agent_id"], "username": u.get("username"), "user_name": u.get("realname"),
                "controlling_model": d["judge"], "post_key": d["post_key"], "oasis_post_id": pid.get(d["post_key"]),
                "post_author_model": d["author"], "same_model": d["self"], "topic": d["topic"],
                "user_interest_in_topic": d["affinity"], "topic_order": d["topic_rank"] + 1,
                "position_in_topic": d["pos_in_topic"] + 1,
                "scroll_position": None,  # filled below, after sorting
                "action": d["action"] if d["action"] else "FAILED", "reason": d["reason"],
                "seconds": d["latency_s"], "prompt_tokens": d["prompt_tokens"], "output_tokens": d["eval_tokens"],
                "attempts": d["attempts"], "outcome": d["outcome"], "stop_reason": d["done_reason"]})
        for k, r in pbank.items():
            if r.get("ok") and r["topic"] in cfg["topics"] and r["author"] in cfg["authors"] \
                    and r["round"] < cfg["posts_per_topic"]:
                posts.setdefault(k, {"post_key": k, "post_set_seed": seed, "topic": r["topic"],
                                     "subreddit": TOPICS[r["topic"]]["sub"], "slot": r["round"] + 1,
                                     "author_model": r["author"], "oasis_post_id": pid.get(k),
                                     "post_type": r["brief"]["ptype"], "subject": r["brief"]["angle"],
                                     "poster_voice": r["brief"]["voice"], "title": r["title"], "body": r["body"],
                                     "words": r["words"], "generation_seconds": r["latency_s"],
                                     "generation_attempts": r["attempts"]})
        day = man.get("started_at", "")[:10]
        for jm, jv in man.get("judges", {}).items():
            timing.append({"round": rnd, "world_label": lab, "post_set_seed": seed, "world": cfg["world"],
                           "model": jm, "users": sum(1 for i in man.get("persona_ids", range(cfg["agents"]))
                                                     if assign(i, cfg["judges"], cfg["world"]) == jm),
                           "decisions": jv["decisions"], "minutes": round(jv["wall_s"] / 60, 2),
                           "seconds_per_decision": jv["s_per_decision"], "posts": man.get("n_posts"),
                           "started_at": man.get("started_at"), "finished_at": man.get("finished_at")})
        for row in parse_log(os.path.join(WORLDS, lab, "run.log"), day):
            progress.append({"round": rnd, "world_label": lab, **row,
                             "users_done_equiv": round(row["decisions_done"] / max(1, man.get("n_posts", 50)), 2)})

    R = pd.DataFrame(reactions)
    R = R.sort_values(["round", "user_id", "topic_order", "position_in_topic"]).reset_index(drop=True)
    R["scroll_position"] = R.groupby(["round", "user_id"]).cumcount() + 1
    R.to_csv(os.path.join(OUT, "reactions.csv"), index=False)

    P = pd.DataFrame(posts.values())
    agg = R.groupby(["post_key", "controlling_model", "action"]).size().unstack(["controlling_model", "action"],
                                                                                 fill_value=0)
    agg.columns = [f"{a}_by_{m}_users" for m, a in agg.columns]
    P = P.merge(agg, left_on="post_key", right_index=True, how="left").fillna(0)
    P.to_csv(os.path.join(OUT, "posts.csv"), index=False)

    U = []
    rounds_cfg = {rnd: man["config"] for rnd, lab, man in W}
    for i, p in people.items():
        row = {"user_id": i, "username": p["username"], "name": p["realname"], "age": p["age"],
               "gender": p["gender"], "place": p["place"], "profession": p["profession"],
               "voting_style": p["voting"], **{f"interest_{t}": v for t, v in p["topic_affinity"].items()}}
        for rnd, cfg in rounds_cfg.items():
            if i < cfg["agents"]:
                row[f"controlled_by_round_{rnd}"] = assign(i, cfg["judges"], cfg["world"])
        row["persona_text"] = p["persona"]
        U.append(row)
    pd.DataFrame(U).to_csv(os.path.join(OUT, "users.csv"), index=False)
    pd.DataFrame(timing).to_csv(os.path.join(OUT, "world_timing.csv"), index=False)
    pd.DataFrame(progress).to_csv(os.path.join(OUT, "progress_timing.csv"), index=False)
    print(f"exported {len(W)} rounds: {len(R)} reactions, {len(P)} posts, {len(U)} users -> {OUT}")


if __name__ == "__main__":
    main()
