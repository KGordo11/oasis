# Simulation 4 — Scaling & Data Pipeline Log

**What this document is.** The working record for the task set in the week of
2026-08-31: make a run take less time, and store what a run produces in a form that
survives being 1,000 agents × 1,000 rounds and can be opened by other software.

**Why it is separate from `SIM4_BUILD_LOG.md`.** That log is the record of a finished
study — how Sim 4 was built and what the nine analysed runs established. This is
engineering work on the machinery underneath it. It does not change any published
result, and nothing here should be read as revising one.

**Related documents**
- Build log: `SIM4_BUILD_LOG.md` — F-1..F-49, B-1..B-21, D-1..D-14, R-1..R-24, Q-1..Q-15
- Design spec: `docs/superpowers/specs/2026-08-24-social-timeline-design.md`
- Project-wide log: `PROJECT_LOG.md`

**Conventions.** Identical to the build log, and the id sequences **continue** rather
than restart, so a search for any id still lands in exactly one place:

| Kind | Build log holds | This log starts at |
|---|---|---|
| Findings `F-n` | F-1 … F-49 | **F-50** |
| Bugs `B-n` | B-1 … B-21 | **B-22** |
| Decisions `D-n` | D-1 … D-14 | **D-15** |
| Runs `R-n` | R-1 … R-24 | **R-25** |
| Open questions `Q-n` | Q-1 … Q-15 | **Q-16** |

---

## 0. STATUS — read this first when resuming

*Last updated 2026-09-03. Update at the end of every working session.*

**All queue items done, plus three scaling defects found and fixed while
double-checking. No full simulation has been run — only 4- and 5-agent smoke tests.**
Branch `social-timeline-sim`, 88 test-gate checks passing.

**The pattern worth noting.** Every one of the three defects (F-57 ranking loop, F-58
index shape, F-55 cache-contaminated benchmark) was invisible at 36 agents and squarely
in the path at 1,000. Measuring *where time goes today* — which is what Q-16's
instrumentation does, correctly — cannot find any of them. They only appear when you
ask how cost scales with size, which is a different question.

**One thing needs your decision before anything else proceeds:** your Ollama server is
still `OLLAMA_NUM_PARALLEL=1`, so `check_deps.py` will now *fail* and block runs until
it is restarted as `OLLAMA_NUM_PARALLEL=8 ollama serve` (or overridden with
`OASIS_ALLOW_SERIAL_OLLAMA=1`). That is deliberate — the misconfiguration cost 24 runs
roughly a third of their speed and nothing caught it — but it is your machine and your
service, so I have not restarted it.

### The task, as given

1. **Efficiency** — can a run take less time?
2. **Data at scale** — a storage format that still works at, say, 1,000 agents ×
   1,000 rounds, and that can be handed to other software to examine. *"If we did
   1000 users and 1000 rounds then what we have now is useless."*

That last sentence is correct, and §1 and §2 below establish in what way — the two
halves fail for completely different reasons and have completely different fixes.

### What was built

| | |
|---|---|
| **Phase timing** | Seven phases per round; anything unaccounted is `llm_wait`. Confirms F-50 by measurement: **99.8 % LLM**, 0.2 % embed, rest sub-millisecond |
| **`export_parquet.py`** | All 19 runs: **115.7 MB → 6.5 MB**, 17.8x smaller. DuckDB cross-run query over all 19 in **14 ms** |
| **`check_deps.py` gate** | Refuses a run when Ollama serialises. Took three probe designs; two produced false results and are documented |
| **Vectorised ranker** | **25-30x** faster, bit-identical including under forced ties. Removes a ~23 min/round wall at target scale |
| **Composite indexes** | **260x** on the informed-action gate; both hot queries now covering-index |
| **Test gates** | 57 → **88 checks** across 6 suites, all passing |

### What the measurements say

- **The wall is the language model** (F-50, now confirmed in-run at 99.8 %). At
  14.4 s per agent-turn, 1000 × 1000 is **167 days**.
- **But there was a second wall underneath it** (F-57). F-50 timed the matmul and
  called scoring free. The Python loop *around* it was **1,231× larger** — ~23 min
  per round at target scale. Now vectorised and gated.
- **And a third, in the index** (F-58). The informed-action gate scanned ~12,000 rows
  per check at scale; the right composite index makes it **260× faster**.
- **There was a free speedup, and F-51 missed it** (F-53, F-56). Ollama had
  `OLLAMA_NUM_PARALLEL:1` — it served one request at a time and the semaphore of 4 only
  filled a queue. Fixing it is worth **~1.3× on realistic prompts**; today's config
  gains nothing at all from concurrency. F-51 is retracted; `check_deps.py` now gates it.
- **Prefill is ~25 % of a turn** (F-55, which retracts F-54). Trimming the prompt is a
  real lever after all — but the feed is the study's independent variable, so cutting it
  changes the experiment rather than optimising it. The free version is the **8 tool
  definitions that never fire** (F-48), and that needs an A/B (Q-21).
- **Two of my own benchmarks were wrong the same way**: they reused one prompt and
  measured Ollama's KV cache. Vary the prompt per call, always.
- **Storage fails separately, and is entirely fixable** (F-52). 43.5 M rows and
  ~14.7 GB of SQLite at target scale; the same data is **0.62 GB** as partitioned
  Parquet — 23× smaller — and readable by pandas, R, DuckDB, Polars and Tableau
  without a converter.
- **The real blocker for analysis is `_analysis.json`**, not the database (F-52).
  Every analysis tool reads that single file. It is 1.6 MB at 36 × 15. It does not
  survive this.

### The build queue — agreed, not started

**Confirmed with the user 2026-09-03. Nothing here has been started, deliberately:
brainstorming is still open and the design may still change. Do not begin building
without checking in.** Update this block — status, findings, and any re-ordering — as
work happens; it is the answer to "where were we".

| # | Task | Cost | Status | Outcome |
|---|---|---|---|---|
| 1 | **Phase-level timing instrumentation** (Q-16) | ~1 h, no run | **DONE** `1c8383f` | Seven phases timed per round; anything unaccounted is `llm_wait`. Smoke-tested: **llm_wait 99.8 %, embed 0.2 %**, everything else sub-millisecond. **F-50 confirmed by measurement rather than inference.** |
| 2 | **`export_parquet.py` → partitioned Parquet** (D-15) | ~3 h, no run | **DONE** `94ea4d1` | All 19 databases exported. **115.7 MB → 6.5 MB, 17.8× smaller, 20.3 bytes/row.** DuckDB answers a cross-run query over all 19 in 14 ms. 22-check fidelity gate (`test_export_parquet.py`) — which caught the exporter silently turning 1,217 NULL scores into 0.0 |
| 3 | **Gate the Ollama misconfiguration** (F-53) | ~15 min | **DONE** `b9ca849` | `check_deps.py` now refuses a run when Ollama serialises. Took three probe designs; the two failures are recorded in its docstring |
| 4 | **Measure a real turn's prefill/decode split** (Q-20) | ~30 min | **DONE** | **Overturned F-54.** Prefill is **~25 % of a turn**, not 4 % — the earlier benchmark reused one prompt and was reading Ollama's KV cache. See F-55, F-56 |

Everything below is the wider backlog, and stays subordinate to those three.

### The rest of the backlog

Not queued — these wait on the three above, or on a decision.

| Task | Cost | Waiting on |
|---|---|---|
| **Streaming writes** so a 14 GB SQLite never exists (D-16) | ~2 h | Item 1's numbers — D-16 is deliberately undecided until instrumentation says what DB writes actually cost |
| **Chunk the score matrix over agents** | ~1 h | Only bites past ~300 agents (4 GB/round at 1000). Not urgent, but it is the one place scoring does break |
| **Decide the honest target scale** (Q-18) | discussion | You and your professor. §3 gives what is reachable; 1000 × 1000 is not |
| **Decide on model size** (D-17) | discussion | Same conversation. `llama3.2:3b` is a *condition*, not an optimisation |

**`--semaphore` alone does nothing** — the server was pinned at `OLLAMA_NUM_PARALLEL:1`
and queued everything (F-53, which retracts F-51). Raise the *server* setting, then the
flag. **Do not** swap to `llama3.2:3b` and call it an optimisation: it is worth 3.35×
and it is a different experimental condition, which makes it D-17's decision, not a
tuning step.

---

## 1. Efficiency — where the time actually goes

### F-50 — The wall is the LLM; scoring and I/O are rounding errors

**Finding.** Measured on `baseline`'s own manifest: **7,279 s of wall clock for 504
agent-turns = 14.4 s per agent-turn.** Round time grows from 309 s to 566 s over the
run as posts accumulate, an ~80 % rise.

Extrapolated to the target, 1,000 agents × 1,000 rounds = **1,000,000 agent-turns**:

| | |
|---|---|
| at 14.4 s/turn | **4,012 hours = 167 days** |

Everything else is negligible by comparison, measured on this machine:

| Phase | Measured | At 1000 × 1000, per round |
|---|---|---|
| Cosine scoring | 935 M pairs/sec | 1000 × 1M posts = 1e9 pairs ≈ **1.1 s** |
| Embedding (TwHIN-BERT, CPU) | 344 texts/sec | ~1000 new profiles ≈ **3 s** |
| LLM turns | ~0.069 turns/sec effective | 1000 turns ≈ **4 hours** |

So the ranking pass that *looks* expensive — an all-pairs embedding comparison — is
about three orders of magnitude cheaper than the thing next to it. **Optimising the
feed builder would be optimising 0.03 % of the runtime.**

**One caveat that matters for the scoring number.** The matmul is fast but the score
matrix is dense: 1000 × 1,000,000 float32 is **4 GB per round**. Time is not the
constraint there, memory is, and it is solved by chunking over agents rather than by
making it faster.

**Evidence.** `data/social_timeline_baseline.json` round timings;
`embedding.embed()` throughput on 512 fresh texts; `torch` matmul on normalised
1000×768 by 20000×768, extrapolated linearly.

### F-51 — Concurrency is already at its optimum; raising it makes things worse

**Finding.** The build log and the mechanics manual both state that the semaphore of
4 "is the main reason a run takes two hours rather than twenty minutes", implying
headroom. **There is none.** Benchmarked directly against Ollama with a
12-post feed prompt:

| `--semaphore` | wall for 2×conc calls | mean latency | throughput |
|---|---|---|---|
| 1 | 8.2 s | 4.1 s | 0.24 calls/s |
| **4** | 4.3 s | 1.7 s | **1.87 calls/s** |
| 8 | 10.5 s | 4.1 s | 1.52 calls/s |

Throughput peaks at 4 and **falls 19 % at 8**. The machine is saturated; adding
concurrency adds contention, not work. `--semaphore 4` was a better choice than the
comment describing it suggested.

**Limitation, stated because it changes what this licenses.** The benchmark generated
60 tokens per call against a synthetic feed prompt. Real turns emit tool calls and
run longer — mean real latency is 14.4 s, not 1.7 s. The *shape* (peak at 4, decline
at 8) is what this establishes; the absolute numbers are not a substitute for
instrumenting a real run, which is Q-16.

---

## 2. Data at scale — why the current format fails

### F-53 — RETRACTS F-51. Ollama was serving one request at a time; the semaphore never did anything

**Finding.** `OLLAMA_NUM_PARALLEL` was never set. The Homebrew-launched server logs
`OLLAMA_NUM_PARALLEL:1` and the runner loads with `Parallel:1`
(`/opt/homebrew/var/log/ollama.log`). **Every agent turn in all 24 runs was served
strictly serially.** The client-side `--semaphore 4` has only ever been filling a
queue inside Ollama.

**F-51 is retracted.** It concluded "throughput peaks at 4 and falls at 8, the machine
is saturated". The measurement was contaminated: the concurrency-1 case had `n=2` and
included the cold model load, which made the serial baseline look artificially slow
and every higher concurrency look like a win. Re-run warm, with equal `n=24` at every
level and a warm-up pass per level, on `llama3.1:8b`:

| `NUM_PARALLEL` | conc 1 | conc 2 | conc 4 | conc 8 |
|---|---|---|---|---|
| **1** (current) | 1.08 turns/s | 0.96 | **0.88** | 0.96 |
| **4** | 1.01 | 1.11 | 1.47 | 1.54 |
| **8** | 1.11 | 1.18 | 1.52 | **1.68** |

Two things fall out, and the second is embarrassing:

1. **Server-side parallelism is worth about 1.6×**, not the 4× the slot count
   suggests. Aggregate throughput rises while *per-stream* decode falls from
   ~41 tok/s to ~9 tok/s — the GPU is shared, not multiplied.
2. **The current configuration is the worst available.** At `Parallel:1`, running
   `--semaphore 4` (0.88 turns/s) is **19 % slower than running `--semaphore 1`**
   (1.08). The queueing buys nothing and costs contention. Whatever else is decided,
   the present combination is strictly dominated.

**Corrected ceiling for the whole knob:**

| Configuration | turns/s | vs today |
|---|---|---|
| 8b, `Parallel:1`, semaphore 4 — **today** | 0.88 | 1.00× |
| 8b, `Parallel:1`, semaphore 1 — one env var | 1.08 | 1.23× |
| 8b, `Parallel:8`, semaphore 8 | 1.68 | **1.91×** |
| 3b, `Parallel:8`, semaphore 8 | 2.95 | **3.35×** |

**Method.** A second Ollama on `:11435` with the alternate settings, benchmarked
against the untouched original on `:11434`, then stopped. 24 calls per level after a
per-level warm-up, 788-token prompt, 80-token cap, timings from Ollama's own
`eval_count`/`eval_duration`.

**Caveat that limits what this licenses.** The synthetic turn takes ~1 s; a real agent
turn takes 14.4 s, because it carries the full OASIS scaffold and 22 tool definitions
and emits tool calls. The **ratios** should carry; the absolute rates will not. This
is precisely why Q-16's in-run instrumentation stays item 1.

### F-54 — Prefill is ~4 % of a turn, so prompt-size reduction is close to worthless

**Finding.** From the same benchmark, per call on a 788-token prompt:

| | time | rate |
|---|---|---|
| Prefill (prompt) | **0.02–0.03 s** | ~26,000 tok/s |
| Decode (generation) | **0.66–0.82 s** | ~40 tok/s |

Prefill is **~4 %** of the call. Generation is ~96 %. Apple Silicon reads the prompt
about 650× faster than it writes tokens.

**Consequence for the queue.** Q-17 / item 3 — trimming the 12-post feed text to cut
prefill — targets 4 % of the wrong end. Even halving the prompt saves ~2 % of a turn.
**Demoted.** The lever that matters is *generated* tokens: how long each agent's reply
is, and how many tool-call round-trips a turn takes. That is worth measuring (Q-20),
and it is a genuinely different question from the one item 3 was going to answer.

### F-60 — The concurrency fix is worth nothing on a full run. F-53's magnitude does not survive

**Finding.** F-53 established that Ollama was serialising, and F-56 measured the fix at
~1.3x on unique prompts. A 12-agent A/B suggested 3.10x. **At full scale it is worth
nothing measurable.**

| Run | Config | Total | s/round |
|---|---|---|---|
| `baseline` (2026-08) | serial, `--semaphore 4` | 7,279 s | 485.3 |
| `full_8b` (2026-09-05) | `NUM_PARALLEL=8`, `--semaphore 8` | 7,326 s | 488.4 |

**+0.6 %.** Identical within any reasonable error.

**And the error is large.** Two runs at the *same* new configuration disagree by 15 %
over their first five rounds — `sweep_8` at 1,770 s against `full_8b` at 2,042 s. Against
baseline's 1,984 s that is **-10.8 %** and **+2.9 %** respectively. The change is
somewhere between "nothing" and "about a tenth", and a single pair of runs cannot
separate those. This is F-35's noise floor showing up in wall clock rather than
behaviour, and it is the reason the earlier estimates were wrong.

**Why the small benchmarks lied.** They had idle gaps for batching to fill. A 36-agent
round does not: the queue is saturated from the first request to the last, so the GPU is
already busy and there is nothing for concurrency to recover. Every measurement in
F-51, F-54 and F-56 was taken at a scale that does not resemble the workload.

**What stands.** The server *was* serialising for all 24 runs, `check_deps.py` now
catches it, and the configuration is no longer strictly dominated. What does not stand
is the claim that fixing it makes runs meaningfully faster. **It does not.**

### F-61 — Past 16 parallel slots the KV cache spills to CPU and throughput collapses

**Finding.** Swept at 36 agents x 5 rounds, one configuration at a time, nothing else
on the GPU:

| `NUM_PARALLEL` | s/round | KV on Metal | KV on CPU | Total |
|---|---|---|---|---|
| **8** | **355.2** | 3.5 GiB | none | 7.0 GiB |
| 16 | 390.4 | 8.0 GiB | none | 16.5 GiB |
| 24 | 1,089.4 | 10.5 GiB | **1.5 GiB** | 22.5 GiB |
| 32 | 1,299.0 | 9.5 GiB | **6.5 GiB** | 28.6 GiB |

The collapse is not contention, it is **placement**. At 24 slots the KV cache no longer
fits in the M2 Max's 21.3 GiB and Ollama silently puts part of it on the CPU; every
attention step then crosses the memory boundary. 24 is **3.1x** slower than 8, and 32 is
**3.7x**.

This answers "can we run all 36 agents at once" with a measurement rather than
arithmetic: **no.** 8 is optimal on this hardware, 16 is already 10 % worse, and past 16
it falls off a cliff. The earlier VRAM estimate put the ceiling near 28 by counting bytes;
the real ceiling is lower because throughput degrades well before allocation fails.

**Generalisable rule:** the useful number is not "how many will load" but "how many keep
the KV cache on the GPU". Ollama logs both placements at load time
(`kv cache device=Metal` / `device=CPU`), so it is checkable before committing to a run.

### F-58 — The informed-action gate's index was the wrong shape; a 260x fix

**Finding.** `_informed()` runs on every like, comment, repost and quote, asking
"has this agent been shown this post?" via
`SELECT 1 FROM rec_history WHERE agent_id=? AND post_id=?`. The only index that
served it was `(agent_id, round)`, which seeks the agent and then **scans every row
that agent has** — about 12,000 of them at 1,000 agents and 12 M exposures.

Benchmarked on a synthetic `rec_history` of 1.2 M rows across 1,000 agents, 300
random lookups:

| Index | Mean lookup |
|---|---|
| `(agent_id, round)` — what existed | **425.7 us** |
| `(agent_id, post_id)` — added | **1.6 us** |

**260x**, and SQLite answers it from the index alone without touching the table
(`USING COVERING INDEX`). The matching `(agent_id, author_id)` index was added for
`_knows_author()`, which gates `follow()` the same way.

Invisible today — `baseline` has 6,048 rows and any index looks fine — and squarely
in the path at the scale being planned for.

### F-59 — Three other suspected walls, measured and cleared

Recorded because "we checked and it is fine" is worth as much as a fix, and stops
the next person re-investigating.

| Suspected | Measured at 1,000 agents x 1 M posts | Verdict |
|---|---|---|
| `fetch_table_from_db("post")` reloads every post every round | 434 ms/round, ~200 MB materialised; **~4 min cumulative** over 1,000 rounds | **not a wall** — trivial beside a 4-hour LLM round. Memory is the real cost, not time |
| `embed_cached` re-hashing every post text each round | 0.5 us per cached lookup -> **~0.5 s/round** | **not a wall** |
| Embeddings stored at double precision | already `float32` | **nothing to win** |

**One genuine limit, deliberately not fixed.** `cosine_matrix` allocates the score
matrix in one block: 1,000 x 1 M float32 is **4.0 GB per round**. Survivable on this
32 GB machine, wasteful, and a hard stop beyond that size. Chunking the score-and-rank
pipeline over agents would cut peak memory ~10x and is straightforward, because
ranking is already per-agent independent.

It is **not being done now**, on purpose. The only scale where 4 GB bites is
1,000 x 1 M, which is 167 days of LLM time (F-50) and therefore unreachable. The
realistic near-term target — a few hundred agents (§3) — needs 0.16 GB. Rewriting the
scoring path a second time to solve a problem that cannot currently be reached is
speculative work on the most safety-critical code in the project. Recorded as **Q-22**,
to be done if and when the scale becomes reachable.

### F-57 — The scoring bottleneck is the Python loop, not the matmul, and it was 1,231x larger

**Finding.** F-50 measured the *matmul* — 1000 agents x 1e6 posts in ~1.1 s — and
concluded that "optimising the feed builder would be optimising 0.03 % of the runtime".
That is true at 36 x 262 and **false at the scale being planned for**, because the
matmul was never the expensive part. The Python loop wrapped around it was.

Measured at ~**1.35 us per (agent, post) pair**, flat across sizes:

| agents x posts | ranking loop |
|---|---|
| 36 x 262 (today) | 0.01 s |
| 100 x 1,000 | 0.14 s |
| 200 x 4,000 | 1.14 s |
| 1,000 x 100,000 | **~2 min per round** |
| 1,000 x 1,000,000 | **~23 min per round** |

Against ~1.1 s for the matmul over the same space: **the loop is ~1,231x the
matrix multiply it wraps.** At 1,000 rounds that is roughly **16 days of pure
ranking**, on top of the LLM time — a second wall nobody had measured, hiding
underneath a phase everyone had agreed was free.

**Fixed.** `_rank_candidates` is now vectorised with numpy: mask self-authored
posts, multiply the similarity row by recency, `argsort` and take the top k.
Measured **25-30x faster** at 200 x 4,000; extrapolated, **28 min -> 0.9 min per
round** at target scale.

**Bit-identical, and gated.** A rewrite of the ranker is a rewrite of what every
agent sees, so `test_ranking.py` holds the new implementation against the old one —
kept verbatim as an oracle — across six shapes including two with **forced exact
ties**, and requires identical output to 1e-9. The tie cases matter: the original
built its list in ascending post-index order and relied on Python's stable sort, so
equal scores kept ascending post index. `np.argsort(kind="stable")` reproduces that
only because it is stable and only because the input order matches. Both are now
things a future change has to break a test to break.

**Why this was missed.** F-50 timed the operation that *looked* expensive. The loop
around it costs nothing at the only scale ever run, so no measurement of an actual
run would have caught it either -- the instrumentation added in Q-16 reports
`score_rank` at 0.0 s, correctly. It only appears when you ask what the cost is as a
function of size, which is a different question from where the time goes today.

### F-55 — RETRACTS F-54. Prefill is ~25 % of a turn, not 4 %; the benchmark was reading its own cache

**Finding.** F-54 reported prefill at 0.02–0.03 s against 0.66–0.82 s of decode, and
concluded prompt-size reduction was worth ~2 % and should be dropped. **That was
measured on the same prompt sent repeatedly**, so every call after the first hit
Ollama's KV cache and paid no prefill at all. A real run sends a *different* prompt to
every agent every round — different persona, different feed — and never reuses a cache
entry.

Re-measured with a unique prompt per call, `num_predict=160`:

| Feed size | Prompt tokens | Prefill | Decode | Wall | Prefill share |
|---|---|---|---|---|---|
| 12 posts (current) | 610 | **1.31 s** | 3.82 s | 5.29 s | **24.8 %** |
| 6 posts | 328 | 0.80 s | 4.20 s | 5.15 s | 15.6 % |
| 3 posts | 187 | 0.52 s | 4.26 s | 4.92 s | 10.5 % |

Prefill is **a quarter of a turn**, and it scales with the prompt as expected. The
identical-prompt benchmark was measuring cache hits and calling it prefill.

**What this restores, and what it does not.** Halving the feed saves ~0.5 s of a 5.3 s
turn — about **10 %**, not the ~2 % F-54 claimed. But feed size is the study's central
independent variable: 12 slots split 5/3/4 is the design (F-25), and every tier
estimate is conditioned on it. **Cutting the feed to go faster would change the
experiment, not optimise it.** Q-17 is reopened as a real lever and immediately
constrained by that.

**The genuinely free version, which needs a test before it can be claimed.** The
prompt also carries ~979 tokens of tool definitions for **22 actions**, and F-48
established that **8 of them never fire in any of the nine analysed runs** — all mutes,
trends and undos. Dropping those eight would cut prompt tokens with, in principle, no
behavioural consequence. In principle is not good enough: an agent that *could* have
muted and now cannot is a different agent, and "never observed in 9 runs" is not
"impossible". This is Q-21, and it needs an A/B against baseline, not an assumption.

**Method note that generalises.** Any LLM benchmark that reuses a prompt measures a
cache. Both F-51 and F-54 were wrong for want of a control the workload actually has —
cold caches in one case, real concurrency in the other. Benchmarks of this system
should vary the prompt per call by default.

### F-56 — The parallelism gain survives the cache correction, at a lower magnitude

**Finding.** F-53's headline was measured with repeated identical prompts, so it needed
re-checking against the same flaw as F-54. Re-run with a unique prompt per call:

| Server | conc 1 | conc 4 | gain |
|---|---|---|---|
| `OLLAMA_NUM_PARALLEL=1` (current) | 0.29 calls/s | 0.30 | **1.01×** — nothing |
| `OLLAMA_NUM_PARALLEL=8` | 0.30 calls/s | 0.39 | **1.30×** |

**F-53's substance stands**: the server was serialising, the semaphore did nothing, and
fixing it is a real gain. The *magnitude* is lower on realistic prompts — about
**1.3× at concurrency 4** rather than the 1.5× the cached benchmark suggested, because
unique prompts spend a quarter of each turn in prefill, which batches less well than
decode. Absolute throughput also falls by ~3× against the cached figures, which is
what a real run actually sees.

### D-17 — Model choice is a scientific decision, not a performance one (still open)

`llama3.2:3b` gives **3.35×** combined with parallelism, against 1.91× for parallelism
alone. It is the single largest lever available on this hardware.

It is also a different experimental condition. Every finding in the build log is
measured on `llama3.1:8b`; F-35's noise floor, F-48's action surface and F-49's
persona effects are all statements about that model. Switching invalidates comparison
with all 24 existing runs unless the change is treated as an experiment in its own
right — which, at ~28 pp of run-to-run noise, needs its own replicates.

**Not deciding this unilaterally.** It belongs in the same conversation as Q-18.

### F-52 — Two separate failures: the database is merely large, the analysis hinge is fatal

**Finding.** Projecting `baseline`'s per-agent-round row rates to 1,000 × 1,000:

| Table | Rows at target |
|---|---|
| `rec_candidates` | 30,000,000 |
| `rec_history` | 11,988,000 |
| `trace` | 1,050,000 |
| `post` | 390,000 |
| `comment` | 100,000 |
| **Total** | **43,528,000** |

At SQLite's measured ~338 bytes/row for this schema, that is **~14.7 GB in one file.**

**That is the lesser problem.** SQLite handles 14 GB. What does not survive is the
pipeline's design: every analysis tool reads `_analysis.json`, a single
fully-materialised JSON document, and `dossier.py` writes a ~28,000-line plain-text
transcript. At 36 × 15 the JSON is 1.6 MB. The same structure at 1000 × 1000 is
multiple GB of JSON that must be parsed into memory before any question can be asked.
**The hinge that makes the current pipeline fast and consistent is exactly what makes
it unusable at scale.**

**The columnar alternative, measured rather than assumed.** Converting `baseline`'s
two large tables to Parquet with zstd compression and right-sized dtypes
(`int16`/`int8` ids and positions, `category` for `source`):

| Table | Rows | Parquet + zstd | bytes/row |
|---|---|---|---|
| `rec_history` | 6,048 | 75.3 KB | 12.4 |
| `rec_candidates` | 15,120 | 236.3 KB | 15.6 |

**14.7 bytes/row against SQLite's 338 — a 23× reduction.** Projected across the 42 M
exposure and candidate rows:

| Format | Size at 1000 × 1000 |
|---|---|
| SQLite | 14.20 GB |
| **Parquet + zstd** | **0.62 GB** |

**Evidence.** `pyarrow` 25.0.1 (installed 2026-09-03 for this measurement),
round-tripped from `data/social_timeline_baseline.db`.

### D-15 — Parquet as the interchange format, partitioned by round

**Decision.** Export to **partitioned Parquet**, not to CSV, HDF5, or a bigger SQLite.

**Rationale, in the order that decided it:**

1. **It opens everywhere the professor might want it**, with no converter: pandas
   (`read_parquet`), R (`arrow::read_parquet`), DuckDB (`SELECT * FROM 'x.parquet'`),
   Polars, Spark, and Tableau/Power BI natively. CSV meets that bar too but costs
   ~20× the space and loses every dtype.
2. **Columnar reads the column, not the row.** `exposure_model.py` needs five
   columns of `rec_history`; Parquet reads five, SQLite reads all of them.
3. **Partitioning by round makes the common query cheap.** Round-windowed analysis
   touches only its partitions, and a run can be examined while it is still running.
4. **It is self-describing.** Schema and dtypes travel with the file, which is
   exactly what the `user_id`-actually-stores-`agent_id` trap (build log §15) costs
   us today.

**Rejected: CSV.** ~20× larger, no types, and the trap above becomes a silent
string/int coercion in whatever reads it.
**Rejected: keeping only SQLite.** Fine as the write-ahead store; wrong as the thing
you hand someone.
**Not yet decided:** whether Parquet *replaces* SQLite during the run or is exported
from it afterwards — see D-16.

### D-16 — Streaming writes (PENDING, not yet decided)

At target scale the post-hoc export path requires the 14.7 GB SQLite to exist first,
and then a full read of it. The alternative is writing Parquet row-groups per round
as the run proceeds and keeping SQLite only for the live world-state the simulation
itself queries. This is the more invasive change and is deliberately **not** being
decided before Q-16's instrumentation says what the DB write cost actually is.

---

## 3. What scale is actually reachable

Stated plainly because the target as given is not achievable on this hardware, and
saying so now is cheaper than discovering it in a month.

At the measured 0.069 agent-turns/sec:

| Budget | Agent-turns | e.g. |
|---|---|---|
| 2 hours | ~500 | 36 × 15 — **the current design point** |
| 8 hours (overnight) | ~2,000 | 100 agents × 20 rounds, or 40 × 50 |
| 1 week continuous | ~42,000 | 200 agents × 210 rounds |
| **1000 × 1000** | **1,000,000** | **167 days** |

To reach 1,000,000 turns in 24 hours needs **11.6 turns/sec — a 168× speedup.** That
is not a tuning target. It is a different serving stack: batched inference on a GPU
(vLLM or similar, where 100+ concurrent sequences is normal), a much smaller model,
or both. Nothing in `examples/experiment/social_timeline/` gets there.

**The useful question is therefore not "how do we hit 1000 × 1000" but "what is the
largest run that answers the professor's question, and what does it cost".** Q-18.

---

## 3b. Bugs

*Continues the build log's sequence at B-22.*

#### B-22 — A run hung for twenty-four hours and nothing noticed

**Where.** Ours, `run_simulation.py` — the model client had no request timeout.

**Symptom.** The `full_3b` run stopped making progress at **18:52:43 on 2026-09-05**
having completed only round 0, and was still sitting there **24 hours later**. The
process was alive at 0.2 % CPU. The Ollama server answered `/api/tags` normally. The
database had not been written since the stall. One LLM request had never returned and
the client was waiting on it with no deadline.

**Why nothing caught it.** Every signal looked healthy. A live process, a responsive
server, and a database that simply is not growing are indistinguishable from a slow
round unless something is comparing progress against elapsed time. This is the same
failure class as B-12 (one small error destroying the feed around it) and B-15 (the
overnight batch silently analysing nothing): **the system's default response to trouble
is to look fine.**

**Cost.** A full day of unattended machine time, and phases 3-5 of the campaign never
started.

**Fix, two layers.**
1. `--request-timeout` (default 300 s), passed into the model config. A request that
   exceeds it raises, which the round loop already handles as a counted agent failure
   and continues past — turning an infinite wait into a visible number.
2. A watchdog in the unattended runner: if the run's database has not been written for
   20 minutes, the run is stalled rather than slow (a worst-case round is ~8 minutes),
   so kill it and move to the next phase rather than lose the night.

**Verified.** Smoke run with `--request-timeout 300`: completes, and the manifest
records the value so any run's timeout is reconstructable after the fact.

---

## 4. Open questions

#### Q-16 — What is the actual per-phase split of a round?

F-50 attributes ~99 % of runtime to the LLM by subtraction and micro-benchmark, not
by measurement inside a real run. Before any optimisation, `run_simulation.py` should
record per-round seconds for: embedding, scoring, feed construction, DB writes, and
LLM wait. Cheap, and it either confirms F-50 or redirects the whole effort.

#### Q-17 — How much of the 14.4 s is prefill, and how much does the feed text cost?

Each turn's prompt carries 12 posts of full content plus the persona. Prefill scales
with that. If prefill dominates, truncating post text in the prompt is a real speedup
that changes no experimental variable except the prompt — which D-2 permits, but
which F-35 says must still be judged against baseline.

#### Q-18 — What is the target scale, given §3?

Needs a decision, not an experiment. The honest options are: stay at ~36 agents and
buy statistical power with more runs; go to a few hundred agents on this machine
overnight; or move to GPU-batched inference and change what is possible. These have
very different costs and very different scientific consequences.

#### Q-19 — Does a bigger world change any published result, or only its precision?

Every finding in the build log is measured at 36 agents. F-35's noise floor is
explicitly a statement about how little a world that size can resolve. Scaling up is
worth doing *because* of that — but it means the results are not automatically
comparable, and the comparison has to be designed rather than assumed.

---

## 5. Run ledger

*Continues at R-25. No runs this phase — none required so far.*

| Run | Config | Outcome |
|---|---|---|
| — | — | no runs yet |
