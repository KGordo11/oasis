"""Gate for the Mantel-Haenszel estimator in `exposure_model.py`.

WHY THIS EXISTS
---------------
The MH odds ratio is the primary result of the exposure analysis, and it is
hand-rolled (including the Robins-Breslow-Greenland variance). The pattern this
project keeps hitting -- F-30's pair-level bootstrap, F-32's unclustered z-test
-- is a plausible-looking statistic that nobody checked against a case with a
known answer. Every check below constructs data whose true odds ratio is known
by construction.

Run:
    oasis-env/bin/python examples/experiment/social_timeline/test_exposure_model.py
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from exposure_model import mantel_haenszel  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    if not ok:
        failures.append(label)


def rows_from_counts(spec):
    """spec: {stratum: {tier: (n_acted, n_total)}} -> exposure rows."""
    out = []
    for strat, tiers in spec.items():
        for tier, (k, n) in tiers.items():
            for i in range(n):
                out.append({"feed": strat, "tier": tier,
                            "acted": 1 if i < k else 0})
    return out


# ---- 1. Homogeneous OR across strata must be recovered ------------------
# Each stratum: exposed 20/100 (odds .25), unexposed 5/100 (odds .0526).
# True OR = .25/.0526 = 4.75
spec = {f"s{i}": {"network": (20, 100), "discovery": (5, 100)}
        for i in range(10)}
m = mantel_haenszel(rows_from_counts(spec), "network", "discovery")
check("recovers a homogeneous odds ratio",
      abs(m["or"] - 4.75) < 0.01, f"OR={m['or']:.4f} (true 4.75)")
check("CI brackets the true value",
      m["lo"] < 4.75 < m["hi"], f"[{m['lo']:.2f},{m['hi']:.2f}]")
check("uses every informative stratum", m["strata"] == 10, f"{m['strata']}")

# ---- 2. A true null must not be flagged --------------------------------
spec = {f"s{i}": {"network": (10, 100), "discovery": (10, 100)}
        for i in range(10)}
m = mantel_haenszel(rows_from_counts(spec), "network", "discovery")
check("OR = 1 under a true null", abs(m["or"] - 1.0) < 1e-9, f"{m['or']:.4f}")
check("null is not significant", m["p"] > 0.5, f"p={m['p']:.3f}")

# ---- 3. Confounding by stratum must be removed -------------------------
# Strata differ wildly in baseline rate AND in tier mix, but the within-
# stratum OR is 1 everywhere. A crude pooled comparison would show an effect
# (Simpson's paradox); MH must return 1.
spec = {
    # high-baseline stratum, mostly network
    "hi": {"network": (90, 100), "discovery": (9, 10)},
    # low-baseline stratum, mostly discovery
    "lo": {"network": (1, 10), "discovery": (10, 100)},
}
rows = rows_from_counts(spec)
crude_n = sum(r["acted"] for r in rows if r["tier"] == "network") / \
    len([r for r in rows if r["tier"] == "network"])
crude_d = sum(r["acted"] for r in rows if r["tier"] == "discovery") / \
    len([r for r in rows if r["tier"] == "discovery"])
m = mantel_haenszel(rows, "network", "discovery")
check("removes confounding a crude comparison would show",
      abs(m["or"] - 1.0) < 0.05,
      f"crude {crude_n*100:.0f}% vs {crude_d*100:.0f}%, MH OR={m['or']:.3f}")

# ---- 4. Strata with no tier variation must drop out --------------------
spec = {
    "informative": {"network": (20, 100), "discovery": (5, 100)},
    "network_only": {"network": (50, 100)},
    "discovery_only": {"discovery": (50, 100)},
}
m = mantel_haenszel(rows_from_counts(spec), "network", "discovery")
check("drops strata with no tier variation", m["strata"] == 1,
      f"strata={m['strata']}")
check("dropping them leaves the estimate unbiased",
      abs(m["or"] - 4.75) < 0.01, f"OR={m['or']:.4f}")

# ---- 5. Direction and degenerate handling ------------------------------
spec = {f"s{i}": {"network": (5, 100), "discovery": (20, 100)}
        for i in range(10)}
m = mantel_haenszel(rows_from_counts(spec), "network", "discovery")
check("reports OR < 1 when exposure protects",
      m["or"] < 1, f"OR={m['or']:.4f}")
m = mantel_haenszel([], "network", "discovery")
check("empty input returns NaN rather than raising", np.isnan(m["or"]))
spec = {"s": {"network": (0, 50), "discovery": (0, 50)}}
m = mantel_haenszel(rows_from_counts(spec), "network", "discovery")
check("all-zero outcome returns NaN rather than raising", np.isnan(m["or"]))

# ---- 6. More data must tighten the interval ----------------------------
small = mantel_haenszel(rows_from_counts(
    {f"s{i}": {"network": (20, 100), "discovery": (5, 100)}
     for i in range(2)}), "network", "discovery")
large = mantel_haenszel(rows_from_counts(
    {f"s{i}": {"network": (20, 100), "discovery": (5, 100)}
     for i in range(50)}), "network", "discovery")
check("CI narrows as strata accumulate",
      (large["hi"] - large["lo"]) < (small["hi"] - small["lo"]),
      f"{small['hi']-small['lo']:.2f} -> {large['hi']-large['lo']:.2f}")

print("\n" + "=" * 60)
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print("Mantel-Haenszel estimator verified against known-answer data.")
