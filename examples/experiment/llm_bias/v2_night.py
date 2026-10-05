"""One night of LLM Bias v2, round 1, spread evenly over every cell (log Part 14 sec. 14.12).

IN PLAIN WORDS
--------------
1. Posting turn for each AI (100 users each).
2. Reading passes. Pass 1: every reader AI reads 8 posts per user from every post set (all 9 cells). Pass 2 tops
   every cell up to 16. Passes go cell by cell for every cell before the next pass starts, so if time runs short
   every cell has the same coverage.
3. Noise floor (stage 1b): each AI re-reads its own post set, 4 posts per user, with fresh randomness.
Before each step it estimates the step's time from the measured seconds per screen and skips it if it would run past
STOP. After each step the OASIS database is rebuilt in the background; after each pass: analysis, commit, push.
At the end the models are unloaded and the Ollama server stopped.

    STOP="2026-10-05 08:45" python v2_night.py
"""
import json, os, subprocess, sys, time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PY = os.path.join(REPO, "oasis-env", "bin", "python")
RUN = os.path.join(HERE, "run_v2.py")
MODELS = ["qwen3:8b", "llama3.1:8b", "mistral:7b"]
ROUND = 1
STOP = datetime.strptime(os.environ["STOP"], "%Y-%m-%d %H:%M").timestamp()
SPS = {"qwen3:8b": 2.0, "llama3.1:8b": 3.5, "mistral:7b": 2.9}  # seconds per screen, measured in the smoke test
LOG = os.path.join(REPO, "data", "llm_bias", "v2", "night.log")


def log(msg):
    line = f"{datetime.now():%F %T} {msg}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def n_posts(model):
    f = os.path.join(REPO, "data", "llm_bias", "v2", f"r{ROUND:03d}", f"posting_{model.replace(':', '-')}.jsonl")
    if not os.path.exists(f):
        return 0
    return sum(sum(x["action"] == "create_post" for x in json.loads(l)["actions"]) for l in open(f))


def step(args, est_s, what):
    left = STOP - time.time()
    if est_s > left:
        log(f"SKIP {what}: needs ~{est_s / 60:.0f} min, {left / 60:.0f} min left")
        return False
    log(f"start {what} (~{est_s / 60:.0f} min)")
    t = time.time()
    rc = subprocess.call([PY, RUN, *args, "--round", str(ROUND), "--no-replay"], cwd=REPO,
                         stdout=open(f"/tmp/v2_night_{what.replace(' ', '_').replace(':', '-')}.log", "a"),
                         stderr=subprocess.STDOUT)
    log(f"end {what} rc={rc} in {(time.time() - t) / 60:.1f} min")
    # rebuild the OASIS database from the records, at background priority (no model calls)
    subprocess.Popen(["taskpolicy", "-b", PY, RUN, *args, "--round", str(ROUND)], cwd=REPO,
                     stdout=open("/tmp/v2_night_replays.log", "a"), stderr=subprocess.STDOUT)
    return rc == 0


def checkpoint(msg):
    """Analysis + commit + push in the background, at low priority, so the next step starts at once."""
    sh = (f"taskpolicy -b {PY} {os.path.join(HERE, 'analyze_v2.py')} > /dev/null 2>&1; "
          f"git add data/llm_bias/v2/r{ROUND:03d} data/llm_bias/v2/summary.md data/llm_bias/v2/night.log; "
          f"git commit -qm 'LLM Bias v2 round {ROUND}: {msg}' -m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'; "
          f"git push -q origin llm-bias")
    subprocess.Popen(["sh", "-c", sh], cwd=REPO, stdout=open("/tmp/v2_night_commits.log", "a"), stderr=subprocess.STDOUT)
    log(f"checkpoint (analysis + commit running in background): {msg}")


log(f"night start, stop at {datetime.fromtimestamp(STOP):%F %H:%M}")
for m in MODELS:
    step(["post", "--model", m], 100 * 6, f"post {m}")
sets = {m: n_posts(m) for m in MODELS}
log(f"post sets: {sets}")
checkpoint("posting turns")
for k_prev, k in ((0, 8), (8, 16)):
    for reader in MODELS:
        for pb in MODELS:
            if sets[pb] == 0:
                continue
            new = 100 * (min(k, sets[pb] - 1) - min(k_prev, sets[pb] - 1))
            step(["read", "--posts-by", pb, "--model", reader, "--max-posts", str(k)], new * SPS[reader],
                 f"read {pb} by {reader} k{k}")
    checkpoint(f"reading pass to {k} posts per user")
for m in MODELS:
    if sets[m]:
        step(["read", "--posts-by", m, "--model", m, "--max-posts", "4", "--draw", "1"], 100 * min(4, sets[m] - 1) * SPS[m],
             f"noise floor {m}")
checkpoint("noise floor re-reads")
time.sleep(600)  # let the last background database rebuilds finish
for m in MODELS:
    subprocess.call(["curl", "-s", "localhost:11434/api/generate", "-d", json.dumps({"model": m, "keep_alive": 0})],
                    stdout=subprocess.DEVNULL)
subprocess.call(["pkill", "-f", "ollama serve"])
log("night end: models unloaded, Ollama stopped")
