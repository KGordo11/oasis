"""Tests for the LLM Bias harness. No model calls -- runs in seconds.

    ./oasis-env/bin/python -m pytest examples/experiment/llm_bias -q
"""

import json
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


def test_fast_clogit_matches_statsmodels():
    df = analyze.long_table(synth(0.5, n_personas=30, n_slots=6))
    sm = analyze.clogit_self(df)
    D, Y, k, _, _, M = analyze._clogit_design(df)
    assert abs(analyze.fast_clogit(D, Y, k, ridge=0.0, M=M)[0] - sm["beta_self"]) < 0.01


def test_fast_clogit_handles_unequal_choice_sets():
    data = synth(0.5, n_personas=30, n_slots=6)
    for d in data:  # drop author C's post from slot 0 -> 2-post choice sets there
        if d["round"] == 0 and d["favorite_key"] != "r0|t|C":
            keep = [i for i, a in enumerate(d["shown_authors"]) if a != "C"]
            d["shown_keys"] = [d["shown_keys"][i] for i in keep]
            d["shown_authors"] = [d["shown_authors"][i] for i in keep]
            d["n_posts"] = len(keep)
    data = [d for d in data if d["favorite_key"] in d["shown_keys"]]
    df = analyze.long_table(data)
    sm = analyze.clogit_self(df)
    D, Y, k, _, _, M = analyze._clogit_design(df)
    assert abs(analyze.fast_clogit(D, Y, k, ridge=0.0, M=M)[0] - sm["beta_self"]) < 0.02


def test_cluster_bootstrap_clogit_null_and_planted():
    null = analyze.clogit_cluster_bootstrap(analyze.long_table(synth(0.0)), B=150)
    lo, hi = null["or_ci_cluster"]
    assert lo < 1 < hi
    planted = analyze.clogit_cluster_bootstrap(analyze.long_table(synth(0.7)), B=150)
    assert planted["or_ci_cluster"][0] > 1


def test_recognition_probe_offline(tmp_path, monkeypatch):
    import recognize
    seed = 777
    monkeypatch.setattr(authors, "DATA", str(tmp_path))
    monkeypatch.setattr(recognize, "DATA", str(tmp_path))
    models = ["m1", "m2", "m3"]
    with open(authors.bank_path(seed), "w") as f:
        for r in range(2):
            for m in models:
                f.write(json.dumps({"key": authors.key(r, "cars", m), "round": r, "topic": "cars", "author": m,
                                    "ok": True, "title": f"t {m}", "body": f"body by {m}"}) + "\n")
    monkeypatch.setattr(llm, "warm", lambda m: None)

    def fake(model, system, user, validate=None, **kw):
        # m1 always finds its own post; others always claim post 1
        blocks = user.split("[Post ")[1:]
        pick = next(i for i, b in enumerate(blocks) if f"body by {model}" in b) + 1 if model == "m1" else 1
        return validate({"mine": pick, "confidence": 50}), {"latency_s": 0.1, "raw": ""}
    monkeypatch.setattr(llm, "chat_json", fake)
    recognize.run(seed, models, k=3, log=lambda *a: None)
    recognize.run(seed, models, k=3, log=lambda *a: None)  # resumable: second call adds nothing
    s = recognize.summarize(seed)
    assert s["n"] == 3 * 2 * 3
    assert s["per_model"]["m1"]["claims_own"] == 1.0
    assert s["per_model"]["m1"]["did"] > 0.5


# ---------- design v2: scrolling shared world ----------

def _toy_posts():
    import itertools
    return {t: [{"key": f"r{k}|{t}|{a}", "author": a, "title": "t", "body": "b", "round": k, "topic": t}
                for k, a in itertools.product(range(5), ["A", "B", "C"])] for t in PRIMARY}


def test_scroll_feed_order_complete_and_fixed():
    import scroll
    p = personas.load_bank()[7]
    f = scroll.feed(p, _toy_posts(), seed=10)
    assert len(f) == 5 * 15 and len({x[3]["key"] for x in f}) == 75  # every post exactly once
    assert f == scroll.feed(p, _toy_posts(), seed=10)  # same every run
    ranks = [p["topic_affinity"][t] for t in scroll.topic_order(p, PRIMARY)]
    assert ranks == sorted(ranks, reverse=True)  # best-loved topic first
    assert [x[1] for x in f][:15] == [scroll.topic_order(p, PRIMARY)[0]] * 15  # whole topic before the next


def test_scroll_validate_and_outcome():
    import scroll
    assert scroll.validate({"action": "Upvote", "reason": "x"})["action"] == "like"
    assert scroll.validate({"action": "keep scrolling"})["action"] == "nothing"
    with pytest.raises(ValueError):
        scroll.validate({"action": "maybe"})
    assert scroll.outcome({"action": "nothing"}, {}) == "chose"
    assert scroll.outcome(None, {"done_reason": "length", "raw": "{\"act"}) == "cut_off"
    assert scroll.outcome(None, {"timeouts": 2, "raw": None}) == "timeout"
    assert scroll.outcome(None, {"done_reason": "stop", "raw": "hmm"}) == "unreadable"


def test_world_rotation_gives_every_persona_every_judge():
    import run_world
    judges = ["j1", "j2", "j3"]
    for pid in range(10):
        assert {run_world.assign(pid, judges, w) for w in range(3)} == set(judges)
    # within one world the split is balanced
    from collections import Counter
    c = Counter(run_world.assign(pid, judges, 0) for pid in range(99))
    assert max(c.values()) - min(c.values()) <= 1


def test_core99_pinned_and_identical_every_time():
    a, b = personas.core99(), personas.core99()
    assert a == b and len(a) == 99 and [p["id"] for p in a] == list(range(99))
    assert personas.bank_hash(a) == personas.PINNED_CORE99_HASH


def test_core99_refuses_changed_personas(monkeypatch):
    bank = personas.load_bank()
    bank[5] = {**bank[5], "persona": bank[5]["persona"] + " (edited)"}
    monkeypatch.setattr(personas, "load_bank", lambda path=None: bank)
    with pytest.raises(personas.PersonaDrift):
        personas.core99()


def test_fast_bootstrap_matches_cluster_bootstrap():
    """explore_world.fast_bootstrap must give the SAME interval and p as analyze.cluster_bootstrap."""
    import pandas as pd
    import explore_world
    rng = np.random.default_rng(3)
    rows = []
    for persona in range(30):
        for slot in range(8):
            for judge_ in ("A", "B"):
                if (persona + slot) % 2 != ("A", "B").index(judge_):
                    continue
                for author in ("A", "B"):
                    p = 0.5 + 0.1 * (author == "A") + 0.05 * (author == judge_)
                    rows.append({"persona": persona, "slot": slot, "judge": judge_, "author": author,
                                 "up": int(rng.random() < p), "down": int(rng.random() < 0.1)})
    df = pd.DataFrame(rows)
    for col in ("up", "down"):
        ci, p = analyze.cluster_bootstrap(df, col, B=150)
        fci, fp = explore_world.fast_bootstrap(df, col, B=150, chunk=40)
        assert np.allclose(ci["_pooled"], fci) and p == fp


def test_pair_feed_covers_every_slot_once_and_is_model_independent():
    import pair
    per = personas.core99()[0]
    posts = {t: [{"key": authors.key(r, t, au), "round": r, "topic": t, "author": au, "title": "x", "body": "y"}
                 for r in range(5) for au in ("gemma4:e2b", "llama3.1:8b")] for t in PRIMARY}
    f1, f2 = pair.feed(per, posts, 20), pair.feed(per, posts, 20)
    assert f1 == f2 and len(f1) == 25
    seen = [(t, two[0]["round"]) for _, t, _, two in f1]
    assert len(set(seen)) == 25
    assert all({q["author"] for q in two} == {"gemma4:e2b", "llama3.1:8b"} for *_, two in f1)
    firsts = [two[0]["author"] for *_, two in f1]
    assert 0 < firsts.count("llama3.1:8b") < 25  # both authors appear in position 1 somewhere


def test_pair_validate():
    import pair
    v = pair.validate({"post_1": "Like", "post_2": "nothing", "favorite": "1", "reason": "ok"})
    assert v["actions"] == ["like", "nothing"] and v["favorite"] == 1
    assert pair.validate({"post_1": "dislike", "post_2": "upvote", "favorite": 2})["actions"] == ["dislike", "like"]
    for bad in ({"post_1": "like", "post_2": "like", "favorite": 3}, {"post_1": "meh", "post_2": "like", "favorite": 1}):
        with pytest.raises(ValueError):
            pair.validate(bad)


def test_length_rule_guard(tmp_path, monkeypatch):
    monkeypatch.setattr(authors, "bank_path", lambda seed: str(tmp_path / f"b{seed}.jsonl"))
    (tmp_path / "b5.jsonl").write_text(json.dumps({"key": "r0|cars|x", "length_rule": ""}) + "\n")
    with pytest.raises(SystemExit):
        authors.generate(5, 1, ["cars"], ["x"], band=(75, 85), enforce=(65, 95))
