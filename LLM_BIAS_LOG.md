# LLM Bias — project log

**This is the log for the LLM Bias project, started 2026-09-23.** It is separate
from `RESEARCH_LOG.md`, which holds Simulations 1-4 and must still be read at the
start of every session for context (conventions, OASIS internals, and the bug
history B-1..B-41 that this project's guards come from).

**Where to resume: §0 STATUS.** It is the only section that goes stale.
Everything after it is append-only. Ids in this file are prefixed `L` so they
never collide with Sim 4's: findings `LF-n`, bugs `LB-n`, decisions `LD-n`,
runs `LR-n`, questions `LQ-n`.

Code: `examples/experiment/llm_bias/`. Data: `data/llm_bias/`. Branch: `llm-bias`.

---

## 0. STATUS — read this first when resuming

*Last updated 2026-09-24 06:00.*

**LF-5: the hypothesis is supported on the main run** (seed 1, 99 personas x 10
rounds x 7 judges, 6,928 valid decisions): pooled self-preference **+5.8 share
points [+2.9, +8.7]**, cluster-bootstrap p < 0.001; conditional logit **odds
ratio 1.49 [1.28, 1.76]** with the clustered bootstrap. Robust to dropping any
judge (+4.2 to +7.1) and positive in 9 of 10 rounds.

Queue (`night1_queue.sh`): self-recognition probe on seed 1 running since 05:46,
then the cars campaign (seed 2, 99 x 3), ETA ~08:10. Do not start other
inference until `data/llm_bias/night1_queue.log` says "cars campaign done".

Artifact: **https://claude.ai/artifact/JRWXc8bgCYU6bXaV3okZC9** — regenerate with
`make_artifact.py --seeds 1,101,2`.

---

## 1. The project in plain words

**The question.** When a language model is told "you are Dale, a 58-year-old
rancher who finds finance influencers annoying" and is shown a handful of Reddit
posts, does it prefer the post that *it* wrote over posts written by other
models? If yes, then any simulation that uses one model to both write content and
play the audience is quietly rigged in that model's favour. That is the
**hypothesis: a persona played by model J picks model J's post more often than
its quality alone would predict.** In the literature this is called
*self-preference bias* (e.g. Panickssery et al. 2024, "LLM Evaluators Recognize
and Favor Their Own Generations").

**One round, step by step.**
1. **Posting.** For each active topic there is one *slot* with a brief: an angle
   ("paying off credit card debt"), a post type ("asking for advice") and a poster
   voice ("a 24-year-old in their first full-time job"). Every author model gets
   the identical brief and writes one post. With 7 authors that is 7 posts on the
   same subject, differing only in which model wrote them.
2. **Voting.** Every persona is played by the *judge* model. It sees the 7 posts
   anonymously, in its own shuffled order, with no vote counts, and answers in
   JSON: up / down / none on each post, plus the ONE post it would most want to
   read (its *favourite*), plus a one-sentence reason in character.
3. **Recording.** Posts are published and votes cast on a real OASIS reddit
   platform (`create_post`, `like_post`, `dislike_post`), so the database is
   standard OASIS. Every decision is also appended to `decisions.jsonl` with
   what was shown, in what order, and what was chosen.

**The crossover — why the test is fair.** Every judge model is run over the SAME
posts, the SAME personas and the SAME display orders. That gives a table: rows are
judge models, columns are author models, each cell is how often that judge picked
that author's post. A column being high everywhere just means that model writes
posts everyone likes (quality). **Self-preference is the diagonal standing out**
— judge J picking J's posts more than the *other* judges pick J's posts:

    SP(J) = share of J's favourites that are J's posts
          − average share of the other judges' favourites that are J's posts

That subtraction is a *difference-in-differences*: it cancels "J writes good
posts". SP = 0 means no self-preference. A second, independent test is a
*conditional logit* — a choice model that treats each favourite pick as a choice
among the posts shown, with a separate quality term for every single post and a
term for screen position; its `self` odds ratio is the multiplicative boost a
post gets from being the judge's own writing (1.0 = none).

**Uncertainty.** Decisions are not independent: the same persona votes every
round, and everyone in a round sees the same posts. The confidence intervals come
from a *two-way cluster bootstrap* — resampling personas and slots together 2000
times — which is wider, and more honest, than treating every vote as independent.

---

## 2. Models (local Ollama only)

Gordon, 2026-09-23: **local Ollama models only** — no Claude, Gemini or other paid
APIs, as authors or as personas. Seven models, six families:

| model | family / maker | size | judge s/decision (7 posts, 4 parallel) |
|---|---|---|---|
| `llama3.1:8b` | Llama / Meta | 8.0 B | 5.0 |
| `llama3.2:3b` | Llama / Meta | 3.2 B | 2.7 |
| `gemma4:e2b` | Gemma / Google | 5.1 B | 1.3 |
| `granite4.1:3b` | Granite / IBM | 3.4 B | 2.8 |
| `qwen2.5:7b` | Qwen / Alibaba | 7.6 B | 4.5 |
| `mistral:7b` | Mistral / Mistral AI | 7.2 B | 4.3 |
| `phi4-mini:3.8b` | Phi / Microsoft | 3.8 B | 3.6 |

`qwen2.5:7b`, `mistral:7b` and `phi4-mini:3.8b` were pulled on 2026-09-23 for this
project. The two Llamas are a deliberate pair: if self-preference exists, does it
extend to a sibling model (family preference)?

**Connecting other providers later (not used, per Gordon).** The client
(`llm.py`) has a `backend` field and a single `chat_json()` entry point, so a
second provider is one function. The cleanest bridges are LiteLLM (one
OpenAI-style API over Anthropic, Gemini, OpenAI, Ollama, ...) or CAMEL's own
`ModelFactory`, which OASIS already uses. Checked on this machine: the `claude`
CLI works headless; the `gemini` CLI is installed but not authenticated. Neither
is used.

---

## 3. Personas

`personas_bank.json` — **1000 hard-coded personas**, committed, hash
`8c9cf5b67383`. Built once by `personas.py` from attribute pools with a fixed
seed; `python personas.py --check` verifies the file still matches the builder.
Person #7 is the same person in every run.

Each persona: name, username, age, gender, place, profession, education, money
situation, MBTI, Big Five (1-10 with a gloss), a signed interest score for all 15
topics (−2 dislike … +2 love; every persona has at least one love and one
dislike), what they value in a post (length, tone, kind of evidence), a pet
peeve, and a voting habit (generous 26 % / typical 54 % / harsh 20 %).

**Why no language model wrote the personas.** If llama had written them, a
llama-flavoured persona prompt could itself nudge judges toward llama-style
posts — contamination that cannot be removed afterwards. Every word is from a
seeded random draw and a fixed template.

**Taken from OASIS and the reference sims:** OASIS's reddit profile schema (all
ten fields, so the bank also loads into stock OASIS generators); the Big Five
1-10 format of the reference repos (`MultiAgent4Collusion`,
`MutiAgent4Fraud`); and Sim 4's lesson that OASIS's generated reddit personas are
0.963 cosine-similar — near-identical characters — so interests here are
explicit, signed and spread.

**How many agents is "max".** The 99 ceiling in Sim 4 was the Twitter persona
file (99 usable bios), not hardware. Here the bank holds 1000 and agents never
interact, so the only limit is time:

    wall clock ≈ agents × rounds × topics × (sum over judges of s/decision)
               ≈ agents × rounds × topics × 24 s   for all 7 judges

99 agents × 8 rounds ≈ 5.3 h; 1000 agents × 1 round ≈ 6.7 h. Memory is not a
constraint: one judge model is loaded at a time.

---

## 4. Topics

15 topics in `topics.py`. **Primary five**, in planned order:
1. **Personal finance & money** (`r/personalfinance`) — **active first.** Everyone
   has a stake, so both interested and uninterested personas have a reason to
   vote; a niche first topic would leave most personas at the floor.
2. Cars, trucks & driving (`r/cars`)
3. Farming, ranching & rural life (`r/farming`)
4. Cooking & food (`r/cooking`)
5. Consumer tech & gadgets (`r/technology`)

Ready as extras: fitness, video games, parenting, sports, travel, home
improvement, pets, movies & TV, science & space, small business. Each topic has
6-16 angles; angles do not repeat within a seed until the list is used up.

---

## 5. Decisions

**LD-1 — Decisions are one JSON answer, not OASIS tool calls; the votes are still
executed as OASIS actions.** The forced choice needs exactly one structured answer
per persona per topic, and tool-calling support is uneven across these seven
models. A JSON answer is model-agnostic. Posts and votes are then applied through
OASIS's own `create_post` / `like_post` / `dislike_post`, so the OASIS database
matches the decision log exactly (verified on the first smoke: 17 upvotes and 9
downvotes in both). A side effect: 1.3-5.0 s per decision against Sim 4's 21 s per
agent-turn, because the prompt is ~1,500 tokens instead of a full tool schema and
feed.

**LD-2 — Authors are anonymous, order is shuffled, scores are hidden.** No username
or model name is shown. Order is shuffled per (persona, round, topic) with a seed
that does NOT include the judge, so every judge sees each persona's feed in the
identical order (paired design). Vote counts are hidden because Sim 2 and 3 showed
visible scores drive herding.

**LD-3 — Posts are normalised to plain text.** Markdown, emoji, hashtags, links and
list markers are stripped (raw text is kept), so formatting habits are not a free
signature. Any post mentioning AI or a model name is rejected and regenerated.
Title < 15 words, body 60-120 words requested (30-220 accepted).

**LD-4 — Same brief for every author in a slot.** Posts differ only by model.

**LD-5 — Post bank generated once per seed and shared by every judge run;
author-major order** (one model writes all its posts before the next loads — no
model swapping).

**LD-6 — Personas assembled by template, no LLM.** See §3.

**LD-7 — `think: false` on every call.** See LB-1.

**LD-8 — Temperatures:** authors 0.8, judges 0.7. Context 8192 set per request.

---

## 6. Bugs

**LB-1 — gemma4 returned empty answers (0/16 valid).** gemma4:e2b is a "thinking"
model: it spent the whole output budget on hidden reasoning and returned empty
content. Fixed by sending `think: false` on every request, to every model —
verified accepted by all seven. Set for authors too, so no model gets a hidden
drafting step the others lack. After the fix gemma is the fastest judge (1.3 s).

**LB-2 — Seed functions used only a few bytes of the key.** The first drafts took
`int.from_bytes(...)` of a string slice, so different personas or topics could
share a sampling seed. Replaced with a SHA-256-based `llm.stable_seed()`; a test
checks 1000 personas get 1000 distinct seeds. Caught before any real run.

**LB-3 — The conditional logit was singular.** Each choice set holds exactly one post
per author from one slot, so that slot's post dummies sum to 1 inside the set.
Fixed by dropping one reference post per slot. Caught by the planted-effect test.

**LB-5 — The fast conditional logit assumed every choice set had 7 posts.** In seed
1, qwen2.5's round-6 post failed all 5 generation attempts (it returned a title
and no body), so round 6 showed 6 posts (693 decisions). The difference-in-
differences was unaffected (rates are over what was shown); the clustered logit
refused to run. Fixed by padding to 7 with masked options that can never be
chosen; a test with unequal choice sets checks it against statsmodels.

**LB-4 — The upvote self-preference measure would have credited generosity.** A judge
that upvotes 80 % of everything (granite) looked self-preferring next to one that
upvotes 22 % (phi4-mini). Up/down rates now use a double difference (each judge's
rate for an author is centred on its own rate for the other authors first).
Favourite shares need no centring — they sum to 1 per judge. A test with a
generous judge and no real effect now guards this (the old formula reads +0.65).

---

## 7. Tests

`./oasis-env/bin/python -m pytest examples/experiment/llm_bias -q` — 13 tests, no
model calls, ~14 s. The important ones are the analysis tests on synthetic data:

* **null with a quality gap** — author A writes better posts, nobody favours their
  own. The naive "how often does J pick J's post" reads > 40 % for A (chance 33 %)
  — it would be fooled. The difference-in-differences CI covers 0 and the logit
  p > 0.01. *This is the confound the design exists to remove.*
* **planted effect** — self-boost β = 0.7 planted; recovered within 0.25, odds
  ratio > 1.5, p < 0.001.
* **generous judge** — see LB-4.

---

## 8. Runs

| id | label | seed | agents x rounds | judges | status |
|---|---|---|---|---|---|
| LR-0 | `smoke1`, `smoke7_*` | 900 | 5x2, 8x2 | 1, then 7 | smoke only; excluded from analysis |
| LR-1 | `pilot_s101_a30_r3_*` | 101 | 30 x 3 | 7 | done 22:10-22:49, 629/630 valid |
| LR-2 | `main_s1_a99_r10_*` | 1 | 99 x 10 | 7 | done 22:59-05:44 (6 h 45 m), 6928/6930 valid |
| LR-3 | recognition probe | 1 | 10 slots x 4 shuffles | 7 | queued behind LR-2 |
| LR-4 | `cars_s2_a99_r3_*` (topic: cars) | 2 | 99 x 3 | 7 | queued behind LR-3 |

**Parallelism check (22:50):** `OLLAMA_NUM_PARALLEL=8` / `--parallel 8` gives no
speed-up over 4 (llama3.1 5.10 vs 5.11 s/decision, llama3.2 2.71 vs 2.61). The GPU
is saturated at 4. Server stays at 4.

**Smoke observations (16 decisions per judge — machinery check, not results):**
granite put 13/16 favourites on whatever was shown first (strong position bias;
the shuffle spreads it evenly over authors, so it adds noise, not bias). Judges
differ a lot in voting temperament: phi4-mini leaves 68 % of posts unvoted, qwen
downvotes 47 %, granite upvotes 80 %.

---

## 9. Open questions

* **LQ-1** Family preference: do llama3.1 and llama3.2 prefer each other's posts?
  (The analysis can answer it once the 7-judge matrix is filled.)
* **LQ-2** Mechanism: is any self-preference *self-recognition* (it can tell which post
  it wrote)? Follow-up probe: ask each model "which of these did you write?".
* **LQ-3** Does showing vote counts (herding) amplify self-preference?
* **LQ-4** Mixed population: personas split across judge models in one world.
* **LQ-5** Does topic interest matter? Manipulation check: upvote rate should rise with
  the persona's interest score.

---

## 10. Findings

### LF-1 — Pilot (seed 101, 30 personas x 3 rounds x 7 judges): suggestive, not established

629 of 630 decisions valid. Chance share per author 14.3 %.

* **Pooled self-preference +5.8 share points** (95 % cluster-bootstrap interval
  −1.3 to +13.7, p = 0.125). Six of seven judges point positive; llama3.2 is the
  exception (−3.4).
* **Conditional logit odds ratio 1.46.** Its model-based p is 0.0003, but that
  treats 629 picks as independent. With the same two-way cluster bootstrap the
  interval is **0.92–2.19, p = 0.12** — the two methods agree on direction and size,
  and the naive p-value was an artefact of ignoring clustering. **Always quote the
  clustered numbers.**
* Strongest single judge: **llama3.1:8b, +12.8 points on favourites**, and its
  upvote/downvote double-differences are both individually significant (+25 upvote
  points, −21 downvote points toward its own posts).
* Only 3 slots (21 posts) — the slot dimension dominates the interval. That is why
  LR-2 runs 10 rounds.

### LF-2 — Most models barely play the persona's interests

Manipulation check: upvote rate by the persona's interest in personal finance
(−2 → +1; no +2 persona in the first 30). **Only qwen2.5 shows a clean gradient**
(upvotes 20 → 57 %, downvotes 59 → 27 %). gemma4, granite and mistral upvote ~90 %
of everything regardless of who they are playing; phi4-mini ~20 % regardless.
This is a finding about persona fidelity in small models, and it matters for any
OASIS-style simulation: for most of these models the "persona" changes the tone
of the reason, not the vote.

### LF-3 — Strong, model-specific screen-position habits

Favourite rate by screen position (chance 14 %): granite picks post 1 **68 %** of
the time, phi4-mini **49 %**; qwen2.5 favours the last post (38 %); gemma4 and
llama3.2 almost never pick post 1 (2 %). Because order is shuffled per persona,
these habits spread evenly over authors — they add noise, not bias — but granite
and phi4-mini carry less information about authorship per decision.

### LF-4 — Family (LQ-1), pilot only

llama3.1 → llama3.2 −6.7 points; llama3.2 → llama3.1 +4.6. No sign of family
preference yet; too small to say.

### LF-5 — MAIN RESULT: models playing personas favour their own posts (seed 1)

99 personas x 10 rounds x 7 judges, one topic (personal finance), 70 posts,
6,928 valid decisions of 6,930 (100.0 %). Chance share per author 14.3 %.

| judge | self-preference, favourite share points [95 % CI] |
|---|---|
| gemma4:e2b | **+13.9 [+5.3, +23.0]** |
| mistral:7b | **+13.8 [+5.6, +23.0]** |
| llama3.1:8b | +8.2 [−1.2, +18.2] |
| phi4-mini:3.8b | +2.4 [−1.8, +6.9] |
| llama3.2:3b | +1.5 [−1.8, +4.9] |
| qwen2.5:7b | +1.3 [−2.8, +5.7] |
| granite4.1:3b | −0.5 [−6.8, +5.1] |
| **pooled** | **+5.8 [+2.9, +8.7], p < 0.001** |

* **Conditional logit** (post + position fixed effects): odds ratio **1.49**,
  two-way cluster bootstrap **[1.28, 1.76]**, 0/300 resamples at or below 1.
  A post's odds of being a persona's favourite are about half again higher when
  the model playing the persona wrote it.
* **Votes agree.** Upvote double-difference +5.1 points [+1.6, +8.6], p = 0.006;
  downvote −4.0 [−6.5, −1.7], p < 0.001. llama3.1 is the clearest here (+19.7 up,
  −13.5 down, both clear of zero) even though its favourite effect misses 0.05.
* **Robustness.** Leave-one-judge-out pooled estimate stays between +4.2 (without
  gemma or mistral) and +7.1. Per round, 9 of 10 slots are positive (range −1.9 to
  +12.0).
* **Which judges show it.** The two with the strongest effect (gemma, mistral) are
  NOT the ones that follow persona interest (LF-6) — they are generous upvoters
  with mild position habits. The two with the strongest position habits (granite
  65 % post 1, phi4-mini 59 %) show essentially none: a judge that mostly picks by
  position has little room left to pick by author.
* **Family (LQ-1).** llama3.1 → llama3.2 +1.2, llama3.2 → llama3.1 +5.7 points.
  No clear family preference from one sibling pair.
* **Length.** All judges favour longer posts (favourites average 71.6 words against
  64.5 shown). Common to every judge, so the post fixed effects absorb it; it
  does not explain the diagonal.
* **Honest limits.** One topic, one post bank (70 posts, 10 slots), and one
  generation per slot per author. The slot dimension is the thin one. A second
  topic (cars, LR-4) is the first replication.

### LF-6 — Persona fidelity, full interest range (seed 1, updates LF-2)

Upvote rate from personas who dislike personal finance (−2) to those who love it
(+2): qwen2.5 **12 → 63 %** (downvotes 69 → 24 %) — the only model that plays the
interest strongly. llama3.1 52 → 61, llama3.2 58 → 63, gemma4 78 → 87: mild.
granite 94 → 98, mistral 88 → 89, phi4-mini 20 → 26: essentially none.

### LF-7 — Screen-position habits replicate (seed 1)

Favourite at position 1 (chance 14 %): granite 65 %, phi4-mini 59 % (pilot 68 %,
49 %). qwen2.5 leans last (27 %). The shuffle keeps these from biasing the
self-preference estimate.
