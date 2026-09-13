"""Tests for server_state.py — the guard that B-28 says should have existed.

B-28: an entire overnight sweep ran at Ollama's default 4,096-token context
because OLLAMA_NUM_PARALLEL was set and OLLAMA_CONTEXT_LENGTH was not. Every
prompt was silently truncated, the feed (which sits at the end of the prompt)
was the part cut, and engagement fell 2.5x while the CLOCK SAID THE RUN GOT
FASTER. Nothing in the manifest recorded the server's actual state, so the
timings were attributed to agent count, persona file and server health in turn
before anyone checked the window.

The rule these tests encode: a run must read the server's real per-slot context
from /api/ps, write it into its own manifest, and refuse to start when that
window cannot hold the prompt it is about to send.
"""
import json
import server_state as S


class FakeResponse:
    def __init__(self, payload): self._p = json.dumps(payload).encode()
    def read(self): return self._p
    def __enter__(self): return self
    def __exit__(self, *a): return False


def fake_opener(payload):
    return lambda *a, **k: FakeResponse(payload)


PS_LOADED = {"models": [{"name": "llama3.1:8b", "context_length": 8192}]}
PS_TRUNCATING = {"models": [{"name": "llama3.1:8b", "context_length": 4096}]}
PS_EMPTY = {"models": []}


def test_reads_context_length_from_ps():
    st = S.probe(opener=fake_opener(PS_LOADED))
    assert st["context_length"] == 8192, st
    assert st["source"] == "api/ps"


def test_reports_unknown_when_no_model_is_loaded():
    """An empty /api/ps is not an error and must not be reported as a number."""
    st = S.probe(opener=fake_opener(PS_EMPTY))
    assert st["context_length"] is None, st


def test_accepts_a_window_that_fits_the_prompt():
    ok, why = S.verify(S.probe(opener=fake_opener(PS_LOADED)), need=8192)
    assert ok, why


def test_REFUSES_the_window_that_caused_B28():
    """The whole point. 4,096 cannot hold a 2,730-token prompt plus transcript."""
    ok, why = S.verify(S.probe(opener=fake_opener(PS_TRUNCATING)), need=8192)
    assert not ok
    assert "4096" in why and "8192" in why, why
    assert "OLLAMA_CONTEXT_LENGTH" in why, "the message must say how to fix it"


def test_refuses_when_the_window_is_unknown():
    """Unknown is not a pass. B-28 happened because nothing checked."""
    ok, why = S.verify(S.probe(opener=fake_opener(PS_EMPTY)), need=8192)
    assert not ok, "an unverifiable server must not be silently accepted"


def test_unreachable_server_reports_rather_than_raises():
    def boom(*a, **k): raise OSError("connection refused")
    st = S.probe(opener=boom)
    assert st["context_length"] is None
    assert "connection refused" in (st.get("error") or "")


def test_strips_the_openai_v1_suffix_before_probing():
    """The driver passes ".../v1"; /api/ps lives at the root. Appending gives 404."""
    seen = {}
    def spy(u, **k):
        seen["url"] = u
        return FakeResponse(PS_LOADED)
    S.probe("http://localhost:11434/v1", opener=spy)
    assert seen["url"] == "http://localhost:11434/api/ps", seen


def test_manifest_block_is_json_serialisable_and_complete():
    """What lands in the manifest is what a future reader has to work from."""
    block = S.manifest_block(S.probe(opener=fake_opener(PS_LOADED)))
    json.dumps(block)
    for k in ("server_context_length", "server_num_parallel_env", "server_probe_source"):
        assert k in block, (k, block)


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn(); print(f"  PASS  {name}")
            except AssertionError as e:
                fails += 1; print(f"  FAIL  {name}: {e}")
    print(f"\n{'all passed' if not fails else str(fails) + ' FAILED'}")
    raise SystemExit(1 if fails else 0)
