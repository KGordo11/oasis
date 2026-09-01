"""Is F-38's anti-predictive 'similarity' actually a recency effect? (Q-10)

WHY THIS EXISTS
---------------
F-38 reported that the TwHIN similarity score is mildly ANTI-predictive of
engagement -- OR 0.305 [0.164, 0.568] "per unit cosine" -- and that claim is
the most surprising one in the write-up while having no mechanism behind it.
Q-10 asked whether it is really a staleness effect: the ranker blends
similarity with recency, so if high-similarity posts are systematically older,
a recency effect would be misread as a similarity effect.

The confound turns out to be more direct than that. The variable F-38 modelled
is not cosine at all:

    rec_candidates.score = sim * recency          (timeline_platform.py:365)
    rec_history.score    = rec_candidates.score   (timeline_platform.py:699-701)
    exposure_model.load_exposures reads rec_history.score and labels it
    "similarity ... per unit cosine"              (exposure_model.py:80, output §5)

So the F-38 regressor is the blended ranking score. The tell is in F-38's own
decile table, whose bottom bin is "sim 0.000-0.387": raw cosine in these runs
never falls below 0.198, but `recency` clamps to RECENCY_FLOOR = 1e-6 for posts
past the age cliff (timeline_platform.py:299-301), which drives the *product*
to ~0 for stale posts regardless of how similar they are.

WHAT THIS SCRIPT DOES
---------------------
Joins each exposure back to `rec_candidates` to recover `sim` and `recency`
separately, then re-asks the F-38 question with the two terms pulled apart:

  1. Reproduces F-38 exactly, on `score`, as a control that the pipeline here
     matches the published number.
  2. Measures the sim/recency relationship -- the confound Q-10 hypothesised.
  3. Engagement by *cosine* decile and by recency level, assumption-free.
  4. Cluster-robust logits: score alone, sim alone, recency alone, and both
     together, each with feed slot, clustered by agent exactly as F-38 was.
  5. The sim effect within each recency level, so recency is held fixed by
     stratification rather than by functional form.

Everything reuses `logit_cluster` and the loading conventions of
exposure_model.py (gated by test_exposure_model.py) rather than re-deriving
them -- hand-rolled statistics are what produced F-30 and F-32.

Discovery tier only, for F-38's own reason: the score is present for 100% of
discovery exposures but 28% of network and 43% of fof, so it is missing not at
random and cannot sit in a model beside tier.

Usage:
    recency_check.py                        # the five three-tier runs
    recency_check.py --runs baseline v8_full
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from collections import defaultdict

import numpy as np

from exposure_model import logit_cluster, mantel_haenszel

# The five runs that use the three-tier feed (exposure_model.py MODERN).
# Older runs predate it and cannot contribute to a discovery-tier estimate.
DEFAULT_RUNS = ("baseline", "v10_register", "v10_replicate",
                "v8_full", "v9_feedback")


def load_scored_exposures(label, data_dir="data"):
    """One row per discovery exposure, with `sim` and `recency` recovered
    separately from rec_candidates.

    The `acted` flag is built exactly as exposure_model.load_exposures builds
    it, from the analysis JSON's seen_and_acted, so the two scripts are
    answering the same question about the same events.
    """
    apath = os.path.join(data_dir, f"social_timeline_{label}_analysis.json")
    with open(apath) as fh:
        d = json.load(fh)
    acted = {(int(a), int(p))
             for a, ag in d["agents"].items()
             for p in (ag.get("seen_and_acted") or [])}

    dbpath = os.path.join(data_dir, f"social_timeline_{label}.db")
    conn = sqlite3.connect(dbpath)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("""
        SELECT h.round, h.agent_id, h.post_id, h.feed_position, h.source,
               h.score, c.sim, c.recency
          FROM rec_history h
          LEFT JOIN rec_candidates c
                 ON c.round = h.round
                AND c.agent_id = h.agent_id
                AND c.post_id = h.post_id
         ORDER BY h.round, h.agent_id, h.feed_position
    """)
    rows = []
    for r in cur:
        aid, pid = int(r["agent_id"]), int(r["post_id"])
        rows.append({
            "run": label,
            "agent": f"{label}|{aid}",
            "feed": f"{label}|{aid}|{r['round']}",
            "round": int(r["round"]),
            "post": pid,
            "tier": r["source"],
            "pos": int(r["feed_position"]),
            "score": r["score"],
            "sim": r["sim"],
            "recency": r["recency"],
            "acted": int((aid, pid) in acted),
        })
    conn.close()

    # Prior sightings of the same (agent, post), in chronological order over
    # the WHOLE feed, not just the discovery tier -- an agent who met a post
    # through a follow has still met it. This is what section 7 tests.
    seen = defaultdict(int)
    for r in sorted(rows, key=lambda x: (x["round"], x["agent"], x["pos"])):
        k = (r["agent"], r["post"])
        r["prior"] = seen[k]
        seen[k] += 1
    return rows


def decile_table(rows, key, n_bins=10):
    """Assumption-free engagement rate by bin of `key`.

    Bins on distinct-value quantiles. `recency` takes only 5-10 distinct
    values per run because it is a deterministic function of post age in
    rounds, so equal-count deciles are impossible for it and equal-value
    groups are used instead.
    """
    vals = sorted(r[key] for r in rows)
    distinct = sorted({r[key] for r in rows})
    if len(distinct) <= n_bins:
        groups = [(v, v, [r for r in rows if r[key] == v]) for v in distinct]
    else:
        edges = [vals[int(i * len(vals) / n_bins)] for i in range(n_bins)]
        edges.append(vals[-1])
        groups = []
        for i in range(n_bins):
            lo, hi = edges[i], edges[i + 1]
            if i == n_bins - 1:
                sel = [r for r in rows if lo <= r[key] <= hi]
            else:
                sel = [r for r in rows if lo <= r[key] < hi]
            groups.append((lo, hi, sel))
    out = []
    for lo, hi, sel in groups:
        n = len(sel)
        a = sum(r["acted"] for r in sel)
        out.append({"lo": lo, "hi": hi, "n": n, "acted": a,
                    "rate": (a / n if n else float("nan"))})
    return out


def fit(rows, terms):
    """Cluster-robust logit of `acted` on `terms` + feed slot + intercept,
    clustered by agent -- the same specification F-38 used."""
    y = [r["acted"] for r in rows]
    X = [[1.0] + [float(r[t]) for t in terms] + [float(r["pos"])]
         for r in rows]
    names = ["intercept"] + list(terms) + ["feed_slot"]
    return logit_cluster(y, X, [r["agent"] for r in rows], names)


def fmt_fit(res, skip_intercept=True):
    L = []
    for t in res:
        if skip_intercept and t["name"] == "intercept":
            continue
        L.append(f"    {t['name']:<14} OR {t['or']:6.3f}"
                 f"  95% CI [{t['lo']:6.3f}, {t['hi']:6.3f}]"
                 f"  p={t['p']:.3g}")
    return L


def render(rows, labels):
    L = []
    add = L.append

    disc = [r for r in rows
            if r["tier"] == "discovery" and r["score"] is not None
            and r["sim"] is not None and r["recency"] is not None]

    add("=" * 78)
    add("Q-10: IS F-38'S ANTI-PREDICTIVE 'SIMILARITY' A RECENCY EFFECT?")
    add("=" * 78)
    add(f"runs             : {len(labels)}  ({', '.join(labels)})")
    add(f"discovery rows   : {len(disc)} with sim, recency and score all present")
    add(f"agents (clusters): {len({r['agent'] for r in disc})}")
    add(f"engaged          : {sum(r['acted'] for r in disc)}")
    add("")
    add("The variable F-38 called 'similarity' is rec_history.score, which is")
    add("sim * recency (timeline_platform.py:365, 699-701) -- not cosine.")

    add("")
    add("-" * 78)
    add("1. CONTROL: F-38 REPRODUCED ON `score`")
    add("   Should match the published OR 0.305 [0.164, 0.568]. If it does,")
    add("   every difference below is the decomposition and not the pipeline.")
    add("-" * 78)
    L.extend(fmt_fit(fit(disc, ["score"])))

    add("")
    add("-" * 78)
    add("2. THE CONFOUND Q-10 HYPOTHESISED: ARE SIMILAR POSTS OLDER?")
    add("-" * 78)
    sim = np.array([r["sim"] for r in disc])
    rec = np.array([r["recency"] for r in disc])
    sco = np.array([r["score"] for r in disc])
    add(f"  corr(sim, recency)   {np.corrcoef(sim, rec)[0, 1]:+.3f}")
    add(f"  corr(sim, score)     {np.corrcoef(sim, sco)[0, 1]:+.3f}")
    add(f"  corr(recency, score) {np.corrcoef(rec, sco)[0, 1]:+.3f}")
    add("")
    add(f"  sim      range {sim.min():.3f} - {sim.max():.3f}   "
        f"mean {sim.mean():.3f}  sd {sim.std():.3f}")
    add(f"  recency  range {rec.min():.6f} - {rec.max():.3f}   "
        f"mean {rec.mean():.3f}  sd {rec.std():.3f}  "
        f"({len(set(rec.tolist()))} distinct values)")
    add(f"  score    range {sco.min():.6f} - {sco.max():.3f}   "
        f"mean {sco.mean():.3f}  sd {sco.std():.3f}")
    add("")
    add("  mean cosine within each recency level:")
    for v in sorted(set(rec.tolist())):
        sel = [r for r in disc if r["recency"] == v]
        s = np.array([r["sim"] for r in sel])
        add(f"    recency {v:9.6f}  n={len(sel):>6}  mean sim {s.mean():.3f}")

    add("")
    add("-" * 78)
    add("3. ASSUMPTION-FREE: ENGAGEMENT BY COSINE, AND BY RECENCY")
    add("-" * 78)
    add("  by cosine decile (this is the variable F-38 claimed to describe):")
    for i, b in enumerate(decile_table(disc, "sim"), 1):
        add(f"    d{i:<2} sim {b['lo']:.3f}-{b['hi']:.3f}  "
            f"{b['acted']:>4}/{b['n']:<5} = {b['rate']*100:5.2f}%")
    add("")
    add("  by recency level (deterministic in post age, so these are age bins;")
    add("  1e-06 is the clamp floor for posts past the age cliff):")
    for b in decile_table(disc, "recency"):
        add(f"    recency {b['lo']:9.6f}  "
            f"{b['acted']:>4}/{b['n']:<5} = {b['rate']*100:5.2f}%")
    add("")
    add("  by blended-score decile (F-38's published table, for comparison):")
    for i, b in enumerate(decile_table(disc, "score"), 1):
        add(f"    d{i:<2} score {b['lo']:.3f}-{b['hi']:.3f}  "
            f"{b['acted']:>4}/{b['n']:<5} = {b['rate']*100:5.2f}%")

    add("")
    add("-" * 78)
    add("4. THE TERMS PULLED APART (cluster-robust logit, clustered by agent)")
    add("-" * 78)
    add("  cosine alone:")
    L.extend(fmt_fit(fit(disc, ["sim"])))
    add("  recency alone:")
    L.extend(fmt_fit(fit(disc, ["recency"])))
    add("  both together:")
    L.extend(fmt_fit(fit(disc, ["sim", "recency"])))

    add("")
    add("-" * 78)
    add("5. COSINE WITHIN EACH RECENCY LEVEL")
    add("   Recency held fixed by stratification rather than functional form.")
    add("   A level needs both variation in cosine and some engagement to be")
    add("   informative; the rest are reported as uninformative, not dropped")
    add("   silently.")
    add("-" * 78)
    for v in sorted(set(rec.tolist())):
        sel = [r for r in disc if r["recency"] == v]
        n_acted = sum(r["acted"] for r in sel)
        if len(sel) < 200 or n_acted < 10 or len({r["agent"] for r in sel}) < 5:
            add(f"  recency {v:9.6f}  n={len(sel):>6}  acted={n_acted:<4} "
                f"-- too thin to fit")
            continue
        try:
            res = fit(sel, ["sim"])
        except Exception as exc:                       # noqa: BLE001
            add(f"  recency {v:9.6f}  n={len(sel):>6}  did not converge: {exc}")
            continue
        t = [x for x in res if x["name"] == "sim"][0]
        add(f"  recency {v:9.6f}  n={len(sel):>6}  acted={n_acted:<4} "
            f"sim OR {t['or']:7.3f}  [{t['lo']:6.3f}, {t['hi']:7.3f}]  "
            f"p={t['p']:.3g}")

    add("")
    add("-" * 78)
    add("6. IS THE RECENCY EFFECT ITSELF JUST A ROUND EFFECT?")
    add("   A post can only be old in a late round, so post age is entangled")
    add("   with round, and engagement varies by round. Stratifying on the")
    add("   FEED (one agent, one round, one run, twelve posts seen at the same")
    add("   instant) holds round, agent and run fixed by construction, exactly")
    add("   as the tier estimate in exposure_model.py section 3 does.")
    add("-" * 78)
    add("  raw engagement rate by round (the thing that could confound it):")
    by_round = defaultdict(lambda: [0, 0])
    for r in disc:
        b = by_round[r["round"]]
        b[0] += r["acted"]
        b[1] += 1
    for rd in sorted(by_round):
        a, n = by_round[rd]
        add(f"    round {rd:>3}   {a:>4}/{n:<5} = {a/n*100:5.2f}%")

    fresh = max(rec.tolist())
    add("")
    add(f"  'fresh' = newest recency level ({fresh:.6f}, age 0); "
        f"'stale' = every older level.")
    mh_rows = [{**r,
                "tier": "stale" if r["recency"] < fresh else "fresh"}
               for r in disc]
    m = mantel_haenszel(mh_rows, "stale", "fresh", stratum="feed")
    add(f"    stale vs fresh, stratified by feed   OR {m['or']:6.3f}"
        f"  95% CI [{m['lo']:6.3f}, {m['hi']:6.3f}]"
        f"  p={m['p']:.3g}  ({m['strata']} informative feeds)")
    m2 = mantel_haenszel(mh_rows, "stale", "fresh", stratum="agent")
    add(f"    stale vs fresh, stratified by agent  OR {m2['or']:6.3f}"
        f"  95% CI [{m2['lo']:6.3f}, {m2['hi']:6.3f}]"
        f"  p={m2['p']:.3g}  ({m2['strata']} informative agents)")
    add("")
    add("  If the feed-stratified OR stays well above 1, older posts really do")
    add("  draw more engagement than fresh ones seen in the same feed, and the")
    add("  round cannot be the explanation. If it collapses toward 1, the")
    add("  recency effect was a round effect.")

    add("")
    add("-" * 78)
    add("7. THE MECHANISM: IT IS NOT AGE, IT IS REPEAT EXPOSURE")
    add("   A post can only be old and still in a feed if it has been")
    add("   circulating, which means the agent has probably already seen it.")
    add("   Age and prior sightings are therefore almost the same variable.")
    add("   `prior` counts earlier sightings of this (agent, post) across the")
    add("   whole feed, not just this tier.")
    add("-" * 78)
    for t, sel in (("fresh", [r for r in disc if r["recency"] >= fresh]),
                   ("stale", [r for r in disc if r["recency"] < fresh])):
        pri = [r["prior"] for r in sel]
        firsts = sum(1 for p in pri if p == 0)
        add(f"  {t:<6} n={len(sel):>6}  mean prior sightings "
            f"{sum(pri)/len(pri):5.2f}   first-sighting share "
            f"{firsts/len(sel)*100:5.1f}%")
    add("")
    add("  A fresh post is a first sighting by construction, so 'fresh vs")
    add("  stale' was largely 'never seen before vs seen before'.")
    add("")
    add("  engagement by number of prior sightings (discovery):")
    by_prior = defaultdict(lambda: [0, 0])
    for r in disc:
        b = by_prior[min(r["prior"], 5)]
        b[0] += r["acted"]
        b[1] += 1
    for k in sorted(by_prior):
        a, n = by_prior[k]
        add(f"    prior={('5+' if k >= 5 else str(k)):<3} {a:>4}/{n:<6} "
            f"= {a/n*100:5.2f}%")
    add("")
    rep = [{**r, "tier": "repeat" if r["prior"] >= 1 else "first"}
           for r in disc]
    for stratum, note in (("feed", "agent+round+run fixed by construction"),
                          ("agent", "agent fixed, pools across rounds")):
        m = mantel_haenszel(rep, "repeat", "first", stratum=stratum)
        add(f"    seen-before vs first sighting, by {stratum:<5} "
            f"OR {m['or']:6.3f}  [{m['lo']:6.3f}, {m['hi']:6.3f}]"
            f"  p={m['p']:.3g}  ({m['strata']} strata, {note})")
    add("")
    add("  The decisive test -- re-run stale vs fresh inside FIRST SIGHTINGS")
    add("  only, where the repeat-exposure channel is closed by construction:")
    only_first = [r for r in disc if r["prior"] == 0]
    mf = mantel_haenszel(
        [{**r, "tier": "stale" if r["recency"] < fresh else "fresh"}
         for r in only_first], "stale", "fresh", stratum="feed")
    add(f"    stale vs fresh | first sightings only  OR {mf['or']:6.3f}"
        f"  [{mf['lo']:6.3f}, {mf['hi']:6.3f}]  p={mf['p']:.3g}"
        f"  ({mf['strata']} feeds, n={len(only_first)})")
    add("")
    add("  Independent replication in the NETWORK tier, where the similarity")
    add("  score plays no part in the feed at all:")
    net = [{**r, "tier": "repeat" if r["prior"] >= 1 else "first"}
           for r in rows if r["tier"] == "network"]
    if net:
        mn = mantel_haenszel(net, "repeat", "first", stratum="feed")
        add(f"    seen-before vs first sighting, by feed  OR {mn['or']:6.3f}"
            f"  [{mn['lo']:6.3f}, {mn['hi']:6.3f}]  p={mn['p']:.3g}"
            f"  ({mn['strata']} feeds, n={len(net)})")
    add("")
    add("  CAVEAT, and it is a real one: prior sightings are not randomly")
    add("  assigned. A post is re-shown because the ranker kept choosing it,")
    add("  so repeat-exposure status is an outcome of the same system whose")
    add("  effect is being estimated. Feed stratification fixes the agent,")
    add("  the round and the run, but not selection into being re-shown.")
    add("  The dose-response and the network-tier replication are what make")
    add("  the reading credible; neither makes it experimental.")

    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="*", default=list(DEFAULT_RUNS))
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    rows, used = [], []
    for lab in args.runs:
        try:
            r = load_scored_exposures(lab, args.data_dir)
        except (OSError, KeyError, sqlite3.Error):
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
