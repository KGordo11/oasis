"""Live world for the reading turn: every action really happens and its result comes back (log 14.47).

IN PLAIN WORDS
--------------
In V1/V2/V3 each screen is one question with no follow-up: the AI sees one post, lists its actions, and nothing comes
back. So search, trending, group chats and messages were dead (the AI even made up group IDs). In a LIVE world:

  * One world per reading cell (one reader AI x one AI's post set). It starts with only that post set and is thrown
    away afterwards, so nothing carries over between cells.
  * Time runs in TICKS. In tick t every user handles the t-th post of their scroll (8 users at a time). Everything a
    user does in tick t (comments, votes, follows, groups, messages, new posts) is seen by OTHER users from tick t+1;
    a user always sees their own actions at once. So the order of users inside a tick does not matter.
  * A post screen now shows the post's comments with their IDs ([c12]) and a notice when the user has new messages.
  * Actions that look something up open a FOLLOW-UP SCREEN with the real result, and the AI answers again there:
      search_posts -> matching posts      trend -> the most-upvoted posts      search_user -> up to 3 profiles
      listen_from_group -> your group chats (their messages) and the groups you can join
      open_messages -> your private messages          open_post -> one post from a list, as a post screen
    At most DETOUR_MAX follow-up screens per post; then the user goes back to scrolling.
  * Private messages (OASIS has none; built the way reference/MutiAgent4Fraud does): send_message works only where
    the person is in front of you (a profile, your inbox), so a DM costs more steps than an upvote, as on the real app.
  * Every screen is one row; "screen" says what kind, "executed" lists each action with ok/failed and why. A failed
    action is recorded, never hidden (OASIS's own rules: e.g. no second upvote, no message to a group you're not in).

The rules copy OASIS's platform.py (like/dislike/follow/mute/report can't be repeated; reposting twice fails; groups:
create = you are its only member, join adds yourself, only members can send/read). Deviation, stated: trending shows
the top LIST_MAX posts (OASIS's default is 1). Stdlib only, so it runs on the Spark (which has no OASIS install).
"""
import json, re, threading

DETOUR_MAX = 4  # follow-up screens per post screen
LIST_MAX = 5    # posts / comments / messages shown per list
NAV = ["search_posts", "search_user", "trend", "listen_from_group", "open_messages", "open_post"]
LIVE_ACTIONS = ["open_messages", "send_message", "open_post", "back"]  # added to the 27 OASIS actions
ON_POST = {"like_post", "unlike_post", "dislike_post", "undo_dislike_post", "create_comment", "repost", "quote_post",
           "report_post"}
MESSAGES_SECTION = """MESSAGES
- open_messages: read your private messages (you can message someone from their profile: search_user)"""
HERE_MENU = """- open_post: open one of the posts listed here  (needs "post_id")
- like_post / dislike_post / repost / report_post / create_comment ... on a post listed here  (add its "post_id")
- search_posts / search_user / trend / listen_from_group / open_messages: go somewhere else
- back: go back to scrolling (an empty list does the same)"""


def live_menu(menu):
    """The study menu with the live changes: comments shown with IDs, group chats open a screen, + MESSAGES."""
    m = (menu.replace("- like_comment / unlike_comment / dislike_comment / undo_dislike_comment  (needs \"comment_id\")",
                      "- like_comment / unlike_comment / dislike_comment / undo_dislike_comment  (needs \"comment_id\", "
                      "shown like [c<number>] under the post)")
             .replace("- listen_from_group: read your group chats",
                      "- listen_from_group: open your group chats (and see the groups you can join)"))
    assert m.count("[c<number>]") == 1 and m.count("open your group chats") == 1, "menu wording changed; update live_menu"
    if "\nMESSAGES\n" in "\n" + m:  # a ranked menu (rank_menu.py) already placed it by its use
        return m
    first = m.split("\n", 1)[0]
    # least-used sections first in the flipped menu (MESSAGES has never been used), last group in the V1 order
    return MESSAGES_SECTION + "\n" + m if first == "GROUP CHATS" else m + "\n" + MESSAGES_SECTION


def _id(v, prefix):
    m = re.fullmatch(rf"\s*{prefix}?\s*(\d+)\s*", str(v), re.I)
    return int(m.group(1)) if m else None


class World:
    def __init__(self, people, posts, topics):
        self.topics, self.lock = topics, threading.RLock()
        self.users = {p["id"]: p["username"] for p in people}
        self.by_name = {u.lower(): i for i, u in self.users.items()}
        self.posts, self.comments, self.groups, self.dms = {}, {}, {}, []
        self.follows, self.mutes = {}, {}  # (a, b) -> tick
        self.next = 1
        for q in posts:
            self._new_post(q["author_id"], q["topic"], q["title"], q["body"], -1, key=q["key"])
        self.pid_of = {p["key"]: i for i, p in self.posts.items()}

    def _id(self):
        self.next += 1
        return self.next - 1

    def _new_post(self, uid, topic, title, body, tick, key=None, quote_of=None):
        i = self._id()
        self.posts[i] = {"id": i, "key": key or f"live|u{uid}|{i}", "author_id": uid, "topic": topic, "title": title,
                         "body": body, "tick": tick, "quote_of": quote_of, "likes": {}, "dislikes": {}, "reposts": {},
                         "reports": {}}
        return i

    @staticmethod
    def vis(obj_tick, owner, me, now):  # others' things from the next tick on; your own at once
        return owner == me or obj_tick < now

    # ---- what a user sees ----
    def comments_of(self, pid, me, now):
        cs = [c for c in self.comments.values() if c["post"] == pid and self.vis(c["tick"], c["user"], me, now)]
        return cs[-LIST_MAX:], len(cs)

    def unseen(self, me, now):
        dms = [d for d in self.dms if d["to"] == me and not d["seen"] and d["tick"] < now]
        gm = sum(1 for g in self.groups.values() if me in g["members"]
                 for m in g["messages"] if m["user"] != me and m["tick"] < now and m["tick"] >= g["members"][me])
        return len(dms), gm

    def post_block(self, pid, me, now):
        q = self.posts[pid]
        sub, tname = self.topics.get(q["topic"], ("r/" + str(q["topic"]), str(q["topic"])))
        cs, n = self.comments_of(pid, me, now)
        lines = [f"Comments ({n}):" if n else "Comments: none yet."]
        if n > len(cs):
            lines.append(f"(the {len(cs)} newest)")
        lines += [f"[c{c['id']}] u/{self.users[c['user']]}: {c['text']}" for c in cs]
        return sub, tname, self.users[q["author_id"]], q["title"], q["body"], "\n".join(lines)

    def notice(self, me, now):
        d, g = self.unseen(me, now)
        parts = ([f"{d} new private message{'s' * (d != 1)} (open_messages)"] if d else []) + \
                ([f"{g} new message{'s' * (g != 1)} in your group chats (listen_from_group)"] if g else [])
        return ("You have " + " and ".join(parts) + ".\n\n") if parts else ""

    def list_posts(self, pids):
        out = []
        for i in pids:
            q = self.posts[i]
            out.append(f"[p{i}] in {self.topics.get(q['topic'], ('r/' + str(q['topic']),))[0]} by "
                       f"u/{self.users[q['author_id']]}: {q['title']} ({sum(1 for c in self.comments.values() if c['post'] == i)} comments)")
        return "\n".join(out)

    def visible_posts(self, me, now):
        return [i for i, q in self.posts.items() if self.vis(q["tick"], q["author_id"], me, now)]

    def search_posts(self, me, now, query):  # OASIS: content LIKE %query%
        ql = str(query).lower()
        hits = [i for i in self.visible_posts(me, now) if ql and ql in (self.posts[i]["title"] + "\n\n" + self.posts[i]["body"]).lower()]
        return hits[:LIST_MAX], len(hits)

    def trend(self, me, now):  # OASIS: ORDER BY num_likes DESC (top_k 1 there; LIST_MAX here)
        def likes(i):
            return sum(1 for u, t in self.posts[i]["likes"].items() if self.vis(t, u, me, now))
        return sorted(self.visible_posts(me, now), key=lambda i: (-likes(i), i))[:LIST_MAX]

    def search_user(self, query):  # OASIS: user_name / name LIKE %query%
        ql = str(query).lower().removeprefix("u/").strip()
        return [i for i, u in self.users.items() if ql and ql in u.lower()][:3]

    def profile(self, uid, me, now):
        fol = sum(1 for (a, b), t in self.follows.items() if b == uid and self.vis(t, a, me, now))
        mine = [i for i, q in self.posts.items() if q["author_id"] == uid and self.vis(q["tick"], uid, me, now)]
        return (f"u/{self.users[uid]}: {len(mine)} post{'s' * (len(mine) != 1)}, {fol} follower{'s' * (fol != 1)}"
                f"{' (you follow them)' if (me, uid) in self.follows else ''}\n"
                + ("\n".join("  " + l for l in self.list_posts(mine[-3:]).split("\n")) if mine else "  (no posts)"))

    def groups_screen(self, me, now):
        mine = [g for g in self.groups.values() if me in g["members"]]
        other = [g for g in self.groups.values() if me not in g["members"] and self.vis(g["tick"], g["owner"], me, now)]
        out = ["Your group chats:" if mine else "Your group chats: none."]
        for g in mine:
            ms = [m for m in g["messages"] if self.vis(m["tick"], m["user"], me, now) and m["tick"] >= g["members"][me]]
            out.append(f"[g{g['id']}] \"{g['name']}\" ({len(g['members'])} members)")
            out += [f"   u/{self.users[m['user']]}: {m['text']}" for m in ms[-LIST_MAX:]] or ["   (no messages yet)"]
        out.append("Other group chats you can join:" if other else "Other group chats you can join: none.")
        out += [f"[g{g['id']}] \"{g['name']}\" ({len(g['members'])} members)" for g in other[-LIST_MAX:]]
        return "\n".join(out)

    def inbox(self, me, now, mark=True):
        with self.lock:
            convo = {}
            for d in self.dms:
                if d["tick"] < now or d["from"] == me:
                    if me in (d["from"], d["to"]):
                        convo.setdefault(d["to"] if d["from"] == me else d["from"], []).append(d)
            out = []
            for other, ds in convo.items():
                out.append(f"Conversation with u/{self.users[other]}:")
                out += [f"   {'you' if d['from'] == me else 'u/' + self.users[d['from']]}: {d['text']}" for d in ds[-LIST_MAX:]]
                if mark:
                    for d in ds:
                        if d["to"] == me:
                            d["seen"] = True
            return "\n".join(out) or "No private messages."

    # ---- doing things (OASIS rules) ----
    def do(self, me, now, a, ctx):
        """Carry out one action. ctx: the post on screen ("post"), the post ids / users shown on this screen
        ("shown_posts", "shown_users"). Returns (ok, error, target)."""
        n = a["action"]
        with self.lock:
            if n in ON_POST or n == "open_post":
                pid = _id(a["post_id"], "p") if a.get("post_id") not in (None, "") else ctx.get("post")
                if pid is None or pid not in self.posts or (pid != ctx.get("post") and pid not in ctx.get("shown_posts", ())):
                    return False, "no such post on this screen", None
                q = self.posts[pid]
                if n == "open_post":
                    return True, None, pid
                rec = {"like_post": "likes", "dislike_post": "dislikes", "repost": "reposts", "report_post": "reports",
                       "unlike_post": "likes", "undo_dislike_post": "dislikes"}.get(n)
                if n in ("like_post", "dislike_post", "repost", "report_post"):
                    if me in q[rec]:
                        return False, f"{n} already done", pid
                    q[rec][me] = now
                elif n in ("unlike_post", "undo_dislike_post"):
                    if me not in q[rec]:
                        return False, "nothing to take back", pid
                    del q[rec][me]
                elif n == "create_comment":
                    c = self._id()
                    self.comments[c] = {"id": c, "post": pid, "user": me, "text": str(a["content"]), "tick": now,
                                        "likes": {}, "dislikes": {}}
                    return True, None, pid
                elif n == "quote_post":
                    self._new_post(me, q["topic"], f"Quote: {q['title']}", str(a["content"]), now, quote_of=pid)
                return True, None, pid
            if n in ("like_comment", "unlike_comment", "dislike_comment", "undo_dislike_comment"):
                cid = _id(a.get("comment_id"), "c")
                c = self.comments.get(cid)
                if c is None or not self.vis(c["tick"], c["user"], me, now):
                    return False, "no such comment", None
                rec = "likes" if "like_comment" in n and "dislike" not in n else "dislikes"
                if n.startswith(("un", "undo")):
                    if me not in c[rec]:
                        return False, "nothing to take back", cid
                    del c[rec][me]
                else:
                    if me in c[rec]:
                        return False, f"{n} already done", cid
                    c[rec][me] = now
                return True, None, cid
            if n in ("follow", "unfollow", "mute", "unmute", "send_message"):
                name = str(a.get("username") or "").strip().removeprefix("u/").lower()
                uid = self.by_name.get(name) if name else (self.posts[ctx["post"]]["author_id"] if ctx.get("post") else None)
                if uid is None:
                    return False, "no such user", None
                if n == "send_message":
                    if uid not in ctx.get("shown_users", ()):
                        return False, "you can only message someone from their profile or your inbox", uid
                    self.dms.append({"from": me, "to": uid, "text": str(a["message"]), "tick": now, "seen": False})
                    return True, None, uid
                book = self.follows if n in ("follow", "unfollow") else self.mutes
                if n in ("follow", "mute"):
                    if (me, uid) in book:
                        return False, f"{n} already done", uid
                    book[(me, uid)] = now
                else:
                    if (me, uid) not in book:
                        return False, "nothing to take back", uid
                    del book[(me, uid)]
                return True, None, uid
            if n == "create_group":
                g = self._id()
                self.groups[g] = {"id": g, "name": str(a["name"]), "owner": me, "tick": now, "members": {me: now},
                                  "messages": []}
                return True, None, g
            if n in ("join_group", "leave_group", "send_to_group"):
                g = self.groups.get(_id(a.get("group_id"), "g"))
                if g is None or not self.vis(g["tick"], g["owner"], me, now):
                    return False, "group does not exist", None
                if n == "join_group":
                    if me in g["members"]:
                        return False, "already in the group", g["id"]
                    g["members"][me] = now
                elif me not in g["members"]:
                    return False, "not a member of this group", g["id"]
                elif n == "leave_group":
                    del g["members"][me]
                else:
                    g["messages"].append({"user": me, "text": str(a["message"]), "tick": now})
                return True, None, g["id"]
            if n == "create_post":
                topic = ctx["topic_of"](a.get("subreddit"))
                return True, None, self._new_post(me, topic, str(a["title"]), str(a["body"]), now)
            return True, None, None  # search_*, trend, listen_from_group, open_messages, refresh, do_nothing, back


def screens():
    """The follow-up screen texts (the post screen is run_v2's READ_SCREEN with comments + notice)."""
    return {
        "search_posts": "You searched posts for \"{query}\". {count}\n{list}\n\nWHAT YOU CAN DO HERE\n" + HERE_MENU,
        "trend": "Trending (the most-upvoted posts right now):\n{list}\n\nWHAT YOU CAN DO HERE\n" + HERE_MENU,
        "search_user": ("You searched users for \"{query}\". {count}\n{list}\n\nWHAT YOU CAN DO HERE\n"
                        "- follow / unfollow / mute / unmute  (needs \"username\")\n"
                        "- send_message: send one of these users a private message  (needs \"username\", \"message\")\n"
                        + HERE_MENU),
        "listen_from_group": ("{list}\n\nWHAT YOU CAN DO HERE\n- create_group  (needs \"name\")\n"
                              "- join_group / leave_group  (needs \"group_id\")\n"
                              "- send_to_group  (needs \"group_id\", \"message\")\n"
                              "- search_posts / search_user / trend / open_messages: go somewhere else\n"
                              "- back: go back to scrolling (an empty list does the same)"),
        "open_messages": ("Your private messages:\n{list}\n\nWHAT YOU CAN DO HERE\n"
                          "- send_message: reply to someone above  (needs \"username\", \"message\")\n"
                          "- search_user: find someone else to message  (needs \"query\")\n"
                          "- back: go back to scrolling (an empty list does the same)"),
    }


def run_live(world, people, feeds, ask, emit, cached, read_screen, fmt, topic_of, parallel, refresh_max, log):
    """Run every user's scroll tick by tick in one live world.
    feeds: user id -> post keys in scroll order. ask(p, text, seed_tail, budget) -> (obj, meta).
    emit(p, kind, key, obj, meta, extra) -> the row, written to disk; it is called inside world.lock, right after the
    row's actions were applied, so the file order is the order the world changed in (resume replays it).
    cached: rows already on disk (resume): their actions are re-applied in file order first, then they are reused."""
    from concurrent.futures import ThreadPoolExecutor
    S = screens()
    by_seq = {}
    for r in cached:  # rebuild the world exactly as it was
        by_seq[(r["user_id"], r["seq"])] = r
        if r["screen"] == "open_messages":
            world.inbox(r["user_id"], r["tick"], mark=True)
        for a, (ok, _, _) in zip(r["actions"], [tuple(e[k] for k in ("ok", "error", "target")) for e in r["executed"]]):
            if ok:
                world.do(r["user_id"], r["tick"], a, {**r["ctx"], "topic_of": topic_of})
    pid = {p["id"]: p for p in people}
    queues = {u: list(f) for u, f in feeds.items()}
    views = {u: {} for u in feeds}
    seq = {u: 0 for u in feeds}

    def render(kind, me, now, arg, key=None):
        ctx = {"shown_posts": [], "shown_users": [], "topic_of": topic_of}
        if kind in ("post", "open_post"):
            i = world.pid_of[key] if key else arg
            ctx["post"] = i
            sub, tname, author, title, body, comments = world.post_block(i, me, now)
            text = world.notice(me, now) + read_screen(sub, tname, author, title, body, comments)
            return text, ctx, world.posts[i]["key"]
        if kind in ("search_posts", "trend"):
            hits, n = world.search_posts(me, now, arg) if kind == "search_posts" else (world.trend(me, now), None)
            ctx["shown_posts"] = hits
            return S[kind].format(query=arg, count=f"{n} found{', the first %d:' % len(hits) if n > len(hits) else ':'}" if n is not None else "",
                                  list=world.list_posts(hits) or "No posts found.") + "\n\n" + fmt, ctx, None
        if kind == "search_user":
            us = world.search_user(arg)
            ctx["shown_users"] = us
            ctx["shown_posts"] = [i for i, q in world.posts.items() if q["author_id"] in us]
            return S[kind].format(query=arg, count=f"{len(us)} found:" if us else "No users found.",
                                  list="\n".join(world.profile(u, me, now) for u in us)) + "\n\n" + fmt, ctx, None
        if kind == "listen_from_group":
            return S[kind].format(list=world.groups_screen(me, now)) + "\n\n" + fmt, ctx, None
        text = world.inbox(me, now)  # open_messages (marks them read)
        ctx["shown_users"] = sorted({d["from"] for d in world.dms if d["to"] == me} | {d["to"] for d in world.dms if d["from"] == me})
        return S["open_messages"].format(list=text) + "\n\n" + fmt, ctx, None

    def unit(u, now):
        p, q = pid[u], queues[u].pop(0)
        views[u][q] = views[u].get(q, 0) + 1
        kind, arg, first = "post", None, None
        for step in range(DETOUR_MAX + 1):
            r = by_seq.get((u, seq[u]))
            if r is None:
                with world.lock:
                    text, ctx, key = render(kind, u, now, arg, q if kind == "post" else None)
                tail = (("view", views[u][q]) if views[u][q] > 1 else ()) if step == 0 else ("live", seq[u])
                obj, meta = ask(p, text, key if step == 0 else None, tail, 800)
                with world.lock:
                    acts = obj["actions"] if obj else []
                    ex, opened = [], None
                    for a in acts:
                        ok, err, tgt = world.do(u, now, a, ctx)
                        if ok and a["action"] in NAV:  # one screen at a time: only the first place asked for opens
                            if opened is not None or step == DETOUR_MAX:
                                ok, err = False, "not opened (one screen at a time)" if opened is not None else \
                                    f"not opened (limit of {DETOUR_MAX} follow-up screens per post)"
                            else:
                                opened = a
                        ex.append({"action": a["action"], "ok": ok, "error": err, "target": tgt})
                    r = emit(p, kind, key, obj, meta, {"screen": kind, "seq": seq[u], "tick": now, "step": step,
                                                      "view": views[u][q] if step == 0 else 0, "executed": ex,
                                                      "ctx": {k: v for k, v in ctx.items() if k != "topic_of"},
                                                      **({"text": text} if kind != "post" else {})})
            seq[u] += 1
            first = first or r
            nav = next((a for a, e in zip(r["actions"], r["executed"]) if a["action"] in NAV and e["ok"]), None)
            if nav is None:
                break
            kind = nav["action"]
            arg = {"search_posts": nav.get("query"), "search_user": nav.get("query"),
                   "open_post": next((e["target"] for e, a in zip(r["executed"], r["actions"]) if a is nav), None)}.get(kind)
            if kind == "open_post" and arg is None:
                break  # the post to open was not on that screen (recorded as failed)
        names = {a["action"] for a in first["actions"]}
        if "refresh" in names and not names & ON_POST and views[u][q] < refresh_max:
            queues[u].insert(1, q)  # V3 refresh loop: the post comes back after the next one

    now = 0
    while any(queues.values()):
        users = [u for u in feeds if queues[u]]
        list(ThreadPoolExecutor(parallel).map(lambda u: unit(u, now), users))
        now += 1
        if now % 10 == 0:
            log(f"  tick {now}: {sum(len(v) for v in queues.values())} post screens left")
