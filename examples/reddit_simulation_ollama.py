import asyncio
import os
from camel.models import ModelFactory
from camel.types import ModelPlatformType
import oasis
from oasis import (ActionType, LLMAction, ManualAction,
                   generate_reddit_agent_graph)
from oasis.social_agent import agents_generator
from oasis.social_agent.agent import SocialAgent, agent_log, ALL_SOCIAL_ACTIONS

# ============================================================================
# Reasoning capture — added entirely in this example script, on purpose.
# Nothing under oasis/ is modified. This subclass only overrides two things:
#   1. The system prompt gets one extra sentence inviting (not requiring)
#      the model to explain its reasoning alongside a tool call.
#   2. perform_action_by_llm additionally logs that reasoning text, if any,
#      to the same log file every other agent already writes to.
# The reasoning-first wording ("explain, then call the function") was tried
# and rejected: it broke tool-calling entirely (0/36 real actions in
# testing). Making it optional restored tool-calling (35/36) while still
# occasionally capturing reasoning text.
# ============================================================================
REASONING_ADDENDUM = (
    " You may optionally include one short sentence about your feeling or "
    "reasoning in your message alongside the tool call, but you must "
    "always call one of the provided functions — never write a function "
    "call out as plain text or JSON.")


class ReasoningSocialAgent(SocialAgent):

    def __init__(self, *args, **kwargs):
        user_info = kwargs.get("user_info")
        if user_info is not None:
            original_to_system_message = user_info.to_system_message

            def patched_to_system_message():
                return original_to_system_message() + REASONING_ADDENDUM

            user_info.to_system_message = patched_to_system_message
        super().__init__(*args, **kwargs)

    async def perform_action_by_llm(self):
        from camel.messages import BaseMessage
        env_prompt = await self.env.to_text_prompt()
        user_msg = BaseMessage.make_user_message(
            role_name="User",
            content=(
                f"Please perform social media actions after observing the "
                f"platform environments. Notice that don't limit your "
                f"actions for example to just like the posts. "
                f"Here is your social media environment: {env_prompt}"))
        try:
            agent_log.info(
                f"Agent {self.social_agent_id} observing environment: "
                f"{env_prompt}")
            response = await self.astep(user_msg)
            if response.msgs:
                reasoning_text = (response.msgs[0].content or "").strip()
                if reasoning_text:
                    agent_log.info(f"Agent {self.social_agent_id} "
                                   f"reasoning: {reasoning_text}")
            for tool_call in response.info['tool_calls']:
                action_name = tool_call.tool_name
                args = tool_call.args
                agent_log.info(f"Agent {self.social_agent_id} performed "
                               f"action: {action_name} with args: {args}")
                if action_name not in ALL_SOCIAL_ACTIONS:
                    agent_log.info(
                        f"Agent {self.social_agent_id} get the result: "
                        f"{tool_call.result}")
                return response
        except Exception as e:
            agent_log.error(f"Agent {self.social_agent_id} error: {e}")
            return e


# Swap in our subclass for the duration of this script only. generate_reddit_
# agent_graph (in oasis/social_agent/agents_generator.py) references the name
# `SocialAgent` at call time, so this redirects agent construction without
# touching that file.
agents_generator.SocialAgent = ReasoningSocialAgent


async def main():
    # Use Ollama (free, local) instead of OpenAI.
    # llama3.1:8b matches the paper's Llama-3-8B-Instruct in size, and unlike
    # the original Llama 3, it has native tool-calling support (verified via
    # `ollama show llama3.1:8b` -> Capabilities: completion, tools). OASIS
    # agents act by calling tools, so this is required, not just a nicety.
    ollama_model = ModelFactory.create(
        model_platform=ModelPlatformType.OLLAMA,
        model_type="llama3.1:8b",
        url="http://localhost:11434/v1",
    )

    # Define the available actions for the agents
    available_actions = ActionType.get_default_reddit_actions()

    # Load the 36 agent profiles
    agent_graph = await generate_reddit_agent_graph(
        profile_path="./data/reddit/user_data_36.json",
        model=ollama_model,
        available_actions=available_actions,
    )

    # Define the path to the database
    db_path = "./data/reddit_simulation.db"
    os.environ["OASIS_DB_PATH"] = os.path.abspath(db_path)

    # Delete the old database so we start fresh
    if os.path.exists(db_path):
        os.remove(db_path)

    # Make the environment
    env = oasis.make(
        agent_graph=agent_graph,
        platform=oasis.DefaultPlatformType.REDDIT,
        database_path=db_path,
    )

    # Run the environment
    await env.reset()

    # Timestep 1 — manually seed the platform with a post
    actions_1 = {}
    actions_1[env.agent_graph.get_agent(0)] = [
        ManualAction(action_type=ActionType.CREATE_POST,
                     action_args={"content": "Hello, world!"}),
        ManualAction(action_type=ActionType.CREATE_COMMENT,
                     action_args={
                         "post_id": "1",
                         "content": "Welcome to the OASIS World!"
                     })
    ]
    actions_1[env.agent_graph.get_agent(1)] = ManualAction(
        action_type=ActionType.CREATE_COMMENT,
        action_args={
            "post_id": "1",
            "content": "I like the OASIS world."
        })
    await env.step(actions_1)

    # Timestep 2 — all agents act freely using their LLM
    actions_2 = {
        agent: LLMAction()
        for _, agent in env.agent_graph.get_agents()
    }
    await env.step(actions_2)

    # Close the environment
    await env.close()
    print("Simulation complete! Database saved to:", db_path)

if __name__ == "__main__":
    asyncio.run(main())