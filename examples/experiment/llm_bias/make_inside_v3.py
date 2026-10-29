"""Build the 'Inside LLM Bias V3' page (log 14.60): how the V3 big sim works, every file it used and made, what changed
from V1 and why, exactly what each AI was shown, and the cleaned data world by world, tick by tick.

    python3 examples/experiment/llm_bias/make_inside_v3.py <out.html> data/llm_bias/v3 [data/llm_bias/v3_flipped]

Run v3_clean.py on each part first. Part 2 is optional: give its folder and every data view gets part 2 next to part 1.
The page text lives in inside_v3_template.html (styles shared with inside_v2_template.html); this script fills in the
data. Every screen shown is rebuilt by replaying the saved world in file order (as a resume does); the script first
checks that this rebuild reproduces every saved open_post screen word for word, and stops if one differs.
Numbers in the page text come from the FACTS dict below (template placeholders {{name}}); a missing one stops the build.
"""
import csv, glob, json, os, re, subprocess, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
import analyze_v2 as A  # noqa: E402
import live_world as L  # noqa: E402
import run_v2 as R  # noqa: E402
from v3_big_summary import load  # noqa: E402

OUT, DIRS = sys.argv[1], [os.path.abspath(d) for d in sys.argv[2:]]
PARTS = ["part 1", "part 2"][:len(DIRS)]
X = "examples/experiment/llm_bias/"
MODELS = ["gemma3:12b", "llama3.1:8b", "qwen3:8b"]
SHORT = {"gemma3:12b": "gemma", "llama3.1:8b": "llama", "qwen3:8b": "qwen"}
SAMPLE_USERS = [0, 1, 2]  # every screen of these users is shown word for word; tick 0 is shown for all 100 users
V3_START = "2026-10-20"  # V3 work began (log 14.43)


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True).stdout.strip()


def origin(path):
    """First commit, number of commits, commits since V3 began; group = new / updated for V3 / unchanged since V1-V2."""
    log = git("log", "--follow", "--format=%h %ad", "--date=short", "--", path).splitlines()
    if not log:
        return "made", "Not in git (made on the Mac by the script named above)."
    first_h, first_d = log[-1].split()
    since = [l for l in log if l.split()[1] >= V3_START]
    group = "new" if first_d >= V3_START else "updated" if since else "same"
    return group, (f"First commit {first_h} ({first_d}); {len(log)} commit{'s' * (len(log) != 1)} in all"
                   + (f", {len(since)} since V3 work began ({V3_START})." if since and group != "new" else "."))


# (path, title, what it does) -- group and history come from git
FILES = [
    (X + "run_v2.py", "One turn of one AI: the posting turn or the reading turn",
     "Builds every screen, writes the exact prompt, calls the AI, checks the answer (validate), saves one row per screen. "
     "Holds the prompt templates (SYSTEM, POST_SCREEN, READ_SCREEN, LIVE_READ_SCREEN), the 27-action MENU, FORMAT and "
     "FORMAT_TWO, and the --v3 switch (run): V1 prompts + posting line 2c; reading = live world + refresh loop + two-action "
     "example; JSON on, thinking off. Part 2 adds --menu-file."),
    (X + "live_world.py", "The live world: actions really happen",
     "One world per reading cell, wiped after. Time runs in ticks; what a user does in tick t is seen by others from t+1. "
     "Post screens show the comments with IDs and a new-messages notice. Look-up actions open a follow-up screen with the "
     "real result (at most 4 per post). Private messages work from a profile or the inbox. OASIS's rules (no second upvote, "
     "group membership...) decide whether an action works; a failed action is saved with the reason."),
    (X + "v2_night.py", "The runner: one round in the right order",
     "Loads one AI at a time, runs its posting turn, then the baseline (it reads its own AI's posts), then the cross cells, "
     "then the noise floor. Skips finished work, so a restart resumes. V3 big sim: slices off (each cross cell in one go)."),
    (X + "v3_big.sh", "One part of the big sim",
     "ARM=1: part 1 = V3 full round into data/llm_bias/v3/, ends 'ARM 1 DONE'. ARM=2: copies part 1's post files into "
     "data/llm_bias/v3_flipped/, ranks the menu from part 1's data (rank_menu.py) and reads the same posts again, reading "
     "only, no noise floor; ends 'ARM 2 DONE'. A lock stops a second copy."),
    (X + "v3_start.sh", "Starts a part safely: preflight first",
     "Runs the real-AI preflight with the part's exact settings; only on ALL CLEAR adds the watchdog to cron and starts "
     "v3_big.sh. Written after the first part-1 start broke (log 14.50: the big sim started while the preflight was still "
     "switching servers)."),
    (X + "v3_watchdog.sh", "Restarts a part if it dies",
     "cron runs it every 10 minutes: if v3_big.sh is not running and the log has no DONE line, it restarts it (resume is "
     "safe). Gives up after 3 restarts. Part 1 and part 2 never needed it."),
    (X + "llm.py", "The one door to the AIs",
     "Every AI call goes through chat_json(): system + user message, JSON mode, the same sampling for every AI (temperature "
     "0.7, top_k 40, top_p 0.9), a seed fixed by round, poster AI, user and post; up to 2 retries with a new seed when the "
     "answer breaks a rule."),
    (X + "llamacpp_servers.sh", "Starts and stops the AI servers on the Spark",
     "One llama.cpp server per AI, 8 answers at a time, 8,192 tokens each. 'only' keeps just the AI in use loaded."),
    (X + "rank_menu.py", "Part 2's menu, made from part 1's data",
     "Counts every action the 3 AIs picked on post screens in part 1's 9 cells, then writes the same V1 menu lines word for "
     "word in a new order: least-used section first, least-used line first inside each section."),
    (X + "preflight_v2.py", "110 safety checks before a part runs alone",
     "Servers, switching AIs, the prompts, a 10-user mini-round through the real runner with the part's exact settings, "
     "kill-and-resume, clean finish."),
    (X + "smoke_test.py", "Fast end-to-end test with fake AIs",
     "Runs the real code against fake_engine.py (no model) in about a minute: both big-sim parts, the live world, resume, "
     "the menu order. Run after any code change."),
    (X + "fake_engine.py", "A pretend AI server for tests", "Answers like an AI would and logs every request's settings."),
    (X + "build_population_v2.py", "Makes the 100 users from US data",
     "Census 2024 (age, sex, state), Census 2020 (city or countryside), CPS 2024 (schooling), BLS (work), Pew 2025 (social "
     "media use). Big Five personality; topic stances balanced: 20 users per stance per topic."),
    (X + "personas_v2.json", "The 100 users (frozen)",
     "Made once by build_population_v2.py, then pinned: run_v2.py refuses to run if the file's fingerprint changes (SHA "
     "ed110626, the same in V1, V2 and V3). Each user's persona text is pasted word for word into every prompt."),
    (X + "v3_clean.py", "Cleans, normalizes and aggregates a part (run first, always)",
     "Keeps noise-floor reruns, unreadable answers and follow-up screens apart, merges refresh returns, marks every action "
     "done or failed with why, then counts per 100 posts read, world by world and tick by tick. Checks its numbers against "
     "the published ones before writing."),
    (X + "make_v3_workbook.py", "The Excel workbook", "Built from the cleaned data; takes part 2 when it exists."),
    (X + "make_inside_v3.py", "This page", "Fills inside_v3_template.html with the code, the rebuilt screens and the data."),
    (X + "v3_big_summary.py", "Part summary + the published numbers",
     "analyze_v2's tables on one part (one row per post read) and the gate: post counts and screens per cell must match "
     "the Spark log."),
    (X + "v3_by_tick.py", "Tick groups and the own-AI bias by tick", "Engagement, upvotes and comments on screen by tick, "
     "next to V1, with the bias number and its 95% range."),
    (X + "check_gemma_own.py", "Why gemma upvotes gemma's posts (log 14.57)",
     "The lean inside topics, lengths, stances and scroll position, and by the tone of the comments on screen."),
    (X + "v3_compare_parts.py", "Part 1 vs part 2", "Ready for when part 2 finishes: each reader's actions, engagement "
     "and the own-AI bias, part 1 next to part 2."),
    (X + "analyze_v2.py", "The shared measures", "Total engagement, the double difference and the bootstrap ranges used "
     "by every analysis script."),
    ("oasis/social_agent/agent_action.py", "OASIS: the user actions",
     "Our 27-action menu is OASIS's action list minus sign_up, purchase_product and interview. live_world.py copies the "
     "rules of OASIS's platform (it runs without OASIS installed, as the Spark has no OASIS)."),
    ("oasis/social_platform/config/user.py", "OASIS: the user's system prompt",
     "to_reddit_system_message() is where the '# OBJECTIVE / # SELF-DESCRIPTION / # RESPONSE METHOD' prompt comes from."),
]


def lang(p):
    return {"py": "python", "sh": "bash", "json": "json", "md": "markdown", "txt": "plaintext", "log": "plaintext"}.get(
        p.rsplit(".", 1)[-1], "plaintext")


files = []
for path, title, what in FILES:
    src = open(os.path.join(REPO, path)).read()
    if path.endswith("personas_v2.json"):
        src = json.dumps(json.load(open(os.path.join(REPO, path)))[:3], indent=1) + "\n\n... 97 more users, same shape"
    group, hist = origin(path)
    if path.startswith("oasis/"):
        group, hist = "oasis", "From camel-ai/oasis, unchanged. " + hist
    files.append({"path": path, "group": group, "title": title, "what": what, "origin": hist, "lang": lang(path),
                  "src": src, "lines": src.count("\n") + 1})

# real output files, shown in the same viewer
P1 = DIRS[0]
rel = lambda p: os.path.relpath(p, REPO)  # noqa: E731
menu2 = subprocess.run([sys.executable, os.path.join(HERE, "rank_menu.py"), os.path.join(P1, "r101"), "/dev/stdout"],
                       capture_output=True, text=True).stdout
row_post = next(json.loads(l) for l in open(os.path.join(P1, "r101", "reading_gemma3-12b__llama3.1-8b.jsonl"))
                if '"screen": "post"' in l and '"tick": 3,' in l and '"user_id": 5,' in l)
row_follow = next(json.loads(l) for l in open(os.path.join(P1, "r101", "reading_gemma3-12b__llama3.1-8b.jsonl"))
                  if '"screen": "search_user"' in l and '"send_message", "ok": true' in l)
for path, title, what, src, lg in [
    (rel(os.path.join(P1, "r101", "reading_qwen3-8b__gemma3-12b.manifest.json")), "A cell's manifest (real, part 1)",
     "Written when a cell finishes: what ran, the fingerprints of the users, posts and prompts, the engine and sampling, "
     "how long, how many answers were unreadable.", None, "json"),
    (rel(os.path.join(P1, "night.log")), "Part 1's runner log (real)", "Every step with its start, end and speed.", None, "plaintext"),
    ("part 2 menu (rank_menu.py on part 1's data)", "The menu part 2 shows (made again here from the same data)",
     "rank_menu.py writes it from part 1's data; the Spark made its copy (v3_flipped/r101/menu.txt) the same way on 10-27. "
     "Compare with run_v2.py's MENU: the same lines, a new order.", menu2, "plaintext"),
    ("one post screen row (real: llama plays user 5, tick 3, gemma's posts)", "What one saved row holds",
     "One row per screen in reading_<posts by>__<reader>.jsonl. 'raw' = the AI's answer word for word; 'executed' = what "
     "happened to each action; 'ctx.post' = the post's ID in this world.", json.dumps(row_post, indent=1), "json"),
    ("one follow-up screen row (real: a profile search that ended in a DM)", "A follow-up screen",
     "Follow-up rows also save 'text': the exact screen the AI was shown.", json.dumps(row_follow, indent=1), "json"),
    (rel(os.path.join(P1, "clean", "cleaning.md")), "The cleaning report (part 1)", "Written by v3_clean.py.", None, "markdown"),
]:
    src = src if src is not None else open(os.path.join(REPO, path)).read()
    files.append({"path": path, "group": "data", "title": title, "what": what, "origin": "Real output of the V3 big sim, part 1.",
                  "lang": lg, "src": src, "lines": src.count("\n") + 1})
refs = {}
for key, path, pat in [("menu", "run_v2.py", r"^MENU = "), ("format", "run_v2.py", r"^FORMAT = "),
                       ("format_two", "run_v2.py", r"^FORMAT_TWO = "), ("system", "run_v2.py", r"^SYSTEM = "),
                       ("read_screen", "run_v2.py", r"^READ_SCREEN = "), ("live_read", "run_v2.py", r"^LIVE_READ_SCREEN"),
                       ("post_screen", "run_v2.py", r"^POST_SCREEN = "), ("post_lines", "run_v2.py", r"^POST_LINES = "),
                       ("v3_switch", "run_v2.py", r"if a\.v3:"), ("validate", "run_v2.py", r"^def validate"),
                       ("world", "live_world.py", r"^class World"), ("run_live", "live_world.py", r"^def run_live"),
                       ("screens", "live_world.py", r"^def screens"), ("live_menu", "live_world.py", r"^def live_menu"),
                       ("post_block", "live_world.py", r"def post_block"), ("chat_json", "llm.py", r"^def chat_json"),
                       ("rank", "rank_menu.py", r"^"), ("big", "v3_big.sh", r"^for r in"), ("start", "v3_start.sh", r"^echo"),
                       ("clean_effort", "v3_clean.py", r"^EFFORT = ")]:
    lines = open(os.path.join(HERE, path)).read().splitlines()
    n = next(i for i, l in enumerate(lines, 1) if re.search(pat, l))
    refs[key] = [X + path, n]

# ---- the screens: replay each world in file order; rebuild post screens for tick 0 (all users) and SAMPLE_USERS ----
R.DATA = P1
people = R.load_personas()[:100]
PEOPLE = [{"id": p["id"], "username": p["username"], "persona": p["persona"], "stances": p["stances"]} for p in people]
live_menu = L.live_menu(R.MENU)
screens, posts_out, checked = {}, {}, Counter()
for m in MODELS:
    for pb in MODELS:
        posts, _ = R.post_set(101, pb, 100)
        posts_out[SHORT[pb]] = [{"key": q["key"], "author_id": q["author_id"], "author": q["author"], "topic": q["topic"],
                                 "title": q["title"], "body": q["body"]} for q in posts]
        w = L.World(people, posts, R.TOPICS)
        keep = []
        for l in open(os.path.join(P1, "r101", f"reading_{R.short(pb)}__{R.short(m)}.jsonl")):
            r = json.loads(l)
            u, t = r["user_id"], r["tick"]
            if r["screen"] in ("post", "open_post"):
                sub, tname, author, title, body, comments = w.post_block(r["ctx"]["post"], u, t)
                notice = w.notice(u, t)
                if r["screen"] == "open_post":
                    text = notice + R.LIVE_READ_SCREEN.format(sub=sub, topic_name=tname, author=author, title=title,
                                                              body=body, comments=comments, menu=live_menu, fmt=R.FORMAT_TWO)
                    assert text == r["text"], f"replay differs from the saved screen: {m} reads {pb}, user {u}, seq {r['seq']}"
                    checked["open_post screens rebuilt word for word"] += 1
            if t == 0 and r["screen"] == "post" or u in SAMPLE_USERS:
                keep.append({"u": u, "seq": r["seq"], "tick": t, "step": r["step"], "screen": r["screen"], "view": r["view"],
                             "post": r["post_key"], "raw": r["raw"], "outcome": r["outcome"], "attempts": r.get("attempts", 1),
                             "errors": r.get("errors") or [], "tokens": [r.get("prompt_tokens"), r.get("eval_tokens")],
                             "secs": r.get("call_latency_s"),
                             "ex": [[a["action"], e["ok"], e.get("error")] for a, e in zip(r["actions"], r["executed"])],
                             **({"notice": notice, "comments": comments} if r["screen"] == "post" else {}),
                             **({"text": r["text"]} if r["screen"] != "post" else {})})
            if r["screen"] == "open_messages":
                w.inbox(u, t, mark=True)
            for a, e in zip(r["actions"], r["executed"]):
                if e["ok"]:
                    w.do(u, t, a, {**r["ctx"], "topic_of": R.topic_of})
        screens[f"{SHORT[m]}|{SHORT[pb]}"] = keep
print("replay check:", dict(checked))

posting = {}
for m in MODELS:
    posting[SHORT[m]] = {r["user_id"]: {"raw": r["raw"], "n": sum(a["action"] == "create_post" for a in r["actions"])}
                         for r in map(json.loads, open(os.path.join(P1, "r101", f"posting_{R.short(m)}.jsonl")))}
post_screen = R.POST_SCREEN.replace("nothing has been posted yet.\n", "nothing has been posted yet.\n" + R.POST_LINES["c"] + "\n")
PROMPTS = {"system": R.SYSTEM, "read": R.LIVE_READ_SCREEN, "live_menu": live_menu, "fmt_two": R.FORMAT_TWO, "fmt": R.FORMAT,
           "post_screen": post_screen.format(subs="\n".join(f"- {s} ({n})" for s, n in R.TOPICS.values()), menu=R.MENU, fmt=R.FORMAT),
           "v1_post_screen": R.POST_SCREEN.format(subs="\n".join(f"- {s} ({n})" for s, n in R.TOPICS.values()), menu=R.MENU, fmt=R.FORMAT),
           "v1_read": R.READ_SCREEN, "menu2": menu2.strip(), "topics": {k: list(v) for k, v in R.TOPICS.items()}}

# ---- the cleaned data, per part ----
def rows(d, name):
    return list(csv.DictReader(open(os.path.join(d, "clean", name))))


def num(v):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


parts = {}
for p, d in zip(PARTS, DIRS):
    parts[p] = {n: [{k: num(v) for k, v in r.items()} for r in rows(d, n + ".csv")]
                for n in ("by_cell_tick", "by_cell_action", "action_effort", "effort_tiers")}
    parts[p]["cleaning"] = open(os.path.join(d, "clean", "cleaning.md")).read()

# V1 round 101, the same measures (no live world: every screen is one post read, nothing else)
v1rows, _ = load(os.path.join(REPO, "data/llm_bias/v1_v2_spark"), "r101")
v1 = defaultdict(list)
v1posts = Counter()
for r in v1rows:
    if r["turn"] == "post":
        v1posts[SHORT[r["model"]]] += sum(a["action"] == "create_post" for a in r["actions"])
    elif r["outcome"] == "chose" and not r["draw"]:
        v1[(SHORT[r["model"]], SHORT[r["posts_by"]])].append(r)
V1 = {f"{m}|{pb}": {"posts read": len(rs), "engagement per 100": round(100 * sum(map(A.n_engage, rs)) / len(rs), 1),
                    "upvoted %": round(100 * sum(A.has(r, "like_post") for r in rs) / len(rs), 1),
                    "commented %": round(100 * sum(A.has(r, "create_comment") for r in rs) / len(rs), 1),
                    "did nothing %": round(100 * sum(not A.did_anything(r) for r in rs) / len(rs), 1)}
      for (m, pb), rs in v1.items()}

# the data files of each part
inventory = []
for p, d in zip(PARTS, DIRS):
    for f in sorted(glob.glob(os.path.join(d, "r101", "*")) + glob.glob(os.path.join(d, "clean", "*")) + glob.glob(os.path.join(d, "*.*"))):
        if os.path.isdir(f):
            continue
        b = os.path.basename(f)
        what = ("the AI's answers in the posting turn, one row per user" if b.startswith("posting_") and b.endswith(".jsonl") else
                "noise floor: the first 4 posts of each user read again with fresh randomness" if "_d1" in b and b.endswith(".jsonl") else
                "one reading cell (world): one row per screen, post screens and follow-up screens" if b.startswith("reading_") and b.endswith(".jsonl") else
                "what ran, fingerprints, engine, timing" if b.endswith(".manifest.json") else
                "the step's console log" if b.endswith(".log") else
                {"reads.csv": "clean: one row per post read", "followups.csv": "clean: one row per follow-up screen",
                 "posts.csv": "clean: one row per post written", "actions.csv": "clean: every chosen action on every screen",
                 "action_effort.csv": "clean: per AI and action, how hard and how often",
                 "effort_tiers.csv": "clean: per AI, actions by how hard they are",
                 "by_cell_action.csv": "clean: every action per world", "by_cell_tick.csv": "clean: every world, every tick",
                 "worlds.md": "clean: the same as tables", "cleaning.md": "clean: what was removed and why",
                 "night.log": "the runner's log", "summary.md": "v3_big_summary.py's tables",
                 "check_gemma_own.md": "check_gemma_own.py's output (log 14.57)", "menu.txt": "part 2's ranked menu"}.get(b, ""))
        n = sum(1 for _ in open(f, "rb")) if b.endswith((".jsonl", ".csv", ".log", ".md", ".txt")) else None
        inventory.append({"part": p, "path": rel(f), "bytes": os.path.getsize(f), "lines": n, "what": what})

# runner steps from the night log
steps = []
for p, d in zip(PARTS, DIRS):
    for l in open(os.path.join(d, "night.log")):
        mm = re.match(r"(\S+ \S+) end r101 (.+?) rc=(\d+): (\d+) screens in ([\d.]+) min \(([\d.]+) s/screen\)", l)
        if mm:
            steps.append({"part": p, "end": mm[1], "step": mm[2], "rc": int(mm[3]), "screens": int(mm[4]),
                          "min": float(mm[5]), "s": float(mm[6])})

# ---- numbers used in the page text ----
tick = {(r["reader"], r["posts_by"], str(r["tick"])): r for r in parts["part 1"]["by_cell_tick"]}
tiers = {(r["reader"], r["tier"]): r for r in parts["part 1"]["effort_tiers"]}
eff = {(r["reader"], r["action"]): r for r in parts["part 1"]["action_effort"]}
allw = {k[:2]: v for k, v in tick.items() if k[2] == "all"}
act_rows = rows(P1, "actions.csv")
FACTS = {
    "posts_read": f"{sum(v['posts read'] for v in allw.values()):,}",
    "followups": f"{sum(v['follow-up screens'] for v in allw.values()):,}",
    "p1_hours": f"{(sum(s['min'] for s in steps if s['part'] == 'part 1')) / 60:.0f}",
    "v1_posts_gemma": v1posts["gemma"], "v1_posts_llama": v1posts["llama"], "v1_posts_qwen": v1posts["qwen"],
    "v3_posts_gemma": len(posts_out["gemma"]), "v3_posts_llama": len(posts_out["llama"]), "v3_posts_qwen": len(posts_out["qwen"]),
    "dms_llama": f"{eff[('llama', 'send_message')]['done']:,}", "dms_gemma": eff.get(("gemma", "send_message"), {"done": 0})["done"],
    "dms_qwen": eff.get(("qwen", "send_message"), {"done": 0})["done"],
    "returns": re.search(r"refresh returns merged into the first view \| ([\d,]+)", parts["part 1"]["cleaning"])[1],
    "replay_checked": f"{checked['open_post screens rebuilt word for word']:,}",
}
for m in ("gemma", "llama", "qwen"):
    FACTS[f"fu_{m}"] = f"{sum(allw[(m, pb)]['follow-up screens'] for pb in ('gemma', 'llama', 'qwen')):,}"
    for t in (1, 2, 3, 4, 5):
        FACTS[f"tier{t}_{m}"] = tiers[(m, t)]["% of all actions chosen"]
    FACTS[f"fail_{m}"] = f"{100 * sum(r['chosen'] - r['done'] for r in parts['part 1']['action_effort'] if r['reader'] == m and r['action'] != 'do_nothing') / sum(r['chosen'] for r in parts['part 1']['action_effort'] if r['reader'] == m and r['action'] != 'do_nothing'):.1f}"
    acts = [r for r in act_rows if r["reader"] == m and r["action"] != "do_nothing"]  # exact, from every action
    FACTS[f"n_{m}"] = f"{len(acts):,}"
    FACTS[f"off_post_{m}"] = f"{sum(r['screen'] != 'post' for r in acts):,}"
    FACTS[f"post_screen_{m}"] = f"{100 * sum(r['screen'] == 'post' for r in acts) / len(acts):.1f}"
    lp, cc = eff.get((m, "like_post")), eff.get((m, "create_comment"))
    FACTS[f"tok_like_{m}"] = lp["median answer tokens (only this action)"] if lp else "-"
    FACTS[f"tok_comment_{m}"] = cc["median answer tokens (only this action)"] if cc else "-"
    FACTS[f"sec_like_{m}"] = lp["median answer seconds (only this action)"] if lp else "-"
    FACTS[f"sec_comment_{m}"] = cc["median answer seconds (only this action)"] if cc else "-"
FACTS["v1_posters_gemma"] = sum(1 for r in v1rows if r["turn"] == "post" and r["model"] == "gemma3:12b" and any(a["action"] == "create_post" for a in r["actions"]))

DATA = {"files": files, "refs": refs, "people": PEOPLE, "posts": posts_out, "screens": screens, "posting": posting,
        "prompts": PROMPTS, "parts": parts, "v1": V1, "inventory": inventory, "steps": steps, "sample_users": SAMPLE_USERS,
        "status": "Part 2 (the same posts, the menu ranked from part 1's data) is running on the Spark; at Thu 10-29 10:11 "
                  "7 of its 9 cells were done. When it finishes, this page is rebuilt with part 2 next to part 1."
                  if len(DIRS) == 1 else "Both parts are done."}

tpl = open(os.path.join(HERE, "inside_v3_template.html")).read()
css = re.search(r"<style>(.*?)</style>", open(os.path.join(HERE, "inside_v2_template.html")).read(), re.S)[1]
tpl = tpl.replace("/*__CSS__*/", css)
missing = sorted(set(re.findall(r"\{\{(\w+)\}\}", tpl)) - set(FACTS))
assert not missing, f"page text uses numbers the script does not compute: {missing}"
tpl = re.sub(r"\{\{(\w+)\}\}", lambda mm: str(FACTS[mm[1]]), tpl)
blob = json.dumps(DATA, separators=(",", ":")).replace("</", "<\\/")
html = tpl.replace("/*__DATA__*/null", blob)
open(OUT, "w").write(html)
print(f"wrote {OUT}: {len(html) / 1e6:.2f} MB; {len(files)} files, {sum(len(v) for v in screens.values()):,} screens, "
      f"{len(inventory)} data files; facts: {json.dumps(FACTS)}")
