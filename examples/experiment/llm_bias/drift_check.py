"""Drift check (LD-18, 2026-10-01): replay a random sample of an earlier world's votes with the SAME seeds and
settings, and compare with what was recorded. Same answers + same like rate => the AI has not drifted over the night.
    python drift_check.py two_r01_gemma3 200
"""
import json, os, random, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import authors, llm, personas, scroll  # noqa: E402

lab, n = sys.argv[1], int(sys.argv[2])
W = os.path.join(authors.DATA, "worlds", lab)
dec = [json.loads(l) for l in open(os.path.join(W, "decisions.jsonl"))]
cfg = json.load(open(os.path.join(W, "manifest.json")))["config"]
users = {p["id"]: p for p in personas.core100()}
bank = authors.load_bank(cfg["seed"])
sample = random.Random(0).sample(dec, n)

def replay(d):
    p, post = users[d["agent_id"]], bank[d["post_key"]]
    obj, meta = llm.chat_json(d["judge"], scroll.SYSTEM_TEMPLATE.format(persona=p["persona"]), scroll.render_user(d["topic"], post),
                              seed=llm.stable_seed(cfg["seed"], p["id"], post["key"], "scroll"), temperature=cfg["temperature"],
                              num_predict=80, validate=scroll.validate, retries=2)
    return obj["action"] if obj else None
new = list(ThreadPoolExecutor(2).map(replay, sample))
old = [d["action"] for d in sample]
same = sum(a == b for a, b in zip(old, new)) / n
out = {"world": lab, "n": n, "same_answer_%": round(100 * same, 1), "recorded": dict(Counter(old)), "replayed": dict(Counter(new))}
print(out)
with open(os.path.join(authors.DATA, "two_ai", "drift_check.jsonl"), "a") as f:
    f.write(json.dumps(out) + "\n")
