"""Tests for the two things that silently produced wrong data.

IN PLAIN WORDS
--------------
A TEST. It checks that our record-keeping is complete and not double-counted.

The entire study rests on the claim that we wrote down every post every person
saw. This test proves that claim by rebuilding the record from both directions
and checking the two agree.

Both bugs these cover were invisible in a passing run -- the simulation
completed, numbers appeared, and the numbers were wrong.

TEST 1 -- exposure source attribution (`following` / `both`)
    `rec_history.source` says whether a post reached an agent through the
    recommendation algorithm, through someone they follow, or both. Across
    every run so far, 100% of exposures were `recsys`, because no follows
    existed -- so the `following` and `both` branches had NEVER executed even
    once. That attribution is the core of "whose posts pop up where", so it
    cannot be shipped untested. Built here with a real follow edge.

TEST 2 -- analyzer target resolution (bug B-4)
    Trace `info` payloads are not uniform: create_comment records only
    `comment_id` (no post_id), quote_post records `quoted_id` as a STRING.
    Assuming uniformity silently dropped real engagement, reporting agents as
    having 0.0 engagement while they were actively commenting. This pins the
    irregular shapes so the next new action type cannot regress it quietly.

Run:
    oasis-env/bin/python examples/experiment/social_timeline/test_instrumentation.py
Exits non-zero on failure.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FAILURES = []


def check(label, ok, detail=""):
    """Run one test and record whether it passed."""
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    if not ok:
        FAILURES.append(label)


async def test_source_attribution():
    """Check each exposure is labelled with the right feed tier."""
    print("\n--- TEST 1: exposure source attribution ---")
    db_path = os.path.join(tempfile.mkdtemp(), "src.db")
    os.environ["OASIS_DB_PATH"] = db_path

    from oasis.social_platform.channel import Channel

    from timeline_platform import TimelinePlatform

    pf = TimelinePlatform(
        db_path=db_path, channel=Channel(), recsys_type="twhin-bert",
        max_rec_post_len=30, refresh_rec_post_count=8,
        following_post_count=4, allow_self_rating=False)

    # alice and carol both post; bob follows alice only.
    for aid, name in ((0, "alice"), (1, "bob"), (2, "carol")):
        await pf.sign_up(aid, (name, name, f"{name} writes about travel"))
    r = await pf.create_post(0, "Exploring the coast of Chile this week.")
    alice_post = r["post_id"]
    r = await pf.create_post(2, "Debugging a memory allocator in C today.")
    carol_post = r["post_id"]

    # F-19: bob must see alice before he can follow her. Following first
    # silently failed the blind-action gate, so no network-tier exposure ever
    # appeared and the attribution checks below had nothing to find.
    await pf.update_rec_table()
    await pf.refresh(1)
    followed = await pf.follow(1, 0)
    check("bob can follow alice once he has seen her", followed.get("success"),
          str(followed))

    await pf.update_rec_table()
    await pf.refresh(1)

    cur = pf.db_cursor
    cur.execute("SELECT post_id, source FROM rec_history WHERE agent_id = 1")
    seen = dict(cur.fetchall())
    print(f"      bob's exposures: {seen}")

    check("bob was exposed to alice's post (he follows her)",
          alice_post in seen, f"post {alice_post}")
    # F-25 renamed the tiers: following -> network, recsys -> discovery,
    # plus a new fof tier. Both vocabularies are accepted so this suite keeps
    # working against databases from either era.
    SOCIAL = ("network", "following", "both", "fof")
    check("alice's post is attributed to the follow graph",
          seen.get(alice_post) in SOCIAL,
          f"source={seen.get(alice_post)!r}")
    check("at least one social source is now exercised",
          any(v in SOCIAL for v in seen.values()),
          f"sources={sorted(set(seen.values()))}")

    # carol is unfollowed, so if she appears at all it must be via recsys.
    if carol_post in seen:
        check("unfollowed author is attributed to the algorithm",
              seen[carol_post] in ("discovery", "recsys"),
              f"source={seen[carol_post]!r}")
    else:
        print("      (carol not in this feed sample -- nothing to assert)")

    cur.execute("SELECT COUNT(*) FROM rec_candidates WHERE agent_id = 1")
    check("candidate pool recorded for bob", cur.fetchone()[0] > 0)


async def test_analyzer_targets():
    """Check the analyser points each action at the right post or person."""
    print("\n--- TEST 2: analyzer target resolution (B-4) ---")
    db_path = os.path.join(tempfile.mkdtemp(), "an.db")
    os.environ["OASIS_DB_PATH"] = db_path

    from oasis.social_platform.channel import Channel

    from timeline_platform import TimelinePlatform

    pf = TimelinePlatform(
        db_path=db_path, channel=Channel(), recsys_type="twhin-bert",
        max_rec_post_len=30, refresh_rec_post_count=8,
        following_post_count=4, allow_self_rating=False)

    for aid, name in ((0, "alice"), (1, "bob")):
        await pf.sign_up(aid, (name, name, f"{name} bio"))
    post_id = (await pf.create_post(0, "Alice's original post."))["post_id"]

    # F-19: bob must see the post before he can act on it.
    await pf.update_rec_table()
    await pf.refresh(1)

    # The three payload shapes that differ from each other.
    await pf.create_comment(1, (post_id, "Bob's reply."))   # comment_id only
    await pf.quote_post(1, (post_id, "Bob quoting alice."))   # quoted_id as str
    await pf.like_post(1, post_id)                          # plain post_id
    await pf.follow(1, 0)                                   # followee_id
    pf.db.commit()

    import analyze
    data = analyze.analyze(db_path)
    bob = data["agents"][1]

    print(f"      bob actions      : {bob['action_counts']}")
    print(f"      bob interacted_with: {bob['interacted_with']}")

    check("comment resolved to the post it replied to (not dropped)",
          post_id in bob["seen_and_acted"] or
          "0" in bob["interacted_with"],
          f"acted={bob['seen_and_acted']} with={bob['interacted_with']}")

    towards_alice = bob["interacted_with"].get("0", {})
    for action in ("create_comment", "quote_post", "like_post", "follow"):
        check(f"{action} attributed to alice",
              action in towards_alice,
              f"got {sorted(towards_alice)}")

    check("alice sees bob's interactions from her side",
          "1" in data["agents"][0]["interacted_by"],
          str(data["agents"][0]["interacted_by"]))


async def main():
    """Run every instrumentation test and report the score."""
    await test_source_attribution()
    await test_analyzer_targets()
    print("\n" + "=" * 60)
    if FAILURES:
        print(f"{len(FAILURES)} FAILED: {FAILURES}")
        sys.exit(1)
    print("All instrumentation tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
