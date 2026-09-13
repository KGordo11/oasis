"""Tests for --shuffle-feed, the experimental arm F-94 asks for.

WHY THIS EXISTS
---------------
F-94 measured that a post's SLOT predicts engagement at an odds ratio of roughly
1.5 to 2.2, after conditioning on the post itself and on the ranker's own
relevance score, replicating across 24 runs and two persona files. That is
observational: position was never assigned, so the estimate cannot separate
"being seen first" from "something the ranker knows that its score does not
capture".

`--shuffle-feed` assigns it. Rank exactly as now, select exactly the same posts,
then permute the order before display. The agent sees the same twelve posts from
the same three tiers; only WHERE each sits changes.

The two outcomes are both informative, which is the property a good experiment
has:
  * engagement flattens across slots and total engagement FALLS
        -> the ranker's ordering carried real information
  * engagement flattens across slots and total engagement HOLDS
        -> position was attention, and the ordering was worth nothing

The invariants below are what make that reading valid. If the shuffle changed
WHICH posts were selected, or was not reproducible, the arm would not be
comparable to the control and neither outcome could be read.
"""
import sys
sys.path.insert(0, ".")
from timeline_platform import shuffle_feed_order


CONTROL = [901, 902, 903, 401, 402, 101, 102, 103, 104, 105, 106, 107]


def test_shuffle_preserves_the_exact_set_of_posts():
    """The arm must change ORDER only. A different feed is a different study."""
    out = shuffle_feed_order(CONTROL, agent_id=7, round_no=3, seed=42)
    assert sorted(out) == sorted(CONTROL), out
    assert len(out) == len(CONTROL)


def test_shuffle_actually_reorders():
    out = shuffle_feed_order(CONTROL, agent_id=7, round_no=3, seed=42)
    assert out != CONTROL, "a shuffle that returns the input tests nothing"


def test_same_agent_round_and_seed_gives_the_same_permutation():
    """Reproducibility: a run must be repeatable from its manifest."""
    a = shuffle_feed_order(CONTROL, agent_id=7, round_no=3, seed=42)
    b = shuffle_feed_order(CONTROL, agent_id=7, round_no=3, seed=42)
    assert a == b


def test_different_agents_get_different_permutations():
    """Otherwise every agent sees the same re-ordering and slot is still
    confounded with content -- the exact thing this arm exists to break."""
    a = shuffle_feed_order(CONTROL, agent_id=7, round_no=3, seed=42)
    b = shuffle_feed_order(CONTROL, agent_id=8, round_no=3, seed=42)
    assert a != b


def test_different_rounds_get_different_permutations():
    a = shuffle_feed_order(CONTROL, agent_id=7, round_no=3, seed=42)
    b = shuffle_feed_order(CONTROL, agent_id=7, round_no=4, seed=42)
    assert a != b


def test_does_not_disturb_the_global_random_stream():
    """Feed selection already draws from `random` for exploration slots. If the
    shuffle consumed from the same stream it would change WHICH posts are
    selected on later calls, and the arm would no longer be a pure re-ordering.
    """
    import random
    random.seed(1234)
    before = [random.random() for _ in range(3)]
    random.seed(1234)
    shuffle_feed_order(CONTROL, agent_id=7, round_no=3, seed=42)
    after = [random.random() for _ in range(3)]
    assert before == after, "the shuffle drew from the global random stream"


def test_handles_empty_and_single_post_feeds():
    """Round 0 has empty feeds; small worlds have short ones."""
    assert shuffle_feed_order([], agent_id=1, round_no=0, seed=42) == []
    assert shuffle_feed_order([5], agent_id=1, round_no=0, seed=42) == [5]


def test_permutation_is_uniform_enough_to_break_the_tier_ordering():
    """Network posts lead the control feed by construction. Across many agents
    the shuffle must put them elsewhere roughly as often as anywhere else,
    otherwise tier and slot stay correlated."""
    first_slot_is_network = 0
    trials = 400
    for agent in range(trials):
        out = shuffle_feed_order(CONTROL, agent_id=agent, round_no=1, seed=42)
        if out[0] in (901, 902, 903):
            first_slot_is_network += 1
    share = first_slot_is_network / trials
    # 3 of 12 posts are network, so expect ~0.25 under a uniform permutation.
    assert 0.18 < share < 0.32, f"network leads slot 0 in {share:.0%} of feeds"


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  PASS  {name}")
            except AssertionError as e:
                fails += 1; print(f"  FAIL  {name}: {e}")
    print(f"\n{'all passed' if not fails else str(fails)+' FAILED'}")
    raise SystemExit(1 if fails else 0)
