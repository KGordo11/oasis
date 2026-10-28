"""Speed tests on the Spark (Gordon 10-28, log 14.59). Run only when nothing else of ours runs (after ARM 2 DONE).

IN PLAIN WORDS
--------------
Every speed idea gets its own test = the reference + ONE change, applied the same way to all three AIs. The reference is
the setup of the big sim (V3, live world, 8 slots, today's llama.cpp). In every test each AI reads its OWN posts from
part 1 (`data/llm_bias/v3/r101`): every user reads the first K posts of their scroll (K=6: ~600 posts read per AI), in a
fresh live world of its own. Same users, same posts, same seeds in every test, so the answers can be compared screen by
screen (speed_summary.py): did the change make it faster, and did it change what the AIs do?

  ref         the reference (8 slots)
  ref_redo    the reference again with fresh randomness: how much answers move by chance (the yardstick)
  slots16     16 slots (LD-46, already chosen: tested here too)
  ub2048      bigger internal batch (-ub 2048)
  cacheram0   no RAM prompt cache (--cache-ram 0)
  swafull     gemma keeps its whole sliding-window memory (--swa-full; qwen and llama have none, so no effect there)
  kvunified   one memory pool shared by all slots (--kv-unified)
  cachereuse  reuse repeated text from memory even when it's not at the start (--cache-reuse 256)
  spec_ngram  speculative decoding, guesses from text already seen (--spec-type ngram-simple)
  spec_draft  speculative decoding, guesses from a small AI of the same family (qwen3 0.6B, llama3.2 1B, gemma3 1B)
  order_b     a PROMPT change: menu + answer format at the top of every screen (--shared-first)
  newbuild    the newest llama.cpp, built next to ours (engines/llama.cpp-new)
  worlds3     all three AIs at once, each in its own separate world (3 servers loaded; needs ~60 GB free)

Before the tests: the small models are downloaded and the new llama.cpp is built (only what is missing). A test that
can't start (a server refuses a flag, a download fails, not enough memory) is recorded as FAILED/SKIPPED and the suite
goes on. Every test checks that its server really runs with its flag (from `ps`), so a setting can't silently not happen.
Resumable: run the same command again and only unfinished parts run (a half-done part is redone from zero, so its time
is clean). Ends with the summary (speed_summary.py) in data/llm_bias/speed/summary.md and the line SPEED SUITE DONE.

    python3 examples/experiment/llm_bias/speed_suite.py                (all tests, ~16 h on a shared Spark)
    TESTS="ref slots16" K=6 python3 examples/experiment/llm_bias/speed_suite.py
"""
import fcntl, json, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PY = os.environ.get("PY", sys.executable)
SERVERS = os.path.join(HERE, "llamacpp_servers.sh")
ROOT = os.environ.get("LLM_BIAS_HOME", os.path.expanduser("~/llm_bias"))
OUT = os.environ.get("SPEED_DIR", os.path.join(REPO, "data", "llm_bias", "speed"))
SRC = os.environ.get("SPEED_POSTS", os.path.join(REPO, "data", "llm_bias", "v3", "r101"))  # part 1's posts
K, AGENTS = int(os.environ.get("K", "6")), int(os.environ.get("AGENTS", "100"))
MANAGE = os.environ.get("MANAGE_SERVERS", "1") == "1"
MODELS = ["qwen3:8b", "llama3.1:8b", "gemma3:12b"]
NEW = os.path.join(ROOT, "engines", "llama.cpp-new")
DRAFT = {"qwen3:8b": "https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/resolve/main/Qwen3-0.6B-Q8_0.gguf",
         "llama3.1:8b": "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q8_0.gguf",
         "gemma3:12b": "https://huggingface.co/ggml-org/gemma-3-1b-it-GGUF/resolve/main/gemma-3-1b-it-Q8_0.gguf"}
short = lambda m: m.replace(":", "-")  # noqa: E731
TESTS = [  # name, what changes (the ONE change vs ref), settings
    ("ref", "reference: the big sim's setup, 8 slots", {}),
    ("ref_redo", "reference again, fresh randomness (yardstick)", {"draw": 1}),
    ("slots16", "16 slots (LD-46)", {"slots": 16}),
    ("ub2048", "server -ub 2048", {"server": "-ub 2048"}),
    ("cacheram0", "server --cache-ram 0", {"server": "--cache-ram 0"}),
    ("swafull", "server --swa-full", {"server": "--swa-full"}),
    ("kvunified", "server --kv-unified", {"server": "--kv-unified"}),
    ("cachereuse", "server --cache-reuse 256", {"server": "--cache-reuse 256"}),
    ("spec_ngram", "speculative decoding, n-gram guesses", {"server": "--spec-type ngram-simple"}),
    ("spec_draft", "speculative decoding, small same-family model", {"server": f"-md {ROOT}/models/draft/@MODEL@.gguf --spec-type draft-simple", "prep": "draft"}),
    ("order_b", "prompt: menu + format first (--shared-first)", {"run": ["--shared-first"]}),
    ("newbuild", "newest llama.cpp build", {"bin": os.path.join(NEW, "build", "bin", "llama-server"), "prep": "build"}),
    ("worlds3", "three AIs at once, own worlds", {"together": True}),
]
PICK = os.environ.get("TESTS", "").split() or [t[0] for t in TESTS]
LOG = os.path.join(OUT, "suite.log")


def log(msg):
    line = f"{time.strftime('%F %T')} {msg}"
    print(line, flush=True)
    open(LOG, "a").write(line + "\n")


def sh(cmd, env=None, out=None):
    return subprocess.call(cmd, cwd=REPO, env=env, stdout=open(out, "a") if out else subprocess.DEVNULL, stderr=subprocess.STDOUT)


def prep_draft():
    d = os.path.join(ROOT, "models", "draft")
    os.makedirs(d, exist_ok=True)
    for m, url in DRAFT.items():
        f = os.path.join(d, short(m) + ".gguf")
        if not os.path.exists(f):
            log(f"prep: downloading the draft model for {m}")
            if sh(["curl", "-fsSL", "-o", f + ".part", url], out=LOG) != 0:
                return f"download failed: {url}"
            os.rename(f + ".part", f)
        if os.path.getsize(f) < 100e6:
            return f"draft model too small: {f}"
    return None


def prep_build():
    exe = os.path.join(NEW, "build", "bin", "llama-server")
    if not os.path.exists(exe):  # the same build commands as ours (log 14.32b), newest llama.cpp
        log("prep: building the newest llama.cpp in engines/llama.cpp-new (~20-40 min)")
        b = os.path.join(OUT, "build_new.log")
        env = dict(os.environ, PATH="/usr/local/cuda/bin:" + os.environ["PATH"], CUDACXX="/usr/local/cuda/bin/nvcc")
        if not os.path.exists(NEW) and sh(["git", "clone", "--depth", "1", "https://github.com/ggml-org/llama.cpp", NEW], out=b):
            return "git clone failed (see build_new.log)"
        if sh(["nice", "-n", "19", "cmake", "-S", NEW, "-B", os.path.join(NEW, "build"), "-DGGML_CUDA=ON", "-DCMAKE_CUDA_ARCHITECTURES=121",
               "-DLLAMA_CURL=OFF", "-DCMAKE_BUILD_TYPE=Release"], env=env, out=b) or \
           sh(["nice", "-n", "19", "cmake", "--build", os.path.join(NEW, "build"), "--config", "Release", "-j", "8", "--target", "llama-server"], env=env, out=b):
            return "build failed (see build_new.log)"
    v = subprocess.run(["git", "-C", NEW, "log", "-1", "--format=%h %cd", "--date=short"], capture_output=True, text=True).stdout.strip()
    log(f"prep: new llama.cpp = {v}")
    return None


def server_args():
    """The command line of every running llama-server of ours (the proof a setting really happened)."""
    pids = subprocess.run(["pgrep", "-u", os.environ.get("USER", ""), "-f", "llama-server -m"], capture_output=True, text=True).stdout.split()
    return [subprocess.run(["ps", "-o", "args=", "-p", p], capture_output=True, text=True).stdout.strip() for p in pids]


def servers(cfg, how, model=None):
    """Start the server(s) for this test; return (error or None, their command lines)."""
    if not MANAGE:
        return None, ["not managed (laptop test)"]
    env = dict(os.environ, SLOTS=str(cfg.get("slots", 8)), SERVER_ARGS=cfg.get("server", ""), LLAMA_BIN=cfg.get("bin", ""))
    sh(["bash", SERVERS, "stop"], out=LOG)
    if sh(["bash", SERVERS, how] + ([model] if model else []), env=env, out=LOG) != 0:
        return f"server did not start ({how} {model or ''}; see ~/llm_bias/logs/llamacpp_*.log)", []
    args = server_args()
    want = [f"-np {cfg.get('slots', 8)}"] + ([cfg["server"].replace("@MODEL@", short(model or ""))] if "server" in cfg else []) \
        + ([cfg["bin"]] if "bin" in cfg else [])
    bad = [w for w in want if not all(w in a for a in args)] if args else ["no server running"]
    return (f"server is missing {bad}: {args}" if bad else None), args


def reading_cmd(cfg, m, d):
    return [PY, os.path.join(HERE, "run_v2.py"), "read", "--round", "101", "--posts-by", m, "--model", m, "--v3",
            "--max-posts", str(K), "--parallel", str(cfg.get("slots", 8)), "--agents", str(AGENTS), "--data-dir", d,
            "--no-replay"] + (["--draw", str(cfg["draw"])] if cfg.get("draw") else []) + cfg.get("run", [])


def out_file(cfg, m, d):
    tag = f"_a{AGENTS}" if AGENTS < 100 else ""
    return os.path.join(d, "r101", f"reading_{short(m)}__{short(m)}{'_d%d' % cfg['draw'] if cfg.get('draw') else ''}{tag}")


def counts(f):
    rows = [json.loads(l) for l in open(f + ".jsonl") if l.strip()] if os.path.exists(f + ".jsonl") else []
    return {"posts_read": sum(r.get("screen", "post") == "post" and r.get("view", 1) == 1 for r in rows), "screens": len(rows),
            "unreadable": sum(r["outcome"] != "chose" for r in rows)}


def record(d, rec):
    open(os.path.join(d, "timing.jsonl"), "a").write(json.dumps(rec) + "\n")
    log(f"  {rec['test']} {rec['model']}: {rec['status']}" + (f" -- {rec['wall_s'] / 60:.1f} min, {rec['posts_read']} posts read, "
        f"{rec['wall_s'] / max(rec['posts_read'], 1):.2f} s per post read" if rec["status"] == "OK" else f" -- {rec.get('why', '')}"))


def done(d):
    f = os.path.join(d, "timing.jsonl")
    return {r["model"] for r in map(json.loads, open(f)) if r["status"] == "OK"} if os.path.exists(f) else set()


def run_test(name, what, cfg, prep_err):
    d = os.path.join(OUT, name)
    os.makedirs(os.path.join(d, "r101"), exist_ok=True)
    for f in os.listdir(SRC):  # part 1's posts, the same for every test
        if f.startswith("posting_") and f.endswith(".jsonl"):
            shutil.copy(os.path.join(SRC, f), os.path.join(d, "r101", f))
    todo = [m for m in MODELS if m not in done(d)]
    if not todo:
        return
    log(f"TEST {name}: {what}")
    base = {"test": name, "what": what, "k": K, "agents": AGENTS, "slots": cfg.get("slots", 8)}
    for m in todo:  # a half-done part is redone from zero, so its time is clean
        for ext in (".jsonl", ".manifest.json"):
            if os.path.exists(out_file(cfg, m, d) + ext):
                os.remove(out_file(cfg, m, d) + ext)
    if prep_err:
        for m in todo:
            record(d, dict(base, model=m, status="FAILED", why=prep_err))
        return
    if cfg.get("together"):
        avail = mem_free_gb()
        if MANAGE and avail is not None and avail < 60:
            for m in todo:
                record(d, dict(base, model=m, status="SKIPPED", why=f"only {avail:.0f} GB free, needs ~60 for three AIs"))
            return
        err, args = servers(cfg, "start")
        if err:
            for m in todo:
                record(d, dict(base, model=m, status="FAILED", why=err))
            return
        t0 = time.time()
        procs = {m: (subprocess.Popen(reading_cmd(cfg, m, d), cwd=REPO, stdout=open(out_file(cfg, m, d) + ".log", "a"),
                                      stderr=subprocess.STDOUT), time.time()) for m in todo}
        ends = {}
        while len(ends) < len(procs):
            for m, (p, _) in procs.items():
                if m not in ends and p.poll() is not None:
                    ends[m] = time.time()
            time.sleep(2)
        for m, (p, t) in procs.items():
            record(d, dict(base, model=m, status="OK" if p.returncode == 0 else "FAILED", why=f"rc={p.returncode}",
                           wall_s=ends[m] - t, together_wall_s=max(ends.values()) - t0, server_args=args, **counts(out_file(cfg, m, d))))
        return
    for m in todo:
        err, args = servers(cfg, "only", m)
        if err:
            record(d, dict(base, model=m, status="FAILED", why=err))
            continue
        t = time.time()
        rc = subprocess.call(reading_cmd(cfg, m, d), cwd=REPO, stdout=open(out_file(cfg, m, d) + ".log", "a"), stderr=subprocess.STDOUT)
        c = counts(out_file(cfg, m, d))
        ok = rc == 0 and c["posts_read"] > 0 and c["unreadable"] <= 0.05 * c["screens"]
        record(d, dict(base, model=m, status="OK" if ok else "FAILED", why=f"rc={rc}, {c}", wall_s=time.time() - t, server_args=args, **c))


def mem_free_gb():
    try:
        return int(next(l for l in open("/proc/meminfo") if l.startswith("MemAvailable")).split()[1]) / 1e6
    except (OSError, StopIteration):
        return None


def main():
    os.makedirs(OUT, exist_ok=True)
    lock = open(os.path.join(OUT, ".lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        sys.exit("the speed suite is already running")
    busy = subprocess.run(["pgrep", "-u", os.environ.get("USER", ""), "-f", "v3_big.sh|v2_night.py|preflight_v2.py|slot_bench.sh"],
                          capture_output=True, text=True).stdout.split()
    if MANAGE and busy:  # bug class 0: two things driving the servers at once
        sys.exit(f"something else of ours is running (pids {busy}): wait until it is done")
    unknown = [t for t in PICK if t not in {n for n, _, _ in TESTS}]
    if unknown:
        sys.exit(f"unknown tests {unknown}")
    if os.environ.get("LLM_BACKEND") != "llamacpp" or not os.environ.get("LLAMACPP_URLS"):
        sys.exit("run first:  source ~/llm_bias/env_llamacpp.sh")
    if not any(f.startswith("posting_") for f in os.listdir(SRC)):
        sys.exit(f"no posts in {SRC}")
    log(f"start: tests {PICK}, K={K} posts per user, {AGENTS} users, managed servers={MANAGE}")
    preps = {}
    for name, what, cfg in TESTS:
        if name in PICK:
            p = cfg.get("prep")
            if p and MANAGE and p not in preps:
                preps[p] = (prep_draft if p == "draft" else prep_build)()
            run_test(name, what, cfg, preps.get(p) if p else None)
    if MANAGE:
        sh(["bash", SERVERS, "stop"], out=LOG)
    subprocess.call([PY, os.path.join(HERE, "speed_summary.py"), OUT], cwd=REPO, stdout=open(os.path.join(OUT, "summary.md"), "w"))
    log("SPEED SUITE DONE (summary: data/llm_bias/speed/summary.md)")


if __name__ == "__main__":
    main()
