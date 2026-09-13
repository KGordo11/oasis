"""Refuse a campaign whose configuration has drifted from its reference runs.

WHY THIS EXISTS
---------------
On 2026-09-13, the command drafted for an 8.5-hour agent sweep did not pass
`--temperature 0.7`. Every previous run in that family had it, because every
shell script in this directory passes it explicitly -- but the bare CLI default
is 0.9, changed in `30e6144` on 2026-08-30 and never reconciled. The sweep would
have run all night at 0.9 and been comparable with nothing: not with
ctx8192_a12/24/36 whose cost curve it was extending, and not with the 28-run
bank.

It was caught by running a 4-agent smoke and diffing its manifest against a
reference run's. That took thirty seconds. This module is that check, made
routine, because the failure mode is the one this project keeps repeating:

    B-26  --agents silently truncated to the persona file
    B-28  the server silently truncated the prompt
    here  the CLI silently sampled at a different temperature

None of the three raises. None of them is slower. Each one just quietly stops
being the experiment that was asked for, and the resulting run is indis-
tinguishable from a real one afterwards.

WHAT IT COMPARES
----------------
The `config` block of a candidate manifest against a reference run's, minus the
keys that are *supposed* to differ between runs in one family.

Keys absent from the reference but present in the candidate are reported
separately and do not fail by default: the manifest schema grows over time
(`shuffle_feed` was added on 2026-09-12), and a new key with an inert default is
not drift. A key whose VALUE differs always fails.
"""
import json
import os

# Keys that legitimately differ between two runs of the same family.
VARIES = frozenset({
    "agents",                       # the sweep's independent variable
    "rounds",                       # set per phase
    "label",                        # names the run
    "seed",                         # may be varied for replicates
    "persona_separability",         # derived from the agent count
    "ollama_server_state",          # observed, not configured
    "ollama_num_parallel_client_env",
})


def load_config(path):
    """Read a manifest's config block. Accepts a manifest path or a run label."""
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("config", {})


def find_manifest(label, search_roots):
    """Locate a run's manifest by label, trying each root in order."""
    names = [
        os.path.join("{root}", "parquet", label, "manifest.json"),
        os.path.join("{root}", f"social_timeline_{label}.json"),
        os.path.join("{root}", "runs", "published", f"social_timeline_{label}.json"),
        os.path.join("{root}", "runs", "control", f"social_timeline_{label}.json"),
    ]
    for root in search_roots:
        for pat in names:
            p = pat.format(root=root)
            if os.path.exists(p):
                return p
    return None


def compare(candidate, reference, ignore=VARIES):
    """Return (drift, new_keys, compared).

    drift     — keys present in both whose values differ. These are failures.
    new_keys  — keys the candidate has and the reference does not. Reported,
                not fatal: the manifest schema grows.
    compared  — how many keys were actually checked, so a vacuous pass is
                visible rather than silent.
    """
    drift, new_keys, compared = [], [], 0
    for k in sorted(set(candidate) | set(reference)):
        if k in ignore:
            continue
        if k not in reference:
            new_keys.append((k, candidate[k]))
            continue
        compared += 1
        if candidate.get(k) != reference.get(k):
            drift.append((k, candidate.get(k), reference.get(k)))
    return drift, new_keys, compared


def verify(candidate_path, reference_path, min_compared=10):
    """Human-readable verdict. Returns (ok, lines)."""
    cand, ref = load_config(candidate_path), load_config(reference_path)
    drift, new_keys, compared = compare(cand, ref)
    lines = []
    for k, v in new_keys:
        lines.append(f"  new key (not drift)  {k} = {v!r}")
    for k, a, b in drift:
        lines.append(f"  DRIFT  {k}: this run {a!r}  <>  reference {b!r}")
    if compared < min_compared:
        lines.append(f"  REFUSING: only {compared} keys compared, expected "
                     f">= {min_compared}. The reference manifest looks wrong.")
        return False, lines
    if drift:
        lines.append(f"  {len(drift)} key(s) drifted from "
                     f"{os.path.basename(os.path.dirname(reference_path))}. "
                     f"This campaign would not be comparable to it.")
        return False, lines
    lines.append(f"  OK: {compared} config keys identical to the reference run.")
    return True, lines


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(
        description="Refuse a campaign whose config drifted from its reference.")
    p.add_argument("--candidate", required=True,
                   help="manifest of a smoke run made with tonight's flags")
    p.add_argument("--reference", required=True,
                   help="manifest (or label) of the run this must match")
    p.add_argument("--data-root", default=None,
                   help="where to look up a reference given as a label")
    a = p.parse_args(argv)

    ref = a.reference
    if not os.path.exists(ref):
        roots = [a.data_root] if a.data_root else []
        here = os.path.dirname(os.path.abspath(__file__))
        roots.append(os.path.join(here, "..", "..", "..", "data"))
        found = find_manifest(ref, [os.path.abspath(r) for r in roots])
        if not found:
            print(f"  REFUSING: no manifest found for reference {ref!r}")
            return 2
        ref = found

    ok, lines = verify(a.candidate, ref)
    print(f"--- config comparability vs {ref}")
    for ln in lines:
        print(ln)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
