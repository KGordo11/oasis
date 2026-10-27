"""Speed test: does putting the shared text FIRST make a screen faster? (Gordon 10-27, log 14.56). Not a sim: answers are
not used, only the server's timings. Stdlib only.

    python3 examples/experiment/llm_bias/prompt_order_bench.py A|B URL MODEL [users] [ticks] [parallel] [max_tokens]

max_tokens 1 = prompt reading only (the order also changes how long the answers are, log 14.56).

Same content, two orders (the V3 live reading screen, part 1's qwen posts, real personas):
  A (now)          system = objective + persona;              user = post + comments + MENU + FORMAT
  B (shared first) system = objective + MENU + FORMAT + persona; user = post + comments
Every screen in B starts with the same ~500 tokens, so llama.cpp can keep them from the last screen (prompt cache) and
only read the persona + post. Runs like the live world: tick by tick, every user's t-th post, `parallel` at a time.
Restart the server between A and B so both start cold. Prints prompt tokens read vs reused and seconds per screen.
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_v2 as R  # noqa: E402
import live_world as LW  # noqa: E402

LAYOUT, URL, MODEL = sys.argv[1], sys.argv[2].rstrip("/"), sys.argv[3]
USERS, TICKS, PAR, MAXTOK = (int(x) for x in (sys.argv[4:] + ["24", "5", "8", "800"][len(sys.argv) - 4:])[:4])
R.DATA = os.path.join(HERE, "..", "..", "..", "data", "llm_bias", "v3")
people = R.load_personas()[:USERS]
posts, _ = R.post_set(101, "qwen3:8b", 100)
world = LW.World(R.load_personas(), [], R.TOPICS)
for k, q in enumerate(posts):
    world.posts[k] = {**q, "tick": -1}
menu, fmt = LW.live_menu(R.MENU), R.FORMAT_TWO
SHARED = f"WHAT YOU CAN DO\n{menu}\n\n{fmt}"


def messages(p, pid):
    sub, tname, author, title, body, comments = world.post_block(pid, p["id"], 0)
    screen = R.LIVE_READ_SCREEN.format(sub=sub, topic_name=tname, author=author, title=title, body=body,
                                       comments=comments, menu=menu, fmt=fmt)
    system = R.system_prompt(MODEL, 101, p["persona"])
    if LAYOUT == "B":
        screen = screen.replace("\n\n" + SHARED, "")
        assert SHARED not in screen
        system = system.replace("# SELF-DESCRIPTION", SHARED + "\n\n# SELF-DESCRIPTION")
    return [{"role": "system", "content": system}, {"role": "user", "content": screen}]


def ask(job):
    p, pid = job
    body = {"model": MODEL, "messages": messages(p, pid), "temperature": 0.7, "top_k": 40, "top_p": 0.9, "min_p": 0,
            "seed": 1000 * p["id"] + pid, "max_tokens": MAXTOK} | ({"response_format": {"type": "json_object"}} if MAXTOK > 1 else {})
    t = time.time()
    req = urllib.request.Request(URL + "/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    out = json.load(urllib.request.urlopen(req, timeout=600))
    return {**out.get("timings", {}), "wall": time.time() - t}


# each user's own scroll (skip their own post), like the sim; tick t = every user's t-th post
scroll = {p["id"]: [k for k, q in enumerate(posts) if q["author_id"] != p["id"]][p["id"] % 7::7] for p in people}
res, t0 = [], time.time()
with ThreadPoolExecutor(PAR) as pool:
    for t in range(TICKS):
        res += list(pool.map(ask, [(p, scroll[p["id"]][t]) for p in people]))
wall = time.time() - t0
s = lambda k: sum(r.get(k, 0) for r in res)
n = len(res)
print(f"layout {LAYOUT} {MODEL}: {n} screens, {USERS} users x {TICKS} ticks, {PAR} at a time, max_tokens {MAXTOK}")
print(f"  prompt tokens per screen: read {s('prompt_n') / n:.0f}, reused from cache {s('cache_n') / n:.0f}")
print(f"  time reading prompts {s('prompt_ms') / 1000:.1f} s, writing answers {s('predicted_ms') / 1000:.1f} s "
      f"({s('predicted_n') / n:.0f} tokens per answer)")
print(f"  WALL {wall:.1f} s = {wall / n:.2f} s per screen")
