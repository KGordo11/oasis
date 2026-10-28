"""Speed test results (speed_suite.py, log 14.59): how much faster, and did the AIs' behaviour change? Stdlib only.

    python3 examples/experiment/llm_bias/speed_summary.py data/llm_bias/speed

1. Speed: seconds per post read (follow-up screens included) per AI, and how many times faster than ref.
2. Behaviour, per AI: total engagement per 100 posts read, % upvoted, % commented, % did nothing, answer length; and the
   change vs ref, screen by screen (the same user and post in both runs), with a 95% range from resampling users.
   ref_redo (ref again with fresh randomness) shows how much things move by chance alone. A change is a speed-only
   change when it moves the AIs no more than ref_redo does. * = 95% range excludes 0 (with ~80 comparisons, a few *
   happen by chance: compare with ref_redo's row).
"""
import json, os, random, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze_v2 as A  # noqa: E402
from v3_big_summary import load  # noqa: E402

D = sys.argv[1]
MODELS = ["qwen3:8b", "llama3.1:8b", "gemma3:12b"]
ORDER = ["ref", "ref_redo", "slots16", "ub2048", "cacheram0", "swafull", "kvunified", "cachereuse", "spec_ngram",
         "spec_draft", "order_b", "newbuild", "worlds3"]
tests = [t for t in ORDER if os.path.exists(os.path.join(D, t, "timing.jsonl"))]
if "ref" not in tests:
    sys.exit(f"no ref test in {D}")
timing = {t: {r["model"]: r for r in map(json.loads, open(os.path.join(D, t, "timing.jsonl")))} for t in tests}  # last record wins
MEASURES = [("total engagement", A.n_engage, 100), ("upvoted %", lambda r: A.has(r, "like_post"), 100),
            ("commented %", lambda r: A.has(r, "create_comment"), 100), ("did nothing %", lambda r: not A.did_anything(r), 100)]


def reads(t):
    rows, _ = load(os.path.join(D, t))
    return {m: {(r["user_id"], r["post_key"]): r for r in rows if r["turn"] == "read" and r["model"] == m and r["outcome"] == "chose"}
            for m in MODELS}


def paired(a, b, f, n=1000):
    """Mean of f(b) - f(a) over screens in both runs; 95% range from resampling users."""
    keys = sorted(set(a) & set(b))
    by = defaultdict(list)
    for k in keys:
        by[k[0]].append(f(b[k]) - f(a[k]))
    users = sorted(by)
    if not users:
        return None, None, None
    mean = lambda us: sum(sum(by[u]) for u in us) / sum(len(by[u]) for u in us)  # noqa: E731
    rng = random.Random(7)
    est = sorted(mean(rng.choices(users, k=len(users))) for _ in range(n))
    return mean(users), est[int(0.025 * n)], est[int(0.975 * n) - 1]


print(f"# Speed tests ({D})\n")
print("## 1. Speed: seconds per post read (follow-up screens included); x = times faster than ref\n")
print("| test | what changes | " + " | ".join(MODELS) + " |\n|---|---|" + "---|" * len(MODELS))
ref = timing["ref"]
for t in tests:
    cells = []
    for m in MODELS:
        r = timing[t].get(m)
        if not r or r["status"] != "OK":
            cells.append(f"{r['status']}: {r.get('why', '')[:60]}" if r else "-")
            continue
        s = r["wall_s"] / r["posts_read"]
        x = (ref[m]["wall_s"] / ref[m]["posts_read"]) / s if ref.get(m, {}).get("status") == "OK" else None
        cells.append(f"{s:.2f}" + (f" ({x:.2f}x)" if x else ""))
    what = next(iter(timing[t].values()))["what"]
    print(f"| {t} | {what} | " + " | ".join(cells) + " |")
w = timing.get("worlds3", {})
if w and all(w.get(m, {}).get("status") == "OK" and ref.get(m, {}).get("status") == "OK" for m in MODELS):
    one_by_one = sum(ref[m]["wall_s"] for m in MODELS)
    together = max(r["together_wall_s"] for r in w.values())
    print(f"\nworlds3: all three AIs together {together / 60:.1f} min vs one after another (ref) {one_by_one / 60:.1f} min "
          f"= {one_by_one / together:.2f}x")

base = reads("ref")
print("\n## 2. Behaviour per AI: level, then the change vs ref screen by screen (95% range from resampling users)\n")
for m in MODELS:
    print(f"**{m}**\n\n| test | posts read | " + " | ".join(n for n, _, _ in MEASURES) + " | answer tokens |\n|---|---|" + "---|" * (len(MEASURES) + 1))
    for t in tests:
        rs = base[m] if t == "ref" else reads(t)[m]
        if not rs:
            print(f"| {t} | 0 |" + " - |" * (len(MEASURES) + 1))
            continue
        cells = []
        for name, f, k in MEASURES:
            lvl = k * sum(f(r) for r in rs.values()) / len(rs)
            if t == "ref":
                cells.append(f"{lvl:.1f}")
                continue
            d, lo, hi = paired(base[m], rs, f)
            star = "*" if lo is not None and (lo > 0 or hi < 0) else ""
            cells.append(f"{lvl:.1f} ({k * d:+.1f}, {k * lo:+.1f} to {k * hi:+.1f}){star}" if d is not None else f"{lvl:.1f}")
        tok = sum(r.get("eval_tokens") or 0 for r in rs.values()) / len(rs)
        print(f"| {t} | {len(rs)} | " + " | ".join(cells) + f" | {tok:.0f} |")
    print()
