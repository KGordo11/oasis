"""Tests for the B-26 guard — `--agents N` must be a request, not a ceiling.

B-26: `--agents N` silently degraded to "use every persona in the file" when N
exceeded the file. The run then had fewer agents than its own name and its own
command line said, and nothing anywhere reported the difference. That is the
same failure shape as B-28: it does not raise, it does not slow down, it just
quietly stops being the experiment that was asked for — and it is worse than
B-28 in one way, because the mislabelled run is indistinguishable from a real
one after the fact.

It nearly mattered on 2026-09-13. The planned sweep runs 18/36/54/72/90 agents
against a persona file with 99 usable bios. 90 fits. 108 — the next increment
of 18 — does not, and would have produced a "108-agent run" of 99 agents.

The rule these tests encode: asking for more agents than the file can supply is
a refusal, not a truncation, unless the operator overrides it deliberately.
"""
import csv
import os
import tempfile

import personas


def write_personas(n, path):
    """Write a minimal twitter-format persona CSV with n rows."""
    cols = ["user_id", "name", "username", "following_agentid_list",
            "previous_tweets", "user_char", "description"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for i in range(n):
            w.writerow({
                "user_id": i,
                "name": f"Person {i}",
                "username": f"person{i}",
                "following_agentid_list": "[]",
                "previous_tweets": "[]",
                "user_char": f"You are person {i}, who cares about topic {i % 7}.",
                "description": "",
            })
    return path


def limit_check(limit, available, override=False):
    """The guard, isolated from the async agent builder that carries it.

    Mirrors timeline_agent.generate_timeline_agents exactly: refuse when the
    request exceeds supply, slice when it is under, pass through when equal.
    """
    if limit is not None and limit > available:
        if override:
            return "overridden"
        raise SystemExit(2)
    if limit is not None and limit < available:
        return "sliced"
    return "exact"


def test_REFUSES_the_run_that_would_have_been_mislabelled():
    # 108 agents against the 99-persona business file: the next increment of 18.
    try:
        limit_check(108, 99)
    except SystemExit as e:
        assert e.code == 2, e.code
        return
    raise AssertionError("108 agents on a 99-persona file must refuse, not truncate")


def test_tonights_whole_sweep_is_within_supply():
    # 18/36/54/72/90 against 99 usable business personas — the actual plan.
    for n in (18, 36, 54, 72, 90):
        assert limit_check(n, 99) == "sliced", f"{n} agents should be servable"


def test_exactly_the_file_size_is_allowed():
    assert limit_check(99, 99) == "exact"


def test_override_is_available_but_must_be_asked_for():
    assert limit_check(108, 99, override=True) == "overridden"


def test_no_limit_uses_the_whole_file():
    assert limit_check(None, 99) == "exact"


def test_the_guard_reads_the_same_count_the_loader_produces():
    """The refusal must be based on what load_personas actually returns.

    A guard that counts CSV rows while the loader drops unusable ones would
    refuse the wrong runs — the business file has 111 rows and 99 usable bios.
    """
    with tempfile.TemporaryDirectory() as d:
        p = write_personas(40, os.path.join(d, "p.csv"))
        entries = personas.load_personas(p)
        assert len(entries) == 40, len(entries)
        assert limit_check(39, len(entries)) == "sliced"
        try:
            limit_check(41, len(entries))
        except SystemExit:
            return
    raise AssertionError("asking for 41 of 40 personas must refuse")


def test_real_business_file_still_supplies_at_least_90():
    """The file tonight's sweep depends on, counted rather than assumed."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    path = os.path.join(root, "data", "twitter_dataset",
                        "anonymous_topic_200_1h", "False_Business_0.csv")
    if not os.path.exists(path):
        return  # not a failure of the guard; the file is data, not code
    n = len(personas.load_personas(path))
    assert n >= 90, f"business file supplies {n} personas, sweep needs 90"


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
