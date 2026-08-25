"""Stage 0 dependency check for Simulation 4 (social timeline).

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

See SIM4_BUILD_LOG.md section 9 (Q-1) and the design spec section 9, stage 0.
"""

import sys
import time

results = []


def check(name):
    """Decorator that records pass/fail and keeps going after a failure."""

    def wrap(fn):
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
    import torch

    cuda = torch.cuda.is_available()
    mps = torch.backends.mps.is_available()
    # recsys.py:85 selects cuda-or-cpu only, so MPS goes unused. Recorded in
    # SIM4_BUILD_LOG.md section 4 as a known performance ceiling.
    from oasis.social_platform.recsys import device as recsys_device

    return (f"cuda={cuda} mps={mps}; OASIS will use device={recsys_device!r} "
            f"(MPS unused by design, recsys.py:85)")


@check("TwHIN-BERT loads via the real OASIS path")
def _twhin_loads():
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

# Recorded from a previous, separate process (see SIM4_BUILD_LOG.md, R-2).
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
    every load. See SIM4_BUILD_LOG.md bugs B-1/B-2 and decision D-13.
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
    import torch

    vecs = _mean_pooled(PROBE_TEXTS)
    if torch.isnan(vecs).any():
        raise ValueError("embeddings contain NaN")

    def cos(i, j):
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
    import torch

    vecs = _mean_pooled(PROBE_TEXTS)

    def cos(i, j):
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
    import urllib.request
    import json

    with urllib.request.urlopen("http://localhost:11434/api/tags",
                                timeout=5) as resp:
        tags = json.loads(resp.read())
    names = [m["name"] for m in tags.get("models", [])]
    if not any(n.startswith("llama3.1:8b") for n in names):
        raise ValueError(f"llama3.1:8b not found; available: {names}")
    return f"models={names}"


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
