"""Measure what a hosted API would actually do for this simulation.

WHY THIS EXISTS
---------------
The claim "a hosted API would be 40-80x faster" is, as of 2026-09-11,
ARITHMETIC AND NOT MEASUREMENT. It comes from published hardware specs
(M2 Max ~400 GB/s against H100 ~3,350 GB/s) and an assumed per-call latency of
3-8 s that nobody has checked. That is a weaker class of evidence than
everything else in this project, and six findings here have already been
overturned by the difference between an estimate and a measurement.

This script replaces the estimate with a number. It sends the REAL prompt --
the real persona, the real twelve-post feed, the real 22 tool schemas -- and
measures three things that together determine whether switching is worth it:

    1. LATENCY at the two prompt sizes that actually occur
       Round 0 is ~2,570 tokens. From round 4 the context is full at ~8,192,
       because accumulated history is re-read every turn (F-86). Benchmarking
       only the small one is how the local benchmarks understated the real cost
       for weeks -- a fresh single-turn request IS a round-0 prompt.

    2. CONCURRENCY behaviour at 36
       The whole speed argument rests on 36 agents going at once instead of 4.
       That is an assumption about the provider, not a fact, and rate limits
       bite here first: a run pushes ~3.4M input tokens.

    3. TOOL-CALL QUALITY on the real schemas
       Speed is worthless if the model will not emit a well-formed call naming
       a post_id that was really in the feed. That is the axis on which three
       local models failed (F-78), and it must be checked on the same footing.

USAGE
    export OPENAI_API_KEY=...        # or ANTHROPIC_API_KEY / GEMINI_API_KEY
    python benchmark_api.py --provider openai --model gpt-5
    python benchmark_api.py --provider anthropic --model claude-sonnet-5
    python benchmark_api.py --provider gemini --model gemini-2.5-pro

    --concurrency 36    how many to fire at once (default 36, the real shape)
    --trials 12         calls per cell

COST. A full pass is roughly 60 calls at up to 8k tokens each: around 0.5M
input tokens, so single-digit dollars at mid-tier pricing and less with
caching. It is cheap next to being wrong about a platform migration.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys
import time
import urllib.error
import urllib.request
import concurrent.futures as cf

sys.path.insert(0, __file__.rsplit("/", 1)[0])

# Measured on this machine, for comparison. See SIM4_LOG.md (Part II) F-86, F-88.
LOCAL = {
    "calls_per_run": 550,
    "concurrency": 4,
    "latency_plateau_s": 86.0,
    "latency_round0_s": 10.1,
    "run_seconds": 10170,
    "input_tokens_per_run": 3_400_000,
}

PROVIDERS = {
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "key": "OPENAI_API_KEY",
        "auth": lambda k: {"Authorization": f"Bearer {k}"},
    },
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "key": "ANTHROPIC_API_KEY",
        "auth": lambda k: {"x-api-key": k, "anthropic-version": "2023-06-01"},
    },
    "gemini": {   # OpenAI-compatible endpoint, so one request shape covers all
        "url": ("https://generativelanguage.googleapis.com/v1beta/openai/"
                "chat/completions"),
        "key": "GEMINI_API_KEY",
        "auth": lambda k: {"Authorization": f"Bearer {k}"},
    },
}


def build_tools():
    """The real 22 tool schemas, terse descriptions and all (F-64)."""
    from camel.toolkits import FunctionTool
    from oasis.social_agent.agent_action import SocialAction
    from timeline_agent import TimelineAgent

    tools = []
    for name in TimelineAgent.TERSE:
        fn = getattr(SocialAction, name, None)
        if fn is None:
            continue
        t = FunctionTool(fn)
        t.set_function_description(TimelineAgent.TERSE[name])
        for pname, pterse in TimelineAgent.TERSE_PARAMS.items():
            try:
                t.set_parameter_description(pname, pterse)
            except Exception:  # noqa: BLE001, S112
                pass
        tools.append(t.get_openai_tool_schema())
    return tools


def build_messages(trial: int, history_turns: int):
    """One turn at a realistic prompt size.

    `history_turns` synthesises the accumulated transcript that makes a plateau
    call cost 8.5x a round-0 call. Passing 0 reproduces round 0; passing 6
    lands near the 8,192-token cap, which is what rounds 4-14 actually send.
    """
    ids = [1000 + trial * 100 + i for i in range(12)]
    feed = "\n".join(
        json.dumps({"post_id": p, "author": f"Agent {i}", "followee_id": i,
                    "content": ("Reflecting on how economic policy shapes "
                                f"sustainable tourism, note {i}."),
                    "likes": i % 4})
        for i, p in enumerate(ids))
    system = ("# OBJECTIVE\nYou're a Twitter user, and I'll present you with "
              "some tweets. After you see the tweets, choose some actions from "
              "the following functions.\n\n# RESPONSE METHOD\nPlease perform "
              "actions by tool calling.")
    persona = ("You are James Miller, a 40-year-old ESTJ from the UK working "
               "in Hospitality & Tourism, interested in Economics and Business.")

    msgs = [{"role": "system", "content": system}]
    for h in range(history_turns):
        old = [f"post {900+h*12+i}: an earlier note on tourism economics"
               for i in range(12)]
        msgs.append({"role": "user",
                     "content": f"{persona}\n\nRound {h} feed:\n" + "\n".join(old)})
        msgs.append({"role": "assistant",
                     "content": f"I engaged with post {900+h*12+3}."})
    msgs.append({"role": "user",
                 "content": (f"{persona}\n\nHere is your feed:\n[{feed}]\n\n"
                             "Copy the id values straight out of the feed "
                             "above. Do whatever fits you.")})
    return ids, msgs


def call(cfg, model, key, ids, msgs, tools, timeout=300.0):
    if cfg["url"].endswith("/messages"):          # Anthropic's native shape
        sys_txt = next((m["content"] for m in msgs if m["role"] == "system"), "")
        body = {"model": model, "max_tokens": 300, "system": sys_txt,
                "messages": [m for m in msgs if m["role"] != "system"],
                "tools": [{"name": t["function"]["name"],
                           "description": t["function"].get("description", ""),
                           "input_schema": t["function"].get("parameters", {})}
                          for t in tools]}
    else:
        body = {"model": model, "messages": msgs, "tools": tools,
                "max_tokens": 300}
    req = urllib.request.Request(
        cfg["url"], json.dumps(body).encode(),
        {"Content-Type": "application/json", **cfg["auth"](key)})
    t0 = time.time()
    try:
        raw = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e:
        return {"ok": False, "err": f"HTTP {e.code}: {e.read()[:120].decode()}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "err": str(e)[:120]}
    wall = time.time() - t0

    # Normalise the two response shapes into one verdict.
    grounded = names = None
    if "content" in raw:                          # Anthropic
        blocks = raw.get("content") or []
        calls = [b for b in blocks if b.get("type") == "tool_use"]
        names = [c.get("name") for c in calls]
        grounded = any((c.get("input") or {}).get("post_id") in ids for c in calls)
        usage = raw.get("usage") or {}
        tok_in = usage.get("input_tokens", 0)
        tok_out = usage.get("output_tokens", 0)
    else:                                          # OpenAI-compatible
        msg = (raw.get("choices") or [{}])[0].get("message") or {}
        calls = msg.get("tool_calls") or []
        names = [c.get("function", {}).get("name") for c in calls]
        grounded = False
        for c in calls:
            try:
                args = json.loads(c["function"]["arguments"])
            except Exception:  # noqa: BLE001
                continue
            if args.get("post_id") in ids:
                grounded = True
        usage = raw.get("usage") or {}
        tok_in = usage.get("prompt_tokens", 0)
        tok_out = usage.get("completion_tokens", 0)

    return {"ok": True, "wall": wall, "calls": len(calls), "names": names,
            "engaged": grounded, "tok_in": tok_in, "tok_out": tok_out}


def cell(cfg, model, key, tools, trials, concurrency, history_turns, label):
    jobs = []
    for i in range(trials):
        ids, msgs = build_messages(i, history_turns)
        jobs.append((ids, msgs))
    t0 = time.time()
    with cf.ThreadPoolExecutor(max(1, concurrency)) as ex:
        res = list(ex.map(lambda j: call(cfg, model, key, j[0], j[1], tools), jobs))
    wall = time.time() - t0
    ok = [r for r in res if r.get("ok")]
    if not ok:
        print(f"  {label:<26} FAILED: {res[0].get('err')}")
        return None
    lat = [r["wall"] for r in ok]
    out = {"label": label, "n": len(ok), "wall": wall,
           "latency": st.mean(lat), "p90": sorted(lat)[int(.9 * len(lat)) - 1],
           "tok_in": st.mean(r["tok_in"] for r in ok),
           "engaged": sum(r["engaged"] for r in ok) / len(ok),
           "tool_rate": sum(1 for r in ok if r["calls"]) / len(ok),
           "throughput": len(ok) / wall}
    print(f"  {label:<26}{out['latency']:>8.1f}s{out['p90']:>8.1f}s"
          f"{out['tok_in']:>9.0f}{100*out['tool_rate']:>8.0f}%"
          f"{100*out['engaged']:>9.0f}%{out['throughput']:>10.2f}/s")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    ap.add_argument("--model", required=True)
    ap.add_argument("--trials", type=int, default=12)
    ap.add_argument("--concurrency", type=int, default=36)
    args = ap.parse_args()

    cfg = PROVIDERS[args.provider]
    key = os.environ.get(cfg["key"])
    if not key:
        print(f"  {cfg['key']} is not set. Export it and re-run.")
        return 1

    tools = build_tools()
    print(f"\n  {args.provider} / {args.model}   {len(tools)} tool schemas, "
          f"{args.trials} trials per cell\n")
    print(f"  {'cell':<26}{'latency':>9}{'p90':>8}{'prompt':>9}"
          f"{'tools':>8}{'ENGAGED':>9}{'thruput':>10}")

    r0_seq = cell(cfg, args.model, key, tools, args.trials, 1, 0, "round 0, sequential")
    rp_seq = cell(cfg, args.model, key, tools, args.trials, 1, 6, "plateau, sequential")
    rp_con = cell(cfg, args.model, key, tools, args.trials, args.concurrency, 6,
                  f"plateau, {args.concurrency} at once")

    if not (rp_seq and rp_con):
        print("\n  not enough cells completed to project a run time.")
        return 1

    print("\n  PROJECTED RUN — 36 agents, 15 rounds, ~550 calls")
    waves = 36 / max(args.concurrency, 1)
    est = 15 * waves * rp_con["latency"]
    print(f"    measured latency at plateau   {rp_con['latency']:.1f} s")
    print(f"    waves per round               {waves:.1f}")
    print(f"    projected run time            {est/60:.1f} min")
    print(f"    local, measured               {LOCAL['run_seconds']/60:.1f} min")
    print(f"    SPEEDUP                       {LOCAL['run_seconds']/max(est,1):.1f}x")

    print("\n  RATE LIMIT — the constraint that actually binds")
    tpm = LOCAL["input_tokens_per_run"] / max(est / 60, 1e-9)
    print(f"    a run pushes ~{LOCAL['input_tokens_per_run']/1e6:.1f}M input tokens")
    print(f"    at that pace it demands      {tpm/1000:>8.0f}K tokens/min sustained")
    print( "    check that against your tier. Below it, the run is throttled")
    print( "    rather than fast -- and prompt caching is the lever that helps,")
    print( "    since two thirds of every prompt is a stable growing prefix.")

    print("\n  QUALITY GATE — speed is worthless without this")
    print(f"    tool-call rate {100*rp_con['tool_rate']:.0f}%   "
          f"ENGAGED {100*rp_con['engaged']:.0f}%")
    print( "    llama3.1:8b scores ~53% ENGAGED on the same harness and is the")
    print( "    model every published result uses. A candidate below that is")
    print( "    faster at doing the wrong thing (F-75, F-78).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
