"""Gate for `compare.py`'s statistics, validated against synthetic data.

IN PLAIN WORDS
--------------
A TEST. It checks that the run-comparison maths is correct.

It runs the calculations on made-up data where the right answer is already
known, and fails loudly if the code disagrees. This exists because several
results in this project were wrong the first time; the tests are what stops
that happening silently again.

WHY THIS EXISTS
---------------
`compare.py` exists because three conclusions in this project were wrong on
statistical grounds (F-30, F-32, F-33): a bootstrap resampled the wrong unit, a
z-test treated clustered actions as independent, and cross-run p-values were
computed with n=1 per condition. Replacing those with a new home-rolled
estimator and *not* testing it would repeat the pattern one level up -- in
particular the ICC estimator, which is what downgraded the headline finding.

Every check below builds data whose true answer is known by construction and
asserts the estimator recovers it.

Run:
    oasis-env/bin/python examples/experiment/social_timeline/test_compare.py
Exits non-zero on any failure.
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compare import (config_diff, holm, icc_and_deff,  # noqa: E402
                     mde_paired, paired_tests)

failures = []


def check(label, ok, detail=""):
    """Run one test and record whether it passed."""
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    if not ok:
        failures.append(label)


def make_run(label, per_agent_actions, config=None):
    """Build a minimal run dict: {agent_id: {action: count}}."""
    events = []
    for aid, counts in per_agent_actions.items():
        for action, n in counts.items():
            events.extend([{"agent_id": aid, "action": action}] * n)
    return {"label": label, "analysis": {"events": events},
            "config": config or {}}


# ---------------------------------------------------------------- Holm
exp = [0.04, 0.06, 0.06, 0.06]
check("holm matches hand-computed values",
      np.allclose(holm(np.array([0.01, 0.02, 0.03, 0.04])), exp))
check("holm is order-invariant",
      np.allclose(holm(np.array([0.04, 0.01, 0.03, 0.02])),
                  [0.06, 0.04, 0.06, 0.06]))
check("holm never reports below the raw p-value",
      bool(np.all(holm(np.array([0.2, 0.5, 0.9])) >= [0.2, 0.5, 0.9])))

# ---------------------------------------------------------------- MDE
m1, m2 = mde_paired(0.10, 36), mde_paired(0.30, 36)
check("MDE grows with SD", m2 > m1, f"{m1:.3f} -> {m2:.3f}")
small, large = mde_paired(0.30, 36), mde_paired(0.30, 400)
check("MDE shrinks with n", large < small, f"n=36 {small:.3f} -> n=400 {large:.3f}")
# Known value: (1.959964+0.841621)*0.30/sqrt(36) = 0.14008
check("MDE matches closed form",
      abs(mde_paired(0.30, 36) - 0.140079) < 1e-4,
      f"{mde_paired(0.30, 36):.6f}")

# ---------------------------------------------------------------- ICC
# Case A: every agent shares the same true rate, so all observed spread is
# binomial noise. True ICC is 0.
rng = np.random.default_rng(0)
m = 12
shares_a = {str(i): rng.binomial(m, 0.6) / m for i in range(400)}
totals_a = {str(i): m for i in range(400)}
icc_a, deff_a, _ = icc_and_deff(shares_a, totals_a)
check("ICC ~ 0 when agents are homogeneous", icc_a < 0.05,
      f"icc={icc_a:.3f} deff={deff_a:.2f}")

# Case B: two populations with very different rates. True ICC is large.
shares_b, totals_b = {}, {}
for i in range(400):
    p = 0.2 if i % 2 else 0.9
    shares_b[str(i)] = rng.binomial(m, p) / m
    totals_b[str(i)] = m
icc_b, deff_b, _ = icc_and_deff(shares_b, totals_b)
check("ICC large when agents genuinely differ", icc_b > 0.5,
      f"icc={icc_b:.3f} deff={deff_b:.2f}")
check("design effect exceeds 1 only under clustering",
      deff_a < 1.6 < deff_b, f"{deff_a:.2f} vs {deff_b:.2f}")

# ---------------------------------------------------------------- paired test
# Inject a known +15pp shift in create_post share for every agent.
base, shifted = {}, {}
for i in range(36):
    n_post, n_other = 6, 6                       # 50% share
    base[str(i)] = {"create_post": n_post, "like_post": n_other}
    # 15pp shift: 7.8/12 ~ 0.65. Use 8/12 = 66.7% for a clean +16.7pp.
    shifted[str(i)] = {"create_post": 8, "like_post": 4}
rows, common = paired_tests(make_run("a", base), make_run("b", shifted),
                            ("create_post", "like_post"))
row = next(r for r in rows if r["action"] == "create_post")
check("paired test pairs all agents", len(common) == 36, f"n={len(common)}")
check("paired test recovers injected effect size",
      abs(row["mean"] - (8/12 - 6/12)) < 1e-9, f"{row['mean']:.4f}")
check("paired test finds a real, noiseless effect significant",
      row["t_p"] < 1e-6, f"p={row['t_p']:.2e}")

# A null effect must NOT come out significant.
noisy_a, noisy_b = {}, {}
for i in range(36):
    ka = rng.binomial(12, 0.5)
    kb = rng.binomial(12, 0.5)
    noisy_a[str(i)] = {"create_post": int(ka), "like_post": int(12 - ka)}
    noisy_b[str(i)] = {"create_post": int(kb), "like_post": int(12 - kb)}
rows_n, _ = paired_tests(make_run("a", noisy_a), make_run("b", noisy_b),
                         ("create_post",))
check("paired test does not fire on a null effect",
      rows_n[0]["t_p"] > 0.05, f"p={rows_n[0]['t_p']:.3f}")

# ---------------------------------------------------------------- config diff
d = config_diff(
    make_run("a", base, {"prompt_version": 8, "temperature": 0.7, "agents": 36}),
    make_run("b", base, {"prompt_version": 10, "temperature": 0.9, "agents": 36}))
keys = {k for k, _, _ in d}
check("config_diff reports every changed setting",
      keys == {"prompt_version", "temperature"}, str(keys))
check("config_diff ignores unchanged settings", "agents" not in keys)
check("config_diff is empty for identical configs",
      config_diff(make_run("a", base, {"x": 1}),
                  make_run("b", base, {"x": 1})) == [])

print("\n" + "=" * 60)
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print("compare.py statistics verified against known-answer data.")
