"""Paired, cluster-aware comparison between simulation runs.

WHY THIS EXISTS
---------------
Findings F-32 and F-33. Every cross-run claim in this project was, until now,
made with a test that did not fit the design, and three of them were wrong as a
result:

  * `analyze.py` reports one run. Comparisons were then made by eye, or with a
    two-proportion z-test over *chosen actions*, treating 418 actions as 418
    independent observations.
  * They are not independent. They are clustered within agent -- measured
    ICC 0.31-0.38 for `create_post` share, design effect 4.3-4.8. Effective n
    is ~90, not ~410, so the true minimum detectable effect is ~20 pp rather
    than the ~9 pp the naive test implies.
  * The unit of randomisation is the *run*, and there was n=1 per condition.
    With one run per arm there are zero degrees of freedom for run-level
    variance, so a p-value comparing two runs is not interpretable at all.

The fix is available in the existing data. `personas.select_diverse` is
deterministic, so the same persona occupies the same agent id in every run
(verified 36/36 across baseline and v10). That makes a **paired within-agent**
design valid retrospectively: compare each agent to itself across runs and the
between-agent variance -- the term that produced the design effect -- drops out
entirely. Measured MDE improves from ~20 pp to 4.7-14.1 pp.

WHAT THIS REPORTS, AND WHY EACH PART IS THERE
---------------------------------------------
  config diff     Two runs that differ in more than one setting cannot
                  attribute an effect to either. This is finding F-22, which
                  was then repeated at v10 (wording and temperature changed
                  together). The tool now refuses to stay quiet about it.
  paired tests    t-test plus Wilcoxon signed-rank. Shares are bounded and
                  skewed, so the non-parametric result is the one to trust when
                  they disagree.
  Holm correction Several actions are tested at once. Holm is uniformly more
                  powerful than Bonferroni at the same family-wise error rate.
  MDE             What the comparison could have detected. Reported always,
                  because "not significant" is only meaningful alongside it --
                  the round-0 intro test in F-30 could only detect >=21 pp and
                  observed 17 pp, so it never could have succeeded.
  noise floor     For two runs of identical config, the paired SD *is* the
                  run-to-run noise. That number sets the ceiling on what any
                  future intervention study here can resolve.

Usage:
    compare.py --runs baseline v10_register
    compare.py --runs v10_register v10_replicate --replicate
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict

import numpy as np
from scipy import stats

# Actions worth testing. The long tail (unfollow, mute, report, search...) has
# never fired in any run, and testing all-zero columns only inflates the
# multiple-comparison correction against the actions that do vary.
DEFAULT_ACTIONS = ("create_post", "create_comment", "like_post", "follow")

# alpha and power used for every MDE figure reported here.
ALPHA = 0.05
POWER = 0.80


def load_run(label, data_dir="data"):
    """Read one run's analysis JSON plus the manifest that recorded its config."""
    apath = os.path.join(data_dir, f"social_timeline_{label}_analysis.json")
    with open(apath) as fh:
        analysis = json.load(fh)
    config = {}
    mpath = os.path.join(data_dir, f"social_timeline_{label}.json")
    if os.path.exists(mpath):
        with open(mpath) as fh:
            config = json.load(fh).get("config", {})
    return {"label": label, "analysis": analysis, "config": config}


def config_diff(a, b):
    """Settings that differ between two runs, excluding derived/timing fields."""
    skip = {"persona_separability", "actions"}
    ca, cb = a["config"], b["config"]
    out = []
    for key in sorted(set(ca) | set(cb)):
        if key in skip:
            continue
        va, vb = ca.get(key), cb.get(key)
        if isinstance(va, (list, dict)) or isinstance(vb, (list, dict)):
            continue
        if va != vb:
            out.append((key, va, vb))
    return out


def per_agent(run, actions):
    """Per-agent action counts, total actions, and shares.

    Agents that took no action at all are carried with share = NaN rather than
    dropped, so the paired vectors stay aligned by agent id; NaN pairs are
    removed per-action at test time.
    """
    counts = defaultdict(Counter)
    for ev in run["analysis"]["events"]:
        counts[str(ev.get("agent_id"))][ev.get("action")] += 1
    ids = sorted(counts, key=lambda x: int(x))
    total = {i: sum(counts[i].values()) for i in ids}
    shares = {a: {i: (counts[i][a] / total[i] if total[i] else np.nan)
                  for i in ids} for a in actions}
    rates = {a: {i: counts[i][a] for i in ids} for a in actions}
    return ids, total, shares, rates


def icc_and_deff(share_map, total_map):
    """One-way ANOVA intra-cluster correlation and the resulting design effect.

    Between-agent variance is compared against the binomial variance expected
    within an agent taking that many actions. If the observed spread is no
    wider than binomial noise, ICC is 0 and clustering costs nothing.
    """
    vals = np.array([v for v in share_map.values() if np.isfinite(v)])
    sizes = np.array([total_map[k] for k, v in share_map.items()
                      if np.isfinite(v)])
    if len(vals) < 2:
        return 0.0, 1.0, float("nan")
    m = float(sizes.mean())
    pbar = float(vals.mean())
    between = float(vals.var(ddof=1))
    within = pbar * (1 - pbar) / m if m else 0.0
    if between + within <= 0:
        return 0.0, 1.0, m
    icc = max(0.0, (between - within) / (between + within))
    return icc, 1 + (m - 1) * icc, m


def mde_paired(sd, n, alpha=ALPHA, power=POWER):
    """Smallest true difference a paired design at this SD and n could detect."""
    if n < 2 or not np.isfinite(sd):
        return float("nan")
    za = stats.norm.ppf(1 - alpha / 2)
    zb = stats.norm.ppf(power)
    return (za + zb) * sd / np.sqrt(n)


def holm(pvals):
    """Holm-Bonferroni adjusted p-values, order preserved."""
    idx = np.argsort(pvals)
    adj = np.empty(len(pvals))
    running = 0.0
    for rank, i in enumerate(idx):
        val = (len(pvals) - rank) * pvals[i]
        running = max(running, val)
        adj[i] = min(1.0, running)
    return adj


def paired_tests(run_a, run_b, actions):
    """Paired within-agent comparison, one row per action."""
    ids_a, tot_a, sh_a, _ = per_agent(run_a, actions)
    ids_b, tot_b, sh_b, _ = per_agent(run_b, actions)
    common = [i for i in ids_a if i in set(ids_b)]

    rows, pvals = [], []
    for act in actions:
        pairs = [(sh_a[act][i], sh_b[act][i]) for i in common]
        pairs = [(x, y) for x, y in pairs
                 if np.isfinite(x) and np.isfinite(y)]
        if len(pairs) < 3:
            continue
        x = np.array([p[0] for p in pairs])
        y = np.array([p[1] for p in pairs])
        d = y - x
        n = len(d)
        sd = float(d.std(ddof=1))
        mean = float(d.mean())
        se = sd / np.sqrt(n) if n else float("nan")

        t_p = stats.ttest_rel(y, x).pvalue if sd > 0 else 1.0
        try:
            w_p = (stats.wilcoxon(y, x).pvalue if np.any(d != 0) else 1.0)
        except ValueError:
            w_p = float("nan")
        crit = stats.t.ppf(1 - ALPHA / 2, n - 1)
        rows.append({
            "action": act, "n": n, "mean": mean, "sd": sd,
            "lo": mean - crit * se, "hi": mean + crit * se,
            "t_p": float(t_p), "w_p": float(w_p),
            "mde": mde_paired(sd, n),
        })
        pvals.append(float(t_p))

    if rows:
        for row, adj in zip(rows, holm(np.array(pvals))):
            row["t_p_holm"] = float(adj)
    return rows, common


def render(run_a, run_b, actions, replicate=False):
    out = []
    add = out.append
    la, lb = run_a["label"], run_b["label"]

    add("=" * 78)
    add(f"PAIRED COMPARISON   {la}  ->  {lb}")
    add("=" * 78)

    diffs = config_diff(run_a, run_b)
    if replicate and diffs:
        add("")
        add("!! --replicate was passed but the configs are NOT identical.")
        add("!! The paired SD below is NOT a clean noise floor: it also")
        add("!! contains whatever these settings changed.")
    if diffs:
        add("")
        add("CONFIG DIFFERENCES")
        for key, va, vb in diffs:
            add(f"  {key:<22} {va!r:>22}  ->  {vb!r}")
        if len(diffs) > 1:
            add("")
            add("  WARNING (F-22): more than one setting differs, so no effect")
            add("  below can be attributed to any single change.")
    elif replicate:
        add("")
        add("CONFIG IDENTICAL -- this is a true replicate. The paired SD below")
        add("is the run-to-run noise floor for this configuration.")

    rows, common = paired_tests(run_a, run_b, actions)
    add("")
    add(f"PAIRED WITHIN-AGENT TESTS   (n={len(common)} personas at matched ids)")
    add("  share of each agent's own chosen actions; paired on agent id")
    add("")
    add(f"  {'action':<16}{'diff':>8}{'SD':>8}{'95% CI':>18}"
        f"{'t p':>8}{'holm':>8}{'wilcox':>8}{'MDE':>8}")
    add("  " + "-" * 74)
    for r in rows:
        star = "  *" if r.get("t_p_holm", 1) < ALPHA else ""
        add(f"  {r['action']:<16}{r['mean']*100:+7.1f}%{r['sd']*100:7.1f}%"
            f"  [{r['lo']*100:+5.1f},{r['hi']*100:+5.1f}]%"
            f"{r['t_p']:8.3f}{r.get('t_p_holm', float('nan')):8.3f}"
            f"{r['w_p']:8.3f}{r['mde']*100:7.1f}pp{star}")
    add("")
    add("  * = survives Holm correction across the actions tested.")
    add("  MDE = smallest true shift this paired design could detect")
    add(f"        (alpha={ALPHA}, power={POWER}). An observed effect below its")
    add("        own MDE is not evidence of absence.")

    add("")
    add("CLUSTERING DIAGNOSTIC (why the unpaired test is not usable)")
    add(f"  {'action':<16}{'run':<16}{'ICC':>7}{'design eff':>12}"
        f"{'eff. n':>9}{'raw n':>8}")
    add("  " + "-" * 68)
    for run in (run_a, run_b):
        ids, tot, sh, _ = per_agent(run, actions)
        raw = sum(tot.values())
        for act in actions:
            icc, deff, _m = icc_and_deff(sh[act], tot)
            add(f"  {act:<16}{run['label']:<16}{icc:7.3f}{deff:12.2f}"
                f"{raw/deff:9.0f}{raw:8d}")
    add("")
    add("  Effective n is what the clustered data is worth. Treating raw n as")
    add("  independent inflates significance; this is finding F-32.")

    if replicate and rows and not diffs:
        add("")
        add("=" * 78)
        add("NOISE FLOOR  (identical configs -- this is pure run-to-run variation)")
        add("=" * 78)
        for r in rows:
            add(f"  {r['action']:<16} paired SD {r['sd']*100:5.1f} pp"
                f"   -> at n=36 an intervention must move"
                f" >= {r['mde']*100:4.1f} pp to be visible")
        add("")
        add("  Agent-pairs required to resolve a given true shift:")
        add(f"  {'shift':>8}" + "".join(f"{r['action'][:11]:>13}" for r in rows))
        za = stats.norm.ppf(1 - ALPHA / 2)
        zb = stats.norm.ppf(POWER)
        for shift in (0.03, 0.05, 0.10):
            cells = "".join(
                f"{((za+zb)*r['sd']/shift)**2:13.0f}" for r in rows)
            add(f"  {shift*100:7.1f}pp" + cells)
        add("")
        add("  Divide by 36 for the number of pooled runs at the current size.")

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs=2, required=True,
                    metavar=("BEFORE", "AFTER"),
                    help="two run labels, e.g. baseline v10_register")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--actions", nargs="*", default=list(DEFAULT_ACTIONS))
    ap.add_argument("--replicate", action="store_true",
                    help="the two runs are meant to be identical; report the "
                         "run-to-run noise floor and required sample sizes")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    a = load_run(args.runs[0], args.data_dir)
    b = load_run(args.runs[1], args.data_dir)
    text = render(a, b, tuple(args.actions), replicate=args.replicate)
    print(text)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
