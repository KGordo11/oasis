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

**Task received; measurement done; nothing built yet. No simulation has been run and
none is needed for the next step.** Working tree clean at `f97c568`, branch
`social-timeline-sim`.

### The task, as given

1. **Efficiency** — can a run take less time?
2. **Data at scale** — a storage format that still works at, say, 1,000 agents ×
   1,000 rounds, and that can be handed to other software to examine. *"If we did
   1000 users and 1000 rounds then what we have now is useless."*

That last sentence is correct, and §1 and §2 below establish in what way — the two
halves fail for completely different reasons and have completely different fixes.

### What the measurements say

- **The wall is the language model, and only the language model** (F-50). At the
  measured 14.4 s per agent-turn, 1000 × 1000 is **167 days**. Scoring is not the
  problem: a full 1000 × 1,000,000 cosine pass is ~1.1 s of matmul.
- **The concurrency knob is already at its optimum** (F-51). Ollama throughput on
  this machine peaks at semaphore 4 and *falls* at 8. There is no free speedup there.
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

| # | Task | Cost | Status | Why it is in this order |
|---|---|---|---|---|
| 1 | **Phase-level timing instrumentation** — split a round into embed / score / feed-build / DB-write / LLM-wait in `run_simulation.py` (Q-16) | ~1 h, no run | **not started** | F-50 attributes ~99 % of runtime to the LLM by *subtraction and micro-benchmark*, not by measuring a real run. This either confirms it or redirects the whole effort, so it goes first and costs almost nothing |
| 2 | **`export.py` → partitioned Parquet** (D-15) | ~3 h, no run | **not started** | Unblocks the professor's actual ask. Testable against the nine existing runs immediately — no simulation needed to prove it works |
| 3 | **Prompt-size reduction** (Q-17) | ~1 h + 1 smoke test | **not started** | Prefill scales with the 12-post feed text. The cheapest real speedup that leaves the model unchanged — but per F-35 it must still be judged against baseline, not against the previous run |

Everything below is the wider backlog, and stays subordinate to those three.

### The rest of the backlog

| # | Task | Cost | Why |
|---|---|---|---|
| 1 | **Phase-level timing instrumentation** (Q-16) | ~1 h, no run | F-50 attributes the cost by arithmetic, not measurement. Before optimising anything, split a round into LLM / embed / score / DB and *see* it |
| 2 | **`export.py` → partitioned Parquet** (D-15) | ~3 h, no run | Unblocks the professor's actual ask; testable against the nine existing runs today |
| 3 | **Prompt-size reduction** (Q-17) | ~1 h + 1 smoke | Prefill scales with feed text. The cheapest real speedup that does not change the model |
| 4 | **Streaming writes** so a 14 GB SQLite never exists (D-16) | ~2 h | At scale the post-hoc export is itself infeasible |
| 5 | Decide the honest target scale (Q-18) | discussion | 1000 × 1000 is not reachable on this laptop. §3 gives what is |

**Do not** raise `--semaphore` expecting a speedup (F-51). **Do not** swap to
`llama3.2:3b` and call it an optimisation — it is a different experimental condition
and invalidates comparison to all 24 existing runs (D-17, pending).

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
