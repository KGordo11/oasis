# flake8: noqa: E402
"""Shielded variant of reddit_simulation_counterfactual.py.

Zero-diff to reddit_simulation_counterfactual.py's `running()`: this reuses
it unmodified and only swaps which agent class agents_generator.py resolves
to at call time, exactly like ReasoningSocialAgent does in
examples/reddit_simulation_ollama.py. Same CLI, same config format -- point
it at down_36_shielded.yaml (identical to down_36.yaml except db_path) to
run the shielded counterpart of the existing down-condition baseline.
"""
import argparse
import asyncio
import os

from yaml import safe_load

from oasis.social_agent import agents_generator

from reddit_simulation_counterfactual import running
from shield_agent import ShieldedSocialAgent

agents_generator.SocialAgent = ShieldedSocialAgent

parser = argparse.ArgumentParser(description="Arguments for script.")
parser.add_argument(
    "--config_path",
    type=str,
    help="Path to the YAML config file.",
    required=False,
    default="",
)

if __name__ == "__main__":
    args = parser.parse_args()

    if os.path.exists(args.config_path):
        with open(args.config_path, "r") as f:
            cfg = safe_load(f)
        data_params = cfg.get("data")
        simulation_params = cfg.get("simulation")
        inference_params = cfg.get("inference")

        asyncio.run(
            running(
                **data_params,
                **simulation_params,
                inference_configs=inference_params,
            ),
            debug=True,
        )
    else:
        asyncio.run(running())
