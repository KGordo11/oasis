# Social Timeline Simulation — Design

**Date:** 2026-08-24
**Status:** Approved design, pending implementation
**Context:** Simulation 4 in the OASIS project. Follows Sim 1 (reasoning capture),
Sim 2 (herd behavior), Sim 3 (iAgent shield). See `PROJECT_LOG.md`.

---

## 1. Goal

Turn the OASIS simulation from a narrow up/downvote experiment into something that
behaves like a real social media app: agents with full personalities acting freely
over many turns, each with their own personalized timeline, discovering each other
through an algorithm and through their social graph — and instrumented finely enough
to reconstruct, per agent, exactly what they saw, what they ignored, what they did,
to whom, how often, and why.

Success is measured by the questions we can answer afterwards, not by any single
headline finding:

- Who was connected before, who is connected after, and what rewired in between?
- Whose posts reached whom, and by which mechanism?
- Who interacted with whom, how many times, and through which action types?
- Which posts did an agent see and act on, see and ignore, or never see at all?

The motivating scenario, in the user's words: *user 1 is friends with user 2, user 2
is friends with user 4, user 2 posts something about user 4, user 1 sees it, and user
1 may or may not interact with user 4 later — depending on how often user 1 sees user
4 and whether the content matches what user 1 likes.*

That scenario is the acceptance test for the design.

---

## 2. Key findings from reading the OASIS source

These drove every decision below. All verified against the code, not the README.

### 2.1 The two recommendation algorithms create fundamentally different worlds

| | Hot-score (`REDDIT`) | Interest-based (`TWHIN`) |
|---|---|---|
| Per-user feed | No — `[top_post_ids] * len(rec_matrix)` (`recsys.py:257`) gives every user a byte-identical feed | Yes, genuinely personalized |
| Interest matching | None | TwHIN-BERT embedding cosine, profile vs. post |
| Interests evolve | No | Yes — appends the user's latest post to their profile (`recsys.py:509-520`) |
| Recency decay | Yes | Yes — log decay on post age |
| Follow graph reaches feed | **No — explicitly skipped** (`platform.py:280`) | Yes — injects followees' posts |
| Supports the motivating scenario | **Impossible** | Yes |

Hot-score produces one shared global timeline — a broadcast world with no
personalization and no social graph. It cannot satisfy the multiple-timelines
requirement.

**Decision: TWHIN (interest-based) is the algorithm.** Hot-score is retained only as
an optional contrast condition for a later comparison run, not part of the primary
build.

### 2.2 The feed is a union of two sources

Under any non-REDDIT recsys, `refresh()` builds the feed from:

1. **Algorithmic** — up to `refresh_rec_post_count` posts sampled from that user's
   `rec` table rows, which the recsys populated.
2. **Social** — the top `following_post_count` posts authored by people the user
   follows, ordered by `num_likes` (`platform.py:285-303`, a
   `JOIN follow ON post.user_id = follow.followee_id`).

This union is what makes the follow graph causally matter, and it is why the
before/after graph diagram is meaningful rather than decorative. Under REDDIT recsys
this second source is skipped entirely.

### 2.3 `RecsysType.TWITTER` is silently broken — avoid it

`RecsysType.TWITTER` dispatches to `rec_sys_personalized_with_trace`, which scores
posts using a module-global `model` that is **never initialized on that code path**
(`recsys.py:39`; only assigned at line 282, inside a different function). When
`model is None` the function falls through to `random.random()` (`recsys.py:749`)
and returns a **uniformly random feed with no error raised**.

Using it would have produced a dataset labelled "interest-based recommendation" that
was in fact a random number generator. This is the same fail-open failure class as
Sim 3's shield. It is the direct justification for requirement §4.3 below: the run
must *assert* that the intended algorithm actually executed.

`DefaultPlatformType.TWITTER` maps to `recsys_type="twhin-bert"` (`env.py:81`), not
`"twitter"`, so the default Twitter platform uses the correct, well-implemented TWHIN
path. Only the explicit `RecsysType.TWITTER` value is affected.

### 2.4 Exposure history is destroyed every round

`update_rec_table()` runs `DELETE FROM rec` on every refresh (`platform.py:383`).
The `rec` table is therefore a snapshot of the current round only. There is no record
anywhere of what any agent saw in any prior round.

This makes "what did they see / not see / see and ignore" — the single most important
analysis requirement — **currently unrecoverable**. Fixing it is the core
instrumentation task (§4.2).

### 2.5 The default feed is far too small

`env.py:82-84` sets `refresh_rec_post_count=2`, `max_rec_post_len=2`,
`following_post_count=3` — roughly 5 posts per refresh, and a recsys that only ever
ranks a top-2 candidate pool per user. That is not a social media feed and leaves
almost no surface for personalization to express itself. Must be raised (§4.1).

### 2.6 Group chat is not direct messaging

`create_group(agent_id, group_name)` takes only a name and creates the group with the
creator as its sole member (`platform.py:1497-1527`). There is no invite, no
recipient, no addressee anywhere in the schema. The only way in is `join_group`,
where an agent adds *itself*, and `get_group_env` shows every agent *all* groups.

Group chat is therefore an open-join public chat room — closer to a Discord server or
subreddit than a DM. True 1:1 DMs cannot be expressed through the existing action set.
See §7 for how this is handled.

### 2.7 Assorted hazards found

- **Module-global state.** `rec_sys_personalized_twh` keeps state in module globals
  (`date_score`, `t_items`, `u_items`, `user_previous_post`, `user_profiles`) that
  persist across calls and are cleared only by `reset_globals()` (`recsys.py:124`).
  Two runs in one process would silently carry stale state from the first into the
  second. **Every run must call `reset_globals()` at start.**
- **`enable_like_score=True` is a trap.** That code path contains
  `pdb.set_trace()` inside exception handlers (`recsys.py:564, 579`), which would
  hang a headless run forever waiting on debugger input. Leave it `False`.
- **Timestep ceiling.** TWHIN's recency score computes
  `log((271.8 - age) / 100)`, which goes non-finite once a post ages past ~171
  timesteps; the source comments a practical ceiling of ~90 (`recsys.py:469-472`).
  Round counts must stay well under this.
- **Off-by-one risk.** `rec_sys_personalized_with_trace` iterates
  `range(1, len(rec_matrix))` and returns `len-1` rows, which can leave the final
  agent with no recommendations. TWHIN does not appear to share this shape, but the
  smoke test must explicitly verify that *every* agent receives a non-empty feed.
- **TwHIN-BERT is not cached locally.** `Twitter/twhin-bert-base` (~560MB) will be
  downloaded on first use, and `load_model` only checks for CUDA — on this Mac it
  runs on **CPU**, not MPS.
- **`generate_twitter_agent_graph` ignores the social network.** It reads the profile
  CSV but uses only `user_char`, `username`, and `description`, never the
  `following_agentid_list` column (`agents_generator.py:614-649`). Using it yields an
  empty initial follow graph. `generate_agents` (line 34) does build the network.

---

## 3. Design principles

1. **Zero diff to `oasis/`.** Everything lives in a new experiment folder, using
   subclassing — the pattern established by `ShieldAgent` in Sim 3. Sim 1 Attempt 1
   proved that editing shared engine files breaks things.
2. **Never touch the tool-call response schema.** Sim 1 Attempt 1 broke tool-calling
   completely (0/36 actions performed) by altering agent-facing structure. Prompt
   content and platform internals are fair game; the action/tool schema is not.
3. **No manual actions.** Every agent acts only through `LLMAction()`, every round,
   driven entirely by its own persona. No scripted posts, no puppeted behavior.
4. **Fail loud, not open.** Sim 3's shield silently failed open ~12.5% of the time and
   polluted its own results. Any degradation of the recommendation algorithm must
   raise, not silently substitute randomness.
5. **State the algorithm precisely.** The run must record exactly which algorithm ran
   with exactly which parameters, and assert it.
6. **Smoke test before every full run.** Established project practice; caught 2 of 3
   real bugs in Sim 3.

---

## 4. What gets built

New folder: `examples/experiment/social_timeline/`

### 4.1 `TimelinePlatform(Platform)`

A subclass overriding `update_rec_table()`. `env.py:103` already accepts a `Platform`
instance directly, so this requires no upstream change.

Responsibilities:

- Call `reset_globals()` at construction to clear TWHIN's module state.
- Delegate recommendation to upstream `rec_sys_personalized_twh` **unchanged**, with
  `enable_like_score=False`, so the algorithm remains exactly upstream TWHIN and
  stays faithfully citable.
- **Assert the algorithm actually ran** — verify the TwHIN model and tokenizer are
  loaded and that recommendations are not degenerate. Raise on failure. This is the
  §2.3 guard.
- **Snapshot exposure into `rec_history` before `rec` is wiped** (§4.2).
- Reject outsiders joining a 2-member group, so emergent DMs stay private (§7).

Feed sizing, raised from the §2.5 defaults:

| Parameter | Default | New | Rationale |
|---|---|---|---|
| `max_rec_post_len` | 2 | 30 | Candidate pool the recsys ranks per user |
| `refresh_rec_post_count` | 2 | 8 | Algorithmic posts shown per refresh |
| `following_post_count` | 3 | 4 | Posts from followees per refresh |

Roughly 12 posts per feed. Deliberately moderate rather than maximal: Sim 1
established that an 8B local model's tool-calling reliability degrades as prompts grow,
and the feed is the bulk of the prompt. Final values confirmed in the smoke test.

### 4.2 Exposure instrumentation — the `rec_history` table

The fix for §2.4. Two additive tables created by our code, never by editing `oasis/`:

```sql
CREATE TABLE rec_history (
    round      INTEGER,
    user_id    INTEGER,
    post_id    INTEGER,
    rank       INTEGER,   -- position in the ranked feed
    source     TEXT,      -- 'recsys' | 'following' | 'both'
    score      REAL,      -- cosine similarity, diagnostic
    PRIMARY KEY (round, user_id, post_id)
);

CREATE TABLE round_boundary (
    round      INTEGER PRIMARY KEY,
    started_at DATETIME
);
```

`rec_history` accumulates rather than being wiped, giving a complete per-round record
of who was shown what.

`round_boundary` makes time-travel queries trivial without a separate graph-snapshot
table: since `follow` already stores `created_at` per edge, *"the social graph as of
round K"* is simply `SELECT * FROM follow WHERE created_at <= (SELECT started_at FROM
round_boundary WHERE round = K)`. Before, after, and every round between come from one
query.

**On `score` and the "why".** Sim 1 established that an 8B model cannot reliably
narrate genuine reasoning alongside structured tool calls, so we do not ask it to and
do not treat any self-report as motive. Instead we log the mechanism: the cosine
similarity that ranked the post, and which of the two feed sources surfaced it. This
is a real, defensible answer to *why did this post reach this user* — the same answer
a real platform's "why am I seeing this?" gives. The similarity is computed by our
subclass over the same TwHIN embeddings for the (user, recommended-post) pairs already
returned; it is **diagnostic metadata only and does not alter the algorithm**.

Writes happen every round regardless of partial agent failures, so snapshots stay
complete — a direct lesson from Sim 3, where one agent's timeout crashed a whole run.

### 4.3 The driver script

- All agents act every round via `LLMAction()`. No `ManualAction` anywhere.
- Full 27-action set (§6).
- Round count configurable, held well under the ~90-timestep TWHIN ceiling (§2.7).
- Bootstraps naturally: round 1 has empty feeds, so agents mostly post; round 2
  onward has content to react to. No seeding required.
- One agent's LLM failure must not abort the round's `asyncio.gather`.
- Records the exact algorithm name and every parameter into the run log, and asserts
  the algorithm ran (§2.3, §3.5).

### 4.4 Initial social graph

The motivating scenario presumes pre-existing friendships, and the follow-injection
feed path (§2.2) only matters once follows exist. `generate_twitter_agent_graph`
would give us an empty graph (§2.7), making "before" trivially zero edges.

We therefore write a generator in the experiment folder that uses the richer Reddit
personas (`bio`, `persona`, `interested_topics` — already well-formed for embedding,
see §5) and seeds an initial follow network.

**This is world initialization, not a manual action** — it sets the starting state of
the world the way personas do, and never scripts what any agent does. Every behavior
after t=0 remains entirely agent-driven.

The seeding rule is stated explicitly as part of the algorithm: homophily-weighted
attachment (agents are likelier to start out following others with overlapping
`interested_topics`) plus a random component so the graph is not perfectly clustered.
Exact parameters recorded in the run log and in the final report.

### 4.5 Analytics

Reads the database and produces per-agent and pairwise detail:

- **Per agent:** every action taken, with type, target, round, and counts by type.
- **Exposure ledger:** for each agent — posts seen and acted on, posts seen and
  ignored, and posts never seen. This is the §4.2 payoff.
- **Pairwise interaction matrix:** who acted on whose content, how many times, by
  action type, and how many times A was exposed to B's content (the exposure-frequency
  term the motivating scenario turns on).
- **Graph deltas:** follower/following counts per round, edges added and removed.
- **Propagation traces:** paths matching the motivating scenario — A exposed to B's
  content, then later interacting with C, with the exposure count and similarity that
  preceded it.

### 4.6 Graph visualization

A self-contained Artifact: force-directed web diagram, nodes as agents, follow edges,
edge weight by interaction volume, scrubable by round with before/after as the
endpoints. No external assets.

---

## 5. Personas — MatrAIx assessment

The existing 36 personas (`data/reddit/user_data_36.json`) carry `realname`,
`username`, `bio`, `persona`, `age`, `gender`, `mbti`, `country`, `profession`, and
`interested_topics`, with genuinely topical bios (e.g. *"Passionate about hospitality
& tourism. Exploring the world one destination at a time."*).

Since the interest-based recsys embeds **bio text**, these are already in exactly the
form the algorithm consumes. MatrAIx-Persona-8B's 1,290 categorical dimensions would
have to be collapsed back into a bio sentence to be usable at all.

MatrAIx's real value is **scale and demographic diversity beyond 36 agents** (1M
personas, MIT licensed, `MatrAIx2026/MatrAIx_Persona_1M_Public_Release`). That makes
it a clean fast-follow with its own spec once this engine works — not a blocker, and
not on this build's critical path.

---

## 6. Action set — 27 actions

**Social (22):** `CREATE_POST`, `CREATE_COMMENT`, `LIKE_POST`, `UNLIKE_POST`,
`DISLIKE_POST`, `UNDO_DISLIKE_POST`, `LIKE_COMMENT`, `UNLIKE_COMMENT`,
`DISLIKE_COMMENT`, `UNDO_DISLIKE_COMMENT`, `REPOST`, `QUOTE_POST`, `REPORT_POST`,
`FOLLOW`, `UNFOLLOW`, `MUTE`, `UNMUTE`, `SEARCH_USER`, `SEARCH_POSTS`, `TREND`,
`REFRESH`, `DO_NOTHING`

**Group (5):** `CREATE_GROUP`, `JOIN_GROUP`, `LEAVE_GROUP`, `SEND_TO_GROUP`,
`LISTEN_FROM_GROUP`

**Excluded, with reasons:**

- `EXIT`, `SIGNUP`, `UPDATE_REC_TABLE` — system-internal plumbing, not user behavior.
- `PURCHASE_PRODUCT` — requires the e-commerce product table; a different experiment.
- `INTERVIEW` — a researcher probe injected from outside, not an agent's own social
  behavior. Including it would contaminate the free-behavior requirement (§3.3).

---

## 7. Direct messaging — resolution

Per §2.6, OASIS cannot express a targeted DM: there is no recipient field, and
`create_group` cannot invite anyone.

A pre-seeded 2-person group was considered and **rejected**, because seeding who talks
to whom is exactly the manual intervention §3.3 forbids. Building a custom `send_dm`
action was also rejected: it would require a new `ActionType` and a change to the
tool-call schema, which is what broke Sim 1 Attempt 1 (§3.2).

**Resolution:** the five group actions are available and agents are free to create and
join groups on their own. Analytics classifies a 2-member group as a de-facto DM and
larger ones as group chat, and both appear in the interaction graph as distinct edge
types. Whether private 1:1 conversation emerges is then a genuine empirical finding
rather than something we engineered.

**Stated limitation:** because `create_group` has no targeting, emergent true 1:1 DMs
may be rare or absent. This will be reported honestly either way, not quietly dropped.

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| Silent algorithm degradation (§2.3) | Hard assertion that TWHIN loaded and ran; fail loud |
| Stale module globals across runs (§2.7) | `reset_globals()` at every run start |
| An agent receives an empty feed (§2.7) | Smoke test asserts every agent's feed is non-empty |
| 27 actions destabilize 8B tool-calling | Validate action names as in Sim 1; measure the performed-action rate in the smoke test against Sim 1's ~32/36 baseline |
| Prompt growth degrades tool-calling | Moderate feed sizing (§4.1), tuned in smoke test |
| TwHIN-BERT download / CPU-only inference | Verified in smoke test before any full run |
| One agent's failure aborts a round | Per-agent exception isolation in the gather |
| Long runtimes | `OLLAMA_KEEP_ALIVE=60m` (established project habit) |
| Exceeding TWHIN's ~90-timestep ceiling | Round count capped well below |

---

## 9. Rollout

1. **Smoke test** — small agent count, few rounds. Verify: TwHIN loads and the
   assertion fires correctly; `rec_history` captures real exposure; every agent gets a
   non-empty feed; the 27-action set does not degrade tool-calling; measure per-round
   wall-clock.
2. **Tune** — set final agent count, round count, and feed sizing from measured
   timings rather than guesses.
3. **Full run** — TWHIN, all agents, many rounds.
4. **Analysis + graph artifact.**
5. **Optional contrast run** — hot-score, same config, to isolate what personalization
   and the social graph actually change. Requires `reset_globals()` between runs.

---

## 10. Out of scope

- **The shield / Bengals-style personalization feedback.** Explicitly deferred by the
  user. The `rec_history` table built here is the substrate a future shield would need,
  since it records what each user was exposed to and engaged with.
- **MatrAIx persona integration** (§5) — separate fast-follow spec.
- **E-commerce and interview actions** (§6).
- **Scaling past the tuned agent count** — the 100/1000/10000 upstream configs remain
  a later thread.
