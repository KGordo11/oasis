# Simulation 4 — Social Timeline: Build Log

**Purpose of this document.** A complete, running record of everything done to build
Simulation 4: every file created or modified, every source consulted, every decision
and why it was made, every bug found and how, and every run with its configuration and
outcome. It is written so that anyone (including future-me) can reconstruct the entire
build without having to ask a question or guess at a rationale.

**Related documents**
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
creator (`platform.py:1497-1527`); there is no recipient field anywhere in the schema.
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

**D-12 — Work on a branch.**
`social-timeline-sim`, branched from `main`. Prior sims committed directly to `main`;
this build is large enough to warrant isolation, and `main` stays clean.

---

## 4. Findings from source investigation

Full detail with rationale lives in spec §2. Condensed index:

| # | Finding | Evidence |
|---|---|---|
| F-1 | Hot-score gives every user an identical feed | `recsys.py:257` — `[top_post_ids] * len(rec_matrix)` |
| F-2 | The follow graph reaches the feed, but only for non-REDDIT recsys | `platform.py:280-303` — `JOIN follow ON post.user_id = follow.followee_id` |
| F-3 | **`RecsysType.TWITTER` silently returns random recommendations** | `recsys.py:39` (`model = None`), assigned only at `:282` in a different function; `:749` falls through to `random.random()` with no error |
| F-4 | Exposure history is destroyed every round | `platform.py:383` — `DELETE FROM rec` |
| F-5 | Default feed is ~5 posts, recsys ranks only a top-2 pool | `env.py:82-84` |
| F-6 | Group chat is open-join public rooms, not DMs | `platform.py:1497-1527`; no recipient field in `group_message.sql` |
| F-7 | TWHIN keeps state in module globals across calls | `recsys.py:436-437`, cleared only by `reset_globals()` at `:124` |
| F-8 | `enable_like_score=True` hits `pdb.set_trace()` in exception handlers | `recsys.py:564, 579` — would hang a headless run indefinitely |
| F-9 | TWHIN recency score goes non-finite past ~171 timesteps | `recsys.py:469-472` — `log((271.8 - age)/100)`; source comments a ~90 ceiling |
| F-10 | `generate_twitter_agent_graph` discards `following_agentid_list` | `agents_generator.py:614-649` |
| F-11 | Agents see only follower/following **counts**, never identities | `agent_environment.py:68-101`, both marked `# TODO` upstream |
| F-12 | Two conflicting index bases for the `rec` matrix | `database.py:281` inserts 1-based; `platform.py:390` inserts 0-based |
| F-13 | Every table's `user_id` column actually stores **agent_id**; only the `user` table has both | `platform.py:407` — `user_id = agent_id`, repeated in every action |

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

Living list. Every file this build creates or modifies, and why.

### Created

| Path | Purpose | Status |
|---|---|---|
| `docs/superpowers/specs/2026-08-24-social-timeline-design.md` | Design spec | Committed `2b82487` |
| `SIM4_BUILD_LOG.md` | This document | In progress |
| `examples/experiment/social_timeline/embedding.py` | Mean-pooled TwHIN-BERT embeddings (D-13). Exists because upstream's `pooler_output` path is non-deterministic and near-non-discriminative (B-1/B-2) | Working |
| `examples/experiment/social_timeline/timeline_platform.py` | `TimelinePlatform(Platform)`: implements the ranking, creates and writes `rec_candidates` / `rec_history` / `round_boundary`, asserts the algorithm ran, enforces DM privacy | Working (R-4) |
| `examples/experiment/social_timeline/timeline_agent.py` | `TimelineAgent` (per-agent exception isolation) and the persona→agent-graph generator, with zero initial follow edges (D-10) | Working (R-4) |
| `examples/experiment/social_timeline/run_simulation.py` | Driver: 27-action set, all-`LLMAction` rounds, run manifest with exact config, timings, counters and action tallies | Working (R-4), B-3 fixed |
| `examples/experiment/social_timeline/check_deps.py` | Stage 0 gate: 6 checks — torch devices, TwHIN-BERT loads, embeddings discriminate across two topics, embedding space reproduces a baseline recorded in a *different* process, upstream pooler regression guard, Ollama reachable | **Strengthened and passing** (R-3). Original 3-text single-process version passed by luck and missed B-1/B-2 |

### Modified

*(none yet — D-1 requires that `oasis/` stay untouched)*

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

*(Entries continue as the build proceeds.)*

---

## 7. Run ledger

Every simulation run: configuration, outcome, timing. No run goes unrecorded,
including failed and aborted ones.

| Run | Stage | Config | Outcome | Wall-clock |
|---|---|---|---|---|
| R-1 | 0 | `check_deps.py`, no simulation | **PASS (but inadequate)** — TwHIN-BERT loaded (279M params, XLMRobertaTokenizerFast + BertModel, device `cpu`), embeddings non-NaN, margin `+0.0358`, Ollama reachable with `llama3.1:8b`. The margin check passed by luck; see B-1/B-2 | 29.7s total (24.6s model load incl. download) |
| R-2 | 0 | `pooler_probe.py`, 4 texts / 2 topics, run in two fresh processes | **Exposed B-1 and B-2.** Pooler weights differ per process (`sum=-6.18` vs `+6.46`); pooler margin `+0.0069` / `+0.0008`; mean-pooled margin `+0.0475` and bit-identical across processes | ~50s for both processes |
| R-4 | 1 | 4 agents, 2 rounds, twhin-bert, `--label stage1` | **Plumbing gate PASSED.** 0 agent failures; `rec_history`=12, `rec_candidates`=12, `round_boundary` correct (r0: 0 posts, r1: 4); every agent received a non-empty feed; own-posts correctly excluded; per-user scores genuinely differ. Exposed **B-3**. Action diversity was nil — see analysis below | 103.2s |
| R-3 | 0 | `check_deps.py`, strengthened to 6 checks | **PASS, and now a real gate.** Mean-pooled margin `+0.0475`; embedding space reproduced a baseline recorded in a *different* process to within `dw=0.00004, da=0.00002`, confirming replication is sound under D-13; pooler regression guard confirms upstream still unfixed | 4.7s (model cached) |

---

## 8. Bug ledger

Bugs found during this build — in our code or upstream — with how each surfaced.

| # | Where | Symptom | Cause | Fix | Found by |
|---|---|---|---|---|---|
| B-1 | Upstream `process_recsys_posts.py:33` | Embedding space differs on every process launch; runs not reproducible | `outputs.pooler_output` reads a pooler whose weights TwHIN-BERT's checkpoint does not contain, so they are randomly re-initialized at every load | Mean-pool `last_hidden_state` instead (D-13) | Stage 0 probe, cross-process fingerprint |
| B-2 | Same line | Interest-based ranking is barely discriminative — one process produced a within-vs-across-topic margin of `+0.0008`, i.e. noise | `tanh` saturation on a random projection compresses all cosines into ~0.88-0.97 | Same fix (D-13) | Stage 0 probe, 2-topic margin test |
| B-3 | Ours — `run_simulation.py` | `final_counts` all `None`, `action_tally` returned `Cannot operate on a closed cursor` | Both were computed *after* `env.close()`, which closes the DB cursor (`platform.py:143-144` on `ActionType.EXIT`) | Read them inside the `try`, before `close()` | R-4 (stage 1) |

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

| # | Question | Status |
|---|---|---|
| Q-1 | Does TwHIN-BERT download and embed acceptably on CPU? | **Answered.** Yes — 279M params, loads in ~25s, embeds 4 texts in ~0.1s. But only usable with the D-13 mean-pooling fix; as shipped it is non-deterministic and near-non-discriminative (B-1/B-2) |
| Q-6 | How much does the D-13 mean-pooling deviation change results vs. upstream-exact? | Measurable via the comparison flag once the engine runs |
| Q-7 | Is a `+0.0475` within-vs-across margin enough dynamic range for personalization to visibly shape feeds, once multiplied by recency decay? | Stage 3 — recency may dominate content similarity |
| Q-2 | Does the 27-action set degrade 8B tool-calling vs. Sim 1's ~32/36 baseline? | Stage 2 gate |
| Q-3 | Do agents actually form follows, given they see only counts and never identities (F-11)? | Stage 2 gate — material to D-10 |
| Q-4 | Do 2-member groups (de-facto DMs) emerge at all (D-7)? | Empirical, reported either way |
| Q-5 | Does F-12's index-base conflict affect TWHIN, leaving any agent with an empty feed? | Stage 1 gate |
