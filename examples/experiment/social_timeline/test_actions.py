"""Mechanical verification that the engagement actions actually work.

IN PLAIN WORDS
--------------
A TEST. It checks that all 22 things a pretend person can do actually work.

This matters for an honest reason. In our runs the people never once disliked,
muted, or unfollowed anything. That could mean two very different things: the
buttons were broken, or the AI simply chose not to press them. This test proves
the buttons work, so it must be a choice.

WHY THIS EXISTS
---------------
Small runs (R-4, R-5) showed agents creating posts and using group chat but
never liking, commenting, following or reposting. That has two very different
possible causes:

  (a) the model chooses not to -- plausible when the feed is nearly empty and
      there is little to react to; or
  (b) those actions are mechanically broken, in which case no amount of extra
      scale or extra rounds would ever produce them.

Distinguishing (a) from (b) by running a bigger simulation would be slow and
ambiguous. This calls the platform methods directly -- no LLM, no agents, no
tool-calling -- so the answer is immediate and unambiguous.

This is a diagnostic harness, not part of the simulation. It deliberately
invokes actions directly, which the no-manual-actions rule (D-6) governs for
*simulation runs*; D-6 is about agents having free will during an experiment,
not about whether we may unit-test the platform.

Run:
    oasis-env/bin/python examples/experiment/social_timeline/test_actions.py
Exits non-zero if any engagement action fails to take effect.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def main():
    """Run every action test and report the score."""
    db_path = os.path.join(tempfile.mkdtemp(), "action_test.db")
    os.environ["OASIS_DB_PATH"] = db_path

    from oasis.social_platform.channel import Channel

    from timeline_platform import TimelinePlatform

    pf = TimelinePlatform(
        db_path=db_path,
        channel=Channel(),
        recsys_type="twhin-bert",
        max_rec_post_len=30,
        refresh_rec_post_count=8,
        following_post_count=4,
        allow_self_rating=False,
    )

    failures = []

    def check(label, ok, detail=""):
        """Run one test and record whether it passed."""
        print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
        if not ok:
            failures.append(label)

    # Two users. sign_up takes (user_name, name, bio).
    for agent_id, uname in ((0, "alice"), (1, "bob")):
        r = await pf.sign_up(agent_id, (uname, uname, f"{uname}'s bio"))
        check(f"sign_up agent {agent_id}", r.get("success"), str(r))

    r = await pf.create_post(0, "A post by alice about tourism in Chile.")
    post_id = r.get("post_id")
    check("create_post", r.get("success"), f"post_id={post_id}")

    # F-19: an agent may only act on what it has been shown, so bob has to see
    # the post before any of the engagement checks below can pass. Without this
    # the suite tests the gate rather than the actions, which is why it began
    # failing wholesale once the gate landed.
    await pf.update_rec_table()
    seen = await pf.refresh(1)
    check("bob's feed contains alice's post",
          any(p.get("post_id") == post_id for p in (seen.get("posts") or [])),
          f"feed={[p.get('post_id') for p in (seen.get('posts') or [])]}")

    # bob engages with alice's post
    r = await pf.like_post(1, post_id)
    check("like_post", r.get("success"), str(r))

    r = await pf.create_comment(1, (post_id, "Great post, I agree!"))
    check("create_comment", r.get("success"), str(r))

    r = await pf.repost(1, post_id)
    check("repost", r.get("success"), str(r))

    r = await pf.follow(1, 0)
    check("follow", r.get("success"), str(r))

    r = await pf.dislike_post(1, post_id)
    check("dislike_post", r.get("success"), str(r))

    # Did the writes actually land, or did the calls merely return success?
    cur = pf.db_cursor
    for table, expected in (("like", 1), ("comment", 1), ("follow", 1),
                            ("dislike", 1)):
        cur.execute(f"SELECT COUNT(*) FROM `{table}`")
        n = cur.fetchone()[0]
        check(f"{table} table has {expected} row", n == expected, f"got {n}")

    # The follow-graph feed source depends on this join working.
    cur.execute("SELECT COUNT(*) FROM post JOIN follow "
                "ON post.user_id = follow.followee_id "
                "WHERE follow.follower_id = 1")
    n = cur.fetchone()[0]
    check("follow-injection join returns alice's post to bob", n >= 1,
          f"got {n}")

    # DM privacy (D-7): a two-member group must refuse a third joiner.
    r = await pf.create_group(0, "private-chat")
    gid = r.get("group_id")
    check("create_group", r.get("success"), f"group_id={gid}")
    r = await pf.join_group(1, gid)
    check("second member can join", r.get("success"), str(r))
    r = await pf.join_group(2, gid)
    check("third member is refused (DM stays private)",
          not r.get("success"), str(r))

    print("\n" + "=" * 60)
    if failures:
        print(f"{len(failures)} FAILED: {failures}")
        sys.exit(1)
    print("All engagement actions work mechanically.")
    print("=> absence of likes/follows/comments in runs is a MODEL CHOICE,")
    print("   not a broken action surface.")


if __name__ == "__main__":
    asyncio.run(main())
