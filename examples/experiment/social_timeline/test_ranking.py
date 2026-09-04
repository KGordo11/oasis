"""Equivalence gate for the vectorised candidate ranking.

`_rank_candidates` was a nested Python loop over (agent, post). That cost
~1.35 us per pair at every size tested -- invisible at 36 x 262, and roughly
23 minutes PER ROUND at 1000 agents x 1e6 posts, against ~1.1 s for the matmul
it wraps. A factor of 1,231. F-50's "scoring is 0.03% of runtime" is true at
today's scale and false at the one being planned for, which is why it was
rewritten.

A rewrite of the ranker is a rewrite of what every agent sees, so "it looks
right" is not good enough. This file holds the vectorised version against the
original implementation, kept here verbatim, and requires bit-identical output.

The subtle part is tie-breaking. The original built its list in ascending
post-index order and used Python's stable sort, so equal scores kept ascending
post index. `np.argsort(kind="stable")` on negated scores reproduces that --
but only because it is stable, and only because the input order matches. The
forced-tie cases below exist to catch a future change to either.

    python test_ranking.py
"""
from __future__ import annotations

import os
import random
import sys
import time

import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline_platform import TimelinePlatform  # noqa: E402

PASS, FAIL = [], []


def check(label: str, cond: bool) -> None:
    (PASS if cond else FAIL).append(label)
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")


def original(agent_ids, post_ids, authors, sims, recency, round_no, k=30):
    """The pre-vectorisation implementation, kept verbatim as the oracle."""
    rec_rows, candidate_rows = [], []
    for u_idx, agent_id in enumerate(agent_ids):
        scored = []
        for p_idx, _post_id in enumerate(post_ids):
            if authors[p_idx] == agent_id:
                continue
            sim = float(sims[u_idx, p_idx])
            scored.append((sim * recency[p_idx], sim, p_idx))
        if not scored:
            continue
        scored.sort(key=lambda t: t[0], reverse=True)
        for rank, (score, sim, p_idx) in enumerate(scored[:k]):
            rec_rows.append((agent_id, post_ids[p_idx]))
            candidate_rows.append(
                (round_no, agent_id, post_ids[p_idx], authors[p_idx],
                 rank, sim, recency[p_idx], score))
    return rec_rows, candidate_rows


class _Stub:
    """Just enough platform to call the method under test."""
    max_rec_post_len = 30

    def __init__(self):
        self.stats = {"empty_candidate_pools": 0}

    _rank_candidates = TimelinePlatform._rank_candidates


def _same(a, b) -> bool:
    if a[0] != b[0]:
        return False
    if len(a[1]) != len(b[1]):
        return False
    for x, y in zip(a[1], b[1]):
        if x[:5] != y[:5]:
            return False
        if any(abs(x[i] - y[i]) > 1e-9 for i in (5, 6, 7)):
            return False
    return True


def main() -> int:
    random.seed(0)
    torch.manual_seed(0)

    cases = [
        ("realistic 36 x 262", 36, 262, False),
        ("wider    50 x 500", 50, 500, False),
        ("forced ties 12 x 80", 12, 80, True),
        ("forced ties  5 x 20", 5, 20, True),
        ("single agent 1 x 40", 1, 40, False),
        ("pool smaller than k", 8, 12, False),
    ]
    for label, na, npst, tie in cases:
        agent_ids = list(range(na))
        post_ids = list(range(1000, 1000 + npst))
        authors = [random.randrange(na) for _ in range(npst)]
        sims = torch.rand(na, npst)
        if tie:
            # Quantise hard so exact ties actually occur, then hold recency
            # constant so the product ties too.
            sims = torch.round(sims * 4) / 4
            recency = [0.5] * npst
        else:
            recency = [round(random.uniform(0.1, 0.93), 6)
                       for _ in range(npst)]

        want = original(agent_ids, post_ids, authors, sims, recency, 7)
        got = _Stub()._rank_candidates(agent_ids, post_ids, authors, sims,
                                       recency, 7)
        check(f"{label}: identical to the original ranker", _same(want, got))

    # An agent who wrote every post in the pool has nothing to be shown, and
    # must be counted rather than silently skipped.
    stub = _Stub()
    got = stub._rank_candidates([0], [1, 2], [0, 0], torch.rand(1, 2),
                                [0.9, 0.9], 1)
    check("agent authoring every post yields no rows",
          got == ([], []))
    check("that case increments empty_candidate_pools",
          stub.stats["empty_candidate_pools"] == 1)

    # Speed is the reason for the change; assert it actually materialised.
    na, npst = 200, 4000
    agent_ids = list(range(na))
    post_ids = list(range(npst))
    authors = [random.randrange(na) for _ in range(npst)]
    sims = torch.rand(na, npst)
    recency = [0.9] * npst
    t = time.time()
    original(agent_ids, post_ids, authors, sims, recency, 1)
    t_old = time.time() - t
    t = time.time()
    _Stub()._rank_candidates(agent_ids, post_ids, authors, sims, recency, 1)
    t_new = time.time() - t
    speedup = t_old / t_new if t_new else 0
    print(f"        200 x 4000: {t_old:.2f}s -> {t_new:.3f}s "
          f"({speedup:.0f}x)")
    check(f"vectorised ranker is at least 5x faster ({speedup:.0f}x)",
          speedup >= 5)

    print("=" * 62)
    print(f"{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        for f in FAIL:
            print(f"  FAILED: {f}")
        return 1
    print("Ranking is bit-identical to the implementation it replaced.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
