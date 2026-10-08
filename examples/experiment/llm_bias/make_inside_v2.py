"""Build the 'Inside LLM Bias v2' page: one HTML file with every code file (click to read it), the exact prompts the
AIs receive, real answers from round 101, every Spark command, and how the pieces fit.

    python3 examples/experiment/llm_bias/make_inside_v2.py data/llm_bias/v2_spark <out.html>

The page text lives in inside_v2_template.html; this script only fills in the data (file sources, line numbers of the
functions the text points to, real prompts and answers), so the code shown is always the code in the repo.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
import run_v2  # noqa: E402  (the real prompt templates)

RES, OUT = sys.argv[1], sys.argv[2]
X = "examples/experiment/llm_bias/"

# (path, group, title, what it does, where it came from)
FILES = [
    (X + "run_v2.py", "new", "One turn: the posting turn or the reading turn",
     "Builds every screen (who sees what), writes the exact prompt, calls the AI, checks the answer, saves one row per screen. "
     "Holds the prompt templates, the 27-action menu and the answer checker. The heart of the study.",
     "Written for v2 (first commit 2b66763, 2 Oct 2026; 11 commits). The prompt's three headings and the action list are "
     "adapted from OASIS (see the two OASIS files)."),
    (X + "v2_night.py", "new", "The runner: does a whole round in the right order",
     "Loads one AI at a time, runs posting, then the baseline, then the six cross cells in growing stages (16, 32, 64, all posts "
     "per user), then the noise floor. Skips finished work, so a restart resumes. Never starts a step it can't finish by STOP.",
     "Written for v2 (da6f5b5, 4 Oct; 10 commits)."),
    (X + "llm.py", "updated", "The one door to the AIs",
     "Every AI call goes through chat_json(): send system + user message, ask for JSON, retry up to 2 more times with a new "
     "seed if the answer is unreadable, record time and tokens. Switches between Ollama and llama.cpp.",
     "Written 23 Sep 2026 for LLM Bias Tests 1-6 (Ollama only). Changed for v2: llama.cpp backend, identical sampling for "
     "every AI (LD-41), the server check that broke the first night (LB-v2-3)."),
    (X + "llamacpp_servers.sh", "new", "Starts and stops the AI servers on the Spark",
     "One llama.cpp server per AI (ports 11601-11603), 8 screens at a time, 8,192 tokens each. 'only' keeps just the AI in "
     "use loaded; 'stop' waits until the server has really exited.",
     "Written for v2 (46ea7cf, 5 Oct; 4 commits)."),
    (X + "preflight_v2.py", "new", "108 safety checks before leaving a run alone",
     "Setup, code, each AI alone, switching AIs, a full mini-round through the real runner, kill-and-resume, clean finish.",
     "Written for v2 (1457456, 6 Oct). Passed 108/108 on the Spark."),
    (X + "progress_v2.py", "new", "Where are we, how much is left, when does it land",
     "Counts screens done vs needed for every cell of every round and estimates the finish time from the live speed.",
     "Written for v2 (23b91bd, 7 Oct)."),
    (X + "analyze_v2.py", "new", "The plain tables and the bias number",
     "Writes summary.md: posting turn, reader x poster table, by stance, the double difference with 95% ranges, the noise floor.",
     "Written for v2 (3c02c46, 3 Oct). Standard library only, so it runs on the Spark."),
    (X + "export_v2.py", "new", "CSV files + a simple workbook", "users, posts, posting_turn, reactions, actions_long, summary_by_round.",
     "Written for v2 (27cc742, 5 Oct). Laptop only (needs pandas)."),
    (X + "make_graphs_v2.py", "new", "Graphs per round", "The first set of round graphs.", "Written for v2 (27cc742, 5 Oct)."),
    (X + "make_report_v2.py", "new", "The full Excel workbook and all 14 graphs",
     "3x3 engagement grids for every action (formulas), bias, stance, topic, posting, posts, people, noise, time per step, and "
     "the time-vs-users and time-vs-rounds graphs.", "Written 7 Oct (dfc3a2e)."),
    (X + "build_population_v2.py", "new", "Makes the 100 pinned users from US data",
     "Census 2024 (age, sex, state), Census 2020 (city or countryside), CPS 2024 (schooling), BLS (work), Pew 2025 (who uses "
     "social media). Big Five personality, and topic stances from an orthogonal array: 20 users per stance per topic.",
     "Written for v2 (2b66763, 2 Oct). The data tables it reads come from the Census Bureau, BLS and Pew."),
    (X + "personas_v2.json", "made", "The 100 users (frozen)",
     "Made once by build_population_v2.py, then pinned: run_v2.py refuses to run if its fingerprint (SHA ed110626) changes. "
     "The 'persona' text of each user is pasted word for word into every prompt.", "Generated 2 Oct 2026."),
    ("oasis/social_agent/agent_action.py", "oasis", "OASIS: the user actions",
     "The functions behind every action an OASIS user can take (like_post, create_comment, follow, ...). Our 27-item menu is "
     "this list minus sign_up, purchase_product and interview. run_v2's replay() calls these to rebuild a real OASIS database.",
     "From camel-ai/oasis, unchanged. Note: the Spark runs use --no-replay (the default), so this code is NOT executed in "
     "the real rounds; it defines the menu and is used only when the replay is switched on."),
    ("oasis/social_platform/config/user.py", "oasis", "OASIS: the user's system prompt",
     "to_reddit_system_message() is where the '# OBJECTIVE / # SELF-DESCRIPTION / # RESPONSE METHOD' prompt comes from. "
     "run_v2's SYSTEM keeps the three headings; it shows one screen instead of 'some posts' and asks for one JSON answer "
     "instead of tool calls (so no AI is penalised for being bad at one tool-calling format).",
     "From camel-ai/oasis, unchanged."),
]
SAMPLES = [
    ("data/llm_bias/v2_spark/r101/reading_qwen3-8b__llama3.1-8b.manifest.json", "data", "A step's manifest (real, round 101)",
     "Written at the end of every step: what ran, the git commit, the fingerprints of the users, posts and prompts, the "
     "engine and sampling, how long it took, how many answers were unreadable.", "Made by run_v2.py on the Spark."),
]


def lang(p):
    return {"py": "python", "sh": "bash", "json": "json", "html": "xml"}.get(p.rsplit(".", 1)[-1], "plaintext")


files = []
for path, group, title, what, origin in FILES + SAMPLES:
    full = os.path.join(REPO, path)
    src = open(full).read()
    if path.endswith("personas_v2.json"):
        src = json.dumps(json.load(open(full))[:3], indent=1) + "\n\n... 97 more users, same shape (the full file is in the repo)"
    files.append({"path": path, "group": group, "title": title, "what": what, "origin": origin, "lang": lang(path),
                  "src": src, "lines": src.count("\n") + 1})

# Spark-only files (not in git): shown as they are on the Spark
files.append({"path": "~/llm_bias/watchdog.sh (on the Spark, not in git)", "group": "spark", "lang": "bash",
              "title": "Restarts the run if it dies", "what": "cron runs it every 10 minutes: if the runner is not alive it "
              "restarts it with the same settings (resume is safe). Does nothing from STOP minus 30 minutes.",
              "origin": "Written 7 Oct after the overnight run was killed (log 14.31c). Installed with crontab.",
              "src": """#!/bin/bash
# Restarts the LLM Bias v2 runner if it died (2026-10-07: whole session killed overnight). Does nothing after STOP-30min.
export USER=$(id -un)
STOP="2026-10-09 06:00"
[ "$(date +%s)" -lt "$(( $(date -d "$STOP" +%s) - 1800 ))" ] || exit 0
ps -u "$USER" -o args | grep -q '^python3 .*[v]2_night' && exit 0
pkill -u "$USER" -f run_v2.py; sleep 3
echo "$(date '+%F %T') WATCHDOG: runner was dead -> restarting" >> $HOME/llm_bias/oasis/data/llm_bias/v2/night.log
cd $HOME/llm_bias/oasis && . $HOME/llm_bias/env_llamacpp.sh && MANAGE_SERVERS=1 STOP="$STOP" ROUNDS="101 102 103" PARALLEL=8 PY=python3 PUSH=0 STOP_OLLAMA=1 exec python3 examples/experiment/llm_bias/v2_night.py >> $HOME/llm_bias/logs/night_run.out 2>&1 < /dev/null

# installed with:
# (crontab -l 2>/dev/null | grep -v watchdog.sh; echo "*/10 * * * * bash $HOME/llm_bias/watchdog.sh") | crontab -"""})
files.append({"path": "~/llm_bias/env_llamacpp.sh (on the Spark, written by llamacpp_servers.sh start)", "group": "spark",
              "lang": "bash", "title": "Tells the code where the AI servers are", "what": "Sourced before every run: switches "
              "llm.py to llama.cpp and lists each AI's server address.", "origin": "Written by llamacpp_servers.sh on 5 Oct.",
              "src": 'export LLM_BACKEND=llamacpp\nexport LLAMACPP_URLS=\'{"qwen3:8b": "http://127.0.0.1:11601", '
                     '"llama3.1:8b": "http://127.0.0.1:11602", "gemma3:12b": "http://127.0.0.1:11603"}\''})
for f in files:
    f["lines"] = f["src"].count("\n") + 1


def line_of(path, pat):
    f = next(x for x in files if x["path"] == path)
    for k, l in enumerate(f["src"].split("\n"), 1):
        if re.search(pat, l):
            return k
    raise SystemExit(f"not found: {pat} in {path}")


R = X + "run_v2.py"
refs = {
    "menu": (R, line_of(R, r"^MENU = ")), "format": (R, line_of(R, r"^FORMAT = ")), "system": (R, line_of(R, r"^SYSTEM = ")),
    "post_screen": (R, line_of(R, r"^POST_SCREEN = ")), "read_screen": (R, line_of(R, r"^READ_SCREEN = ")),
    "validate": (R, line_of(R, r"^def validate\(obj\)")), "post_set": (R, line_of(R, r"^def post_set")),
    "ring": (R, line_of(R, r"ring = posts\[:\]")), "own": (R, line_of(R, r"never your own post")),
    "screen": (R, line_of(R, r"def screen\(p, page, pos\)")), "row": (R, line_of(R, r"def row\(p, q, pos")),
    "pool": (R, line_of(R, r"pool = ThreadPoolExecutor")), "manifest": (R, line_of(R, r"man = \{")),
    "replay": (R, line_of(R, r"^async def replay")), "pinned": (R, line_of(R, r"^def load_personas")),
    "chat_json": (X + "llm.py", line_of(X + "llm.py", r"^def chat_json")), "llamacpp": (X + "llm.py", line_of(X + "llm.py", r"^def _llamacpp")),
    "sampling": (X + "llm.py", line_of(X + "llm.py", r"^SAMPLING = ")), "seed": (X + "llm.py", line_of(X + "llm.py", r"^def stable_seed")),
    "night_loop": (X + "v2_night.py", line_of(X + "v2_night.py", r"^for r in ROUNDS")),
    "night_step": (X + "v2_night.py", line_of(X + "v2_night.py", r"^def step\(")),
    "slices": (X + "v2_night.py", line_of(X + "v2_night.py", r"for k in SLICES")),
    "only": (X + "llamacpp_servers.sh", line_of(X + "llamacpp_servers.sh", r"^only\)")),
    "oasis_actions": ("oasis/social_agent/agent_action.py", line_of("oasis/social_agent/agent_action.py", r"async def like_post")),
    "oasis_prompt": ("oasis/social_platform/config/user.py", line_of("oasis/social_platform/config/user.py", r"def to_reddit_system_message")),
    "personas_built": (X + "build_population_v2.py", 1),
}

# exact prompts, built with run_v2's own templates, for user 0 (andrewh47)
people = json.load(open(os.path.join(HERE, "personas_v2.json")))
u0 = people[0]
subs = "\n".join(f"- {s} ({n})" for s, n in run_v2.TOPICS.values())
rows = lambda f: [json.loads(l) for l in open(os.path.join(RES, "r101", f))]
posting = {m: next(d for d in rows(f"posting_{m.replace(':', '-')}.jsonl") if d["user_id"] == 0) for m in run_v2.MODELS}
post_key = "r101|qwen3-8b|u73|0"
q = next({"title": a["title"], "body": a["body"], "sub": a.get("subreddit"), "author": d["username"]}
         for d in rows("posting_qwen3-8b.jsonl") if d["user_id"] == 73 for a in d["actions"] if a["action"] == "create_post")
t = run_v2.topic_of(q["sub"])
sub, tname = run_v2.TOPICS[t]
reading = {m: next((d for d in rows(f"reading_qwen3-8b__{m.replace(':', '-')}.jsonl")
                    if d["user_id"] == 0 and d["post_key"] == post_key and not d["draw"]), None) for m in run_v2.MODELS}
data = {
    "files": files, "refs": refs,
    "post_prompt": {"system": run_v2.SYSTEM.format(persona=u0["persona"]),
                    "user": run_v2.POST_SCREEN.format(subs=subs, menu=run_v2.MENU, fmt=run_v2.FORMAT)},
    "post_answers": {m: {"raw": d.get("raw"), "seconds": d.get("latency_s"), "in": d.get("prompt_tokens"), "out": d.get("eval_tokens")}
                     for m, d in posting.items()},
    "read_prompt": {"system": run_v2.SYSTEM.format(persona=u0["persona"]),
                    "user": run_v2.READ_SCREEN.format(sub=sub, topic_name=tname, author=q["author"], title=q["title"],
                                                      body=q["body"], menu=run_v2.MENU, fmt=run_v2.FORMAT)},
    "read_post": {**q, "sub": sub, "tname": tname, "stance": u0["stances"][t]},
    "read_answers": {m: ({"raw": d.get("raw"), "seconds": d.get("latency_s"), "in": d.get("prompt_tokens"), "out": d.get("eval_tokens")} if d else None)
                     for m, d in reading.items()},
    "user0": {"username": u0["username"], "persona": u0["persona"]},
}
tpl = open(os.path.join(HERE, "inside_v2_template.html")).read()
blob = json.dumps(data).replace("</", "<\\/")
open(OUT, "w").write(tpl.replace("/*__DATA__*/null", blob))
print(f"wrote {OUT}: {os.path.getsize(OUT) / 1e6:.2f} MB, {len(files)} files")
