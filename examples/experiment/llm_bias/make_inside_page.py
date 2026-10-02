"""Build the 'Inside the Two-AI Feed' page: how the LD-18 test works, end to end, from the real files.

Everything the page shows is read from disk here, never retyped: the code files (with line numbers computed from the
source, so every "see lines x-y" link is exact), a real vote traced through every layer (persona text, prompts, the
HTTP request and Ollama's reply, the decision record, the OASIS database rows), the scroll order of one user, the
job cards of one round, the manifest, sample lines of every data file, file sizes, and the git history.

    python make_inside_page.py <out_dir> [results_url]   # writes <out_dir>/inside.html, inside_data.js, inside_code.js
"""

import ast
import csv
import glob
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
import authors  # noqa: E402
import personas  # noqa: E402
import scroll  # noqa: E402
from topics import PRIMARY, TOPICS  # noqa: E402

DATA = authors.DATA
GH = "https://github.com/KGordo11/oasis/blob/llm-bias/"
SCRATCH_TRACE = sys.argv[3] if len(sys.argv) > 3 else None

CODE_FILES = [  # (file, role)
    ("two_ai_campaign.sh", "runs every round"), ("run_world.py", "one AI's turn in one round"),
    ("authors.py", "job cards and post writing"), ("scroll.py", "the voting question and the scroll order"),
    ("llm.py", "talks to the AIs"), ("personas.py", "the 100 users"), ("topics.py", "subreddits and job-card lists"),
    ("pair.py", "imported by run_world.py; used only by an earlier test"),
    ("two_ai_after_round.sh", "after each round"), ("check_world.py", "health checks"),
    ("speed_pick.py", "picked the two AIs"), ("drift_check.py", "replay check"),
    ("analyze_two_ai.py", "headline math"), ("analyze_world.py", "loads votes, shared math"),
    ("analyze.py", "double difference and bootstrap"), ("analyze_deep.py", "every breakdown"),
    ("make_two_ai_page.py", "builds the results page"), ("make_inside_page.py", "builds this page"),
    ("make_doc_charts.py", "charts for the report doc"),
]


def sh(cmd):
    return subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True, text=True).stdout


def py_ranges(path):
    """name -> (first, last) line for every top-level function, class and assignment (decorators included)."""
    src = open(path).read()
    tree = ast.parse(src)
    out = {}
    for n in tree.body:
        names = []
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = [n.name]
        elif isinstance(n, ast.Assign):
            names = [t.id for t in n.targets if isinstance(t, ast.Name)]
        for nm in names:
            out[nm] = (n.lineno, n.end_lineno)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for m in ast.walk(n):
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m is not n:
                    out.setdefault(f"{n.name}.{m.name}", (m.lineno, m.end_lineno))
    return out


def main(out_dir, results_url):
    os.makedirs(out_dir, exist_ok=True)
    code, ranges = {}, {}
    for f, _ in CODE_FILES:
        p = os.path.join(HERE, f)
        code[f] = open(p).read()
        if f.endswith(".py"):
            ranges[f] = py_ranges(p)

    def ref(m):
        parts = m.group(1).split(":")
        f = parts[0]
        if len(parts) == 2:
            a, b = ranges[f][parts[1]]
        else:
            a, b = int(parts[1]), int(parts[2])
        lab = m.group(2) or (f"{f}, line {a}" if a == b else f"{f}, lines {a}–{b}")
        return f'<a class="cref" href="#code" data-file="{f}" data-from="{a}" data-to="{b}">{lab}</a>'

    D = {}
    # --- machine
    man = json.load(open(os.path.join(DATA, "worlds", "two_r03_gemma4", "manifest.json")))
    D["manifest"] = man
    D["versions"] = {"python": sh("./oasis-env/bin/python --version").strip(),
                     "ollama": sh("ollama --version").strip().replace("ollama version is ", ""),
                     "packages": {l.split()[0]: l.split()[1] for l in sh("./oasis-env/bin/pip list 2>/dev/null").splitlines()
                                  if l.split() and l.split()[0] in ("camel-ai", "camel-oasis", "pandas", "numpy", "statsmodels")},
                     "git": sh("git rev-parse --short HEAD").strip(), "platform": man["machine"]["platform"]}
    D["models"] = {l.split()[0]: l.split()[2] + " " + l.split()[3] for l in sh("ollama list").splitlines()[1:] if l.split()}
    D["speed"] = json.load(open(os.path.join(DATA, "speed_pick.json")))
    # --- users
    bank = personas.load_bank()
    core = personas.core100()
    D["user0"] = bank[0]
    D["hashes"] = {"bank": personas.bank_hash(bank), "core99": personas.bank_hash(core[:99]), "core100": personas.bank_hash(core)}
    D["user_count_check"] = len(core)
    # --- job cards for round 3, all 25
    D["briefs_r3"] = [{"topic": t, "slot": k, "i": 5 * (203 - 201) + k, **authors.slot_brief(203, k, t)} for t in PRIMARY for k in range(5)]
    D["topic_lists"] = {t: {"sub": TOPICS[t]["sub"], "angles": TOPICS[t]["angles"]} for t in PRIMARY}
    from topics import POST_TYPES, POSTER_VOICES
    D["post_types"], D["voices"] = POST_TYPES, POSTER_VOICES
    # --- the traced post and vote (round 3, user 0, r/cars slot 1)
    pb = authors.load_bank(203)
    D["post_g4"], D["post_g3"] = pb["r1|cars|gemma4:e2b"], pb["r1|cars|gemma3:1b"]
    D["post_prompt_user"] = authors.NATURAL_USER.format(sub="r/cars", topic_name=TOPICS["cars"]["name"], **D["post_g4"]["brief"])
    D["post_prompt_system"] = authors.NATURAL_SYSTEM
    D["vote_system"] = scroll.SYSTEM_TEMPLATE.format(persona=core[0]["persona"])
    D["vote_user"] = scroll.render_user("cars", D["post_g4"])
    rec = {}
    for w in ("two_r03_gemma4", "two_r03_gemma3"):
        for line in open(os.path.join(DATA, "worlds", w, "decisions.jsonl")):
            d = json.loads(line)
            if d["agent_id"] == 0 and d["post_key"] == "r1|cars|gemma4:e2b":
                rec[w] = d
                break
    D["decision_records"] = rec
    if SCRATCH_TRACE and os.path.exists(SCRATCH_TRACE):
        D["live"] = json.load(open(SCRATCH_TRACE))
    db = sqlite3.connect(os.path.join(DATA, "worlds", "two_r03_gemma4", "oasis.db"))
    q = lambda s: [dict(zip([c[0] for c in cur.description], r)) for cur in [db.execute(s)] for r in cur.fetchall()]  # noqa: E731
    D["db"] = {
        "tables": [r["name"] for r in q("select name from sqlite_master where type='table' order by name")],
        "counts": {t: q(f"select count(*) n from '{t}'")[0]["n"] for t in ("user", "post", "like", "dislike", "trace")},
        "user_rows": q("select user_id,agent_id,user_name,name,bio,created_at from user where agent_id in (0,1,100,101)"),
        "post_row": q("select post_id,user_id,content,created_at,num_likes,num_dislikes from post where post_id=13")[0],
        "like_row": q("select * from 'like' where user_id=0 and post_id=13")[0],
        "trace_rows": q("select user_id,created_at,action,info from trace where user_id=0 and (action='sign_up' or info like '%\"post_id\": 13,%')"),
        "schema": {t: q(f"select sql from sqlite_master where name='{t}'")[0]["sql"] for t in ("user", "post", "like", "dislike", "trace")},
    }
    # --- user 0's whole scroll in round 3 (both AIs), recomputed with the real function and checked against the log
    posts = [pb[authors.key(k, t, au)] for t in PRIMARY for k in range(5) for au in ("gemma4:e2b", "gemma3:1b")]
    posts = [p for p in posts if p.get("ok")]
    by_topic = {t: [p for p in posts if p["topic"] == t] for t in PRIMARY}
    feed = scroll.feed(core[0], by_topic, 203)
    acts = {}
    for w in ("two_r03_gemma4", "two_r03_gemma3"):
        acts[w] = {json.loads(l)["post_key"]: json.loads(l) for l in open(os.path.join(DATA, "worlds", w, "decisions.jsonl"))
                   if json.loads(l)["agent_id"] == 0}
    D["scroll_u0"] = [{"n": i + 1, "topic_rank": r, "topic": t, "pos": pos, "author": p["author"].split(":")[0], "title": p["title"],
                       "g4": acts["two_r03_gemma4"][p["key"]]["action"], "g3": acts["two_r03_gemma3"][p["key"]]["action"],
                       "g4_reason": acts["two_r03_gemma4"][p["key"]]["reason"], "g3_reason": acts["two_r03_gemma3"][p["key"]]["reason"],
                       "match_log": acts["two_r03_gemma4"][p["key"]]["topic_rank"] == r and acts["two_r03_gemma4"][p["key"]]["pos_in_topic"] == pos}
                      for i, (r, t, pos, p) in enumerate(feed)]
    D["topic_order_u0"] = scroll.topic_order(core[0], PRIMARY)
    # --- one round's timeline (round 3) from the logs and manifests
    tl = []
    for w in ("two_r03_gemma4", "two_r03_gemma3"):
        m = json.load(open(os.path.join(DATA, "worlds", w, "manifest.json")))
        lines = open(os.path.join(DATA, "worlds", w, "run.log")).read().splitlines()
        tl.append({"world": w, "started": m["started_at"], "finished": m["finished_at"], "post_s": m["post_generation_s"],
                   "judge": list(m["judges"])[0], "vote_s": list(m["judges"].values())[0]["wall_s"],
                   "first_log": lines[0], "last_log": lines[-1], "n_log": len(lines)})
    D["round3_timeline"] = tl
    # --- seeds
    import llm
    D["seeds"] = {"vote": llm.stable_seed(203, 0, "r1|cars|gemma4:e2b", "scroll"), "post": authors.hash_seed(203, 1, "cars"),
                  "sha": hashlib.sha256("203|0|r1|cars|gemma4:e2b|scroll".encode()).hexdigest()}
    # --- samples of every data file
    def head(path, n):
        with open(path) as f:
            return "".join(next(f) for _ in range(n))
    T = os.path.join(DATA, "two_ai")
    D["samples"] = {
        "reactions.csv": head(os.path.join(T, "reactions.csv"), 3),
        "posts.csv_header": head(os.path.join(T, "posts.csv"), 1),
        "users.csv_header": head(os.path.join(T, "users.csv"), 1),
        "timing.csv": head(os.path.join(T, "timing.csv"), 3),
        "slots.csv": head(os.path.join(T, "slots.csv"), 3),
        "summary.txt": open(os.path.join(T, "summary.txt")).read(),
        "checks": head(os.path.join(DATA, "two_ai_checks_final.txt"), 8),
        "campaign_log": head(os.path.join(DATA, "two_ai_campaign.log"), 12),
        "run_log": head(os.path.join(DATA, "worlds", "two_r03_gemma4", "run.log"), 6),
        "analysis_keys": list(json.load(open(os.path.join(T, "analysis.json"))).keys()),
        "deep_keys": list(json.load(open(os.path.join(T, "deep.json"))).keys()),
        "drift": open(os.path.join(T, "drift_check.jsonl")).read(),
    }
    # --- inventory
    tracked = set(sh("git ls-files data/llm_bias examples/experiment/llm_bias LLM_BIAS_LOG.md LLM_BIAS_DATA_DICTIONARY.md").split())
    inv = []
    def add(rel, what):
        p = os.path.join(REPO, rel)
        if not os.path.exists(p):
            return
        size = os.path.getsize(p)
        lines = sum(1 for _ in open(p, errors="replace")) if size < 60_000_000 and not rel.endswith(".db") else None
        inv.append({"path": rel, "bytes": size, "lines": lines, "git": rel in tracked, "what": what})
    E = "examples/experiment/llm_bias/"
    for f, role in CODE_FILES:
        add(E + f, role)
    add(E + "personas_bank.json", "the 1,000 generated people; the first 100 are the users")
    add(E + "results_template.html", "the results page's layout and charts")
    add(E + "inside_template.html", "this page's layout")
    for r in range(1, 16):
        add(f"data/llm_bias/postbank_s{200 + r}.jsonl", f"round {r}: every post, word for word, with its job card and raw reply")
    for r in (1, 15):
        for j in ("gemma4", "gemma3"):
            w = f"data/llm_bias/worlds/two_r{r:02d}_{j}/"
            add(w + "decisions.jsonl", f"round {r}, {j} playing: one line per vote")
            add(w + "manifest.json", f"round {r}, {j} playing: every setting, model fingerprints, timing")
            add(w + "run.log", f"round {r}, {j} playing: progress log")
            add(w + "oasis.db", f"round {r}, {j} playing: the pretend-Reddit database")
    for f, what in (("reactions.csv", "all 147,600 votes"), ("posts.csv", "all 750 planned posts"), ("users.csv", "the 100 users"),
                    ("timing.csv", "minutes per run"), ("slots.csv", "one row per post pair"), ("analysis.json", "headline numbers"),
                    ("deep.json", "every breakdown"), ("deep_posts.json", "posts + votes + sample reasons for the post browser"),
                    ("deep_users.json", "users + every vote for the user browser"), ("summary.txt", "printed headline"),
                    ("drift_check.jsonl", "replay checks")):
        add("data/llm_bias/two_ai/" + f, what)
    for f, what in (("speed_pick.json", "the speed test of 9 AIs"), ("two_ai_checks.txt", "checker output after every round"),
                    ("two_ai_checks_final.txt", "final checker output"), ("two_ai_round_s.txt", "last round's seconds (stop rule)"),
                    ("two_ai_campaign.log", "the campaign's own log"), ("two_ai_after.log", "after-round log")):
        add("data/llm_bias/" + f, what)
    add("LLM_BIAS_LOG.md", "the lab notebook")
    add("LLM_BIAS_DATA_DICTIONARY.md", "every column explained")
    D["inventory"] = inv
    D["n_world_dirs"] = len(glob.glob(os.path.join(DATA, "worlds", "two_r*")))
    # --- git history of the test
    D["commits"] = [dict(zip(("hash", "when", "msg"), l.split("\t", 2))) for l in
                    sh("git log --since='2026-09-30 22:00' --format='%h\t%ad\t%s' --date=format:'%b %d %H:%M' -- . ").splitlines()][::-1]
    D["oasis_upstream"] = "https://github.com/camel-ai/oasis"
    D["gh"] = GH

    html = open(os.path.join(HERE, "inside_template.html")).read()
    html = re.sub(r"\[\[ref:([^\]|]+)(?:\|([^\]]+))?\]\]", ref, html)
    html = html.replace("{RESULTS}", results_url).replace("{GH}", GH)
    open(os.path.join(out_dir, "inside.html"), "w").write(html)
    with open(os.path.join(out_dir, "inside_data.js"), "w") as f:
        f.write("window.IN=" + json.dumps(D, default=str) + ";")
    with open(os.path.join(out_dir, "inside_code.js"), "w") as f:
        f.write("window.CODE=" + json.dumps(code) + ";window.CODE_ORDER=" + json.dumps(CODE_FILES) + ";")
    bad = [s for s in D["scroll_u0"] if not s["match_log"]]
    print(f"wrote inside.html ({len(html) // 1024} KB), data {os.path.getsize(os.path.join(out_dir, 'inside_data.js')) // 1024} KB, "
          f"code {os.path.getsize(os.path.join(out_dir, 'inside_code.js')) // 1024} KB; scroll recompute mismatches: {len(bad)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "#")
