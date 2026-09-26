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

*Last updated 2026-09-25 21:45 — RUNNING overnight (Gordon away until 08:00).*

**Running:** campaign resumed 21:37 (`v2_s13_w1` from 2,337, then post sets 14-15, ETA ~02:15); agent sweep
queued behind it (ETA ~04:00). Ollama up with LF-14 settings.

**Overnight plan (Gordon: keep running, keep interpreting, find speed-ups, improve the sim, smoke-test):**
1. After each post set: validate the new worlds, refresh analysis/exploration/pages, log, push.
2. While timing-sensitive runs are going: NO other inference (B-32). Write and test tooling only.
3. ~04:00-07:30, machine free: (a) concurrency benchmark: llama alone vs llama+gemma together vs 2x llama,
   same people and posts; (b) retest noise: same model, same person and post, new seed, which shows
   whether cross-model agreement (kappa 0.21) is low or just noisy; (c) length-controlled post-bank smoke
   test; (d) record Ollama model digests in manifests (+ tests). Each starts as a small smoke test.
4. 08:00 morning report here and in chat.

**To resume** (start Ollama first — command below; this picks up v2_s13_w1 where it stopped, skips finished
worlds, then runs post sets 14-15; the size sweep waits behind it; ~3.5 h + ~1.75 h):

    cd /Users/gordon/research/oasis
    SEEDS="10 11 12 13 14 15" nohup caffeinate -i examples/experiment/llm_bias/world_campaign.sh \
      >> data/llm_bias/campaign_v2.log 2>&1 &
    nohup caffeinate -i examples/experiment/llm_bias/agent_sweep.sh >> data/llm_bias/agent_sweep.log 2>&1 &

Ollama is down — start it first (LF-14):
`OLLAMA_FLASH_ATTENTION=1 OLLAMA_NUM_PARALLEL=4 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=24h ollama serve > /tmp/ollama_serve.log 2>&1 &`

Night-1 design (pick-a-favourite, 7 models) found +5.6 [+3.4, +7.8] (LF-10).

Pages: design v2 **https://claude.ai/artifact/PEMNidbCam72v6qKC3GNBx** · design v1
**https://claude.ai/artifact/JRWXc8bgCYU6bXaV3okZC9**. Data: `data/llm_bias/export/`,
explained in `LLM_BIAS_DATA_DICTIONARY.md`.

**Next, when resumed:** finish post sets 13-15 → refresh export, analysis, exploration and both
pages (recipe at end of LF-16) → agent sweep for the time-vs-agents chart → rerun the length test as a
pre-stated check on sets 10-15 (LF-15/16). Later: SSH/GPU machine
(record model digests in manifests first).

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

### LF-13 — Two post sets (seeds 10-11, 19,800/19,800 valid): leaning self-preferring, not significant

| like rate | llama's posts | gemma's posts |
|---|---|---|
| users controlled by llama | 67.2 % | 65.4 % |
| users controlled by gemma | 73.0 % | 75.4 % |

Like self-preference **+4.2 points [−2.8, +11.2]**, p = 0.27; dislike **−4.7
[−10.4, +0.5]**, p = 0.08 (negative = self-preferring). Post set 11 reversed set
10's pattern: gemma-controlled users disliked llama's set-11 posts heavily. The
slot-to-slot swing is large, so more post sets are the only fix.

**LB-6 — `post_key` is not unique across post sets.** `r0|cooking|gemma4:e2b`
exists in every seed. The self-preference numbers were unaffected (they group
by model and by slot, and slots carry the seed), but `analyze_world` counted 50
posts instead of 100, and **`export_world` dropped set 11 from `posts.csv`**
and merged its counts into set 10's. Fixed: `post_uid = s<seed>|<post_key>` in
the analysis and both exports; the dictionary documents it. Re-exported: 100
posts, 100 unique ids.

**Speed work (Gordon, 2026-09-24): campaign PAUSED at 14:00 after post set 11**
(4 worlds done, all finished — nothing partial). Benchmark `bench_speed.sh`
running: scheduler (interleaved vs new per-user) x flash attention (off/on),
users 0-7 on post set 10. `run_world.py` now defaults to `--scheduler per-user`
(each worker sends one user's whole scroll back-to-back so the personality text
can be reused from Ollama's prompt cache), and every manifest records the
server's own settings (`ollama_server`, read from its start-up log). MLX
deliberately not tried: it needs separately converted model weights, so it would
no longer be the same llama3.1/gemma4 as every run so far.

### LF-14 — Speed work: flash attention on (~7 % faster); per-user ordering gives nothing

`bench_speed.sh`, users 0-7 on post set 10, 400 decisions per run
(`data/llm_bias/bench_speed.txt`, runs `speed_*`):

| run | llama3.1 s/decision | gemma4 s/decision | answers identical to A |
|---|---|---|---|
| A interleaved, FA off | 1.304 | 0.350 | — |
| A2 repeat of A (noise) | 1.282 | 0.348 | 99.8 % |
| B per-user, FA off | 1.319 | 0.345 | 99.5 % |
| C per-user, FA on | 1.194 | 0.328 | 99.0 % |
| D interleaved, FA on | 1.215 | 0.327 | 99.5 % |

* **Per-user ordering (Gordon's #4): no gain**, within the A/A2 noise (1.7 %).
  The interleaved queue was already persona-ordered with 8 requests in flight,
  so Ollama very likely reused the personality prefix already. Default reverted
  to `--scheduler interleaved` (fewer changes); per-user kept as an option.
* **Flash attention (#5): llama −7 %, gemma −6 %.** Answers change on ~1 % of
  decisions (vs 0.2 % between two identical runs) — behaviourally negligible, and
  both worlds of a post set always share one setting, so the within-set
  self-preference comparison is unaffected.
* **Adopted: `OLLAMA_FLASH_ATTENTION=1` from post set 12 on** (server restarted
  14:31). Every manifest now records `ollama_server`. Post sets 10-11: FA off;
  12-15 and the agent sweep: FA on. The whole-runs chart compares only FA-on runs.
* MLX not tried (different model weights → not the same models). Expected gain
  from both levers together is small (a 99-user round ~65 → ~61 min); the big
  lever is a GPU machine (SSH plan).
* Campaign resumed 14:31 (post sets 12-15, ETA ~22:00), agent sweep re-queued
  behind it.

**Start Ollama like this from now on:**

    OLLAMA_FLASH_ATTENTION=1 OLLAMA_NUM_PARALLEL=4 OLLAMA_CONTEXT_LENGTH=8192 \
      OLLAMA_KEEP_ALIVE=24h ollama serve > /tmp/ollama_serve.log 2>&1

### LF-15 — Exploration of post sets 10-11 (2026-09-25, while the campaign ran): what drives a reaction

`explore_world.py` → `data/llm_bias/explore_v2.json` (+ `explore_v2_posts.csv`, one row per
post). 19,800 reactions, complete post sets only. **All of this is exploratory — none of it
was planned before seeing the data**, so the intervals describe, they do not confirm.
"Cares" = the person's interest in the post's topic is 0, +1 or +2; "doesn't care" = −1 or −2.
Intervals are the persona x slot cluster bootstrap (B = 2000) unless stated.

**1. Where the headline comes from.** Like rate (%), people who care about the topic:

| | gemma posts | llama posts |
|---|---|---|
| gemma-played people | 80.4 | 77.9 |
| llama-played people | 88.8 | 90.7 |

Dislike rate (%), people who care:

| | gemma posts | llama posts |
|---|---|---|
| gemma-played people | 6.6 | **11.9** |
| llama-played people | 0.8 | 0.9 |

Each model likes its own posts a little more (+2.5 and +1.9 points). The dislike signal is
**entirely gemma-played people disliking llama's posts** (11.9 vs 6.6 %; top reasons "too
vague", "too much whining", "slick talk nonsense"). llama-played people who care about a topic
almost never dislike anything. With only two models the double difference is symmetric by
construction: it cannot say *which* model is self-preferring, only that each is relatively
kinder to its own posts than the other model is.

**2. Only where people care.** Self-preference like +4.5 [−2.4, +11.5], dislike −5.2
[−11.4, +0.1], p = 0.058. Where they don't care: like +3.2 [−4.8, +11.6], dislike −3.3
[−10.9, +3.6]. Slightly sharper where people care, as expected (llama answers "nothing" to
81-85 % of posts in topics its people dislike, so those carry little signal); not a different
conclusion.

**3. By topic.** Like self-preference: tech +11.4 [+3.5, +18.9] (p = 0.003), cars +11.0
[−7.0, +27.0], personal finance +0.7, cooking 0.0, farming −2.3. Five topics were tested, so
tech alone would be p ≈ 0.015 after a Bonferroni correction (multiplying by 5 for the five
tries); the per-topic intervals are wide (only 10 slots per topic).

**4. Post length may explain most of the like signal.** gemma writes slightly longer posts
(mean 85 vs 78 words). gemma-played people like longer posts more (short/medium/long terciles
74 / 82 / 83 % where they care); llama-played people don't care about length (90 / 89 / 91 %).
A linear model with post and person-x-model fixed effects (clustered by slot) gives a
self-preference coefficient of +2.1 [−1.3, +5.5] points (half the double difference, so ≈ +4.2
on the headline scale). Adding "gemma-played x post length" shrinks it to **+0.4 [−3.9, +4.7]**
(≈ +0.7 on the headline scale), while the length term is +4.3 per standard deviation of length
[−1.1, +9.7]. Reading: gemma's lean toward its own posts may be a taste for longer posts, which
it happens to write. Suggestive only — the length term's interval includes zero. Worth a planned
test on post sets 10-15.

**5. The model matters more than the person.** Each person is played by both models on the same
posts (9,900 pairs). The two versions give the same reaction 63.7 % of the time vs 54.1 %
expected from their overall habits alone — Cohen's kappa (agreement beyond chance, 0 = none,
1 = perfect) **0.21** (weak). Where the person cares: 0.21. Where they don't: **0.00** — llama
ignores the post (84 % "nothing") while gemma likes 60 % of posts in topics the person dislikes.

**6. The models barely agree on which posts are good.** Per-post like rate among people who
care: Spearman rank correlation between llama-played and gemma-played = **0.32**. llama-played
people like almost every post in a topic they care about (spread across posts: SD 9 points);
gemma-played people discriminate far more (SD 23 points). So llama's selectivity is about
topics, not posts. Both authors average 84 % likes where people care; llama's posts draw
slightly more dislikes (6 vs 4 %).

**7. No scroll-position effects.** Like rate is flat across positions 1-10 within a topic
(llama 65-67 %, gemma 73-77 %) and across the scroll (no fatigue by post 50).

**8. Persona traits.** Voting style dominates and is honoured by both models: "harsh" people
like 40-42 % vs "generous" 74 % (llama) / 96 % (gemma). llama turns "harsh" into "nothing"
(54 %); gemma turns it into dislikes (23 %). llama barely separates "generous" from "typical"
(−3 points vs gemma's −20). Age: the raw gap (llama, under-30 like 59 % vs 60+ 72 %) vanishes
once voting style and interest are controlled — younger personas happen to include more
"harsh" ones. Female-played people like slightly less than male (−3.6 [−6.8, −0.5] gemma,
−2.5 [−5.1, +0.2] llama, same controls). Only 4 non-binary personas — too few to say anything.

**9. Reasons.** gemma's are 2.7 words on average, only 20 % distinct ("too vague" 708 times),
and mention the person's own life 0.6 % of the time. llama's are 5.9 words, 73 % distinct, and
mention the person's own life (job, city, "as a…") 24 % of the time. So gemma's persona play is
shallow in the reasons too. Reason length and content do not differ for own vs other-model posts.

**What to do with this:** (a) at the end of the campaign, rerun on post sets 10-15 and
pre-state the length test (item 4) as the one follow-up hypothesis before looking;
(b) report the dislike result as "gemma dislikes llama's posts", not as a symmetric bias;
(c) the weak person-level agreement (item 5) is itself a finding for anyone using these
models as simulated audiences: who the person is matters less than which model plays them.

**LB-note:** `analysis_v2.txt` written at 12:08:56 today includes the first 1,399 decisions of
the unfinished `v2_s12_w0` (llama-played people only), which shifts the headline to +4.5; the
file is overwritten with clean numbers when post set 12 finishes. Use complete post sets only
(explore_world.py enforces this).

### LF-16 — Post set 12 done (3 sets, 29,700 reactions): the DISLIKE self-preference is now clear of zero; the like one isn't

Clean analysis (both rotation worlds of sets 10-12, `analyze_world.py --prefix v2_`):

| | estimate | 95 % range | p |
|---|---|---|---|
| like self-preference | **+3.2** points | −2.8 to +9.5 | 0.33 |
| dislike self-preference | **−4.7** points | −9.8 to −0.3 | **0.038** |

(`explore_world.py` with its own bootstrap draws: like +3.2 [−3.2, +9.6]; dislike −4.7 [−9.7, −0.1], p = 0.044.)
Like rates: llama-played 68.0 % on llama posts / 65.7 % on gemma posts; gemma-played 74.2 / 75.1.
Dislike rates: llama-played 4.2 / 3.9; gemma-played **12.7 / 7.6**.

**LF-15 re-run on sets 10-12** (all still exploratory):
* **Length story got stronger for likes:** self term +3.2 → **−1.0** (double-difference scale) once gemma-played x
  post length is added; the length term is now **+5.5 per SD [+0.9, +10.1]** (was +4.3 [−1.1, +9.7]). gemma writes
  86 vs 79 words. **Length does NOT explain dislikes:** −4.7 → −4.0, length term −1.0 [−4.1, +2.2]. So: the like
  signal looks like "gemma likes long posts"; the dislike signal is "gemma dislikes llama's posts" for other reasons
  (top: "too vague", "too much whining", "waste of time", "too much fuss").
* **Tech's +11 (LF-15 item 3) shrank to +5.9 [−5.5, +15.6]** — the small-sample fluke we warned about. No topic
  now clears zero.
* Stable: same-person agreement kappa 0.21 (0.01 where the person doesn't care); per-post agreement between the
  AIs rho 0.31; voting style honoured; no scroll fatigue; gemma reasons 2.8 words vs llama 5.9.

**Pipeline fixes (same session):**
* `analyze_world.py` now skips unfinished worlds AND post sets with only one finished world (fixes the LF-15
  LB-note contamination for good; `--include-unfinished` to override).
* `export_world.py` exports finished worlds only (a running world would show a half round in every table).
* Timing charts leave out a paused-and-resumed round: `v2_s12_w0`'s llama clock covers only the 1,101 reactions
  after the restart (22.9 min, not ~51). Shown in the table view, excluded from the charts, and said so on the page.
  **Resumed worlds' `wall_s` is post-restart time only** — never use it as a round's cost.

**Design-v2 page rewritten for a 5th grader (Gordon, 2026-09-25)** — https://claude.ai/artifact/PEMNidbCam72v6qKC3GNBx
v3. Plain-words answer first, "For grown-ups" numbers second; "How we keep it fair" worked through with the real
like rates; new **What else we found** (length bars, dislike bars, same-person match bars with a real example,
per-post scatter, per-topic whiskers, voting style bars, scroll fatigue, reasons); new **Look it up yourself** tool:
pick any post → all 99 people with both AIs' reaction + reason side by side (disagreements shaded), or pick any
person → profile, the exact description the AI got, and every choice they made. The tool reads `world_data.js`
(1.3 MB now, ~2.6 MB at 6 sets), written next to the page by `make_world_artifact.py`; publish both files.

**Refresh recipe (every post set):**

    P=./oasis-env/bin/python; S=examples/experiment/llm_bias
    $P $S/export_world.py
    $P $S/analyze_world.py --prefix v2_ --out data/llm_bias/analysis_v2.json > data/llm_bias/analysis_v2.txt
    $P $S/explore_world.py --out data/llm_bias/explore_v2.json > /dev/null
    $P $S/make_world_artifact.py --out <dir>/scroll_test.html     # also writes <dir>/world_data.js
    # publish scroll_test.html to PEMNidbCam72v6qKC3GNBx with files={"world_data.js": ...}

**Design-v1 page rewritten for a 5th grader too (2026-09-25)** — https://claude.ai/artifact/JRWXc8bgCYU6bXaV3okZC9 v4.
Data unchanged (night 1: seeds 1, 2, 101 + combined). Plain answer first, grown-up numbers second; statistics moved
into a "For grown-ups" fold; links to the design-v2 page. Rebuild: `make_artifact.py --seeds 1,2,101 --out <file>`.

### LF-17 — Post set 13 done (4 sets, 39,600 reactions): dislike holds, like edges toward zero-clear; length story repeats

Health check (`check_world.py`, new tonight: counts, duplicates, rotation, persona pin, OASIS db = log, cut-offs,
like-rate and speed vs other worlds): all 8 v2 worlds PASS.

| | estimate | 95 % range | p |
|---|---|---|---|
| like self-preference | +4.5 | −0.5 to +9.5 | 0.07 |
| dislike self-preference | **−4.0** | **−8.0 to −0.3** | **0.031** |

(analyze_world, B = 2000; explore_world B = 1000 gives +4.5 [−0.5, +9.4] and −4.0 [−8.1, −0.2].)
* **Length again explains most of the like signal** (self term 2.27 → 0.82, i.e. +4.5 → +1.6 on the headline
  scale) **and none of the dislike signal** (−1.98 → −2.06).
* **Cumulative dislike number:** after set 10 +1.7 [−2.0, +5.7]; after 11 −4.7; after 12 −4.7; after 13 −4.0
  [−8.1, −0.2]. Set 10 alone pointed the other way; it has been stable near −4 to −5 since.
* Topic likes: tech +8.3, cars +6.1, farming +4.3, money +4.3, cooking −0.3 (all wide).
* Same person, two AIs: kappa 0.215 (65 % agree vs 56 % by chance), unchanged.
* Page v4 adds "Is the answer settling down?" (cumulative and per-set whisker charts).
* Operational: exploration refreshes now run under `taskpolicy -b` (efficiency cores) so they do not slow the
  campaign; that made the refresh take 17 min — the bootstrap is being vectorised.

### LD-12 — Pre-stated test on UNSEEN post sets 14-15 (written 2026-09-25 22:25, before set 14 finished; set 15 not yet generated)

The length explanation (LF-15) was found by looking at sets 10-11 and re-checked on 12-13, so those sets
cannot confirm it. Sets 14 and 15 are held out. Predictions, tested on sets 14+15 ONLY with
`explore_world.py`'s length models (post + person-x-AI fixed effects, clustered by slot):
* **P1** gemma writes longer posts than llama in sets 14-15 (mean words).
* **P2** the gemma-played x post-length term on likes is positive.
* **P3** adding it shrinks the like self-preference term by at least half.
* **P4** it does NOT shrink the dislike self-preference term by half (dislikes are not about length).
* **P5** the dislike self-preference double difference on sets 14-15 is negative (direction only; 2 sets
  cannot give a narrow range).
Held-out sets are small (2 x 50 posts), so a failed P2/P3 with a wide interval is "not confirmed", not
"refuted". Whatever happens is reported.

### LF-18 — Post set 14 done (5 sets, 49,500 reactions): the dislike result WEAKENS; post sets differ a lot

Health check: v2_s14_w0/w1 PASS (llama 1.22 s, gemma 0.33 s per decision — normal).

| | estimate | 95 % range | p |
|---|---|---|---|
| like self-preference | +3.8 | −0.6 to +8.0 | 0.086 |
| dislike self-preference | −2.2 | **−5.6 to +1.0** | 0.19 |

**The dislike result (LF-16/17) is no longer clear of zero.** Each post set on its own (dislike double difference):
set 10 +1.7, set 11 **−11.1**, set 12 −4.8, set 13 −1.7, set 14 **+5.0** [+0.3, +11.3]. Likes: −3.0, +11.3, +1.4,
+8.4, +0.7. So the "clear of zero" at 3-4 sets leaned heavily on set 11. The effect depends strongly on which
50 posts get written — between-set variation is large next to the within-set interval. Implications:
(a) more post sets are worth more than more people; (b) any single-set result (including night 1's 3-round cars
run, LF-9) should be read as one draw; (c) the page now says this in plain words.
Dislike rates where people care (sets 10-14): gemma-played 6.6 % on gemma posts vs 8.4 % on llama posts;
llama-played 1.1 vs 0.5.
**LD-12 held-out length test is NOT looked at yet** (needs sets 14+15; set 15 running, ETA ~02:15).

### LF-19 — Campaign complete (6 post sets, 59,400 reactions): no clear self-preference in the scroll design; the held-out length test

All 12 v2 worlds PASS `check_world.py`. Campaign ended 02:23; agent sweep started 02:23.

**Final headline (sets 10-15, analyze_world B = 2000):**

| | estimate | 95 % range | p |
|---|---|---|---|
| like self-preference | +2.7 | −1.2 to +6.6 | 0.17 |
| dislike self-preference | −1.5 | −4.6 to +1.3 | 0.30 |

Per post set (like / dislike): 10: −3.0 / +1.7 · 11: +11.3 / −11.1 · 12: +1.4 / −4.8 · 13: +8.4 / −1.7 ·
14: +0.7 / +5.0 · 15: −2.9 / +1.7. **Conclusion for design v2: no reliable self-preference.** Any lean is small
(a few points per 100) and swings with the particular posts; the mid-campaign "clear of zero" dislike result
(LF-16/17) did not survive sets 14-15. Contrast night 1 (pick-a-favourite among 7): +5.6 [+3.4, +7.8] — the
comparison format may matter (choosing between side-by-side posts vs reacting to one post at a time).

**LD-12 held-out test (sets 14+15 only, written 22:23 before they existed; `heldout_s14_15.json`):**
P1 gemma longer — **yes** (87 vs 80 words). P2 gemma-played x length on likes positive — **direction yes, not
confirmed** (+1.5 per SD [−1.9, +4.8]). P3 halves the like self term — **not testable**: no like self-preference
in 14-15 (self term −0.54 [−2.95, +1.88]; double difference −1.1 [−6.0, +4.4]). P4 dislike term not shrunk by
length — **yes** (+1.67 → +1.80). P5 dislike double difference negative — **no** (+3.3 [−0.6, +7.6]).
On all six sets, allowing for length takes the like number +2.7 → +0.3 (self 1.34 → 0.13).

**Where the uncertainty comes from** (bootstrap SD, points; resample people only / posts only / both):
likes 0.45 / 1.84 / 1.95; dislikes 0.30 / 1.46 / 1.55. **~94 % of the variance is which posts got written.**
More people barely helps; more post sets (slots) does. Halving the interval needs ~4x the slots.

Stable descriptive results (6 sets): same person, two AIs, kappa 0.22 (66 % agree vs 56 % by chance);
per-post agreement between the AIs rho 0.32; like rates where people care: gemma-played 84.2 / 83.0 (own / llama),
llama-played 90.8 / 88.8; dislike gemma-played 6.3 on gemma posts vs 7.9 on llama posts.

Page v6 (PEMNidbCam72v6qKC3GNBx): all 6 sets, held-out check shown under the length card, new "More posts would
help much more than more people" card.

### LF-20 — Post by post, the own-post boost appears where gemma's post is much longer (exploratory)

150 slots (sets 10-15), people who care about the topic. For each slot, the like double difference vs the word
gap (gemma − llama; gemma is longer in 71 % of slots, mean +7.8 words):

| word-gap tercile | mean gap | like DD | dislike DD |
|---|---|---|---|
| similar length | −5 words | −0.6 | −0.1 |
| middle | +9 | +2.2 | +1.7 |
| gemma much longer | +21 | **+8.7** | **−7.4** |

Spearman gap vs like DD +0.19 (p = 0.023); vs dislike DD −0.16 (p = 0.051). So at slot level length tracks BOTH
signals, while the regression (LF-15..19) said length explains likes but not dislikes; the two views weight slots
differently (regression: continuous words, all people; this: slot means, carers only). Found after looking, on
all sets, so exploratory. **Design implication: match post lengths (length_test.py tonight) before the next
campaign, or put length in the analysis model from the start.** Page v7 shows it in the length card.

### LF-21 — Overnight speed and design tests (machine otherwise idle, 02:23-04:51)

**Agent sweep (time vs number of people; post set 10, world 0, flash attention on):**

| people | llama min | gemma min | total min | llama s/decision |
|---|---|---|---|---|
| 10 | 5.2 | 1.4 | 6.5 | 1.24 |
| 25 | 13.2 | 3.3 | 16.5 | 1.22 |
| 50 | 25.0 | 6.8 | 31.8 | 1.20 |
| 75 | 38.0 | 10.1 | 48.1 | 1.20 |
| 99 (sets 14-15) | ~50 | ~13.8 | ~64 | 1.22 |

Perfectly linear: **~0.65 min per person per 50-post world**; per-decision cost does not change with size.

**Can two sims share the machine? (`bench_concurrency.sh`, 8 people, 400 decisions per job)**

| setup | wall | vs one-after-the-other |
|---|---|---|
| A llama alone | 495 s | |
| B gemma alone | 142 s | A+B = 637 s |
| C llama + gemma at once | 589 s | **−7.6 %** |
| D two llama jobs at once | 944 s | vs 990 s: **−4.6 %** |

The chip is already saturated at NUM_PARALLEL 4: a second full sim gives ~5 %, not 2x. Running a world's two
judges at the same time instead of in turn saves ~8 % (~5 min per world). Per-decision latency under C: llama
1.44 s (vs 1.21), gemma 0.58 s (vs 0.33) — they share the chip. **Recommendation: not worth changing the harness
now; the real speed lever is the GPU machine.** (If adopted later: a `--concurrent-judges` flag; answers would
shift ~1 % from batching, like flash attention, so never switch mid-comparison.)

**Can post length be matched? (`length_test.py`, set 10's exact briefs, separate bank `data/llm_bias/lengthtest/`)**

| variant | gemma words | llama words | gap | cost |
|---|---|---|---|---|
| real set 10 ("60 to 120") | 81.7 ± 6.8 | 76.6 ± 8.6 | 5.1 | |
| prompt "75 to 85" only | 71.3 ± 6.3 | 61.8 ± 7.2 | **9.5 (worse)** | 1 try/post |
| prompt "75 to 85" + reject outside 65-95 | 72.2 ± 5.4 | 69.8 ± 4.6 | **2.4** | 1.86 tries/post, 2 of 50 failed |

Both models undershoot a stated word range (llama much more), so asking alone widens the gap; asking + rejecting
works. A third variant (ask 85-100, enforce 68-95) is running to cut the retries.

**Harness (applied 04:53, after the campaign and sweep; default behaviour unchanged, 23/23 tests pass):**
`run_world.py --draw N` (fresh reproducible random draw; 0 = original seed formula) and every manifest now
records `ollama_models` digests (llama3.1:8b 46e0c10c…, gemma4:e2b 7fbdbf8f…). Needed for the GPU move.

### LF-22 — Retest: each AI agrees with itself; the gap between AIs is real (and more length variants)

`rt_s13_w0/w1`: people 0-19 of post set 13, both worlds, same model per person, `--draw 1` (new random draw);
both PASS check_world; like/dislike/nothing rates match the originals for the same 20 people (llama 58.7 vs
59.0 % like, gemma 81.8 vs 81.9 %). `retest_compare.py` → `data/llm_bias/retest_s13.json`:

| pair (same people, same posts) | agree | by chance | kappa |
|---|---|---|---|
| gemma vs gemma (new draw) | 96.1 % | 68.7 % | **0.88** |
| llama vs llama (new draw) | 86.9 % | 48.0 % | **0.75** |
| llama vs gemma | 61.1 % | 52.6 % | **0.18** |

llama's self-agreement is lower on topics the person dislikes (kappa 0.26 there vs 0.58 where they care): its
"skip vs like" on uninteresting topics is the noisy part. **Conclusion: the cross-AI disagreement (LF-15, kappa
~0.2) is a real difference between the models, not sampling noise.** For simulation users: the persona text
constrains behaviour far less than the choice of model does. Page v9 shows this in the "same person" card.

Length variants (set 10 briefs, 50 posts each):

| variant | gemma | llama | gap | tries/post | failed |
|---|---|---|---|---|---|
| ask 85-100, reject outside 68-95 | 86.4 | 76.1 | 10.3 | 1.28 | 0 |
| ask 75-85, reject outside 70-90 | 74.6 | 75.3 | **0.7** | 2.58 | **10** (9 llama) |
| ask 75-85, reject outside 65-95 (LF-21) | 72.2 | 69.8 | 2.4 | 1.86 | 2 |

**Recommended for the next campaign:** ask 75-85, reject outside 65-95, allow more retries (so no post is
lost), and keep post length in the analysis model regardless.

Post set 16 (same design, harness unchanged in behaviour; now records model digests) started 05:36 — more post
sets are what narrows the answer (LF-19).
