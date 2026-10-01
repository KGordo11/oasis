"""Speed test to pick the two fastest AIs (Gordon, 2026-09-30). Not a simulation.

Per model: 40 votes (users 0-9 x 4 posts from post set 40, the real scroll prompt, 4 at a time like run_world)
and 2 natural posts (the real post prompt). Records seconds per vote, seconds per post, and how many answers
were readable. Results: data/llm_bias/speed_pick.json
    python speed_pick.py llama3.2:1b gemma4:e2b ...
"""
import json, os, sys, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import authors, llm, personas, scroll  # noqa: E402
from topics import TOPICS  # noqa: E402

users = personas.core100()[:10]
posts = [r for r in authors.load_bank(40).values() if r.get("ok") and r["topic"] == "personal_finance"][:4]
out = {}
for m in sys.argv[1:]:
    llm.warm(m)
    jobs = [(u, p) for u in users for p in posts]

    def vote(job):
        u, p = job
        return llm.chat_json(m, scroll.SYSTEM_TEMPLATE.format(persona=u["persona"]), scroll.render_user(p["topic"], p),
                             seed=llm.stable_seed(u["id"], p["key"], "speed"), temperature=0.7, num_predict=80,
                             validate=scroll.validate, retries=2)
    t0 = time.time()
    res = list(ThreadPoolExecutor(4).map(vote, jobs))
    s_vote = (time.time() - t0) / len(jobs)
    acts = Counter(o["action"] if o else "BROKEN" for o, _ in res)
    t0, ok, words = time.time(), 0, []
    for r in range(2):
        b = authors.slot_brief(40, r, "cooking")
        o, _ = llm.chat_json(m, authors.NATURAL_SYSTEM, authors.NATURAL_USER.format(
            sub=TOPICS["cooking"]["sub"], topic_name=TOPICS["cooking"]["name"], **b), seed=r, temperature=0.8,
            num_predict=2000, validate=authors.validate_natural, retries=4)
        ok += o is not None
        words += [len(o["body"].split())] if o else []
    s_post = (time.time() - t0) / 2
    out[m] = {"s_per_vote": round(s_vote, 3), "votes": dict(acts), "s_per_post": round(s_post, 1),
              "posts_ok": f"{ok}/2", "post_words": words}
    print(m, out[m], flush=True)
    llm._post("/api/generate", {"model": m, "keep_alive": 0}, 60)  # unload so models don't compete for memory
json.dump(out, open(os.path.join(authors.DATA, "speed_pick.json"), "w"), indent=1)
