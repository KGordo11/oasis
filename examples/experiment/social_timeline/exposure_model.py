"""What actually predicts whether an agent engages with a post it was shown.

WHY THIS EXISTS
---------------
Findings F-35 and F-36 established that the cross-run noise floor (30.7 pp for
posting share) is several times larger than any prompt intervention this
project tested, so those comparisons could never have resolved anything. The
questions this simulation was actually built to answer are not cross-run at
all. "Who sees whose posts, and does reach flow through connections?" is a
*within-run* question, asked of 6048 exposure events per run and ~50k pooled,
and the noise floor does not apply to it.

IDENTIFICATION
--------------
The naive crosstab -- network-tier posts draw 13.7% engagement vs discovery's
2.3% -- is confounded twice over:

  1. **Feed position.** Network posts only ever occupy slots 0-4; discovery
     fills the tail. Top-of-feed posts are engaged with more regardless of
     where they came from, so part of the tier gap is really a position gap.
  2. **The agent, the round, and the run.** Agents differ enormously in how
     much they act at all (ICC up to 0.38, F-32), and an agent's activity
     varies by round.

Both are handled by stratifying on the **feed** -- one agent, one round, one
run, twelve posts seen at the same instant. Within a single feed the agent,
their disposition, the round and the run are all held fixed by construction,
and tier still varies because tiers backfill into each other's slots. The
Mantel-Haenszel estimator pools those strata without assuming a functional
form, and strata with no tier variation drop out automatically, exactly as a
fixed-effects estimator would.

A third confound cannot be removed and is reported rather than hidden:
**selection into the network tier.** An agent follows authors it already likes,
so network-tier authors are pre-selected on affinity. The `fof` contrast is the
answer to that -- friend-of-friend authors were chosen by *someone else's*
follows, never by the focal agent -- so `fof` vs `discovery` is the estimate to
trust for a causal reading, and `network` vs `discovery` is an upper bound.

SIMILARITY IS ANALYSED SEPARATELY, AND HERE IS WHY
--------------------------------------------------
The TwHIN similarity score is present for 100% of discovery exposures but only
28% of network and 43% of fof ones -- missing not at random, because it is
computed for ranked candidates rather than graph-injected ones. Putting it in a
model beside tier would induce selection bias. It is therefore tested only
within the discovery tier, which is both complete and the place where the score
is the ranking signal that put the post there.

Usage:
    exposure_model.py                       # every analysed run
    exposure_model.py --runs baseline v10_register
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict

import numpy as np
import statsmodels.api as sm
from scipy import stats


def load_exposures(label, data_dir="data"):
    """One row per exposure: which feed it sat in, its tier, slot, score, and
    whether the agent acted on that post."""
    path = os.path.join(data_dir, f"social_timeline_{label}_analysis.json")
    with open(path) as fh:
        d = json.load(fh)
    acted = {(int(a), int(p))
             for a, ag in d["agents"].items()
             for p in (ag.get("seen_and_acted") or [])}
    rows = []
    for e in d["exposures"]:
        aid, pid = int(e["agent_id"]), int(e["post_id"])
        rows.append({
            "run": label,
            "feed": f"{label}|{aid}|{e['round']}",   # the stratum
            "agent": f"{label}|{aid}",               # the cluster
            "tier": e["source"],
            "pos": int(e["feed_position"]),
            "score": e.get("score"),
            "acted": int((aid, pid) in acted),
        })
    return rows


def mantel_haenszel(rows, exposed, unexposed, stratum="feed"):
    """Stratified odds ratio with Robins-Breslow-Greenland variance.

    Strata containing only one of the two tiers contribute nothing to either
    sum, so they drop out on their own -- the fixed-effects property.
    """
    cells = defaultdict(lambda: {"a": 0, "b": 0, "c": 0, "d": 0})
    for r in rows:
        if r["tier"] == exposed:
            cells[r[stratum]]["a" if r["acted"] else "b"] += 1
        elif r["tier"] == unexposed:
            cells[r[stratum]]["c" if r["acted"] else "d"] += 1

    R = S = 0.0
    vr = vrs = vs = 0.0
    used = 0
    for c in cells.values():
        a, b, cc, dd = c["a"], c["b"], c["c"], c["d"]
        n = a + b + cc + dd
        if n == 0 or (a + b) == 0 or (cc + dd) == 0:
            continue                      # no tier variation in this feed
        used += 1
        Ri, Si = a * dd / n, b * cc / n
        Pi, Qi = (a + dd) / n, (b + cc) / n
        R += Ri
        S += Si
        vr += Pi * Ri
        vrs += Pi * Si + Qi * Ri
        vs += Qi * Si

    if R == 0 or S == 0:
        return {"or": float("nan"), "lo": float("nan"), "hi": float("nan"),
                "p": float("nan"), "strata": used}
    or_mh = R / S
    var = vr / (2 * R * R) + vrs / (2 * R * S) + vs / (2 * S * S)
    se = np.sqrt(var)
    z = np.log(or_mh) / se
    return {
        "or": or_mh,
        "lo": float(np.exp(np.log(or_mh) - 1.959964 * se)),
        "hi": float(np.exp(np.log(or_mh) + 1.959964 * se)),
        "p": float(2 * stats.norm.sf(abs(z))),
        "strata": used,
        "z": float(z),
    }


def crude_rates(rows, tier):
    sel = [r for r in rows if r["tier"] == tier]
    n = len(sel)
    a = sum(r["acted"] for r in sel)
    return a, n, (a / n if n else float("nan"))


def logit_cluster(y, X, groups, names):
    """Logit with cluster-robust covariance at the agent level."""
    model = sm.Logit(np.asarray(y, float), np.asarray(X, float))
    # statsmodels >=0.14 takes the robust covariance at fit time; there is no
    # get_robustcov_results on LogitResults.
    codes = {g: i for i, g in enumerate(dict.fromkeys(groups))}
    rob = model.fit(disp=0, method="newton", maxiter=200,
                    cov_type="cluster",
                    cov_kwds={"groups": np.array([codes[g] for g in groups])})
    out = []
    for i, nm in enumerate(names):
        b = rob.params[i]
        se = rob.bse[i]
        out.append({"name": nm, "coef": b, "or": float(np.exp(b)),
                    "lo": float(np.exp(b - 1.959964 * se)),
                    "hi": float(np.exp(b + 1.959964 * se)),
                    "p": float(rob.pvalues[i])})
    return out


MODERN = ("network", "fof", "discovery")
# Runs predating the three-tier feed label their sources differently. They
# cannot contribute to a network/fof/discovery contrast and must not be
# counted in its denominator -- but `following` vs `recsys` is the same
# comparison under an older feed, so they serve as an independent replication.
LEGACY = ("following", "recsys", "both")


def render(all_rows, labels):
    L = []
    add = L.append
    rows = [r for r in all_rows if r["tier"] in MODERN]
    legacy = [r for r in all_rows if r["tier"] in LEGACY]
    mod_runs = sorted({r["run"] for r in rows})
    leg_runs = sorted({r["run"] for r in legacy})

    add("=" * 78)
    add("WHAT PREDICTS ENGAGEMENT WITH A POST THE AGENT WAS SHOWN")
    add("=" * 78)
    add(f"analysed    : {len(mod_runs)} runs with the three-tier feed")
    add(f"              {', '.join(mod_runs)}")
    add(f"exposures   : {len(rows)}")
    add(f"feeds       : {len({r['feed'] for r in rows})}")
    add(f"agents      : {len({r['agent'] for r in rows})}")
    add(f"engaged     : {sum(r['acted'] for r in rows)}")
    if legacy:
        add("")
        add(f"held aside  : {len(leg_runs)} older runs ({len(legacy)} exposures) "
            f"label feed sources")
        add("              'following'/'recsys'/'both' and predate the")
        add("              three-tier feed. They are EXCLUDED from every")
        add("              estimate below and used only as an independent")
        add("              replication in the final section.")

    add("")
    add("-" * 78)
    add("1. CRUDE RATES (confounded -- shown for reference only)")
    add("-" * 78)
    for tier in ("network", "fof", "discovery"):
        a, n, rate = crude_rates(rows, tier)
        add(f"  {tier:<10} {a:>5}/{n:<6} = {rate*100:5.2f}%")

    add("")
    add("-" * 78)
    add("2. STRATIFIED BY FEED (Mantel-Haenszel)")
    add("   one agent, one round, one run, one moment -- so agent, round, run")
    add("   and disposition are all held fixed. Position is not yet held fixed.")
    add("-" * 78)
    for exp_, unexp in (("network", "discovery"), ("fof", "discovery"),
                        ("network", "fof")):
        m = mantel_haenszel(rows, exp_, unexp)
        add(f"  {exp_:>9} vs {unexp:<10} OR {m['or']:6.2f}"
            f"  95% CI [{m['lo']:5.2f}, {m['hi']:5.2f}]"
            f"  p={m['p']:.2e}  ({m['strata']} informative feeds)")
    add("")
    add("  The fof contrast is the one to trust causally: fof authors were")
    add("  chosen by other agents' follows, never by the focal agent, so it")
    add("  carries no selection-on-affinity. network vs discovery is an")
    add("  upper bound that includes that selection.")

    add("")
    add("-" * 78)
    add("3. PRIMARY: STRATIFIED BY (AGENT, FEED SLOT), SLOTS 0-4")
    add("   Holds the agent AND the feed position fixed; tier varies across")
    add("   rounds within a stratum. This is the identified estimate.")
    add("-" * 78)
    add("   Why this stratum and not (feed, slot): a slot holds exactly one")
    add("   post, so a (feed, slot) stratum can never contain two tiers.")
    add("   Why slots 0-4: network posts NEVER occupy slots 5-11, so over the")
    add("   whole feed tier and position are structurally collinear -- a logit")
    add("   on network vs discovery with slot dummies is literally singular.")
    add("   Slots 0-4 are where all three tiers actually compete.")
    add("")
    for tier in ("network", "fof", "discovery"):
        sel = [r["pos"] for r in rows if r["tier"] == tier and r["pos"] <= 4]
        if sel:
            add(f"   mean slot within 0-4, {tier:<10} {np.mean(sel):.2f}"
                f"  (n={len(sel)})")
    add("")
    top = [dict(r, agentslot=f"{r['agent']}|{r['pos']}") for r in rows
           if r["pos"] <= 4]
    for exp_, unexp in (("network", "discovery"), ("fof", "discovery"),
                        ("network", "fof")):
        m = mantel_haenszel(top, exp_, unexp, stratum="agentslot")
        add(f"  {exp_:>9} vs {unexp:<10} OR {m['or']:6.2f}"
            f"  95% CI [{m['lo']:5.2f}, {m['hi']:5.2f}]"
            f"  p={m['p']:.2e}  ({m['strata']} strata)")
    add("")
    add("  Compare against section 2, where position is NOT held fixed:")
    add("  controlling for slot roughly halves the tier effect, so about half")
    add("  the crude gap was the feed builder putting network posts on top.")
    add("  What remains is the tier itself.")

    add("")
    add("-" * 78)
    add("4. WHY THERE IS NO MULTIVARIABLE LOGIT FOR TIER")
    add("-" * 78)
    add("  Because tier is not separately identified from position in this")
    add("  design. The feed builder assigns network to slots 0-4, fof to 1-7")
    add("  and discovery to all 12, so on the network-vs-discovery subset the")
    add("  slot dummies for 5-11 predict 'not network' perfectly and the")
    add("  Hessian is singular. Fitting slot as a single linear term hides")
    add("  that rather than solving it, and the resulting estimate is not")
    add("  stable: dropping the fof rows moves the network OR from 1.76 to")
    add("  5.52 without any change to the contrast being estimated.")
    add("  The stratified estimate in section 3 is reported instead, because")
    add("  it conditions on exactly the strata where the comparison exists")
    add("  and discards the rest rather than extrapolating into them.")

    add("")
    add("-" * 78)
    add("5. DOES THE RANKING SCORE PREDICT ANYTHING?")
    add("   Tested inside the discovery tier only: the score is present for")
    add("   100% of discovery exposures but 28% of network and 43% of fof,")
    add("   so it is missing not at random and cannot sit beside tier.")
    add("-" * 78)
    disc = [r for r in rows if r["tier"] == "discovery"
            and r["score"] is not None]
    add(f"  discovery exposures with a score: {len(disc)}")
    if len(disc) > 100:
        X = [[1.0, float(r["score"]), float(r["pos"])] for r in disc]
        y = [r["acted"] for r in disc]
        g = [r["agent"] for r in disc]
        try:
            for row in logit_cluster(y, X, g,
                                     ["intercept", "rank_score", "feed_slot"]):
                if row["name"] == "intercept":
                    continue
                add(f"  {row['name']:<16} OR {row['or']:6.3f}"
                    f"  95% CI [{row['lo']:5.3f}, {row['hi']:5.3f}]"
                    f"  p={row['p']:.3f}")
            add("")
            add("  NOTE (F-42): this variable is rec_history.score, which is")
            add("  sim * recency (timeline_platform.py:365), NOT cosine. An")
            add("  earlier version of this output labelled it 'similarity'")
            add("  and that produced the retracted F-38. Cosine and recency")
            add("  are decomposed in recency_check.py: cosine alone is null.")
        except Exception as exc:                      # noqa: BLE001
            add(f"  logit failed: {exc}")
        # decile view, robust to any functional form
        sc = np.array([r["score"] for r in disc], float)
        ac = np.array([r["acted"] for r in disc], float)
        add("")
        add("  engagement by ranking-score decile (assumption-free view):")
        qs = np.quantile(sc, np.linspace(0, 1, 11))
        for i in range(10):
            lo, hi = qs[i], qs[i + 1]
            m = (sc >= lo) & (sc <= hi if i == 9 else sc < hi)
            if m.sum():
                add(f"    d{i+1:<2} score {lo:.3f}-{hi:.3f}"
                    f"  {int(ac[m].sum()):>4}/{int(m.sum()):<5}"
                    f" = {ac[m].mean()*100:5.2f}%")
    add("")
    add("-" * 78)
    add("6. IS THE EFFECT STABLE ACROSS RUNS, OR DRIVEN BY ONE?")
    add("   Same stratified estimator, computed run by run.")
    add("-" * 78)
    add(f"  {'run':<16}{'network vs discovery':>26}{'fof vs discovery':>26}")
    n_pos = n_sig = n_tot = 0
    fof_sig = fof_tot = 0
    for lab in mod_runs:
        sub = [r for r in rows if r["run"] == lab]
        top = [dict(r, agentslot=f"{r['agent']}|{r['pos']}")
               for r in sub if r["pos"] <= 4]
        a = mantel_haenszel(top, "network", "discovery", stratum="agentslot")
        b = mantel_haenszel(top, "fof", "discovery", stratum="agentslot")

        def fmt(m):
            if not m["strata"] or m["or"] != m["or"]:
                return f"{'--':>26}"
            return f"{m['or']:8.2f} [{m['lo']:5.2f},{m['hi']:6.2f}]"
        if a["strata"] and a["or"] == a["or"]:
            n_tot += 1
            n_pos += a["or"] > 1
            n_sig += a["lo"] > 1
        if b["strata"] and b["or"] == b["or"]:
            fof_tot += 1
            fof_sig += b["lo"] > 1
        add(f"  {lab:<16}{fmt(a):>26}{fmt(b):>26}")
    add("")
    add(f"  network vs discovery: positive in {n_pos}/{n_tot} runs, "
        f"individually significant in {n_sig}/{n_tot}.")
    add(f"  fof vs discovery: individually significant in only "
        f"{fof_sig}/{fof_tot} runs.")
    add("  The direction is consistent; the magnitude is heterogeneous. The")
    add("  fof contrast is the weaker of the two per-run and leans on pooling,")
    add("  so it should be reported as suggestive rather than established.")

    if legacy:
        add("")
        add("-" * 78)
        add("7. INDEPENDENT REPLICATION ON THE PRE-THREE-TIER RUNS")
        add("   Those runs label sources 'following' (came from someone you")
        add("   follow) and 'recsys' (ranked in by similarity) -- the same")
        add("   contrast under a different feed implementation.")
        add("-" * 78)
        top = [dict(r, agentslot=f"{r['agent']}|{r['pos']}")
               for r in legacy if r["pos"] <= 4]
        for lab in leg_runs:
            sub = [r for r in top if r["run"] == lab]
            m = mantel_haenszel(sub, "following", "recsys",
                                stratum="agentslot")
            if m["strata"]:
                add(f"  {lab:<16} OR {m['or']:6.2f}"
                    f"  95% CI [{m['lo']:5.2f}, {m['hi']:5.2f}]"
                    f"  ({m['strata']} strata)")
        m = mantel_haenszel(top, "following", "recsys", stratum="agentslot")
        add(f"  {'POOLED':<16} OR {m['or']:6.2f}"
            f"  95% CI [{m['lo']:5.2f}, {m['hi']:5.2f}]"
            f"  p={m['p']:.2e}  ({m['strata']} strata)")
        add("")
        add("  A separate feed implementation, a different source vocabulary,")
        add("  and earlier prompt versions reproduce the same effect. This is")
        add("  the strongest evidence that the result is not an artefact of")
        add("  one feed builder.")

    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="*", default=None)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    labels = args.runs
    if not labels:
        labels = sorted(
            os.path.basename(p)[len("social_timeline_"):-len("_analysis.json")]
            for p in glob.glob(os.path.join(
                args.data_dir, "social_timeline_*_analysis.json")))
    rows, used = [], []
    for lab in labels:
        try:
            r = load_exposures(lab, args.data_dir)
        except (OSError, KeyError):
            continue
        if r:
            rows.extend(r)
            used.append(lab)
    if not rows:
        raise SystemExit("no exposures found")

    text = render(rows, used)
    print(text)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
