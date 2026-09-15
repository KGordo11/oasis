"""Gate for load_verdict.py.

Exists because the tool it replaces was wrong in a way that looked right: a
verdict that fires on every pass reads as diligence and is noise. The checks
below are the two ways this tool could fail the same way -- judging runs that
are not on the curve, and failing to notice one that is genuinely off it.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load_verdict import comparable, per_agent_turn, verdict  # noqa: E402

PASS, FAIL = [], []


def check(label: str, cond: bool) -> None:
    (PASS if cond else FAIL).append(label)
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")


def man(agents, secs, terse=True, ctx=8192):
    return {"config": {"agents": agents, "terse_tools": terse},
            "environment": {"server_context_length": ctx},
            "rounds": [{"seconds": s} for s in secs]}


def main() -> int:
    # ---------- plateau arithmetic ----------
    m = man(10, [100, 200, 300, 400, 500, 500, 500, 500])
    check("plateau excludes the ramp (rounds 0-3)", per_agent_turn(m) == 50.0)
    check("too few rounds returns None", per_agent_turn(man(10, [1, 2])) is None)

    # ---------- the failure that motivated this tool ----------
    ok, why = comparable(man(36, [800] * 8, ctx=4096))
    check("B-28 truncated run is NOT judged against the curve", ok is False)
    check("  ...and says why", "4096" in why or "truncation" in why)
    ok, _ = comparable(man(36, [800] * 8, terse=False))
    check("pre-F-93 full-documentation run is NOT judged", ok is False)
    ok, _ = comparable(man(36, [800] * 8, ctx=None))
    check("run with no recorded context is NOT judged", ok is False)
    ok, _ = comparable(man(36, [800] * 8))
    check("validated-configuration run IS judged", ok is True)

    # ---------- verdict bands ----------
    check("on-curve cost is OK", verdict(21.44)[0] == "OK")
    check("+5% is still OK (within observed honest spread)", verdict(21.44 * 1.05)[0] == "OK")
    check("+15% is SUSPECT", verdict(21.44 * 1.15)[0] == "SUSPECT")
    check("B-32's 2.16x would be CONTAMINATED",
          verdict(21.44 * 2.16)[0] == "CONTAMINATED")
    check("a run 60% cheap is CONTAMINATED, not silently ignored",
          verdict(21.44 * 0.40)[0] == "CONTAMINATED")
    check("missing cost degrades to NO COST", verdict(None)[0] == "NO COST")

    # ---------- the regression that matters ----------
    # Every pass on record sat at 127-137% median CPU and every run landed
    # within ~4% of the curve. If a future change makes load drive the verdict
    # again, this fails.
    observed = [21.12, 22.47, 20.98, 21.61, 21.00, 22.05, 21.73, 22.06, 21.46,
                21.59, 22.31]
    check("every real run at the validated config reads OK "
          f"({len(observed)} runs, 127-137% median CPU throughout)",
          all(verdict(c)[0] == "OK" for c in observed))

    print("\n" + "=" * 62)
    print(f"{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        return 1
    print("Verdict follows measured cost, not a CPU proxy that never predicted it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
