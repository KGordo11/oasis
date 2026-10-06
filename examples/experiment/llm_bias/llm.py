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

import os as _os

# OLLAMA_URL lets a shared machine (the DGX Spark) use a private Ollama on its own port instead of 11434
OLLAMA_URL = _os.environ.get("OLLAMA_URL", "http://localhost:11434")
NUM_CTX = 8192
TIMEOUT_S = 300
# LLM_BACKEND=llamacpp sends requests to llama.cpp servers (one per model) instead of Ollama, using the SAME model
# files. LLAMACPP_URLS maps each model name to its server, e.g. {"qwen3:8b": "http://127.0.0.1:11601"}.
# A different engine is a different setup: every round of one study must use the same backend.
BACKEND = _os.environ.get("LLM_BACKEND", "ollama")
LLAMACPP_URLS = json.loads(_os.environ.get("LLAMACPP_URLS", "{}"))
# LD-41: on llama.cpp every model gets the SAME sampling settings (Ollama silently applied a different top_k/top_p/
# repeat penalty per model from each Modelfile). Temperature still comes from the caller (0.7 for every model).
SAMPLING = {"top_k": 40, "top_p": 0.9, "min_p": 0.0, "repeat_penalty": 1.0}


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
    meta = {"model": model, "backend": BACKEND, "attempts": 0, "errors": [],
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
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        payload = {"model": model, "stream": False, "think": False, "format": "json", "options": opts,
                   "messages": msgs}
        t = time.time()
        try:
            r = _post("/api/chat", payload, timeout) if BACKEND == "ollama" else _llamacpp(model, msgs, opts, timeout)
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


def _llamacpp(model, msgs, opts, timeout):
    """One chat request to the model's llama.cpp server, returned in Ollama's response shape."""
    payload = {"model": model, "messages": msgs, "stream": False, "temperature": opts["temperature"],
               "max_tokens": opts["num_predict"], "response_format": {"type": "json_object"},
               "chat_template_kwargs": {"enable_thinking": False},  # same as Ollama's think=False
               **SAMPLING}
    if "seed" in opts:
        payload["seed"] = opts["seed"]
    req = urllib.request.Request(LLAMACPP_URLS[model] + "/v1/chat/completions", json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        r = json.load(resp)
    c = r["choices"][0]
    return {"message": {"content": c["message"].get("content") or "",
                        "thinking": c["message"].get("reasoning_content") or ""},
            "prompt_eval_count": r.get("usage", {}).get("prompt_tokens"),
            "eval_count": r.get("usage", {}).get("completion_tokens"),
            "done_reason": c.get("finish_reason")}


def _get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.load(r)


def loaded_models():
    try:
        return [m["name"] for m in _post_get("/api/ps").get("models", [])]
    except Exception:
        return []


def _post_get(path):
    with urllib.request.urlopen(OLLAMA_URL + path, timeout=10) as r:
        return json.load(r)


def server_up():
    if BACKEND == "llamacpp":  # LB-v2-3: any ONE healthy server counts -- a stopped server must not end the check
        return bool(available_models())
    try:
        _post_get("/api/tags")
        return True
    except Exception:
        return False


def available_models():
    if BACKEND == "llamacpp":
        up = []
        for m, u in LLAMACPP_URLS.items():
            try:
                if _get(u + "/health").get("status") == "ok":
                    up.append(m)
            except Exception:
                pass
        return up
    return [m["name"] for m in _post_get("/api/tags").get("models", [])]


def model_digests(names):
    """Exact build of each model (name -> digest), so a run can be tied to the weights it used."""
    if BACKEND == "llamacpp":  # the server reports the model file; Ollama's blob files are named by digest
        out = {}
        for n in names:
            try:
                out[n] = "llamacpp:" + _get(LLAMACPP_URLS[n] + "/props").get("model_path", "").split("sha256-")[-1]
            except Exception:
                out[n] = None
        return out
    tags = {m["name"]: m.get("digest") for m in _post_get("/api/tags").get("models", [])}
    return {n: tags.get(n) for n in names}


def warm(model):
    """Load a model before timing anything (B-40: a cold model inflates the first round)."""
    if BACKEND == "llamacpp":
        _llamacpp(model, [{"role": "user", "content": "hi"}], {"temperature": 0, "num_predict": 1}, TIMEOUT_S)
        return
    _post("/api/generate", {"model": model, "prompt": "hi", "stream": False,
                            "options": {"num_ctx": NUM_CTX, "num_predict": 1}}, TIMEOUT_S)


def stable_seed(*parts):
    """Reproducible 31-bit seed from any parts (Python's hash() is salted per process)."""
    import hashlib
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8], 16) % (2**31)


def server_config(log_path=None):
    """The running Ollama server's own settings, read from the config line it logs at start-up.

    Records what the SERVER used (flash attention, parallel slots, context), which the
    client's environment cannot tell us. Returns {} if the log is not found.
    """
    import os
    import re as _re
    if BACKEND == "llamacpp":  # each server reports its own settings
        out = {"backend": "llamacpp"}
        for m, u in LLAMACPP_URLS.items():
            try:
                p = _get(u + "/props")
                out[m] = {"total_slots": p.get("total_slots"), "build": p.get("build_info"),
                          "n_ctx": (p.get("default_generation_settings") or {}).get("n_ctx")}
            except Exception:
                out[m] = None
        return out
    log_path = log_path or os.environ.get("OLLAMA_SERVE_LOG", "/tmp/ollama_serve.log")
    try:
        lines = [ln for ln in open(log_path, errors="replace") if "server config" in ln]
    except OSError:
        return {}
    if not lines:
        return {}
    keys = ("OLLAMA_FLASH_ATTENTION", "OLLAMA_NUM_PARALLEL", "OLLAMA_CONTEXT_LENGTH", "OLLAMA_KV_CACHE_TYPE",
            "OLLAMA_KEEP_ALIVE", "OLLAMA_MAX_LOADED_MODELS")
    out = {}
    for k in keys:
        m = _re.search(rf"{k}:(\S*)", lines[-1])
        if m:
            out[k] = m.group(1).rstrip("]")
    return out
