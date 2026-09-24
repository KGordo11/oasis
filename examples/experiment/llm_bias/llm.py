"""One small client for local Ollama models. Every model call in the project goes through here.

IN PLAIN WORDS
--------------
Sends one chat request to the local Ollama server and asks for a JSON answer.
Returns the parsed JSON plus the bookkeeping a run needs: how long it took, how
many tokens went in and out, and how many attempts it needed.

Two guards, both learned the hard way in Sim 4:

* B-22: every request has a timeout. A request that never returns used to hang
  a whole run for 24 hours.
* B-28: the context window is set on EVERY request (`num_ctx`), not left to the
  server default, and any prompt that comes back using >= 95 % of the window is
  flagged as possibly truncated. Sim 4 lost days to a 4096-token default that
  silently cut the feed and made runs look faster.

Only local Ollama models are used (Gordon, 2026-09-23: no Claude / Gemini / paid
APIs). The `backend` field exists so a second provider could be added later
without touching callers; today the only backend is "ollama".
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request

OLLAMA_URL = "http://localhost:11434"
NUM_CTX = 8192
TIMEOUT_S = 300


class LLMError(RuntimeError):
    pass


def _post(path, payload, timeout):
    req = urllib.request.Request(OLLAMA_URL + path, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def extract_json(text):
    """Parse a JSON object out of model text. Tolerates code fences and chatter around it."""
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError("no JSON object in response")


def chat_json(model, system, user, *, seed=None, temperature=0.7, num_predict=400,
              validate=None, retries=2, timeout=TIMEOUT_S):
    """Call `model` and return (obj, meta).

    `validate(obj)` may raise ValueError to force a retry (bad label, missing field).
    Each retry uses seed+attempt so it is a genuinely new sample, still reproducible.
    """
    meta = {"model": model, "backend": "ollama", "attempts": 0, "errors": [],
            "latency_s": 0.0, "prompt_tokens": 0, "eval_tokens": 0, "truncation_risk": False,
            # why generation stopped ("stop" = finished; "length" = hit num_predict) and how much
            # hidden reasoning came back -- the two things to check when a model "does nothing"
            "done_reason": None, "thinking_chars": 0, "timeouts": 0}
    last_raw = None
    for attempt in range(retries + 1):
        meta["attempts"] = attempt + 1
        opts = {"temperature": temperature, "num_ctx": NUM_CTX, "num_predict": num_predict}
        if seed is not None:
            opts["seed"] = int(seed) + attempt
        # think=False: gemma4 is a "thinking" model and otherwise spends the whole token
        # budget on hidden reasoning and returns empty content (0/16 valid on first smoke).
        # Set for every model so no author or judge gets a hidden drafting step the others lack.
        payload = {"model": model, "stream": False, "think": False, "format": "json", "options": opts,
                   "messages": [{"role": "system", "content": system},
                                {"role": "user", "content": user}]}
        t = time.time()
        try:
            r = _post("/api/chat", payload, timeout)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            meta["errors"].append(f"transport: {e}")
            if "timed out" in str(e).lower():
                meta["timeouts"] += 1
            meta["latency_s"] += time.time() - t
            continue
        meta["latency_s"] += time.time() - t
        meta["prompt_tokens"] = r.get("prompt_eval_count") or 0
        meta["eval_tokens"] += r.get("eval_count") or 0
        if meta["prompt_tokens"] >= 0.95 * NUM_CTX:
            meta["truncation_risk"] = True
        last_raw = r.get("message", {}).get("content", "")
        meta["done_reason"] = r.get("done_reason")
        meta["thinking_chars"] += len(r.get("message", {}).get("thinking") or "")
        meta["raw"] = last_raw
        try:
            obj = extract_json(last_raw)
            if validate:
                obj = validate(obj) or obj
            return obj, meta
        except (ValueError, KeyError, TypeError) as e:
            meta["errors"].append(f"invalid: {e}")
    meta["raw"] = last_raw
    return None, meta


def loaded_models():
    try:
        return [m["name"] for m in _post_get("/api/ps").get("models", [])]
    except Exception:
        return []


def _post_get(path):
    with urllib.request.urlopen(OLLAMA_URL + path, timeout=10) as r:
        return json.load(r)


def server_up():
    try:
        _post_get("/api/tags")
        return True
    except Exception:
        return False


def available_models():
    return [m["name"] for m in _post_get("/api/tags").get("models", [])]


def warm(model):
    """Load a model before timing anything (B-40: a cold model inflates the first round)."""
    _post("/api/generate", {"model": model, "prompt": "hi", "stream": False,
                            "options": {"num_ctx": NUM_CTX, "num_predict": 1}}, TIMEOUT_S)


def stable_seed(*parts):
    """Reproducible 31-bit seed from any parts (Python's hash() is salted per process)."""
    import hashlib
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8], 16) % (2**31)
