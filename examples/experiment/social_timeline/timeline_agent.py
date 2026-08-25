"""TimelineAgent and the agent-graph generator for Simulation 4.

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
PROMPT_VERSION = 2


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
        super().__init__(action)
        self.agent_id = agent_id
        self.include_groups = include_groups

    def _query(self, sql, params=()):
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
        return {r[0]: (r[1] or f"agent{r[0]}")
                for r in self._query(
                    "SELECT agent_id, COALESCE(user_name, name) FROM user")}

    async def to_text_prompt(self, *args, **kwargs) -> str:
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
                    "author": author,
                    # follow() takes an integer id, not a name, so the id has
                    # to be visible or the action is uncallable in practice.
                    "author_id": p.get("user_id"),
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
                        "content": c.get("content"),
                    } for c in comments[:3]]
                lines.append(entry)
            feed = ("Here is your feed. Each post shows who wrote it:\n"
                    + json.dumps(lines, indent=1))
        else:
            feed = ("Your feed is empty right now -- nobody you can see has "
                    "posted yet. This is a good moment to post something "
                    "yourself.")

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
            "Call one or more of these functions directly. Use exactly these "
            "parameter names and pass nothing else:\n"
            "  create_post(content=\"...\")\n"
            "  create_comment(post_id=N, content=\"...\")\n"
            "  like_post(post_id=N)\n"
            "  dislike_post(post_id=N)\n"
            "  like_comment(comment_id=N)\n"
            "  follow(followee_id=N)\n"
            "  repost(post_id=N)\n"
            "  quote_post(post_id=N, quote_content=\"...\")\n"
            "N is a number you read from the feed above: use post_id for a "
            "post, author_id for a person, comment_id for a comment. Do not "
            "wrap the call in an extra parameter, and do not pass a parameter "
            "named after the function itself.\n"
            "Replying to and following other people is usually more "
            "interesting than only posting your own thoughts.")

        return "\n\n".join(x for x in
                           [social, feed, own, groups, guidance] if x)


class TimelineAgent(SocialAgent):
    """A SocialAgent whose per-round failure cannot take down the round."""

    def __init__(self, *args, include_groups: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.action_failures = 0
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

    async def perform_action_by_llm(self):
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
    include_groups: bool = False,
) -> AgentGraph:
    """Build the agent graph. No follow edges, no scripted actions.

    Args:
        profile_path: JSON persona file (Reddit persona schema).
        model: camel model backend shared by all agents.
        available_actions: the ActionType list agents may call.
        limit: use only the first N personas. Small runs come first (D-11),
            and this is how a stage dials itself down.
    """
    with open(profile_path, "r") as fh:
        entries = json.load(fh)
    if limit is not None:
        entries = entries[:limit]

    agent_graph = AgentGraph()

    async def build(i: int, entry: dict):
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
            },
        }
        user_info = UserInfo(
            name=entry["username"],
            description=entry["bio"],
            profile=profile,
            # "twitter" selects the Twitter system prompt; see module docstring.
            recsys_type="twitter",
        )
        agent = TimelineAgent(
            include_groups=include_groups,
            agent_id=i,
            user_info=user_info,
            agent_graph=agent_graph,
            model=model,
            available_actions=available_actions,
        )
        agent_graph.add_agent(agent)

    await asyncio.gather(*(build(i, e) for i, e in enumerate(entries)))
    return agent_graph
