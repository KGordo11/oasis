"""Tests for assert_comparable.py — the guard against silent config drift.

The failure it exists to prevent, in full: on 2026-09-13 an 8.5-hour agent sweep
was about to be launched without `--temperature 0.7`. Every run in the family it
was extending carries 0.7, because every shell script here passes it explicitly.
The bare CLI default is 0.9. Nothing would have errored, nothing would have run
slower, and the resulting five runs would have been a cost curve comparable with
nothing -- indistinguishable, after the fact, from a real one.

The rule these tests encode: a value that differs from the reference is a
refusal; a KEY the reference never had is not, because the manifest schema grows
and an inert new default is not drift.
"""
import json
import os
import tempfile

import assert_comparable as A


# The real drift, reduced to its essentials.
REF = {"agents": 36, "rounds": 7, "label": "ctx8192_a36", "seed": 42,
       "temperature": 0.7, "recsys": "twhin-bert", "semaphore": 4,
       "terse_tools": True, "max_rec_post_len": 30, "model": "llama3.1:8b",
       "prompt_version": 10, "following_post_count": 4,
       "refresh_rec_post_count": 8, "n_actions": 27}


def manifest(cfg):
    fd, p = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"config": cfg}, f)
    return p


def test_CATCHES_the_temperature_drift_that_nearly_cost_a_night():
    cand = dict(REF, agents=18, label="sweep18_a18", temperature=0.9)
    drift, new, compared = A.compare(cand, REF)
    assert [d[0] for d in drift] == ["temperature"], drift
    assert drift[0][1] == 0.9 and drift[0][2] == 0.7, drift


def test_a_new_manifest_key_is_not_drift():
    # shuffle_feed was added to the manifest on 2026-09-12, after the reference
    # runs. Its default is inert. It must not fail a campaign.
    cand = dict(REF, shuffle_feed=False)
    drift, new, compared = A.compare(cand, REF)
    assert drift == [], drift
    assert new == [("shuffle_feed", False)], new


def test_a_new_key_with_a_LIVE_value_is_still_not_drift_but_is_reported():
    # The guard cannot know an unknown key's semantics, so it reports rather
    # than guesses. The operator reads the line.
    cand = dict(REF, shuffle_feed=True)
    drift, new, compared = A.compare(cand, REF)
    assert drift == []
    assert new == [("shuffle_feed", True)], new


def test_keys_that_are_SUPPOSED_to_vary_do_not_fail():
    cand = dict(REF, agents=90, rounds=5, label="sweep18_a90", seed=7,
                persona_separability={"n": 90}, ollama_server_state=[{"x": 1}])
    drift, new, compared = A.compare(cand, REF)
    assert drift == [], drift


def test_identical_configs_pass():
    drift, new, compared = A.compare(dict(REF), REF)
    assert drift == [] and new == []
    assert compared >= 10, compared


def test_a_missing_key_counts_as_drift():
    cand = {k: v for k, v in REF.items() if k != "terse_tools"}
    drift, new, compared = A.compare(cand, REF)
    assert [d[0] for d in drift] == ["terse_tools"], drift
    assert drift[0][1] is None, drift


def test_several_drifts_are_all_reported_not_just_the_first():
    cand = dict(REF, temperature=0.9, semaphore=8, recsys="reddit")
    drift, new, compared = A.compare(cand, REF)
    assert sorted(d[0] for d in drift) == ["recsys", "semaphore", "temperature"], drift


def test_REFUSES_a_vacuous_pass_on_an_empty_reference():
    """A reference with no config must not read as 'everything matches'.

    This is the guard's own failure mode: compare({}, {}) is trivially clean,
    and a guard that green-lights a night because it compared nothing is worse
    than no guard, because it is believed.
    """
    a, b = manifest(dict(REF)), manifest({})
    try:
        ok, lines = A.verify(a, b)
        assert ok is False, "empty reference must refuse"
        assert any("only 0 keys compared" in ln for ln in lines), lines
    finally:
        os.unlink(a); os.unlink(b)


def test_verify_reports_the_drift_in_words():
    a, b = manifest(dict(REF, temperature=0.9)), manifest(REF)
    try:
        ok, lines = A.verify(a, b)
        assert ok is False
        assert any("DRIFT" in ln and "temperature" in ln for ln in lines), lines
    finally:
        os.unlink(a); os.unlink(b)


def test_verify_passes_a_real_pair_of_reference_runs():
    """ctx8192_a12 and ctx8192_a36 are the same configuration at two sizes."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", "..", "..", "data", "parquet"))
    a = os.path.join(root, "ctx8192_a12", "manifest.json")
    b = os.path.join(root, "ctx8192_a36", "manifest.json")
    if not (os.path.exists(a) and os.path.exists(b)):
        return  # data, not code
    ok, lines = A.verify(a, b)
    assert ok, lines


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  PASS  {name}")
            except AssertionError as e:
                fails += 1; print(f"  FAIL  {name}: {e}")
    print(f"\n{'all passed' if not fails else str(fails) + ' FAILED'}")
    raise SystemExit(1 if fails else 0)
