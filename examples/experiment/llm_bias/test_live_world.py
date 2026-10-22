"""Tests for live_world.py (log 14.47). No model, no server: oasis-env/bin/python -m pytest -q test_live_world.py"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live_world as L  # noqa: E402
import run_v2 as R  # noqa: E402

PEOPLE = [{"id": i, "username": f"user{i}"} for i in range(4)]
POSTS = [{"key": f"k{i}", "author_id": i % 4, "topic": "sports", "title": f"Title {i}", "body": f"Body {i} hockey"}
         for i in range(6)]


def world():
    return L.World(PEOPLE, POSTS, R.TOPICS)


def do(w, me, now, ctx=None, **a):
    return w.do(me, now, a, {"topic_of": R.topic_of, **(ctx or {})})


def test_oasis_rules_on_posts():
    w = world(); p = w.pid_of["k1"]; ctx = {"post": p}
    assert do(w, 0, 0, ctx, action="like_post")[0]
    assert do(w, 0, 0, ctx, action="like_post")[1] == "like_post already done"  # OASIS: no second like
    assert do(w, 0, 0, ctx, action="dislike_post")[0]  # OASIS: like and dislike are separate records
    assert do(w, 1, 0, ctx, action="unlike_post")[1] == "nothing to take back"
    assert do(w, 0, 0, ctx, action="repost")[0] and not do(w, 0, 0, ctx, action="repost")[0]
    # a post that is not on this screen cannot be acted on (no blind actions)
    assert do(w, 0, 0, ctx, action="like_post", post_id=w.pid_of["k2"])[1] == "no such post on this screen"
    assert do(w, 0, 0, {"post": p, "shown_posts": [w.pid_of["k2"]]}, action="like_post", post_id=f"p{w.pid_of['k2']}")[0]


def test_comments_visible_from_next_tick():
    w = world(); p = w.pid_of["k1"]
    ok, _, _ = do(w, 2, 5, {"post": p}, action="create_comment", content="hi")
    assert ok
    assert w.comments_of(p, 2, 5)[1] == 1 and w.comments_of(p, 3, 5)[1] == 0 and w.comments_of(p, 3, 6)[1] == 1
    cid = next(iter(w.comments))
    assert not do(w, 3, 5, {"post": p}, action="like_comment", comment_id=f"c{cid}")[0]  # not visible yet
    assert do(w, 3, 6, {"post": p}, action="like_comment", comment_id=f"c{cid}")[0]
    assert "[c%d] u/user2: hi" % cid in w.post_block(p, 3, 6)[5]


def test_private_messages_need_a_profile_and_arrive_next_tick():
    w = world()
    assert do(w, 0, 1, {}, action="send_message", username="user1", message="yo")[1].startswith("you can only message")
    assert do(w, 0, 1, {"shown_users": [1]}, action="send_message", username="u/user1", message="yo")[0]
    assert w.unseen(1, 1) == (0, 0) and w.unseen(1, 2) == (1, 0)
    assert "open_messages" in w.notice(1, 2)
    assert "u/user0: yo" in w.inbox(1, 2) and w.unseen(1, 2) == (0, 0)  # reading marks them seen


def test_groups_follow_oasis():
    w = world()
    ok, _, g = do(w, 0, 1, {}, action="create_group", name="hockey fans")
    assert ok and w.groups[g]["members"] == {0: 1}
    assert do(w, 1, 1, {}, action="join_group", group_id=g)[1] == "group does not exist"  # not visible yet
    assert do(w, 1, 2, {}, action="send_to_group", group_id=g, message="x")[1] == "not a member of this group"
    assert do(w, 1, 2, {}, action="join_group", group_id=f"g{g}")[0]
    assert do(w, 1, 2, {}, action="join_group", group_id=g)[1] == "already in the group"
    assert do(w, 1, 2, {}, action="send_to_group", group_id=g, message="go team")[0]
    assert w.unseen(0, 3) == (0, 1) and "u/user1: go team" in w.groups_screen(0, 3)
    assert do(w, 1, 3, {}, action="leave_group", group_id=g)[0] and 1 not in w.groups[g]["members"]


def test_search_and_trend():
    w = world()
    hits, n = w.search_posts(0, 0, "hockey")
    assert n == 6 and len(hits) == L.LIST_MAX
    do(w, 1, 0, {"post": w.pid_of["k3"]}, action="like_post")
    assert w.trend(2, 1)[0] == w.pid_of["k3"] and w.search_user("USER2") == [2]


def test_live_menu_keeps_every_action():
    for m in (R.MENU, R.MENU_FLIPPED):
        lm = L.live_menu(m)
        for n in R.ACTION_NAMES + ["open_messages"]:
            assert n in lm, n
    assert L.live_menu(R.MENU_FLIPPED).startswith("MESSAGES") and L.live_menu(R.MENU).rstrip().endswith("search_user)")
    assert R.validate({"actions": [{"action": "back"}]}, live=True)["actions"] == [{"action": "back"}]
    try:
        R.validate({"actions": [{"action": "back"}]})
        assert False, "V1 must still refuse live-only actions"
    except ValueError:
        pass


def scripted(p, text, key, tail, budget):
    """A deterministic stand-in for the AI: one of everything, driven by the screen."""
    u, rnd = p["id"], len(text) % 7
    if text.startswith("You searched users"):
        acts = [{"action": "send_message", "username": "user%d" % ((u + 1) % 4), "message": "hi"}]
    elif text.startswith("Your private messages") and "Conversation with u/" in text:
        acts = [{"action": "send_message", "username": text.split("Conversation with u/")[1].split(":")[0], "message": "ok"}]
    elif text.startswith("Your group chats"):
        acts = [{"action": "create_group", "name": f"g{u}"}]
    elif "You're scrolling" in text:
        acts = [{"action": "like_post"}, {"action": "create_comment", "content": f"c{u}"}]
        acts += [[{"action": "search_user", "query": "user%d" % ((u + 1) % 4)}], [{"action": "listen_from_group"}],
                 [{"action": "open_messages"}], [], [], [{"action": "trend"}, {"action": "search_posts", "query": "x"}], []][rnd]
    else:
        acts = []
    return {"actions": acts, "reason": ""}, {"attempts": 1}


def run(rows_in, parallel=1):
    w, out = world(), []

    def emit(p, kind, key, obj, meta, extra):
        r = {"user_id": p["id"], "actions": obj["actions"], **extra}
        out.append(json.loads(json.dumps(r)))
        return r
    feeds = {p["id"]: [q["key"] for q in POSTS if q["author_id"] != p["id"]] for p in PEOPLE}
    shown = lambda *a: "You're scrolling Reddit. " + " | ".join(a)  # noqa: E731
    L.run_live(w, PEOPLE, feeds, scripted, emit, rows_in, shown, "FMT", R.topic_of, parallel, 1, lambda m: None)
    return w, out


def test_run_and_resume_rebuild_the_same_world():
    w_full, rows = run([])
    main = [(r["user_id"], r["seq"]) for r in rows if r["screen"] == "post"]
    assert len(main) == sum(1 for p in PEOPLE for q in POSTS if q["author_id"] != p["id"])  # every post read once
    assert len(set((r["user_id"], r["seq"]) for r in rows)) == len(rows)
    assert {r["screen"] for r in rows} >= {"post", "search_user", "listen_from_group", "open_messages", "trend"}
    assert any(e["error"] == "not opened (one screen at a time)" for r in rows for e in r["executed"])
    assert w_full.dms and w_full.groups and w_full.comments
    for cut in (1, len(rows) // 3, len(rows) - 1):  # a hard kill after `cut` rows, then the same command again
        w2, more = run(rows[:cut])
        assert len(rows[:cut]) + len(more) == len(rows)
        assert rows[:cut] + more == rows, f"resume after {cut} rows differs"
        assert (len(w2.dms), len(w2.groups), len(w2.comments)) == (len(w_full.dms), len(w_full.groups), len(w_full.comments))
