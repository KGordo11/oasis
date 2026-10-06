"""Full preflight for LLM Bias v2 on the DGX Spark: every part, end to end, PASS/FAIL per check (log Part 14).

IN PLAIN WORDS
--------------
Run this before leaving a real round unattended. It needs about 20-30 minutes and uses test round 904 (10 users),
which the real analysis ignores. It checks, in order:
  A. setup        the code includes every fix, settings files, llama.cpp program, all 3 model files, disk, memory,
                  nothing else of yours already running
  B. code         the 100 users are the pinned ones, the answer checkers accept good answers and reject bad ones
  C. each AI      switch to it alone, exactly one server loaded, a real answer comes back as JSON, thinking off
  D. switching    qwen -> llama -> gemma -> qwen, each time the right server answers (what broke on 2026-10-05)
  E. mini-round   the real runner (v2_night.py) on 10 users: every step rc=0, then the DATA is checked -- every user
                  read every post, nobody read their own post, no duplicates, few unreadable answers, every file
                  records llama.cpp + the same sampling settings, every AI's posting turn exists
  F. resume       a reading step is killed half-way on purpose, restarted, and must end complete with no duplicates
  G. clean finish the runner stops the servers at the end and the memory comes back

    source ~/llm_bias/env_llamacpp.sh && python3 examples/experiment/llm_bias/preflight_v2.py
Exit code 0 = everything passed.
"""
import glob, json, os, shutil, signal, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
ROUND, AGENTS, TAG = 904, 10, "_a10"
RD = os.path.join(REPO, "data", "llm_bias", "v2", f"r{ROUND:03d}")
SERVERS = os.path.join(HERE, "llamacpp_servers.sh")
HOME = os.path.expanduser("~/llm_bias")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""), flush=True)
    return ok


def sh(cmd, timeout=600):
    p = subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True, text=True, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).strip()


def free_gb():
    try:
        for line in open("/proc/meminfo"):
            if line.startswith("MemAvailable"):
                return int(line.split()[1]) / 1048576
    except OSError:
        pass
    return 0  # not Linux: the memory checks will show FAIL, never crash


def servers_running():
    return len(my_procs("llama-server -m"))


print("=== A. setup")
rc, _ = sh("git merge-base --is-ancestor 5f794c9 HEAD")
check("code includes the LB-v2-3 fix (5f794c9)", rc == 0)
check("llama.cpp backend selected (env_llamacpp.sh sourced)", os.environ.get("LLM_BACKEND") == "llamacpp",
      os.environ.get("LLM_BACKEND", "not set"))
urls = json.loads(os.environ.get("LLAMACPP_URLS", "{}"))
check("server addresses for all 3 AIs", set(urls) == {"qwen3:8b", "llama3.1:8b", "gemma3:12b"}, str(sorted(urls)))
check("llama-server program exists", os.path.exists(os.path.join(HOME, "engines/llama.cpp/build/bin/llama-server")))
for m in ["qwen3:8b", "llama3.1:8b"]:
    man = os.path.join(HOME, "models/manifests/registry.ollama.ai/library", m.split(":")[0], m.split(":")[1])
    ok = os.path.exists(man) and any(os.path.exists(os.path.join(HOME, "models/blobs", l["digest"].replace(":", "-")))
                                     for l in json.load(open(man))["layers"] if l["mediaType"].endswith(".model"))
    check(f"model file for {m}", ok)
check("model file for gemma3:12b (standard GGUF)", os.path.getsize(os.path.join(HOME, "models/gguf/gemma3-12b.gguf")) > 6e9
      if os.path.exists(os.path.join(HOME, "models/gguf/gemma3-12b.gguf")) else False)
check("disk: at least 20 GB free in home", shutil.disk_usage(os.path.expanduser("~")).free > 20e9,
      f"{shutil.disk_usage(os.path.expanduser('~')).free / 1e9:.0f} GB free")
def my_procs(*needles):
    """Your processes whose command line contains any needle -- plain ps (same on Linux and macOS), never this one."""
    me = {os.getpid(), os.getppid()}
    out = subprocess.run(["ps", "-u", os.environ.get("USER", ""), "-o", "pid=,args="], capture_output=True, text=True).stdout
    return [l.strip() for l in out.splitlines()
            if any(n in l for n in needles) and "preflight" not in l and int(l.split()[0]) not in me]


busy = my_procs("v2_night.py", "run_v2.py")
check("no other run of yours is going", not busy, "; ".join(busy)[:120])
check("python 3.9+", sys.version_info >= (3, 9), sys.version.split()[0])

print("=== B. code")
import llm, run_v2  # noqa: E402
try:
    P = run_v2.load_personas()
    check("100 pinned users unchanged (hash)", len(P) == 100)
except SystemExit as e:
    check("100 pinned users unchanged (hash)", False, str(e))
good = run_v2.validate({"actions": [{"action": "upvote"}, {"action": "comment", "content": "nice"}], "reason": "x"})
check("answer checker accepts a good answer", [a["action"] for a in good["actions"]] == ["like_post", "create_comment"])
for bad in ({"actions": [{"action": "fly"}]}, {"actions": [{"action": "create_post", "subreddit": "r/cats", "title": "a", "body": "b"}]},
            {"actions": [{"action": "comment"}]}):
    try:
        run_v2.validate(bad); check(f"answer checker rejects {bad['actions'][0]}", False)
    except ValueError:
        check(f"answer checker rejects {bad['actions'][0]['action']}", True)
check("sampling identical for every AI", llm.SAMPLING == {"top_k": 40, "top_p": 0.9, "min_p": 0.0, "repeat_penalty": 1.0},
      str(llm.SAMPLING))

print("=== C/D. each AI alone, and switching between them")
for m in ["qwen3:8b", "llama3.1:8b", "gemma3:12b", "qwen3:8b"]:
    rc, out = sh(f"bash {SERVERS} only {m}", timeout=300)
    check(f"switch to {m} only", rc == 0 and "READY" in out or "already only" in out, out.splitlines()[-1] if out else "")
    check(f"  exactly one server loaded", servers_running() == 1, f"{servers_running()} running")
    check(f"  server check sees {m} (and only it)", llm.server_up() and llm.available_models() == [m], str(llm.available_models()))
    obj, meta = llm.chat_json(m, "Reply with JSON only.", 'Reply with {"ok": true}', seed=1, num_predict=20)
    check(f"  real answer from {m} is valid JSON", obj == {"ok": True}, str(obj or meta.get("raw"))[:80])
    check(f"  no hidden thinking", meta["thinking_chars"] == 0, str(meta["thinking_chars"]))
one_loaded = free_gb()
check("free memory with one AI loaded", one_loaded > 60, f"{one_loaded:.0f} GB available")

print("=== E. mini-round through the real runner (10 users, round 904)")
shutil.rmtree(RD, ignore_errors=True)
env = dict(os.environ, MANAGE_SERVERS="1", STOP=time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() + 6 * 3600)),
           ROUNDS=str(ROUND), AGENTS=str(AGENTS), SLICES="4 0", NOISE="2", PARALLEL="8", PY=sys.executable,
           PUSH="0", STOP_OLLAMA="1")
t = time.time()
p = subprocess.run([sys.executable, os.path.join(HERE, "v2_night.py")], cwd=REPO, env=env, capture_output=True, text=True,
                   timeout=7200)
log = p.stdout + p.stderr
ends = [l for l in log.splitlines() if " end r904" in l]
check("runner finished (exit 0, no STOPPING)", p.returncode == 0 and "STOPPING" not in log,
      f"exit {p.returncode}, {(time.time() - t) / 60:.0f} min")
check("every step rc=0", ends and all("rc=0" in l for l in ends), f"{sum('rc=0' in l for l in ends)}/{len(ends)} steps ok")
G = "G. clean finish: servers stopped at the end"
check(G, servers_running() == 0, f"{servers_running()} still running")
check("   memory back (more free than with one AI loaded)", free_gb() > one_loaded + 5,
      f"{free_gb():.0f} GB available now vs {one_loaded:.0f} GB with one AI")

posts = {}
for m in ["qwen3:8b", "llama3.1:8b", "gemma3:12b"]:
    f = os.path.join(RD, f"posting_{m.replace(':', '-')}{TAG}.jsonl")
    ok = os.path.exists(f) and os.path.exists(f.replace(".jsonl", ".manifest.json"))
    rows = [json.loads(l) for l in open(f)] if ok else []
    own = {d["user_id"]: sum(a["action"] == "create_post" for a in d["actions"]) for d in rows}
    posts[m] = own
    check(f"posting turn for {m}: all {AGENTS} users answered", len(rows) == AGENTS, f"{sum(own.values())} posts written")
for f in sorted(glob.glob(os.path.join(RD, "reading_*.jsonl"))):
    name = os.path.basename(f).replace(".jsonl", "")
    rows = [json.loads(l) for l in open(f)]
    pb = rows[0]["posts_by"] if rows else None
    draw = rows[0]["draw"] if rows else 0
    pairs = [(r["user_id"], r["post_key"]) for r in rows]
    n = sum(posts.get(pb, {}).values())
    want = sum(min(2, n - posts[pb].get(u, 0)) if draw else n - posts[pb].get(u, 0) for u in range(AGENTS)) if pb else 0
    check(f"{name}: every user read every post ({len(rows)}/{want})", len(rows) == want)
    check(f"  no duplicates", len(pairs) == len(set(pairs)))
    check(f"  nobody read their own post", all(r["author_id"] != r["user_id"] for r in rows))
    bad = sum(r["outcome"] != "chose" for r in rows)
    check(f"  unreadable answers under 5%", bad <= 0.05 * max(1, len(rows)), f"{bad}/{len(rows)}")
    man = json.load(open(f.replace(".jsonl", ".manifest.json")))
    check(f"  file records llama.cpp + uniform sampling", man["config"]["backend"] == "llamacpp"
          and man["config"]["sampling"] == llm.SAMPLING)
rc, out = sh(f"{sys.executable} examples/experiment/llm_bias/analyze_v2.py --test")
check("analysis runs on the mini-round", rc == 0, out.splitlines()[-1][:80] if out else "")

print("=== F. interrupt and resume")
m = "qwen3:8b"
sh(f"bash {SERVERS} only {m}", timeout=300)
cmd = [sys.executable, os.path.join(HERE, "run_v2.py"), "read", "--round", str(ROUND), "--posts-by", m, "--model", m,
       "--agents", str(AGENTS), "--draw", "3", "--no-replay"]
f = os.path.join(RD, f"reading_{m.replace(':', '-')}__{m.replace(':', '-')}_d3{TAG}.jsonl")
n = sum(posts[m].values())
want = sum(n - posts[m].get(u, 0) for u in range(AGENTS))
q = subprocess.Popen(cmd, cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(240):  # kill it once about a third is done (hard kill, like a crash or power cut)
    time.sleep(0.5)
    if os.path.exists(f) and sum(1 for _ in open(f)) >= max(1, want // 3):
        break
q.send_signal(signal.SIGKILL); q.wait()
half = sum(1 for _ in open(f)) if os.path.exists(f) else 0
p = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
rows = [json.loads(l) for l in open(f)] if os.path.exists(f) else []
pairs = [(r["user_id"], r["post_key"]) for r in rows]
check("killed half-way, then resumed to complete", p.returncode == 0 and len(rows) == want and 0 < half < want,
      f"{half} done before the kill, {len(rows)}/{want} after resume")
check("  no duplicates after resume", len(pairs) == len(set(pairs)))
sh(f"bash {SERVERS} stop")
check("  servers stopped after the test", servers_running() == 0)

fails = [r for r in results if not r[1]]
print(f"\n=== {len(results) - len(fails)} PASS, {len(fails)} FAIL")
for name, _, d in fails:
    print(f"  FAIL: {name}  {d}")
print("ALL CLEAR -- safe to start the real round." if not fails else "NOT SAFE -- paste this output to Claude.")
sys.exit(1 if fails else 0)
