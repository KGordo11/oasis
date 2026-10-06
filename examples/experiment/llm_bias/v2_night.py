"""Run LLM Bias v2 rounds until a stop time, spreading the work evenly over every cell (log Part 14).

IN PLAIN WORDS
--------------
For each round:
1. Posting turn for each AI (100 users each).
2. Baselines first (LD-40): each AI posts, then the same AI reads ALL of its own posts, one AI after another.
3. Then the cross tests in growing slices: every reader AI reads the first 16 posts of each user's scroll in the
   other AIs' sets, then 32, 64, then all of them (0 = all). The slices are nested -- a bigger slice only adds posts at the end of each
   user's scroll -- so whenever time runs out, every cell has the same coverage, and the next run continues there.
3. Optional noise floor (NOISE=4): each AI re-reads 4 posts per user of its own set with fresh randomness.
Before each step it estimates the step's time from the seconds per screen it has measured so far (on this machine)
and skips the step if it would run past STOP. After each round: analysis, and a commit + push if PUSH=1.
At the end the models are unloaded (and the Ollama server stopped if STOP_OLLAMA=1).

The OASIS database rebuild (replay) is off by default (REPLAY=0) so a remote machine needs only Python, git and
Ollama; rebuild later with `run_v2.py read ... ` without --no-replay.

    STOP="2026-10-06 08:00" ROUNDS="1 2 3" SLICES="16 32 64 0" python v2_night.py
"""
import json, os, subprocess, time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PY = os.environ.get("PY", os.path.join(REPO, "oasis-env", "bin", "python"))
RUN = os.path.join(HERE, "run_v2.py")
MODELS = os.environ.get("MODELS", "qwen3:8b llama3.1:8b gemma3:12b").split()
ROUNDS = [int(x) for x in os.environ.get("ROUNDS", "1").split()]
SLICES = [int(x) for x in os.environ.get("SLICES", "16 32 64 0").split()]
NOISE = int(os.environ.get("NOISE", "4"))
AGENTS = int(os.environ.get("AGENTS", "100"))  # fewer users = a quick end-to-end test of the whole runner
TAG = f"_a{AGENTS}" if AGENTS < 100 else ""  # run_v2.py names files this way when --agents < 100
PARALLEL = os.environ.get("PARALLEL", "4")  # requests in flight; match the server's OLLAMA_NUM_PARALLEL
URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
STOP = datetime.strptime(os.environ["STOP"], "%Y-%m-%d %H:%M").timestamp()
REPLAY = os.environ.get("REPLAY", "0") == "1"
PUSH = os.environ.get("PUSH", "1") == "1"
NICE = ["taskpolicy", "-b"] if os.uname().sysname == "Darwin" else ["nice", "-n", "19"]
SPS = {m: 3.5 for m in MODELS}  # seconds per screen; replaced by what this machine measures
LOG = os.path.join(REPO, "data", "llm_bias", "v2", "night.log")
os.makedirs(os.path.dirname(LOG), exist_ok=True)


def log(msg):
    line = f"{datetime.now():%F %T} {msg}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def rdir(r):
    return os.path.join(REPO, "data", "llm_bias", "v2", f"r{r:03d}")


def n_posts(r, m):
    f = os.path.join(rdir(r), f"posting_{m.replace(':', '-')}{TAG}.jsonl")
    return sum(sum(x["action"] == "create_post" for x in json.loads(l)["actions"]) for l in open(f)) if os.path.exists(f) else 0


def expected(r, pb, k):
    """Screens a reading cell needs at slice k: each user reads min(k, posts not their own); k=0 means all."""
    f = os.path.join(rdir(r), f"posting_{pb.replace(':', '-')}{TAG}.jsonl")
    own = {}
    for l in open(f):
        d = json.loads(l)
        own[d["user_id"]] = sum(x["action"] == "create_post" for x in d["actions"])
    n = sum(own.values())
    return sum((n - own.get(u, 0)) if k == 0 else min(k, n - own.get(u, 0)) for u in range(AGENTS))


def screens_done(r, name):
    f = os.path.join(rdir(r), name + ".jsonl")
    return sum(1 for _ in open(f)) if os.path.exists(f) else 0


MANAGE = os.environ.get("MANAGE_SERVERS", "0") == "1" and os.environ.get("LLM_BACKEND") == "llamacpp"
SERVERS = os.path.join(HERE, "llamacpp_servers.sh")


def only(model):
    """LD-42: load only the model this step uses (llama.cpp); the other servers are stopped."""
    if MANAGE:
        rc = subprocess.call(["bash", SERVERS, "only", model], stdout=open(LOG, "a"), stderr=subprocess.STDOUT)
        if rc != 0:
            log(f"could not start the {model} server (rc={rc})")


def step(r, args, est_screens, reader, what, name):
    name += TAG
    only(reader)
    est = est_screens * SPS[reader]
    left = STOP - time.time()
    if est > left:
        log(f"SKIP {what}: needs ~{est / 60:.0f} min, {left / 60:.0f} min left")
        return False
    log(f"start {what} (~{est_screens} screens, ~{est / 60:.0f} min)")
    t, before = time.time(), screens_done(r, name)
    rc = subprocess.call([PY, RUN, *args, "--round", str(r), "--parallel", PARALLEL, "--agents", str(AGENTS)] + ([] if REPLAY else ["--no-replay"]), cwd=REPO,
                         stdout=open(f"/tmp/v2_{name}.log", "a"), stderr=subprocess.STDOUT)
    did = screens_done(r, name) - before
    if did > 20:
        SPS[reader] = (time.time() - t) / did
    log(f"end {what} rc={rc}: {did} screens in {(time.time() - t) / 60:.1f} min ({SPS[reader]:.2f} s/screen)")
    if rc != 0 and did == 0:
        # LB-v2-3 lesson: a step that fails before a single screen means something is broken (server, code, env);
        # stop the whole run instead of failing every remaining step in seconds. Re-running resumes.
        log(f"STOPPING: '{what}' failed with nothing done -- see /tmp/v2_{name}.log; fix it, then run the same command again")
        raise SystemExit(2)
    return rc == 0


def checkpoint(r, msg):
    sh = f"{' '.join(NICE)} {PY} {os.path.join(HERE, 'analyze_v2.py')} > /dev/null 2>&1; " \
         f"git add data/llm_bias/v2/r{r:03d} data/llm_bias/v2/summary.md; " \
         f"git commit -qm 'LLM Bias v2 round {r}: {msg}' -m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'"
    if PUSH:
        sh += "; git push -q origin llm-bias"
    subprocess.Popen(["sh", "-c", sh], cwd=REPO, stdout=open("/tmp/v2_commits.log", "a"), stderr=subprocess.STDOUT)
    log(f"checkpoint round {r}: {msg}")


log(f"start: rounds {ROUNDS}, models {MODELS}, slices {SLICES}, stop {datetime.fromtimestamp(STOP):%F %H:%M}")
for r in ROUNDS:
    # LD-40 (Gordon): baselines first, one AI at a time -- AI posts, then the same AI reads ALL of its own posts --
    # and only then the cross tests. Order does not change any answer (every screen is independent); it means the
    # three baselines are complete before any cross reading starts.
    for m in MODELS:
        if not os.path.exists(os.path.join(rdir(r), f"posting_{m.replace(':', '-')}{TAG}.manifest.json")):
            step(r, ["post", "--model", m], 100, m, f"r{r} post {m}", f"posting_{m.replace(':', '-')}")
        n = n_posts(r, m)
        name = f"reading_{m.replace(':', '-')}__{m.replace(':', '-')}"
        todo = max(0, expected(r, m, 0) - screens_done(r, name + TAG)) if n else 0
        if todo:
            step(r, ["read", "--posts-by", m, "--model", m], todo, m, f"r{r} BASELINE {m} reads own posts (all)", name)
    sets = {m: n_posts(r, m) for m in MODELS}
    log(f"r{r} post sets: {sets}; baselines done")
    checkpoint(r, "baselines")
    # cross tests, in growing slices so all six cells stay evenly covered if time runs short
    for k in SLICES:
        for reader in MODELS:
            for pb in MODELS:
                if pb == reader or sets[pb] == 0:
                    continue
                name = f"reading_{pb.replace(':', '-')}__{reader.replace(':', '-')}"
                todo = max(0, expected(r, pb, k) - screens_done(r, name + TAG))
                if todo:
                    step(r, ["read", "--posts-by", pb, "--model", reader] + (["--max-posts", str(k)] if k else []),
                         todo, reader, f"r{r} CROSS {reader} reads {pb} slice {k or 'all'}", name)
        checkpoint(r, f"cross tests slice {k or 'all'}")
    if NOISE:
        for m in MODELS:
            if sets[m]:
                name = f"reading_{m.replace(':', '-')}__{m.replace(':', '-')}_d1"
                todo = max(0, AGENTS * min(NOISE, sets[m] - 1) - screens_done(r, name + TAG))
                if todo:
                    step(r, ["read", "--posts-by", m, "--model", m, "--max-posts", str(NOISE), "--draw", "1"],
                         todo, m, f"r{r} noise floor {m}", name)
        checkpoint(r, "noise floor")
for m in MODELS:
    subprocess.call(["curl", "-s", URL + "/api/generate", "-d", json.dumps({"model": m, "keep_alive": 0})],
                    stdout=subprocess.DEVNULL)
if os.environ.get("STOP_OLLAMA", "1") == "1":
    subprocess.call(["pkill", "-u", os.environ.get("USER", ""), "-f", "ollama serve"])
    subprocess.call(["bash", SERVERS, "stop"], stdout=open(LOG, "a"), stderr=subprocess.STDOUT)  # waits until exited
log("end: models unloaded")
