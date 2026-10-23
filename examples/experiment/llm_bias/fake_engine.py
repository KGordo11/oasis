"""A fake llama.cpp server for laptop tests: answers like an AI would, with no model (smoke_test.py, log 14.47).

    python fake_engine.py PORT [REQUEST_LOG.jsonl]

It speaks the three endpoints llm.py uses (/health, /props, /v1/chat/completions) and picks actions by reading the
screen, deterministically from the request's seed, so a rerun gets the same answers:
  posting screen      one create_post (sometimes two), in a subreddit from the list
  post screen         a mix of like/dislike/comment/refresh/report, and sometimes a trip: search_user (the poster),
                      search_posts, trend, listen_from_group, open_messages, like_comment on a shown [cN]
  follow-up screens   search results -> open_post / like a listed post; profiles -> follow or send_message;
                      group chats -> create, join a listed group, or send to one of yours; messages -> reply
Every request is appended to REQUEST_LOG (think on/off, JSON mode on/off, which menu came first, screen kind), so a
test can check that each run sent exactly the intended settings.
"""
import json, random, re, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = open(sys.argv[2], "a") if len(sys.argv) > 2 else None
SUBS = ["r/politics", "r/technology", "r/business", "r/sports", "r/entertainment"]


def answer(u, rng):
    a = []
    if "nothing has been posted yet" in u or "have no posts yet" in u:
        for k in range(1 + (rng.random() < 0.2)):
            a.append({"action": "create_post", "subreddit": rng.choice(SUBS), "title": f"Fake title {rng.randrange(999)}",
                      "body": f"Fake body about things {rng.randrange(999)}."})
        return a
    posts, comments = re.findall(r"\[p(\d+)\]", u), re.findall(r"\[c(\d+)\]", u)
    groups_mine = re.findall(r"\[g(\d+)\][^\n]*\n   ", u.split("Other group chats")[0])
    groups_other = re.findall(r"\[g(\d+)\]", u.split("Other group chats")[-1]) if "Other group chats" in u else []
    users = re.findall(r"^u/(\S+):", u, re.M) + re.findall(r"Conversation with u/(\S+):", u)
    if u.startswith(("You searched posts", "Trending")):
        return [{"action": "open_post", "post_id": f"p{posts[0]}"}] if posts and rng.random() < 0.5 else \
               ([{"action": "like_post", "post_id": posts[-1]}] if posts else [{"action": "back"}])
    if u.startswith("You searched users"):
        if users and rng.random() < 0.6:
            return [{"action": "send_message", "username": users[0], "message": "hey, saw your post"}]
        return [{"action": "follow", "username": users[0]}] if users else []
    if u.startswith("Your group chats"):
        if groups_other:
            return [{"action": "join_group", "group_id": groups_other[-1]}]
        if groups_mine:
            return [{"action": "send_to_group", "group_id": f"g{groups_mine[0]}", "message": "hi all"}]
        return [{"action": "create_group", "name": f"fans {rng.randrange(99)}"}]
    if u.startswith("Your private messages"):
        return [{"action": "send_message", "username": users[0], "message": "thanks!"}] if users else []
    # a post screen
    author = re.search(r"posted by u/(\S+?):", u)
    r = rng.random()
    a.append({"action": rng.choice(["like_post", "like_post", "dislike_post"])})
    if r < 0.25:
        a.append({"action": "create_comment", "content": "fake comment"})
    if comments and rng.random() < 0.3:
        a.append({"action": "like_comment", "comment_id": f"c{comments[-1]}"})
    if "open_messages)" in u and rng.random() < 0.7:
        a.append({"action": "open_messages"})
    trip = rng.random()
    if trip < 0.08 and author:
        a.append({"action": "search_user", "query": author.group(1)})
    elif trip < 0.28:  # often enough that 6 users always make, join and use groups (smoke_test checks it)
        a.append({"action": "listen_from_group"})
    elif trip < 0.31:
        a.append({"action": "trend"})
    elif trip < 0.34:
        a.append({"action": "search_posts", "query": "Fake"})
    elif trip < 0.37:
        a = [{"action": "refresh"}]
    return a


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, o):
        b = json.dumps(o).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._send({"status": "ok"} if self.path == "/health" else {"model_path": "fake", "total_slots": 8,
                                                                     "build_info": "fake", "chat_template": "fake"})

    def do_POST(self):
        p = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        u = p["messages"][-1]["content"]
        think = bool((p.get("chat_template_kwargs") or {}).get("enable_thinking"))
        if LOG:
            menu = u[u.find("WHAT YOU CAN DO"):]
            LOG.write(json.dumps({"model": p.get("model"), "think": think, "json": "response_format" in p, "two": '...the fields it needs}, {"action"' in u,
                                  "seed": p.get("seed"), "menu_first": menu.split("\n")[1] if "\n" in menu else "",
                                  "screen": u[:60]}) + "\n"); LOG.flush()
        rng = random.Random(p.get("seed"))
        reply = json.dumps({"actions": answer(u, rng), "reason": "fake"})
        self._send({"choices": [{"message": {"content": reply, "reasoning_content": "thinking..." if think else ""},
                                 "finish_reason": "stop"}], "usage": {"prompt_tokens": len(u) // 4, "completion_tokens": 20}})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
