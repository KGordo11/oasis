"""Ask the inference server what it is actually doing, and refuse to run blind.

IN PLAIN WORDS
--------------
Before a simulation starts, this asks the model server one question: how much
text can you actually hold in one conversation? If the answer is smaller than
the prompt we are about to send, the run is stopped. Otherwise the answer is
written down in the run's own record, so anyone reading the results later can
see what the machine was set to.

WHY THIS EXISTS
---------------
B-28. An overnight sweep of six runs was made with `OLLAMA_NUM_PARALLEL=4` and
no `OLLAMA_CONTEXT_LENGTH`, so the server used its 4,096-token default. The
simulation's prompt is ~2,730 tokens before an agent has said anything, and the
transcript pushes it past 4,096 inside one round. Every prompt was cut. The feed
sits at the END of the prompt, so the feed is what was lost.

The failure was invisible in the obvious place. Wall clock went DOWN, because
truncated prompts are cheap to process, and that read as a clean scaling result.
Engagement -- the thing the study measures -- fell from 6.8 % to 2.5 % at an
otherwise identical configuration. The runs looked faster and were emptier.

This is the fourth error in this project traceable to a setting nothing
recorded: F-65 (prompts truncated by a context split nobody checked), F-77 (a
concurrency recommendation built on a serialising server), F-85 (a noise floor
computed across runs that were not identical), and now B-28. F-65 even states
the rule -- "anyone raising NUM_PARALLEL must raise OLLAMA_CONTEXT_LENGTH with
it" -- and it was read on the night the mistake was made. A written warning is
not a control.
"""
from __future__ import annotations

import json
import os
import urllib.request

DEFAULT_URL = "http://localhost:11434"

# The prompt is ~2,730 tokens with no transcript (F-93's measurement of the
# terse-tool configuration). Agents accumulate history every turn, so the window
# must have real headroom above that, not merely clear it.
MIN_CONTEXT = 8192


def probe(url: str = DEFAULT_URL, opener=None, timeout: float = 5.0) -> dict:
    """What is the server's per-slot context? None means 'could not tell'.

    Note for anyone reading Ollama's docs: in 0.24 `OLLAMA_CONTEXT_LENGTH` is
    the PER-SLOT window and is not divided by `OLLAMA_NUM_PARALLEL`. F-65
    described it as divided, which was true of an earlier version. Measured
    directly: NUM_PARALLEL=4 with CONTEXT_LENGTH=8192 reports 8192 per slot.
    """
    open_ = opener or urllib.request.urlopen
    # Callers pass the OpenAI-compatible base ("…:11434/v1"), but /api/ps sits
    # at the server root. Appending blindly gives /v1/api/ps and a 404, which
    # this module would then report as "cannot verify" -- a false refusal that
    # is just as bad as the false pass it exists to prevent.
    url = (url or "").rstrip("/")
    if url.endswith("/v1"):
        url = url[:-3]
    state = {
        "context_length": None,
        "source": "api/ps",
        # Recorded for completeness, but it is the CLIENT's environment and says
        # nothing about the server -- which is exactly how B-28 slipped through.
        "num_parallel_env": os.environ.get("OLLAMA_NUM_PARALLEL", "(unset)"),
        "context_length_env": os.environ.get("OLLAMA_CONTEXT_LENGTH", "(unset)"),
    }
    try:
        with open_(f"{url}/api/ps", timeout=timeout) as r:
            models = (json.loads(r.read()) or {}).get("models") or []
        if models:
            state["context_length"] = models[0].get("context_length")
            state["model"] = models[0].get("name")
    except Exception as exc:  # noqa: BLE001 -- any failure is "could not tell"
        state["error"] = str(exc)
    return state


def verify(state: dict, need: int = MIN_CONTEXT) -> tuple[bool, str]:
    """Is this window big enough? Unknown is a refusal, not a pass."""
    got = state.get("context_length")
    if got is None:
        return False, (
            "cannot read the server's context length from /api/ps"
            + (f" ({state['error']})" if state.get("error") else
               " -- no model is loaded, so send one request first")
            + ". Refusing to run: B-28 happened because nothing checked."
        )
    if got < need:
        return False, (
            f"server context is {got} tokens per slot, need at least {need}. "
            f"The prompt is ~2,730 tokens before the agent has said anything and "
            f"grows every turn, so at {got} it will be silently truncated -- and "
            f"the feed sits at the END of the prompt, so the feed is what is lost. "
            f"This does not show up as an error; it shows up as a FASTER run with "
            f"less engagement (B-28). Fix:\n"
            f"      OLLAMA_NUM_PARALLEL=4 OLLAMA_CONTEXT_LENGTH={need} ollama serve"
        )
    return True, f"server context {got} tokens per slot (need {need})"


def manifest_block(state: dict) -> dict:
    """The fields a future reader needs to know what the machine was set to."""
    return {
        "server_context_length": state.get("context_length"),
        "server_model": state.get("model"),
        "server_probe_source": state.get("source"),
        "server_probe_error": state.get("error"),
        "server_num_parallel_env": state.get("num_parallel_env"),
        "server_context_length_env": state.get("context_length_env"),
    }
