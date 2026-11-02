"""Every number for the V3 data page and the V3 Excel file, computed once (log 14.62). Stdlib only.

    python3 examples/experiment/llm_bias/v3_report_data.py data/llm_bias/v3_report.json

Runs: V3 = big sim part 1 (data/llm_bias/v3, V1's menu order), V3a = part 2 (data/llm_bias/v3_flipped, the same posts,
menu ranked from V3's own choices), V1 = round 101 (and 102) of data/llm_bias/v1_v2_spark. V3 and V3a also get
"tick 0" (each user's first post, before anyone commented = no timeline). Run v3_clean.py on both V3 parts first.

One record per post read: V3/V3a from <part>/clean/reads.csv (refresh returns = one read at the first look's tick);
V1 from the raw rows (readable answers, noise floor left out). Answer kinds, with their exact output:
  actions    = at least one real action (anything but do_nothing)
  do_nothing = it picked the menu action do_nothing (and nothing else)
  empty      = it sent an empty action list [] with only a reason
Measures: % of posts read (each action, upvoted, ...) and actions per 100 posts read (total engagement, LD-43).
"""
import csv, json, os, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze_v2 as A  # noqa: E402
from v3_big_summary import load  # noqa: E402

DATA = os.path.join(HERE, "../../../data/llm_bias")
S = {"gemma3:12b": "gemma", "llama3.1:8b": "llama", "qwen3:8b": "qwen"}
AIS = ["gemma", "llama", "qwen"]
STANCES = ["LOVE", "LIKE", "NEUTRAL", "DISLIKE", "HATE"]
PARTS = {"V3": "v3", "V3a": "v3_flipped"}


def kind(acts):
    return "actions" if any(a != "do_nothing" for a in acts) else "do_nothing" if acts else "empty"


def reads():
    out = {}
    for run, d in PARTS.items():
        rs = []
        for r in csv.DictReader(open(os.path.join(DATA, d, "clean", "reads.csv"))):
            acts = [a for a in r["actions_chosen"].split(";") if a]
            rs.append({"reader": r["reader"], "posts_by": r["posts_by"], "user": int(r["user_id"]), "post": r["post_key"],
                       "author": int(r["author_id"]), "topic": r["topic"], "stance": r["stance"], "tick": int(r["tick"]),
                       "acts": acts, "seen": int(r["comments_seen"]), "fu": int(r["followup_screens"])})
        out[run] = rs
        out[run + " tick 0"] = [r for r in rs if r["tick"] == 0]
    for rd, name in (("r101", "V1"), ("r102", "V1 r102")):
        rows, _ = load(os.path.join(DATA, "v1_v2_spark"), rd)
        out[name] = [{"reader": S[r["model"]], "posts_by": S[r["posts_by"]], "user": r["user_id"], "post": r["post_key"],
                      "author": r["author_id"], "topic": r["topic"], "stance": r["stance"], "tick": None,
                      "acts": [a["action"] for a in r["actions"]], "seen": 0, "fu": 0}
                     for r in rows if r["turn"] == "read" and r["outcome"] == "chose" and not r["draw"]]
    return out


def measures(rs, acts_all):
    n = len(rs)
    if not n:
        return None
    k = Counter(kind(r["acts"]) for r in rs)
    pct = lambda c: round(100 * c / n, 1)  # noqa: E731
    m = {"posts read": n, "actions per 100": round(100 * sum(sum(a != "do_nothing" for a in r["acts"]) for r in rs) / n, 1),
         "% engaged": pct(k["actions"]), "% chose do_nothing": pct(k["do_nothing"]), "% empty answer": pct(k["empty"]),
         "% upvoted": pct(sum("like_post" in r["acts"] for r in rs)),
         "% downvoted": pct(sum("dislike_post" in r["acts"] for r in rs)),
         "% commented": pct(sum("create_comment" in r["acts"] for r in rs)),
         "comments seen per post": round(sum(r["seen"] for r in rs) / n, 1),
         "follow-up screens per 100": round(100 * sum(r["fu"] for r in rs) / n, 1)}
    m["actions"] = {a: {"% of posts": pct(sum(a in r["acts"] for r in rs)),
                        "per 100": round(100 * sum(r["acts"].count(a) for r in rs) / n, 1),
                        "times": sum(r["acts"].count(a) for r in rs)} for a in acts_all}
    return m


def bias(rs, n_boot):
    """Own-AI bias per pair: the four % (or per-100) numbers it is made of, the double difference and its 95% range."""
    out = []
    for i, j in (("gemma", "llama"), ("gemma", "qwen"), ("llama", "qwen")):
        rows = [{"model": r["reader"], "posts_by": r["posts_by"], "post_key": r["post"], "user_id": r["user"],
                 "eng": sum(a != "do_nothing" for a in r["acts"]), "up": int("like_post" in r["acts"])} for r in rs]
        for meas, key in (("upvoted %", "up"), ("actions per 100", "eng")):
            f = lambda r, key=key: 100 * r[key]  # noqa: E731
            cell = defaultdict(list)
            for r in rows:
                cell[(r["model"], r["posts_by"])].append(f(r))
            mean = {c: round(sum(v) / len(v), 1) for c, v in cell.items()}
            v = A.dd(rows, i, j, f)
            lo, hi = A.boot(rows, i, j, f, n=n_boot)
            out.append({"pair": f"{i} vs {j}", "i": i, "j": j, "measure": meas,
                        "i on i": mean[(i, i)], "j on i": mean[(j, i)], "i on j": mean[(i, j)], "j on j": mean[(j, j)],
                        "bias": round(v, 1), "low": round(lo, 1), "high": round(hi, 1), "clear": lo > 0 or hi < 0})
    return out


def posting():
    out = {}
    for name, d, rd in (("V1", "v1_v2_spark", "r101"), ("V1 r102", "v1_v2_spark", "r102"), ("V3", "v3", "r101")):
        rows, _ = load(os.path.join(DATA, d), rd)
        for m in AIS:
            ps = sorted((r for r in rows if r["turn"] == "post" and S[r["model"]] == m), key=lambda r: r["user_id"])
            users = []
            for r in ps:
                acts = [a["action"] for a in r["actions"]]
                users.append({"user": r["user_id"], "posts": acts.count("create_post"), "acts": acts, "outcome": r["outcome"],
                              "raw": r["raw"], "topics": [a.get("subreddit") for a in r["actions"] if a["action"] == "create_post"],
                              "chars": [len(str(a.get("title", ""))) + len(str(a.get("body", ""))) for a in r["actions"]
                                        if a["action"] == "create_post"], "tokens": r.get("eval_tokens"), "tries": r.get("attempts", 1)})
            out[f"{name}|{m}"] = users
    return out


def main(out_path):
    R = reads()
    acts_all = sorted({a for rs in R.values() for r in rs for a in r["acts"]})
    runs = list(R)
    res = {"runs": runs, "actions": acts_all, "world": {}, "reader": {}, "total": {}, "stance": {}, "tick": {}, "posts": {},
           "users": {}, "bias": {}}
    for run, rs in R.items():
        g = defaultdict(list)
        for r in rs:
            g[("world", r["reader"], r["posts_by"])].append(r)
            g[("reader", r["reader"])].append(r)
            g[("stance", r["reader"], r["stance"])].append(r)
            g[("post", r["post"], r["reader"])].append(r)
            g[("user", r["reader"], r["user"])].append(r)
            g[("stance_w", r["reader"], r["posts_by"], r["stance"])].append(r)  # per world: never pooled over whose posts
            g[("user_w", r["reader"], r["posts_by"], r["user"])].append(r)
            if r["tick"] is not None and not run.endswith("tick 0"):
                g[("tick", r["reader"], r["posts_by"], r["tick"])].append(r)
        res["total"][run] = measures(rs, acts_all)
        for key, xs in g.items():
            if key[0] == "world":
                res["world"][f"{run}|{key[1]}|{key[2]}"] = measures(xs, acts_all)
            elif key[0] == "reader":
                res["reader"][f"{run}|{key[1]}"] = measures(xs, acts_all)
            elif key[0] == "stance":
                res["stance"][f"{run}|{key[1]}|{key[2]}"] = {k: v for k, v in measures(xs, []).items() if k != "actions"}
            elif key[0] == "tick":
                m = measures(xs, ["like_post", "dislike_post", "create_comment", "like_comment"])
                res["tick"][f"{run}|{key[1]}|{key[2]}|{key[3]}"] = {**{k: v for k, v in m.items() if k != "actions"},
                                                                     **{f"% {a}": x["% of posts"] for a, x in m["actions"].items()}}
            elif key[0] == "post":
                n = len(xs)
                res["posts"][f"{run}|{key[1]}|{key[2]}"] = [n, round(100 * sum("like_post" in r["acts"] for r in xs) / n, 1),
                                                            round(100 * sum("dislike_post" in r["acts"] for r in xs) / n, 1),
                                                            round(100 * sum("create_comment" in r["acts"] for r in xs) / n, 1),
                                                            round(100 * sum(sum(a != "do_nothing" for a in r["acts"]) for r in xs) / n, 1)]
            elif key[0] == "stance_w":
                res.setdefault("stance_w", {})[f"{run}|{key[1]}|{key[2]}|{key[3]}"] = {k: v for k, v in measures(xs, []).items() if k != "actions"}
            elif key[0] == "user_w":
                n = len(xs)
                res.setdefault("users_w", {})[f"{run}|{key[1]}|{key[2]}|{key[3]}"] = [
                    n, round(100 * sum(sum(a != "do_nothing" for a in r["acts"]) for r in xs) / n, 1),
                    round(100 * sum("like_post" in r["acts"] for r in xs) / n, 1), round(100 * sum("create_comment" in r["acts"] for r in xs) / n, 1)]
            elif key[0] == "user":
                n = len(xs)
                res["users"][f"{run}|{key[1]}|{key[2]}"] = [n, round(100 * sum(sum(a != "do_nothing" for a in r["acts"]) for r in xs) / n, 1),
                                                            round(100 * sum("like_post" in r["acts"] for r in xs) / n, 1),
                                                            round(100 * sum("create_comment" in r["acts"] for r in xs) / n, 1)]
        res["bias"][run] = bias(rs, 300)
        print(f"{run}: {len(rs):,} posts read", flush=True)
    res["posting"] = posting()
    post_info = {}
    for run in ("V1", "V3"):
        d, rd = ("v1_v2_spark", "r101") if run == "V1" else ("v3", "r101")
        for m in AIS:
            for line in open(os.path.join(DATA, d, rd, f"posting_{ {'gemma': 'gemma3-12b', 'llama': 'llama3.1-8b', 'qwen': 'qwen3-8b'}[m]}.jsonl")):
                r = json.loads(line)
                for k, a in enumerate(x for x in r["actions"] if x["action"] == "create_post"):
                    key = f"r101|{ {'gemma': 'gemma3-12b', 'llama': 'llama3.1-8b', 'qwen': 'qwen3-8b'}[m]}|u{r['user_id']}|{k}"
                    post_info[f"{run}|{key}"] = {"ai": m, "user": r["user_id"], "title": str(a.get("title", "")),
                                                 "chars": len(str(a.get("title", ""))) + len(str(a.get("body", ""))),
                                                 "sub": a.get("subreddit")}
    res["post_info"] = post_info
    # easy vs hard per world (every chosen action on every screen, do_nothing left out), whole scroll and tick 0
    for run, d in PARTS.items():
        c = defaultdict(Counter)
        for r in csv.DictReader(open(os.path.join(DATA, d, "clean", "actions.csv"))):
            if r["action"] == "do_nothing":
                continue
            for rr in (run, run + " tick 0") if r["tick"] == "0" else (run,):
                c[(rr, r["reader"], r["posts_by"])][r["tier"]] += 1
                c[(rr, r["reader"], r["posts_by"])]["fail" + r["tier"]] += r["ok"] == "0"
        for (rr, m, pb), t in c.items():
            n = sum(t[x] for x in "12345")
            res.setdefault("effort_w", {})[f"{rr}|{m}|{pb}"] = {x: {"chosen": t[x], "%": round(100 * t[x] / n, 1),
                                                                    "failed %": round(100 * t["fail" + x] / t[x], 1) if t[x] else None} for x in "12345"}
    for run, d in PARTS.items():
        res.setdefault("cleaning", {})[run] = open(os.path.join(DATA, d, "clean", "cleaning.md")).read()
        res.setdefault("effort", {})[run] = list(csv.DictReader(open(os.path.join(DATA, d, "clean", "effort_tiers.csv"))))
    # self-check: V3/V3a world numbers equal the cleaned by_cell_tick 'all' rows (posts read, engagement, upvoted)
    for run, d in PARTS.items():
        for r in csv.DictReader(open(os.path.join(DATA, d, "clean", "by_cell_tick.csv"))):
            if r["tick"] == "all":
                w = res["world"][f"{run}|{r['reader']}|{r['posts_by']}"]
                assert w["posts read"] == int(r["posts read"]) and w["actions per 100"] == float(r["engagement per 100"]) \
                    and w["% upvoted"] == float(r["upvoted %"]), (run, r["reader"], r["posts_by"])
    json.dump(res, open(out_path, "w"), separators=(",", ":"))
    print(f"wrote {out_path} ({os.path.getsize(out_path) / 1e6:.1f} MB); self-check vs clean/by_cell_tick.csv OK")


if __name__ == "__main__":
    main(sys.argv[1])
