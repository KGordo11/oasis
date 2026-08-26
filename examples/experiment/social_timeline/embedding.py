"""Mean-pooled TwHIN-BERT embeddings for Simulation 4.

WHY THIS EXISTS
---------------
OASIS embeds text via `process_recsys_posts.process_batch`, which returns
`outputs.pooler_output` (process_recsys_posts.py:33). TwHIN-BERT's published
checkpoint does not contain trained pooler weights, so `from_pretrained`
randomly re-initializes `pooler.dense.{weight,bias}` on every single load.

Two measured consequences (SIM4_BUILD_LOG.md, bugs B-1 and B-2):

  B-1  The embedding space differs on every process launch. Two processes
       produced pooler weight fingerprints of sum=-6.18 and sum=+6.46, and
       different embeddings for identical input. Runs would not be
       replicable, which would make this project's core methodological
       habit -- running an experiment more than once to separate signal
       from noise -- structurally meaningless.

  B-2  A random projection through tanh compresses all cosines into a narrow
       band. Measured within-topic vs across-topic margin: +0.0069 in one
       process and +0.0008 in another. The second is indistinguishable from
       noise, i.e. the "interest-based" recommendation would have been
       ranking at random.

Mean-pooling `last_hidden_state` instead is the standard way to obtain
sentence embeddings from an encoder with no trained pooler. Measured margin
+0.0475, and bit-identical across processes.

This is decision D-13, recorded as an explicit, stated deviation from
upstream TWHIN rather than a silent fix. The TwHIN-BERT weights themselves
are unchanged and still used -- they are genuinely trained on Twitter data
and so are well matched to this domain.
"""

from __future__ import annotations

import torch

# Cached so the ~560MB model loads once per process rather than per call.
_tokenizer = None
_model = None


def get_embedder():
    """Load (once) and return the TwHIN-BERT tokenizer and model.

    Deliberately reuses OASIS's own `get_recsys_model` so we load exactly the
    same weights the upstream algorithm would; only the pooling differs.
    """
    global _tokenizer, _model
    if _model is None:
        from oasis.social_platform.recsys import get_recsys_model
        _tokenizer, _model = get_recsys_model(recsys_type="twhin-bert")
        _model.eval()
    return _tokenizer, _model


_cache: dict[str, torch.Tensor] = {}


def embed_cached(texts: list[str], batch_size: int = 64) -> torch.Tensor:
    """embed(), but only computes vectors for text not seen before.

    A post's content never changes once written, yet the ranking pass
    re-embedded every post in existence on every round. By round 12 of a
    36-agent run that was ~100 unchanged posts re-encoded through a 279M
    parameter model on CPU, every round -- the reason round time climbed from
    299s to 640s over a single run, and the bulk of the machine's load.

    Keyed on exact text, so two agents posting identical content share a
    vector, which is correct: identical text has an identical embedding.
    """
    missing = [t for t in dict.fromkeys(texts) if t not in _cache]
    if missing:
        vecs = embed(missing, batch_size=batch_size)
        for t, v in zip(missing, vecs):
            _cache[t] = v
    return torch.stack([_cache[t] for t in texts]) if texts \
        else torch.empty(0, 768)


def cache_stats() -> dict:
    return {"cached_texts": len(_cache)}


def embed(texts: list[str], batch_size: int = 64) -> torch.Tensor:
    """Embed texts as mean-pooled last_hidden_state.

    Args:
        texts: Strings to embed. Empty/None entries are replaced with a
            placeholder so the batch shape stays aligned with the caller's
            indexing -- silently dropping them would misalign every
            downstream (user, post) score.
        batch_size: Texts per forward pass.

    Returns:
        Tensor of shape (len(texts), 768), on CPU.
    """
    if not texts:
        return torch.empty(0, 768)

    tokenizer, model = get_embedder()
    safe = [t if (t and isinstance(t, str) and t.strip()) else "empty"
            for t in texts]

    chunks = []
    for i in range(0, len(safe), batch_size):
        batch = safe[i:i + batch_size]
        inputs = tokenizer(batch, return_tensors="pt", padding=True,
                           truncation=True, max_length=512)
        with torch.no_grad():
            out = model(**inputs)
        mask = inputs["attention_mask"].unsqueeze(-1).float()
        # Mean over real tokens only; padding must not drag the vector.
        pooled = (out.last_hidden_state * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
        chunks.append(pooled.cpu())

    result = torch.cat(chunks, dim=0)
    if result.shape[0] != len(texts):
        raise RuntimeError(
            f"embedding count {result.shape[0]} != input count {len(texts)}; "
            f"downstream (user, post) score alignment would be silently wrong")
    return result


def cosine_matrix(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    """Row-wise cosine similarity between every row of `a` and every row of `b`.

    Returns a tensor of shape (len(a), len(b)).
    """
    if a.shape[0] == 0 or b.shape[0] == 0:
        return torch.empty(a.shape[0], b.shape[0])
    a_n = a / a.norm(dim=1, keepdim=True).clamp(min=1e-9)
    b_n = b / b.norm(dim=1, keepdim=True).clamp(min=1e-9)
    return a_n @ b_n.T
