"""Where the v2 run is: screens done / left per cell for each round, and an estimated finish time.

    python3 examples/experiment/llm_bias/progress_v2.py            # rounds 101 102 103
    python3 examples/experiment/llm_bias/progress_v2.py 102

Read-only (stdlib only, safe while the run is going). Same counting as v2_night.py: a cell is done when every user
has read every post not their own; the noise floor is 4 posts per user. A post set that is not written yet is
assumed to be the size of the newest written one. Speed = the latest measured s/screen per reader in night.log
(unshared speeds if none), so the ETA assumes the GPU stays as busy as it was on the last step.
"""
import json, os, re, sys, time
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(HERE, "..", "..", "..", "data", "llm_bias", "v2")
MODELS = ["qwen3:8b", "llama3.1:8b", "gemma3:12b"]
SPS = {"qwen3:8b": 0.45, "llama3.1:8b": 0.52, "gemma3:12b": 0.95}  # unshared, measured 2026-10-06/07
NOISE, USERS, SWITCH_S = 4, 100, 60  # each model switch (server load) ~1 min
f = lambda m: m.replace(":", "-")

log = os.path.join(V2, "night.log")
if os.path.exists(log):
    for line in open(log):
        m = re.search(r"end r\d+ (?:CROSS|BASELINE|noise floor)? ?(\S+) .*\(([\d.]+) s/screen\)", line)
        if m and m.group(1) in SPS:
            SPS[m.group(1)] = float(m.group(2))
# the step running now: its live speed beats the last finished step's (the GPU may have become shared since)
live = sorted((p for p in (os.path.join("/tmp", n) for n in os.listdir("/tmp")) if re.match(r".*/v2_reading_\S+__\S+\.log$", p)),
              key=os.path.getmtime)[-1:]
for p in live:
    tail = open(p, errors="ignore").read()[-2000:]
    m = re.findall(r"\(([\d.]+) s each", tail)
    rd = next((x for x in SPS if f(x) == re.match(r".*__(.+?)(_d1)?(_a\d+)?\.log$", p).group(1)), None)
    if m and rd and time.time() - os.path.getmtime(p) < 600:
        SPS[rd] = float(m[-1])
stop = None
wd = os.path.expanduser("~/llm_bias/watchdog.sh")
if os.path.exists(wd):
    m = re.search(r'^STOP="([^"]+)"', open(wd).read(), re.M)
    stop = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M") if m else None


def lines(p):
    return sum(1 for _ in open(p)) if os.path.exists(p) else 0


def own_posts(r, m):
    p = os.path.join(V2, f"r{r:03d}", f"posting_{f(m)}.jsonl")
    if not os.path.exists(os.path.join(V2, f"r{r:03d}", f"posting_{f(m)}.manifest.json")):
        return None
    own = {}
    for l in open(p):
        d = json.loads(l)
        own[d["user_id"]] = sum(x["action"] == "create_post" for x in d["actions"])
    return own


def round_left(r, guess):
    """-> (rows, seconds left, switches). guess = post-set sizes to assume for sets not written yet."""
    rows, secs, switches = [], 0.0, 0
    sets = {}
    for m in MODELS:
        own = own_posts(r, m)
        sets[m] = own if own is not None else {u: (1 if u < guess.get(m, 0) else 0) for u in range(USERS)}
        if own is None:
            secs += 120; switches += 1
            rows.append((f"post   {m}", 0, USERS))
    for reader in MODELS:
        did_any = False
        for pb in MODELS:
            own = sets[pb]; n = sum(own.values())
            need = sum(n - own.get(u, 0) for u in range(USERS))
            done = lines(os.path.join(V2, f"r{r:03d}", f"reading_{f(pb)}__{f(reader)}.jsonl"))
            rows.append((f"{'BASE ' if pb == reader else 'cross'}  {reader:<12} reads {pb}", min(done, need), need))
            secs += max(0, need - done) * SPS[reader]; did_any |= done < need
        own = sets[reader]; n = sum(own.values())
        need = sum(min(NOISE, n - own.get(u, 0)) for u in range(USERS))
        done = lines(os.path.join(V2, f"r{r:03d}", f"reading_{f(reader)}__{f(reader)}_d1.jsonl"))
        rows.append((f"noise  {reader}", min(done, need), need))
        secs += max(0, need - done) * SPS[reader]; did_any |= done < need
        switches += did_any
    return rows, secs + switches * SWITCH_S, sets


rounds = [int(x) for x in sys.argv[1:]] or [101, 102, 103]
now, t, guess = datetime.now(), 0.0, {m: 100 for m in MODELS}
print(f"{now:%a %H:%M}   speed used (s/screen): " + ", ".join(f"{m} {s:.2f}" for m, s in SPS.items()))
for r in rounds:
    rows, secs, sets = round_left(r, guess)
    guess = {m: sum(v.values()) for m, v in sets.items()}
    done, need = sum(d for _, d, _ in rows), sum(n for _, _, n in rows)
    print(f"\n== round {r}: {done:,} / {need:,} screens ({100 * done / max(need, 1):.0f}%)   post sets "
          + ", ".join(f"{m.split(':')[0]} {sum(v.values())}" for m, v in sets.items())
          + ("" if all(own_posts(r, m) is not None for m in MODELS) else "  (unwritten sets = guessed)"))
    for name, d, n in rows:
        mark = "done" if d >= n else f"{n - d:,} left"
        print(f"   {name:<38} {d:>6,} / {n:<6,} {mark}")
    t += secs
    eta = now + timedelta(seconds=t)
    late = stop and eta > stop
    print(f"   -> {secs / 3600:.1f} h left in this round; lands ~{eta:%a %H:%M}"
          + (f"   (AFTER the {stop:%a %H:%M} stop: the runner skips what won't fit)" if late else ""))
