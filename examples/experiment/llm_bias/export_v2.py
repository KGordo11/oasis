"""Export LLM Bias v2 results to CSV files and one Excel workbook (log Part 14).

IN PLAIN WORDS
--------------
Reads every finished turn in a results folder (data/llm_bias/v2 on the laptop, or a copy from the DGX Spark such as
data/llm_bias/v2_spark) and writes <folder>/export/:

  users.csv           the 100 pinned users: age, gender, state, education, work, personality, stance on each topic
  posts.csv           every post written in a posting turn: round, which AI's users wrote it, author, topic, text
  posting_turn.csv    every user's posting-turn screen: every action taken, posts written, reason
  reactions.csv       every reading screen (one post seen by one user): reader AI, whose post, own-AI or not, the
                      user's stance on the topic, and one column per action (upvote, downvote, comment, share, ...),
                      the comment / quote text, the reason, and timing
  actions_long.csv    one row per single action taken anywhere (for counting any action you like)
  summary_by_round.csv  plain counts and % for every round x reader AI x whose posts
  LLM_bias_v2.xlsx    all of the above as sheets (reactions capped at Excel's row limit, see the README sheet)

    python export_v2.py                         # data/llm_bias/v2, real rounds (< 900)
    python export_v2.py data/llm_bias/v2_spark  # the Spark copy
    python export_v2.py data/llm_bias/v2 --test # smoke-test rounds (>= 900)
"""
import glob, json, os, sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ACTS = ["like_post", "dislike_post", "create_comment", "repost", "quote_post", "report_post", "follow", "unfollow",
        "mute", "unmute", "unlike_post", "undo_dislike_post", "like_comment", "dislike_comment", "search_posts",
        "search_user", "trend", "refresh", "create_post", "create_group", "join_group", "send_to_group", "do_nothing"]
NICE = {"like_post": "upvote", "dislike_post": "downvote", "create_comment": "comment", "repost": "share",
        "quote_post": "quote", "report_post": "report"}


def load(folder, test):
    turns = []
    for m in sorted(glob.glob(os.path.join(folder, "r*", "*.manifest.json"))):
        man = json.load(open(m))
        if (man["round"] >= 900) != test:
            continue
        f = m.replace(".manifest.json", ".jsonl")
        rows = [json.loads(l) for l in open(f)] if os.path.exists(f) else []
        turns.append((man, rows))
    return turns


def users_table():
    P = json.load(open(os.path.join(HERE, "personas_v2.json")))
    out = []
    for p in P:
        d = {"user_id": p["id"], "username": p["username"], "name": p["name"], "age": p["age"], "gender": p["sex"],
             "state": p["state"], "region": p["region"], "community": p["community"], "education": p["education"],
             "work": p["work"]}
        d.update({f"big5_{k}": v for k, v in p["big_five"].items()})
        d.update({f"stance_{k}": v for k, v in p["stances"].items()})
        out.append(d)
    return pd.DataFrame(out)


def main(folder, test):
    turns = load(folder, test)
    if not turns:
        raise SystemExit(f"no finished turns in {folder}")
    out = os.path.join(folder, "export")
    os.makedirs(out, exist_ok=True)
    users = users_table()
    posts, posting, reacts, long = [], [], [], []
    for man, rows in turns:
        for r in rows:
            base = {"round": r["round"], "user_id": r["user_id"], "username": r["username"]}
            for i, a in enumerate(r["actions"]):
                long.append({**base, "turn": r["turn"], "model": r["model"], "posts_by": r.get("posts_by"),
                             "draw": r.get("draw", 0), "post_key": r.get("post_key"), "action": a["action"],
                             "details": json.dumps({k: v for k, v in a.items() if k != "action"}, ensure_ascii=False)})
            if r["turn"] == "post":
                wrote = [a for a in r["actions"] if a["action"] == "create_post"]
                posting.append({**base, "ai_playing_users": r["model"], "outcome": r["outcome"],
                                "posts_written": len(wrote), "actions": ", ".join(a["action"] for a in r["actions"]) or "(nothing)",
                                "reason": r["reason"], "seconds": r["latency_s"]})
                for k, a in enumerate(wrote):
                    posts.append({"round": r["round"], "written_by_ai": r["model"],
                                  "post_key": f"r{r['round']}|{r['model'].replace(':', '-')}|u{r['user_id']}|{k}",
                                  "author_user_id": r["user_id"], "author_username": r["username"],
                                  "subreddit": a.get("subreddit"), "title": a.get("title"), "body": a.get("body"),
                                  "words": len(str(a.get("body", "")).split())})
            else:
                acts = [a["action"] for a in r["actions"]]
                get = lambda name, field: " | ".join(str(a.get(field, "")) for a in r["actions"] if a["action"] == name)
                d = {**base, "reader_ai": r["model"], "posts_by_ai": r["posts_by"], "own_ai_post": r.get("own_ai"),
                     "draw": r.get("draw", 0), "post_key": r["post_key"], "post_author_user_id": r.get("author_id"),
                     "topic": r.get("topic"), "user_stance_on_topic": r.get("stance"), "position_in_scroll": r["pos"],
                     "outcome": r["outcome"], "did_anything": int(any(x != "do_nothing" for x in acts)),
                     "n_actions": len(acts)}
                d.update({NICE.get(a, a): int(a in acts) for a in ACTS})
                d.update({"comment_text": get("create_comment", "content"), "quote_text": get("quote_post", "content"),
                          "report_reason": get("report_post", "reason"), "reason": r["reason"],
                          "seconds": r["latency_s"], "prompt_tokens": r["prompt_tokens"], "output_tokens": r["eval_tokens"]})
                reacts.append(d)
    posts, posting, reacts, long = map(pd.DataFrame, (posts, posting, reacts, long))
    if len(reacts):
        reacts = reacts.merge(users.drop(columns=["username"]), on="user_id", how="left")
        main_ = reacts[(reacts.draw == 0) & (reacts.outcome == "chose")]
        cols = ["upvote", "downvote", "comment", "share", "quote", "report", "follow", "mute", "did_anything"]
        g = main_.groupby(["round", "reader_ai", "posts_by_ai"])
        summ = g.size().rename("screens").to_frame()
        for c in cols:
            summ[c] = g[c].sum()
            summ[c + "_%"] = (100 * g[c].mean()).round(1)
        summ = summ.reset_index()
        summ["cell"] = summ.apply(lambda x: "baseline" if x.reader_ai == x.posts_by_ai else "cross", axis=1)
    else:
        summ = pd.DataFrame()
    for name, df in [("users", users), ("posts", posts), ("posting_turn", posting), ("reactions", reacts),
                     ("actions_long", long), ("summary_by_round", summ)]:
        df.to_csv(os.path.join(out, f"{name}.csv"), index=False)
    readme = pd.DataFrame({"sheet": ["summary_by_round", "reactions", "posts", "posting_turn", "users", "actions_long"],
                           "what it is": ["plain counts and % per round x reader AI x whose posts (baseline = same AI)",
                                          "one row per post seen by one user, every action as a 0/1 column",
                                          "every post written in a posting turn", "every user's posting-turn screen",
                                          "the 100 pinned users", "one row per single action (CSV only if very long)"]})
    limit = 1_048_000
    with pd.ExcelWriter(os.path.join(out, "LLM_bias_v2.xlsx")) as xw:
        readme.to_excel(xw, sheet_name="README", index=False)
        summ.to_excel(xw, sheet_name="summary_by_round", index=False)
        for name, df in [("reactions", reacts), ("posts", posts), ("posting_turn", posting), ("users", users),
                         ("actions_long", long)]:
            df.head(limit).to_excel(xw, sheet_name=name, index=False)
    print(f"wrote {out}: {len(users)} users, {len(posts)} posts, {len(posting)} posting screens, "
          f"{len(reacts)} reading screens, {len(long)} actions")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(os.path.join(REPO, args[0]) if args else os.path.join(REPO, "data", "llm_bias", "v2"), "--test" in sys.argv)
