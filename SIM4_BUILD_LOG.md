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

## 0. STATUS — read this first when resuming

*Last updated 2026-09-01. Update this section at the end of every working session.*

**Branch `social-timeline-sim`. Four overnight replicates (R-21..R-24) completed
2026-09-02 06:24 and are analysed; the project now has **9 three-tier runs**.
Nothing is mid-flight; no run in progress.**

### The three results

1. **Connection predicts engagement; content does not.** Over **9 runs / 54,444 exposures**, holding agent *and* feed slot
   fixed: `network` vs `discovery` **OR 3.51** [3.06, 4.04], significant in
   **9/9 runs**. `fof` vs `discovery` **OR 2.34** [1.64, 3.35], significant in
   **3/7** runs individually — stronger than before but still **suggestive,
   not established**. Independently replicated under a structurally different
   feed builder at **OR 5.00** [3.83, 6.52].
2. **Repetition beats both content and freshness.** Engagement
   rises monotonically with the number of times an agent has already seen a
   post: **2.05% → 4.17% → 5.75% → 6.95% → 8.19%** (2.05% → 4.94% in absolute
   terms, a 2.89 pp gap). Within-feed **OR 2.624** [2.184, 3.153], p=7.4e-25;
   survives adding feed slot (2.454) and replicates in the network tier (1.643),
   whose feed never touches the ranking score. **Significant in 8/9 runs —
   `v9_feedback` is the lone null at 0.89 — and in 2/3 tiers — `fof` is null at
   1.222.** Consistent, not universal. **One supporting argument weakened: restricted to
   first sightings only, the stale-post advantage used to reverse significantly
   and is now p=0.097 — report it as directional only, never as a reversal.**
   Observational, not randomised — the ranker chose what to repeat, we did not.
   The designed test (deliberately re-injecting a fixed post set on a schedule)
   is still the top open item.
3. **The cross-run noise floor swamps every prompt intervention tried.** Pure run-to-run SD for posting share is **~28-31 pp**; the four
   interventions moved it 3-5 pp against a detectable minimum of 14.3 pp. They
   were unfalsifiable at this scale, not merely unsupported. **Confirmed across
   all 15 pairs of six identical runs, not just the original pair.**

*Every finding, bug, decision, run and open question also has an id (`F-43`,
`B-15`, `D-5`, `R-21`, `Q-14`). Ids are for searching this file — each is its own
`####` heading whose title states the claim, so searching an id lands you on a
sentence, not a cross-reference.*

### RETRACTED — do not repeat this claim

**F-38, "TwHIN similarity is anti-predictive of engagement (OR 0.305 per unit
cosine)", is wrong and is retracted by F-42.** The variable was
`rec_history.score` = `sim * recency`, not cosine. Cosine alone is **null**:
OR 1.544 [0.588, 4.054], p=0.38. The correct statement is *similarity has no
detectable effect*. **The write-up artifact was corrected on 2026-09-01** — section 03 now carries the
retraction, section 04 the repeat-exposure result, and the forest plot shows
similarity in neutral grey spanning the null line.

### Done

- Instrumentation, three-tier feed, informed-action gate, 22-action surface.
- 20 runs (see §7). 9 analysed runs in the data artifact.
- `analyze.py` (per-run), `dossier.py` (~28k-line transcripts), `make_graph.py`
  (artifact), `compare.py` (cross-run, paired), `exposure_model.py`
  (within-run), `recency_check.py` (the F-42/F-43 decomposition).
- Test gates for all statistics: `test_compare.py` 16/16,
  `test_exposure_model.py` 12/12, plus `check_deps.py`, `test_actions.py`,
  `test_instrumentation.py`.
- Findings F-1..F-43, bugs B-1..B-14, decisions D-1..D-14 — all recorded below.

### Next, in priority order

| # | Task | Cost | Why |
|---|---|---|---|
| 1 | **A designed repeat-exposure run** (Q-15): re-inject a fixed set of posts at controlled intervals | ~1 run (2 h) | Still the top item. F-44 made repeat exposure the project's best-evidenced effect (OR 2.62, 8/9 runs) but more replicates cannot make it experimental — only assignment can |
| 2 | Optional: a `follow`-targeted designed experiment | ~1 run | F-36 — `follow` has ICC 0.000, ~35 agent-pairs for 5 pp |
| 3 | Open, unexplained: 14 of 21 actions never fire | unscoped | Limits any claim about the action surface being exercised |
| 4 | Open, unexplained: F-24, ~32% of posts echo the author's own bio | unscoped | Per F-35 do **not** attack it with prompt tweaks |

**Do not** run another prompt-intervention experiment at 36 agents. F-35 shows it
cannot resolve anything. Judge any future change against **baseline**, never
against the previous run, and use `compare.py` so the correction and the MDE are
reported automatically.

### Deliverables

- Write-up for the professor (corrected 2026-09-01): https://claude.ai/code/artifact/55d7c5a5-4a69-406c-bc4f-8f14a94f710b
- Field guide — step-by-step explainer of the whole build: https://claude.ai/code/artifact/b878972f-ab95-4d0c-ba12-e1b1684467ba
- 9-run data explorer: https://claude.ai/code/artifact/732d1879-2f3b-49fe-83f6-0cf4b55c87c3
- `data/social_timeline_exposure_model.txt` — the engagement analysis
- `data/social_timeline_noise_floor.txt` — the replicate/noise-floor analysis
- `data/social_timeline_recency_check.txt` — the F-42/F-43/F-44/F-45 decomposition
- `data/social_timeline_noise_floor_6runs.txt` — Q-14, the six-run noise floor
- `data/social_timeline_<label>_DOSSIER.txt` — per-round transcripts per run

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
`rec_history.score`, which is `sim * recency` (`timeline_platform.py:365` writes the
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


**Evidence.** The shield works. Reach flows through the graph, and it is not merely an
artefact of network posts being shown first

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

Living list. Every file this build creates or modifies, and why.

All simulation and analysis code lives in `examples/experiment/social_timeline/`;
that prefix is dropped from the entries below. Paths outside it are given in
full.

### Created

#### `docs/superpowers/specs/2026-08-24-social-timeline-design.md`

**Purpose.** Design spec

**Status.** Committed `2b82487`

#### `SIM4_BUILD_LOG.md`

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

**Question.** Why do 14 of the 21 available actions never fire? No `dislike`,
`unfollow`, `mute`, `report`, `search` or `trend` in any run. `test_actions.py` proves
they work mechanically, so it is a model choice — but an unexplained one

**Status.** **Open.** Limits any claim that the action surface is exercised

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

