"""Stage 0 dependency check for Simulation 4 (social timeline).

IN PLAIN WORDS
--------------
This is the PRE-FLIGHT CHECK. Run it before starting a simulation.

It makes sure everything the run needs is actually working: the AI model loads,
the text-to-numbers model behaves, and the numbers come out the same twice in a
row. If something is broken it says so now, instead of you finding out two
hours into a run.

Verifies every external dependency the simulation relies on BEFORE any
simulation code is written or run, so that a failure here costs seconds
rather than a multi-hour run.

Exercises the real OASIS code paths (`get_recsys_model`,
`generate_post_vector`) rather than an approximation, so that what passes
here is what the simulation will actually call.

Checks:
  1. TwHIN-BERT downloads, loads, and reports its device.
  2. It produces sane embeddings, and cosine similarity behaves as the
     recommendation algorithm assumes (related text scores above unrelated).
  3. Ollama is reachable and llama3.1:8b is present.

Run:  oasis-env/bin/python examples/experiment/social_timeline/check_deps.py
Exits non-zero on any failure.

See SIM4_LOG.md (Part I) section 9 (Q-1) and the design spec section 9, stage 0.
"""

import sys
import time

results = []


def check(name):
    """Decorator that records pass/fail and keeps going after a failure."""

    def wrap(fn):
        """Run one check and report whether it passed, without crashing the rest."""
        print(f"\n--- {name} ---")
        start = time.time()
        try:
            detail = fn()
            elapsed = time.time() - start
            print(f"PASS  ({elapsed:.1f}s)  {detail}")
            results.append((name, True, detail, elapsed))
        except Exception as exc:  # noqa: BLE001 - report, never abort the suite
            elapsed = time.time() - start
            print(f"FAIL  ({elapsed:.1f}s)  {type(exc).__name__}: {exc}")
            results.append((name, False, f"{type(exc).__name__}: {exc}", elapsed))
        return fn

    return wrap


@check("torch device availability")
def _torch_device():
    """Check which hardware the maths will run on (CPU or GPU)."""
    import torch

    cuda = torch.cuda.is_available()
    mps = torch.backends.mps.is_available()
    # recsys.py:85 selects cuda-or-cpu only, so MPS goes unused. Recorded in
    # SIM4_LOG.md (Part I) section 4 as a known performance ceiling.
    from oasis.social_platform.recsys import device as recsys_device

    return (f"cuda={cuda} mps={mps}; OASIS will use device={recsys_device!r} "
            f"(MPS unused by design, recsys.py:85)")


@check("TwHIN-BERT loads via the real OASIS path")
def _twhin_loads():
    """Check the text-to-numbers model downloads and loads."""
    from oasis.social_platform.recsys import get_recsys_model

    tokenizer, model = get_recsys_model(recsys_type="twhin-bert")
    n_params = sum(p.numel() for p in model.parameters())
    return (f"tokenizer={type(tokenizer).__name__} "
            f"model={type(model).__name__} params={n_params/1e6:.0f}M "
            f"device={next(model.parameters()).device}")


# Two topics, two texts each. A single topic pair cannot distinguish a real
# signal from a lucky random projection, which is exactly how the first
# version of this gate passed while bugs B-1/B-2 were live.
PROBE_TEXTS = [
    # topic A: travel / hospitality
    "Passionate about hospitality and tourism, exploring new destinations.",
    "Just got back from an amazing trip abroad, the local food was incredible.",
    # topic B: systems programming
    "Compiling the kernel from source and debugging a memory allocator.",
    "Wrote a lock-free queue in C today, the atomics were tricky.",
]

# Recorded from a previous, separate process (see SIM4_LOG.md (Part I), R-2).
# Mean-pooled embeddings are deterministic, so a fresh process must reproduce
# these. Divergence means the embedding space changed underneath us — the
# B-1 failure mode, which would make run-to-run replication meaningless.
EXPECTED_WITHIN = 0.8009
EXPECTED_ACROSS = 0.7534
TOLERANCE = 2e-3
MIN_MARGIN = 0.02


def _mean_pooled(texts):
    """Embed via mean-pooled last_hidden_state.

    Deliberately NOT process_batch()/pooler_output: TwHIN-BERT's checkpoint
    carries no trained pooler, so those weights are randomly re-initialized on
    every load. See SIM4_LOG.md (Part I) bugs B-1/B-2 and decision D-13.
    """
    import torch
    from oasis.social_platform.recsys import get_recsys_model

    tokenizer, model = get_recsys_model(recsys_type="twhin-bert")
    inputs = tokenizer(texts, return_tensors="pt", padding=True,
                       truncation=True)
    with torch.no_grad():
        out = model(**inputs)
    mask = inputs["attention_mask"].unsqueeze(-1).float()
    return (out.last_hidden_state * mask).sum(1) / mask.sum(1)


@check("embeddings are discriminative across two topics")
def _twhin_discriminative():
    """Check the model can actually tell two different topics apart.

    If it cannot, ranking by similarity is meaningless.
    """
    import torch

    vecs = _mean_pooled(PROBE_TEXTS)
    if torch.isnan(vecs).any():
        raise ValueError("embeddings contain NaN")

    def cos(i, j):
        """Measure how similar two lists of numbers are, from 0 to 1."""
        a, b = vecs[i], vecs[j]
        return float(torch.dot(a, b) / (torch.norm(a) * torch.norm(b)))

    within = (cos(0, 1) + cos(2, 3)) / 2
    across = (cos(0, 2) + cos(0, 3) + cos(1, 2) + cos(1, 3)) / 4
    margin = within - across

    # The recommendation algorithm ranks by exactly this cosine. Too little
    # separation and personalization is noise no matter how cleanly the model
    # loaded -- pooler_output measured +0.0008 in one process.
    if margin < MIN_MARGIN:
        raise ValueError(
            f"insufficient separation: within={within:.4f} "
            f"across={across:.4f} margin={margin:+.4f} < {MIN_MARGIN}")

    return (f"shape={tuple(vecs.shape)} within={within:.4f} "
            f"across={across:.4f} margin={margin:+.4f}")


@check("embedding space is reproducible across processes")
def _twhin_deterministic():
    """Check the model gives the SAME numbers when run twice.

    A model that answers differently every time makes runs unrepeatable.
    """
    import torch

    vecs = _mean_pooled(PROBE_TEXTS)

    def cos(i, j):
        """Measure how similar two lists of numbers are, from 0 to 1."""
        a, b = vecs[i], vecs[j]
        return float(torch.dot(a, b) / (torch.norm(a) * torch.norm(b)))

    within = (cos(0, 1) + cos(2, 3)) / 2
    across = (cos(0, 2) + cos(0, 3) + cos(1, 2) + cos(1, 3)) / 4

    dw = abs(within - EXPECTED_WITHIN)
    da = abs(across - EXPECTED_ACROSS)
    if dw > TOLERANCE or da > TOLERANCE:
        raise ValueError(
            f"embedding space drifted from the recorded baseline: "
            f"within={within:.4f} (expected {EXPECTED_WITHIN}, d={dw:.5f}) "
            f"across={across:.4f} (expected {EXPECTED_ACROSS}, d={da:.5f}). "
            f"Runs would not be replicable.")

    return (f"matches recorded baseline within {TOLERANCE} "
            f"(dw={dw:.5f} da={da:.5f})")


@check("upstream pooler regression guard")
def _pooler_guard():
    """Assert the known-bad upstream path is still known-bad.

    If upstream ever fixes process_batch, this check fails loudly and D-13
    should be revisited rather than silently carried forever.
    """
    import inspect
    from oasis.social_platform import process_recsys_posts

    src = inspect.getsource(process_recsys_posts.process_batch)
    if "pooler_output" not in src:
        raise ValueError(
            "process_batch no longer returns pooler_output -- upstream may "
            "have fixed B-1/B-2. Revisit decision D-13.")
    return ("upstream still returns pooler_output (random, untrained); "
            "our mean-pooling deviation remains necessary")


@check("Ollama reachable with llama3.1:8b")
def _ollama():
    """Check the AI model is running and responding."""
    import urllib.request
    import json

    with urllib.request.urlopen("http://localhost:11434/api/tags",
                                timeout=5) as resp:
        tags = json.loads(resp.read())
    names = [m["name"] for m in tags.get("models", [])]
    if not any(n.startswith("llama3.1:8b") for n in names):
        raise ValueError(f"llama3.1:8b not found; available: {names}")
    return f"models={names}"


@check("Ollama's context window can hold our prompt (B-28)")
def _ctx_window():
    """The window must fit the prompt, or the feed is silently cut.

    B-28: a six-run sweep was made at Ollama's 4,096-token default. The prompt
    is ~2,730 tokens before an agent has said anything and grows every turn, so
    every prompt was truncated -- and the feed sits at the END of the prompt.
    Engagement fell from 6.8 % to 2.5 % at an otherwise identical configuration
    while the WALL CLOCK IMPROVED, which is why nothing caught it for six runs.

    F-65 stated the rule and it was not enough. This is the control.
    """
    import server_state
    st = server_state.probe()
    ok, why = server_state.verify(st)
    if ok:
        return why
    if os.environ.get("OASIS_ALLOW_SMALL_CONTEXT"):
        return why + " -- OVERRIDDEN by OASIS_ALLOW_SMALL_CONTEXT"
    raise ValueError(why)


@check("Ollama batches requests (OLLAMA_NUM_PARALLEL > 1)")
def _ollama_parallel():
    """Detect OLLAMA_NUM_PARALLEL=1, which silently serialises every agent.

    F-53: this was misconfigured for all 24 runs. `--semaphore 4` sent four
    concurrent requests and Ollama processed them one at a time, so the flag
    only ever filled a queue. Setting the server correctly is worth ~1.9x, and
    at Parallel:1 `--semaphore 4` is actually 19% SLOWER than serial, because
    queueing costs contention and buys nothing.

    Measured as a THROUGHPUT ratio, not a latency ratio. Two earlier versions
    of this gate got it wrong in both directions and are worth recording:

      * an 8-token probe finished in 0.2s, where queueing hid inside the
        noise -- false PASS on a server we knew was serial;
      * comparing wall time for 2 concurrent requests against 1 -- false FAIL
        on a correctly configured server, because two streams share one GPU
        and each individually slows down. Per-request latency rises either
        way; only aggregate throughput separates the two cases.

    So: run a fixed batch at concurrency 1, then the same batch at
    concurrency 4, and compare completed-calls-per-second.

    The threshold is 1.0, and deliberately not tighter. Measured on this
    machine: a serialising server returns 0.82-0.85 (concurrency makes it
    *worse*, because queueing costs contention and buys nothing), a batching
    one 1.17-1.19. Putting the line at 1.0 leaves ~0.17 margin on both sides
    and states the honest claim -- "concurrency bought nothing at all" -- 
    rather than fitting a number to one measurement. A threshold of 1.15 was
    tried and rejected: it passed by 0.02, which is inside the run-to-run
    noise of the probe itself.

    Set OASIS_ALLOW_SERIAL_OLLAMA=1 to proceed anyway.
    """
    import concurrent.futures as cf
    import json
    import os
    import time
    import urllib.request

    def ping(_):
        body = json.dumps({"model": "llama3.1:8b",
                           "prompt": "Describe a social media feed in detail.",
                           "stream": False,
                           "options": {"num_predict": 48,
                                       "temperature": 0.7}}).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate", body,
            {"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=120).read()

    def throughput(conc, n=6):
        with cf.ThreadPoolExecutor(max_workers=conc) as ex:
            t0 = time.time()
            list(ex.map(ping, range(n)))
            return n / (time.time() - t0)

    # Warm BOTH the model and each concurrency level. Ollama allocates its
    # KV slots lazily, so the first batch at concurrency 4 pays to build four
    # caches and reads ~15% slower than steady state -- enough to push a
    # correctly configured server under the threshold and fail it.
    ping(0)
    serial = throughput(1)
    throughput(4, n=4)                        # warm the parallel slots
    batched = throughput(4)
    gain = batched / serial if serial else 0
    verdict = (f"{serial:.2f} calls/s at conc 1, {batched:.2f} at conc 4 "
               f"(gain {gain:.2f}x)")

    if gain < 1.0:
        if os.environ.get("OASIS_ALLOW_SERIAL_OLLAMA"):
            return verdict + " -- SERIAL, allowed by override"
        raise ValueError(
            verdict + " -- concurrency buys nothing, so Ollama is serialising "
            "(OLLAMA_NUM_PARALLEL=1). Every agent turn queues and the run "
            "takes roughly twice as long as it needs to. Fix:\n"
            "      OLLAMA_NUM_PARALLEL=4 OLLAMA_KEEP_ALIVE=24h ollama serve\n"
            "    then run with --semaphore 4.\n"
            "    FOUR, not eight: F-77 replicated the sweep and eight gives 5x\n"
            "    the wall-clock variance for no mean gain, holding 17 GB and\n"
            "    leaving the machine 0.5 GB free. F-53's 1.9x and 8-slot advice\n"
            "    were single measurements and are retracted.\n"
            "    To proceed anyway: OASIS_ALLOW_SERIAL_OLLAMA=1")
    return verdict + " -- batching"


print("\n" + "=" * 68)
failed = [r for r in results if not r[1]]
for name, ok, detail, elapsed in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name}  ({elapsed:.1f}s)")
print("=" * 68)

if failed:
    print(f"\n{len(failed)} of {len(results)} checks FAILED. "
          f"Do not proceed to stage 1.")
    sys.exit(1)
print(f"\nAll {len(results)} checks passed. Stage 0 gate is clear.")
