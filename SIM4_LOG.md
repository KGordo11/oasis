# Simulation 4 — the complete log

**One file, deliberately.** This was two documents, `SIM4_BUILD_LOG.md` and
`SIM4_SCALING_LOG.md`, until 2026-09-13. They were split because the first
recorded a finished study and the second recorded engineering on the machinery
underneath it, but the id sequences always continued across both, and in
practice every search had to be run twice. Merged on 2026-09-13.

**How to read it.** Section 0 is the resume point and is the only part that
goes stale; everything after it is append-only history. Findings are `F-n`,
bugs `B-n`, decisions `D-n`, runs `R-n`, open questions `Q-n`, and each id
appears in exactly one place. **Retractions are kept, not deleted** — a claim
that was believed and then killed is the most useful entry in a research log,
and this one has a lot of them.

| Part | What it holds | Ids |
|---|---|---|
| **Part I — building it** | how Simulation 4 was designed, what the sources said, what the code does, and the nine analysed runs | F-1..F-49, B-1..B-21, D-1..D-14, R-1..R-24, Q-1..Q-15 |
| **Part II — making it run** | efficiency, cost laws, scaling, the data pipeline, and the errors found while measuring them | F-50 onward, B-22 onward, D-15 onward, Q-16 onward |

---

## 0. STATUS — read this first when resuming

*Last updated 2026-09-12 05:40, overnight session. Update at the end of every session.*

### Read this first: one mistake dominates the night

**B-28. I ran a six-point agent sweep at Ollama's 4,096-token default**, because
I set `OLLAMA_NUM_PARALLEL=4` and not `OLLAMA_CONTEXT_LENGTH`. Every prompt was
truncated, the feed sits at the end of the prompt so the feed was cut, and
engagement fell to 2.50 % against the bank's 5.88-6.83 % at an otherwise
identical configuration -- **while the wall clock improved**, which is why it
read as a scaling result for four hours.

Three findings were written and then withdrawn on the strength of it (F-97,
F-98, and an engagement-cost "law"). **The bank runs were correct all along.**
The re-run at 8,192 reproduces them on cost (769 s at round 4 against 793) and
on engagement (5.16 %). **F-81 and F-86 are vindicated, not overturned.**

### Nothing is running

The corrected sweep finished 07:53. `ctx8192_a12/24/36` (twitter) and
`ctx8192_a36_reddit`, all at **8,192 context verified in each run's own log**.
They settle F-96 below.

### What stands from the night

| | |
|---|---|
| **F-94** | Slot position is worth **OR 1.48-2.15** depending on configuration, replicating in **24 runs across three configurations and two persona files**. Raw gradient 17.0 % at slot 0 to 1.7 % at slot 10. Unaffected by B-28 -- it is a within-run comparison |
| **F-95** | Memory does not create the connection effect, it amplifies it: removing it takes OR 3.07 to 2.05, non-overlapping intervals. Found in three runs that had never been analysed |
| **F-96** | **SETTLED: cost is LINEAR in agents, exponent 0.991 (R² 0.9988), at 22.7 s per agent-turn.** Confirms F-91's 0.99. My earlier 1.081 was a truncation artefact and is withdrawn |
| **F-65a** | Ollama 0.24 does NOT divide context across slots; `CONTEXT_LENGTH` is per-slot and 4,096 is simply the default. Corrects F-65's arithmetic, not its warning |
| **B-27** | `build_package.py` published one run's timings under another's name (a `/tmp` log scrape). Now reads each manifest. Coverage 16 -> 32 runs |
| **B-28** | The truncation above |
| **Guard** | `server_state.py` + 8 tests. Reads `/api/ps`, refuses below 8,192, writes `server_context_length` into every manifest. Wired into `run_simulation.py` and `check_deps.py` (now 8 checks) |

### Artifacts — consolidated 8 to 3

`732d1879` Agent Network Formation (explorer, untouched) · `55d7c5a5` Connection
Over Content (science; now carries F-94, the population limits, the statistics
explainer, the likely-questions list and the glossary) · `869156cd` Sim 4
Scaling Laws (engineering; corrected to v10 after B-28).

**Five retired pages are absorbed but STILL LIVE and need the user to confirm
deletion:** `e49bf8a7`, `d80d6149`, `45b122c4`, `b878972f`, `96788f41`.

### Handoff, 2026-09-13 — read this before the next session

Written to disk deliberately: the session that produced it ends here (effort
raised to `xhigh`, which needs a restart).

#### The goal, restated by Gordon

**Our sims must run more agents and more rounds than the two published OASIS
projects.** Theirs: `MultiAgent4Collusion` 1,000 agents x 100 timesteps;
`MutiAgent4Fraud` 110 main and 1,100 largest, also 100 timesteps. And **agent
counts move in increments of 18.**

#### The arithmetic, and it does not work head-on

At the measured 22.7 s per agent-turn (F-96), every agent acting every round:

    1,100 agents x 100 rounds = 110,000 agent-turns = ~29 DAYS

**But the collusion paper does not activate every agent.** Its agents act with a
Bernoulli probability averaging **0.02**. That is how 1,000 x 100 is affordable
at all, and it sits in their appendix rather than being sold as a method:

    1,100 x 100 at 2 % activation = 2,200 agent-turns = ~14 hours

**One overnight.** Sparse activation is the single parameter separating
"impossible on this laptop" from "routine", and **neither paper treats it as a
scientific variable** -- Collusion uses 0.02, Fraud uses 1.0, and neither asks
whether the conclusion depends on it. That is both our route to their scale and
a question they left open.

**Not implemented here.** Every agent acts every round in this codebase. Adding
an activation probability is a real change to the simulation and should be
brainstormed before it is built.

#### The binding constraint is PERSONAS, not compute

Usable bios per file, counted today:

| file | usable personas |
|---|---|
| `anonymous_topic_200_1h/False_Business_0.csv` | **99** |
| `group_polarization/197_progressive.csv` | 193 |
| `group_polarization/197_baoshou.csv` | 193 |
| `reddit/user_data_36.json` | 36 |

`--agents` silently truncates to the file's length (B-26), so **anything above 99
agents on the business file is a mislabelled run.** Exceeding 1,100 agents needs
~1,100 personas that do not exist. Both surveyed repos generate theirs with an
LLM; Collusion's `agents_init.py` is a parametric cohort generator with
switchable network topology and activation distribution. **Persona generation is
a prerequisite, not a detail.**

The two polarization files are politically sorted. One is a coherent population;
both together give 386 agents with a built-in two-community structure --
interesting, but a different experiment.

#### Tonight's sweep, in increments of 18

All five fit inside the 99-persona business file and continue the twitter series,
so the exponent stays comparable:

| agents | est. wall |
|---|---|
| 18 | ~34 min |
| 36 | ~69 min |
| 54 | ~103 min |
| 72 | ~138 min |
| 90 | ~172 min |

**~8.6 hours total.** 7 rounds each, `--semaphore 4`, seed 42. Start the server
as `OLLAMA_NUM_PARALLEL=4 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=24h
ollama serve` -- the run refuses to start otherwise (B-28).

#### Built and verified, not yet used

`--shuffle-feed`, F-94's experiment. Ranks and selects exactly as normal, then
permutes the order before display: same posts, same tiers, position assigned
rather than observed. Eight unit tests plus an in-run assertion that the feed
CONTENTS are unchanged, which holds on a live run.

**A shuffled run cannot be verified against a control run post-hoc.** Sampling at
temperature 0.7 makes any two runs diverge whatever the feed does, so that
comparison proves nothing. I ran it and it "failed" meaninglessly. The invariant
is checked inside the run instead.

#### Artifacts

Three live. `732d1879` the explorer, now 30 runs with a **Cost & scaling tab**
carrying all three timing charts. `55d7c5a5` science. `869156cd` engineering.

**Five retired pages are absorbed but still live and need Gordon's confirmation
to delete:** `e49bf8a7`, `d80d6149`, `45b122c4`, `b878972f`, `96788f41`.

**Regenerating the explorer:** `make_graph.py` does NOT reproduce the
hand-written comparison panel above the tabs. Read the live artifact and merge
that block back, or republishing deletes it silently. Also remove
`.artifact_baseline` from the data dir first, or its alphabetical filter cuts the
run list to a handful.

### Immediately next

1. Artifact `869156cd` Law 2 still shows the withdrawn 1.081 and needs the
   settled 0.991 at 22.7 s per agent-turn, plus the B-28 row in its
   reproducibility table.
2. `docs/superpowers/specs/2026-09-11-research-agenda.md` -- the flagship
   proposal is a shuffled-feed arm testing whether the ranker contributes
   anything beyond allocating attention. Its costings assume the bank's rate,
   which B-28 confirms is correct.
3. The five artifact deletions.

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
- **Prefill is ~78 % of a turn** (F-66, which supersedes F-55). F-55's 25 % was
  measured on a 610-token prompt; the real prompt is ~2,570 once the 22 tool
  schemas are counted. Trimming the prompt is a
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

### Standing warnings — these do not go stale

*Carried forward from the retired build log's status block when the two logs
were merged. Everything else in that block was dated progress and was dropped.*

**RETRACTED — do not repeat this claim.** F-38, *"TwHIN similarity is
anti-predictive of engagement (OR 0.305 per unit cosine)"*, is wrong and is
retracted by F-42. The variable was `rec_history.score` = `sim * recency`, not
cosine. **Cosine alone is null**: OR 1.544 [0.588, 4.054], p = 0.38. The correct
statement is *similarity has no detectable effect*. The science artifact carries
the retraction in its own section 04.

**Do not run another prompt-intervention experiment at 36 agents.** F-35 shows it
cannot resolve anything: an intervention must move posting share by ~14.3 pp to
be visible, and the four that were tried moved it 3-5 pp. Judge any future change
against **baseline**, never against the previous run, and use `compare.py` so the
correction and the minimum detectable effect are reported automatically.

**Never start the inference server without setting the context length.** B-28:
`OLLAMA_NUM_PARALLEL=4 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=24h ollama
serve`. The 4,096 default truncates the prompt and cuts the feed, and the failure
shows up as a FASTER run with less engagement. `check_deps.py` and
`run_simulation.py` now refuse to proceed without it, but the habit matters more
than the guard.

**No configuration change on a single measurement.** Six performance conclusions
in this project were drawn from one reading and later overturned. A claim about
a mechanism needs a variable shown to move *within* a family where everything
else is fixed, not two or three families that happen to line up.

**After any scripted edit to a document, grep for a string only the new content
contains.** B-30: three separate edits reported success and changed nothing,
because an anchor matched a raw character where the file held an HTML entity.
An edit that reports success is not evidence; the changed bytes are.

---

# Part I — building it

*Originally `SIM4_LOG.md` Part I. Its own STATUS block described a study that was already finished when this merge happened, so it is superseded by section 0 above and has been dropped; nothing else was removed.*

# Simulation 4 — Social Timeline: Build Log

**Purpose of this document.** A complete, running record of everything done to build
Simulation 4: every file created or modified, every source consulted, every decision
and why it was made, every bug found and how, and every run with its configuration and
outcome. It is written so that anyone (including future-me) can reconstruct the entire
build without having to ask a question or guess at a rationale.

**Related documents**
- **Scaling & data-pipeline work: `SIM4_LOG.md` Part II** — the current task
  (make runs faster; store results at 1000x1000 scale). It continues the
  `F-`/`B-`/`D-`/`R-`/`Q-` sequences from this file rather than restarting them, and
  changes no result recorded here.
- Design spec: `docs/superpowers/specs/2026-08-24-social-timeline-design.md`
- Project-wide running log: `PROJECT_LOG.md`
- Prior simulations: `SESSION_REPORT (basic sim1).md`,
  `COUNTERFACTUAL_EXPERIMENT_REPORT(sim 2, groups).md`, `SHIELD_EXPERIMENT_REPORT.md`

**Conventions used here**
- Every claim about OASIS behavior cites `file:line` so it can be re-verified.
- Decisions are numbered `D-n` and referenced elsewhere by that number.
- Bugs are numbered `B-n`, runs `R-n`.
- Reversed decisions are struck through and kept, never deleted — the reasoning
  behind a wrong turn is worth as much as the correction.

---

## Contents

- [0. STATUS — read this first when resuming](#0-status--read-this-first-when-resuming)
- [1. Environment](#1-environment)
- [2. Sources consulted](#2-sources-consulted)
- [3. Decision log](#3-decision-log)
- [4. Findings from source investigation](#4-findings-from-source-investigation)
- [5. File inventory](#5-file-inventory)
- [6. Chronological log](#6-chronological-log)
- [7. Run ledger](#7-run-ledger)
- [8. Bug ledger](#8-bug-ledger)
- [9. Open questions](#9-open-questions)

Findings are `F-n`, bugs `B-n`, decisions `D-n`, runs `R-n`, open questions
`Q-n`; each is its own `####` entry and can be jumped to by searching that id.

---

## 1. Environment

Captured 2026-08-24 by direct inspection, not from memory.

| Component | Value |
|---|---|
| Repo | `/Users/gordon/research/oasis` |
| Branch | `social-timeline-sim` (branched from `main` @ `10b1a5b`) |
| Baseline commit | `2b82487` — design spec |
| Python | 3.11.15 (venv at `oasis-env/`) |
| LLM backend | Ollama, `llama3.1:8b` (4.9 GB, local) |
| Ollama endpoint | `http://localhost:11434/v1` — verified responding |
| `OLLAMA_KEEP_ALIVE` | unset in shell; **must be set to `60m` for runs** (see D-5) |
| camel-ai | 0.2.78 |
| torch | 2.12.0 |
| transformers | 4.57.6 |
| sentence-transformers | 3.0.0 |
| pandas / numpy | 2.2.2 / 2.4.6 |
| CUDA available | **False** |
| MPS available | **True** (but unused — see §4, note on `recsys.py:85`) |

**Model choice — `llama3.1:8b`, confirmed.** Selected over `llama3.2:3b` and base
Llama 3 specifically because it has native tool-calling. OASIS agents act by emitting
tool calls, not free text, so tool-calling support is a hard requirement rather than a
preference. Unchanged from Sims 1-3.

---

## 2. Sources consulted

### 2.1 Primary — the OASIS source tree (read directly, not the docs)

Everything in §4 was established by reading these files. Line numbers are as of commit
`10b1a5b`.

| File | What it established |
|---|---|
| `oasis/social_platform/typing.py` | The full `ActionType` enum (30 members) and `RecsysType` (4 members); the default Twitter/Reddit action subsets |
| `oasis/social_platform/recsys.py` | All four recommendation algorithms, their scoring maths, the uninitialized-model trap, module-global state, the `pdb.set_trace()` landmines, the timestep ceiling |
| `oasis/social_platform/platform.py` | Feed construction in `refresh()`, the recsys dispatch in `update_rec_table()`, `DELETE FROM rec`, all group-chat action implementations |
| `oasis/social_platform/database.py` | Table inventory, `rec` matrix fetch/insert conventions and their two conflicting index bases |
| `oasis/social_platform/schema/*.sql` | Exact schemas for `user`, `post`, `follow`, `like`, `comment`, `trace`, `rec`, `chat_group`, `group_members`, `group_messages` |
| `oasis/social_agent/agent_environment.py` | What an agent actually sees each turn; the follower/following count-only stubs |
| `oasis/social_agent/agents_generator.py` | How agent graphs and initial follow edges are built; that `generate_twitter_agent_graph` discards the network column |
| `oasis/environment/env.py` | Platform construction, default feed-size parameters, that a custom `Platform` instance is accepted |
| `examples/twitter_simulation_openai.py` | The canonical driver-script shape (`env.reset()` / `env.step()` / `env.close()`) |
| `data/reddit/user_data_36.json` | Persona schema and content quality |
| `data/twitter_dataset/.../False_Business_0.csv` | Twitter profile CSV columns, incl. `following_agentid_list` |

### 2.2 External repositories

| Source | URL | What was taken |
|---|---|---|
| OASIS | `github.com/camel-ai/oasis` | The simulator itself. README's "23 actions" and "interest-based and hot-score-based recommendation algorithms" claims were the starting point — both verified against source, and the action count corrected to 30 enum members / 27 usable (§5, D-4) |
| MultiAgent4Collusion | `github.com/renqibing/MultiAgent4Collusion` | Confirmed as an OASIS-derived project (Apache-2.0). Reviewed for reusable approach, **not vendored**: its per-agent behavior-trajectory logging and embedding/cluster visualization validate the analytics direction taken in spec §4.5-4.6. No code copied. |
| MatrAIx-Persona-8B | `github.com/MatrAIx-ai/MatrAIx-Persona-8B` | Persona infrastructure: 1M-persona coreset, 1,290 categorical dimensions, MIT licensed, HF id `MatrAIx2026/MatrAIx_Persona_1M_Public_Release`. **Deferred** — see D-8. |
| TwHIN-BERT | HF `Twitter/twhin-bert-base` | The embedding model behind the chosen recommendation algorithm. ~560 MB, not present in the local HF cache as of 2026-08-24. |

### 2.3 Prior work in this project

Sims 1-3 supplied hard-won constraints that shaped this design; see D-1, D-2, D-5 and
the risk table in spec §8.

---

## 3. Decision log

**D-1 — Zero diff to `oasis/`; extend by subclassing.**
All new behavior lives in `examples/experiment/social_timeline/`. Rationale: Sim 1
Attempt 1 edited shared engine files (`oasis/social_platform/config/user.py`,
`oasis/social_agent/agent.py`) and broke tool-calling completely — 0/36 actions
performed. Sim 3's `ShieldAgent` established subclassing as the working alternative.
`env.py:103` accepts a `Platform` instance directly, so a `Platform` subclass needs no
upstream change.

**D-2 — Never modify the tool-call response schema.**
Prompt content and platform internals may be changed; the action/tool schema may not.
Same Sim 1 Attempt 1 evidence as D-1. This decision is what rules out a custom
`send_dm` action (D-7).

**D-3 — TWHIN (interest-based) is the recommendation algorithm.**
Hot-score (`REDDIT`) assigns every user a byte-identical feed (`recsys.py:257`) and
skips the follow-graph feed source entirely (`platform.py:280`), so it cannot produce
per-user timelines. TWHIN personalizes, evolves user profiles from their own posting
history, and receives follow-graph injection. Hot-score is retained only as an optional
later contrast condition. Full comparison in spec §2.1.

**D-4 — 27 actions enabled; 3 excluded with cause.**
`ActionType` has 30 members. Excluded: `EXIT`, `SIGNUP`, `UPDATE_REC_TABLE` (internal
plumbing, not user behavior), `PURCHASE_PRODUCT` (needs the e-commerce product table —
different experiment), `INTERVIEW` (an externally injected researcher probe; including
it would contaminate the free-behavior requirement). That leaves 22 social + 5 group.

**D-5 — `OLLAMA_KEEP_ALIVE=60m` for all runs.**
Default is 5 minutes. This simulation has multi-minute gaps between LLM bursts, during
which the model unloads and must reload. Sim 3 measured the effect: a run doing ~27
actions in 80 minutes did 30 more in the 12 minutes after restarting `ollama serve`
with a 60m keep-alive, and the next full run finished in ~19 minutes versus 65-90
minutes for every earlier run. Tuning keep-alive is preferred over touching experiment
or model logic whenever the complaint is *speed* rather than correctness.

**D-6 — No manual actions.**
Every agent acts only via `LLMAction()`, every round, driven by its own persona. No
scripted posts, no puppeted behavior. Directly per user instruction.

**D-7 — Direct messages are not faked.**
OASIS cannot express a targeted DM: `create_group` takes only a name and adds only its
creator (`platform.py:1497-1527`); wasnthe there is no recipient field anywhere in the schema.
Two workarounds were considered and both rejected — pre-seeding 2-person groups
(violates D-6) and adding a custom `send_dm` action (violates D-2). Resolution: the
five group actions are available, agents may form groups freely, and analytics
classifies a 2-member group as a de-facto DM. Whether 1:1 conversation emerges becomes
an empirical result. If it turns out rare or absent, that is reported, not hidden.

**D-8 — MatrAIx personas deferred to a fast-follow.**
The interest-based algorithm embeds **bio text**. The existing 36 personas already
carry rich topical bios plus `interested_topics`, i.e. they are already in the exact
form the algorithm consumes. MatrAIx's 1,290 categorical dimensions would have to be
collapsed back into a bio sentence to be usable at all. Its real value is scale and
demographic diversity beyond 36 agents, which is not on this build's critical path.

**D-9 — ~~Seed a homophily-weighted initial follow network.~~ REVERSED.**
~~Reasoning: the motivating scenario presumes existing friendships, and the
follow-injection feed path only matters once follows exist.~~
**Reversed 2026-08-24 by user correction.** The scenario was an *illustration* of
emergent multi-hop propagation, not a fixture to reproduce; it was read too literally.
Seeding would also be precisely the world-staging D-6 forbids. See D-10.

**D-10 — The follow graph starts empty; the network self-assembles.**
Zero initial edges. The "before" graph is empty, and the before/after comparison
becomes *network formation* rather than *network rewiring* — a legitimate and arguably
more interesting baseline. Accepted consequence: the follow-injection feed source
contributes nothing early and grows as agents choose to follow each other, so the
balance between algorithmic and social discovery **shifts across the run**. That shift
is a measurable finding, recorded round-by-round via `rec_history.source`.

**D-11 — Staged rollout; no full runs until small ones are clean.**
Per user instruction and Sim 3 precedent, where roughly four full runs (~4 hours) were
spent on three bugs a 20-minute smoke test would have caught. Gates are in spec §9.
"Smallest" means smallest-that-still-exposes-the-bug: Sim 3's `"rank": null` crash
needed enough LLM calls for a rare model output to surface at all.

**D-13 — Implement the ranking in our subclass, with two stated deviations from
upstream TWHIN.**

Forced by B-1/B-2. The original plan was to delegate to upstream
`rec_sys_personalized_twh` unchanged, for fidelity. That is no longer tenable: the
upstream embedding path is non-deterministic across processes and, in one observed
process, non-discriminative.

A second, independent reason points the same way: `rec_sys_personalized_twh` returns
only a recommendation matrix, **not** per-pair scores — yet `rec_history.score`
(spec §4.2) requires exactly those scores to answer *why did this post reach this
user*. We were always going to have to compute them ourselves.

The ranking therefore lives in `TimelinePlatform`, faithfully following TWHIN's
documented formula — cosine similarity between an evolving user profile and post
content, multiplied by a log recency decay — with two deviations, both stated:

1. **Mean-pooled `last_hidden_state` replaces `pooler_output`.** This is the standard
   way to obtain sentence embeddings from a BERT encoder whose checkpoint carries no
   trained pooler. Deterministic, and ~7x more discriminative (§8).
2. **Per-(user, post) scores are captured** for logging. Diagnostic only; does not
   affect ranking.

Everything else — the TwHIN-BERT weights themselves (genuinely trained on Twitter
data, so well matched to this domain), the evolving-profile mechanism, the recency
decay, the candidate filtering — follows upstream.

Rejected alternatives: seeding the RNG before load (makes the randomness reproducible
but leaves an untrained projection with near-zero discrimination); monkeypatching
`process_batch` (opaque runtime patching, and still yields no scores); switching to
`paraphrase-MiniLM-L6-v2` (a properly trained sentence-similarity model, but trained
on generic text rather than social media, and it would abandon TwHIN's domain fit).

The upstream-exact path remains available behind a flag for comparison, so the cost
of this deviation can itself be measured rather than assumed.

**D-14 — Run the simulation with 22 actions; group chat off by default.**
Forced by the R-5 vs R-6 A/B, which was identical in every respect except the
action set:

| | 27 actions (R-5) | 22 actions (R-6) |
|---|---|---|
| action_rate | 0.469 | **0.812** |
| posts | 6 | 14 |
| comments | **0** | **9** |
| quote_post | 0 | 3 |
| follow | 0 | 1 |
| exposure events | 77 | 148 |

Group chat was not merely adding five more tools to choose between — it was
**hijacking the prompt** (F-14). Because `to_text_prompt()` renders `$groups_env`
ahead of `$posts_env` on every turn *regardless of `available_actions`*, a single
agent creating a group put a wall of group instructions above the feed in every
other agent's prompt, and each new group message compounded it. `send_to_group`
became the single most common action while content engagement stayed at zero.

Consequence for D-4 and D-7: the headline "27 actions" is available and verified
working (`test_actions.py`), but running with it produces a *worse* social
simulation on an 8B model. The 5 group actions remain implemented and switchable
via `--no-groups`; they are simply off for the primary configuration. This also
settles D-7 empirically — emergent DMs cannot be studied without re-introducing
the very actions that suppress feed behaviour, so that remains an honest,
reported limitation rather than something engineered around.

**D-12 — Work on a branch.**
`social-timeline-sim`, branched from `main`. Prior sims committed directly to `main`;
this build is large enough to warrant isolation, and `main` stays clean.

---

## 4. Findings from source investigation

Full detail with rationale lives in spec §2. Condensed index:

#### F-1

**Finding.** Hot-score gives every user an identical feed

**Evidence.** `recsys.py:257` — `[top_post_ids] * len(rec_matrix)`

#### F-2

**Finding.** The follow graph reaches the feed, but only for non-REDDIT recsys

**Evidence.** `platform.py:280-303` — `JOIN follow ON post.user_id = follow.followee_id`

#### F-3 — `RecsysType.TWITTER` silently returns random recommendations


**Evidence.** `recsys.py:39` (`model = None`), assigned only at `:282` in a different
function; `:749` falls through to `random.random()` with no error

#### F-4

**Finding.** Exposure history is destroyed every round

**Evidence.** `platform.py:383` — `DELETE FROM rec`

#### F-5

**Finding.** Default feed is ~5 posts, recsys ranks only a top-2 pool

**Evidence.** `env.py:82-84`

#### F-6

**Finding.** Group chat is open-join public rooms, not DMs

**Evidence.** `platform.py:1497-1527`; no recipient field in `group_message.sql`

#### F-7

**Finding.** TWHIN keeps state in module globals across calls

**Evidence.** `recsys.py:436-437`, cleared only by `reset_globals()` at `:124`

#### F-8

**Finding.** `enable_like_score=True` hits `pdb.set_trace()` in exception handlers

**Evidence.** `recsys.py:564, 579` — would hang a headless run indefinitely

#### F-9

**Finding.** TWHIN recency score goes non-finite past ~171 timesteps

**Evidence.** `recsys.py:469-472` — `log((271.8 - age)/100)`; source comments a ~90
ceiling

#### F-10

**Finding.** `generate_twitter_agent_graph` discards `following_agentid_list`

**Evidence.** `agents_generator.py:614-649`

#### F-11

**Finding.** Agents see only follower/following **counts**, never identities

**Evidence.** `agent_environment.py:68-101`, both marked `# TODO` upstream

#### F-12

**Finding.** Two conflicting index bases for the `rec` matrix

**Evidence.** `database.py:281` inserts 1-based; `platform.py:390` inserts 0-based

#### F-13

**Finding.** Every table's `user_id` column actually stores **agent_id**; only the
`user` table has both

**Evidence.** `platform.py:407` — `user_id = agent_id`, repeated in every action

#### F-30 — F-28's reword did not work, and four interventions have now failed

**Finding.** Measured on v10 vs v9 over the same rounds (0-8): round-0 intro share
77%->60% (p=0.135, CI [-5.2, +39.5] pp) and corpus similarity 0.8285->0.8175 (CI
[-0.015, +0.038]). **Neither reaches significance.** Together with F-21b
(notifications), F-27 (reception block) and F-29 (echo chamber), four separate
interventions have failed to move content quality. The convergent conclusion is that the
vagueness is a capacity limit of `llama3.1:8b`, not a fixable property of the prompt or
the feed. **Methodological caveat, stated because it nearly produced a false finding:**
the first bootstrap resampled *pairs* and returned CI [+0.0089, +0.0132], "real".
Pairwise cosines are not independent -- each post appears in ~150 pairs -- so resampling
pairs understates uncertainty. Resampling *posts*, the correct unit, widened the CI to
span zero. **Second caveat:** v10 changed the wording *and* temperature (0.7->0.9)
together, so even a real effect could not have been attributed. Both errors are mine and
both are the same error the log records at F-22


**Evidence.** Recorded as a negative result. Stop tuning the prompt for content quality;
a larger model is the only remaining lever

#### F-40 — F-37's evidence base was overstated, its network result is robust, and its fof result is not

**Finding.** Two corrections. (a) **Reporting error, mine:** the pooled header claimed
"57,682 exposures, 13 runs". Eight of those runs predate the three-tier feed and label
sources `following`/`recsys`/`both`, so they contributed **zero** to every tier contrast
while still being counted in the denominator. The estimates were always computed on the
right rows; only the headline was wrong. Correct base: **5 runs, 30,240 exposures, 2,520
feeds, 2,174 engagements (7.2%)**. (b) **Per-run heterogeneity:** `network` vs
`discovery` is positive and individually significant in **5/5 runs** (baseline 5.77, v8
1.85, v9 8.67, v10 3.73, v10_replicate 3.04) -- direction fully consistent, magnitude
spanning 4.7x. But `fof` vs `discovery` is individually significant in **only 1/4 runs**
and its pooled significance is an artefact of pooling. **The fof contrast -- the one
carrying the causal interpretation -- must be reported as suggestive, not established**


**Evidence.** Header corrected in `exposure_model.py`; legacy runs now explicitly
excluded and named. Per-run breakdown added as section 6

#### F-41 — Independent replication under a different feed implementation

**Finding.** The eight excluded runs are not useless: `following` (came from someone you
follow) vs `recsys` (ranked in by similarity) is the same contrast built by an earlier,
structurally different feed builder, at earlier prompt versions. Same stratified
estimator, on strata sharing nothing with the main analysis: **full_twhin OR 4.79 [3.14,
7.32], full_twhin_v2 OR 5.14 [3.65, 7.22], pooled OR 5.00 [3.83, 6.52], p=1.8e-32, 222
strata.** A different feed builder reproduces the effect at comparable magnitude


**Evidence.** The strongest evidence that F-37 is not an artefact of one feed
implementation. Added as section 7

#### F-42 — F-38 is wrong, and the error is a mislabelled variable, not a confound

**Finding.** The regressor F-38 reported as "similarity ... per unit cosine" is
`rec_history.score`, which is `sim * recency` (`timeline_platform.py:380` writes the
product; `:699-701` copies it into the exposure row; `exposure_model.py:80` reads it and
§5 of its output labels it "similarity"). The tell was visible in F-38's own decile
table, whose bottom bin reads "sim 0.000-0.387" — raw cosine never falls below **0.198**
in any run, but `recency` clamps to `RECENCY_FLOOR = 1e-6` past the age cliff
(`timeline_platform.py:299-301`), driving the *product* to ~0 for stale posts however
similar they are. Recovering `sim` and `recency` separately from `rec_candidates` and
re-fitting F-38's exact specification (cluster-robust logit, clustered by agent, feed
slot included; the control reproduces OR 0.305 [0.164, 0.568] to three decimals):
**cosine alone OR 1.544 [0.588, 4.054], p=0.38 — null, and positive if anything.** The
negative coefficient belonged entirely to the recency half: **recency alone OR 0.176
[0.103, 0.300], p=1.7e-10.** Cosine is also null inside every one of the 8 fittable
recency levels (one nominal p=0.024 across 8 tests). **Retract "TwHIN similarity is
anti-predictive." The supported claim is that similarity has no detectable effect on
engagement**


**Evidence.** Q-10 closed. The "connection beats content" headline is unaffected and if
anything cleaner: content similarity does nothing, rather than doing something
backwards. `recency_check.py`, `data/social_timeline_recency_check.txt`

#### F-43 — What the recency coefficient actually is: repeat exposure

**Finding.** Taken at face value the recency term says older posts draw *more*
engagement, which is backwards for a social feed and needed checking. It is not a round
effect — raw engagement *falls* over rounds (5.65% in round 1 to 1.86% in round 14), so
pooling would bias the estimate the other way, and stratifying on the feed (one agent,
one round, one run — the F-37 identification) leaves **stale vs fresh OR 1.751 [1.384,
2.215], p=3.0e-06, 1956 feeds.** The mechanism is that age and prior sightings are
nearly the same variable here: a fresh post is a first sighting **by construction**
(100% of fresh exposures), while stale posts average **1.69** prior sightings and are
first sightings only 19.4% of the time. Engagement rises monotonically with prior
sightings — **2.20% → 4.52% → 5.94% → 6.80% → 7.33%** (0,1,2,3,4 priors) — and
within-feed **seen-before vs first-sighting OR 2.321 [1.826, 2.951], p=6.1e-12.**
Decisive test: inside first sightings only, where the repeat channel is closed by
construction, the stale advantage **reverses** to **OR 0.551 [0.314, 0.969]**.
Replicated independently in the **network** tier, where the similarity score plays no
part in feed construction: **OR 1.801 [1.348, 2.406], p=6.9e-05.** **Caveat:** prior
sightings are not randomly assigned — a post is re-shown because the ranker kept
choosing it — so this is an observational reading supported by dose-response and
replication, not an experiment. **Robustness (added same day, per the F-40 lesson):
significant in 4/5 runs individually** (baseline 2.76, v10_register 2.32, v10_replicate
2.60, v8_full 2.46) but **v9_feedback returns 0.89 [0.38, 2.11], null** — the same run
that is the outlier on the tier effect at 8.67. **By tier: network 1.801 and discovery
2.321 hold, fof 1.290 [0.805, 2.068] does not**, so this is a network-and-discovery
effect, not a whole-feed one. Adding feed slot to the stratification leaves 2.130
[1.700, 2.669], and re-shown posts sit LOWER in the feed (mean slot 7.60 vs 6.40)
because age drives their score down — position biases against this result, not for it.
Absolute scale 2.20% -> 5.27%, a 3.07 pp gap; the OR is the larger-sounding number
because the base rate is low. The apparent turnover past 4 sightings is NOT claimed:
only 81 distinct posts are ever shown a sixth time


**Evidence.** A third result alongside F-37 and F-35: **repetition drives engagement
more than either content or freshness**. Also the mechanism F-38 was missing. Testable
properly with a designed re-exposure run

#### F-44 — Four more replicates take repeat exposure to 8 of 9 runs

**Finding.** Four additional runs at one identical configuration (prompt v10,
temperature 0.9 — `v10_rep3` through `v10_rep6`, R-21..R-24) were added, giving
**9 three-tier runs, 54,444 exposures, 4,536 feeds, 324 agents, 3,692
engagements**. Repeat exposure now reproduces in **8 of 9 runs individually**
(2.11, 2.32, 2.46, 2.60, 2.76, 3.30, 3.91, 4.55), with `v9_feedback` still the
sole null at 0.89 [0.38, 2.11]. Pooled within-feed **OR 2.624 [2.184, 3.153],
p=7.4e-25**, up from 2.321 on five runs and with a substantially tighter
interval. Survives adding feed slot (**2.454 [2.065, 2.916]**) and holds by
agent (**1.768 [1.534, 2.038]**). The dose-response is cleaner than before and
now monotone through five levels: **2.05% → 4.17% → 5.75% → 6.95% → 8.19%**.
Absolute scale 2.05% → 4.94%, a 2.89 pp gap.

**Tier picture unchanged in shape:** network **1.643 [1.331, 2.028]** holds,
`fof` **1.222 [0.851, 1.755]** still does not. This remains a
network-and-discovery effect.

**Evidence.** `recency_check.py` §8 over 9 runs;
`data/social_timeline_recency_check.txt`. The four new runs are a genuine
out-of-sample test: they were run after F-43 was written, at a configuration
fixed in advance, with no analysis choices changed.

#### F-45 — One of F-43's supporting arguments weakened and must be restated

**Finding.** F-43 leaned on a "decisive test": restricted to first sightings
only, where the repeat channel is closed by construction, stale posts did
*worse* — OR 0.551 [0.314, 0.969], p=0.039 on five runs. **On nine runs that
result is no longer significant: OR 0.703 [0.463, 1.066], p=0.097.** The point
estimate still sits below 1 and the direction is unchanged, but the interval now
crosses it.

This does not overturn F-43 — the main contrast strengthened, and the
network-tier replication (a tier whose feed never touches the ranking score)
still holds at 1.643. But the specific claim that age *reverses* inside first
sightings is no longer supported at the 5% level and must be reported as
directional only. **Do not repeat "the advantage reverses" as though it were
established.**

**Evidence.** `recency_check.py` §7, "stale vs fresh | first sightings only",
5-run vs 9-run output. An honest cost of adding data: more evidence made the
headline stronger and one supporting argument weaker at the same time.

#### F-49 — F-24's bio-echo figure belongs to a different persona file and does not describe the nine analysed runs

**Finding.** F-24 reported *"21 of 66 posts (32%) closely reproduce the author's own
profile text — one at similarity 1.00, i.e. verbatim"*, with a gap of **+0.14** to
own bio vs others (0.785 / 0.641). That figure is quoted as a general known weakness
in §0, in the field guide and in the mechanics manual. **It does not hold on the nine
analysed runs.**

F-24 was measured on **`v7_full`** — the only run with exactly 66 posts — which uses
`data/twitter_dataset/.../False_Business_0.csv`, mean pairwise persona similarity
**0.637**. The nine analysed runs use `data/reddit/user_data_36.json` at **0.829**.

Re-measured on all **2,019** posts of the nine analysed runs, using F-24's own metric
(cosine between a post and its author's bio, mean-pooled TwHIN-BERT):

| threshold | share of posts |
|---|---|
| >= 0.80 | 56.0% |
| >= 0.85 | 17.5% |
| >= 0.90 | 1.1% |
| >= 0.95 | **0** |
| verbatim | **0** — max observed is 0.942 |

A bare percentage is meaningless here: it is entirely a function of the threshold, and
nothing is verbatim. **The baseline is the honest number.** Against a random *other*
agent's bio:

- cosine to own author's bio: **0.795**
- cosine to another agent's bio: **0.782**
- **gap +0.013, 95% CI [+0.010, +0.016]**, n=2,019

Significant, and about **eleven times smaller** than F-24's +0.14. The mechanism is
the persona file: when mean pairwise similarity is 0.829, everything resembles
everything, so resembling *your own* bio adds almost nothing. On the more separable
Twitter personas there was room for the effect to show.

**This is the fourth instance of the same error class** — a per-run figure promoted to
an all-run claim — after F-40, the inflated denominator, and F-48. All four survived
because nobody re-ran the query after the run set changed.

**Evidence.** `embedding.embed_cached` over 2,019 posts and their authors' bios across
the nine analysed databases; persona files and separability read from each run manifest.

#### F-48 — The action surface IS exercised: 14 of 22 fire, and the 8 that do not are all undos

**Finding.** The long-standing claim that *"14 of the 21 actions never fire — no
dislike, unfollow, mute, report, search or trend in any run"* is **wrong and is
retracted.** It appeared in Q-11, in §0 STATUS, and in the field guide.

Measured across the nine analysed runs (`SELECT action, COUNT(*) FROM trace`):

| | count | runs |
|---|---|---|
| `refresh` | 4,537 | 9 |
| `create_post` | 1,988 | 9 |
| `create_comment` | 519 | 9 |
| `follow` | 424 | 9 |
| `like_post` | 360 | 9 |
| `sign_up` | 324 | 9 |
| `like_comment` | 110 | 9 |
| `quote_post` | 33 | 9 |
| `repost` | 17 | 8 |
| `search_user` | 7 | 4 |
| `dislike_post` | 5 | 3 |
| `report_post` | 4 | 3 |
| `search_posts` | 3 | 2 |
| `do_nothing` | 1 | 1 |
| `unfollow` | 1 | 1 |

The offered set is **22** (`build_action_set(include_groups=False)`, verified by
import — `sign_up` is *not* among them; it is internal plumbing). Of those 22,
**14 fire at least once and 8 never do.**

**The eight that never fire:** `mute`, `unmute`, `trend`, `dislike_comment`,
`unlike_post`, `unlike_comment`, `undo_dislike_post`, `undo_dislike_comment`.

**Why this is a better finding than the one it replaces.** Every single one of the
eight is a mute, a trend lookup, or an **undo**. The agents never reverse an action
they have already taken. That is a specific, explainable behavioural regularity;
"two thirds of the buttons are unused" was neither.

**How the error happened, and why it matters.** The claim was read off `baseline`'s
action table, which has exactly nine rows, and generalised to "not once in 20 runs".
It is the **third** instance of the same mistake already on this project's record —
alongside F-40 (a pooled estimate that was really one run) and the inflated
denominator ("57,682 exposures across 13 runs" when 8 contributed zero). A per-run
figure was promoted to an all-run claim without re-running the query.

**Evidence.** `SELECT DISTINCT action FROM trace` over all nine analysed databases;
action set confirmed by importing `run_simulation.build_action_set`.

#### F-46 — Every run manifest already records which feed built it; the explorer never reads it

**Finding.** `run_simulation.py:215-236` writes a self-describing `algorithm`
block per run. The nine three-tier runs carry `feed_model: "three-tier: network >
friend-of-friend > discovery; social ties are not interest-filtered"` plus
`network_slots: 5`, `fof_slots: 3`, `discovery_slots: 4`, `feed_size: 12`,
`explore_slots: 2`. The four pre-three-tier runs (`v4_full`..`v7_full`) carry none
of those — only `explore_slots` and `recency_span_rounds`. Verified across
`v4_full`, `v7_full`, `v8_full`, `baseline`, `v10_rep6`.

`make_graph.py` reads none of them. Its Algorithm box and Method tab read
`config.refresh_rec_post_count` (8), `config.following_post_count` (4) and
`config.max_rec_post_len` (30) instead — upstream knobs the three-tier `refresh()`
never consults (`timeline_platform.py:574-631` uses the slot fields exclusively).

**Why this matters.** B-18 and B-19 are therefore pure presentation defects: no
re-run, no re-analysis, no new data. The correct values sit in manifests the
explorer already loads, and the presence of `feed_model` is a ready-made
discriminator — one field decides which vocabulary and which description a run gets.

#### F-47 — Tier attribution is correct today, but rests on three invariants nothing checks

**Finding.** Not a bug; no incorrect row has been produced. Recorded because B-14
was already a tier-attribution bug, so this is the part of the code with a
demonstrated capacity to be silently wrong.

1. **`fof` travels by side channel.** `refresh()` passes network and discovery into
   `_log_exposure()` as arguments but hands it `fof` via `self._last_fof`, an
   attribute on the shared platform object (`timeline_platform.py:667-669`).
   Correct today for two independent reasons: `_log_exposure` is synchronous with
   no `await` (verified: zero `await` tokens in `:703-737`), and the platform is a
   single-consumer loop (`oasis/social_platform/platform.py:128-130`), so refreshes
   are serialised by the channel. Both are real; neither is stated at the call
   site. The asymmetry is the smell — two tiers as parameters, one as instance state.
2. **Disjointness is asserted by construction and verified by nothing.**
   `_log_exposure` labels by first match, `network` -> `fof` -> `discovery` ->
   `unknown` (`:724-728`). B-14 was precisely an overlap — a followee's sixth post
   falling into the fof tier, 37 exposures mislabelled in R-16. Priority ordering
   *masks* a recurrence of that class rather than surfacing it.
3. **`"unknown"` is reachable and unmonitored.** `:728` can emit it; no integrity
   counter tracks it. It has never fired — `SELECT source, COUNT(*) FROM
   rec_history GROUP BY source` returns only `discovery`/`fof`/`network` on
   three-tier runs and only `recsys`/`following`/`both` on pre-three-tier runs.
   See B-20 for what the explorer would do with one.

**Fix for all three:** pass `fof` as a parameter; assert the three sets pairwise
disjoint before labelling; count `unknown` in `self.stats` so it surfaces in the
integrity table the Method tab already renders.

#### F-37 — Connection predicts engagement; content similarity does not. This is the project's actual result

**Finding.** Pooled over 13 analysed runs: **57,682 exposures, 5,345 feeds, 412
agent-runs, 6,834 engagements.** Crude rates network 18.6% / fof 11.5% / discovery 3.1%,
but that is confounded by agent, round, run and feed position. **Identified estimate,
Mantel-Haenszel stratified by (agent, feed slot) over slots 0-4 -- holding both the
agent and the position in the feed fixed: network vs discovery OR 3.54 [2.92, 4.29]
p=4e-38; fof vs discovery OR 1.97 [1.25, 3.11] p=.003; network vs fof OR 2.12 [1.42,
3.16].** Stratifying by feed only (position free) gives 11.07 and 4.11, so **roughly
half the crude gap is the feed builder placing network posts at the top, and half is the
tier itself.** **The `fof` contrast is the causal one**: friend-of-friend authors were
selected by *other* agents' follows and never by the focal agent, so it carries no
selection-on-affinity, whereas the network contrast is an upper bound that does. Unlike
every cross-run comparison in this project, this sits far above any noise floor because
it is a within-agent, within-slot contrast


**Evidence.** Reach flows through the social graph, and it is not merely an artefact
of network posts being shown first.

> **Superseded — read the numbers below, not the ones above.** As first written,
> this finding claimed "13 analysed runs, 57,682 exposures". Eight of those runs
> predate the three-tier feed and contributed **zero** to every estimate while
> still being counted in the denominator; the estimates were always computed on
> the right rows, only the headline was wrong. Corrected first to 5 runs / 30,240
> exposures, and now standing at **9 runs / 54,444 exposures / 4,536 feeds /
> 3,692 engagements**, with `network` vs `discovery` **OR 3.51 [3.06, 4.04]**
> significant in **9/9 runs** and `fof` vs `discovery` **OR 2.34 [1.64, 3.35]**
> significant in **3/7**. The original text is kept unedited above, because the
> wrong turn is worth as much as the correction.
>
> ("The shield works" was a stray sentence here from the start — a leftover from
> Simulation 3's vocabulary. Simulation 4 has no shield; see the note below.)

#### F-38 — The TwHIN similarity score is mildly ANTI-predictive of engagement

**Finding.** Tested inside the discovery tier only -- the score is present for 100% of
discovery exposures but 28% of network and 43% of fof, so it is missing not at random
and cannot sit in a model beside tier. On 20,822 scored discovery exposures,
cluster-robust by agent: **similarity OR 0.305 [0.164, 0.568] per unit cosine, p<.001 --
in the wrong direction.** The assumption-free decile view agrees and is close to
monotone: engagement falls **3.94% -> 3.60% -> 3.51% -> 3.41% -> 2.59% -> 3.65% -> 2.21%
-> 2.55% -> 2.11% -> 2.98%** from least to most similar. So the ranking signal the
recommender is built on does not select posts these agents engage with, and if anything
slightly anti-selects. Consistent with F-29 (the corpus is uniformly homogeneous, mean
pairwise 0.81, so the score has almost no real range to work with)


**Evidence.** Major caveat on any personalisation claim. The graph carries the
personalisation; the embedding does not

#### F-39 — Tier and feed position are structurally collinear, and a naive logit hides it

**Finding.** The feed builder assigns network to slots 0-4, fof to 1-7, discovery to all
12. On the network-vs-discovery subset, slot dummies for 5-11 predict "not network"
perfectly and the Hessian is **singular**. Fitting slot as one linear term conceals this
and yields an unstable estimate: **dropping the fof rows moves the network OR from 1.76
to 5.52 with no change to the contrast being estimated.** The stratified estimator is
reported instead because it conditions on the strata where the comparison actually
exists and discards the rest rather than extrapolating into them


**Evidence.** `exposure_model.py` reports no multivariable logit for tier and states
why. `test_exposure_model.py` validates the MH estimator against known-answer data
including a Simpson's-paradox case (crude 83% vs 17%, true OR 1, recovered 1.000)

#### F-35 — The noise floor is measured, and it is larger than every effect this project has ever tested for

**Finding.** `v10_replicate` reruns `v10_register` at byte-identical config (prompt v10,
temp 0.9, seed 0, 36 agents, 15 rounds); `compare.py` confirms zero config differences.
Paired within-agent differences are a clean null -- `create_post` +0.6 pp (p=.91),
`create_comment` -0.4 pp (p=.90), `like_post` -1.6 pp (p=.50), `follow` +0.1 pp (p=.94),
nothing surviving Holm -- which is what a valid replicate should look like and validates
the apparatus. **The decisive number is the dispersion.** Pure run-to-run SD is **30.7
pp** for posting share, against **30.3 pp** for the baseline->v10 comparison that
changed *both* prompt version and temperature. Two runs differing in two settings vary
no more than two identical runs. The 30.3 pp attributed to "agent x run variation" in
F-33 was **entirely noise** -- there was never signal in it. Consequence: at n=36 an
intervention must move posting share **>=14.3 pp** to be visible, and every intervention
tested here (F-21b, F-27, F-28, F-29) moved it by roughly 3-5 pp. **All four were
unfalsifiable by construction at this scale**, which is a stronger and cleaner statement
than F-30's "they failed"


**Evidence.** Definitive. Noise floor written to `data/social_timeline_noise_floor.txt`

#### F-36 — Engagement actions are 8x cheaper to study than posting

**Finding.** The per-action noise floor is not uniform: `create_post` SD 30.7 pp (ICC
.26-.31), `create_comment` 18.4 pp, `like_post` 13.9 pp, `follow` 10.6 pp with **ICC
0.000 in both runs** -- agents follow at genuinely uniform rates, so clustering costs
nothing there and the naive unpaired test was never wrong for `follow`. Agent-pairs
needed to resolve a 5 pp shift: **295 for `create_post` (8.2 runs), 106 for
`create_comment`, 60 for `like_post`, 35 for `follow` (~1 run)**


**Evidence.** Any future intervention study should target follow/like behaviour, which
is answerable in 1-2 runs, and treat posting-share claims as needing 8+ pooled runs

#### F-32 — F-30 and F-31 overstated their conclusion: the design was never able to detect the effects it was looking for

**Finding.** Power analysis on the tests actually run: at n=403 vs 418 chosen actions
the minimum detectable effect (alpha=.05, power=.80) is **9.1 pp** for `create_post`,
and the observed shift was 3.2 pp. The round-0 intro test could only detect **>=21.1
pp** and observed 17.1 pp -- **it could not have confirmed F-28 no matter what
happened.** Worse, those MDEs assume independent observations, and the actions are
clustered within agent: per-agent `create_post` share ranges 0.14-1.00, **ICC ~
0.31-0.38, design effect ~ 4.3-4.8**, so effective n is **~90, not ~410**, and the true
MDE is **~20 pp**. Recomputing the two "significant" F-31 hits with clustering: z 2.23
-> 1.05 (p~.29) and z 2.10 -> 0.99 (p~.32) -- null on their own, before any Bonferroni.
**The correct statement is not "the interventions did nothing" but "this design cannot
distinguish no effect from an effect smaller than ~20 pp."** The capacity-limit
conclusion is still the best available explanation but is no longer *established* by
these runs


**Evidence.** F-30/F-31 downgraded from "negative result" to "underpowered,
inconclusive". Do not repeat the capacity claim as settled

#### F-33 — The unit of randomisation is the run, and every cross-run p-value so far had n=1 per condition

**Finding.** Treating 418 actions as 418 observations when they come from 36 agents in a
single run is the same units-of-analysis error as F-30's pair-level bootstrap, one level
up. **Fix available in existing data:** `select_diverse` is deterministic, so the same
36 personas occupy the same agent ids in every run (verified 36/36 for baseline vs v10)
-- a **paired within-agent design** is therefore valid retrospectively and removes the
between-agent variance that causes the design effect. Paired MDE improves from ~20 pp to
**4.7-14.1 pp**. Paired baseline->v10: `create_post` -5.3 pp (p=.29), `create_comment`
-0.5 pp (p=.88), `follow` +0.8 pp (p=.62), `like_post` +4.2 pp (p=.041, but below its
own 5.8 pp MDE and not surviving Bonferroni across 4 tests). **The dominant term is
within-agent across-run SD of 30.3 pp for posting share** -- the same persona posts 20%
of the time in one run and 80% in another. Roughly half of that is binomial noise from
only ~11 actions per agent; the rest is genuine agent x run variation


**Evidence.** Paired analysis is now the required method for any cross-run claim.
Powering an intervention to 5 pp needs ~288 agent-pairs, i.e. ~8 pooled runs at 36
agents or one run at ~240 agents

#### F-34 — "Nobody replies to anybody" was wrong

**Finding.** Threading is stable and unremarkable across runs: **38.9% of commented
posts became threads in baseline, 35.5% in v9, 32.5% in v10** (>1 comment on the same
post). Comments do reach agents -- the three-tier `refresh()` override calls
`pl_utils._add_comments_to_posts` (`timeline_platform.py:649`) exactly as upstream does,
and all 40 commented posts in v10 were subsequently shown to someone


**Evidence.** Open question retired. No bug; the earlier claim was stale

#### F-31 — The action mix is also unchanged since baseline — the negative result covers behaviour, not just content

**Finding.** Full-run comparison (v10 n=418 chosen actions, v9 n=447, baseline n=403):
baseline->v10 `create_post` 63.5%->60.3% (p=0.34), `create_comment` 14.6%->14.1%
(p=0.83), `like_post` 7.2%->11.0% (p=0.058), `follow` 10.4%->11.0% (p=0.79). **Nothing
significant.** The pairwise v9->v10 test *did* return two hits (`create_post` p=0.026,
`like_post` p=0.036), and taken alone they look like the reception block being a
regression that the reword fixed. They are not: v9 is itself indistinguishable from
baseline on every measure (`create_post` p=0.22, `create_comment` p=0.087, `like_post`
p=0.88), so both "significant" results sit between two runs that each match baseline.
**12 tests were run; at alpha=0.05 that expects ~0.6 false positives, and Bonferroni
gives alpha=0.0042 — neither hit survives.** This is the same error class as F-30's
pair-level bootstrap: a test applied at the wrong unit or without correction
manufactures an effect


**Evidence.** Recorded. Any future intervention must be judged against **baseline**, not
against the previous run, and corrected for the number of comparisons

#### F-29 — The homogeneity is the model's, not the feed's

**Finding.** Tested directly: two posts shown to the same agent are 0.824 similar, a
random pair from the whole corpus is 0.809 — the feed contributes **+0.015**. The corpus
is uniformly alike regardless of who saw what, so the echo-chamber explanation is dead
and no ranking change can fix it


**Evidence.** Recorded. Rules out feed-side fixes

#### F-28 — Round 0's wording seeded the register for the entire run

**Finding.** The empty-feed line read *"a good moment to post something yourself"*, and
with 36 agents hitting an empty feed simultaneously, **77% of round-0 posts were
introductions**. Those became the whole feed, and agents mimic what they read — vague
begets vague. The same model prompted cold writes concrete things ("attended a panel on
supply chain innovation")


**Evidence.** Reworded to state the fact without inviting an introduction. Says nothing
about what to write

#### F-27 — Agents were posting into a void

**Finding.** In R-17, 21 posts drew likes and 36 drew comments, and none of it was ever
visible to their authors — an agent could not tell whether anything it wrote had reached
anyone. A plausible reason 64% of all actions were `create_post`


**Evidence.** Added a reception block: likes, dislikes and reply counts on your own
recent posts. Information, not instruction — nobody is told to engage, they are told
what happened

#### F-26 — A self-inflicted regression, traced to one word

**Finding.** Malformed calls climbed every run from v3 onward: 113 → 169 → 429 →
**831**. Cause: prompt v3 opened with *"Take TWO OR THREE of these **actions** this
turn"*, reintroducing the exact word F-20 had removed. The smoking gun is `follow() got
an unexpected keyword argument 'actions'` — **the plural**, 87 times


**Evidence.** Reworded without the word, and the forced volume dropped entirely. Smoke
test: **831 → 0 malformed**

#### F-25 — Reach came from a global pool, not the social graph

**Finding.** Every agent drew candidates from all posts ranked by interest × recency, so
a completely unconnected agent saw as much as a hub. That is a magazine, not a social
network


**Evidence.** Three-tier feed: **network** (people you follow, *not* interest-filtered)
> **friend-of-friend** (2-hop, interest ranked) > **discovery** (small global slice).
Isolation is not penalised — it falls out, since an agent with no follows fills only the
discovery tier

#### B-21 — Republishing a downloaded artifact silently renamed two of them

**Where.** Ours — the republish procedure, not any file in the repo.

**Symptom.** After the 2026-09-03 re-figuring, the gallery listed the write-up and
field guide as **"writeup"** and **"guide"** instead of *Connection Over Content* and
*Simulation 4 Field Guide*. Their published pages also carried a duplicated document
skeleton.

**Cause.** `Artifact action:read` returns the page *as served*, including the
injected `<!doctype html><head>` and the ~13.8 KB frame-runtime script. Those edits
were made to that downloaded file and published back verbatim. Two consequences: the
publish wrapper wrapped an already-complete document, and — because only the first
**8 KB** is scanned for a `<title>` — the real `<title>` now sat at byte **14,080**,
past the window, so each artifact fell back to its *filename* for a name.

**Why it went unnoticed.** The pages still rendered. Nothing errored. The only
visible symptom was in the gallery listing, which is not where you look after
publishing.

**Fix.** Strip everything before `<title>` and the trailing `</body></html>` before
republishing, so the file contains only authored content and `<title>` sits at byte
0. Both artifacts re-published; names restored.

**Rule going forward.** *A downloaded artifact is not a publishable artifact.* Take
the authored region only. Verify with `s.find('<title>') < 8192`.

#### B-18 — The explorer describes the pre-three-tier feed for all runs, including the nine the results rest on

**Where.** Ours, `make_graph.py:686-690` (Algorithm box) and `:1250-1260`
(Method & integrity tab).

**Symptom.** For every one of the 13 runs the Method tab states: *"A feed is the
union of **two sources**, and every exposure records which one delivered it:
**recsys** (the ranking chose it), **following** (the viewer follows the author),
or **both**. 8 algorithmic posts + 4 from people followed, ranked from a pool of
30."*

For the nine three-tier runs this is wrong in every particular. The feed is
**three** tiers, not two; 5 network + 3 fof + 4 discovery into a fixed `feed_size`
of 12, not 8+4; `both` does not exist in that vocabulary (confirmed: zero rows);
and `fof`, which does, is not mentioned. The Algorithm box repeats the same
8/4/30. These are the nine runs every published estimate is computed on.

**Cause.** The Method tab was written for the v4-v7 feed and never revisited when
F-25 introduced the three-tier builder. It reads config fields that still exist
but went inert (F-46).

**Why it survived.** The numbers it prints are real config values, so the tab
looks data-driven and internally consistent. Nothing is blank or obviously stale —
it is confidently describing a different experiment.

**Fix — DONE 2026-09-03.** The Method tab and Algorithm box now branch on
`algorithm.feed_model`: three-tier runs get the real tier breakdown, slot counts and
backfill rule; pre-three-tier runs keep the two-source description plus an explicit
note that they are excluded from every estimate and why. Explorer regenerated and
republished.

#### B-19 — The explorer renders the held-aside runs in the three-tier vocabulary

**Where.** Ours, `make_graph.py:942` (`SRCNAME`) and `:1111` (`SRCN`), both
`['discovery','network','fof','both','?']`; encoding at `:1384-1391`.

**Symptom.** In the People tab's per-agent exposure table and the Rounds tab's
feed-source breakdown, `v4_full`..`v7_full` exposures are labelled **discovery**
and **network**. Those runs' databases contain no such values — they hold `recsys`
(3,651 rows in v4_full), `following` (889) and `both` (157). The index collapse at
`:1389` maps `recsys`->0->"discovery" and `following`->1->"network".

**Cause.** Deliberate, documented in-code as *"They are the same concepts renamed,
so both vocabularies map to one index set and runs from either era stay readable
side by side."*

**Why that reasoning does not hold.** The study's own argument contradicts it. The
write-up excludes these runs from every estimate and then presents their pooled
**OR 5.00 [3.83, 6.52]** as an *independent replication* — evidence that carries
weight *because* the feed builder is structurally different, not a renaming. The
build log holds them apart for the same reason (F-37, F-41). Displaying their
exposures under three-tier names erases, in the artifact, the very distinction the
headline evidence depends on. It is also the exact failure class as the retracted
F-38: a column shown under a name that is not what it holds.

**Fix — DONE 2026-09-03.** `SRC_LABELS` now holds one label set per era and
`srcName(run, i)` selects between them from `algorithm.feed_model`. Three-tier runs
read discovery/network/fof; pre-three-tier runs read recsys/following/both. The
shared `SRCNAME`/`SRCN` arrays are gone.

#### B-20 — An unrecognised feed source would silently render as "both"

**Where.** Ours, `make_graph.py:1389` — `SRC.get(e.get("source"), 3)`.

**Symptom.** The default index for an unknown source string is **3**, which
`SRCNAME`/`SRCN` render as `"both"` — a plausible-looking label borrowed from the
pre-three-tier vocabulary. Index **4** (`'?'`), the slot that exists precisely to
mean "unrecognised", is unreachable: nothing ever produces it.

**Why it is live rather than theoretical.** `_log_exposure` can emit the string
`"unknown"` (`timeline_platform.py:728`) whenever a shown post is in none of the
three tier sets. It has never fired, so no wrong row exists today. But both halves
are in place: the writer can produce a value the reader will mislabel, and it will
mislabel it as a real category rather than as an error. This is the project's own
catalogued upstream failure mode — fail silently, produce quietly meaningless data
— reproduced in our code.

**Fix — DONE 2026-09-03.** The encoder defaults to `4`, which renders as
`unrecognised` in both label sets. Index 3 is now reachable only from a literal
`both`. Counting `unknown` in `self.stats` (F-47) remains open.

#### B-17 — The write-up's forest plot drew the 5-run estimates under 9-run labels

**Where.** The write-up artifact (`55d7c5a5`), section 02 forest plot.

**Symptom.** When the four overnight replicates took the study from five runs to
nine, the forest plot's printed values were updated but the CSS geometry that
draws each bar was not. Every bar was positioned from the superseded estimate
while the number beside it read the current one. Decoding the published
`left`/`width` percentages against the plot's own log axis
(`pos(x) = (log10(x)+1) x 45.35`, calibrated from its 0.1/0.3/1/3/10 ticks)
recovers the old values exactly:

| Row | Drawn at | Labelled |
|---|---|---|
| network vs discovery | 3.55 [2.93, 4.30] | 3.51 [3.06, 4.04] |
| fof vs discovery | 1.97 [1.25, 3.11] | 2.34 [1.64, 3.35] |
| network vs fof | 2.13 [1.42, 3.16] | 1.85 [1.38, 2.48] |
| seen before | 2.33 [1.83, 2.94] | 2.62 [2.18, 3.15] |

**Cause.** The plot stores each bar's position as a hand-computed literal rather
than deriving it from the estimate, so a value edit and a geometry edit are two
separate actions and nothing enforces that both happen. The field guide's
equivalent plot computes geometry from a data array and was internally
consistent — the same content, one implementation self-checking and one not.

**Fix.** All five rows recomputed from the analysis output and verified
programmatically against the axis scale (max placement error 0.05%). The lesson
generalises past this plot: **a chart whose marks are literals will drift from
its labels silently.** Prefer the field guide's pattern — one data array, geometry
derived — for anything that gets re-estimated.

**Found.** 2026-09-03, while re-figuring both artifacts from 5-run to 9-run
numbers. Nothing flagged it; it surfaced only because the bar positions were
checked against the axis rather than trusted.

#### B-16 — The graph's edge filter made cumulative interactions look like they vanished

**Where.** Ours, `make_graph.py:551` `interactionEdges()`

**Symptom.** Scrubbing the round slider on `v10_rep6`, interaction edges appeared
to **disappear** between round 5 and round 6 — from a well-connected picture to a
sparse one. Interactions are strictly cumulative and can never decrease, so the
picture contradicted the data.

**Cause.** A decluttering rule: at 60 or fewer interaction pairs the graph draws
every one; above 60 it silently switches to drawing only pairs that interacted
more than once. `v10_rep6` crosses that threshold at exactly round 6 — **54 pairs
drawn at round 5, then 61 pairs exist but only 14 are drawn at round 6.** The
underlying data grew, as it must; the rendering rule changed underneath the
viewer with no indication. A disclosure existed but sat in the methodology text
of a different tab and quoted run-totals, so it was invisible at the moment of
confusion.

**Worse than first thought.** The original rule had three modes — draw everything
at <=60 pairs, else only pairs seen more than once, else the 40 heaviest — and
switched between them as density grew. Because the modes return wildly different
counts, a run could collapse **more than once**: `v10_rep5` drops twice, 56 -> 40
at round 5 (falling to the top-40 mode) and 40 -> 14 at round 6 (switching to
repeated-only), while its real count rose 56 -> 63 -> 74.

**Fix.** Replaced with a single rule that cannot decrease: **draw the heaviest
pairs, capped at 60**. `min(real, 60)` rises and then plateaus, so the drawn
count never falls, and every round below the cap still shows all its edges — the
early network stays fully legible, which the fixed-rule alternatives lost. A
caption under the graph updates live with the slider, states that the view is
cumulative, and when the cap bites says "Drawing the 60 heaviest of 113
interaction pairs ... the hidden pairs still exist: the tables and every
statistic are unfiltered."

**Verified** in the browser by scrubbing every round of **all 13 runs** in the
artifact and asserting the drawn count never decreases: zero drops.

**Found by.** Gordon, reading the artifact and noticing the picture disagreed
with the claim that interactions accumulate.

#### B-15 — The overnight batch script silently failed every analysis

**Where.** Ours, `overnight_replicates.sh`

**Symptom.** All four overnight runs (R-21..R-24) completed normally, but each
reported "ran but analysis FAILED", and the script's final line read "batch done:
0 of 4 runs completed and analysed" despite four complete runs sitting on disk.

**Cause.** The script called `analyze.py "data/social_timeline_$LABEL.db"`
positionally. `analyze.py` requires the path behind `--db`, so argparse exited
with a usage error every time. The run data was never at risk -- only the
convenience step of analysing it automatically.

**Fix.** Pass `--db`. Found after the first run at 00:31; the script was
deliberately **not** edited mid-flight, because bash re-reads a running script by
byte offset and editing one in place can corrupt execution. A separate watcher
process analysed rep4-rep6 as their manifests appeared, and rep3 was analysed by
hand. The flag was fixed once the batch had finished.

**Found by.** The monitor on `overnight.log`, at the first run's completion.

#### B-14

**Where.** Ours — `refresh()` tier assembly

**Symptom.** 37 exposures in R-16 were labelled `fof` but came from a **direct
connection**, so the social/algorithmic split the tiers exist to measure was wrong

**Cause.** fof excluded only the posts already *picked* for the network tier, which
`network_slots` caps at 5 — so a followee's sixth post fell through into fof

**Fix.** Exclude posts by anyone already followed, not merely the posts already
chosen. Tiers are now disjoint

#### B-13

**Where.** Ours — `refresh()` + upstream `trace` schema

**Symptom.** A duplicate refresh in one round threw `IntegrityError` and destroyed the
whole feed

**Cause.** `trace`'s primary key is `(user_id, created_at, action, info)`, and for a
refresh `info` is the entire feed — so refreshing twice with an unchanged feed collides.
Same shape as B-12: one small error taking down everything around it

**Fix.** Catch it and count it. Exposure rows are already written by that point, so
only the duplicate audit row is lost — the one row carrying no new information

#### F-24 — A third of posts are the author's bio, echoed back

**Finding.** 21 of 66 posts (32%) closely reproduce the author's own profile text — one
at similarity 1.00, i.e. verbatim. Posts *do* match their author (0.785 to own bio vs
0.641 to others, +0.14 gap), but that number is inflated by parroting rather than earned
by the agent writing something new


**Evidence.** Open — likely needs the prompt to stop showing the bio as if it were
content to riff on

#### F-23 — F-22's fix backfired badly and was reverted

**Finding.** Gluing the id into the author string as `"name (followee_id=7)"` made
malformed calls jump 169 → **429**, with `follow()` handed `post_id` 145 times and
`action=` wrapping exploding across every action. Burying a key=value pair inside a JSON
*value* made the object harder to read, so the model grabbed the first id it saw


**Evidence.** Reverted to v6's shape: the id stays in its own field named exactly as the
tool expects

#### F-22 — Removing digits from handles created a new failure

**Finding.** F-20's fix worked precisely — invalid follow targets fell 77→17, follows
rose 53→73 — but with no digits to grab, the model started calling `follow()` with **no
argument at all** (29 times) and reverted to `action=` wrapping. Action rate fell
0.72→0.611, malformed rose 113→169


**Evidence.** Stop fighting the habit: the id now travels *with* the name — `author:
"strategist_chief (followee_id=7)"` — so grabbing digits and reading the field both
yield the right value

#### F-21b

**Finding.** **Notifications are disproved, now cleanly.** R-15 tested them confounded
with F-22's damage; R-16 ran them with F-22 reverted and got **0 of 17 threads** with an
author replying — identical to before. Being unable to see replies was never the reason
nobody answers anybody. The real cause is elsewhere and is still unknown

**Evidence.** Open. Notifications are kept (they cost nothing and are realistic) but
they are not the fix

#### F-21 — Agents never saw replies to their own posts, so nobody ever answered anyone

**Finding.** In R-13, 17 posts drew multiple comments and the author replied back on
**zero** of them. Cause: an agent's own posts are correctly excluded from its feed, but
the comments live *under* those posts — so replies were invisible to the one person they
were addressed to. The result was parallel monologue, not conversation


**Evidence.** Added a notifications block: replies you received, with the `post_id` to
answer, `comment_id` to like, and `followee_id` to follow

#### F-20 — Numeric handles were being parsed as ids

**Finding.** The scraped personas ship as `user0`..`user110`; agents read the digits out
of the handle and passed them as ids — `follow(46)` for `user46`. Measured in R-13:
**230 rejected follows aimed at id 46, 136 at 44, 126 at 96**, plus 280 at the
placeholder `12345`. This is why follows fell 90 → 53


**Evidence.** Handles are now generated from the persona's own words: readable, unique,
digit-free (`@strategist_chief`, `@advanced_trading`)

#### F-19 — Agents acted on targets they had never seen

**Finding.** Round 0 of the first v5 attempt logged **zero exposures** yet produced 12
follows and 4 likes — agent 13 "liked" post 2 having never seen it, agent 2 "followed"
agent 1 with no exposure to them. B-10 catches non-existent ids, but a model guessing a
small integer lands on a *valid* agent id most of the time, so that check cannot catch a
valid-but-unseen target. Measured contamination: **8 of ~26 attempted actions (~30%)**
were blind


**Evidence.** Fixed by an informed-action gate; search hits count as encountered

#### F-17 — The feed discarded its own ranking

**Finding.** `refresh()` ranked 30 candidates then `random.sample()`d 8
(`platform.py:276-278`). Median rank shown was 14/30; only 16% came from the top 5.
Posts were also rendered in arbitrary SQL order, so an agent's best match could appear
anywhere


**Evidence.** Fixed: top-ranked + 2 explore slots, rendered best-first. Median rank
14→3, top-5 share 16%→67%

#### F-18 — The persona population was the ceiling on personalisation

**Finding.** Reddit `persona` texts (which become the system prompt) are **0.963**
similar to each other; `bio` (which the recommender ranks on) 0.829. Agents were handed
near-identical characters


**Evidence.** Switched to diversity-selected scraped twitter bios: **0.637**

#### F-16 — Freshness barely counts over a short run

**Finding.** Upstream recency `log((271.8-age)/100)` is calibrated for ~170 timesteps;
across 12 rounds it moves only 0.9999→0.9586 (spread 0.04) while cosine similarity spans
~0.25. Ranking was therefore ~85% similarity, and a round-0 post was never displaced —
post #3 reached 33 agents while a round-10 post reached 1


**Evidence.** Measured; fixed via `recency_span_rounds`

#### F-15 — Agents attempt actions and fumble the arguments

**Finding.** — 18 malformed tool calls in 5 rounds of the full run, 10 of them `follow`,
mostly "unexpected keyword argument". These leave no trace row, so they were previously
invisible and counted as "did nothing"


**Evidence.** Measured by `analyze.py --log`

#### F-14 — Group chat hijacks the prompt and crowds out feed engagement


**Evidence.** `agent_environment.py:49-53` puts `$groups_env` *before* `$posts_env`;
`:40-48` is a wall of imperatives; `:118-135` renders it every turn regardless of
`available_actions`. Measured in R-5


**Note on F-3.** This is the most consequential finding of the investigation. Had we
selected the option whose name most suggests "the interest-based one", the run would
have produced a dataset labelled as using an interest-based recommendation algorithm
that was in fact a uniform random number generator — with no error raised anywhere.
This is the same fail-open class as Sim 3's shield, which silently failed ~12.5% of
calls and polluted its own results. It is the direct justification for making an
explicit algorithm assertion a hard requirement (spec §4.1, §4.3).

**Note on MPS.** `load_model` selects `torch.device("cuda" if torch.cuda.is_available()
else "cpu")` (`recsys.py:85`). This machine reports `cuda False, mps True`, so
TwHIN-BERT will run on **CPU** despite an available MPS backend. Recorded as a known
performance ceiling; not changed, because correctness comes before speed and altering
device selection would diverge from upstream behavior. Revisit only if embedding time
proves to be a real bottleneck (measured, not assumed).

---

## 5. File inventory

Every file this build **consumes**, **creates**, **modifies** and **produces** —
what it is, where it lives, and where it came from. A file that the simulation
reads but nobody wrote is just as much a dependency as one we authored, and was
missing from earlier versions of this section.

All simulation and analysis code lives in `examples/experiment/social_timeline/`;
that prefix is dropped from the entries below. Paths outside it are given in
full.

### Consumed — inputs the simulation reads but did not create

#### `data/reddit/user_data_36.json`

**What.** The 36 personas. 32 KB, one record each with `realname`, `username`,
`bio`, `persona`, `age`, `gender`, `mbti`, `country`, `profession`,
`interested_topics`.

**Where from.** **Ships with OASIS upstream** — last touched by upstream author
`yiyiyi0817` in commit `9db593a`, not by us. This matters for the result: we did
not author the population, so we could not have shaped it to produce the answer
we wanted.

**How it is used.** `personas.py:192` `select_diverse()` picks a maximally
separated subset (deterministic — no RNG, so persona #7 is agent 7 in every
run); `timeline_agent.py:341` `compose_persona()` flattens each record into the
paragraph that becomes that agent's **system prompt**.

**Caveat.** Topically lopsided — 24 of 36 declare "Business", mean pairwise bio
similarity 0.83. That caps what any interest-based recommender could
discriminate.

#### `Twitter/twhin-bert-base` (Hugging Face model)

**What.** 279M-parameter BERT trained by Twitter on tweets. Turns any text into
768 numbers so two pieces of text can be compared for meaning.

**Where.** Downloaded on first use to `~/.cache/huggingface/hub/`, ~1.1 GB. Not
in the repo.

**How it is used.** `embedding.py` mean-pools `last_hidden_state` — deliberately
NOT the `pooler_output` upstream uses, whose weights are randomly re-initialised
in every process and would make runs unreproducible.

#### `llama3.1:8b` (Ollama model)

**What.** The language model that *is* every agent. 4.9 GB, served locally at
`http://localhost:11434/v1`.

**Where.** Ollama's own store, outside the repo. `ollama pull llama3.1:8b`.

**Why this one.** OASIS agents act by emitting tool calls, and this model
supports them natively. A model without tool-calling cannot drive the simulation
at all. Nothing leaves the machine and there is no API bill.

#### The OASIS engine itself — `oasis/`

**What.** The upstream framework: database schema, the agent-to-LLM plumbing,
the `Platform` and `SocialAgent` classes this project subclasses.

**How it is used.** Read extensively (§2) and subclassed, never edited. `oasis/`
stays byte-identical to upstream commit `10b1a5b`.

### Created

#### `docs/superpowers/specs/2026-08-24-social-timeline-design.md`

**Purpose.** Design spec

**Status.** Committed `2b82487`

#### `SIM4_LOG.md` Part I

**Purpose.** This document

**Status.** In progress

#### `embedding.py`

**Purpose.** Mean-pooled TwHIN-BERT embeddings (D-13). Exists because upstream's
`pooler_output` path is non-deterministic and near-non-discriminative (B-1/B-2)

**Status.** Working

#### `timeline_platform.py`

**Purpose.** `TimelinePlatform(Platform)`: implements the ranking, creates and writes
`rec_candidates` / `rec_history` / `round_boundary`, asserts the algorithm ran, enforces
DM privacy

**Status.** Working (R-4)

#### `timeline_agent.py`

**Purpose.** `TimelineAgent` (per-agent exception isolation) and the persona→agent-graph
generator, with zero initial follow edges (D-10)

**Status.** Working (R-4)

#### `run_simulation.py`

**Purpose.** Driver: 27-action set, all-`LLMAction` rounds, run manifest with exact
config, timings, counters and action tallies

**Status.** Working (R-4), B-3 fixed

#### `check_deps.py`

**Purpose.** Stage 0 gate: 6 checks — torch devices, TwHIN-BERT loads, embeddings
discriminate across two topics, embedding space reproduces a baseline recorded in a
*different* process, upstream pooler regression guard, Ollama reachable

**Status.** **Strengthened and passing** (R-3). Original 3-text single-process version
passed by luck and missed B-1/B-2

#### `personas.py`

**Purpose.** Persona loading, greedy max-min diversity selection, digit-free handle
generation (F-20), separability reporting. **`select_diverse` is deterministic**, which
is what makes the paired design in `compare.py` valid

**Status.** Working

#### `analyze.py`

**Purpose.** Per-run ledgers → `_analysis.json` / `_analysis.txt`. Carries an explicit
warning that its report is single-run and that cross-run claims need `compare.py`
(F-32/F-33)

**Status.** Working

#### `dossier.py`

**Purpose.** The exhaustive per-round transcript → `_DOSSIER.txt`, ~28k lines / 2 MB per
run. Real names, every action, every exposure, per-pair chronologies

**Status.** Working

#### `make_graph.py`

**Purpose.** Multi-run interactive artifact (network graph, per-round detail, per-agent
records, run comparison)

**Status.** Working, 9 runs

#### `compare.py`

**Purpose.** **Cross-run comparison.** Paired within-agent tests (agent ids are stable
across runs), Holm correction, MDE reported alongside every null, ICC/design-effect
diagnostics, `--replicate` noise-floor mode, and an F-22 warning when two runs differ in
more than one setting

**Status.** Working (F-33)

#### `exposure_model.py`

**Purpose.** **Within-run engagement analysis.** Mantel-Haenszel stratified by (agent,
feed slot); per-run stability; independent replication on pre-three-tier runs;
similarity tested inside `discovery` only because the score is missing-not-at-random

**Status.** Working (F-37..F-41)

#### `recency_check.py`

**Purpose.** Pulls similarity and recency apart -- they are stored multiplied
together in the exposure record, which is what made the retracted similarity
claim possible. Recovers both from `rec_candidates`, refits the original
specification on each separately, and tests repeat exposure. Produced the
retraction and the project's second result.

**Status.** Working. 9 runs, 37,668 discovery rows.

#### `noise_floor.py`

**Purpose.** Measures how much results move when nothing is changed at all,
across every pair of identical-configuration runs. Written 2026-09-02 to settle
whether the original noise floor -- which rested on a single replicate pair --
was a fair draw. It was: all four single-pair figures fall inside the spread of
all fifteen pairs.

**Status.** Working. 15 pairs over six identical runs.

#### `test_actions.py`

**Purpose.** Gate: every engagement action works mechanically, so absence in a run is a
model choice not a broken surface

**Status.** Passing

#### `test_instrumentation.py`

**Purpose.** Gate: exposure/interaction records reconstruct correctly from both sides

**Status.** Passing

#### `test_compare.py`

**Purpose.** Gate: Holm vs hand-computed values and order-invariance, MDE closed form
and monotonicity, ICC ~0 for homogeneous agents vs 0.73 for heterogeneous, paired
recovery of an injected effect, no false positive on a null

**Status.** **16/16 passing**

#### `test_exposure_model.py`

**Purpose.** Gate: Mantel-Haenszel against known-answer data — homogeneous-OR recovery,
true null, **Simpson's paradox (crude 83% vs 17%, true OR 1, recovered 1.000)**, stratum
dropping, degenerate inputs, CI narrowing

**Status.** **12/12 passing**


### Modified

| Path | Change | Why |
|---|---|---|
| `oasis-env` | Added `statsmodels` | Cluster-robust logistic regression for F-38. Hand-rolling it is exactly what produced F-30 and F-32 |

*`oasis/` itself remains untouched per D-1 — every deviation is a subclass.*

### Produced — output files, and which tool writes each

Nothing here is hand-edited; every file is regenerable from the database by
re-running the tool named. `<label>` is the run label, e.g. `baseline`.

**Per run — written by `run_simulation.py`**

| File | Size | Contents |
|---|---|---|
| `data/social_timeline_<label>.db` | ~8 MB | The entire world: users, posts, comments, follows, likes, `trace`, and our three instrumentation tables. **Gitignored** (`.gitignore:98`, `*.db`) — regenerable only by re-running the 2-hour simulation, so back it up separately. |
| `data/social_timeline_<label>.json` | ~8 KB | The run manifest: exact settings, library versions, per-round timings and counters, action tallies. Committed. This is what makes a run self-describing years later. |

**Per run — written by the analysis tools**

| File | Size | Written by |
|---|---|---|
| `..._<label>_analysis.json` | ~1.6 MB | `analyze.py` — the hinge file every other tool reads |
| `..._<label>_analysis.txt` | ~630 KB | `analyze.py` — human-readable per-run summary |
| `..._<label>_DOSSIER.txt` | ~2 MB | `dossier.py` — the ~28,000-line round-by-round transcript |

**Cross-run reports**

| File | Written by | What it answers |
|---|---|---|
| `data/social_timeline_exposure_model.txt` | `exposure_model.py` | Does connection or content predict engagement? |
| `data/social_timeline_recency_check.txt` | `recency_check.py` | Similarity vs recency pulled apart; the repeat-exposure result |
| `data/social_timeline_noise_floor_6runs.txt` | `noise_floor.py` | How much do results move when nothing changes? (15 pairs) |
| `data/social_timeline_noise_floor.txt` | `compare.py` | The original single-pair replicate comparison |
| `data/graph.html` | `make_graph.py` | The interactive explorer artifact (~5 MB) |

**Not committed**

| Path | Why |
|---|---|
| `data/*.db` | ~8 MB each, 15 of them. `.gitignore:98` |
| `data/overnight_logs/` | 241 MB of verbose LLM output from the replicate batch. The manifests already carry the timings that matter. `.gitignore:107` |
| `oasis-env/` | The virtualenv. Rebuild with `python3.11 -m venv oasis-env && pip install -e . && pip install statsmodels` |

Total data footprint on disk: **161 MB** across all runs, of which ~120 MB is
databases that git does not track.

### Where to find everything

```
oasis/
├── SIM4_LOG.md (Part I)                     this file
├── PROJECT_LOG.md                        project-wide log (modified)
├── overnight_replicates.sh               the batch runner
├── .gitignore                            :98 *.db   :107 overnight_logs
├── docs/superpowers/specs/
│   └── 2026-08-24-social-timeline-design.md    the design spec
├── oasis/                                UPSTREAM ENGINE — never edited
├── data/
│   ├── reddit/user_data_36.json          THE 36 PERSONAS (upstream)
│   └── social_timeline_*                 every run's db, manifest, analysis,
│                                         dossier, and the cross-run reports
└── examples/experiment/social_timeline/  ALL 7,540 LINES WE WROTE
    ├── run_simulation.py                 the start button
    ├── timeline_platform.py              the website
    ├── timeline_agent.py                 one pretend person
    ├── personas.py                       the personalities
    ├── embedding.py                      text -> numbers
    ├── check_deps.py                     pre-flight gate
    ├── analyze.py                        db -> analysis json
    ├── dossier.py                        the transcript
    ├── exposure_model.py                 the main result
    ├── recency_check.py                  the retraction + repeat exposure
    ├── noise_floor.py                    how much noise is there
    ├── compare.py                        run vs run
    ├── make_graph.py                     the explorer artifact
    └── test_*.py                         four gates, 57 checks
```


---

## 6. Chronological log

### 2026-08-24 — Investigation and design

1. Checked repo state: clean working tree, `main` @ `10b1a5b`, 6 commits ahead of
   `origin`. No uncommitted work outstanding (a standing check for this repo, since
   report files have historically been edited across sessions without being committed
   same-day).
2. Read the OASIS source tree per §2.1. Produced findings F-1 through F-12.
3. Reviewed MultiAgent4Collusion and MatrAIx-Persona-8B (§2.2).
4. Wrote the design spec; committed as `2b82487` on new branch `social-timeline-sim`.
5. User corrections received: the §1 scenario is illustrative, not a fixture (→ D-9
   reversed, D-10 adopted); no full runs until small ones are clean (→ D-11
   strengthened into staged gates); maintain this build log.
6. Spec updated accordingly: §1 reframed, §4.4 rewritten, §9 replaced with a staged
   gate table.

### 2026-08-24 — Stage 0: dependency gate

7. Wrote `examples/experiment/social_timeline/check_deps.py`, deliberately exercising
   the real OASIS code paths (`get_recsys_model`, `generate_post_vector`) rather than
   an approximation, so that whatever passes the gate is what the simulation calls.
8. Ran it (R-1). All four checks passed. TwHIN-BERT downloaded and loaded in 24.6s.
9. Two things in the output looked wrong despite the pass: a warning that
   `pooler.dense.{weight,bias}` were "newly initialized", and a thin discrimination
   margin. Checked `process_batch` and confirmed it returns `pooler_output` —
   i.e. embeddings pass through those random weights.
10. Wrote a probe (R-2) comparing `pooler_output` / `mean_pooled` / `cls_raw` across
    two topics and two separate processes. Confirmed **B-1** (embedding space differs
    per process, so runs are not reproducible) and **B-2** (pooler margin collapses to
    `+0.0008` in one process — noise).
11. Adopted **D-13**: implement ranking in our subclass with mean pooling and score
    capture, deviations stated. Recorded that `check_deps.py` itself needs
    strengthening — a gate that can pass by luck is not a gate.

### 2026-08-24 — Stage 1: plumbing

12. Wrote the four implementation modules (§5). Design points worth recording:
    - `post.user_id`, `follow.follower_id`, `trace.user_id` and `rec.user_id` all
      store **agent_id**, not the `user` table's primary key (`platform.py:407`,
      `user_id = agent_id`). The `user` table alone has both columns. Upstream's rec
      insertion works only because 0-based positional indices happen to coincide with
      agent_id (F-12). Our code keys on `agent_id` explicitly everywhere, which
      removes that class of off-by-one rather than reproducing it. Logged as **F-13**.
    - `UserInfo.to_system_message()` forks on `recsys_type`: the Reddit prompt
      includes gender/age/MBTI/country, the Twitter prompt does not
      (`config/user.py:50-111`). We need the Twitter platform (follows, reposts) but
      the richer persona, so the full persona is composed into the `user_profile`
      string the Twitter prompt already renders. Prompt *structure* is untouched —
      Sim 1 Attempt 1 proved structural changes break tool-calling outright.
    - `env.step()` gathers agent tasks with a bare `asyncio.gather(*tasks)`
      (`env.py:193`, no `return_exceptions=True`), so one agent raising aborts the
      round — exactly how Sim 3 lost a run. Absorbed in `TimelineAgent`, the only
      place available without modifying `oasis/`.
13. Verified cheaply before spending LLM time: all modules import, the action set is
    exactly 27, and personas compose into rich readable profiles.
14. Ran R-4 (4 agents, 2 rounds). **Plumbing gate passed** — details in §7.
15. Found **B-3** (counts read after the cursor closed). Fixed, and added a
    `turns_without_action` metric so tool-calling health is measured every run
    against Sim 1's ~89% baseline rather than eyeballed.

**On the absence of action diversity in R-4.** The trace showed only `create_post`
(6), `sign_up` (4), `refresh` (4) — no likes, follows, or comments at all. Before
attributing this to the model, the plumbing was checked directly: **all 27 tools are
correctly registered** on the agent (`action_tools`), with nothing requested-but-
missing. So the tool surface is intact and the model simply chose to post.

Much of that is legitimate at this scale: in round 0 no posts exist, so the feed reads
"there are no existing posts" and posting is the only sensible action. That accounts
for 4 of the 8 agent-turns. Only round 1 is informative, and 4 turns is far too small
a sample to conclude anything.

One real signal did surface: `do_nothing` **does** write a trace row
(`platform.py:1332-1344`), and no such rows exist — so the two round-1 agents that
produced nothing emitted **no tool call at all**, rather than deliberately choosing to
abstain. That is a genuine tool-calling miss. Whether it is a rate worth worrying
about is Q-2, and needs stage 2's larger sample to answer.

### 2026-08-24 — Stage 2: behaviour, and the group-chat problem

16. Wrote `analyze.py`, producing the per-agent micro-detail ledger (§4.5 of the
    spec): seen / seen-and-acted / seen-and-ignored / never-seen, pairwise exposure
    counts, interaction matrix, and the follow graph at every round. Verified against
    the R-4 database.
17. Ran R-5 (8 agents, 4 rounds, 27 actions). Instrumentation was flawless — 77
    exposure events, 0 agent failures — but the **behaviour gate failed**.
18. Before blaming the model, wrote `test_actions.py` to call the platform's
    engagement actions directly, with no LLM and no tool-calling involved. **All 16
    mechanical checks pass**: like, comment, repost, follow, dislike all write their
    rows, the follow-injection join returns a followee's post, and a third agent is
    correctly refused entry to a 2-member group (D-7 works). So the action surface is
    entirely functional and the absence of engagement is a **model choice**, not a
    broken mechanism. This took seconds and removed the main competing hypothesis;
    diagnosing it by running bigger simulations would have been slow and ambiguous.
19. Diagnosed the likely cause as **F-14**, a feedback loop in the prompt:
    `env_template` places `$groups_env` *before* `$posts_env`
    (`agent_environment.py:49-53`); the group block is a wall of imperative
    instructions (`:40-48`); and `to_text_prompt()` renders it every turn
    **regardless of `available_actions`** (`:118-135`). So one agent creating a group
    puts group instructions and group messages at the top of *every* agent's prompt,
    ahead of the feed. Each new group message makes the next prompt more group-heavy
    still. `send_to_group` was in fact the single most common action.
20. Added `--no-groups` (22 actions) and launched R-6 as a controlled A/B against
    R-5 — identical in every other respect — to separate two candidate causes: the
    prompt hijack (F-14), and simple tool-count overload on an 8B model.

**Two bugs of my own, both from the same careless edit.** The `--no-groups` argparse
flag was added twice (once by a scripted replace whose success I misjudged from a
too-narrow `grep`, once by a subsequent explicit edit), producing
`argparse.ArgumentError: conflicting option string` and wasting one run. The lesson is
narrow but real: `grep` for the literal string that would appear in the file
(`--no-groups`), not the transformed one (`no_groups`), before concluding an edit
did not land.

21. R-6 came back decisively (see D-14). Removing group chat nearly doubled
    tool-calling reliability and produced the build's first real content
    engagement. F-14 confirmed.
22. Running the analysis on R-6 surfaced **B-4** in my own analyzer: agents showed
    `engagement_rate 0.0` while visibly having commented. Trace payloads turned out
    not to be uniform across action types — `create_comment` records only
    `comment_id`, `quote_post` records `quoted_id` as a *string*. Real engagement was
    being silently dropped from the exposure ledger. Fixed; with it fixed the
    propagation ledger populates as designed:
    `agent 0 saw agent 3 x3 -> create_comment x3`,
    `agent 1 saw agent 2 x5 -> quote_post`. Repeated exposure preceding
    interaction — the mechanism the whole simulation exists to observe.
23. Wrote `make_graph.py` and verified the output **in a real browser** before
    publishing, which caught **B-5** (mojibake from unicode escapes decoded by a
    non-raw Python template string, plus a `td` colour inherited rather than
    tokenised). Output is now pure ASCII. Published as an artifact.

**Where the build stands.** Stages 0, 1 and 2 are green. The engine works, the
instrumentation is complete and verified, the analysis produces the intended
micro-detail, and the graph diagram renders. What is *not* yet demonstrated is a
network with enough follow edges to make the before/after comparison substantial —
R-6 produced exactly one. That is the next question, and it is about scale and
duration rather than correctness (Q-3).

### 2026-08-24 — Stage 3: fixing what suppressed engagement

24. Addressed all four gaps identified after stage 2.

    **(a) Untested source attribution.** 100% of exposures across every run
    were `source='recsys'`, so the `following` and `both` branches had never
    executed once — untested code sitting directly under the "whose posts pop
    up where" deliverable. `test_instrumentation.py` TEST 1 builds a real
    follow edge and asserts the attribution. It passed, and `both` is now also
    confirmed **live** in R-7.

    **(b) Analyzer regression test.** TEST 2 pins the irregular trace payload
    shapes. It immediately earned its cost by finding **B-6**: `follow`
    records only `{"follow_id"}` with the followee absent entirely, so every
    follow was unattributed. Surveying all relational actions showed each uses
    a different key — `mutee_id`, `reposted_id`, `comment_id`, `followee_id`.
    All now handled.

    **(c) The follow/like problem.** Wrote `TimelineEnvironment`, changing
    prompt *content* only (D-2; Sim 1 proved *structure* changes break
    tool-calling). Four changes: feed first and groups last (F-14); name who
    you follow rather than counting them (F-11); expose `author_id` per post,
    without which `follow()` — which takes an integer — is literally
    uncallable from a feed showing only names; and replace the double-negative
    *"Do not limit your action in just `like` to like posts"* with positive
    guidance (Q-8).

    **(d) Duplicate posts.** Show each agent its own recent posts. Note the
    event log revealed this was *not* only self-repetition: three **different**
    agents had independently produced the identical "fresh cup of coffee"
    opener, i.e. cross-agent convergence on a generic phrase.

25. A 3-agent/2-round check before spending a full run produced 3 follows and
    the first `like` of the entire build. Reading the rendered prompt in that
    log then exposed **B-7**: the environment was keyed on camel's UUID rather
    than `social_agent_id`, so every follow lookup silently returned nothing
    and agents were *always* told they followed nobody. Worth noting the
    improvement happened **despite** that bug — the gains came from feed-first
    ordering, visible `author_id`, and the reworded guidance.

26. Ran R-7, the controlled comparison against R-6. Follows 1→5, likes 0→6,
    duplicates eliminated, action_rate held at 0.812. Agent 3 became a genuine
    hub, followed by agents 0, 1, 2 and 6 after three exposures each — the
    propagation mechanism this simulation was built to observe, emerging with
    nothing staged.

27. Expanded `analyze.py` with the two ledgers the micro-detail requirement
    actually needs: an **event log** (every action with actor, target and
    content) and an **exposure ledger** (every post shown to every agent, with
    feed position, source, score, and whether it was acted on or ignored).

28. Launched **R-8**, the full run: 36 agents, 12 rounds.

### 2026-08-25 — R-8, the full run, and what it exposed

29. R-8 completed cleanly: 36 agents, 12 rounds, 105 minutes, **zero agent
    failures**, 3581 exposure events, 10 distinct action types. The network
    assembled itself from zero to 55 follow edges with nothing seeded, and the
    propagation mechanism appears exactly as intended at scale —
    `agent 31 saw agent 2 x26 -> follow + create_comment`,
    `agent 1 saw agent 14 x16 -> like_post + follow + quote_post`. Agents 2
    and 14 became genuine hubs purely through repeated exposure.

30. **Follow growth plateaus.** Edges by round: 45, 45, 47, 50, 51, 53, 55.
    Comments kept climbing throughout. Agents settle their network early and
    then shift to conversation — a real dynamic, not a limitation.

31. **The headline problem: 393 malformed tool calls against 260 successful
    actions.** `follow` failed 189 times to 55 successes — a 77% failure rate,
    meaning the follow graph is roughly a quarter of what the agents actually
    attempted. Broken down, the dominant error is unambiguous:

    | Error | Count |
    |---|---|
    | `follow() got an unexpected keyword argument 'action'` | 171 |
    | `create_comment() ... 'action'` | 165 |
    | `like_post() ... 'action'` | 92 |
    | `follow() ... 'content'` | 36 |
    | `follow() ... 'follow'` | 27 |
    | `create_comment() ... 'create_comment'` | 26 |

    The model emits `follow(action="follow", followee_id=5)` — wrapping the
    call in an extra `action` parameter — or echoes the function's own name as
    a parameter. **The v1 guidance used the word "action" repeatedly and was
    priming the exact mistake it produced.**

32. Wrote prompt **v2**: drops the word "action" entirely, lists exact
    signatures with real parameter names taken from `agent_action.py`, and
    states explicitly not to wrap the call or repeat the function name. Added
    `PROMPT_VERSION`, recorded in every manifest, since runs are only
    comparable to each other at the same prompt version.

33. **v2 was deliberately NOT applied to R-9.** The contrast run had already
    launched on v1, and changing the prompt mid-comparison would confound the
    algorithm comparison with a prompt change — the same freezing discipline
    Sim 3 used for `shield_agent.py` across its 3x2 grid. R-8 vs R-9 is a
    clean TWHIN-vs-hot-score comparison at v1; measuring v2 needs its own
    TWHIN run against R-8.

### 2026-08-25 — Depth pass: the data behind the summaries

34. **Round 0 investigated after Gordon asked how anyone was connected before
    anything happened.** The answer: they were not. Round 0 has **zero**
    exposures and zero real edges. The "2 follows" reported were both **B-10**
    — two agents following hallucinated id `12345`, which upstream `follow()`
    happily inserted because it never checks the followee exists. Now rejected
    at the platform, and segregated (never silently dropped) in analysis. Real
    edge count for the v2 run corrects from 70 to **68**.

35. **`dossier.py` extended from 540 KB to 1.2 MB / 18k lines.** The gap was
    that summaries said "saw them 30x" without the 30 rows behind it. Added:
    - **Section 7B, pair chronologies** — for all 888 ordered pairs, EVERY
      exposure listed individually: round, post id, score, which route
      delivered it, a content snippet, and what the viewer did *at that exact
      moment* (including comment text). This is the "what did they do each
      time" record.
    - **Per-agent own-post ledger** — each of an agent's posts, who it was
      shown to by name, and who engaged with it and how. This answers "which
      of their posts were liked, and by whom".

36. **F-16 found while reading that ledger.** Post #3 (round 0) reached 33
    agents; post #85 (round 10) reached 1. Since score = similarity × recency
    and recency only moves 0.04 across a 12-round run, freshness was
    contributing ~15% of ranking and early posts were permanently entrenched.
    Added `recency_span_rounds`, which stretches the same curve across the run
    (age 0 → 1.00, age 7 → 0.37, age 15 → 0.00) so freshness competes with
    similarity. Stated in the manifest; `--no-recency-scaling` keeps upstream.

37. **Graph rebuilt for legibility** after feedback that lines could not be
    traced and some dots were unnamed: every node labelled, arrowheads showing
    follow direction, curved edges so reciprocal pairs separate, and
    click-to-isolate with the person's connections spelled out beneath.

38. Prompt **v3** written (not yet run at scale): feed field `author_id` →
    `followee_id`, because the model copies feed field names into calls —
    `follow(author_id=…)` failed 19x, `create_comment(comment_id=…)` 21x. Also
    asks for 2-3 actions per turn, since agents averaged only 0.70.

### 2026-08-26 — R-12, the improved full run

39. Five changes went in before this run, each from measurement rather than
    guesswork: **F-17** (feed was random-sampling its own ranked pool),
    **F-18** (persona homogeneity), **F-16** (recency scaling), **B-10**
    (phantom follow validation) and prompt **v3**. Plus an embedding cache and
    explicit seed/temperature.

40. **Results, against the two earlier full runs:**

    | run | rate | act/turn | malformed | follows | posts | exposures | min |
    |---|---|---|---|---|---|---|---|
    | v1, reddit personas, 12r | 0.461 | 0.60 | 393 | 55 | 47 | 3581 | 105 |
    | v2, reddit personas, 12r | 0.604 | 0.70 | 106 | 68 | 99 | 3940 | 86 |
    | **v4, diverse personas, 15r** | **0.733** | **0.91** | **70** | **90** | **132** | **4697** | 92 |

41. **Evidence the individual fixes landed**, not just that totals rose:
    - **0 phantom follows** (B-10), against 2 in v2.
    - The three most-seen posts now include one written in **round 6**; in v2
      all three were round-0 posts. Freshness (F-16) is displacing entrenched
      early content.
    - Round time held **flat at ~370-390s** instead of climbing 299→640s
      within the run — the embedding cache removing repeated work.
    - 30 agents, 30 distinct feeds in the final round: personalisation is
      per-person, not shared.

42. **Honest caveats.** 70 malformed calls remain. Six agents received no feed
    in the final round (they appear in earlier rounds), which is unexplained
    and worth a look. And this is one run: the project's own standard is to
    repeat before treating a number as real.

### 2026-08-26 — Multi-run artifact, and making silent failures loud

43. **The artifact accumulates runs from a baseline forward.** Previously each
    publish overwrote the last, so the history was lost and a change could not
    be traced to the run that introduced it. `make_graph.py` now discovers every
    analysed run, projects each to what the page renders, and bundles them: a
    run selector switches the graph, stats, algorithm box and all three tables,
    and a comparison table highlights the best value per metric. Future runs
    append automatically -- no flag needed.

    The baseline is **v4_full**, recorded in `data/.artifact_baseline` so it
    persists between invocations. Earlier runs are excluded deliberately: they
    used different personas, a different prompt, and a feed that discarded its
    own ranking (F-17), so sitting them beside current runs in one comparison
    table would invite false conclusions. Their databases are kept; only the
    artifact filters.

44. Pruned orphaned `_analysis.json` files whose databases had been deleted, so
    the artifact does not resurrect runs that no longer exist.

45. **B-11.** Chased down the six agents that ended R-12's final round with no
    feed. They each had 30 ranked candidates, so the ranking was fine; the
    problem was that `refresh()` wraps its entire body in a bare
    `except Exception: return {"success": False}` -- inherited from upstream's
    style -- so a failure is indistinguishable from "nothing to show". Refresh
    traces came to 476 against ~540 expected.

    Rather than guess at the cause, the failure is now *visible*: exceptions are
    logged with agent and round and counted in `refresh_errors`, while genuinely
    empty feeds (round 0 before anyone has posted, or an agent whose only
    visible posts are their own) are counted separately in `empty_feeds`. The
    next run will state which of the two it was instead of leaving it to
    inference.

46. Fixed a third mojibake instance -- a literal middle dot in a JS
    `textContent` string. Entities do not decode in `textContent`, so those
    strings must be pure ASCII. The generator now emits ASCII only, verified.

47. **Clarified a display confusion.** Handles like `user82` looked like agent
    indices, prompting a reasonable "if there are 36 personalities how do we
    have user82?". They are anonymised names carried over from the source
    persona file, which holds 111 profiles (`user0`..`user110`); diversity
    selection picks 36 of them, so the handles are scattered across that range.
    There are exactly 36 agents, `agent_id` 0-35. The per-agent table now leads
    with an explicit `#` column, node tooltips show `(agent #N)`, and the
    footnote states the distinction.

### 2026-08-26 — R-13, and three bugs it exposed

48. R-13 ran clean: 36 agents, 15 rounds, 94 minutes, zero agent failures,
    5033 exposures. **Round 0 is finally a true baseline** — 35 posts and
    nothing else, because with no exposures there was nothing to act on. The
    previous attempt invented 12 follows and 4 likes out of nothing.

49. **Headline numbers fell, and that is the point.**

    | | R-12 (v4) | R-13 (v5) |
    |---|---|---|
    | action rate | 0.733 | 0.720 |
    | follow edges | 90 | **53** |
    | exposures | 4697 | **5033** |
    | invalid follow targets | 52 | **77** |
    | blind actions rejected | n/a | **49** |

    R-12's 90 follows were **inflated**: many were guesses at ids the agent had
    never seen. R-13's 53 are every one of them informed — the agent had been
    shown that person's content first. A smaller true graph beats a larger
    false one, and the counters make the difference auditable rather than a
    matter of trust.

50. **F-20, found by reading which ids were rejected.** The invented targets
    were not random: 230 aimed at id 46, 136 at 44, 126 at 96 — all matching
    `user46`, `user44`, `user96` present in the feed. Agents were **parsing the
    digits out of the username** and passing them as ids. This was a
    self-inflicted wound from the persona switch: `millerhospitality` had no
    digits to confuse, `user46` does. Handles are now generated from each
    persona's own words — digit-free, unique, and readable
    (`@strategist_chief`, `@advanced_trading`, `@empresario_viajero`), which
    also makes the graph interpretable in a way `user46` never was.

51. **B-12, found within minutes of the run starting**, because B-11 had
    stopped swallowing exceptions the day before. A single quoted post anywhere
    in a feed raised `UnboundLocalError` and blanked that agent's *entire*
    feed. That is the root cause of the six no-feed agents in R-12 that had
    been logged as "unexplained". Fixed by a mixin that retries the batch
    post-by-post so one unrenderable post costs only itself.

    The chain is worth noting: making a silent failure loud (B-11) is what
    found the real bug (B-12), which explained an earlier mystery.

52. R-13 was deliberately **not** restarted when B-12 appeared. The bug was by
    then counted rather than invisible, so the run measures its exact cost —
    3 refresh failures — and the fix lands in the next run. Restarting a third
    time would have cost more than the measurement was worth.

53. **Complete roster added to every agent dossier.** The pair chronologies
    covered pairs that had activity; what was missing was the *whole* picture
    per agent. Each dossier entry now carries a row for **every one of the
    other 35 agents** — times seen, which of their posts specifically, what
    this agent did to them, what they did back — including the agents never
    seen at all, which are stated rather than omitted. Each ends with a
    summary line: *"Saw content from 26 of 35 other agents; never saw 9."*

    Absence is data here: an agent that never once saw another is a fact about
    what the feed did, and leaving those rows out would make the roster look
    complete while hiding the reach gaps.

    Dossier is now ~23,600 lines across 12 sections.

### 2026-08-27 — R-15: two changes, both failures

54. **Stated plainly: both changes in R-15 made things worse or did nothing.**
    v6 (R-14) remains the best configuration.

    | | R-13 | R-14 | R-15 |
    |---|---|---|---|
    | action rate | 0.720 | **0.611** | 0.487 |
    | malformed | 113 | **169** | 429 |
    | follows | 53 | **73** | 65 |
    | comments | 124 | **134** | 90 |

55. **F-22 (id glued to the name) backfired.** The theory was that the model
    reaches for a number next to the person, so putting the right number there
    would help. Instead malformed calls jumped to 429, with `follow()` handed
    `post_id` 145 times. Burying `key=value` inside a JSON *value* made the
    object harder to parse and the model grabbed the first id it saw, while
    `action=` wrapping exploded across every action type. Reverted.

56. **F-21 (notifications) did not produce conversation.** Authors replied on
    **0 of 23** threads, identical to R-14's 0 of 29. So the inability to see
    replies was *not* the reason nobody answered anybody.

    Caveat that matters: notifications shipped in the same run as F-22, so the
    two are confounded — F-22's damage may have swamped any effect. Prompt v6
    keeps notifications while reverting F-22 precisely so the next run tests
    them in isolation. Until then, "notifications don't help" is unproven, not
    established.

57. Worth recording as method: R-14's regression was predicted by nothing and
    only surfaced because malformed calls are counted. Three runs in a row now
    have had their real story told by the integrity counters rather than by the
    headline numbers.

### 2026-08-27 — Making the artifact the deliverable, and the feed social

58. **The artifact became the only thing anyone needs to open.** The detail had
    been living in a 1.6 MB `.txt` while the published page showed summaries,
    so the one artefact anyone actually reads was the one missing the data.
    Six tabs now: Network, Rounds, Transcript, People, Posts, Timeline,
    Method & integrity.

59. **Two artifacts existed with the same name**, and there is a real chance
    earlier feedback was aimed at a stale copy from 25 August rather than the
    live one. The duplicate (`96788f41…`) has been overwritten with a notice
    pointing at the live URL (`732d1879…`) so it cannot mislead again. Worth
    recording as a process failure: publishing under a second filename silently
    forked the deliverable.

60. **Round 0 showed phantom connections.** The graph draws follow edges *and*
    interaction edges; follows respected the round slider, interactions did not
    — they came from a run-total and ignored it entirely, so round 0 displayed
    every interaction that ever occurred on a network with zero edges.
    Interactions are now rebuilt from the event log filtered to the round on
    screen.

61. **Rounds tab.** One round in full: action mix, exposure count and the share
    delivered via the follow graph, every action with actor/target/full text,
    every new follow edge, and who saw whom. Two checkboxes compare a second
    round or the same round in another run, side by side.

62. **Transcript tab.** A narrated log rather than a table — for each round,
    each agent in turn, what they were shown and what they did:

    ```
    mainstream_retweeten (user_89) opened the app and was shown nothing.
    mainstream_retweeten (user_89) posted (post #4).
        Retweeten wirkt meist mehr als Liken.
    ```

    With feeds on, every exposure is listed individually with post id, author,
    delivery route, score, feed slot, and ACTED / scrolled past.

63. **Real names.** The display name is now the person's actual name from the
    persona file — *James Miller*, not `millerhospitality` and not `user_98`.
    The persona default moved back to `data/reddit/user_data_36.json`, which
    carries real names plus age, gender, MBTI, country and profession; the
    twitter CSV is more separable (0.637 vs 0.829) but anonymised to
    `user0..user110`, which made every table unreadable. **Separability was
    traded for interpretability, deliberately.**

64. **F-24, measured rather than assumed.** Posts do track their author's
    persona — 0.785 similarity to their own bio against 0.641 to everyone
    else's, a +0.14 gap — but **21 of 66 posts (32%) echo the author's own bio**,
    one of them verbatim at similarity 1.00. The gap is therefore partly
    parroting rather than the agent composing something new, and the headline
    number overstates how persona-driven the content really is.

65. **F-25: the feed became social.** Until now every agent drew candidates
    from a global pool ranked by interest × recency, so a completely
    unconnected agent saw as much as a hub — a magazine, not a social network.
    Reach now flows through the graph in three tiers: **network** (people you
    follow, deliberately *not* interest-filtered, because real friendships span
    people with nothing in common) > **friend-of-friend** (2-hop, interest
    ranked, since no relationship justifies that reach on its own) >
    **discovery** (a small global slice, and the only source an unconnected
    agent has).

    Isolation is not penalised anywhere in the code; it simply falls out.
    Verified on a 4-agent fixture: a connected agent received one post from
    each tier, while the loner received discovery only.

    Placement note: the tiers live in `refresh()` rather than
    `update_rec_table()`, because `refresh()` is the only place that knows
    *which* agent is asking and can therefore consult *their* follow graph.
    `oasis/` remains byte-identical.

### 2026-08-27 — Practice runs before scaling up

66. **P1 (6 agents, 5 rounds) caught a real problem with F-25.** Fixed tier
    sizes meant an unconnected agent got a 4-post feed against a connected
    agent's 12 — measured at **4.5 posts per feed against the old ~12** — and
    with so little to act on it never formed the connections that would grow
    the feed. A trap the simulation could not climb out of.

    There was also a methodological flaw: if isolated agents receive both
    fewer social sources *and* a smaller feed, the two are confounded and low
    engagement cannot be attributed to either.

    Fix: discovery **backfills** whatever the graph did not supply, so feed
    size is constant and only *composition* varies. A lonely agent still
    receives nothing *from other users* — their feed is entirely algorithmic,
    which is what a real platform shows someone who follows nobody.

67. **P2 (8 agents, 6 rounds) confirmed the fix.** Feed size climbs 7.0 → 11.4
    posts as connections form, exposures went 109 → 378, action rate held at
    0.833, and the network and fof tiers grow round on round while discovery
    shrinks to fill the remainder — the algorithmic-to-social shift, visible:

    | round | network | fof | discovery | posts/feed |
    |---|---|---|---|---|
    | 1 | 0 | 0 | 56 | 7.0 |
    | 3 | 7 | 1 | 69 | 9.6 |
    | 5 | 9 | 3 | 79 | 11.4 |

68. **Caught before the big run, not after:** renaming the feed sources broke
    the artifact silently. It still mapped `recsys/following/both`, so every
    exposure from a three-tier run would have rendered as `?`. Both
    vocabularies now map to one index set, so runs from either era stay
    readable side by side.

### 2026-08-27 — R-16 (v8): the social feed works, the prompt did not

69. **R-16 ran clean mechanically** — 36 agents, 15 rounds, 124 min, zero agent
    failures, zero refresh errors, **6048 exposures** (the highest of any run).
    Real names worked (*James Miller*, *Emma Hayes*), and the three-tier feed
    delivered as designed:

    | source | exposures | share |
    |---|---|---|
    | discovery | 4062 | 67% |
    | network | 1157 | 19% |
    | fof | 829 | 14% |

    **A third of all reach now flows through the social graph** rather than a
    global pool. That is the F-25 design doing its job.

70. **But behaviour degraded badly, and it was my fault.** action_rate fell to
    **0.306** and malformed calls hit **831**. Tracing the errors showed
    `action=` wrapping dominating again — the failure F-20 had fixed.

    The cause was one word. Prompt v3 opened with *"Take TWO OR THREE of these
    **actions** this turn"*, which reintroduced the priming word removed in v2.
    The plural gave it away: `follow() got an unexpected keyword argument
    'actions'`, 87 times. Malformed counts had been climbing ever since v3
    (113 → 169 → 429 → 831) and I had attributed each rise to whatever else
    that run changed. **Logged as F-26.**

71. **Two prompt changes, and the second was Gordon's call.** Removing the word
    took the smoke test to 0.58 malformed/turn. Removing the *forced volume*
    entirely — "as many or as few as you feel like, including nothing at all"
    — took it to **0.00**, against v8's 1.54/turn.

    Forcing a volume was also bad method: dictating how much agents act biases
    the very behaviour the simulation exists to measure. Action rate fell from
    0.875 (forced) to 0.708 (free), which is the honest number rather than a
    coerced one.

### 2026-08-30 — R-17: the baseline, and what it reveals

72. **Pre-flight caught that all three test gates were broken**, and the code
    was right in every case — the tests had gone stale. `test_actions` called
    engagement methods without showing the agent anything first, so F-19's
    informed-action gate rejected them; the suite was testing the gate rather
    than the actions. `test_instrumentation` still expected the pre-F-25 tier
    names and also followed before seeing. Repaired both. Broken gates are
    worse than none: they cry wolf until nobody reads them.

73. **R-17 is the reference run.** Everything correct simultaneously for the
    first time: disjoint three-tier feed, informed-action gate, real names,
    prompt v8 with no priming word and no forced volume.

    | | v7 | v8 | **baseline** |
    |---|---|---|---|
    | action rate | 0.487 | 0.306 | **0.617** |
    | malformed | 429 | 831 | **237** |
    | invalid follow targets | 23 | 26 | **0** |
    | refresh errors | 0 | 0 | **0** |
    | exposures | 4897 | 6048 | **6048** |

74. **The headline finding: unprompted agents broadcast, they do not converse.**
    256 of 403 chosen actions (64%) were `create_post`. Posts outnumber
    comments **262 to 59**, likes 29, follows 42.

    Earlier runs told agents *"engaging with other people is more interesting
    than only posting your own thoughts"* and got the opposite mix. Removing
    that line — correctly, since instructing the behaviour under study
    contaminates it — revealed the underlying disposition: **left alone, an 8B
    agent treats a social network as a broadcast channel.** Every prior
    engagement number in this project was partly an artefact of being told to
    engage.

75. **The social feed holds up under the honest prompt.** Isolation reproduces
    cleanly — connected agents (≥2 follows) draw **39.3%** of their feed
    through the graph, isolated agents **0.0%** — and the tiers are now
    disjoint after B-14. The sparser graph (42 edges vs v8's 64) is a
    consequence of agents choosing to follow less, not of the feed model.

76. **Conversation remains near-zero: 1 of 36 threads** had an author reply,
    the first non-zero count across five runs, and not enough to call a change.
    F-21b already ruled out notifications as the cause. With broadcasting now
    identified as the default disposition, the likelier explanation is that
    these agents do not model an interlocutor at all — they post *at* a feed
    rather than *to* a person. Untested.

77. **Malformed calls fell 831 → 237 but did not vanish**, and the mix is still
    led by `action=` wrapping (240). Since the word no longer appears anywhere
    in the prompt, the remaining cases are the model's own prior rather than
    something being primed — a floor rather than a bug to chase.

### 2026-08-30 — R-18: a clean negative result

78. **F-27 was refuted.** The reasoning was that agents broadcast because they
    had no way to know anything they wrote landed — 21 posts drew likes and 36
    drew comments in R-17, none of it visible to the authors. Adding a
    reception block (likes, dislikes, reply counts on your own recent posts)
    should, on that theory, have shifted behaviour toward engagement.

    It did the opposite:

    | | baseline | +feedback |
    |---|---|---|
    | posts | 256 | **302** |
    | comments | 59 | **48** |
    | post : engage | 1.82:1 | **2.24:1** |
    | author-replies | 1/36 | **0/31** |
    | action rate | 0.617 | 0.687 |

    Agents got *more* active overall but the extra activity went into posting.
    In hindsight the mechanism is obvious: telling someone their post drew
    three likes **reinforces posting**. The feedback rewarded exactly the
    behaviour it was introduced to counter.

79. **What this rules out.** Two explanations for the broadcast disposition are
    now dead: agents cannot see replies (F-21b, disproved), and agents cannot
    tell whether anything landed (F-27, disproved — and it made things worse).
    The remaining hypothesis, still untested, is that these agents do not model
    an interlocutor at all: they post *at* a feed rather than *to* a person,
    and no amount of information about the audience changes that.

80. **Everything else held.** Social feed share 28.5% → 27.9%, malformed 237 →
    276, zero agent failures, zero refresh errors, zero invalid follow targets.
    The infrastructure is stable across both runs; only the prompt differed,
    which is what makes this a clean comparison rather than a confounded one.

81. **Kept, not reverted.** The reception block stays in the prompt: it is
    realistic — every platform shows this — and the run is more informative for
    having it. What changes is the claim attached to it. It is now documented
    as a measured *negative* result rather than an improvement.

*(Entries continue as the build proceeds.)*

---

## 7. Run ledger

Every simulation run: configuration, outcome, timing. No run goes unrecorded,
including failed and aborted ones.

**DB label mapping.** Runs are stored as `data/social_timeline_<label>.db`. In
chronological order: `stage1`, `stage2`, `stage2_nogroups`, `stage3`,
`full_twhin`, `full_twhin_v2`, `v4_full`, `v5_full`, `v6_full`, `v7_full`,
`v8_full`, `baseline`, `v9_feedback`, `v10_register`, `v10_replicate`.
*Known inconsistency:* the `v4..v8_full` labels do not track `prompt_version` in
their own manifests (`v6_full` records pv=3, `v8_full` records pv=6), because the
version counter was not always bumped when the label was. **Trust the manifest's
`prompt_version`, not the label.** From `baseline` onward the two agree.

| Run | Label | Config | Outcome | Wall-clock |
|---|---|---|---|---|
| R-20 | `v10_replicate` | 36 agents, 15 rounds, prompt **v10**, temp 0.9, seed 0 — **byte-identical to R-19**; `compare.py` confirms zero config differences | **The noise-floor run (F-35).** 243 posts, 391 actions, 44 edges, 6048 exposures, 0 agent failures. Paired vs R-19 is a clean null: `create_post` +0.6 pp (p=.91), `create_comment` -0.4 pp, `like_post` -1.6 pp, `follow` +0.1 pp, nothing surviving Holm. **Pure run-to-run SD 30.7 pp for posting share vs 30.3 pp for the baseline->v10 comparison that changed two settings** — so that variance was entirely noise | 118 min |
| R-19 | `v10_register` | 36 agents, 15 rounds, prompt **v10**, **temp 0.9** (raised from 0.7) — F-28 reword of the empty-feed line | **Both pre-registered predictions failed (F-30).** 255 posts, 418 actions, 46 edges, 6048 exposures, 0 agent failures. Round-0 intro share 77%->60% is **p=0.135**; corpus similarity 0.8285->0.8175 **spans zero** at the post level. Also confounded: wording *and* temperature changed together, repeating the F-22 error | 110 min |
| R-18 | `v9_feedback` | 36 agents, 15 rounds, prompt **v9**, temp 0.7 — F-27 reception block (likes/dislikes/replies on your own recent posts) | **Made broadcasting worse, not better.** 312 posts, 447 actions, 46 edges. `create_post` share rose to 67.6%, the highest of any run. Later shown by F-31 to be indistinguishable from baseline once clustering is accounted for — the apparent regression was noise | 121 min |
| R-17 | `baseline` | 36 agents, 15 rounds, prompt **v8**, temp 0.7, seed 0 | **The reference run. Judge every future change against this one (F-31), never against the previous run.** 262 posts, 403 actions, 42 edges, 6048 exposures, 0 agent failures. Action mix `create_post` 63.5%, `create_comment` 14.6%, `follow` 10.4%, `like_post` 7.2% | 121 min |
| R-16 | `v8_full` | 36 agents, 15 rounds, prompt v6 per manifest, temp 0.7 | **Highest engagement of any run, and the least broadcast-heavy.** 57 posts but 264 actions: `create_comment` 77, `follow` 64, `create_post` 53, `like_post` 51, `like_comment` 15. **64 follow edges.** `create_post` only 20.1% of actions vs baseline's 63.5% — the mix later runs never recovered | 124 min |
| R-1 | `--` | `check_deps.py`, no simulation | **PASS (but inadequate)** — TwHIN-BERT loaded (279M params, XLMRobertaTokenizerFast + BertModel, device `cpu`), embeddings non-NaN, margin `+0.0358`, Ollama reachable with `llama3.1:8b`. The margin check passed by luck; see B-1/B-2 | 29.7s total (24.6s model load incl. download) |
| R-2 | 0 | `pooler_probe.py`, 4 texts / 2 topics, run in two fresh processes | **Exposed B-1 and B-2.** Pooler weights differ per process (`sum=-6.18` vs `+6.46`); pooler margin `+0.0069` / `+0.0008`; mean-pooled margin `+0.0475` and bit-identical across processes | ~50s for both processes |
| R-6 | 2 | 8 agents, 4 rounds, **22 actions** (`--no-groups`) — controlled A/B against R-5, identical otherwise | **Behaviour gate PASSED.** action_rate **0.812** (26/32, vs R-5's 0.469 and Sim 1's ~0.89); 14 posts, **9 comments, 3 quote_posts, 1 follow**, 1 search, 1 do_nothing; 148 exposures (nearly 2x R-5). First genuine content engagement of the build. Confirms F-14 | 340.1s |
| R-11 | contrast | 36 agents, 12 rounds, **reddit hot-score**, prompt **v2** | **Completed.** action_rate **0.956**, only **7** malformed calls, 413 actions, **113 follows**, 106 posts, 2976 exposures. Verified: **1 distinct candidate pool** (all 36 agents see an identical feed) and 100% `recsys` source (no follow-injection) | 77 min |
| R-15 | full | 36 agents, 15 rounds, prompt **v5** (id glued to name + notifications) | **WORSE. Both changes failed.** action_rate **0.487** (from 0.611), malformed **429** (from 169), comments 134→90, follows 73→65. And notifications did **not** produce conversation: **0 of 23** threads had the author reply back, identical to v6's 0 of 29 | 109 min |
| R-14 | full | 36 agents, 15 rounds, prompt v4, **readable handles** | **Best run so far.** invalid_follow_targets **77→17** and follows **53→73**, both exactly as F-20 predicted; refresh_errors **3→0** (B-12 holds). But action_rate fell 0.72→0.611 and malformed rose 113→169 — an unpredicted regression, diagnosed as F-22 | 97 min |
| R-13 | full | 36 diverse personas, 15 rounds, prompt v3, **informed-action gate** | **Clean but sparse.** 94 min, 0 agent failures, 5033 exposures, 130 posts, 124 comments, 125 likes. **Round 0 finally correct: 35 posts, 0 follows, 0 likes, 0 comments** — nothing to act on, so nothing acted on. But only **53 follows**, because the gate rejected 77 invalid targets and 49 blind actions. Exposed **F-20** and **B-12** | 94 min |
| R-12 | full | 36 **diversity-selected twitter** personas, 15 rounds, prompt v3, recency scaling, ranked feed, seed 0 / temp 0.7 | **Best run to date.** action_rate **0.733**, actions/turn **0.91**, malformed **70**, **90 follow edges**, 132 posts, 148 comments, 100 likes, 4697 exposures, 7 action types, **0 phantom follows**, 0 agent failures. Round time held ~370-390s **flat** (was 299->640s climbing) thanks to the embedding cache | 92 min |
| R-10 | full | 36 agents, 12 rounds, twhin-bert, prompt **v2** | **Completed.** action_rate 0.604 (vs 0.461 at v1), malformed calls **393 → 106 (-73%)**, 302 actions, 70 follows, 99 posts, 3940 exposures. Sources: recsys 3073 / following 772 / both 95 — **22% of exposures arrived via the social graph**. 36 distinct candidate pools (fully personalized) | 86 min |
| R-9 | contrast | 36 agents, 12 rounds, reddit, prompt v1 | **KILLED and data deleted** — B-8 meant `--recsys reddit` was silently running TWHIN, so it was comparing TWHIN to itself | — |
| R-8 | full | 36 agents, 12 rounds, twhin-bert, 22 actions, prompt **v1** | **Completed, 0 agent failures.** 47 posts, 89 comments, 55 follows, 42 likes, 1 dislike, 3581 exposures, 10 distinct action types. action_rate 0.461. **But 393 malformed tool calls vs 260 successful actions** — see F-15 | 6277.6s (105 min) |
| R-7 | 3 | 8 agents, 4 rounds, 22 actions, **all four fixes**, `--label stage3` | **Dynamics gate PASSED.** action_rate 0.812; **5 follow edges** (vs 1), **6 likes** (vs 0 in every prior run), 8 comments, 8/8 distinct posts (no duplicates); `source='both'` appears **live** and grows 4→5 as the graph grows; 0 agent failures | 312.7s |
| R-5 | 2 | 8 agents, 4 rounds, 27 actions, `--label stage2` | **Behaviour gate FAILED.** 0 agent failures, instrumentation clean (77 exposures), but **action_rate 0.469** (15/32 turns) vs Sim 1's ~0.89 baseline, and the action mix was `send_to_group` 6, `create_post` 6, `create_group` 2, `join_group` 1 — **zero likes, follows, comments or reposts**. Diagnosed as F-14 | 352.7s |
| R-4 | 1 | 4 agents, 2 rounds, twhin-bert, `--label stage1` | **Plumbing gate PASSED.** 0 agent failures; `rec_history`=12, `rec_candidates`=12, `round_boundary` correct (r0: 0 posts, r1: 4); every agent received a non-empty feed; own-posts correctly excluded; per-user scores genuinely differ. Exposed **B-3**. Action diversity was nil — see analysis below | 103.2s |
| R-3 | 0 | `check_deps.py`, strengthened to 6 checks | **PASS, and now a real gate.** Mean-pooled margin `+0.0475`; embedding space reproduced a baseline recorded in a *different* process to within `dw=0.00004, da=0.00002`, confirming replication is sound under D-13; pooler regression guard confirms upstream still unfixed | 4.7s (model cached) |

---

| R-21 | 0 | `v10_rep3` — 36 agents, 15 rounds, prompt v10, temp 0.9, `--no-groups`. Overnight replicate batch, launched to give six runs at one identical configuration | **PASS.** 116 min, 0 agent failures. 208 posts, 56 comments, 41 follows, 34 likes, 6048 exposures. Analysis initially failed (the batch script called `analyze.py` without its required `--db` flag); the run data was unaffected and all four were analysed by a separate watcher |
| R-22 | 0 | `v10_rep4` — 36 agents, 15 rounds, prompt v10, temp 0.9, `--no-groups`. Overnight replicate batch, launched to give six runs at one identical configuration | **PASS.** 115 min, 0 agent failures. 243 posts, 56 comments, 44 follows, 46 likes, 6048 exposures. Analysis initially failed (the batch script called `analyze.py` without its required `--db` flag); the run data was unaffected and all four were analysed by a separate watcher |
| R-23 | 0 | `v10_rep5` — 36 agents, 15 rounds, prompt v10, temp 0.9, `--no-groups`. Overnight replicate batch, launched to give six runs at one identical configuration | **PASS.** 120 min, 0 agent failures. 215 posts, 49 comments, 49 follows, 42 likes, 6048 exposures. Analysis initially failed (the batch script called `analyze.py` without its required `--db` flag); the run data was unaffected and all four were analysed by a separate watcher |
| R-24 | 0 | `v10_rep6` — 36 agents, 15 rounds, prompt v10, temp 0.9, `--no-groups`. Overnight replicate batch, launched to give six runs at one identical configuration | **PASS.** 117 min, 0 agent failures. 243 posts, 64 comments, 47 follows, 40 likes, 6048 exposures. Analysis initially failed (the batch script called `analyze.py` without its required `--db` flag); the run data was unaffected and all four were analysed by a separate watcher |

---

## 8. Bug ledger

Bugs found during this build — in our code or upstream — with how each surfaced.

#### B-8

**Where.** Ours, `timeline_platform.update_rec_table`

**Symptom.** `--recsys reddit` produced results indistinguishable from `--recsys
twhin-bert` — because it *was* TWHIN. The intended hot-score-vs-interest comparison was
silently TWHIN against itself

**Cause.** The override reimplemented ranking but never branched on `self.recsys_type`,
so the flag was accepted and ignored

**Fix.** Branch on `recsys_type` (now `timeline_platform.py:330` and `:489`). **R-9 was
killed and its data deleted** rather than reported

**Found by.** Noticing two "different" algorithms gave identical candidate pools

#### B-9

**Where.** Upstream `oasis/environment/env.py:197-198`

**Symptom.** `created_at` stayed `0` for every post in non-Twitter runs, so recency
ranking had no signal and round boundaries could not be recovered from the clock

**Cause.** `self.platform.sandbox_clock.time_step += 1` is guarded by `if
self.platform_type == DefaultPlatformType.TWITTER`, so the clock never advances on any
other platform type

**Fix.** Do not depend on the sandbox clock. `round_boundary` is written directly by our
own instrumentation, and `created_at` is stamped from the round number we control

**Found by.** Round-0 posts and round-14 posts carrying the same timestamp

#### B-1

**Where.** Upstream `process_recsys_posts.py:33`

**Symptom.** Embedding space differs on every process launch; runs not reproducible

**Cause.** `outputs.pooler_output` reads a pooler whose weights TwHIN-BERT's checkpoint
does not contain, so they are randomly re-initialized at every load

**Fix.** Mean-pool `last_hidden_state` instead (D-13)

**Found by.** Stage 0 probe, cross-process fingerprint

#### B-2

**Where.** Same line

**Symptom.** Interest-based ranking is barely discriminative — one process produced a
within-vs-across-topic margin of `+0.0008`, i.e. noise

**Cause.** `tanh` saturation on a random projection compresses all cosines into
~0.88-0.97

**Fix.** Same fix (D-13)

**Found by.** Stage 0 probe, 2-topic margin test

#### B-4

**Where.** Ours — `analyze.py`

**Symptom.** Agents showed `engagement_rate 0.0` and `acted on: []` despite having
posted real comments — genuine engagement silently missing from the ledger

**Cause.** Trace `info` payloads are **not uniform**: `create_comment` records only
`comment_id` (no `post_id`), and `quote_post` records `quoted_id` as a **string**, which
an `isinstance(..., int)` check rejects

**Fix.** Numeric-string coercion + a `comment_id -> post_id` lookup via the comment
table

**Found by.** R-6 analysis: comment counts and "acted on" disagreed

#### B-5

**Where.** Ours — `make_graph.py`

**Symptom.** Usernames rendered as `millerhospitaliâ€¦`; table text illegibly
low-contrast

**Cause.** The HTML template is a **non-raw** Python string, so `\\u2013`-style escapes
were decoded into literal non-ASCII before ever reaching the file, and mojibake appeared
wherever charset was not guaranteed. Separately, `td` inherited its colour through the
table instead of taking a token

**Fix.** Emit pure ASCII (HTML entities); set `td { color: var(--fg) }` explicitly

**Found by.** Browser verification before publishing

#### B-6

**Where.** Upstream `platform.py:905` + our `analyze.py`

**Symptom.** Every `follow` was unattributed — the interaction ledger could not say who
was followed

**Cause.** `follow` records only `{"follow_id": ...}`; the followee appears **nowhere**
in the payload. Surveyed all relational actions and found each uses a different key:
`unfollow`→`followee_id`, `mute`→`mutee_id`, `repost`→`reposted_id`, comment
actions→`comment_id` only

**Fix.** Recover followee via the follow table; add the other keys; generalise the
comment lookup

**Found by.** `test_instrumentation.py` TEST 2

#### B-7

**Where.** Ours — `timeline_agent.py`

**Symptom.** Agents were *always* told "you do not follow anyone yet", even holding
follow edges; authors rendered as bare `agentN`

**Cause.** Keyed on `self.agent_id`, which is **camel's UUID**; the integer is
`social_agent_id` (`agent.py:71`). Every lookup silently matched nothing. Separately,
`sign_up` leaves `user_name` NULL and puts the handle in `name`

**Fix.** Use `social_agent_id`; `COALESCE(user_name, name)`

**Found by.** Reading the rendered prompt in the promptcheck run

#### B-12

**Where.** Upstream `platform_utils.py:85-157`

**Symptom.** **A single quoted post anywhere in a feed blanks that agent's entire
feed.** This is the root cause behind B-11's symptom

**Cause.** `_add_comments_to_posts` assigns `num_reports` in the `repost` and `common`
branches but **not** in the `quote` branch, then reads it unconditionally at `:157` →
`UnboundLocalError`, which upstream's bare `except` swallowed

**Fix.** `_ResilientPlatformUtils` mixin: on failure, retry the batch post-by-post so
one unrenderable post costs only itself; unrenderable posts are still rendered from the
row already held, since dropping them would bias recorded exposure

**Found by.** The B-11 logging, within minutes of the v5 run starting

#### B-11

**Where.** Ours + upstream pattern — `refresh()`

**Symptom.** Six agents ended round 14 of R-12 with no feed despite having 30 ranked
candidates waiting, and nothing anywhere said why

**Cause.** `refresh()` wrapped its whole body in `except Exception: return {"success":
False}`, so any failure produced a missing feed with **no signal at all**. Refresh
traces totalled 476 against ~540 expected

**Fix.** Log the exception and count it; count legitimate empty feeds (round 0,
own-posts-only) separately so the two cannot be confused

**Found by.** Investigating the six missing feeds

#### B-10

**Where.** Upstream `platform.py:868-890`

**Symptom.** Agents "followed" people who do not exist; round 0 appeared to start with 2
connections when the network was genuinely empty

**Cause.** `follow()` checks for a duplicate edge but **never that the followee exists**
— it inserts whatever integer it is handed. Two agents both followed hallucinated id
`12345`

**Fix.** Validate the target in `TimelinePlatform.follow/unfollow/mute`; `analyze.py`
segregates phantom edges instead of counting them

**Found by.** Gordon asking how anyone was connected at round 0

#### B-3

**Where.** Ours — `run_simulation.py`

**Symptom.** `final_counts` all `None`, `action_tally` returned `Cannot operate on a
closed cursor`

**Cause.** Both were computed *after* `env.close()`, which closes the DB cursor
(`platform.py:143-144` on `ActionType.EXIT`)

**Fix.** Read them inside the `try`, before `close()`

**Found by.** R-4 (stage 1)


### B-1 / B-2 in detail

**Symptom.** Loading `Twitter/twhin-bert-base` emits:

```
Some weights of BertModel were not initialized from the model checkpoint at
Twitter/twhin-bert-base and are newly initialized:
['pooler.dense.bias', 'pooler.dense.weight']
```

`process_batch` then returns `outputs.pooler_output` — that is,
`tanh(W · CLS + b)` where `W` and `b` are **random and untrained**. The entire
interest-based recommendation therefore ranks content through a random projection.

**Evidence.** Same four texts (two travel, two systems-programming), two fresh
processes:

| Method | P1 margin | P2 margin | Cross-process identical? |
|---|---|---|---|
| `pooler_output` (what OASIS uses) | `+0.0069` | `+0.0008` | **No** |
| `mean_pooled` | `+0.0475` | `+0.0475` | **Yes** |
| `cls_raw` | `+0.0041` | `+0.0041` | **Yes** |

Pooler weight fingerprint: `sum=-6.175595` (P1) vs `sum=+6.457529` (P2).
That `mean_pooled` and `cls_raw` are bit-identical across processes proves the base
model is deterministic and isolates the random pooler as the sole cause of B-1.

**Why this matters more than it looks.** Replication is the central methodological
habit of this project — Sim 2 was run twice specifically to separate signal from
single-run noise, and Sim 3 ran the `down` condition four times. With B-1 present,
two runs of an identical configuration would be executing against *different embedding
spaces*, so run-to-run variation would silently conflate genuine stochasticity with a
random projection changing underneath the experiment. Replication would be structurally
meaningless. B-2 compounds it: in process 2 the algorithm had essentially no
discriminative power at all.

This is the same fail-open failure class as F-3 and as Sim 3's shield: degraded
silently, produced plausible-looking numbers, raised nothing.

**Lesson about the test itself.** The original `check_deps.py` discrimination check
**passed** at `+0.0358` and was wrong to. It used three texts and a single process, so
one lucky random draw looked healthy. Exposing the bug required two topics, four
texts, and two processes. `check_deps.py` has been strengthened accordingly (§5) —
a check that can pass by luck is not a gate.

---

## 9. Open questions

**Still genuinely open (as of 2026-08-31) — the rest of this table is answered
history, kept for the record.**

#### Q-10 — Is F-38's anti-predictive similarity actually a recency effect?


**Status.** **Answered — and F-38 is retracted.** Not a confound but a mislabelled
variable: F-38 modelled `sim * recency`, not cosine. Cosine alone is null (OR 1.544,
p=0.38); the negative coefficient was recency, and recency in turn is repeat exposure.
See F-42, F-43

#### Q-15 — Does repeat exposure (F-43) survive a designed test?

**Question.** Prior sightings are an outcome of the ranker, not randomised, so the
current estimate is observational. A run that deliberately re-injects a fixed set of
posts at controlled intervals would settle it


**Status.** **Open.** The most valuable single run this setup could still do: the effect
is large (OR 2.3) so it needs far less power than the prompt interventions that failed
in F-35

#### Q-11

**Question.** Why do some available actions never fire? `test_actions.py` proves they
work mechanically, so it is a model choice — but an unexplained one

**Status.** **Open, but the question was mis-stated and is corrected by F-48.** It used
to read "14 of the 21 available actions never fire. No `dislike`, `unfollow`, `mute`,
`report`, `search` or `trend` in any run." That was measured on `baseline` alone and
generalised. The action set is **22**, not 21, and across the nine analysed runs **14
fire and 8 do not**. `dislike_post`, `unfollow`, `report_post`, `search_user` and
`search_posts` all occur — rarely, but they occur.

The surviving question is narrower and sharper: the eight that never fire are `mute`,
`unmute`, `trend`, `dislike_comment`, `unlike_post`, `unlike_comment`,
`undo_dislike_post`, `undo_dislike_comment` — every one a mute, a trend lookup, or an
**undo**. *Agents never reverse an action they have taken.* That is a far more specific
behavioural claim than "two thirds of the buttons are unused", and it is the one worth
explaining

#### Q-12

**Question.** F-24: ~32% of posts echo the author's own bio. Is that persona-anchoring,
or the 8B model's limited generation?

**Status.** **Open.** Per F-35, do **not** attack this with prompt tweaks at n=36 — the
noise floor makes it unmeasurable

#### Q-13

**Question.** Does the `fof` effect (F-37) survive a properly powered test? It is
significant pooled but in only 1 of 4 runs individually

**Status.** **Open.** Would need either more runs or the F-36 follow-targeted design

#### Q-14 — Is the F-35 noise floor itself stable?

**Question.** It rested on a single replicate pair, though it landed within
0.4 pp of an independent estimate.

**Status.** **Answered — it stands.** Six runs at one identical configuration
give all 15 pairs. Mean paired SD: `create_post` **28.2%** (range 24.7-33.1),
`create_comment` 18.5% (16.2-22.0), `like_post` 15.5% (13.1-18.8), `follow`
9.6% (8.0-11.4). Every figure from the original single pair (30.5 / 18.4 / 14.4
/ 10.7) falls **inside** the spread of all fifteen, so F-35 was a fair draw and
the conclusion built on it holds. `noise_floor.py`,
`data/social_timeline_noise_floor_6runs.txt`

#### Q-1

**Question.** Does TwHIN-BERT download and embed acceptably on CPU?

**Status.** **Answered.** Yes — 279M params, loads in ~25s, embeds 4 texts in ~0.1s. But
only usable with the D-13 mean-pooling fix; as shipped it is non-deterministic and
near-non-discriminative (B-1/B-2)

#### Q-6

**Question.** How much does the D-13 mean-pooling deviation change results vs.
upstream-exact?

**Status.** Measurable via the comparison flag once the engine runs

#### Q-9

**Question.** Can the malformed-call rate (F-15) be reduced by stating each action's
exact signature in the guidance rather than a prose list? 10 lost follows in 5 rounds is
a material undercount of intent

**Status.** Open — prompt-content change, testable as an A/B

#### Q-8

**Question.** Why do agents post but rarely like or follow? Note the prompt's closing
line reads "Do not limit your action in just `like` to like posts"
(`agent_environment.py:51-53`) — awkward enough that an 8B model may read it as an
instruction *against* liking

**Status.** Open; testable by rewording prompt content only, which D-2 permits

#### Q-7

**Question.** Is a `+0.0475` within-vs-across margin enough dynamic range for
personalization to visibly shape feeds, once multiplied by recency decay?

**Status.** Stage 3 — recency may dominate content similarity

#### Q-2

**Question.** Does the 27-action set degrade 8B tool-calling vs. Sim 1's ~32/36
baseline?

**Status.** **Answered: yes, badly.** 0.469 with 27 actions vs 0.812 with 22. Cause was
not tool count alone but the group-chat prompt hijack (F-14). Resolved by D-14

#### Q-3

**Question.** Do agents actually form follows, given they see only counts and never
identities (F-11)?

**Status.** **Partially.** Exactly 1 follow in 32 agent-turns (R-6) — non-zero, so it is
possible, but far too sparse for a meaningful before/after graph. The likeliest cause is
F-11: agents are told only *how many* people they follow, never *who*, so a follow
target must be inferred from author ids in the feed. Open, and now the build's main
question

#### Q-4

**Question.** Do 2-member groups (de-facto DMs) emerge at all (D-7)?

**Status.** **Yes, but at a cost.** R-5 produced 2 groups, 3 members and 6 group
messages unprompted — so they do emerge. But the same actions suppress feed engagement
(F-14/D-14), so studying DMs and studying timelines are in direct tension on an 8B
model. Reported, not engineered around

#### Q-5

**Question.** Does F-12's index-base conflict affect TWHIN, leaving any agent with an
empty feed?

**Status.** **Answered: no.** Every agent received a non-empty feed in R-4 and R-6.
Avoided by keying on `agent_id` explicitly (F-13) rather than reproducing upstream's
positional indexing

---

# Part II — making it run

*Originally `SIM4_LOG.md` Part II.*

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

### F-68 — Validated at 36 agents: terse tools are the only lever that works. 1.35x

**Finding.** Four configurations, 36 agents x 3 rounds each, uncapped tokens, run
back to back on an idle machine:

| Config | s/round | vs upstream | Engagement |
|---|---|---|---|
| Upstream: full docstrings, persona in system, NP=8 | 453.4 | 1.00x | 5.93 % |
| **Terse tool descriptions**, NP=8 | **335.4** | **1.35x** | **6.55 %** |
| Terse + persona hoisted, NP=8 | 330.9 | 1.37x | 5.91 % |
| Terse + hoisted, **sequential** (NP=1, sem 1) | 381.7 | 1.19x | 5.44 % |

**Terse descriptions are worth 1.35x and engagement does not suffer — it rises,
6.55 % against 5.93 %.** That is the only change in this entire campaign that makes
the simulation faster without costing anything, and it is now the default.

**Persona hoisting (F-66) is worth ~1 % and is retracted as a speedup.** The bench
predicted 2.5-5x. It is kept only because it is harmless and makes the prompt
cache *available* should the execution model ever change.

**Sequential execution is 15 % SLOWER than 8-way concurrency**, not faster. The
mid-run reading that suggested otherwise was taken at round 2, and early rounds are
cheap because the world has barely any posts in it — comparing a partial early
measurement against a full-run average is not a comparison.

### F-69 — Prefix caching does not survive concurrency, which is why F-66 failed

**Finding.** Ollama's prompt cache is per-slot and only helps when requests arrive
one at a time:

| | Prefill on an identical shared prefix |
|---|---|
| Sequential | **0.07 s** |
| 8 concurrent | **24.9 s** |

A 350x difference. Under continuous batching the slots are reset and every request
pays full prefill, so arranging for a shared prefix (F-66) buys nothing at
`NUM_PARALLEL=8`. The two optimisations are mutually exclusive: **either batch and
pay prefill every time, or serialise and pay it once.** Measured end to end,
batching wins (330.9 s/round against 381.7), so the cache stays unused.

This is worth stating because it looks like free money and is not. It would become
free money on a serving stack with cross-request prefix sharing — vLLM's automatic
prefix caching does exactly this — which is another reason the eventual answer for
scale is a different serving stack, not a different setting.

### F-70 — Four of five optimisation hypotheses this campaign died on contact with the real workload

**Recorded because the pattern is now the most reliable finding here.**

| Hypothesis | Bench predicted | Measured at 36 agents | Outcome |
|---|---|---|---|
| Server concurrency (F-51/F-53) | 1.9-3.1x | +0.6 % | retracted (F-60) |
| `max_tokens` cap | 1.48x | 1.48x but **engagement 0 %** | retracted (F-63) |
| 3b model | 4.7x | **engagement 0 %** | unusable |
| Persona hoisting (F-66) | 2.5-5x | ~1 % | retracted (F-68) |
| **Terse tool descriptions** | 1.54x | **1.35x** | **held** |

The one that survived is the one whose bench estimate was closest to modest. Every
bench run in this project has an idle GPU, a warm cache, or a small queue, and a
36-agent round has none of those. **Nothing should be believed here until it has run
at 36 agents with the engagement gate on it.**

### F-66 — Prefill is 78 % of a turn and it is re-computed for every agent. Prompt ORDER is the fix

**Finding.** The single largest inefficiency in the simulation is not the model, the
concurrency, or the code. It is that **every agent re-processes the same ~2,000 tokens
of shared prompt from scratch, 540 times per run.**

Measured raw rates on this machine, single stream, unique prompts:

| | Rate | Bound by |
|---|---|---|
| Prefill (reading the prompt) | ~490 tok/s | compute |
| Decode (writing the reply) | ~54 tok/s | memory bandwidth |

A turn is ~2,675 prompt tokens and ~60-100 generated, so **prefill is ~5.5 s and decode
~1.5 s — prefill is 78 % of the work.** Every earlier claim in this log that decode
dominates was measured on repeated identical prompts, where prefill is served from
cache and costs nothing.

**Ollama does cache prompt prefixes, and the simulation defeats it.** A shared prefix
followed by a varying suffix reprocesses at **20,000 tok/s instead of 490** — a 40x
difference, effectively free. But the prompt is laid out as

    [ system: OBJECTIVE + THIS AGENT'S PERSONA ] [ tools ] [ user: feed ]

and the persona is at the **front**, so no two of the 36 agents share a prefix and the
cache never hits. Moving the persona behind the shared block:

| Layout | agent 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Persona in system (current) | 5.47 s | 6.78 s | 6.78 s | 6.92 s |
| Persona in the user turn | 6.92 s | **1.27 s** | **1.17 s** | **1.20 s** |

**5.7x faster after the first agent**, 2.46x even across only four. Over a full run the
cold cost is paid once per parallel slot and then never again, so essentially every
turn hits.

**Nothing is removed and nothing is constrained.** The agent is told exactly the same
things about itself; the words sit in a different message. That distinguishes this
from every other lever tried: `--lean-actions` removes actions, `--max-tokens` caps
output and destroys engagement, the 3b model cannot tool-call. This only reorders.

**It is still a prompt change**, so per F-35 it must be judged against baseline rather
than assumed harmless — models do weight system and user content differently.

### F-67 — The hardware is not being wasted; the work is being repeated

**Finding.** Recorded to close off a whole family of "buy a better setup" answers.

| | Theoretical | Measured | Utilisation |
|---|---|---|---|
| Decode, 8B Q4 | 81 tok/s (400 GB/s ÷ 4.92 GB) | 54 tok/s | 66 % |
| Prefill | ~800 tok/s | ~490 tok/s | ~60 % |
| GPU busy during a run | — | **100 %** | — |

The M2 Max is delivering roughly two thirds of its theoretical ceiling and is busy
100 % of wall clock during a run (measured across 236 requests). **There is no idle
capacity to reclaim and no configuration that makes the chip faster.** Every remaining
win must come from doing *less work*, which is why F-64 (shorter prompts) and F-66
(cache-friendly ordering) are the only levers that have worked.

### F-64 — The prompt is 80 % tool docstrings, and shortening them is the one real speedup

**Finding.** Every turn ships the full Python docstring of all 22 actions as tool
descriptions. Measured directly:

| | Tokens |
|---|---|
| 22 tool docstrings | **~3,759** |
| persona + 12-post feed + instructions | ~1,000 |
| **total prompt** | **~4,761** |

**Eighty percent of every prompt is API documentation the model does not need.**
`search_user` alone is ~302 tokens, `refresh` ~289, `search_posts` ~273 — and
`refresh` is not even a model choice (it is our own prompt-building, see the
campaign notes).

Replacing each description with its **first line only** — same 22 tools, same
signatures, same action surface, nothing removed:

| | Wall | Prompt | Tool calls |
|---|---|---|---|
| Full docstrings | 5.10 s | 4,761 tok | 0 / 5 |
| First line only | **3.53 s** | **1,320 tok** | **2 / 5** |

**1.44x faster, 72 % fewer prompt tokens, and tool calling got *better*, not worse.**
That last part is the opposite of the usual efficiency trade and is mechanically
sensible: less irrelevant text between the feed and the instruction.

This is the only lever tested in this whole campaign that speeds the simulation up
without changing what the agents can do. Unlike `--lean-actions` it removes no
action, and unlike `--max-tokens` it constrains no output.

### F-65 — Raising NUM_PARALLEL silently truncated every prompt, and I caused it

**Finding.** Ollama divides its context across parallel slots. At
`OLLAMA_NUM_PARALLEL=1` each sequence gets the whole 32,768 tokens. At
`NUM_PARALLEL=8` each gets **4,096** — and the real prompt is **4,761**.

Demonstrated by holding everything else fixed and growing the feed:

| Feed | ctx 4096/slot | ctx 8192/slot |
|---|---|---|
| 12 posts | prompt **4,096** | prompt 4,712 |
| 30 posts | prompt **4,096** | prompt 5,270 |
| 60 posts | prompt **4,096** | — |

Pinned at exactly 4,096 regardless of input: the prompt was being **cut**, and
`prompt_tokens` reports the truncated length without complaint.

**This is my doing.** F-53 recommended `OLLAMA_NUM_PARALLEL=8` on the strength of a
throughput benchmark, and nothing in that benchmark used a prompt near the context
limit. The 24 historical runs at `NUM_PARALLEL=1` were *not* truncated. Every run
from last night's campaign was.

**Two consequences.** Anyone raising `NUM_PARALLEL` must raise
`OLLAMA_CONTEXT_LENGTH` with it — 8192 at NP=8 costs ~7 GiB of KV against 21.3 GiB
available. And F-64's shorter descriptions fix this for free by putting the prompt
back under 1,400 tokens, where truncation cannot occur at any sensible slot count.

#### F-65a — CORRECTS F-65's mechanism. Ollama 0.24 does NOT divide context across slots

F-65 says *"Ollama divides its context across parallel slots. At
`OLLAMA_NUM_PARALLEL=1` each sequence gets the whole 32,768. At
`NUM_PARALLEL=8` each gets 4,096."* That was true of the version measured then.
**It is not true of 0.24.0**, which is what this project runs now.

Measured directly against the running server:

    NUM_PARALLEL=4, CONTEXT_LENGTH unset    ->  /api/ps reports  4,096
    NUM_PARALLEL=4, CONTEXT_LENGTH=32768    ->  /api/ps reports 32,768
    NUM_PARALLEL=4, CONTEXT_LENGTH=8192     ->  /api/ps reports  8,192

**`OLLAMA_CONTEXT_LENGTH` is the PER-SLOT window and is not divided by the slot
count.** The 4,096 in the first row is 0.24's default, not 16,384 split four ways.

**Why the distinction matters.** Under F-65's model you could leave
`CONTEXT_LENGTH` alone and infer the per-slot window from the slot count. Under
the real behaviour the default is small and fixed, so **raising `NUM_PARALLEL`
does not shrink the window -- the window was already too small and nothing
announced it.** B-28 is what that looks like in practice.

**F-65's warning survives intact** and is if anything stronger: set
`OLLAMA_CONTEXT_LENGTH` explicitly, every time, and verify it. Only its
arithmetic falls.

**Now enforced in code.** `server_state.py` reads `/api/ps` for the real
per-slot figure; `check_deps.py` fails a run below 8,192; `run_simulation.py`
refuses to start and writes `server_context_length` into every manifest. Eight
unit tests, including one pinning the URL handling that broke on first attempt.

### F-62 — Cost is exactly linear in agent count, and the sim cannot exceed 36 agents

**Finding.** Nothing in this project had ever measured cost against agent count —
all 24 runs were 36 agents. Held at 3 rounds, one config, one at a time:

| Agents | Time | Per agent |
|---|---|---|
| 12 | 83.0 s | **6.92 s** |
| 24 | 166.5 s | **6.94 s** |
| 36 | 250.1 s | **6.95 s** |

**Linear to three significant figures.** There is no hidden quadratic in the code
path — which is the outcome that matters, because F-57 found exactly such a term
in the ranking loop and this confirms nothing comparable survives elsewhere. Double
the agents, double the cost; nothing worse.

**And a hard ceiling nobody had hit.** `--agents 72` silently produced a **36-agent
run**. `data/reddit/user_data_36.json` holds 36 personas and `select_diverse()`
returns what it has, without complaint. The 72-agent data point was invalid and is
discarded; the real finding is that **the simulation cannot currently run more than
36 agents at all.** Bigger worlds are blocked on persona supply, not on speed —
which reverses the assumption behind every scaling estimate in this log.

### F-63 — RETRACTS the `max_tokens` speedup. It was agents ceasing to engage

**Finding.** Capping generated tokens looked like the cheapest real win of the
campaign: 1,220 s to 823 s, a **1.48x** speedup on an otherwise identical config.
It is not a speedup. It is the agents no longer doing the thing the study measures.

8b, 36 agents x 3 rounds, everything else held:

| Config | Time | Engagement with shown posts |
|---|---|---|
| 22 actions, uncapped | 1,220 s | **4.31 %** |
| 14 actions, uncapped | 967 s | **3.87 %** |
| 14 actions, **capped 512** | 641 s | **0.00 %** |
| 3b + 14 actions + capped | 258 s | **0.00 %** |

The cap is causal and total: holding the action set fixed at 14, uncapped gives
3.87 % engagement and capped gives **zero**. Agents still post — 59 posts, a full
12-slot feed, 1.26 actions per turn — they simply never react to anything they are
shown. Across the seven full replicates the campaign then spent on that config:
**1 engagement in 42,336 exposures.**

**`--max-tokens` must never be set below the default.** The flag is kept only so the
manifest records that it was not used.

**Lean actions are separately suspect.** 4.31 % to 3.87 % is within one pair at
F-35's noise, so it is not established — but it is the wrong direction, and the
1.26x it buys is not worth a behavioural risk that would need replicates to clear.

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

### F-71 — Tool-call rate does not predict whether a model is usable. Feed engagement does

`llama3.2:3b` is 4.7x faster than `llama3.1:8b` and produced ONE engagement in
42,336 exposures. Discovering that cost seven full runs. `eval_model.py` now
reproduces the failure in about 80 seconds, but only after the first version of
it failed:

    n=6, first metrics          tool rate   grounded   variety
      llama3.1:8b                    100%       100%         4
      llama3.2:3b                    100%       100%         4

Identical. A filter that passes the model it exists to catch is not a filter.
The action mix is where the two separate:

      llama3.1:8b    like_post x3, follow x3, search_posts x1, create_post x1
      llama3.2:3b    search_posts x3, create_post x3, create_comment x1

The 3b model never touches what it was shown. It is busy — it posts, it
searches — and every one of those actions is invisible to `seen_and_acted`,
which `analyze.py:270-295` defines as an action carrying a `post_id` the agent
was actually exposed to. Note this excludes `follow`, which carries no post_id.

Rebuilt around that definition, at n=25:

    metric        llama3.1:8b   llama3.2:3b
      tool rate          100%           88%     <- nearly useless as a gate
      ENGAGED             64%           24%     <- the discriminator
      grounded           100%           78%
      tok/s               11.5          38.0

**The lesson is more general than model choice.** Every cheap proxy in this
project has measured activity when the thing that matters is engagement: B-23
gated a campaign on activity and waved through the config with 1 engagement in
42,336; F-63's `max_tokens=512` collapse looked healthy on every count except
engagement; this harness reinvented the same error in its first draft. The
proxy has to be the metric the run is scored on, or it is not a proxy.

Caveat, and it is not a small one: the proxy COMPRESSES the gap. 64% vs 24% is
2.7x where reality was ~500x. Eight to twenty-five fresh single turns cannot
reproduce a deficit that compounds over 15 rounds of a filling feed. So a
shortfall here is disqualifying, and a tie is only ever "worth one full run" —
never evidence of equivalence.

### F-72 — 70 % of every prompt is the same 22 tool schemas, re-sent on every call

    tool schemas   7,147 chars   ~1,786 tokens   identical on EVERY call
    persona+feed   3,124 chars   ~  781 tokens   the only part that varies

Locally this is why F-66 failed: Ollama's prefix cache should make the static
70 % nearly free, but F-69 showed the cache does not survive eight concurrent
slots evicting each other, so the simulation pays full prefill for that block
roughly 1,000 times per run. This is the single largest identified waste in the
local pipeline and there is no local fix for it — the cache is the fix, and
concurrency is what breaks the cache.

On a hosted API the same number is an opportunity rather than a loss, because
explicit prompt caching is not subject to eviction by a neighbouring slot.

### F-73 — A hosted API is a ~60x wall-clock win, and the constraint stops being concurrency

Measured basis, from the run ledger: a healthy 15-round run is 504 agent-turns
(36 x 14) and ~940 trace rows, so roughly 1,000 LLM calls, at ~2,000 prompt
tokens and ~150 output tokens each — about 2.0M in / 0.15M out per run.

The local ceiling is 8 concurrent slots, and F-67 established it is a COMPUTE
ceiling, not a memory one. **F-76 RETRACTS THAT** — it is a memory ceiling, and
NUM_PARALLEL=16 spills catastrophically (52x slower). 36 agents through 8 slots is what makes a run take ~2 hours. A hosted
API has no such ceiling at this scale — 36 concurrent requests is unremarkable
for any of the three major providers — so a round becomes one wave instead of
five, and the run becomes minutes.

**What replaces it as the binding constraint is cost, and per-run cost at this
size is small.** Order-of-magnitude, before caching, at 2.0M in / 0.15M out:

    Haiku 4.5   ($1 / $5  per MTok)    ~$2.75 per run
    Sonnet 5    ($2 / $10 per MTok)    ~$5.50 per run
    Opus 5      ($5 / $25 per MTok)    ~$13.75 per run

F-72's static 70 % is cacheable, which takes a meaningful bite out of the input
side. Cache reads are a fraction of base input price, so a cache-aware
implementation lands well below these figures; the exact multiplier should be
read from current pricing rather than assumed.

**This is not a recommendation to switch, and three things must be said plainly:**

1. It changes the experiment. Every published Sim 4 result is `llama3.1:8b`.
   A hosted model is a different population, and F-35's ~28pp noise floor means
   old and new runs cannot be pooled. It would be a new baseline, not more of
   the existing one.
2. It sends persona and feed content to a third party. That is a supervisor's
   call, not mine.
3. It has a real failure mode this project has not faced: a bug that loops
   costs money rather than time. The B-22 watchdog exists for a hang; a spend
   cap would be its equivalent.

The honest framing for the professor is that the 2-hour run is an artefact of
one 8-slot GPU, not of the simulation design, and that the fastest available
path to large runs is not a better local model.

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

#### B-23 — The behavioural gate measured activity, and let a dead config through

**Where.** Ours, `overnight.sh` — the `gate()` function as first written.

**Symptom.** The gate checked actions per turn, posts written, feed size and action
diversity. Every one of those stayed healthy on a config where agents had **stopped
engaging with their feed entirely**. It passed `max_tokens=512` at 1.26 actions/turn,
59 posts and a full 12-slot feed, and the campaign then spent **seven full 36x15
runs** — about four hours — on a world with 1 engagement in 42,336 exposures.

**Cause.** The gate measured *activity*. The study measures *engagement with a post
the agent was shown*. Those come apart exactly when a config makes agents write into
the void, which is what happened, and nothing in the gate could see it.

**Why it is the same mistake as F-38.** F-38 reported on a column that was not what
its name said. This gate reported on a quantity adjacent to the one that mattered.
Both pass every internal consistency check and both are wrong about the world.

**Fix.** The gate now reads `seen_and_acted` from `analyze.py`'s own output, so the
gate and the analysis cannot drift apart on what engagement means, and fails below
1.0 %. Validated against every config the night produced:

| Config | Engagement | Verdict |
|---|---|---|
| `baseline` | 2.40 % | PASS |
| `s_ctrl` (8b, uncapped) | 4.31 % | PASS |
| `diag_leanuncap` | 3.87 % | PASS |
| `s_cap` (capped) | 0.36 % | **FAIL** |
| `s_lean` (capped) | 0.00 % | **FAIL** |
| 3b replicates | 0.00 % | **FAIL** |

Clean separation, with the threshold sitting in open space between the two groups.

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

### F-74 — Model speed does NOT scale with file size. It scales with parameter count, and I got this wrong

**The error.** Comparing five candidate models on 2026-09-08 I estimated each
one's run time by scaling measured tok/s with download size. That is the DECODE
rule, and F-66 established decode is only 22 % of a turn. Prefill is the other
78 %, prefill is compute-bound, and compute scales with **parameters**, not
gigabytes.

**The correct rule**, from F-66's split:

    run time ratio  ~=  0.78 x (param ratio)  +  0.22 x (file-size ratio)

Applied to the five candidates against llama3.1:8b (8.0B, 4.9 GB):

| model | params | file | file-size est. (wrong) | correct est. |
|---|---|---|---|---|
| granite4.1:8b | 8.79B | 5.3 GB | 2.2 h | 2.2 h |
| ornith:9b | 8.95B | 5.6 GB | 2.3 h | 2.2 h |
| **gemma4:e2b** | **5.12B** | 7.2 GB | **3.0 h** | **~1.6 h** |
| gemma4:12b | 11.9B | 7.6 GB | 3.1 h | 3.0 h |
| qwen2.5:14b | 14.8B | 9.0 GB | 3.7 h | 3.7 h |

Four of five barely move, because for dense models trained at similar quantisation
the two ratios track each other. `gemma4:e2b` is the exception and it inverts:
5.12B parameters in a 7.2 GB file, because embedding tables and a vision tower
occupy bytes without doing prefill arithmetic on text. **It is the only one of the
five plausibly FASTER than the current model, and the file-size estimate ranked it
second-slowest.**

This also retracts half of the "strictly dominated, drop it" verdict given the same
day. The memory objection stands — 7.2 GB for 5.12B params is poor packing, and
the vision tower is dead weight for a text-only sim. The speed objection was
backwards.

**Unresolved, and it cuts both ways.** `e2b` advertises configurable *thinking*.
Thinking tokens are decode tokens, and enough of them would erase a prefill
advantage. The `e` prefix also suggests effective-parameter packing, where active
params during text inference may be lower still. Both are directly measurable by
`eval_model.py` (real tok/s, real output length) without a sim — that test should
precede any further claim about this model.

**Method note.** This is the same failure as F-51, F-54 and F-66: a plausible
scaling assumption applied without checking which regime the workload is in. The
log now records the split explicitly so the next estimate starts from it.

### F-75 — The break-even rule: a faster model must retain engagement in proportion to its speedup

**The metric that matters is engagement events per hour, not seconds per round.**
Baseline: 6,049 exposures per run x 5.9 % engagement = ~357 events per run, over
2.0 h = **~179 events/hour**. A candidate is only an improvement if

    (engagement rate ratio) / (run time ratio)  >  1

which means a model 2.5x faster must keep >=40 % of baseline engagement merely to
break even.

**Applied to the one case with real data.** `llama3.2:3b` is 2.5x faster (3.21B
params, F-74 rule). Using the harness's GENEROUS proxy (24 % vs 64 % ENGAGED =
0.375) it scores 0.375 / 0.40 = **0.93 — already a net loss**. Using what the
seven real runs produced (1 engagement in 42,336 exposures) it scores ~0.001.
The 2.5x speedup delivered LESS data per hour, not more.

**Two multipliers that make the trade worse than the rule suggests.**

1. *Variance collapse, which has no alarm.* The `llama3.2:3b` failure was loud —
   zero engagement. The dangerous version is a model that engages plenty but
   homogeneously. Sim 4's findings are measured ACROSS 36 distinct personas; a
   model that drifts to generic responses attenuates the effect size rather than
   removing the data, and that reads as "the effect is weaker" instead of "the
   model stopped differentiating". This is S-2 and nothing at run level catches it.

2. *The noise floor is model-specific.* F-35's ~28pp is a `llama3.1:8b`
   measurement (S-4). Runs-to-conclusion scales with (noise/effect)^2, so a
   candidate whose floor is 1.5x higher needs 2.25x more runs — cancelling a 2.5x
   speedup almost exactly.

**Consequence for model selection.** On this hardware speed is bought almost
entirely with engagement, and engagement is the dependent variable. Candidates
worth the harness are those with a specific reason to beat the trade:
`granite4.1:3b` (3.4B, 2.2x, trained for tool use + structured JSON — the exact
capability llama3.2:3b lacked; needs >=45 % of baseline) and `gemma4:e2b` (5.12B,
1.25x, needs >=80 %, but its thinking mode may erase the gain). `qwen2.5:7b` at
1.05x is inside noise and not worth a switch.

**The one lever exempt from this rule is F-72** — 70 % of every prompt is the same
22 tool schemas, re-prefilled ~1,000 times per run. Removing that cost changes no
model behaviour at all, which makes it the only speed available without paying for
it in the outcome measure.

### F-76 — The concurrency ceiling is MEMORY, not compute, and the optimum is 4 — not 8, and never 16

**This retracts every "8-slot compute ceiling" statement in this log, including
ones written earlier the same day.** The claim rested on `sweep_8/16/24/32`, and
all four of those runs carry `ollama_num_parallel: (unset -> server default)` —
a server pinned at 1. They raised a client semaphore in front of a serialising
backend and measured nothing. F-56 tested concurrency 4 and no higher.

Measured properly on 2026-09-08: server restarted per config, `NUM_PARALLEL`
matched to client concurrency, unique prompt per call (F-55 method note), real
22 tool schemas, real 12-post feed, llama3.1:8b, ctx 8192, flash attention on.

| config | calls/s | mean latency | loaded | free RAM | swap |
|---|---|---|---|---|---|
| NP=4 conc 4 | **0.368** | 10.8 s | 11 GB | 4.3 GB | 775 M |
| NP=8 conc 8 | 0.317 | 24.4 s | 17 GB | 0.8 GB | 775 M |
| NP=16 conc 16 | **0.0071** | **2,261 s** | 30 GB | 0.4 GB | 1,264 M |
| NP=32 conc 36 | **0** (all timed out at 600 s) | — | 56 GB | 0.5 GB | 1,264 M |

**Memory scales linearly and it is the whole mechanism:**

    footprint  ~=  4.9 GB weights  +  1.55 GB per slot   (ctx 8192, flash attn)

NP=32 asked for 56 GB on a 32 GB machine. NP=16 asked for 30 GB and spent 37
minutes per call thrashing. There is no compute story here at all — the GPU was
never the constraint above 4 slots.

**Consequences.**

1. **NP=8 — the setting used for every run this session and in `campaign.sh` —
   is 14 % slower than NP=4.** A free win, in the direction nobody was looking.
2. The practical slot budget follows from the formula. With ~12 GB of desktop
   apps resident, ollama gets ~20 GB, so `(20 - 4.9) / 1.55` is about **9 slots
   before swapping** — and NP=8 already leaves only 0.8 GB free. Anything that
   grows the desktop pushes the optimum down, not up.
3. F-67's "the hardware is not being wasted" survives, but its explanation does
   not. The chip is not saturated by 8 concurrent requests; the machine is out
   of RAM.

**Still n=1 per config.** The NP=16 and NP=32 results are so extreme that
replication cannot reverse them. The NP=4-vs-NP=8 gap is 14 % on single
measurements and is exactly the size of effect this project has gotten wrong
four times (F-51, F-54, F-66, F-74). It needs Phase 0b's five replicates before
`campaign.sh` is changed.

**Method note.** Three separate assertions of a "compute ceiling" were made today
before anyone ran the four-line benchmark that disproves them. The benchmark cost
about twenty minutes. The assertions were built on a sweep whose own manifest
recorded, in plain text, that the server setting was unset.

### F-77 — RETRACTS F-76's 14 % concurrency win. NP=4 through NP=8 is a plateau; the case for NP=4 is variance and memory, not speed

**What happened.** F-76 reported NP=4 beating NP=8 by 14 % (0.368 vs 0.317
calls/s) on one measurement each. Phase 0b re-ran every config five times:

| NP | mean c/s | sd | CV | min-max | loaded | free |
|---|---|---|---|---|---|---|
| 1 | 0.394 | 0.015 | 3.8 % | 0.371-0.411 | 6.3 GB | 5.1 GB |
| 2 | 0.362 | 0.026 | 7.2 % | 0.337-0.395 | 7.9 GB | 2.2 GB |
| 3 | 0.422 | 0.019 | 4.5 % | 0.398-0.437 | 9.5 GB | 0.6 GB |
| **4** | **0.446** | **0.014** | **3.1 %** | 0.431-0.466 | 11 GB | 0.5 GB |
| 6 | 0.411 | 0.045 | 10.9 % | 0.331-0.444 | 14 GB | 0.5 GB |
| 8 | 0.418 | 0.064 | 15.3 % | 0.306-0.465 | 17 GB | 0.5 GB |

**NP=8's replicated mean is 0.418, not 0.317.** F-76 caught it on a bad rep —
0.306 is inside the observed NP=8 range, so the single measurement was not
wrong, merely unrepresentative. NP=4 vs NP=8 is **1.07x with overlapping
ranges: not resolvable at n=5.**

**What survives from F-76, unchanged.** NP=16 at 52x slower and NP=32 failing
outright are far too extreme for replication to reverse, and the memory formula
holds across all six configs: `4.9 GB + ~1.55 GB per slot`. The ceiling is still
memory, not compute. Only the 14 % claim falls.

**What replicates, and it is smaller than anyone thought.** Parallelism is worth
**1.13x** (NP=1 -> NP=4), not the 1.30x F-56 reported. Both F-56 and F-76 measured
it once.

**The real signal is variance, not throughput.** CV rises monotonically with slot
count above 4 — 3.1 % at NP=4 against 15.3 % at NP=8 — and it tracks memory
exactly: NP=8 holds 17 GB and leaves 0.5 GB free, so its slow reps are the machine
swapping, not the GPU saturating. **NP=8's worst rep (0.306) is 27 % below NP=4's
worst (0.431).**

**Recommendation, stated for what it is.** Move `campaign.sh` from NP=8 to NP=4
**for predictability and 6 GB of reclaimed RAM, not for speed.** Mean throughput
is statistically indistinguishable. A 2-hour unattended run benefits from a
config whose worst case is 27 % better and that leaves the desktop 6 GB, and
that argument does not require the speed claim I made and have now withdrawn.

**Method note, fifth instance.** F-51, F-54, F-66, F-74 and now F-76 were each a
single measurement that replication overturned. Phase 0b cost 45 minutes and
caught this one before it reached `campaign.sh`. The rule this log should have
adopted long ago: **no configuration change on n=1, ever.**

### F-78 — Phase 0d: both candidate models fail. Keep llama3.1:8b

`granite4.1:3b` and `gemma4:e2b` pulled and scored on the real prompt, real 22
tool schemas, real 12-post feed, 25 trials, NP=1 single stream.

| | tool rate | ENGAGED | grounded | out tok | wall |
|---|---|---|---|---|---|
| llama3.1:8b | 88 % | **40 %** | 100 % | ~80 | 2.7 s |
| granite4.1:3b | 100 % | **4 %** | 100 % | — | 1.4 s |
| gemma4:e2b (capped 300) | 0 % | 0 % | n/a | 300 (truncated) | 4.9 s |
| gemma4:e2b (uncapped) | 62 % | **12 %** | — | **911** | **12.1 s** |

**`granite4.1:3b` answers `do_nothing` 24 times out of 25.** It emits perfectly
formed tool calls — 100 % tool rate, the best of the three — and uses them to
decline. This is a new failure mode, distinct from llama3.2:3b's (which acted, but
never on the feed). It needed >=29 % ENGAGED under F-75 and scored 4 %.

**`gemma4:e2b` is 4.5x SLOWER, not 1.25x faster — F-74's prediction for it is
dead.** Its thinking mode emits **911 output tokens per turn against llama3.1:8b's
~80**. Decode is 22 % of a turn at 80 tokens; at 911 it dominates completely and
the low parameter count buys nothing. F-74's rule is correct as far as it goes —
prefill scales with parameters — but it silently assumes comparable output length,
and a reasoning model violates that by an order of magnitude. **The rule needs the
caveat: it holds only between models with similar output-token behaviour.**

**A harness bug this exposed, worth keeping.** At `max_tokens=300` gemma4:e2b
scored 0 % tool rate with `finish_reason=length` — it spent the entire budget
reasoning and never reached the call. That is my cap, not the model: the real sim
runs uncapped (`--max-tokens` default 999,999,999). **`eval_model.py` is biased
against thinking models and must be run uncapped for them.** Had this not been
checked, a model would have been rejected for a limit the simulation does not
impose.

**Conclusion. Keep `llama3.1:8b`.** This is the outcome R5 of the run plan
predicted on cost grounds, now confirmed on capability grounds. Neither candidate
is worth a run, so S-1..S-6 stay unqueued and the ~8 runs of baseline-rebuilding
overhead a model change would cost are not spent.

### F-79 — The harness baseline is noisy at n=25, which softens every gate built on it

`llama3.1:8b` ENGAGED, six replicates of 25 trials each:

    44 %, 52 %, 60 %, 48 %, 64 %, 48 %
    mean 52.7 %   sd 7.8   CV 14.7 %   range 44-64 %

**The 64 % single reading that F-75's gates were built on is the TOP of the
distribution, not its centre.** Every threshold quoted from it (>=29 %, >=51 %) was
about 20 % too high. Corrected against the replicated mean: granite4.1:3b (2.2x
faster) needs >=24 %, and gemma4:e2b — now known to be 4.5x SLOWER — would need to
EXCEED baseline, >=53 %.

**What the harness can and cannot resolve.** At sd 7.8 per 25-trial replicate,
separating a candidate 10pp from baseline needs about 10 replicates (~240 trials),
not one. A single 25-trial reading only reliably distinguishes gaps beyond ~20pp.

**It does not change F-78's conclusion** — 4 % and 12 % sit 40pp+ below the
replicated mean and below even the worst baseline replicate (44 %), far outside
anything this spread could explain. But it does mean:

1. Gate thresholds must be quoted against a REPLICATED baseline, not one reading.
2. `--trials 25` is too few to separate candidates that land near the line. A
   candidate scoring within the baseline's own spread is "worth one full run",
   never "equivalent".
3. This is the same lesson as F-77 one level up: the harness that catches n=1
   errors in full runs is itself being read at n=1.

### F-80 — REVISES F-69. The prefix cache DOES survive concurrency; the benefit decays with slot count rather than collapsing

Block A, 3 replicates per cell, identical content in both layouts — only the
ORDER differs, so any gap is cache and nothing else.

| NP | shared prefix | persona-first (upstream) | ratio |
|---|---|---|---|
| 1 | 0.290 c/s | 0.179 | **1.62x** |
| 2 | 0.349 | 0.183 | **1.91x** |
| 4 | 0.345 | 0.208 | **1.66x** |
| 8 | 0.312 | 0.250 | 1.25x |

F-69 concluded the cache "does not survive concurrency", and F-68 retracted
F-66's predicted 2.5-5x down to ~1 % on that basis. **Both were too pessimistic.**
The cache survives at every slot count tested; what decays is the size of the win
— 1.91x at NP=2 down to 1.25x at NP=8 — because more slots evict each other's
entries faster. A gradient, not a cliff.

**This does not license a change, because the shared layout is ALREADY the
default.** `--persona-in-system` is `store_false` on `shared_prefix`, so every
published run since F-66 already hoists the persona out of the system message.
What this measurement does is *quantify a default that was previously believed to
be worthless*: it is worth 1.66x at NP=4.

**It also sharpens the NP choice.** With the shared layout, throughput peaks at
NP=2 (0.349) and NP=4 (0.345) — a tie — and falls at NP=8 (0.312). The cache
benefit is larger at low NP, so the two effects agree: **NP=2-4 is optimal, and
NP=8 is worse for two independent reasons.** F-77 chose NP=4 on variance grounds;
F-80 supports the same choice on throughput.

### F-81 — Cost per round RAMPS for three rounds, then plateaus flat. Every estimate built on a 3-round smoke is wrong

Per-round wall clock, 36 agents, 15 rounds, NP=4:

    round  0    90s      <- empty world, nothing to rank
    round  1   351s
    round  2   546s          the ramp: the feed is filling
    round  3   790s
    rounds 4-14  ~790s    <- plateau, flat to the end (751-821s)

**Updated 09-10 from six replicates rather than one: the plateau mean is
769 s** (the 790 s above is a single run). The ramp replicates almost exactly --
95 / 352 / 549 s against the original 90 / 351 / 546 -- so the SHAPE is solid
and only the level shifts, by about 3 %. Recomputed from `round_timings.csv`
in the data package, which any reader can verify independently.

**The plateau is the operative number, and the ramp is a trap.** A 3-round smoke
totals 986 s and looks like ~330 s/round; the true steady-state cost is 790 s/round,
2.4x higher. That is exactly why last night's 15-round run took **174 minutes
against my 120-minute estimate** — I scaled a 3-round measurement by 5 when the
correct factor is 10.6.

This is F-60's pattern once more (small benchmarks overpredict), but with a
mechanism: the cost driver is how full the feed is, and a short run never fills it.

**What it means for the "1000 rounds" question.** Cost per round does NOT grow
without bound — it flattens. So long runs are predictable, just expensive:

    36 agents, 1000 rounds   ~= 986 + 997 x 790  = 788,600 s  ~= 9.1 days

### F-82 — 99 agents runs. Agent count scales SUBLINEARLY; this is the answer to "bigger worlds"

Block E, 99 agents from the Twitter persona set, 3 rounds: **completed in 39
minutes with 4.06 % engagement** — the first run in this project's history above
36 agents. `personas.py:75` already loads the CSV, so this needed a flag, not code.

Per-round, still inside the ramp at round 2:

    36 agents:  90 / 351 / 546 -> plateau 790 s
    99 agents: 177 / 827 / 1327 -> plateau ~1,925 s (projected by the 36-agent ramp shape)

    2.44x the cost for 2.75x the agents  ->  exponent ~0.88, SUBLINEAR

Sublinear in agents is the good direction and makes bigger worlds cheaper than
feared. Extrapolating both laws:

    1000 agents x 1000 rounds  ~= 790 x (1000/36)^0.88 x 1000  ~= 170 days

which independently reproduces the earlier 167-day figure by a different route.

**Caveat that must travel with this result.** The Twitter personas carry no age,
gender or MBTI, so a 99-agent run is a different persona construction and cannot
be pooled with the published nine. Engagement of 4.06 % versus the 36-agent
smoke's 5.70 % may be that difference, the round-2 ramp, or noise — three
confounds and one measurement. It establishes FEASIBILITY, nothing more.

### B-24 — An unlocalized loop variable cost a validation run

    server () { ...; for i in $(seq 1 90); do curl ... && return 0; done }
    for i in 1 2; do server 4; run np4_val_r$i 36 15; done

`server()` never declared `local i`, so its readiness poll clobbered the caller's
counter. The server answered on its 2nd poll, leaving `i=2`; iteration one ran
`np4_val_r2`, and iteration two found that manifest and skipped. **One of two
validation runs silently never happened.** The resumable-by-manifest design,
which exists to make interrupts cheap, is what converted the bug into a silent
skip instead of a visible error. Fix: `local i` in every helper.

### F-83 — The remaining lever is CALL COUNT, not call cost. 46 % of a run's model calls buy a second action that happens 1 % of the time

**Per-call cost is already at its floor, and that is what points at the answer.**
Reconciling F-80 and F-81 against the measured 790 s round:

    observed   790 s/round / 67 calls / 4 slots      = 2.9 s of GPU per call
    predicted  cached prefix 1,786 tok               ~ free (F-80)
               varying   781 tok / 490 tok/s         = 1.6 s prefill
               decode     80 tok /  54 tok/s         = 1.5 s
                                                       -------
                                                       3.1 s

These agree. The prefix cache is working, the static block is already nearly
free, and the remaining 781 tokens are persona and feed -- the experiment
itself. **Shrinking the prompt further saves almost nothing.** What is left is
the number of calls.

**What the follow-up call actually buys.** Measured over a full 15-round run,
504 agent turns:

| | |
|---|---|
| turns taking 0 or 1 action | **499 (99.0 %)** |
| turns taking 2 or more | **5 (1.0 %)** |
| actions returning content the model must read | **0 of 431** |

Every action in the entire run was terminal -- a like, a comment, a post, a
follow. Not one `search_posts`, `search_user` or `trend`. camel's loop
nonetheless makes a second model call after every tool call so the agent can
react to a result it cannot use, and that follow-up is **~46 % of all LLM calls
in a run**.

**The fix, and why it is not either of the two existing flags.**
`--smart-tool-loop` stops the loop after a TERMINAL action and continues after
an INFORMATIONAL one, by mutating `max_iteration` inside `_aexecute_tool` --
camel reads it immediately afterwards (`chat_agent.py:2070`), so this needs no
upstream change (D-1 holds; it is a subclass override).

    --lean-actions       removes 8 actions -> changes what an agent CAN do (F-55)
    --max-tool-rounds 1  blunt cap -> also destroys search -> read -> act
    --smart-tool-loop    removes neither; drops only the no-op round-trip

**What is proven and what is not.** `test_smart_tool_loop.py` -- 10 checks,
all passing, exercising the real method with only the parent stubbed -- proves
the loop stops where intended, that all 22 tools are classified with none
silently dropped, that search->read->act survives, that the flag off is a true
no-op, and that a cap does not leak between turns.

**It proves nothing about speed or behaviour at 36 agents.** The 46 % figure is
a count of calls, not a measured speedup, and the 1 % of turns that lose a
second action is exactly the kind of small effect this project has six times
mistaken for zero. **The flag is OFF by default and needs an A/B** -- 3
replicates per arm, engagement-gated, at 36 agents. Until then it is an
implemented hypothesis, not a result.

### F-84 — RETRACTS F-83. OASIS already caps the tool loop at 1. There was no follow-up call to remove

**Measured, from the live server log rather than inferred from trace rows:**

    LLM requests / agent-turn      1.25      (F-83 claimed 1.85)
    oasis/social_agent/agent.py:69 -> max_iteration: int = 1

**The follow-up call F-83 set out to eliminate was eliminated upstream before
this project started.** F-83's 46 % came from counting rows in the `trace`
table and assuming each implied a model call. Trace rows are ACTIONS, not
calls. The real overhead above one call per turn is 0.25 — a ~20 % ceiling, not
46 % — and it is not the tool loop at all (most likely retries and the round-0
sign-up phase; not yet pinned).

**The implemented flag fires and changes nothing.** `--smart-tool-loop` logged
**60 short-circuits in 72 agent-turns**, so the hook works exactly as its 10
tests claim. But what it does on firing is set `max_iteration = 1`, which is
already the value. It is a correct implementation of a no-op.

**Worse for the design argument: the capability F-83 claimed to preserve does
not exist.** F-83's case against `--max-tool-rounds 1` was that it destroys
search -> read -> act. With `max_iteration=1` upstream, **that path is already
gone for every run this project has ever done.** An agent that calls
`search_posts` gets its results appended and the loop stops before it can act
on them. That is a real finding about the simulation's semantics and it is
worth more than the optimisation was: the 22-action surface advertises a
capability the loop cannot deliver.

**Consequence. There is no remaining local optimisation.** Per-call cost is at
its floor (F-83's arithmetic, which still holds), call count is already
minimal, concurrency is settled at NP=4 (F-77), the prefix cache is already
banked (F-80), and no smaller model is usable (F-78). **The system is at its
floor on this hardware.** Remaining machine time is worth more spent on
replicates than on optimisation.

### B-25 — A reader bug aborted a 12-hour campaign and stranded 6 unrelated runs

The A/B's smoke gate read short-circuits via
`json.load(...).get("manifest", {})`. Those fields are written at the JSON TOP
level, so it read 0 from a run that had 60, declared the flag a no-op and
called `exit 1`.

**Two compounding faults, and the second is the expensive one:**

1. The reader assumed a nesting that does not exist, and had never been tested
   against a real manifest — the same defect class as B-24.
2. **The gate was wired to `exit 1`, which killed everything queued behind it,
   including a 6-run replicate bank that did not depend on the flag at all.**
   Five hours of machine time were lost to that, not to the bug. A failed gate
   should skip its own phase and fall through to work that does not depend on
   it. Restructured so the bank now runs as an independent script that no gate
   can strand.

#### B-27 — The shipped data package published one run's timings under another run's name

**Where.** Ours, `build_package.py::round_timings()`.

**Symptom.** `round_timings.csv` carried **eleven** rounds for `scale99_full` at
89 / 337 / 521 / 732 s -- the 36-agent shape -- for a run that is 99 agents and
five rounds. The real numbers, in the run's own manifest, are 172 / 801 / 1292 /
1936 / 2086, which is what F-91 cites. The published sums did not even match the
run's `total_seconds` (6,985 s against 6,288 s) and nothing checked.

**Cause.** The function recovered per-round wall clock by globbing
`/tmp/*_<label>.log` and scraping every `round N done in Xs` line from the first
file that matched. B-26's mislabelled 36-agent run was originally *named*
`scale99_full`; relabelling it to `bank36_mislabelled` and pulling it from the
Parquet export never touched `/tmp`, so the stale log still matched the glob and
the package rebuilt the wrong timings straight back in.

**Why it matters more than it looks.** These are the numbers behind F-81's
plateau and F-91's scaling exponent, and the package is the artifact a
collaborator would be handed. The findings themselves are safe -- both were
computed from manifests -- but anyone reproducing them from the package would
have got a different answer and no way to tell which was wrong.

**Fix.** Read `rounds[].seconds` from the run's own `manifest.json`, which is
written by the run, is per-run by construction, and cannot be contaminated by a
neighbour. Added a consistency assertion: round seconds must sum to within 5 %
of `total_seconds` or the builder prints a warning. Coverage went from 16 runs
to **24** as a side effect, because the scrape only ever found logs for runs
whose files happened to survive in `/tmp`.

**The pattern, third instance.** B-26 (`--agents` truncates silently), F-38 (a
column that was not what its name said), and now this: **a label that stops
meaning what it says, with no check tying it back to the thing it names.**

### F-85 — The noise floor is ~5x tighter than assumed. A/B experiments are affordable after all

Six runs at one genuinely identical, validated configuration (llama3.1:8b,
NP=4, 36 agents, 15 rounds, terse tools, uncapped output):

| run | wall | engagement |
|---|---|---|
| np4_val_r1 | 175 m | 5.99 % |
| np4_val_r2 | 174 m | 6.98 % |
| bank_r1 | 169 m | 7.68 % |
| bank_r2 | 172 m | 7.37 % |
| bank_r3 | 164 m | 7.11 % |
| bank_r4 | 165 m | 7.15 % |

    wall clock   mean 170.3 m   sd 4.71    CV 2.8 %
    engagement   mean  7.05 %   sd 0.573   CV 8.1 %

**Against the assumptions every plan in this log was sized on:**

| | assumed | measured |
|---|---|---|
| wall-clock noise | ~15 % (`campaign.sh` power note) | **2.8 %** |
| behavioural noise | ~28pp (F-35) | **0.57pp** |

**Why the old figures were so wrong.** They were computed across runs that were
not actually at the same configuration. The two runs behind the 15 % figure (355
vs 408 s/round) straddled the NUM_PARALLEL masquerade described in the F-77
correction, where a server believed to be at NP=8 was serving at NP=1. Comparing
runs whose config differed in an unrecorded way measures the difference, not the
noise. This is the same root cause as B-25 and F-76: **the manifest recorded our
intention rather than the server's state.** Every variance estimate taken before
that was fixed is suspect.

**What it unlocks. At alpha .05 / power .8:**

    effect                        at assumed 15%    at measured 2.8%
    wall clock 10 % faster            35 runs/arm         1 run/arm
    wall clock 20 % faster             9 runs/arm         1 run/arm

    engagement 1.5pp shift                    —           2 runs/arm
    engagement 1.0pp shift                    —           5 runs/arm
    engagement 0.5pp shift                    —          21 runs/arm

**Several conclusions in this log rest on the old figure and are now too
pessimistic.** `campaign.sh`'s header states that detecting a 1pp engagement
shift "would take far more runs than any campaign affords" — it takes five per
arm. The run plan's R1 argued Phase 1 could not resolve a 14 % speed difference
without ~18 runs per arm; it needs one or two. **The A/B experiments this project
kept declining as unaffordable were affordable the whole time.**

**Caveat, and it is not small.** A variance estimate from n=6 is itself
imprecise: the 95 % interval on an sd at n=6 spans roughly 0.62x to 2.45x the
point estimate. So engagement sd could plausibly be as high as ~1.4pp, which
would put a 1pp detection nearer 30 runs per arm. The bank is being extended to
n=10+ specifically to tighten this. **What is already safe to say is that the
floor is nowhere near 28pp**, and that behavioural A/Bs belong back on the table.

### F-86 — The plateau is CONTEXT ACCUMULATION, not a filling feed. This overturns F-81's mechanism and F-84's "no lever remains"

Found during the 09-10 audit, by reconciling a discrepancy nobody had checked:
the simulation is 100 % `llm_wait`, yet it achieves **1/8th the call rate the
NP=4 benchmark achieves at the same concurrency**. Concurrency was not the
cause — measured over all 550 requests of `bank_r5`, four are in flight **94.4 %
of the time** and the GPU is idle 0.1 %. F-67 was right about saturation.

**The cause is per-request latency, and it grows with the round:**

| round | wall | mean request latency |
|---|---|---|
| 0 | 94 s | **10.1 s** |
| 1 | 337 s | 35.3 s |
| 2 | 513 s | 54.9 s |
| 3 | 727 s | 75.6 s |
| 4 | 851 s | 86.2 s |
| 5-14 | ~790 s | **80-88 s, flat** |

**Round 0 matches the standalone benchmark almost exactly (10.1 s vs 10.8 s),
because at round 0 an agent has no history and its prompt is just system +
tools + feed.** By round 4 the same call takes 8.5x longer and then stops
growing — the signature of a context window filling to its cap and truncating.

`oasis/social_agent/agent.py:184` says it outright: *"Camel can not stop
updating the agents memory after stop and astep."* Every turn appends the user
message, the assistant reply and the tool result to that agent memory, and all
of it is re-prefilled on the next turn.

**This overturns two earlier conclusions.**

1. **F-81's mechanism was wrong.** The plateau is not the feed saturating at 12
   slots; it is `OLLAMA_CONTEXT_LENGTH=8192` truncating an ever-growing history.
   F-81's *numbers* stand — the ramp and the ~769 s plateau are measured — but
   its explanation does not, and the explanation is what predicts behaviour at
   other settings.
2. **F-84's "there is no remaining local optimisation" was wrong.** There is,
   and it is the largest yet found. If an agent's memory were cleared between
   rounds, every round would cost about what round 0 costs. A 15-round run would
   drop from ~170 min toward ~25 min — of order **6x**, against the 1.13x
   concurrency and 1.66x prefix-cache levers.

**Why this hid for so long.** Every benchmark in this project, mine included,
issued fresh single-turn requests — which is exactly a round-0 prompt. The bench
was measuring the cheapest round of the run and calling it representative. F-60
recorded that small benchmarks overpredict four times running; this is the same
error one level deeper, and it inflated the apparent cost of nothing while
hiding the real one.

**What is NOT yet established, and must not be asserted before it is tested.**
Whether clearing memory between rounds changes agent behaviour. There is an
argument it barely can: the context is already capped at 8192, so agents are
already losing most of their history to truncation and receiving an arbitrary
sliding window rather than coherent memory. But that is an argument, not a
measurement, and this log has six entries recording what happens when those are
confused. **It needs an A/B against the 7-run bank, which F-85 says costs 2-5
runs, not a campaign.**

### F-87 — `--fresh-context` is real and large: ~3.9x. It also halves engagement, so it is a trade, not a free win

Implemented from F-86 and smoke-tested at 36 agents, 3 rounds, against the
3-round control (`smoke_on`).

| round | control | fresh-context |
|---|---|---|
| 0 | 94 s | 106 s |
| 1 | 337 s | **216 s** |
| 2 | 513 s | **203 s** |
| 3 | 727 s | — |
| 4-14 | ~790 s (plateau) | — |

**The mechanism is confirmed and the shape is the point.** Control climbs to a
~790 s plateau. Fresh-context has ALREADY FLATTENED at ~205 s by round 2, because
each turn starts from the system message and nothing accumulates. 108 context
resets were logged, exactly 36 agents x 3 rounds. Projected to 15 rounds: about
**50 minutes against 170 — roughly 3.4x**, and ~3.9x at the plateau. That is
larger than every other lever found combined.

**And it halves engagement.**

    engagement    control 5.70 %   fresh-context 2.81 %
    action rate   control 0.792    fresh-context 0.898
    action mix    fresh-context: create_post x89, like_post x7

Agents with no memory are MORE active and engage with their feed LESS. They
default to broadcasting rather than reacting — the F-63 signature, arrived at by
a new route.

**By F-75's own arithmetic it still passes break-even.** A config 2.5x faster
needs 40 % of baseline engagement to break even on data per hour; it retains
49 %, so it yields about 23 % more engagement events per hour. **That is not
sufficient grounds to adopt it**, because engagement is not merely the sample
size here — it is the dependent variable. Halving it changes the phenomenon
being measured, not just the precision of the measurement.

**Status: a genuine 3.9x efficiency lever with a genuine behavioural cost.**
Both halves have to be reported. It should NOT become the default, and it is
exactly the kind of trade a supervisor decides rather than an engineer.

**Caveats on these numbers.** n=1 per arm, three rounds, and the control
(`smoke_on`) carried `--smart-tool-loop`, which F-84 established is a no-op, so
it is a fair control but was not run for this purpose. F-85 says a proper A/B
costs 2-5 runs per arm. **A 15-round fresh-context run is the single most
informative thing left to run**, because it settles both the plateau and whether
the engagement gap widens or narrows over a full run.

### F-88 — SETTLES F-87. `--fresh-context` is 3.09x faster, retains 33 % of engagement, and yields 1.02x data per hour. It is a wash

The full A/B, overnight 09-10/11. Treatment n=3 at 15 rounds; control is the
8-run validated bank at identical configuration.

| arm | n | wall | engagement |
|---|---|---|---|
| control | 8 | 170.2 m (sd 4.18) | **6.94 %** (sd 0.523) |
| fresh-context | 3 | **55.1 m** (sd 2.60) | **2.30 %** (sd 0.466) |

    SPEEDUP        3.09x
    ENGAGEMENT     -4.64pp   (33 % of control)
    DATA PER HOUR  1.02x     <- F-75 break-even is exactly 1.00

**The two effects cancel almost perfectly.** Three times the runs, a third of
the engagement per run: the same number of engagement events per hour, to within
2 %. `--fresh-context` does not buy anything. It buys *differently*.

**This is a cleaner refutation than the smoke suggested.** F-87's 3-round test
measured 49 % engagement retention and a 1.23x yield, which looked like a modest
win. At full length the retention is 33 % and the yield is 1.02. The gap widens
over a run, exactly as F-87 warned it might and could not then test.

**What it costs, and it is not only engagement.** Fresh-context agents post
instead of reacting. Every run's action tally is dominated by `create_post`
while `like_post` collapses — the F-63 signature. Since Sim 4's published
findings are all about *what agents engage with*, a configuration that cuts
engagement to a third is not a faster version of the experiment. It is a
different one, measured worse.

**Verdict: do not adopt. The flag stays, off by default, with this result
attached.** It is a real and correctly-implemented 3x lever whose entire gain is
consumed by the behaviour it changes, and that is worth recording precisely so
nobody re-derives it in six months.

### F-89 — Noise floor at n=9, and it is holding

**Updated with `bank_r7`:** control n=9, wall 169.5 m (sd 4.53, CV 2.7 %),
engagement 6.94 % (sd 0.489, CV 7.0 %). The F-88 A/B with n=9 control: speedup
3.07x, engagement 33 % of control, data per hour **1.02x** — unchanged. Measured
plateaus: control **765 s**, fresh-context **235 s**.

*Original n=8 entry follows.*

### F-89a — Noise floor at n=8

    wall clock   170.2 m   sd 4.18    CV 2.5 %
    engagement     6.94 %  sd 0.523   CV 7.5 %

Against n=6 (CV 2.8 % / 8.1 %) the estimate has barely moved, which is the
reassuring outcome: the floor is stable, not an artefact of a small sample.
F-85's headline stands and tightens slightly.

    runs per arm    1.5pp engagement shift    1.9
                    1.0pp                     4.3
                    0.5pp                    17.2

### B-26 — A missing `--personas` flag turned the headline 99-agent run into a 36-agent run

`final.sh` queued `run scale99_plateau 99 8` **without** `--personas`, so it
loaded the default `user_data_36.json`, which holds 36 records, and `--agents 99`
silently capped at 36. The run completed, looked healthy, and produced a
"99-agent plateau" of 736 s that matched the 36-agent 769 s exactly.

**It matched because it WAS a 36-agent run.** Caught only because that agreement
was too good: F-82 projected 1,925 s, and a 2.6x miss in the favourable direction
is the shape of a bug, not a discovery. Verified from the database — `sign_up: 36`,
`agent_turns_total: 288 = 36 x 8`.

Two lessons. **`--agents` silently truncates to the persona file's length rather
than failing**, which is how a mis-specified run produces plausible output. And
an earlier version of this queue (in `supervisor.sh`) *did* carry the flag; it
was lost when the queue was rewritten under time pressure. The run has been
relabelled `bank36_mislabelled` and removed from the Parquet export so nothing
downstream reads it as a 99-agent result.

### F-90 — CORRECTS F-85 and F-89. The 28pp and the 0.52pp measure different things; F-35 was never overturned

**The error.** F-85 reported the noise floor as "~5x tighter than assumed" and set
0.523pp against F-35's ~28pp as though one replaced the other. **They are
different quantities and both are correct.**

| | what it measures | value |
|---|---|---|
| F-35 | **per-agent posting share**, SD across agents and runs | 30.7pp |
| F-89 | **run-level aggregate engagement rate**, SD across runs | 0.52pp |

F-35 asks "how differently do individual agents behave from one run to the
next"; F-89 asks "how much does the run's headline number move". Averaging 36
agents collapses the first into the second — this is the central limit theorem,
not a contradiction, and a factor of ~sqrt(36)=6 plus the difference between a
share-of-actions and a rate accounts for the rest.

**What actually follows, stated correctly:**

1. **Run-level comparisons are cheap.** Comparing the aggregate engagement rate
   between two configurations needs 2-5 runs per arm (F-89). The fresh-context
   A/B in F-88 is exactly this shape and was correctly powered at n=3 vs n=8.
2. **Per-agent intervention studies remain expensive, exactly as F-35 said.**
   An intervention must move posting share >=14.3pp to be visible at 36 agents,
   and the four prompt experiments that moved it 3-5pp remain unfalsifiable at
   this scale. **F-35 stands untouched.**
3. F-36's refinement also stands: follow and like behaviour is far cheaper to
   study than posting, and an intervention study should target those.

**What was wrong in the artifacts, and is now fixed.** The Mechanics page was
edited to say the 28pp figure "was computed across runs whose server settings
differed" — that explanation belonged to the *wall-clock* 15 % figure (F-77's
NUM_PARALLEL masquerade), not to F-35, which was measured on a byte-identical
config pair and validated by a clean paired null. That edit has been reverted to
a correct statement.

**How it happened.** Two numbers both called "the noise floor" in a log with
ninety findings, and I matched on the phrase rather than on the quantity. The
tell was available: F-35 says "over 15 pairs" and "posting share", neither of
which describes a run-level rate. **Caught by reading F-35 before overwriting a
figure that cited it** — which is the only reason it did not reach the
presentation.

### F-91 — RETRACTS F-82's sublinear exponent. Agent scaling is LINEAR (0.992), and bigger worlds cost ~45 % more than projected

The real 99-agent run finally executed — 99 agents verified in the database, 5
rounds, twitter personas — after B-26's missing `--personas` flag was fixed.

| round | 36 agents | 99 agents | ratio | implied exponent |
|---|---|---|---|---|
| 0 | 95 s | 172 s | 1.81 | 0.589 |
| 1 | 352 s | 801 s | 2.28 | 0.813 |
| 2 | 549 s | 1,292 s | 2.35 | 0.846 |
| 3 | 745 s | 1,936 s | 2.60 | 0.944 |
| 4 | **765 s** | **2,086 s** | **2.73** | **0.992** |

**99/36 = 2.75. The cost ratio converges on exactly that.** The exponent is
**0.992 — linear**, not the 0.88 F-82 reported.

**Why F-82 was wrong, and it is the same error a third time.** Its exponent came
from rounds 0-2, the only rounds it had. Those are ramp rounds, where neither
world has filled its context window — and the exponent *climbs monotonically
through the ramp* (0.589 -> 0.813 -> 0.846 -> 0.944 -> 0.992) precisely because
context accumulation has not yet saturated. F-81 warned that estimates built on
a 3-round run are wrong; F-86 explained the mechanism; F-91 is the third
instance, and this time it was measured rather than projected.

**Revised projections, linear in agents:**

    99 agents x 15 rounds     ~2,086 s/round   ~8.7 hours
    1000 agents x 1000 rounds ~20,680 s/round  ~239 days

F-82 projected 165 days for the last of those. **The real figure is ~45 %
higher.** Sublinearity was the one piece of good news about scaling and it does
not survive measurement: adding agents costs exactly proportionally.

**What still stands from F-82.** 99 agents run successfully; the persona file
supports it with a flag and no code; and the twitter set cannot be pooled with
the reddit 36. Only the exponent falls.

### F-92 — The headline finding INDEPENDENTLY REPLICATES at a different configuration. This is the most scientifically valuable result of the efficiency work

The nine validated-config runs were built as an *efficiency* baseline and had
never been put through `exposure_model.py`. They should have been: they are
54,000 fresh exposures, and — critically — **they are not a repeat of the
published runs.** They differ in three ways at once:

| | published `v10_*` | new bank runs |
|---|---|---|
| temperature | 0.9 | **0.7** |
| tool descriptions | full docstrings | **terse** (F-64) |
| prompt ordering | persona first | **shared prefix** (F-80) |

That makes pooling illegitimate — and makes them something better than more data.
**They are an independent replication.**

    PRIMARY, stratified by (agent, feed slot), slots 0-4:
      network vs discovery   OR 3.07  95% CI [2.76, 3.42]  p=7e-93  (888 strata)
      fof     vs discovery   OR 1.86  95% CI [1.54, 2.24]  p=7e-11  (397 strata)

    Per-run: positive in 9/9, individually significant in 9/9.
      3.12, 3.50, 3.95, 2.92, 1.76, 2.71, 3.59, 3.88, 3.25

**Against the published OR 3.51.** The new interval [2.76, 3.42] excludes 3.51,
so the magnitudes are formally distinguishable — unsurprising, since temperature
alone should move it. **The direction, the significance and the order of
magnitude all hold across a three-way configuration change.** A result that
survives being measured on a different prompt at a different temperature is worth
considerably more than the same result measured twice the same way.

**The fof contrast remains the weaker claim,** individually significant in only
4/9 runs and leaning on pooling. It should be reported as suggestive, exactly as
the original analysis said.

**Method note, and it is a criticism of how this was run.** These nine runs sat
for two days as "efficiency replicates" while the science artifacts continued to
cite nine older runs. Nobody asked whether the new data bore on the research
question until prompted. **Efficiency work generates real data; it should be
analysed as data, not just as timings.**

### F-93 — Terse tool descriptions did not only save time. Engagement TRIPLED, 2.29 % -> 6.94 %, and nobody checked until asked

**How it was found.** Gordon asked how the efficiency changes could possibly have
raised engagement. The expected answer was "they cannot, that is the point" -- the
six adopted levers are all changes to *packaging*, and F-64's own note that tool
calling "got better, not worse" had been read as a pleasant side remark. Grouping
all 20 full-length 36x15 runs by prompt says otherwise.

| tool descriptions | n | engagement | range | action rate | wall |
|---|---|---|---|---|---|
| full docstrings | 8 | **2.29 %** | 1.58-2.71 | 0.634 | 118 m |
| first line only (F-64) | 9 | **6.94 %** | 5.99-7.68 | 0.776 | 169 m |

Old group: `v10_register`, `v10_replicate`, `v10_rep3..6`, `baseline`, `full_8b`.
New group: `np4_val_r1/r2`, `bank_r1..r7`. Computed from
`data/sim4_package/runs_index.csv`; any reader can reproduce the grouping.

**The ranges do not overlap and the denominator is fixed.** Exposures per run are
6,050 (old) against 6,048 (new) -- 36 agents x 14 scored rounds x 12 slots. The
entire difference is in the numerator: actions landing on posts the agent was
shown.

**Mechanism, and F-64 already stated it.** 3,759 of 4,761 prompt tokens were the
22 docstrings, sitting between the feed and the instruction. F-65 supplies the
extreme case: `full_8b` is the lowest-engagement full run ever recorded here at
**1.576 %**, and it is the one run made at NP=8 with the long prompt, where the
per-slot context of 4,096 silently truncated a 4,761-token prompt. **The feed is
at the end of the prompt, so the feed is what was cut.**

**It costs wall clock and is still a large net win.** Engaged agents emit more
tool calls and more text, which accumulates into the next turn's context (F-86),
so the run got *slower* despite the shorter prompt measuring 1.44x faster alone.
On F-75's metric:

    full docstrings    139 events / 1.97 h  =   70 events/hour
    first line only    420 events / 2.82 h  =  149 events/hour   -> 2.1x

**This is the mirror image of F-88.** `--fresh-context` buys 3.09x wall clock and
returns 1.02x data per hour: a wash. Terse tools *cost* 1.43x wall clock and
return 2.1x data per hour. F-75's rule works in both directions and this is the
only entry in the ledger that comes out clearly ahead on it.

**What is NOT established.** This is two groups of runs, not two arms. Terse
descriptions (F-64) and the shared prefix (F-80) were adopted together, so their
split is unresolved. Temperature is ruled out -- the old group spans 0.7 and 0.9
and both sit inside the same 1.6-2.7 % band -- and the metric is ruled out:
`git log` shows `analyze.py`'s `seen_and_acted` and `engagement_rate` untouched
across the boundary. F-68's 3-round test measured only +0.62pp, inside the noise
floor, so **the effect grows with round count and a short test cannot see it**
(F-60 and F-81 a further time). At F-89's floor a 4.6pp effect needs 2 runs/arm.

**The methodological point, and it is the same one as F-92.** An efficiency
change altered the dependent variable by a factor of three and sat unexamined for
eleven days because it was filed under performance. **Every change to the prompt
is a change to the experiment, including the ones adopted for speed.** The
improvement ledger below now carries engagement for every entry that has it.

### F-94 — WHERE a post lands beats WHAT the post is. Slot position is worth OR 2.15 after controlling for the ranker's own score, and it replicates 9/9

**The question.** Every exposure record carries `feed_position`. Nine months of
analysis has treated it as a nuisance to stratify away -- `exposure_model.py`
stratifies by (agent, feed slot) precisely to remove it. Nobody had estimated
it. It turns out to be the same order of magnitude as the headline finding.

**Raw, discovery tier only, 9 control runs, 25,788 first-exposures:**

    slot  0   17.0 %        slot  6    3.7 %
    slot  1   10.9 %        slot  7    3.1 %
    slot  2    6.8 %        slot  8    2.8 %
    slot  3    5.8 %        slot  9    2.1 %
    slot  4    5.3 %        slot 10    1.7 %
    slot  5    4.2 %        slot 11    2.3 %

**A ten-fold spread from top to bottom of a single feed, within one tier.**

**The design.** Post fixed effects remove "some posts are simply better". The
remaining worry is that position encodes personalised affinity: a post at slot 0
for you and slot 9 for me may differ because the ranker predicts you will like
it more. Conditioning on the ranker's own SCORE as well as the post removes
exactly that. The identifying variation is that two agents can see the same post
at the same predicted relevance and still land at different slots, because each
agent's feed has different competition.

| stratification | OR | 95 % CI |
|---|---|---|
| post | 2.47 | — |
| post x score decile | 2.45 | [2.02, 2.98] |
| **post x score decile, discovery tier only** | **2.15** | **[1.75, 2.64]** |
| agent x score decile | 2.65 | [2.25, 3.11] |

**Controlling for score HARDER does not weaken it.** 5 / 10 / 20 / 40 / 80 score
bins give 2.09 / 2.13 / 2.31 / 2.21 / 2.53. If position were a proxy for
predicted relevance the effect would decay as the control tightens. It does not
move.

**Replication.** Positive in **9/9** runs, individually significant in 7/9:
1.99, 3.18, 2.51, 2.04, 2.19, 1.63, 2.18, 1.46, 3.36.

**Why the design works better than expected.** Spearman rho between score and
position inside the discovery tier is only **-0.338**, and the same post lands
at positions with a median spread of **2.88 slots** across agents. The feed is
not a sorted list of scores -- recency scaling and tier backfill scramble it --
so position carries a large quasi-random component. This is closer to a natural
experiment than a regression control.

**What it means, stated against the published result.** Connection beats content
at OR 3.07 [2.76, 3.42] (F-92). Position beats relevance at OR 2.15 [1.75,
2.64], measured on the same runs, inside one tier, after conditioning on the
ranker's own judgement. **Roughly 70 % of the headline effect, from a variable
the analysis was designed to erase.**

**The tier confound, handled.** The three-tier feed puts network content at slot
0 (16.8 % of slot-0 exposures are network; every slot from 8 down is 100 %
discovery), so pooled position and source are partly the same variable. The
discovery-only row is the one to quote. Network-tier exposures have almost no
within-post position variation and contribute nothing.

**INDEPENDENT REPLICATION, added the same night.** The ten pre-terse-prompt
runs were put through the identical specification. They are a different
configuration in three ways at once -- temperature 0.9 for six of them, full tool
docstrings, persona-first prompt ordering -- and they engage at 2.71 % against
6.08 %, less than half the rate.

| runs | OR, discovery x post x score decile | 95 % CI | strata | positive |
|---|---|---|---|---|
| new prompt (9) | 2.15 | [1.75, 2.64] | 475 | 9/9 |
| **old prompt (8)** | **1.99** | **[1.50, 2.64]** | 225 | **8/8** |

**THIRD CONFIGURATION, final.** The seven sweep runs are a different persona
file in six of seven cases, a different round count (7 not 15) and a much lower
base rate (1.67 % engagement). Computed across all seven now that the sweep is
complete:

| configuration | runs | OR | 95 % CI | strata |
|---|---|---|---|---|
| new prompt, reddit | 9 | 2.15 | [1.75, 2.64] | 475 |
| old prompt, reddit | 8 | 1.99 | [1.50, 2.64] | 225 |
| **sweep, 7 rounds** | **7** | **1.48** | **[1.08, 2.04]** | 173 |

**The preliminary figure was 2.26 on the first four runs and fell to 1.48 on all
seven.** That is recorded rather than quietly replaced: an interim estimate on a
third of the data moved by a third once the rest arrived, which is what small
numbers of informative strata do. The sweep contributes 173 strata against the
bank's 475, because seven short rounds at 1.67 % engagement produce few
comparisons.

**The effect still replicates, more weakly.** The interval excludes 1, and the
raw gradient is intact: **5.34 % at slot 0 against 0.55 % at slot 11**, a ten-fold
spread. Positive in 5 of 7 runs; `sweep_a75` returns 0.94 and `sweep_a12` has too
few strata to estimate at all.

**Twenty-four runs across three configurations and two persona files.** The
sweep's point estimate is the lowest of the three and the honest summary is a
range of roughly **1.5 to 2.2**, not a single number.

**Seventeen of seventeen runs positive across two configurations**, with point
estimates 2.15 and 1.99 and heavily overlapping intervals. The raw gradient
replicates too, 5.48 % at slot 0 against 0.88 % at slot 11 -- a shallower spread
than the new prompt's ten-fold, which is what a halved base rate predicts.

This is the F-92 pattern deliberately repeated: **a result measured on a
different prompt at a different temperature is worth more than the same result
measured twice the same way.** Position was not an artefact of the terse prompt,
and it was present in every run this project has ever done.

**What is NOT established.** This is observational within a run, not an
intervention. The clean test is a shuffled-slot arm: rank as normal, then
randomise the order before display. If the effect is attention rather than any
residual relevance the ranker knows about, engagement should flatten across
slots and total engagement should fall. That is one run.

**Method note.** Found while answering a question about the efficiency work, on
data that had been sitting in the package for two days. Same lesson as F-92,
third instance: **the data we already have has not been fully asked.**

### F-95 — Memory does not CREATE the connection effect, it AMPLIFIES it. Removing it cuts OR 3.07 to 2.05

The three `--fresh-context` runs were produced for the F-88 efficiency A/B and,
exactly as F-92 records happening once already, were never put through
`exposure_model.py`. They are 18,144 fresh exposures on an arm nobody had asked
a scientific question of.

| arm | n | network vs discovery, primary | engagement |
|---|---|---|---|
| control | 9 | **3.07** [2.76, 3.42] | 6.94 % |
| fresh-context | 3 | **2.05** [1.56, 2.68] | 2.30 % |

Primary is the published specification unchanged: Mantel-Haenszel stratified by
(agent, feed slot), slots 0-4. **The intervals do not overlap.**

**What it means.** An agent that cannot remember previous rounds still engages
more with posts from accounts it follows -- positive in 3/3 runs, individually
significant in 2/3, at 1.09 / 3.36 / 2.39. So the effect does not require
memory. But it is about a third weaker without it.

That is the interesting shape. The follow relationship is visible in the prompt
every turn regardless of memory, so a purely stimulus-driven agent should show
the full effect. It does not. **Something about accumulated history makes an
agent treat its own connections as more worth acting on**, and that is a claim
about what memory does socially rather than computationally.

**Caveats that must travel with it.** n=3 against n=9. The fresh-context arm
engages at a third the rate, so its estimate rests on far fewer events and its
per-run spread is wide. The fof contrast collapses entirely under memory removal
(0.64 [0.19, 2.20], 45 strata) and should not be read at all at this n.

**Why it matters for what to do next.** It converts the memory-window proposal
in the research agenda from "how fast does it run" into "what does memory do to
the phenomenon", and it gives that study a second dependent variable it did not
have. The dose-response now has two endpoints already measured.

#### B-28 — I ran a six-point sweep at a 4,096-token context and called the result a scaling law

**What happened.** Ollama was started at 21:24 with `OLLAMA_NUM_PARALLEL=4` and
**no** `OLLAMA_CONTEXT_LENGTH`. Ollama 0.24's default is **4,096 tokens per
slot**. The prompt is ~2,733 tokens before any transcript, and the transcript
pushes it past 4,096 within one round. Every run in the sweep was truncated, and
**the feed sits at the end of the prompt**, so the feed is what was cut.

Measured directly against the running server:

    prompt sent  ~2,093 tok  ->  reports  2,109
    prompt sent  ~6,571 tok  ->  reports  4,096   TRUNCATED
    prompt sent ~17,932 tok  ->  reports  4,096   TRUNCATED

**The scientific proof.** `sweep_a36_reddit` is the same personas, prompt,
temperature, model and seed as the control bank:

| run | context | engagement |
|---|---|---|
| `sweep_a36_reddit` | 4,096 | **2.50 %** |
| `ctx8192_a36_reddit` (re-run) | 8,192 | **5.16 %** |
| `bank_r5` | larger | 5.88 % |
| `bank_r1` | larger | 6.83 % |

**Engagement halved because the agents could not see their feeds** -- while the
wall clock IMPROVED, which is why it read as a clean scaling result for four
hours and produced two findings that had to be withdrawn.

**The re-run closes it.** At 8,192 the reddit configuration reproduces the bank on
cost (769 s at round 4 against 793) and restores the three-round ramp exactly.

**Two caps, two ramp lengths, one mechanism.** At 4,096 the window fills inside
one round and the curve is flat from round 1. At 8,192 it fills over three rounds.
**This is the strongest confirmation yet that the ramp is context accumulation**
(F-86) rather than anything else, arrived at by accident.

**Cause: mine, and this log warned about it.** F-65 says *"anyone raising
`NUM_PARALLEL` must raise `OLLAMA_CONTEXT_LENGTH` with it."* I read that finding
the same night and made the same class of mistake in the other direction.

**Now enforced in code.** `server_state.py` (+8 tests) reads `/api/ps`, refuses
below 8,192, and writes `server_context_length` into every manifest. Wired into
`run_simulation.py` (aborts) and `check_deps.py` (now 8 checks). Override with
`OASIS_ALLOW_SMALL_CONTEXT=1`.

    OLLAMA_NUM_PARALLEL=4 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=24h ollama serve

#### F-97 and F-98 — BOTH WITHDRAWN. Recorded so nobody re-derives them

Written between 02:00 and 03:30 on the truncated data, and both are artefacts of
B-28. Kept here because this log's value is in recording what was believed and
why it was wrong.

- **F-97 claimed the reddit bank "cost 2.2x what an identical configuration costs
  on a verified server"**, and speculated about a serialising server. Backwards:
  the bank cost more because it was doing more. **The bank was correct.**
- **F-98 claimed the three-round ramp "does not exist on a verified server"**,
  retiring F-81 as family-specific and breaking F-86's generality. Also
  backwards: the ramp vanished because the window filled in one round. **F-81 and
  F-86 are vindicated.**

Two further claims from the same hours are withdrawn: an engagement-cost "law"
(refuted by its own data at R^2 0.595), and an assertion that the server
hypothesis was "killed by no discontinuity at any session boundary" (never
verified -- server state was not recorded for any earlier run).

**The pattern in all four: a mechanism proposed after two or three families
lined up, without checking whether the variable moves WITHIN a family where
everything else is fixed.**

### F-96 — SETTLED. Cost is LINEAR in agent count (exponent 0.991) at 22.7 s per agent-turn. F-91 was right

**Final measurement.** Twitter personas, `--semaphore 4`, context verified at
8,192 per slot, plateau = mean of rounds 4-6:

| agents | plateau | sd | per agent-turn |
|---|---|---|---|
| 12 | 276.0 s | 9.7 | 23.00 s |
| 24 | 532.3 s | 18.0 | 22.18 s |
| 36 | 824.8 s | 26.7 | 22.91 s |

    log-log fit:  plateau proportional to agents^0.991     R^2 = 0.9988
    per agent-turn: mean 22.70 s, sd 0.45

**Cost is linear in agent count.** Not sublinear, not superlinear.

#### This corrects the first version of F-96, which claimed 1.081

That version was measured on the truncated sweep. When B-28 was found I kept the
exponent and argued *"truncation applies equally at every world size, so the
shape survives -- read the exponent, not the level."*

**Withdrawn.** Truncation does **not** apply equally: a larger world produces
more content per round, so its prompts reach the cap sooner and lose
proportionally more. The bias is size-dependent, which is precisely what inflates
an exponent. **1.081 truncated against 0.991 correct -- about 9 %.**

*"The confound applies to every point, so the shape is safe"* is an argument, not
a measurement. **A shape claim needs its own clean data.**

#### F-91 is CONFIRMED, not superseded

F-91 reported **0.99** from a 36-agent and a 99-agent run, and I wrote that F-96
superseded it and later that it was "computed on a ramp round of a degrading
run". Both withdrawn. **A clean three-point sweep at verified context returns
0.991 -- F-91's figure to three decimals.** Its method was thinner and its
99-agent run was genuinely still climbing, but its answer was right.

**F-82's 0.88 remains superseded**; it came from ramp rounds.

#### Planning numbers, measured rather than inferred

    wall clock  ~=  agents x rounds x 22.7 s     after a three-round ramp (F-81)

    36 x 15     ->  ~170 min   <- reproduces the nine-run bank exactly
    99 x 15     ->  ~8.7 hours
    1000 x 1000 ->  ~263 days

**The cost model and the historical record now agree**, which is the check that
matters.

#### B-30 — Three edits reported success and changed nothing, and the artifact was published self-contradicting for forty minutes

**Symptom.** Reading the published page end to end at 08:47 found it asserting
both an exponent of 1.081 and 0.991 in its own headline figures; carrying the
**withdrawn** F-98 as "Law 1 -- the ramp was an artefact" while Law 2 and the
reproducibility section described the opposite; and a runbook still instructing
`OLLAMA_NUM_PARALLEL=4 ... ollama serve` with no `OLLAMA_CONTEXT_LENGTH` --
**the exact command that caused B-28**, on the page that documents B-28.

**Cause.** Section replacements matched on a raw `·` while the file contained
`&middot;`, because an earlier edit had itself introduced the entity. The loop
found no match, copied every line through, and printed its unconditional success
message. Three separate rewrites -- Law 1's correction, Law 2's correction, and
one headline figure -- silently did nothing, and I reported each as done.

**Why it survived several checks.** The HTML validator passed, because nothing
was malformed. The tag-balance check passed. `grep` for new content would have
caught it instantly and was not run. **A structural check cannot detect an edit
that did not happen.**

**Fix.** All four defects corrected and republished (v12), rebased on the live
version rather than the local file, since the two had diverged. **Rule: after any
scripted edit, grep for a string that only the NEW content contains.** An edit
that reports success is not evidence; the changed bytes are.

**Third instance tonight of the same class** -- B-27 (a label that stopped
meaning what it said), B-29 (a replacement whose blast radius nobody checked),
and now this. All three are edits whose effect was assumed rather than verified,
which is precisely the failure B-28 was about, applied to text instead of runs.

#### B-29 — I destroyed four log sections with my own edits, and only noticed two hours later

Rewriting section 0 STATUS at 05:40 replaced everything between the STATUS
heading and `### The task, as given`. F-96, F-97, F-98, B-28 and an interim note
had all been inserted into that span earlier in the night, and all were deleted.
Found at 08:00 when a `grep` for F-96 returned the STATUS summary line and no
section.

**Cause.** Repeated large-span `s[:start] + new + s[end:]` replacements against a
file whose structure was changing between edits. Several of those edits also
appended their own anchor, which is how `### Immediately next` ended up
duplicated five times in one line earlier.

**Rule.** Anchor replacements to the smallest unique span that does the job, and
`grep` for the ids you expect to survive after any edit that spans more than one
section. Content restored above from the session record.

## 3d. The codebase: what is ours, what is upstream, where it lives

Added 2026-09-11. This log had ninety findings and no inventory, so a reader had
no way to know which code a finding referred to or whether it was ours to change.

**D-1 restated: upstream OASIS is never edited.** Where behaviour had to differ
we subclassed. `TimelineAgent(SocialAgent)`, `TimelinePlatform(Platform)`,
`TimelineEnvironment(SocialEnvironment)`. Two consequences that have both paid
off: upstream changes cannot silently alter our results, and any finding can be
attributed to our code or theirs without archaeology.

### Upstream (read-only)

| file | lines | role |
|---|---|---|
| `oasis/social_platform/platform.py` | 1,642 | the platform: posts, likes, follows, schema |
| `oasis/social_agent/agent_action.py` | 758 | the 22-action surface |
| `oasis/social_agent/agent.py` | 321 | one agent's turn; `max_iteration=1` lives here (F-84) |
| `oasis/social_agent/agent_graph.py` | 292 | agent collection and follow graph |
| `oasis/social_platform/channel.py` | 71 | agent-to-platform message queue |

### Ours — `examples/experiment/social_timeline/` (~9,500 lines)

**Running it**

| file | lines | role |
|---|---|---|
| `run_simulation.py` | 723 | driver; owns the manifest, the timing instrumentation and every CLI flag |
| `timeline_platform.py` | 1,017 | three-tier personalised feed + the exposure ledger. The scientific core |
| `timeline_agent.py` | 723 | persona to prompt; terse tools (F-64), shared prefix (F-80), `fresh_context` (F-87) |
| `personas.py` | 265 | deterministic selection; separability measurement |
| `embedding.py` | 147 | mean-pooled TwHIN-BERT (D-13 deviation from upstream) |
| `check_deps.py` | 317 | pre-flight; blocks a run on a serialising server (F-56) |

**Analysis**

| file | lines | role |
|---|---|---|
| `analyze.py` | 682 | database to metrics; defines `seen_and_acted` (F-71) |
| `exposure_model.py` | 441 | Mantel-Haenszel and cluster-robust logistic regression |
| `compare.py` | 328 | paired, cluster-aware run comparison |
| `dossier.py` | 848 | human-readable full-run report |
| `make_graph.py` | 1,590 | before/after follow-graph diagram |
| `noise_floor.py` | 166 | the F-35 replicate measurement |
| `export_parquet.py` | 382 | 18x compaction (D-15) |
| `build_package.py` | 327 | the handover folder; `arm` column added 09-11 |
| `eval_model.py` | 256 | 80-second model screen (F-71, F-78) |

**Tests — each exists because something failed silently**

`test_instrumentation.py` (the two bugs that produced wrong data),
`test_ranking.py` (vectorisation is bit-identical), `test_export_parquet.py`
(no value changes under compaction), `test_exposure_model.py`,
`test_compare.py`, `test_actions.py`, `test_smart_tool_loop.py`.

### Data

    data/reddit/user_data_36.json               36 personas, 9 fields each
    data/twitter_dataset/.../False_Business_0.csv   99 scraped bios
    data/social_timeline_<label>.db             one per run
    data/social_timeline_<label>.json           manifest: config + timings
    data/parquet/<label>/                       compacted, partitioned by round
    data/sim4_package/                          the handover folder

## 3e. Improvement ledger — every efficiency change, with its verdict

| change | measured | verdict |
|---|---|---|
| Terse tool descriptions (F-64, **F-93**) | **1.44x**, and engagement **2.29 % -> 6.94 %** | **adopted.** 80 % of the prompt was docstrings. The only entry here that improved the dependent variable; 2.1x data per hour |
| Vectorised ranking | **25-30x** on that phase | **adopted.** Bit-identical, gated by `test_ranking.py` |
| Two composite indexes | **260x** on that lookup | **adopted** |
| Shared prompt prefix (F-80) | **1.66x** at NP=4 | **already the default.** Believed worthless until measured |
| Parquet export (D-15) | **18x** storage | **adopted** |
| Concurrency 1 -> 4 (F-77) | **1.13x** | **adopted.** Also the memory sweet spot |
| Concurrency 4 -> 8 | not resolvable | **rejected.** 5x the variance for no mean gain |
| Concurrency 16, 32 (F-76) | 52x slower / fails | **rejected.** Memory, not compute |
| `--smart-tool-loop` (F-83/84) | **no-op** | **rejected.** Upstream already caps the loop |
| `--fresh-context` (F-87/88) | 3.07x, 1.02x yield | **rejected.** Real speed, entirely consumed by lost engagement |
| Smaller models (F-78) | 2.2-4.7x | **rejected.** All three fail the engagement gate |
| `--max-tokens` cap (F-63) | faster | **rejected.** Engagement 4.31 % -> 0.36 % |

**The pattern across twelve entries: every lever that touches what the model
says costs more engagement than it buys time.** The six adopted changes are all
changes to how the work is *packaged* — shorter prompts, better ordering,
smarter indexes, right-sized concurrency — and none of them changes a single
decision an agent makes.

## 3c. Deferred sim queue — questions the harness CANNOT answer

Raised 2026-09-08 while comparing granite4.1:8b, ornith:9b, gemma4:e2b,
gemma4:12b, qwen2.5:14b. `eval_model.py` settles tool-call rate, ENGAGED,
grounding, action mix and real tok/s in ~80 s per model. Everything below needs
a full 36-agent run and is NOT to be run without explicit permission.

| # | Question | Why the harness can't answer it | Cost |
|---|---|---|---|
| S-1 | Does ENGAGED hold over 15 rounds as the feed fills? | F-71: the proxy compresses a 500x deficit to 2.7x. Single fresh turns cannot see a deficit that compounds. | 1 run |
| S-2 | Does the model write *in persona*, or like its training domain? | The harness scores whether a call is well-formed and feed-grounded, never whether the prose is plausibly a 40-year-old ESTJ. Sharpest for `ornith:9b`, an RL-trained coding agent. | 1 run + read |
| S-3 | Do the three published findings survive a model change? | Connection-beats-content (OR 3.51), repetition-beats-both (OR 2.62) are properties of the model+feed system, not the feed alone. A new model is a new population. | 3+ runs |
| S-4 | What is the noise floor for the new model? | F-35's ~28pp is measured on llama3.1:8b ONLY. Every effect size is judged against it, so it must be re-established per model before any comparison means anything. | 5+ runs |
| S-5 | Does gemma4's thinking mode inflate output tokens at 36 agents? | Partially harness-visible (tok/s, output length), but F-60 is unambiguous: every small bench in this project overpredicted, four times running. Confirm at 36. | 1 run |
| S-6 | Real wall-clock per round at 36 agents through 8 slots | Single-stream tok/s ignores the contention that makes a 16.4 s call out of ~2.0 s of GPU work (F-67). | 1 run |

**Order if this is ever run:** S-1 first — it is the cheapest and it gates every
other question. A model that fails S-1 makes S-2 through S-6 moot, which is
exactly the sequencing that seven wasted runs on llama3.2:3b did not have.

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
