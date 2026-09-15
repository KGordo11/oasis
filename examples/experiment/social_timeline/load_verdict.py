"""Was a run contaminated by machine load? Judge it by cost, not by CPU percent.

WHY THIS REPLACES THE OLD VERDICT
---------------------------------
`night_queue.sh` labels each pass CLEAN / BUSY / HEAVILY LOADED from the median
non-simulation CPU, with thresholds 40 % and 100 % inherited from
`sweep_when_idle.sh`. That script answers a different question -- "is the machine
free right now" -- and the thresholds do not transfer.

Measured, across every pass that has a load trace:

    pass              median other-CPU   runs in it, s/agent-turn
    sweep18                 130 %        22.05 21.73 22.06 21.46 21.59 22.31
    r15                     137 %        21.12 22.47 20.98 21.61
    r15_s43                 136 %        21.00

Every pass is flagged HEAVILY LOADED. Every run lands within 4 % of the
21.44 s/agent-turn curve. **A warning that fires on 100 % of passes and predicts
nothing is not a warning**, and acting on it would mean discarding every run we
have.

The deeper problem is that the metric measures the wrong resource. B-32 -- the
run that actually cost 2.16x its reference -- was contended by a GPU-heavy
foreground application. `other_cpu` barely sees that, and B-32 predates load
sampling, so there is no positive example in the data at all: we have ~14
observations of "loaded and harmless" and zero of "loaded and harmful".

So this tool judges the outcome rather than the proxy. Cost per agent-turn is
already measured per run, the curve is known to 0.37 s, and a contaminated run
shows up there directly -- B-32 would have been a 2.16x deviation, impossible to
miss. Load is still reported, as context, never as the verdict.

USAGE
    python load_verdict.py                 # every run that has a manifest
    python load_verdict.py --run r15_a54
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import statistics as st

# The eight-point 7-round curve, independently reproduced by five 15-round runs
# (F-114): exponent ~1.0, 21.44 s per agent-turn, sd 0.37 across world sizes.
CURVE_MEAN = 21.44
CURVE_SD = 0.37

# Deviation bands. 3 sd is ~5 % and sits above the largest honest spread seen
# across 16 runs; 25 % is far below B-32's 116 % and still unmistakable.
WARN_FRAC = 0.10
BAD_FRAC = 0.25


def per_agent_turn(manifest: dict) -> float | None:
    """Plateau seconds per agent-turn: the run's own cost, ramp excluded."""
    rounds = manifest.get("rounds") or []
    agents = (manifest.get("config") or {}).get("agents")
    if not agents or len(rounds) < 6:
        return None
    plateau = [r["seconds"] for r in rounds][4:]
    return st.mean(plateau) / agents


def load_trace(prefix: str) -> dict | None:
    """Median and peak non-simulation CPU for the pass a run belonged to."""
    path = f"data/load_{prefix}.csv"
    if not os.path.exists(path):
        return None
    vals = []
    with open(path) as fh:
        for row in csv.DictReader(fh):
            try:
                vals.append(float(row["other_cpu_pct"]))
            except (TypeError, ValueError, KeyError):
                pass
    if not vals:
        return None
    return {"median": st.median(vals), "peak": max(vals), "n": len(vals)}


def comparable(manifest: dict) -> tuple[bool, str]:
    """Is this run even on the curve?

    The 21.44 s figure describes ONE configuration: terse tool descriptions and
    a context window that can hold the prompt. Judging other configurations
    against it produces exactly the wrong answer -- the B-28 truncated sweeps
    come out 60 % "fast" and the pre-terse-tools runs 40 %, and neither was
    contaminated by anything. They were cheaper because their agents did less
    (F-93), which is a finding, not a fault.
    """
    cfg = manifest.get("config") or {}
    env = manifest.get("environment") or {}
    ctx = env.get("server_context_length")
    if ctx is not None and ctx < 8192:
        return False, f"context {ctx} < 8192 (B-28 truncation)"
    if cfg.get("terse_tools") is not True:
        return False, "full tool documentation (pre-F-93 prompt)"
    if ctx is None:
        return False, "server context not recorded (pre-B-28 guard)"
    return True, ""


def verdict(cost: float | None) -> tuple[str, str]:
    """Judge the run by how far its cost sits from the curve."""
    if cost is None:
        return "NO COST", "too few rounds to have a plateau"
    dev = (cost - CURVE_MEAN) / CURVE_MEAN
    if abs(dev) >= BAD_FRAC:
        return "CONTAMINATED", f"{dev:+.0%} vs curve -- investigate before using"
    if abs(dev) >= WARN_FRAC:
        return "SUSPECT", f"{dev:+.0%} vs curve"
    return "OK", f"{dev:+.1%} vs curve"


def find_prefix(label: str) -> str:
    """Which pass's load trace covers this run. Longest matching prefix wins."""
    cands = [os.path.basename(p)[5:-4] for p in glob.glob("data/load_*.csv")]
    hits = [c for c in cands if label.startswith(c)]
    return max(hits, key=len) if hits else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default=None)
    ap.add_argument("--parquet-dir", default="data/parquet")
    args = ap.parse_args()

    labels = ([args.run] if args.run
              else sorted(os.listdir(args.parquet_dir)))
    print(f"{'run':22s}{'agents':>7s}{'s/agent-turn':>14s}{'verdict':>14s}"
          f"{'load median':>13s}{'peak':>7s}   note")
    shown = 0
    for label in labels:
        mp = os.path.join(args.parquet_dir, label, "manifest.json")
        if not os.path.exists(mp):
            continue
        man = json.load(open(mp))
        cost = per_agent_turn(man)
        if cost is None:
            continue
        ok_cfg, why = comparable(man)
        if ok_cfg:
            v, note = verdict(cost)
        else:
            v, note = "n/a", f"not on this curve: {why}"
        tr = load_trace(find_prefix(label))
        med = f"{tr['median']:.0f}%" if tr else "-"
        peak = f"{tr['peak']:.0f}%" if tr else "-"
        agents = (man.get("config") or {}).get("agents", "?")
        print(f"{label:22s}{agents:>7}{cost:>14.2f}{v:>14s}{med:>13s}{peak:>7s}   {note}")
        shown += 1
    print(f"\n{shown} runs listed. Only runs at the validated configuration are "
          f"judged against\n{CURVE_MEAN} s/agent-turn (sd {CURVE_SD}); SUSPECT at "
          f"{WARN_FRAC:.0%}, CONTAMINATED at {BAD_FRAC:.0%}. Everything else is "
          f'marked "n/a" with the reason --\na run at another configuration is not '
          f"slow or fast, it is a different experiment.")
    print("Load is reported as context only. It has never predicted a cost "
          "deviation in this project;\nthe one run that was genuinely "
          "contaminated (B-32, 2.16x) predates load sampling entirely.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
