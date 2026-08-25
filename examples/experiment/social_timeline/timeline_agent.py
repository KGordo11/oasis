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

from oasis.social_agent.agent import SocialAgent
from oasis.social_agent.agent_graph import AgentGraph
from oasis.social_platform.config import UserInfo

log = logging.getLogger("social_timeline.agent")


class TimelineAgent(SocialAgent):
    """A SocialAgent whose per-round failure cannot take down the round."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action_failures = 0

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
            agent_id=i,
            user_info=user_info,
            agent_graph=agent_graph,
            model=model,
            available_actions=available_actions,
        )
        agent_graph.add_agent(agent)

    await asyncio.gather(*(build(i, e) for i, e in enumerate(entries)))
    return agent_graph
