"""Q-14: is the F-35 noise floor real, or an artefact of one replicate pair?

IN PLAIN WORDS
--------------
This measures HOW MUCH RESULTS MOVE WHEN YOU CHANGE NOTHING AT ALL.

If you run the exact same simulation twice, you do not get the same answer --
the AI makes different choices each time. That wobble sets a floor: any change
you make to the simulation has to move things by MORE than the wobble, or you
can never tell whether your change did anything.

We first measured that wobble using a single pair of identical runs, which is
thin evidence for such an important number. This file remeasures it using six
identical runs, which gives fifteen pairs instead of one.

WHY IT MATTERS
--------------
F-35 used the single v10_register/v10_replicate pair to conclude that the
run-to-run SD for posting share is ~30.7 pp, and that the four prompt
interventions -- which moved things 3-5 pp -- were therefore unfalsifiable
rather than merely unsupported. That conclusion reshaped the whole project,
so the number behind it deserves more than one pair (recorded as Q-14).

Six runs at one identical configuration (prompt v10, temperature 0.9) make all
fifteen pairwise comparisons available. If the single-pair figure sits inside
the spread of the fifteen, F-35 stands.

METHOD
------
For each run, each agent's share of its OWN chosen actions is computed --
`refresh`, `sign_up` and `do_nothing` are excluded, since they are not content
choices. Agents are paired across runs by id, which is valid because
`select_diverse` is deterministic and persona #7 is agent 7 in every run. The
paired standard deviation is then taken for every pair of runs.

Usage:
    noise_floor.py
    noise_floor.py --runs v10_register v10_replicate --out data/nf.txt
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import statistics as st

# The six runs sharing one identical configuration: prompt v10, temperature
# 0.9, seed 0, 36 agents, 15 rounds, twhin-bert, --no-groups. Verified against
# every manifest before use.
IDENTICAL_RUNS = ("v10_register", "v10_replicate",
                  "v10_rep3", "v10_rep4", "v10_rep5", "v10_rep6")

# Actions that represent a real content choice. refresh/sign_up/do_nothing are
# bookkeeping, not decisions about what to say or who to follow.
ACTIONS = ("create_post", "create_comment", "like_post", "follow")
NOT_A_CHOICE = ("refresh", "sign_up", "do_nothing")


def agent_shares(label, data_dir="data"):
    """For one run, each agent's percentage split across the tracked actions."""
    path = os.path.join(data_dir, f"social_timeline_{label}_analysis.json")
    with open(path) as fh:
        d = json.load(fh)
    out = {}
    for aid, ag in d["agents"].items():
        counts = ag.get("action_counts") or {}
        chosen = {k: v for k, v in counts.items() if k not in NOT_A_CHOICE}
        total = sum(chosen.values())
        if total:
            out[int(aid)] = {a: chosen.get(a, 0) / total * 100 for a in ACTIONS}
    return out


def paired_sd(sa, sb, action):
    """Standard deviation of the per-agent difference between two runs.

    Pairing on agent id removes the agent's own disposition, which is the
    largest source of variation (ICC up to 0.38). What is left is run-to-run
    noise, which is exactly what we are trying to measure.
    """
    common = set(sa) & set(sb)
    diffs = [sa[i][action] - sb[i][action] for i in common]
    return st.stdev(diffs) if len(diffs) > 2 else None


def render(shares, labels):
    L = []
    add = L.append
    add("=" * 78)
    add("Q-14: THE NOISE FLOOR, MEASURED ACROSS SIX IDENTICAL RUNS")
    add("=" * 78)
    add(f"runs            : {len(labels)}  ({', '.join(labels)})")
    add(f"agents per run  : {[len(shares[r]) for r in labels]}")
    add(f"pairs available : {len(list(itertools.combinations(labels, 2)))}")
    add("")
    add("Every run here shares one identical configuration, so any difference")
    add("between them is noise by construction -- nothing was changed.")
    add("")
    add("-" * 78)
    add("PAIRED SD PER ACTION, OVER ALL PAIRS")
    add("-" * 78)
    add(f"  {'action':<18}{'pairs':>6}{'mean SD':>10}{'min':>9}{'max':>9}")
    results = {}
    for a in ACTIONS:
        sds = [s for x, y in itertools.combinations(labels, 2)
               if (s := paired_sd(shares[x], shares[y], a)) is not None]
        if not sds:
            continue
        results[a] = sds
        add(f"  {a:<18}{len(sds):>6}{st.mean(sds):>9.1f}%"
            f"{min(sds):>8.1f}%{max(sds):>8.1f}%")

    add("")
    add("-" * 78)
    add("DOES THE ORIGINAL SINGLE-PAIR FIGURE (F-35) STAND?")
    add("-" * 78)
    if "v10_register" in shares and "v10_replicate" in shares:
        add("  F-35 used only the v10_register / v10_replicate pair:")
        add(f"  {'action':<18}{'that pair':>11}{'range of all pairs':>22}"
            f"{'inside?':>10}")
        for a in ACTIONS:
            one = paired_sd(shares["v10_register"], shares["v10_replicate"], a)
            if one is None or a not in results:
                continue
            lo, hi = min(results[a]), max(results[a])
            inside = "yes" if lo <= one <= hi else "NO"
            add(f"  {a:<18}{one:>10.1f}%{f'{lo:.1f}% - {hi:.1f}%':>22}"
                f"{inside:>10}")
        add("")
        add("  If every single-pair figure falls inside the spread of all")
        add("  fifteen pairs, the F-35 noise floor is confirmed rather than")
        add("  a lucky draw, and the conclusion built on it stands.")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="*", default=list(IDENTICAL_RUNS))
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    shares, used = {}, []
    for lab in args.runs:
        try:
            shares[lab] = agent_shares(lab, args.data_dir)
            used.append(lab)
        except (OSError, KeyError):
            continue
    if len(used) < 2:
        raise SystemExit("need at least two runs")

    text = render(shares, used)
    print(text)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
