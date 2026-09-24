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

*Last updated 2026-09-24 09:40.*

**Design v2 is running** (Gordon, 2026-09-24 morning — see §12). Two models,
llama3.1:8b and gemma4:e2b, both write posts AND play personas, in one shared
OASIS world; every persona scrolls all 50 posts (5 topics x 5 posts x 2 models)
and likes / dislikes / does nothing, one post at a time. Vote counts hidden.
**The same 99 pinned personas every run** (fingerprint `964462b96652`, enforced in
code — `personas.core99()` refuses to run if any persona changed).

Campaign: `world_campaign.sh`, SEEDS 10-15, two rotation worlds per seed (~2.2 h
per seed), launched 09:32, log `data/llm_bias/campaign_v2.log`. First result
after seed 10 (~11:45); analysis refreshes to `data/llm_bias/analysis_v2.txt`
after every seed. Resumable: re-launching skips finished worlds and resumes a
half-done one.

**LF-12 (post set 10, 9,900/9,900 valid): no own-model like boost so far, −3.0
points [−9.7, +3.9].** Design-v2 page: **https://claude.ai/artifact/PEMNidbCam72v6qKC3GNBx**
(refresh: `export_world.py` then `make_world_artifact.py`, republish).

Night-1 results (design v1, 7 models, pick-a-favourite) are §10-11 and stay valid
as a separate design.

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
| LR-3 | recognition probe | 1 | 10 slots x 4 shuffles | 7 | done 05:46-05:53, 276/276 valid |
| LR-4 | `cars_s2_a99_r3_*` (topic: cars) | 2 | 99 x 3 | 7 | done 05:53-08:01, 2077/2079 valid |
| LR-5 | recognition probe extended | 1 | 10 slots x 20 shuffles | 7 | done 08:02-08:29, 1379 tries |

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

### LF-8 — (PROVISIONAL, k=4) Models do not recognise their own posts

Self-recognition probe on seed 1 (no persona; "one of these is yours — which?";
10 slots x 4 shuffles, 276/276 valid, chance 14.3 %). Share of tries where the
model claimed its own post, and the difference from how often OTHER models claim
that author's post:

| model | claims own | others claim it | difference |
|---|---|---|---|
| mistral:7b | 30 % | 23 % | +7 |
| gemma4:e2b | 22 % | 21 % | +1 |
| llama3.2:3b | 20 % | 6 % | +14 |
| llama3.1:8b | 18 % | 14 % | +4 |
| granite4.1:3b | 15 % | 20 % | −5 |
| phi4-mini:3.8b | 10 % | 7 % | +3 |
| qwen2.5:7b | 3 % | 6 % | −3 |

Answers are driven by screen position (llama3.2 names the last post 28/40 times;
gemma the last 21/40), not authorship. **gemma — the strongest self-preferring
judge (+13.9) — shows +1 on recognition.** Reading so far: the bias is *shared
taste* (a model likes a style it also writes in), not knowing self-favouritism.
n = 40 per model is too small to be firm; `night1_queue2.sh` extends to k = 20
after the cars run.

### LF-9 — Second topic (cars, seed 2): the favourite effect replicates, the vote effect does not

99 personas x 3 rounds x 7 judges, 21 posts, 2,077 valid decisions.

* **Favourites: pooled +4.9 share points; all 3 rounds positive (+5.4, +4.9, +4.4).**
  Conditional logit odds ratio **1.47** — against 1.49 on personal finance.
  **Caveat:** with only 3 slots the slot-cluster bootstrap cannot represent
  between-slot variation, so the cars-only intervals ([+3.0, +7.0]; OR
  [1.26, 1.72]) are too narrow. Read cars as a direction-and-size replication,
  not an independent significance test.
* **Votes do not replicate.** Upvote double-difference −3.2 [−7.7, +1.7];
  downvote +2.7 [−1.6, +7.4]. gemma and granite *downvote* their own car posts
  more (+9.1, +6.3). On personal finance both vote measures were significant in
  the self-favouring direction. So far, **the robust effect is on which post a
  persona chooses to read, not on how it votes.**
* **Persona fidelity is stronger on cars** for llama3.1 (upvotes 29 → 54 % from
  dislike to love; personal finance 52 → 61) and gemma4 (63 → 81 vs 78 → 87);
  qwen2.5 again strongest (7 → 64).
* Family: llama3.1 → llama3.2 +3.9, llama3.2 → llama3.1 +5.1 (personal finance
  +1.2, +5.7). All four sibling estimates are positive, all small.

### LF-10 — Both topics pooled (13 slots, 9,005 decisions)

Favourite self-preference **+5.6 share points [+3.4, +7.8]**, p < 0.001 (0/2000
resamples at or below zero). Clustered conditional logit **OR 1.48 [1.26, 1.71]**.
Every judge's point estimate is positive: mistral +14.1 and gemma +10.4
(individually significant), llama3.1 +7.1 [−0.5, +14.5], llama3.2 +2.2, phi4-mini
+2.5, granite +1.9, qwen +1.0. Upvote +3.2 [−0.3, +6.6], p = 0.07.
File: `data/llm_bias/analysis_combined_s1_s2.txt`.

### LF-8 (final, k = 20) — Models favour their own posts without being able to pick them out

1,379 tries (200 per model; qwen 180 — its round-6 post is missing). Difference =
P(model claims its own post) − P(other models claim that author's post); 95 %
interval from a bootstrap over the 10 rounds.

| model | claims own | others claim it | difference [95 %] | judge self-preference (LF-10) |
|---|---|---|---|---|
| llama3.2:3b | 16.1 % | 7.1 % | **+9.0 [+2.7, +13.9]** | +2.2 |
| phi4-mini:3.8b | 13.0 % | 8.0 % | **+5.0 [+2.5, +8.0]** | +2.5 |
| gemma4:e2b | 24.0 % | 19.2 % | +4.8 [−4.9, +14.2] | **+10.4** |
| mistral:7b | 26.0 % | 21.2 % | +4.8 [−4.8, +14.3] | **+14.1** |
| granite4.1:3b | 21.0 % | 20.8 % | +0.2 [−9.3, +8.8] | +1.9 |
| llama3.1:8b | 12.5 % | 13.0 % | −0.5 [−7.5, +8.4] | +7.1 |
| qwen2.5:7b | 5.0 % | 7.7 % | −2.7 [−7.0, +3.0] | +1.0 |

Recognition is weak everywhere, and it does not line up with preference. The two
models that recognise themselves beyond noise (llama3.2, phi4-mini) barely favour
themselves as judges; the two that favour themselves most (mistral, gemma) do not
recognise their posts beyond noise. **The bias looks like shared taste — a model
likes the style it writes in — not knowing self-favouritism.** The k = 4 table
above is superseded.

---

## 11. Morning report, 2026-09-24 (night 1)

**Done overnight, unattended, no failures:** 5 campaigns/probes, 11,655 persona
decisions (≈ 100 % valid) + 1,379 recognition tries, 8 commits pushed to
`origin/llm-bias`. Machine time 22:10 → 08:30.

**Answer to the hypothesis so far: yes, modestly.** A model playing a persona picks
its own post 5.6 share points more often than other models pick that post
(chance 14.3 %), odds ratio 1.48. It replicates across two topics and survives
dropping any judge. It is carried by the *choice* measure; on votes it
replicated on personal finance but not cars. And it is not self-recognition.

**Questions for Gordon** (each changes what runs next):
1. **Agents vs posts.** Statistics here are limited by the number of distinct posts
   (slots), not personas: 99 personas already give tight per-slot numbers. For
   the same hours, 99 personas x 20 rounds beats 1000 personas x 2 rounds. 1000
   personas is possible, but one round of all 7 judges over 1000 personas takes
   about 6.5 h. Do you want maximum agents or more rounds?
2. **Topics:** run the remaining three (farming, cooking, tech) one at a time as
   separate campaigns, or all five on screen per round (5x the time per round)?
3. **Posts per round:** 1 per model per topic now (7 on screen). Raise to 2 (14 on
   screen)? Longer prompts strengthen the position habits (LF-7).
4. **Herding arm (LQ-3):** show vote counts to see if self-preference snowballs?
5. **Mixed population (LQ-4):** one world where personas are split across the 7
   models, closer to a real OASIS sim.
6. More model families? Any Ollama model can join (e.g. deepseek, olmo, cohere
   command-r7b); each adds an author and a judge.

---

## 12. Design v2 (2026-09-24 morning, Gordon)

**What changed and why (Gordon's words, summarised):**
* Two models only, for a fast but proven test: **llama3.1:8b** (used all night)
  and **gemma4:e2b** (fastest). Each writes posts and plays personas. llama3.1
  was kept as the main model because it votes selectively (~55 % likes in v1)
  while gemma likes ~85 % of everything, which leaves little room for a bias to
  show in likes (LF-6).
* **Scrolling, not comparing.** Each persona sees every post, one call per post,
  and chooses like / dislike / nothing. No favourite pick.
* **Topic order follows the persona:** best-loved topic first, down to the most
  disliked; ties broken by a fixed per-persona draw. Within a topic, a fixed
  per-persona shuffle.
* **5 posts per model per topic**, all five primary topics → 50 posts per world.
* **One shared world**: all posts from both models are live on one OASIS
  platform; likes/dislikes are OASIS `like_post` / `dislike_post`.
* **Vote counts hidden** (Gordon chose this; not studying herding). This is also
  what lets the harness run one model at a time: with no visible counts, the
  order in which personas act cannot matter.
* **The same 99 personas every run** — see LD-10.

**LD-9 — Rotation.** Persona i is played by `judges[(i + world) % 2]`. World 0 and
world 1 use the same post bank with the assignment swapped, so every persona is
played by both models on identical posts. Otherwise "llama happened to get the
finance fans" could pass for bias.

**LD-10 — The 99 are pinned.** Personas #0-98 of `personas_bank.json` (the same 99
every v1 run used). Fingerprints are constants in `personas.py`
(`PINNED_BANK_HASH = 8c9cf5b67383`, `PINNED_CORE99_HASH = 964462b96652`);
`core99()` raises `PersonaDrift` if either differs, and `run_world.py` will not
start. Each manifest records the fingerprint and the persona ids. Tests check
both the pin and that an edited persona is refused.

**The test.** A 2 x 2 table of like rates (rows: model playing the persona; columns:
model that wrote the post). Self-preference = (llama-personas' llama-vs-gemma
gap) − (gemma-personas' llama-vs-gemma gap), reported as the double difference
from `analyze.did` with the persona x slot cluster bootstrap
(`analyze_world.py`). The same for dislike rates, where self-preference is
negative.

### LF-11 — Benchmark (bench_v2: 10 personas x 50 posts, seed 10): the "nothing" answers are real choices

* Speed: **llama3.1 1.23 s / decision, gemma4 0.33 s** (4 parallel). A 99-persona
  world ≈ 65 min; a rotation pair ≈ 2.2 h.
* **500/500 valid. 0 failures, 0 timeouts, 0 replies cut off at the token limit,
  0 characters of hidden thinking, 0 retries.** Every "nothing" carries a reason
  ("Not really my thing", "too vague to comment", "Need real data").
* "Nothing" follows interest: llama-played personas do nothing on **78-93 %** of
  posts in topics they dislike (−2/−1) and **15-23 %** in topics they like. gemma
  23-26 % vs 3-10 %.
* Persona fidelity is far stronger in the scroll design than in v1: llama-played
  personas like **0-5 %** of posts in disliked topics and **84-85 %** in liked
  ones (v1 finance: 52 → 61 %).
* The self-preference numbers from 10 personas (−2.4) are noise; bench_v2 is
  excluded from the campaign analysis (prefix `v2_`).

**LD-11 — Everything per post is exported and documented (Gordon, 2026-09-24:
"I need what users did for each post, time it took at each post, who made what
post and who was controlling the users for each reaction; times-vs-rounds and
time-vs-agents graphs; all documented").**
* `export_world.py` writes `data/llm_bias/export/`: `reactions.csv` (one row per
  user per post: action, reason, seconds, author model, controlling model, topic
  order, scroll position, tokens, outcome), `posts.csv`, `users.csv` (with the
  controlling model per round), `world_timing.csv`, `progress_timing.csv`.
* Every column is defined in **`LLM_BIAS_DATA_DICTIONARY.md`** (repo root).
* `make_world_artifact.py` builds the design-v2 page: result, "nothing" diagnosis,
  **time per round** (minutes per model per round), **time vs agents** (elapsed
  time every 5 users inside a round) and **whole runs at different sizes**.
* `agent_sweep.sh` (queued behind the campaign, ~1.75 h): standalone runs at 10,
  25, 50 and 75 users on post set 10, world 0, so the size chart uses real runs.
  Labels `sweep_*` are never mixed into the result (analysis uses prefix `v2_`).
* Timing note: a decision's `seconds` is that one request's duration with 4
  requests sharing the chip; throughput (`seconds_per_decision` in
  world_timing.csv) is ~4x lower. Both are documented.
* Chart colours: llama3.1 = blue, gemma4 = orange, fixed; validated for
  colour-blind separation in light and dark mode.

### LF-12 — First post set (seed 10, worlds 0+1): no own-model like boost yet

99 users x 50 posts x 2 worlds = 9,900 decisions, **9,900 valid**, every user
played by both models. Rounds took 64.7 and 66.4 min (llama 51-52 min at
1.22-1.27 s/decision; gemma 13.5-14.4 min at 0.33-0.35).

| like rate | llama's posts | gemma's posts |
|---|---|---|
| users controlled by llama | 66.5 % | 63.7 % |
| users controlled by gemma | 82.6 % | 76.8 % |

* **Both groups prefer llama's posts** (llama users +2.8 points, gemma users
  +5.8): llama wrote better-liked posts. Self-preference on likes = **−3.0 points
  [−9.7, +3.9]**, p = 0.40; on dislikes +1.7 [−1.9, +5.5] (self-preference would be
  negative). **Not supported on one post set.**
* Exploratory split by interest (not pre-planned): liked topics −2.1 [−9.5, +5.4];
  disliked topics −5.3 [−14.3, +2.4]. Nothing hiding in either.
* **Persona interest dominates the vote:** llama-controlled users like 4.5 % / 2.5 %
  of posts in topics they dislike (−2/−1) and 85-92 % in topics they are at least
  indifferent to; gemma 58-69 % vs 83-88 %.
* "Nothing" again fully explained: 0 failures, 100 % with reasons, tracks interest
  (llama 73-90 % for disliked topics vs 8-14 % for liked).
* **Contrast with night 1 (LF-5/LF-10):** when a user had to pick ONE favourite out
  of seven side by side, the controlling model's own post won +5.6 points more often.
  Rating posts one at a time, with no comparison, shows nothing so far. If this
  holds over more post sets, it is itself a finding: the bias appears when a model
  compares, not when it rates alone. This is consistent with self-preference
  studies that find it strongest in pairwise judgements. Five more post sets are
  queued (seeds 11-15).
