"""TimelineAgent and the agent-graph generator for Simulation 4.

IN PLAIN WORDS
--------------
This is ONE PRETEND PERSON.

It holds that person's personality, shows them their feed, asks the AI what
they want to do, and carries out their choice.

It also enforces one honesty rule: you may only like or reply to a post that
was actually shown to you. Without that rule the AI invents post numbers and
"reacts" to things it never saw, which would make all our measurements
meaningless.

TWO JOBS
--------
1. `TimelineAgent` isolates per-agent failures. `env.step()` gathers all agent
   tasks with a bare `asyncio.gather(*tasks)` (env.py:193) -- no
   `return_exceptions=True` -- so a single agent raising aborts the entire
   round. That is exactly how Sim 3 lost a full 36-agent run to one
   `openai.APITimeoutError`. Since `oasis/` must stay unmodified (D-1), the
   exception is absorbed here instead, at the only other place it can be.

2. `generate_timeline_agents` builds the agent graph from the rich Reddit
   personas, with NO initial follow edges (decision D-10 -- the network
   self-assembles) and no scripted behaviour of any kind (D-6).

WHY THE PERSONA IS FLATTENED INTO ONE STRING
--------------------------------------------
`UserInfo.to_system_message()` forks on `recsys_type`: the Reddit prompt
includes gender/age/MBTI/country, the Twitter prompt includes only
`user_profile` (config/user.py:50-111). This simulation needs the Twitter
platform (follows, reposts, quotes) but the Reddit prompt's richer persona.

Rather than fork the prompt structure, the full persona is composed into the
`user_profile` string that the Twitter prompt already renders. Sim 1 Attempt 1
established that changing prompt *structure* breaks tool-calling outright
(0/36 actions performed); changing prompt *content* is safe. This keeps the
known-good structure and enriches only the content.

It also sidesteps an upstream debug `print()` on the Reddit path
(config/user.py:93) that would spam the console once per agent.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3

from oasis.social_agent.agent import SocialAgent
from oasis.social_agent.agent_environment import SocialEnvironment
from oasis.social_agent.agent_graph import AgentGraph
from oasis.social_platform.config import UserInfo
from oasis.social_platform.database import get_db_path

log = logging.getLogger("social_timeline.agent")

# Bumped whenever the agent-facing prompt changes, and recorded in every run
# manifest. Runs are only comparable to each other at the same version --
# v1 -> v2 changed the action guidance after it was found to be priming
# malformed tool calls (see TimelineEnvironment).
PROMPT_VERSION = 10


class TimelineEnvironment(SocialEnvironment):
    """What the agent sees each turn. Content changed, structure preserved.

    Three measured problems with the stock environment prompt, all of which
    suppress exactly the behaviour this simulation exists to study:

    F-14  `env_template` renders `$groups_env` BEFORE `$posts_env`, and does so
          on every turn regardless of available_actions. Once any group exists,
          a wall of group imperatives sits above the feed in every agent's
          prompt. Measured effect: action_rate 0.469 vs 0.812 without groups.
          Fixed here by putting the feed first and groups last.

    F-11  `get_followers_env` / `get_follows_env` report only a COUNT -- "I have
          3 follows" -- never WHO. Both are marked `# TODO` upstream. An agent
          therefore has no idea who it already follows, and must reverse a
          username out of raw feed JSON to follow anyone. Only 1 follow edge
          appeared in 32 agent-turns. Fixed here by naming names.

    Q-8   The stock closing line reads "Do not limit your action in just `like`
          to like posts", and the user message says "don't limit your actions
          for example to just like the posts". Both are double negatives an 8B
          model can plausibly read as an instruction AGAINST liking -- and zero
          likes were recorded across every run. Reworded positively here.

    Also surfaces the agent's own recent posts, because agents were repeating
    themselves verbatim (10 distinct posts out of 14 in R-6).

    IMPORTANT: this changes prompt CONTENT only. The tool-call schema is
    untouched (D-2). Sim 1 Attempt 1 proved that altering the response
    structure breaks tool-calling outright (0/36 actions); changing what the
    agent reads is safe and is how this project has always tuned behaviour.
    """

    def __init__(self, action, agent_id: int, include_groups: bool = False):
        """Set up one pretend person: their personality, feed, and connection to the AI."""
        super().__init__(action)
        self.agent_id = agent_id
        self.include_groups = include_groups

    def _query(self, sql, params=()):
        """Ask the database a question and hand back the rows."""
        try:
            conn = sqlite3.connect(get_db_path())
            rows = conn.execute(sql, params).fetchall()
            conn.close()
            return rows
        except Exception:  # noqa: BLE001 - the prompt must still render
            return []

    def _usernames(self):
        # B-7: sign_up leaves user_name NULL and puts the handle in `name`
        # (verified in the DB), so COALESCE is required or every author
        # renders as a bare "agentN".
        """Look up display names for a set of person ids."""
        return {r[0]: (r[1] or f"agent{r[0]}")
                for r in self._query(
                    "SELECT agent_id, COALESCE(user_name, name) FROM user")}

    persona_text = None      # set by TimelineAgent when F-66 hoisting is on

    async def to_text_prompt(self, *args, **kwargs) -> str:
        """Turn this person's feed into the text the AI actually reads."""
        names = self._usernames()
        me = names.get(self.agent_id, f"agent{self.agent_id}")

        # --- the feed, first and named -----------------------------------
        result = await self.action.refresh()
        lines = []
        if result.get("success") and result.get("posts"):
            for p in result["posts"]:
                author = names.get(p.get("user_id"), f"agent{p.get('user_id')}")
                entry = {
                    "post_id": p.get("post_id"),
                    # F-22 REVERTED. v7 glued the id into this string as
                    # "name (followee_id=7)" on the theory that the model
                    # reaches for a number next to the person. It backfired
                    # badly: malformed calls 169 -> 429, with follow() being
                    # handed post_id 145 times, because burying a key=value
                    # pair inside a JSON *value* made the object harder to
                    # read and the model grabbed the first id it saw. Keep the
                    # id in its own field, named exactly as the tool expects.
                    "author": author,
                    # v3: named `followee_id`, not `author_id`. At v2 this key
                    # was `author_id` and the model copied the FIELD name into
                    # the call -- follow(author_id=5) failed 19 times. Field
                    # names in the feed are the names the model reaches for, so
                    # they must match the tool parameter exactly.
                    "followee_id": p.get("user_id"),
                    "content": p.get("content"),
                    "likes": p.get("num_likes"),
                    "dislikes": p.get("num_dislikes"),
                }
                comments = p.get("comments") or []
                if comments:
                    entry["comments"] = [{
                        "comment_id": c.get("comment_id"),
                        "by": names.get(c.get("user_id"),
                                        f"agent{c.get('user_id')}"),
                        "followee_id": c.get("user_id"),
                        "content": c.get("content"),
                    } for c in comments[:3]]
                lines.append(entry)
            feed = ("Here is your feed. Each post shows who wrote it:\n"
                    + json.dumps(lines, indent=1))
        else:
            # F-28. The old wording -- "a good moment to post something
            # yourself" -- invited an introduction, and round 0 has an empty
            # feed for everyone at once. 77% of round-0 posts were "just
            # joined / excited to be here", which then became the entire feed
            # and set the register for the whole run: agents mimic what they
            # read, and vague posts beget vague posts.
            #
            # Measured context: posts in-run are 0.809 similar to each other,
            # while the same model prompted cold writes concrete things
            # ("attended a panel on supply chain innovation"). The sameness is
            # partly self-inflicted by what round 0 seeds.
            #
            # This says nothing about what to write, only removes the cue that
            # produced 36 simultaneous hellos.
            feed = ("Your feed is empty -- nothing has been posted that you "
                    "can see.")

        # --- who you already follow, by name (F-11) -----------------------
        following = [names.get(r[0], f"agent{r[0]}") for r in self._query(
            "SELECT followee_id FROM follow WHERE follower_id = ?",
            (self.agent_id, ))]
        followers = [names.get(r[0], f"agent{r[0]}") for r in self._query(
            "SELECT follower_id FROM follow WHERE followee_id = ?",
            (self.agent_id, ))]
        social = (f"You are {me}. "
                  + (f"You follow: {', '.join(following)}. "
                     if following else "You do not follow anyone yet. ")
                  + (f"Following you: {', '.join(followers)}."
                     if followers else "Nobody follows you yet."))

        # --- how your own posts have landed (F-27) -------------------------
        # An agent could not tell whether anything it wrote had reached anyone.
        # In R-17, 21 posts drew likes and 36 drew comments, and none of that
        # was ever visible to their authors: they were posting into a void,
        # which is a plausible reason 64% of all actions were create_post.
        #
        # Every real platform shows this. It is information, not instruction --
        # no one is told to engage more, they are simply told what happened,
        # which is the feedback loop a social network runs on.
        mine_stats = self._query(
            "SELECT post_id, num_likes, num_dislikes, "
            "(SELECT COUNT(*) FROM comment WHERE comment.post_id = post.post_id)"
            " FROM post WHERE user_id = ? ORDER BY post_id DESC LIMIT 5",
            (self.agent_id, ))
        landed = [r for r in mine_stats if (r[1] or r[2] or r[3])]
        if landed:
            reception = ("How your recent posts have landed:\n" + json.dumps(
                [{"post_id": r[0], "likes": r[1], "dislikes": r[2],
                  "replies": r[3]} for r in landed], indent=1))
        elif mine_stats:
            reception = ("None of your posts have had any likes or replies "
                         "yet.")
        else:
            reception = ""

        # --- replies to your own posts, i.e. notifications (F-21) ---------
        # An agent's own posts are excluded from its feed, which is correct --
        # nobody is shown their own content by a recommender. But the comments
        # on those posts live *under* them, so an agent never saw a single
        # reply it received. Measured in R-13: 17 posts drew multiple comments
        # and the author replied back on **zero** of them. That is not
        # conversation, it is parallel monologue.
        #
        # Every real platform closes this with notifications. This is the
        # notification tab: replies you received, which you can answer.
        replies = self._query(
            "SELECT c.comment_id, c.post_id, c.user_id, c.content "
            "FROM comment c JOIN post p ON c.post_id = p.post_id "
            "WHERE p.user_id = ? AND c.user_id != ? "
            "ORDER BY c.comment_id DESC LIMIT 6", (self.agent_id,
                                                   self.agent_id))
        if replies:
            lines_r = [
                {"comment_id": cid, "on_your_post_id": pid,
                 "from": names.get(uid, f"agent{uid}"),
                 "followee_id": uid, "said": content}
                for cid, pid, uid, content in replies
            ]
            notifications = ("People replied to YOUR posts. You can reply back "
                             "with create_comment(post_id=..., content=...), "
                             "like their reply with like_comment(comment_id="
                             "...), or follow them:\n"
                             + json.dumps(lines_r, indent=1))
        else:
            notifications = "Nobody has replied to your posts yet."

        # --- your own recent posts, so you do not repeat yourself ---------
        mine = [r[0] for r in self._query(
            "SELECT content FROM post WHERE user_id = ? "
            "ORDER BY post_id DESC LIMIT 3", (self.agent_id, ))]
        own = ("You have not posted yet." if not mine else
               "You already posted these -- do NOT repeat them, say something "
               "new:\n" + "\n".join(f"- {m[:160]}" for m in mine))

        # --- groups, last and only when they exist (F-14) -----------------
        groups = await self.get_group_env() if self.include_groups else ""

        # --- guidance, v2 (Q-8 and F-15) ----------------------------------
        # v1 phrased this as a prose list ("- follow(followee_id) to follow an
        # author...") and repeatedly used the word "action". The full 36-agent
        # run then produced 393 malformed calls against 260 successful ones --
        # follow alone failed 189 times to 55 successes. The dominant error was
        # `got an unexpected keyword argument 'action'`, i.e. the model emitting
        # follow(action="follow", followee_id=5); others echoed the function
        # name itself, follow(follow=...) or create_comment(create_comment=...).
        # The word "action" in the guidance was priming the very mistake.
        #
        # v2 therefore drops that word entirely, shows exact signatures with
        # real parameter names taken from agent_action.py, and says explicitly
        # not to wrap the call or repeat the function name.
        guidance = (
            "You can do any of these, as many or as few as you feel like -- "
            "including nothing at all. Copy the id values straight out of the "
            "feed above:\n"
            "  post_id      -> use with like_post, dislike_post, "
            "create_comment, repost, quote_post\n"
            "  followee_id  -> use with follow (this is the person, not the "
            "post)\n"
            "  comment_id   -> use with like_comment only\n"
            "\n"
            "  like_post(post_id=N)\n"
            "  dislike_post(post_id=N)\n"
            "  create_comment(post_id=N, content=\"your reply\")\n"
            "  follow(followee_id=N)\n"
            "  repost(post_id=N)\n"
            "  quote_post(post_id=N, quote_content=\"your take\")\n"
            "  like_comment(comment_id=N)\n"
            "  create_post(content=\"something new\")\n"
            "\n"
            "Pass only the parameters listed. Never add a parameter that is "
            "not in the signature above, and never repeat the function name "
            "as a parameter.\n"
            "Do whatever fits you and what you have just read.")

        # F-66: when the persona has been hoisted out of the system message so
        # every agent shares a cacheable prefix, it is reinstated here -- first,
        # so the agent still reads who it is before it reads its feed.
        who = (f"You are {self.persona_text}" if self.persona_text else None)

        return "\n\n".join(x for x in
                           [who, social, feed, reception, notifications, own,
                            groups, guidance] if x)


class TimelineAgent(SocialAgent):
    """A SocialAgent whose per-round failure cannot take down the round."""

    # F-64. Upstream ships each action's full Python docstring as its tool
    # description: ~3,759 tokens across 22 actions, against ~1,000 for the
    # persona, the twelve-post feed and the instructions combined. Eighty
    # percent of every prompt was API documentation the model does not need --
    # `search_user` alone is 302 tokens explaining a return dictionary.
    #
    # These replacements say what the action DOES, in the vocabulary the feed
    # already uses. Signatures, parameters and names are untouched, so D-2
    # holds: the tool-call schema is unchanged and only the prose describing it
    # is shorter. Measured: 5.10s -> 3.53s per turn, 4,761 -> 1,320 prompt
    # tokens, and tool-call reliability went UP rather than down.
    #
    # It also removes F-65's truncation risk outright. At NUM_PARALLEL=8 a
    # sequence gets 4,096 tokens of context and the old prompt was 4,761, so
    # prompts were being silently cut; at ~1,300 there is no slot count where
    # that can happen.
    # F-83. Actions whose RETURN VALUE the model needs to see. Everything else
    # is terminal: the effect is already committed to the database and the
    # follow-up call teaches the agent nothing. `do_nothing` is terminal by
    # definition. Keep this list conservative -- a wrongly-terminal action
    # silently removes a capability, which is the failure --lean-actions has.
    INFORMATIONAL = frozenset({"search_user", "search_posts", "trend",
                               "refresh"})

    TERSE = {
        "create_post":          "Write a new post.",
        "create_comment":       "Reply to a post you were shown.",
        "like_post":            "Like a post you were shown.",
        "unlike_post":          "Remove your like from a post.",
        "dislike_post":         "Dislike a post you were shown.",
        "undo_dislike_post":    "Remove your dislike from a post.",
        "like_comment":         "Like a comment.",
        "unlike_comment":       "Remove your like from a comment.",
        "dislike_comment":      "Dislike a comment.",
        "undo_dislike_comment": "Remove your dislike from a comment.",
        "repost":               "Repost a post to your own followers.",
        "quote_post":           "Repost a post with your own comment added.",
        "report_post":          "Report a post, with a reason.",
        "follow":               "Follow a person, so their posts reach you.",
        "unfollow":             "Stop following a person.",
        "mute":                 "Mute a person.",
        "unmute":               "Unmute a person.",
        "search_user":          "Search for people by name or bio.",
        "search_posts":         "Search posts by their text.",
        "trend":                "See the most-liked recent posts.",
        "refresh":              "Fetch your feed again.",
        "do_nothing":           "Do nothing this turn.",
    }

    # Parameter descriptions, same principle. The names are already explicit.
    TERSE_PARAMS = {
        "post_id":       "id of the post, copied from the feed",
        "comment_id":    "id of the comment",
        "followee_id":   "id of the person",
        "mutee_id":      "id of the person",
        "content":       "the text to write",
        "quote_content": "your comment on the post",
        "query":         "what to search for",
        "report_reason": "why you are reporting it",
    }

    def __init__(self, *args, terse_tools: bool = True,
                 shared_prefix: bool = True,
                 max_tool_rounds: int | None = None,
                 smart_tool_loop: bool = False,
                 fresh_context: bool = False,
                 include_groups: bool = False, **kwargs):
        """Set up the agent wrapper that survives errors without killing the run."""
        super().__init__(*args, **kwargs)
        self.action_failures = 0

        if terse_tools:
            self._shorten_tool_descriptions()
        # Q-23. camel's tool loop is `while True`: it calls the model, runs
        # whatever tools came back, then calls the model AGAIN so it can react
        # to the results, and repeats until the model stops asking for tools.
        # `max_iteration=None` (its default) means unlimited. Measured cost:
        # 1.31 model calls per agent turn, so ~24% of all LLM work is the
        # follow-up call.
        #
        # For this simulation the follow-up is close to worthless: the actions
        # have already been executed and written to the database by then, and
        # the model's closing prose is discarded. Setting this to 1 stops after
        # the first round of tool calls.
        #
        # It is NOT the default, because the risk is real: an agent that wants
        # to take a second action in a second round-trip would lose it, and
        # turns average 1.70 actions. That is an A/B, not an assumption.
        if max_tool_rounds is not None:
            self.max_iteration = max_tool_rounds

        # F-83. The measured version of the paragraph above, and a better fix
        # than a blunt cap. In a full 15-round run of 504 agent turns:
        #
        #     turns with 0 or 1 action      499  (99.0 %)
        #     turns with 2 or more            5  ( 1.0 %)
        #     actions returning content the model must read:  0 of 431
        #
        # Every action taken was terminal -- a like, a follow, a post. The
        # follow-up model call shows the agent a result it does not use, so it
        # can take a second action once in a hundred turns. That follow-up is
        # ~46 % of all LLM calls in a run.
        #
        # `max_tool_rounds=1` removes it, but also removes the search -> read
        # -> act path the action surface is supposed to permit. The conditional
        # version keeps that path and drops the rest: stop after terminal
        # actions, keep going after informational ones. The action surface is
        # untouched, unlike --lean-actions (F-55).
        self.smart_tool_loop = smart_tool_loop

        # F-86. Every turn appends the user message, the assistant reply and
        # the tool result to this agent's memory, and all of it is re-prefilled
        # next turn. Measured on bank_r5: request latency runs 10.1 s at round 0,
        # 86.2 s by round 4, then flat -- the context filling to
        # OLLAMA_CONTEXT_LENGTH and truncating. Round 0 costs 94 s of wall
        # clock; rounds 4+ cost ~790 s, and the difference is re-reading
        # history.
        #
        # With this on, each turn starts from the system message alone, so
        # every round costs about what round 0 costs.
        #
        # The behavioural question is open and this is OFF by default. Note the
        # agent is ALREADY losing most of its history to truncation at 8192
        # tokens -- it gets an arbitrary sliding window, not coherent memory --
        # so the change may be smaller than it sounds. That is an argument, not
        # a result. A/B it against the bank (F-85: 2-5 runs, not a campaign).
        self.fresh_context = fresh_context
        self.context_resets = 0
        self._base_max_iteration = self.max_iteration
        self.short_circuits = 0

        self.shared_prefix = shared_prefix
        self.persona_text = None
        if shared_prefix:
            self._hoist_persona_out_of_system()
        # Swap in the environment that names names and leads with the feed.
        # Reuses the SocialAction the base class already wired to the channel,
        # so nothing about the action/tool path changes (D-2).
        # B-7: use social_agent_id, NOT agent_id. SocialAgent stores the
        # integer id as `social_agent_id` (agent.py:71); `agent_id` is camel's
        # own UUID. Passing the UUID made every follow/own-post lookup silently
        # return nothing, so agents were always told "you do not follow anyone".
        self.env = TimelineEnvironment(self.env.action,
                                       agent_id=self.social_agent_id,
                                       include_groups=include_groups)
        # F-66: the persona was taken out of the system message so every agent
        # shares a cacheable prefix. It has to arrive somewhere, so the
        # environment prepends it to the per-turn message. Same words, later.
        self.env.persona_text = self.persona_text

    def _hoist_persona_out_of_system(self):
        """Make the system message identical for every agent (F-66).

        Ollama caches prompt prefixes and serves a hit at ~20,000 tok/s against
        ~490 for a cold prompt -- a 40x difference on the 78% of a turn that is
        prefill. The simulation was defeating that cache by construction: the
        prompt is laid out

            [ system: OBJECTIVE + THIS AGENT'S PERSONA ] [ tools ] [ user: feed ]

        and because the persona sits at the FRONT, no two of the 36 agents share
        a prefix and the cache never hits. Every agent paid ~5.5s to re-read the
        same tool block.

        This moves the persona out of the system message and into the per-turn
        user message, leaving a system message that is byte-identical across
        agents. Measured 6.92s -> 1.20s from the second agent onward.

        The agent is told exactly the same things about itself. Only the message
        it arrives in changes, so no action is removed and no output constrained
        -- but it IS a prompt change, and per F-35 must be judged against
        baseline rather than assumed harmless.
        """
        try:
            full = self.system_message.content
        except Exception:  # noqa: BLE001
            return
        # The persona lives under "# SELF-DESCRIPTION" in upstream's template
        # (oasis/social_platform/config/user.py). Everything else is shared.
        marker = "# SELF-DESCRIPTION"
        if marker not in full:
            self.persona_text = None
            return
        head, _, rest = full.partition(marker)
        # Keep any trailing shared sections (e.g. "# RESPONSE METHOD").
        tail = ""
        for nxt in ("# RESPONSE METHOD", "# OBJECTIVE"):
            if nxt in rest:
                _, _, tail = rest.partition(nxt)
                tail = nxt + tail
                rest = rest[:rest.index(nxt)]
                break
        self.persona_text = rest.strip()
        shared = (head + tail).strip()
        # `system_message` is a read-only property on ChatAgent; the backing
        # field is `_system_message`, and init_messages() rebuilds the memory
        # from it. Assigning the property raises, so set the field and re-init.
        from camel.messages import BaseMessage
        self._system_message = BaseMessage.make_assistant_message(
            role_name="system", content=shared)
        try:
            self.init_messages()
        except Exception as exc:  # noqa: BLE001
            agent_log.debug("init_messages after persona hoist: %s", exc)

    def _shorten_tool_descriptions(self):
        """Swap each tool's docstring for a one-line description (F-64).

        Only the human-readable description changes. Names, parameters and
        types are untouched, so the model is offered exactly the same actions
        with exactly the same call signatures.
        """
        swapped = 0
        for tool in (getattr(self, "action_tools", None) or []):
            name = getattr(getattr(tool, "func", None), "__name__", None)
            terse = self.TERSE.get(name)
            if not terse:
                continue
            try:
                tool.set_function_description(terse)
                # Parameter descriptions are the other half of the weight:
                # "The ID of the post to which the comment is to be added."
                # where the parameter is already named `post_id` and typed
                # integer. The name and type carry the meaning; the sentence
                # is restating them at ~15 tokens each across 22 tools.
                for pname, pterse in self.TERSE_PARAMS.items():
                    try:
                        tool.set_parameter_description(pname, pterse)
                    except Exception:  # noqa: BLE001, S112
                        pass          # tool simply lacks that parameter
                swapped += 1
            except Exception as exc:  # noqa: BLE001
                # A camel version that names this differently must not take
                # the run down; the long description is merely wasteful.
                agent_log.debug("could not shorten %s: %s", name, exc)
        self.terse_tools_applied = swapped

    async def _aexecute_tool(self, tool_call_request):
        """Run the tool, then decide whether a follow-up call is worth making.

        camel reads `self.max_iteration` immediately AFTER this returns
        (chat_agent.py:2070), so mutating it here takes effect on this same
        iteration. That is why this needs no change to upstream.
        """
        record = await super()._aexecute_tool(tool_call_request)
        if self.smart_tool_loop:
            name = getattr(tool_call_request, "tool_name", None)
            if name in self.INFORMATIONAL:
                # The agent asked for information; it must get a turn to read it.
                self.max_iteration = self._base_max_iteration
            else:
                self.max_iteration = 1
                self.short_circuits += 1
        return record

    async def perform_action_by_llm(self):
        """Show this person their feed, ask the AI what to do, and do it."""
        # Each turn starts from the configured budget; a previous turn's
        # short-circuit must not leak into this one.
        if self.smart_tool_loop:
            self.max_iteration = self._base_max_iteration
        if self.fresh_context:
            # init_messages() rebuilds memory from the system message alone.
            # The persona lives in the system message (or, when hoisted, is
            # re-sent with the feed), so identity survives; only the transcript
            # of previous rounds is dropped.
            try:
                self.init_messages()
                self.context_resets += 1
            except Exception as exc:  # noqa: BLE001 - never fail a turn
                agent_log.debug("fresh_context reset failed: %s", exc)
        try:
            return await super().perform_action_by_llm()
        except Exception as exc:  # noqa: BLE001 - deliberate: never propagate
            self.action_failures += 1
            # Logged rather than swallowed silently. A run that quietly loses
            # agents looks identical to a run where agents chose to do
            # nothing, and those are very different results.
            log.warning("agent %s failed to act: %s: %s", self.agent_id,
                        type(exc).__name__, exc)
            return None


def compose_persona(entry: dict) -> str:
    """Flatten one persona record into the profile string the prompt renders.

    Source fields come from data/reddit/user_data_36.json:
    realname, username, bio, persona, age, gender, mbti, country,
    profession, interested_topics.
    """
    parts = [entry.get("persona") or entry.get("bio") or ""]

    demographics = []
    if entry.get("gender"):
        demographics.append(str(entry["gender"]))
    if entry.get("age"):
        demographics.append(f"{entry['age']} years old")
    if entry.get("country"):
        demographics.append(f"from {entry['country']}")
    if demographics:
        parts.append("You are " + ", ".join(demographics) + ".")

    if entry.get("mbti"):
        parts.append(f"Your MBTI personality type is {entry['mbti']}.")
    if entry.get("profession"):
        parts.append(f"You work in {entry['profession']}.")
    topics = entry.get("interested_topics")
    if topics:
        parts.append("You are especially interested in "
                     + ", ".join(topics) + ".")

    return " ".join(p for p in parts if p).strip()


async def generate_timeline_agents(
    profile_path: str,
    model=None,
    available_actions=None,
    limit: int | None = None,
    smart_tool_loop: bool = False,
    fresh_context: bool = False,
    include_groups: bool = False,
    diverse: bool = True,
    terse_tools: bool = True,
    shared_prefix: bool = True,
    max_tool_rounds: int | None = None,
) -> AgentGraph:
    """Build the agent graph. No follow edges, no scripted actions.

    Args:
        profile_path: JSON persona file (Reddit persona schema).
        model: camel model backend shared by all agents.
        available_actions: the ActionType list agents may call.
        limit: use only the first N personas. Small runs come first (D-11),
            and this is how a stage dials itself down.
    """
    from personas import describe, load_personas, select_diverse

    entries = load_personas(profile_path)
    # Take a maximally-separated subset rather than the first N: an
    # interest-based feed can only distinguish people to the degree they
    # differ, so the sample should span the population, not whatever the file
    # happened to list first. Measured effect on the twitter set at k=36:
    # mean pairwise similarity 0.689 (first-36) -> 0.637 (diverse-36).
    if limit is not None and limit < len(entries):
        entries = (select_diverse(entries, limit) if diverse
                   else entries[:limit])
    separability = describe(entries)
    log.info("persona population: %s", separability)

    agent_graph = AgentGraph()

    async def build(i: int, entry: dict):
        """Create all the pretend people, each with their own personality."""
        profile = {
            "nodes": [],
            "edges": [],
            "other_info": {
                # The Twitter prompt reads only this key, so the whole
                # persona is composed into it.
                "user_profile": compose_persona(entry),
                # Retained for analysis and reporting, not read by the prompt.
                "mbti": entry.get("mbti"),
                "gender": entry.get("gender"),
                "age": entry.get("age"),
                "country": entry.get("country"),
                "profession": entry.get("profession"),
                "interested_topics": entry.get("interested_topics"),
                "realname": entry.get("realname"),
                "handle": entry.get("username"),
            },
        }
        # The DISPLAY NAME is the person's real name from the persona file --
        # "James Miller", not "millerhospitality" and certainly not "user_98".
        # Every table, graph label, transcript line and feed entry keys off
        # this, so a reader can point at a node and know exactly who it is.
        # sign_up stores it in user.name, which is what everything downstream
        # reads (COALESCE(user_name, name)).
        display = (entry.get("realname") or entry.get("username")
                   or f"agent{i}")
        user_info = UserInfo(
            name=display,
            description=entry["bio"],
            profile=profile,
            # "twitter" selects the Twitter system prompt; see module docstring.
            recsys_type="twitter",
        )
        agent = TimelineAgent(
            terse_tools=terse_tools,
            shared_prefix=shared_prefix,
            max_tool_rounds=max_tool_rounds,
            smart_tool_loop=smart_tool_loop,
            fresh_context=fresh_context,
            include_groups=include_groups,
            agent_id=i,
            user_info=user_info,
            agent_graph=agent_graph,
            model=model,
            available_actions=available_actions,
        )
        agent_graph.add_agent(agent)

    await asyncio.gather(*(build(i, e) for i, e in enumerate(entries)))
    agent_graph.persona_separability = separability
    return agent_graph
