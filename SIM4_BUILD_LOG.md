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
| F-14 | **Group chat hijacks the prompt and crowds out feed engagement** | `agent_environment.py:49-53` puts `$groups_env` *before* `$posts_env`; `:40-48` is a wall of imperatives; `:118-135` renders it every turn regardless of `available_actions`. Measured in R-5 |

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

*(Entries continue as the build proceeds.)*

---

## 7. Run ledger

Every simulation run: configuration, outcome, timing. No run goes unrecorded,
including failed and aborted ones.

| Run | Stage | Config | Outcome | Wall-clock |
|---|---|---|---|---|
| R-1 | 0 | `check_deps.py`, no simulation | **PASS (but inadequate)** — TwHIN-BERT loaded (279M params, XLMRobertaTokenizerFast + BertModel, device `cpu`), embeddings non-NaN, margin `+0.0358`, Ollama reachable with `llama3.1:8b`. The margin check passed by luck; see B-1/B-2 | 29.7s total (24.6s model load incl. download) |
| R-2 | 0 | `pooler_probe.py`, 4 texts / 2 topics, run in two fresh processes | **Exposed B-1 and B-2.** Pooler weights differ per process (`sum=-6.18` vs `+6.46`); pooler margin `+0.0069` / `+0.0008`; mean-pooled margin `+0.0475` and bit-identical across processes | ~50s for both processes |
| R-6 | 2 | 8 agents, 4 rounds, **22 actions** (`--no-groups`) — controlled A/B against R-5, identical otherwise | **Behaviour gate PASSED.** action_rate **0.812** (26/32, vs R-5's 0.469 and Sim 1's ~0.89); 14 posts, **9 comments, 3 quote_posts, 1 follow**, 1 search, 1 do_nothing; 148 exposures (nearly 2x R-5). First genuine content engagement of the build. Confirms F-14 | 340.1s |
| R-8 | full | 36 agents, 12 rounds, twhin-bert, 22 actions | *(running)* | — |
| R-7 | 3 | 8 agents, 4 rounds, 22 actions, **all four fixes**, `--label stage3` | **Dynamics gate PASSED.** action_rate 0.812; **5 follow edges** (vs 1), **6 likes** (vs 0 in every prior run), 8 comments, 8/8 distinct posts (no duplicates); `source='both'` appears **live** and grows 4→5 as the graph grows; 0 agent failures | 312.7s |
| R-5 | 2 | 8 agents, 4 rounds, 27 actions, `--label stage2` | **Behaviour gate FAILED.** 0 agent failures, instrumentation clean (77 exposures), but **action_rate 0.469** (15/32 turns) vs Sim 1's ~0.89 baseline, and the action mix was `send_to_group` 6, `create_post` 6, `create_group` 2, `join_group` 1 — **zero likes, follows, comments or reposts**. Diagnosed as F-14 | 352.7s |
| R-4 | 1 | 4 agents, 2 rounds, twhin-bert, `--label stage1` | **Plumbing gate PASSED.** 0 agent failures; `rec_history`=12, `rec_candidates`=12, `round_boundary` correct (r0: 0 posts, r1: 4); every agent received a non-empty feed; own-posts correctly excluded; per-user scores genuinely differ. Exposed **B-3**. Action diversity was nil — see analysis below | 103.2s |
| R-3 | 0 | `check_deps.py`, strengthened to 6 checks | **PASS, and now a real gate.** Mean-pooled margin `+0.0475`; embedding space reproduced a baseline recorded in a *different* process to within `dw=0.00004, da=0.00002`, confirming replication is sound under D-13; pooler regression guard confirms upstream still unfixed | 4.7s (model cached) |

---

## 8. Bug ledger

Bugs found during this build — in our code or upstream — with how each surfaced.

| # | Where | Symptom | Cause | Fix | Found by |
|---|---|---|---|---|---|
| B-1 | Upstream `process_recsys_posts.py:33` | Embedding space differs on every process launch; runs not reproducible | `outputs.pooler_output` reads a pooler whose weights TwHIN-BERT's checkpoint does not contain, so they are randomly re-initialized at every load | Mean-pool `last_hidden_state` instead (D-13) | Stage 0 probe, cross-process fingerprint |
| B-2 | Same line | Interest-based ranking is barely discriminative — one process produced a within-vs-across-topic margin of `+0.0008`, i.e. noise | `tanh` saturation on a random projection compresses all cosines into ~0.88-0.97 | Same fix (D-13) | Stage 0 probe, 2-topic margin test |
| B-4 | Ours — `analyze.py` | Agents showed `engagement_rate 0.0` and `acted on: []` despite having posted real comments — genuine engagement silently missing from the ledger | Trace `info` payloads are **not uniform**: `create_comment` records only `comment_id` (no `post_id`), and `quote_post` records `quoted_id` as a **string**, which an `isinstance(..., int)` check rejects | Numeric-string coercion + a `comment_id -> post_id` lookup via the comment table | R-6 analysis: comment counts and "acted on" disagreed |
| B-5 | Ours — `make_graph.py` | Usernames rendered as `millerhospitaliâ€¦`; table text illegibly low-contrast | The HTML template is a **non-raw** Python string, so `\\u2013`-style escapes were decoded into literal non-ASCII before ever reaching the file, and mojibake appeared wherever charset was not guaranteed. Separately, `td` inherited its colour through the table instead of taking a token | Emit pure ASCII (HTML entities); set `td { color: var(--fg) }` explicitly | Browser verification before publishing |
| B-6 | Upstream `platform.py:905` + our `analyze.py` | Every `follow` was unattributed — the interaction ledger could not say who was followed | `follow` records only `{"follow_id": ...}`; the followee appears **nowhere** in the payload. Surveyed all relational actions and found each uses a different key: `unfollow`→`followee_id`, `mute`→`mutee_id`, `repost`→`reposted_id`, comment actions→`comment_id` only | Recover followee via the follow table; add the other keys; generalise the comment lookup | `test_instrumentation.py` TEST 2 |
| B-7 | Ours — `timeline_agent.py` | Agents were *always* told "you do not follow anyone yet", even holding follow edges; authors rendered as bare `agentN` | Keyed on `self.agent_id`, which is **camel's UUID**; the integer is `social_agent_id` (`agent.py:71`). Every lookup silently matched nothing. Separately, `sign_up` leaves `user_name` NULL and puts the handle in `name` | Use `social_agent_id`; `COALESCE(user_name, name)` | Reading the rendered prompt in the promptcheck run |
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
| Q-8 | Why do agents post but rarely like or follow? Note the prompt's closing line reads "Do not limit your action in just `like` to like posts" (`agent_environment.py:51-53`) — awkward enough that an 8B model may read it as an instruction *against* liking | Open; testable by rewording prompt content only, which D-2 permits |
| Q-7 | Is a `+0.0475` within-vs-across margin enough dynamic range for personalization to visibly shape feeds, once multiplied by recency decay? | Stage 3 — recency may dominate content similarity |
| Q-2 | Does the 27-action set degrade 8B tool-calling vs. Sim 1's ~32/36 baseline? | **Answered: yes, badly.** 0.469 with 27 actions vs 0.812 with 22. Cause was not tool count alone but the group-chat prompt hijack (F-14). Resolved by D-14 |
| Q-3 | Do agents actually form follows, given they see only counts and never identities (F-11)? | **Partially.** Exactly 1 follow in 32 agent-turns (R-6) — non-zero, so it is possible, but far too sparse for a meaningful before/after graph. The likeliest cause is F-11: agents are told only *how many* people they follow, never *who*, so a follow target must be inferred from author ids in the feed. Open, and now the build's main question |
| Q-4 | Do 2-member groups (de-facto DMs) emerge at all (D-7)? | **Yes, but at a cost.** R-5 produced 2 groups, 3 members and 6 group messages unprompted — so they do emerge. But the same actions suppress feed engagement (F-14/D-14), so studying DMs and studying timelines are in direct tension on an 8B model. Reported, not engineered around |
| Q-5 | Does F-12's index-base conflict affect TWHIN, leaving any agent with an empty feed? | **Answered: no.** Every agent received a non-empty feed in R-4 and R-6. Avoided by keying on `agent_id` explicitly (F-13) rather than reproducing upstream's positional indexing |
