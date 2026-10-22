"""One command that checks the whole LLM Bias pipeline end to end with fake AIs (log 14.47). Laptop or Spark, ~2 min.

    python3 examples/experiment/llm_bias/smoke_test.py          # (laptop: oasis-env/bin/python ...)

IN PLAIN WORDS
--------------
No model is used: fake_engine.py stands in for the three llama.cpp servers and answers like an AI (posts, votes,
comments, searches, groups, private messages). Everything else is the real code, run the way the Spark runs it:

  1. unit tests: test_live_world.py (always), test_llm_bias.py (when pytest + numpy are installed)
  2. V1 round       v2_night.py, 4 users: posting, baselines, cross cells, noise floor
  3. V3 big sim     v3_big.sh, 4 users: arm 1 (V3) and arm 2 (same posts, flipped menu)
  4. V3 live world  v2_night.py EXTRA="--v3 --live", 6 users; then a hard kill half-way through a cell and a resume
After each, the CHECKS below. The last line is "SMOKE: ALL PASS" or "SMOKE: n FAILED" with the list.
  - every user read every post of every set except their own, exactly once (post screens, first view)
  - no unreadable answers; every manifest says the right version and changes
  - every request had the intended settings: thinking (V3 reading only), JSON mode ON, which menu came first
  - arm 2 read exactly arm 1's posts; the live world really made comments, groups and private messages, and every
    follow-up screen shows its real result; after a resume nothing is missing or doubled
Run it after any code change, before giving Gordon a command. It never touches data/llm_bias/v* (temp folder only).
"""
import glob, json, os, shutil, signal, socket, subprocess, sys, tempfile, time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PY = sys.executable
MODELS = ["qwen3:8b", "llama3.1:8b", "gemma3:12b"]
fails, passes = [], 0


def check(name, ok, detail=""):
    global passes
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""), flush=True)
    passes += bool(ok)
    if not ok:
        fails.append(name)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def load(f):
    return [json.loads(l) for l in open(f) if l.strip()]


def check_dir(d, label, agents, version, changes, live=False):
    """Every reading file: every non-own post read once; manifests; posts."""
    r = sorted(glob.glob(os.path.join(d, "r*")))
    check(f"{label}: round folder exists", bool(r), d)
    if not r:
        return
    r = r[0]
    tag = f"_a{agents}"
    posts = {}
    for m in MODELS:
        f = os.path.join(r, f"posting_{m.replace(':', '-')}{tag}.jsonl")
        rows = load(f) if os.path.exists(f) else []
        posts[m] = [(x["user_id"], k) for x in rows for k, a in enumerate(y for y in x["actions"] if y["action"] == "create_post")]
    check(f"{label}: every AI wrote posts", all(posts.values()), str({m: len(v) for m, v in posts.items()}))
    cells = 0
    for reader in MODELS:
        for pb in MODELS:
            f = os.path.join(r, f"reading_{pb.replace(':', '-')}__{reader.replace(':', '-')}{tag}.jsonl")
            if not os.path.exists(f):
                check(f"{label}: cell {reader} reads {pb} exists", False)
                continue
            cells += 1
            rows = load(f)
            main = [x for x in rows if x.get("screen", "post") == "post" and x.get("view", 1) == 1]
            want = sum(1 for u in range(agents) for (a, _) in posts[pb] if a != u)
            keys = [(x["user_id"], x["post_key"]) for x in main]
            ok = len(keys) == want and len(set(keys)) == want and all(x["author_id"] != x["user_id"] for x in main)
            if not ok or reader == pb:
                check(f"{label}: {reader} reads {pb}: every post once, none own", ok, f"{len(set(keys))}/{want}")
            bad = sum(x["outcome"] != "chose" for x in rows)
            if bad:
                check(f"{label}: {reader} reads {pb}: no unreadable", False, f"{bad}")
            man = json.load(open(f.replace(".jsonl", ".manifest.json")))
            if man.get("version") != version or man.get("changes_from_v1") != changes:
                check(f"{label}: {reader} reads {pb}: manifest version/changes", False,
                      f"{man.get('version')} {man.get('changes_from_v1')} != {version} {changes}")
            if live:
                seqs = [(x["user_id"], x["seq"]) for x in rows]
                if len(seqs) != len(set(seqs)):
                    check(f"{label}: {reader} reads {pb}: no doubled screen after resume", False)
    check(f"{label}: all 9 reading cells checked", cells == 9, f"{cells}/9")


def requests(log, **want):
    rs = load(log)
    for k, v in want.items():
        got = Counter(r[k] for r in rs if r.get("screen", "").startswith("You're scrolling") or k != "menu_first")
        check(f"  requests: {k} = {v!r}", set(got) == {v}, str(dict(got)))
    return rs


def main():
    tmp = tempfile.mkdtemp(prefix="llm_bias_smoke_")
    print(f"smoke test in {tmp}")
    print("== 1. unit tests")
    sys.path.insert(0, HERE)
    import test_live_world as T
    for n in sorted(k for k in dir(T) if k.startswith("test_")):
        try:
            getattr(T, n)(); check(f"test_live_world.{n}", True)
        except Exception as e:  # noqa: BLE001
            check(f"test_live_world.{n}", False, repr(e)[:120])
    try:
        import numpy, pytest  # noqa: F401
        rc = subprocess.call([PY, "-m", "pytest", "-q", os.path.join(HERE, "test_llm_bias.py")], cwd=REPO,
                             stdout=open(os.path.join(tmp, "pytest.txt"), "w"), stderr=subprocess.STDOUT)
        check("test_llm_bias.py (pytest)", rc == 0, open(os.path.join(tmp, "pytest.txt")).read().strip().splitlines()[-1])
    except ImportError:
        print("  skip  test_llm_bias.py (needs pytest + numpy; run it on the laptop)")

    # fake servers + a flock shim where the OS has none (macOS)
    bindir = os.path.join(tmp, "bin"); os.makedirs(bindir)
    if not shutil.which("flock"):
        open(os.path.join(bindir, "flock"), "w").write("#!/bin/sh\nexit 0\n"); os.chmod(os.path.join(bindir, "flock"), 0o755)
    reqlog = os.path.join(tmp, "requests.jsonl")
    ports = {m: free_port() for m in MODELS}
    procs = [subprocess.Popen([PY, os.path.join(HERE, "fake_engine.py"), str(p), reqlog]) for p in ports.values()]
    time.sleep(1.5)
    env = dict(os.environ, LLM_BACKEND="llamacpp", PATH=bindir + os.pathsep + os.environ["PATH"], PY=PY,
               LLAMACPP_URLS=json.dumps({m: f"http://127.0.0.1:{p}" for m, p in ports.items()}),
               MANAGE_SERVERS="0", STOP_OLLAMA="0", PUSH="0", CHECKPOINT="0", PARALLEL=os.environ.get("SMOKE_PARALLEL", "4"),
               STOP=time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() + 3 * 3600)))

    def night(data, agents, extra="", **kw):
        open(reqlog, "w").close()
        e = dict(env, DATA_DIR=data, AGENTS=str(agents), EXTRA=extra, ROUNDS="950", NOISE="2", **kw)
        p = subprocess.run([PY, os.path.join(HERE, "v2_night.py")], cwd=REPO, env=e, capture_output=True, text=True, timeout=900)
        check(f"v2_night exit 0 {extra}", p.returncode == 0 and "STOPPING" not in p.stdout,
              (p.stdout + p.stderr).strip().splitlines()[-1][:120] if (p.stdout + p.stderr).strip() else "")
        return p
    try:
        print("== 2. V1 round (4 users)")
        night(os.path.join(tmp, "v1"), 4, "--v1")  # test rounds (>= 900) otherwise get the V2 line
        check_dir(os.path.join(tmp, "v1"), "V1", 4, None, [])
        requests(reqlog, think=False, json=True)

        print("== 3. V3 big sim, both arms (4 users)")
        open(reqlog, "w").close()
        e = dict(env, V3_ROOT=os.path.join(tmp, "big"), AGENTS="4", ROUNDS="950", NOISE="2")
        p = subprocess.run(["bash", os.path.join(HERE, "v3_big.sh")], cwd=REPO, env=e, capture_output=True, text=True, timeout=900)
        check("v3_big.sh ends BIG DONE", p.stdout.strip().endswith("BIG DONE"), p.stdout.strip()[-80:])
        check_dir(os.path.join(tmp, "big", "v3"), "V3 arm 1", 4, "V3", ["think", "refresh_loop"])
        check_dir(os.path.join(tmp, "big", "v3_flipped"), "V3 arm 2", 4, "V3", ["think", "refresh_loop", "menu_order"])
        rs = load(reqlog)
        reading = [r for r in rs if r["screen"].startswith("You're scrolling")]
        posting = [r for r in rs if not r["screen"].startswith("You're scrolling")]
        check("V3: every reading request has thinking ON and JSON mode ON", reading and all(r["think"] and r["json"] for r in reading))
        check("V3: every posting request has thinking OFF and JSON mode ON", posting and all(not r["think"] and r["json"] for r in posting))
        firsts = Counter(r["menu_first"] for r in reading)
        check("V3: reading menus are V1 order (arm 1) and flipped (arm 2)", set(firsts) == {"ON THE POST ON YOUR SCREEN", "GROUP CHATS"}, str(dict(firsts)))
        same = all(open(f, "rb").read() == open(f.replace("/v3/", "/v3_flipped/"), "rb").read()
                   for f in glob.glob(os.path.join(tmp, "big", "v3", "r*", "posting_*.jsonl")))
        check("V3: arm 2 read exactly arm 1's posts", same)
        n0 = len(load(reqlog))
        subprocess.run(["bash", os.path.join(HERE, "v3_big.sh")], cwd=REPO, env=e, capture_output=True, text=True, timeout=300)
        check("V3: running it again asks the AI nothing (all done)", len(load(reqlog)) == n0, f"{len(load(reqlog)) - n0} new calls")

        print("== 4. V3 live world (6 users), then a hard kill and resume")
        live = os.path.join(tmp, "live")
        night(live, 6, "--v3 --live", SLICES="0")
        check_dir(live, "V3 live", 6, "V3", ["think", "refresh_loop", "live"], live=True)
        rows = [x for f in glob.glob(os.path.join(live, "r*", "reading_*.jsonl")) for x in load(f)]
        kinds = Counter(x["screen"] for x in rows)
        done = Counter(e["action"] for x in rows for e in x["executed"] if e["ok"])
        check("live: follow-up screens happened (search, profiles, groups, messages)",
              all(kinds[k] for k in ("search_user", "listen_from_group", "open_messages")), str(dict(kinds)))
        check("live: comments, groups, joins and private messages really happened",
              all(done[k] for k in ("create_comment", "create_group", "join_group", "send_message", "like_comment")),
              str({k: done[k] for k in ("create_comment", "create_group", "join_group", "send_to_group", "send_message", "like_comment")}))
        prof = [x for x in rows if x["screen"] == "search_user"]
        check("live: a profile screen shows the real result", any("u/" in x["text"] and "post" in x["text"] for x in prof))
        dm_ok = all(e["ok"] or e["error"].startswith("you can only message") for x in rows for e in x["executed"] if e["action"] == "send_message")
        check("live: messages only fail for 'not on a profile or inbox'", dm_ok)
        # hard kill half-way through one cell, then the same command again
        f = sorted(glob.glob(os.path.join(live, "r*", "reading_qwen3-8b__llama3.1-8b_a6.jsonl")))[0]
        full = load(f)
        man = f.replace(".jsonl", ".manifest.json")
        with open(f, "w") as o:
            o.writelines(json.dumps(x) + "\n" for x in full[: len(full) // 2])
            o.write('{"broken": half a line')  # what a SIGKILL mid-write leaves
        os.remove(man)
        night(live, 6, "--v3 --live", SLICES="0")
        again = load(f)
        seqs = [(x["user_id"], x["seq"]) for x in again]
        main = [x for x in again if x["screen"] == "post" and x["view"] == 1]
        check("live resume: no doubled screen, every post read once",
              len(seqs) == len(set(seqs)) and len(main) == len({(x["user_id"], x["post_key"]) for x in main}) ==
              len([x for x in full if x["screen"] == "post" and x["view"] == 1]), f"{len(again)} rows (first run {len(full)})")
        check("live resume: the kept half is unchanged", again[: len(full) // 2] == full[: len(full) // 2])

        print("== 5. analysis on the fake data")
        p = subprocess.run([PY, os.path.join(HERE, "live_summary.py"), live], cwd=REPO, capture_output=True, text=True)
        check("live_summary.py runs", p.returncode == 0 and "STEPS" in p.stdout, (p.stderr or p.stdout).strip()[-120:])
    finally:
        for p in procs:
            p.send_signal(signal.SIGTERM)
    print(f"\nSMOKE: {'ALL PASS' if not fails else f'{len(fails)} FAILED'} ({passes} checks passed)")
    for n in fails:
        print("  FAILED:", n)
    if not fails:
        shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
