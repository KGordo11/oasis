"""Tests for the LLM Bias harness. No model calls -- runs in seconds.

    ./oasis-env/bin/python -m pytest examples/experiment/llm_bias -q
"""

import os
import random
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze  # noqa: E402
import authors  # noqa: E402
import judge  # noqa: E402
import llm  # noqa: E402
import personas  # noqa: E402
from topics import PRIMARY, TOPICS  # noqa: E402


# ---------- personas ----------

def test_committed_bank_matches_builder():
    assert personas.bank_hash(personas.load_bank()) == personas.bank_hash(personas.build_bank())


def test_bank_shape():
    bank = personas.load_bank()
    assert len(bank) == personas.BANK_SIZE
    assert [p["id"] for p in bank] == list(range(len(bank)))
    assert len({p["username"] for p in bank}) == len(bank)
    for p in bank:
        aff = p["topic_affinity"]
        assert set(aff) == set(TOPICS)
        assert max(aff.values()) == 2 and min(aff.values()) == -2  # every persona has an edge
        for k in ("realname", "username", "bio", "persona", "age", "gender", "mbti", "country",
                  "profession", "interested_topics"):  # OASIS reddit schema
            assert k in p


def test_bank_interest_spread_on_primary_topics():
    bank = personas.load_bank()
    for t in PRIMARY:
        vals = [p["topic_affinity"][t] for p in bank]
        assert {-2, -1, 0, 1, 2} <= set(vals), t


# ---------- posts ----------

def test_clean_text_strips_formatting():
    s = "**Title:** Hello #budget 😀\n- item one\n1. item two\nsee https://x.com `code`"
    c = authors.clean_text(s)
    for bad in ("**", "#", "😀", "https", "`", "- item", "1. item"):
        assert bad not in c


def test_validate_post_rejects_leaks_and_lengths():
    body = " ".join(["word"] * 60)
    assert authors.validate_post({"title": "Fine title", "body": body})
    with pytest.raises(ValueError):
        authors.validate_post({"title": "As an AI I think", "body": body})
    with pytest.raises(ValueError):
        authors.validate_post({"title": "ok", "body": "too short"})
    with pytest.raises(ValueError):
        authors.validate_post({"title": "ok", "body": body + " llama rocks"})


def test_slot_brief_same_for_every_author_and_deterministic():
    a = authors.slot_brief(1, 3, "cars")
    assert a == authors.slot_brief(1, 3, "cars")
    assert authors.slot_brief(1, 0, "cars")["angle"] != authors.slot_brief(1, 1, "cars")["angle"]


def test_stable_seed():
    assert llm.stable_seed(1, 2, "x") == llm.stable_seed(1, 2, "x")
    seeds = {llm.stable_seed(1, a, 0, "t", "judge") for a in range(1000)}
    assert len(seeds) == 1000


# ---------- judge ----------

def test_display_order_is_a_permutation_and_judge_independent():
    o = judge.display_order(7, 1, 42, 3, "cars")
    assert sorted(o) == list(range(7))
    assert o == judge.display_order(7, 1, 42, 3, "cars")
    # over many personas, every author lands in every position (no fixed position per author)
    first = {judge.display_order(7, 1, p, 0, "cars")[0] for p in range(200)}
    assert first == set(range(7))


def test_validator_normalises():
    v = judge.make_validator(3)
    out = v({"votes": {"1": "Upvote", "2": "down", "3": "skip"}, "favorite": "Post 2", "reason": "x"})
    assert out["favorite"] == 2 and out["votes"] == {1: "up", 2: "down", 3: "none"}
    out = v({"votes": ["up", "none", "none"], "favorite": 3})
    assert out["favorite"] == 3
    for bad in ({"votes": {}, "favorite": 4}, {"votes": {"1": "up"}, "favorite": "none"},
                {"votes": {}, "favorite": 1}):
        with pytest.raises(ValueError):
            v(bad)


def test_extract_json_tolerates_fences():
    assert llm.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ValueError):
        llm.extract_json("no json here")


# ---------- analysis: planted effect ----------

def synth(beta_self, judges=("A", "B", "C"), n_personas=60, n_slots=12, seed=0):
    """Choice data where post quality is shared and the judge adds beta_self to its own posts."""
    rng = np.random.default_rng(seed)
    quality = {(s, a): rng.normal(0, 1) for s in range(n_slots) for a in judges}
    quality.update({(s, "A"): quality[(s, "A")] + 0.8 for s in range(n_slots)})  # A writes better posts
    out = []
    for J in judges:
        for s in range(n_slots):
            for p in range(n_personas):
                order = list(judges)
                random.Random(f"{p}{s}").shuffle(order)
                u = [quality[(s, a)] + (beta_self if a == J else 0) + rng.gumbel() for a in order]
                fav = int(np.argmax(u))
                keys = [f"r{s}|t|{a}" for a in order]
                out.append({"label": J, "judge": J, "seed": 1, "round": s, "topic": "t", "agent_id": p,
                            "affinity": 0, "n_posts": len(order), "shown_keys": keys, "shown_authors": order,
                            "ok": True, "favorite_key": keys[fav],
                            "votes": {k: ("up" if uu > 0.5 else "none") for k, uu in zip(keys, u)}})
    return out


def test_null_effect_not_detected_despite_quality_gap():
    res, _ = analyze.analyze(synth(0.0), B=300)
    lo, hi = res["sp_chosen"]["_pooled"]["ci95"]
    assert lo < 0 < hi
    # raw self-share for A is high purely from quality -- the naive measure WOULD be fooled
    assert res["raw_self_share"]["A"] > 0.4
    assert res["clogit"]["p"] > 0.01


def test_planted_effect_detected():
    res, _ = analyze.analyze(synth(0.7), B=300)
    lo, hi = res["sp_chosen"]["_pooled"]["ci95"]
    assert lo > 0
    assert res["clogit"]["odds_ratio"] > 1.5 and res["clogit"]["p"] < 0.001
    # beta recovered roughly
    assert abs(res["clogit"]["beta_self"] - 0.7) < 0.25


def test_generous_judge_is_not_mistaken_for_self_preference_on_upvotes():
    # judge A upvotes nearly everything, B and C rarely; nobody favours their own posts
    data = synth(0.0)
    rng = np.random.default_rng(5)
    for d in data:
        p_up = 0.85 if d["judge"] == "A" else 0.2
        d["votes"] = {k: ("up" if rng.random() < p_up else "none") for k in d["shown_keys"]}
    res, _ = analyze.analyze(data, B=300)
    lo, hi = res["sp_up"]["A"]["ci95"]
    assert lo < 0 < hi, res["sp_up"]["A"]
