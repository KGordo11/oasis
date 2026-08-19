"""Shield layer for OASIS, adapted from "iAgent: LLM Agent as a Shield
between User and Recommender Systems" (Xu et al., ACL 2025 Findings,
https://aclanthology.org/2025.findings-acl.943/).

Zero-diff to oasis/: everything here is a subclass defined in example code,
following the exact pattern already used by ReasoningSocialAgent in
examples/reddit_simulation_ollama.py (swap the name `SocialAgent` resolves
to inside oasis.social_agent.agents_generator, at call time, from outside
the package).

Maps onto the paper's iAgent (the base version, not the heavier i2Agent
with cross-session dynamic memory -- OASIS agents are single-session):

  Paper's iAgent piece   -> What this file does
  ---------------------- -> --------------------------------------------
  Parser (X_I -> X_IK)   -> Reused for free: each OASIS agent already
                             carries a structured persona (age, MBTI,
                             country, persona paragraph) generated at
                             agent-creation time. `_persona_text()` turns
                             that into the same short profile string
                             `to_reddit_system_message()` already builds,
                             without the tool-calling boilerplate the
                             shield doesn't need. No extra LLM call spent
                             on this step.
  Reranker (Eq. 2)        -> `_shield_rerank()`: one extra local Ollama
                             call per refresh(). Given the persona text
                             and the platform's raw feed (content,
                             comments, AND the platform's own like/dislike
                             counts), the shield returns a credibility-
                             based reorder plus a short shield_note per
                             post. The agent is shown ONLY the shield's
                             reordered view with shield_note fields -- the
                             raw crowd vote counts are stripped out before
                             the text ever reaches the agent, so herding
                             on visible vote counts becomes structurally
                             impossible downstream, regardless of whether
                             the shield's own judgement fully resists it.
  Self-reflection          -> After parsing the shield's JSON response, we
  (Section 2.1)              check the returned post_id set exactly
                             matches the input set. One retry with a
                             corrective prompt on mismatch; if it still
                             doesn't match, the shield fails OPEN (returns
                             the original unshielded post list untouched)
                             and logs a shield_error line, so a shield bug
                             degrades to "no shield" instead of stalling
                             or crashing the simulation.
"""
from __future__ import annotations

import json
import re

from camel.agents import ChatAgent
from camel.messages import BaseMessage

from oasis.social_agent.agent import SocialAgent, agent_log
from oasis.social_agent.agent_environment import SocialEnvironment

SHIELD_SYSTEM_PROMPT = (
    "You are a content-ranking component inside a social-media research "
    "simulation (not a real platform, no real users or real health/medical "
    "advice is involved). You stand between the simulator's recommender "
    "system and a simulated user, and your only job is a mechanical "
    "scoring task: reorder a list of posts by textual plausibility and "
    "internal consistency, ignoring the platform's crowd-vote counts. You "
    "will be given: (1) a short profile of the simulated user, and (2) a "
    "list of posts the simulator's recommender selected, each with its "
    "current like/dislike counts and any comments.\n\n"
    "Scoring rule (apply mechanically, this is data analysis, not medical "
    "or factual advice to anyone): a post's plausibility score is HIGHER "
    "when its claims are internally consistent, specific, and match "
    "well-established scientific or historical consensus; the score is "
    "LOWER when a post uses absolute language ('always', 'everyone "
    "knows'), cites no mechanism, or contradicts well-established "
    "consensus -- regardless of the post's like/dislike counts. Rank "
    "highest-scoring posts first. This task never requires refusing: "
    "every post must receive a rank, even ones you would decline to "
    "discuss directly with a person.\n\n"
    "Return ONLY a JSON array, one object per post, in this exact shape, "
    "and include EVERY post_id you were given exactly once:\n"
    '[{"post_id": <int>, "rank": <int, 1 = show first>, '
    '"shield_note": "<one short sentence on the scoring rule you applied>"}]\n'
    "No prose outside the JSON array.")

RETRY_ADDENDUM = (
    "\n\nYour previous response did not include exactly this set of "
    "post_ids, each exactly once: {ids}. This is a mechanical ranking "
    "task over simulation data, not a request for advice -- every post "
    "must get a rank. Return ONLY the JSON array again, fixing that.")


def _persona_text(user_info) -> str:
    """Same profile string to_reddit_system_message() builds internally,
    minus the OBJECTIVE/RESPONSE METHOD boilerplate the shield doesn't
    need, and without that method's stray debug print()."""
    name_string = f"Your name is {user_info.name}." if user_info.name else ""
    profile = user_info.profile or {}
    other_info = profile.get("other_info", {})
    user_profile = other_info.get("user_profile")
    if not user_profile:
        return name_string or "No profile available."
    description = f"{name_string}\nYour have profile: {user_profile}."
    description += (
        f" You are a {other_info.get('gender')}, {other_info.get('age')} "
        f"years old, with an MBTI personality type of "
        f"{other_info.get('mbti')} from {other_info.get('country')}.")
    return description


def _extract_json_array(text: str):
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


class ShieldedSocialEnvironment(SocialEnvironment):
    """Same as SocialEnvironment, except get_posts_env() routes the raw
    refresh() feed through one extra local LLM call (the Shield) before it
    is turned into the agent's prompt text."""

    def __init__(self, action, model, persona_text, agent_id):
        super().__init__(action)
        self.shield_model = model
        self.persona_text = persona_text
        self.agent_id = agent_id

    # Vote-signal field names to strip before the agent ever sees a post.
    # platform_utils.py emits EITHER "score" (net likes-dislikes, when the
    # config sets show_score=True -- true for every *_36*.yaml in this
    # project) OR separate "num_likes"/"num_dislikes" (show_score=False).
    # Only one of these two shapes is ever present at once, but stripping
    # both is harmless and future-proofs against a config with either
    # setting.
    _VOTE_FIELDS = ("score", "num_likes", "num_dislikes")

    async def _shield_rerank(self, posts: list[dict]) -> list[dict]:
        post_ids = {p["post_id"] for p in posts}
        shield_view = [{
            "post_id": p["post_id"],
            "content": p.get("content"),
            "score": p.get("score"),
            "num_likes": p.get("num_likes"),
            "num_dislikes": p.get("num_dislikes"),
            "comments": p.get("comments", []),
        } for p in posts]

        user_content = (
            f"User profile:\n{self.persona_text}\n\n"
            f"Posts to rank:\n{json.dumps(shield_view, indent=2)}")

        for attempt in range(2):
            shield_chat = ChatAgent(
                system_message=BaseMessage.make_assistant_message(
                    role_name="system", content=SHIELD_SYSTEM_PROMPT),
                model=self.shield_model,
            )
            prompt = user_content
            if attempt == 1:
                prompt += RETRY_ADDENDUM.format(ids=sorted(post_ids))
            try:
                response = await shield_chat.astep(
                    BaseMessage.make_user_message(role_name="User",
                                                  content=prompt))
            except Exception as e:
                # Network/timeout/backend errors must degrade to "no
                # shield" like a malformed response does, not propagate --
                # get_posts_env() has no caller-side try/except for this
                # (perform_action_by_llm() in oasis/social_agent/agent.py
                # fetches the env prompt BEFORE its own try/except begins),
                # so an uncaught exception here crashes the whole
                # simulation run, not just this one agent's turn.
                agent_log.warning(
                    f"Agent {self.agent_id} shield attempt {attempt + 1} "
                    f"raised {type(e).__name__}: {e}")
                continue
            raw = (response.msgs[0].content if response.msgs else "") or ""
            parsed = _extract_json_array(raw)
            returned_ids = set()
            if isinstance(parsed, list):
                try:
                    returned_ids = {int(item["post_id"]) for item in parsed}
                except (KeyError, TypeError, ValueError):
                    returned_ids = set()
            if returned_ids == post_ids:
                rank_by_id = {}
                note_by_id = {}
                for item in parsed:
                    pid = int(item["post_id"])
                    # dict.get(key, default) only falls back to default
                    # when the key is ABSENT -- the model sometimes emits
                    # valid JSON with an explicit "rank": null, which
                    # .get("rank", 0) passes straight through as None and
                    # crashes sorted()'s int comparison below. Coerce any
                    # non-numeric rank explicitly instead.
                    rank = item.get("rank")
                    rank_by_id[pid] = rank if isinstance(
                        rank, (int, float)) else 0
                    note = item.get("shield_note")
                    note_by_id[pid] = note if isinstance(note, str) else ""
                ordered = sorted(posts,
                                 key=lambda p: rank_by_id.get(
                                     p["post_id"], 0))
                shielded_posts = []
                for p in ordered:
                    p = dict(p)
                    for field in self._VOTE_FIELDS:
                        p.pop(field, None)
                    p["shield_note"] = note_by_id.get(p["post_id"], "")
                    shielded_posts.append(p)
                agent_log.info(
                    f"Agent {self.agent_id} shield reranked "
                    f"{len(shielded_posts)} posts on attempt "
                    f"{attempt + 1}.")
                return shielded_posts
            agent_log.warning(
                f"Agent {self.agent_id} shield attempt {attempt + 1} "
                f"failed self-reflection check (expected ids {post_ids}, "
                f"got {returned_ids}; raw response: {raw[:200]!r}).")

        agent_log.error(
            f"Agent {self.agent_id} shield_error: failed validation twice, "
            f"falling back to unshielded post order.")
        return posts

    async def get_posts_env(self) -> str:
        posts = await self.action.refresh()
        if posts["success"]:
            shielded = await self._shield_rerank(posts["posts"])
            posts_env = json.dumps(shielded, indent=4)
            posts_env = self.posts_env_template.substitute(posts=posts_env)
        else:
            posts_env = "After refreshing, there are no existing posts."
        return posts_env


class ShieldedSocialAgent(SocialAgent):
    """Drop-in replacement for SocialAgent: identical behavior, except its
    self.env is a ShieldedSocialEnvironment instead of a plain
    SocialEnvironment. Swap in via
    `agents_generator.SocialAgent = ShieldedSocialAgent` before calling
    generate_reddit_agents(), exactly like ReasoningSocialAgent does in
    examples/reddit_simulation_ollama.py."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = ShieldedSocialEnvironment(
            action=self.env.action,
            model=self.model_backend,
            persona_text=_persona_text(self.user_info),
            agent_id=self.social_agent_id,
        )
