"""How much does a model agree with ITSELF? (Context for LF-15/16: llama vs gemma agree only kappa 0.21.)

IN PLAIN WORDS
--------------
A retest world re-runs the same people on the same posts with the same model, changing only the
random draw (run_world.py --draw 1). Comparing it with the original world gives each model's
agreement with itself. If a model only agrees with itself, say, 70 % of the time, then two
different models agreeing 64 % is not so far off; if it agrees with itself 95 %, the gap between
models is real.

    python retest_compare.py --orig v2_s13_w0,v2_s13_w1 --retest rt_s13_w0,rt_s13_w1
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from explore_world import kappa  # noqa: E402

WORLDS = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..", "..")), "data", "llm_bias", "worlds")


def load(labels):
    rows = []
    for l in labels:
        rows += [json.loads(x) for x in open(os.path.join(WORLDS, l, "decisions.jsonl")) if x.strip()]
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orig", required=True)
    ap.add_argument("--retest", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    O, T = load(a.orig.split(",")), load(a.retest.split(","))
    people = sorted(T["agent_id"].unique())
    O = O[O["agent_id"].isin(people)]
    k = ["agent_id", "post_key", "judge"]
    m = O.merge(T, on=k, suffixes=("_1", "_2"))
    res = {"people": len(people), "pairs": len(m)}
    for j, g in m.groupby("judge"):
        kap, agree, chance = kappa(g["action_1"].values, g["action_2"].values)
        cares = g["affinity_1"] >= 0
        kc = kappa(g.loc[cares, "action_1"].values, g.loc[cares, "action_2"].values)
        kn = kappa(g.loc[~cares, "action_1"].values, g.loc[~cares, "action_2"].values)
        res[f"self_{j}"] = {"kappa": kap, "agree_%": agree, "chance_%": chance, "pairs": len(g),
                            "cares": dict(zip(("kappa", "agree_%", "chance_%"), kc)),
                            "does_not_care": dict(zip(("kappa", "agree_%", "chance_%"), kn))}
    # the two models on the same people and posts, from the original worlds (same subset of people)
    w = O.pivot_table(index=["agent_id", "post_key"], columns="judge", values="action", aggfunc="first").dropna()
    if w.shape[1] == 2:
        kap, agree, chance = kappa(w.iloc[:, 0].values, w.iloc[:, 1].values)
        res["cross_model"] = {"kappa": kap, "agree_%": agree, "chance_%": chance, "pairs": len(w)}
    print(json.dumps(res, indent=1))
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
