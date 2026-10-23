"""Why does gemma act so differently? Diagnostic probes for the Spark (log Part 14 sec. 14.42). Read-only on the study data.

IN PLAIN WORDS
--------------
In the posting turn gemma's users mostly pick "refresh" (57%) or nothing (18%) instead of posting, and say things like
"let's see if anything new has popped up". In the reading turn gemma mostly just votes and rarely comments. These probes
ask WHY, one possible cause at a time, on the machine and engine the study used. Each probe runs on whichever AI's
llama.cpp server is up (llamacpp_servers.sh only <model>), and writes to data/llm_bias/v2/probe/ -- never into r101-r104.

  template   The exact text the engine feeds the model (chat template applied). Gemma 3 has no "system" role, so this
             shows where the person's description really ends up. Also the model file and template the server loaded.
  replay     Re-asks 30 posting and 60 reading screens of round 101 with the recorded seed and prompt: does the pipeline
             reproduce what was saved? (8 at a time, as in the study; batching can change a few answers.)
  posting    The posting turn for all 100 users (round-101 prompt, new seeds, the SAME seed in every variant):
               control       exactly as in the study
               no_refresh    the menu without "refresh: refresh your feed"
               no_empty_line the screen without "Your feed is empty -- nothing has been posted yet."
               free_text     no JSON-only mode on the engine (the study forced JSON output)
               google_sampling Google's recommended Gemma 3 sampling (temperature 1.0, top_k 64, top_p 0.95)
  reading    150 recorded reading screens of round 101 (50 per poster AI), re-asked as control / free_text /
             google_sampling: is the low comment rate the model, the JSON-only mode, or the sampling?
  ask        Each of the 100 users gets its own round-101 posting screen and its own recorded answer, then: why did you
             answer that, what did you expect to happen next, did you see you could write a post? (free text)
  count      Why does gemma do exactly ONE thing per post (log 14.47)? 150 recorded reading screens, re-asked with one
             wording change at a time (same seed in every variant):
               control        exactly as in the study
               no_single      system message "Reply with a JSON object" instead of "a single JSON object"
               two_slots      the answer example shows two action entries instead of one
               more_than_one  + "You can pick more than one." after "as many of these actions as you like, or none."
             then asks each screen's control answer: did you think about doing more than one thing? (free text)
  all        template + replay + posting + reading + ask for the AI that is up.
  summary    One table per probe from every file in the probe folder (any machine; stdlib only).

Usage (Spark):  python3 examples/experiment/llm_bias/gemma_probe.py all --model gemma3:12b
"""
import argparse, json, os, random, sys, time, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import llm  # noqa: E402
import run_v2 as R  # noqa: E402

OUT = os.path.join(R.DATA, "probe")
RND = 101  # every probe uses round 101 (V1: no identity line)
SUBS = "\n".join(f"- {s} ({n})" for s, n in R.TOPICS.values())
GOOGLE = {"temperature": 1.0, "top_k": 64, "top_p": 0.95, "min_p": 0.0, "repeat_penalty": 1.0}
ASK = ("Stepping out of the role for a moment: in one or two sentences, why did you answer the way you did? "
       "What did you expect to happen next? Did you see that you could write a post yourself?")


def call(model, msgs, seed, max_tokens, json_mode=True, sampling=None, temperature=0.7):
    """One request, built exactly like llm._llamacpp() unless a variant overrides json_mode or sampling."""
    p = {"model": model, "messages": msgs, "stream": False, "temperature": temperature, "max_tokens": max_tokens,
         "chat_template_kwargs": {"enable_thinking": False}, **llm.SAMPLING, "seed": seed}
    if json_mode:
        p["response_format"] = {"type": "json_object"}
    if sampling:
        p.update(sampling)
    req = urllib.request.Request(llm.LLAMACPP_URLS[model] + "/v1/chat/completions", json.dumps(p).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        d = json.load(r)
    c = d["choices"][0]
    return c["message"].get("content") or "", c.get("finish_reason"), d.get("usage", {})


def ask_json(model, system, user, seed, budget, **kw):
    """Like llm.chat_json: parse + run_v2.validate, two retries with seed+1, seed+2. Returns (actions|None, raw, tries)."""
    raw = ""
    for k in range(3):
        try:
            raw, _, _ = call(model, [{"role": "system", "content": system}, {"role": "user", "content": user}],
                             seed + k, budget, **kw)
            return R.validate(llm.extract_json(raw)), raw, k + 1
        except Exception as e:  # noqa: BLE001 -- any failure = a retry, like the study
            raw = raw or f"ERROR {e}"
    return None, raw, 3


def post_screen(menu=R.MENU, empty_line=True):
    s = R.POST_SCREEN.format(subs=SUBS, menu=menu, fmt=R.FORMAT)
    return s if empty_line else s.replace(" Your feed is empty -- nothing has been posted yet.", "")


def read_screen(q):
    sub, tname = R.TOPICS[q["topic"]]
    return R.READ_SCREEN.format(sub=sub, topic_name=tname, author=q["author"], title=q["title"], body=q["body"],
                                menu=R.MENU, fmt=R.FORMAT)


def recorded(name):
    return [json.loads(l) for l in open(os.path.join(R.DATA, f"r{RND}", name + ".jsonl"))]


def save(name, rows):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + ".jsonl"), "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    print(f"  wrote probe/{name}.jsonl ({len(rows)} rows)", flush=True)


def pmap(fn, jobs, par):
    t = time.time()
    out = list(ThreadPoolExecutor(par).map(fn, jobs))
    print(f"  {len(jobs)} calls in {time.time() - t:.0f} s", flush=True)
    return out


def t_template(m, people, par):
    props = json.load(urllib.request.urlopen(llm.LLAMACPP_URLS[m] + "/props", timeout=30))
    p = people[0]
    res = {"model": m, "model_path": props.get("model_path"), "chat_template": props.get("chat_template"),
           "n_ctx": (props.get("default_generation_settings") or {}).get("n_ctx")}
    for rnd in (101, 103):
        msgs = [{"role": "system", "content": R.system_prompt(m, rnd, p["persona"])}, {"role": "user", "content": post_screen()}]
        req = urllib.request.Request(llm.LLAMACPP_URLS[m] + "/apply-template", json.dumps({"messages": msgs}).encode(),
                                     {"Content-Type": "application/json"})
        res[f"prompt_r{rnd}"] = json.load(urllib.request.urlopen(req, timeout=30)).get("prompt", "")
    pr = res["prompt_r101"]
    print(f"  model file: {res['model_path']}\n  context per slot: {res['n_ctx']}")
    print(f"  persona text inside the prompt: {p['persona'][:60] in pr};  V2 identity line inside the r103 prompt: "
          f"{'simulating this profile' in res['prompt_r103']}")
    print("  ---- first 700 characters of what the model really reads (round 101, user 0, posting turn):")
    print("  " + pr[:700].replace("\n", "\n  "))
    save(f"template_{R.short(m)}", [res])


def t_replay(m, people, par):
    pid = {p["id"]: p for p in people}
    rows = [r for r in recorded(f"posting_{R.short(m)}") if r["outcome"] == "chose"][:30]
    rng = random.Random(f"probe|replay|{m}")
    for pb in R.MODELS:
        rr = [r for r in recorded(f"reading_{R.short(pb)}__{R.short(m)}") if r["outcome"] == "chose"]
        rows += rng.sample(rr, 20)
    posts = {q["key"]: q for pb in R.MODELS for q in R.post_set(RND, pb, 100)[0]}

    def job(r):
        p, k = pid[r["user_id"]], r["attempts"] - 1  # the seed that produced the saved answer
        if r["turn"] == "post":
            seed, user, budget = llm.stable_seed(R.SEED, RND, "post", p["id"]) + k, post_screen(), 1500
        else:
            seed = llm.stable_seed(R.SEED, RND, "read", r["posts_by"], p["id"], r["post_key"]) + k
            user, budget = read_screen(posts[r["post_key"]]), 800
        raw, _, _ = call(m, [{"role": "system", "content": R.system_prompt(m, RND, p["persona"])},
                             {"role": "user", "content": user}], seed, budget)
        try:
            new = R.validate(llm.extract_json(raw))["actions"]
        except Exception:  # noqa: BLE001
            new = None
        return {"turn": r["turn"], "user_id": r["user_id"], "post_key": r["post_key"], "same_raw": raw == r["raw"],
                "same_actions": new == r["actions"], "saved": r["actions"], "new": new, "raw": raw}
    out = pmap(job, rows, par)
    print(f"  identical reply text: {sum(o['same_raw'] for o in out)}/{len(out)};  identical actions: "
          f"{sum(o['same_actions'] for o in out)}/{len(out)}")
    save(f"replay_{R.short(m)}", out)


def variants():
    no_refresh = "\n".join(l for l in R.MENU.split("\n") if not l.startswith("- refresh:"))
    return {"control": {}, "no_refresh": {"menu": no_refresh}, "no_empty_line": {"empty_line": False},
            "free_text": {"json_mode": False}, "google_sampling": {"sampling": GOOGLE, "temperature": 1.0}}


def t_posting(m, people, par):
    for v, o in variants().items():
        print(f"  posting / {v}")
        user = post_screen(o.get("menu", R.MENU), o.get("empty_line", True))
        kw = {k: o[k] for k in ("json_mode", "sampling", "temperature") if k in o}

        def job(p):
            acts, raw, tries = ask_json(m, R.system_prompt(m, RND, p["persona"]), user,
                                        llm.stable_seed("probe", "posting", m, p["id"]), 1500, **kw)
            return {"variant": v, "user_id": p["id"], "actions": acts, "reason": (acts or {}).get("reason"),
                    "tries": tries, "raw": raw}
        save(f"posting_{v}_{R.short(m)}", pmap(job, people, par))


def t_reading(m, people, par):
    pid = {p["id"]: p for p in people}
    posts = {q["key"]: q for pb in R.MODELS for q in R.post_set(RND, pb, 100)[0]}
    rng = random.Random(f"probe|reading|{m}")
    rows = []
    for pb in R.MODELS:
        rows += rng.sample([r for r in recorded(f"reading_{R.short(pb)}__{R.short(m)}") if r["outcome"] == "chose"], 50)
    for v, o in variants().items():
        if v in ("no_refresh", "no_empty_line"):
            continue  # posting-screen variants only
        print(f"  reading / {v}")
        kw = {k: o[k] for k in ("json_mode", "sampling", "temperature") if k in o}

        def job(r):
            p = pid[r["user_id"]]
            acts, raw, tries = ask_json(m, R.system_prompt(m, RND, p["persona"]), read_screen(posts[r["post_key"]]),
                                        llm.stable_seed("probe", "reading", m, p["id"], r["post_key"]), 800, **kw)
            return {"variant": v, "user_id": r["user_id"], "post_key": r["post_key"], "posts_by": r["posts_by"],
                    "stance": r["stance"], "actions": acts, "saved": r["actions"], "tries": tries, "raw": raw}
        save(f"reading_{v}_{R.short(m)}", pmap(job, rows, par))


def t_ask(m, people, par):
    saved = {r["user_id"]: r for r in recorded(f"posting_{R.short(m)}")}

    def job(p):
        r = saved[p["id"]]
        msgs = [{"role": "system", "content": R.system_prompt(m, RND, p["persona"])}, {"role": "user", "content": post_screen()},
                {"role": "assistant", "content": r.get("raw") or json.dumps({"actions": r["actions"], "reason": r["reason"]})},
                {"role": "user", "content": ASK}]
        text, _, _ = call(m, msgs, llm.stable_seed("probe", "ask", m, p["id"]), 250, json_mode=False)
        kind = ("posted" if any(a["action"] == "create_post" for a in r["actions"]) else
                "nothing" if not r["actions"] else "+".join(sorted({a["action"] for a in r["actions"]})))
        return {"user_id": p["id"], "saved_choice": kind, "saved_reason": r["reason"], "answer": text}
    out = pmap(job, people, par)
    for o in [o for o in out if o["saved_choice"] != "posted"][:6]:
        print(f"  [{o['saved_choice']}] {o['answer'][:220]!r}")
    save(f"ask_{R.short(m)}", out)


FORMAT_TWO = R.FORMAT_TWO
COUNT = {"control": {}, "no_single": {"system": ("a single JSON object", "a JSON object")},
         "two_slots": {"fmt": FORMAT_TWO},
         "more_than_one": {"fmt": R.FORMAT.replace("or none.\n", "or none. You can pick more than one.\n")}}
ASK_COUNT = ("Stepping out of the role for a moment: you took {n} action(s) on this post. Did you think about doing "
             "more than one thing with it (for example voting AND commenting)? In one or two sentences, why or why not?")


def t_count(m, people, par):
    assert all(v.get("fmt", R.FORMAT) != R.FORMAT for k, v in COUNT.items() if "fmt" in v), "a variant did not change"
    pid = {p["id"]: p for p in people}
    posts = {q["key"]: q for pb in R.MODELS for q in R.post_set(RND, pb, 100)[0]}
    rng = random.Random("probe|count")  # the same 150 screens for every AI: 50 per poster, users 0-99
    rows = []
    for pb in R.MODELS:
        rows += rng.sample([r for r in recorded(f"reading_{R.short(pb)}__gemma3-12b") if r["outcome"] == "chose"], 50)
    out = {}
    for v, o in COUNT.items():
        print(f"  count / {v}", flush=True)

        def job(r):
            p, q = pid[r["user_id"]], posts[r["post_key"]]
            system = R.system_prompt(m, RND, p["persona"])
            if "system" in o:
                assert o["system"][0] in system
                system = system.replace(*o["system"])
            sub, tname = R.TOPICS[q["topic"]]
            user = R.READ_SCREEN.format(sub=sub, topic_name=tname, author=q["author"], title=q["title"], body=q["body"],
                                        menu=R.MENU, fmt=o.get("fmt", R.FORMAT))
            acts, raw, tries = ask_json(m, system, user, llm.stable_seed("probe", "count", p["id"], r["post_key"]), 800)
            return {"variant": v, "user_id": r["user_id"], "post_key": r["post_key"], "posts_by": r["posts_by"],
                    "stance": r["stance"], "actions": acts, "tries": tries, "raw": raw, "system": system, "user": user}
        out[v] = pmap(job, rows, par)
        save(f"count_{v}_{R.short(m)}", out[v])
    print("  count / ask", flush=True)

    def ask(r):
        n = sum(a["action"] != "do_nothing" for a in (r["actions"] or {}).get("actions", []))
        msgs = [{"role": "system", "content": r["system"]}, {"role": "user", "content": r["user"]},
                {"role": "assistant", "content": r["raw"]}, {"role": "user", "content": ASK_COUNT.format(n=n)}]
        text, _, _ = call(m, msgs, llm.stable_seed("probe", "count-ask", r["user_id"], r["post_key"]), 200, json_mode=False)
        return {"user_id": r["user_id"], "post_key": r["post_key"], "n_actions": n, "answer": text}
    save(f"countask_{R.short(m)}", pmap(ask, [r for r in out["control"] if r["actions"]], par))


def kind_of(acts):
    if acts is None:
        return "unreadable"
    names = [a["action"] for a in acts["actions"]]
    if "create_post" in names:
        return "posted"
    if not names:
        return "empty list"
    return "only do_nothing" if set(names) == {"do_nothing"} else "only refresh" if set(names) == {"refresh"} else "other"


def summary():
    files = sorted(f for f in os.listdir(OUT) if f.endswith(".jsonl"))
    print("POSTING TURN (100 users each): % of users")
    for f in files:
        if f.startswith("posting_"):
            rows = [json.loads(l) for l in open(os.path.join(OUT, f))]
            c = Counter(kind_of(r["actions"]) for r in rows)
            print(f"  {f[8:-6]:34s} " + "  ".join(f"{k} {c[k]:3d}" for k in ("posted", "only refresh", "empty list", "only do_nothing", "other", "unreadable")))
    print("READING TURN (150 screens each): % of screens")
    for f in files:
        if f.startswith("reading_"):
            rows = [json.loads(l) for l in open(os.path.join(OUT, f))]
            n, ok = len(rows), [r for r in rows if r["actions"]]
            has = lambda a: 100 * sum(any(x["action"] == a for x in r["actions"]["actions"]) for r in ok) / max(1, len(ok))
            empty = 100 * sum(not r["actions"]["actions"] for r in ok) / max(1, len(ok))
            tot = 100 * sum(sum(x["action"] != "do_nothing" for x in r["actions"]["actions"]) for r in ok) / max(1, len(ok))
            print(f"  {f[8:-6]:28s} actions/100 {tot:5.0f}  up {has('like_post'):3.0f}  down {has('dislike_post'):3.0f}  "
                  f"comment {has('create_comment'):3.0f}  empty {empty:3.0f}  do_nothing {has('do_nothing'):3.0f}  unreadable {n - len(ok)}")
    print("ACTION COUNT (count probe, same 150 screens): % of answers with 0 / 1 / 2 / 3+ actions (do_nothing = 0)")
    for f in files:
        if f.startswith("count_"):
            ok = [r for r in map(json.loads, open(os.path.join(OUT, f))) if r["actions"]]
            n = [min(3, sum(x["action"] != "do_nothing" for x in r["actions"]["actions"])) for r in ok]
            com = 100 * sum(any(x["action"] == "create_comment" for x in r["actions"]["actions"]) for r in ok) / max(1, len(ok))
            print(f"  {f[6:-6]:28s} " + " / ".join(f"{100 * n.count(k) / max(1, len(n)):3.0f}" for k in range(4))
                  + f"   actions/100 {100 * sum(n) / max(1, len(n)):4.0f}   comment {com:3.0f}%   unreadable {150 - len(ok)}")
    for f in files:
        if f.startswith("replay_"):
            rows = [json.loads(l) for l in open(os.path.join(OUT, f))]
            print(f"REPLAY {f[7:-6]}: identical text {sum(r['same_raw'] for r in rows)}/{len(rows)}, "
                  f"identical actions {sum(r['same_actions'] for r in rows)}/{len(rows)}")
        if f.startswith("template_"):
            t = json.loads(open(os.path.join(OUT, f)).readline())
            print(f"TEMPLATE {f[9:-6]}: {t['model_path']}  ctx {t['n_ctx']}  prompt starts: {t['prompt_r101'][:90]!r}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("probe", choices=["template", "replay", "posting", "reading", "ask", "count", "all", "summary"])
    ap.add_argument("--model", choices=R.MODELS)
    ap.add_argument("--parallel", type=int, default=8)
    ap.add_argument("--data-dir", help="results folder holding r101 (default data/llm_bias/v2; laptop: data/llm_bias/v1_v2_spark)")
    a = ap.parse_args()
    if a.data_dir:
        R.DATA, OUT = a.data_dir, os.path.join(a.data_dir, "probe")
    if a.probe == "summary":
        summary(); sys.exit()
    if llm.BACKEND != "llamacpp" or a.model not in llm.available_models():
        sys.exit(f"start the server first: source ~/llm_bias/env_llamacpp.sh && bash {HERE}/llamacpp_servers.sh only {a.model}")
    people = R.load_personas()
    for t in (["template", "replay", "posting", "reading", "ask"] if a.probe == "all" else [a.probe]):
        print(f"== {t} ({a.model})", flush=True)
        globals()["t_" + t](a.model, people, a.parallel)
