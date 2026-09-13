"""Score a local model on the thing that actually decides whether it is usable.

WHY THIS EXISTS
---------------
`llama3.2:3b` is 4.7x faster than `llama3.1:8b` and completely unusable: across
seven full runs it produced ONE engagement in 42,336 exposures, because it could
not emit tool calls reliably. That cost about four hours of machine time to
discover, and a full 36-agent run to confirm.

The property that separates a usable model from an unusable one is tool-call
reliability on THIS prompt -- the real persona, the real twelve-post feed, the
real 22 tool schemas. That can be measured in a couple of minutes per model
instead of two hours, and it is what this script does.

WHAT IT MEASURES, IN PRIORITY ORDER
-----------------------------------
1. tool-call rate      -- fraction of turns that produce a parseable tool call.
                          Below ~0.5 the model cannot drive the simulation at
                          all; llama3.1:8b sits around 0.8 on the terse prompt.
2. feed grounding      -- of the calls that reference a post, how many name a
                          post_id that was ACTUALLY in the feed. A model that
                          invents ids will be rejected by the informed-action
                          gate and look like an agent that did nothing.
3. action variety      -- how many distinct actions it reaches for. A model that
                          only ever calls create_post produces the F-63 pattern:
                          busy, and scientifically dead.
4. speed               -- tokens/sec and wall time per turn. Last, deliberately.
                          Speed only matters among models that pass 1-3.

WHAT IT CANNOT TELL YOU
-----------------------
Whether the model's *choices* are reasonable -- whether it follows plausible
people or writes in character. That needs a full run and the engagement gate.
This is a filter to avoid spending two hours on a model that was never viable,
not a substitute for the run.

USAGE
    python eval_model.py --models llama3.1:8b granite4.1:3b gemma4:4b
    python eval_model.py --models llama3.1:8b --trials 20
"""
from __future__ import annotations

import argparse
import collections
import json
import statistics
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, __file__.rsplit("/", 1)[0])

FEED_SIZE = 12


def build_tools(terse: bool = True):
    """The real tool schemas the simulation sends, terse descriptions and all."""
    from camel.toolkits import FunctionTool
    from oasis.social_agent.agent_action import SocialAction
    from timeline_agent import TimelineAgent

    tools = []
    for name in TimelineAgent.TERSE:
        fn = getattr(SocialAction, name, None)
        if fn is None:
            continue
        t = FunctionTool(fn)
        if terse:
            t.set_function_description(TimelineAgent.TERSE[name])
            for pname, pterse in TimelineAgent.TERSE_PARAMS.items():
                try:
                    t.set_parameter_description(pname, pterse)
                except Exception:  # noqa: BLE001, S112
                    pass          # this tool has no such parameter
        tools.append(t.get_openai_tool_schema())
    return tools


def build_turn(trial: int):
    """One realistic turn: shared system block, persona and feed in the user turn."""
    ids = [1000 + trial * 100 + i for i in range(FEED_SIZE)]
    feed = "\n".join(
        json.dumps({
            "post_id": pid,
            "author": f"Agent {i}",
            "followee_id": i,
            "content": ("As an agriculture enthusiast I am excited to explore how "
                        f"economic principles apply to sustainable farming, post {i}."),
            "likes": 0,
        })
        for i, pid in enumerate(ids)
    )
    system = ("# OBJECTIVE\nYou're a Twitter user, and I'll present you with some "
              "tweets. After you see the tweets, choose some actions from the "
              "following functions.\n\n# RESPONSE METHOD\nPlease perform actions "
              "by tool calling.")
    user = (f"You are James Miller, a 40-year-old ESTJ from the UK working in "
            f"Hospitality & Tourism, interested in Economics and Business.\n\n"
            f"Here is your feed. Each post shows who wrote it:\n[{feed}]\n\n"
            f"Copy the id values straight out of the feed above. Do whatever "
            f"fits you and what you have just read.")
    return ids, [{"role": "system", "content": system},
                 {"role": "user", "content": user}]


def one_turn(model: str, tools, trial: int, timeout: float = 300.0,
             max_tokens: int = 300):
    ids, messages = build_turn(trial)
    body = json.dumps({"model": model, "messages": messages, "tools": tools,
                       "max_tokens": max_tokens, "temperature": 0.7}).encode()
    req = urllib.request.Request(
        "http://localhost:11434/v1/chat/completions", body,
        {"Content-Type": "application/json"})
    t0 = time.time()
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "err": str(exc)[:60]}
    wall = time.time() - t0

    msg = data.get("choices", [{}])[0].get("message", {}) or {}
    calls = msg.get("tool_calls") or []
    usage = data.get("usage", {}) or {}

    names, grounded, ungrounded = [], 0, 0
    for c in calls:
        fn = c.get("function", {}) or {}
        names.append(fn.get("name"))
        raw = fn.get("arguments")
        try:
            args = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except json.JSONDecodeError:
            ungrounded += 1     # unparseable arguments are as bad as invented ids
            continue
        pid = args.get("post_id")
        if pid is None:
            continue            # follow/search/etc. carry no post id
        if pid in ids:
            grounded += 1
        else:
            ungrounded += 1

    return {"ok": True, "wall": wall, "calls": len(calls), "names": names,
            "truncated": data.get("choices",[{}])[0].get("finish_reason")=="length",
            "engaged": grounded > 0, "grounded": grounded, "ungrounded": ungrounded,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "out_tokens": usage.get("completion_tokens", 0),
            "text": (msg.get("content") or "")[:80]}


def evaluate(model: str, trials: int, tools, max_tokens: int = 300,
             offset: int = 0):
    rows = [one_turn(model, tools, offset + i, max_tokens=max_tokens)
            for i in range(trials)]
    good = [r for r in rows if r.get("ok")]
    if not good:
        return {"model": model, "error": rows[0].get("err", "no response")}
    with_call = [r for r in good if r["calls"] > 0]
    g = sum(r["grounded"] for r in good)
    u = sum(r["ungrounded"] for r in good)
    names = [n for r in good for n in r["names"] if n]
    mix = collections.Counter(names)
    return {
        "model": model,
        "n": len(good),
        "tool_rate": len(with_call) / len(good),
        "engage": sum(r["engaged"] for r in good) / len(good),
        "grounding": (g / (g + u)) if (g + u) else None,
        "variety": len(set(names)),
        "mix": ", ".join(f"{k} x{v}" for k, v in mix.most_common(5)) or "-",
        "wall": statistics.mean(r["wall"] for r in good),
        "prompt_tokens": statistics.mean(r["prompt_tokens"] for r in good),
        "tok_s": (sum(r["out_tokens"] for r in good)
                  / sum(r["wall"] for r in good)),
        "out_tokens": statistics.mean(r["out_tokens"] for r in good),
        # F-78: a thinking model spends its whole budget reasoning and never
        # reaches the tool call. That is OUR cap, not the model -- the real sim
        # runs uncapped -- so a high rate here invalidates the reading.
        "trunc_rate": sum(r.get("truncated", False) for r in good) / len(good),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--trials", type=int, default=12)
    ap.add_argument("--reps", type=int, default=1,
                    help="repeat the whole evaluation N times and report mean "
                         "and spread. F-79: a single 25-trial reading of the "
                         "baseline swung 44-64%%, so one reading is not a "
                         "measurement.")
    ap.add_argument("--max-tokens", type=int, default=300,
                    help="output cap. F-78: thinking models need this high "
                         "(4000+) or they are rejected for a limit the real "
                         "simulation does not impose.")
    ap.add_argument("--verbose-tools", action="store_true",
                    help="use upstream's full docstrings instead of the terse "
                         "descriptions (F-64), for comparison")
    args = ap.parse_args()

    tools = build_tools(terse=not args.verbose_tools)
    print(f"  {len(tools)} tool schemas, {args.trials} trials per model, "
          f"{'verbose' if args.verbose_tools else 'terse'} descriptions\n")
    print(f"  {'model':<20}{'tool rate':>11}{'ENGAGED':>10}{'grounded':>10}"
          f"{'wall':>8}{'tok/s':>8}")

    for m in args.models:
        reps = [evaluate(m, args.trials, tools, args.max_tokens,
                         offset=k * args.trials * 7)
                for k in range(args.reps)]
        ok = [r for r in reps if "error" not in r]
        if not ok:
            print(f"  {m:<20}  FAILED: {reps[0].get('error')}")
            continue
        eng = [100 * r["engage"] for r in ok]
        mu = statistics.mean(eng)
        sd = statistics.stdev(eng) if len(eng) > 1 else 0.0
        last = ok[-1]
        gr = ("n/a" if last["grounding"] is None
              else f"{100*last['grounding']:.0f}%")
        spread = f"{mu:.0f}%" if len(eng) == 1 else f"{mu:.0f}%+-{sd:.0f}"
        print(f"  {m:<20}{100*last['tool_rate']:>10.0f}%{spread:>10}{gr:>10}"
              f"{last['wall']:>7.1f}s{last['tok_s']:>8.1f}")
        print(f"  {'':<20}  actions: {last['mix']}")
        print(f"  {'':<20}  out {last['out_tokens']:.0f} tok"
              + ("   TRUNCATED on "
                 f"{100*last['trunc_rate']:.0f}% of turns -- RAISE --max-tokens,"
                 " this reading is INVALID" if last["trunc_rate"] > 0.1 else ""))
        if len(eng) > 1:
            print(f"  {'':<20}  {len(eng)} reps: "
                  + ", ".join(f"{e:.0f}%" for e in eng))

    print("\n  HOW TO READ THIS")
    print("   ENGAGED is the gate. It is the share of turns emitting at least one")
    print("   action whose post_id is really in the feed -- analyze.py's own")
    print("   definition of seen_and_acted, which is what the run is scored on.")
    print("   Everything else is diagnostic:")
    print("     tool rate  turns producing any parseable call. Necessary, NOT")
    print("                sufficient -- llama3.2:3b scores 100% here and is")
    print("                still unusable, which is exactly why ENGAGED exists.")
    print("     grounded   of calls naming a post_id, the share naming a real one.")
    print("     actions    the mix. All search_posts/create_post with no like or")
    print("                comment is the F-63 pattern: busy, and dead.")
    print("\n  CALIBRATION. llama3.1:8b is the reference; it engages on roughly a")
    print("  third of turns and delivers ~5.9% of exposures in a real run. A")
    print("  candidate must match it on ENGAGED before its speed means anything.")
    print("  The proxy COMPRESSES the difference -- 8 fresh turns cannot reproduce")
    print("  a 500x gap -- so treat a shortfall as disqualifying and a tie as")
    print("  'worth one full run', never as proof of equivalence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
