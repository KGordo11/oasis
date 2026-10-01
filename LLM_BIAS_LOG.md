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

*Last updated 2026-10-01 14:10 — LD-18 DONE (11 rounds). Nothing running (Ollama idle).*

**Answer (LF-48):** users played by an AI upvote that AI's posts **+7.1 points** more [+2.9, +11.5] and downvote them
**−4.7** less [−7.6, −1.9]; 10/11 rounds positive; mostly gemma4; +12.5 at equal length. 108,800 votes, 0 failed.
**Next (Gordon's call):** cross-family pair (gemma4 vs llama3.2:1b, ~8 rounds/night), neutral referee crowd,
length-matched posts (~179 words), visible counts, GPU machine.

*(was, 08:50)* LD-18 RUNNING, round 8 of ~12.

**Design (Gordon 2026-09-30, LD-18):** gemma4:e2b + gemma3:1b (fastest two of 9 speed-tested) each write 5 new natural
posts per subreddit every round (50/round, briefs never reused); then gemma4 plays all 100 pinned users through every
post (upvote/downvote/nothing, author hidden, no memory), then gemma3 plays the same 100 on the same posts.
`two_ai_campaign.sh` runs rounds until 14:30; `two_ai_after_round.sh` checks, analyses, rebuilds the page, commits.
**After 7 rounds (69,600 votes, 0 invalid):** own-AI upvote boost +7.1 points, 7/7 rounds positive, wider 95 % interval
[+1.5, +13.6]; downvotes −5.0 [−8.5, −1.2]. Mostly gemma4 favouring its own posts (+6.6 vs gemma3 +0.5). Length hides
part of it (gemma3 writes longer; gemma3-users dislike length, gemma4-users like it): at equal length +14.0.
Same user + post, two AIs agree 67.5 % (κ 0.18). Drift check: replay of round-1 votes 97 % identical.
**Pages:** results page (every round) https://claude.ai/artifact/HPmkfevmeC3LTYWhN4citW · report doc tab "Test 6"
(results through round 7; final redraw at the end via make_doc_charts.py).
**If it stops:** `A=gemma4:e2b B=gemma3:1b STOP_AT="2026-10-01 14:30" examples/experiment/llm_bias/two_ai_campaign.sh`
resumes (finished worlds skipped, half-done ones resumed). Start Ollama first (LF-14 settings).

---
*Previous status (2026-09-29 06:40):*

*(was) Last updated 2026-09-29 06:40 — ALL TASKS DONE, everything stopped (Ollama off, nothing running).*

**Final answers:** three AIs writing freely, 6 post sets (LF-46): every AI favours its own posts, pooled +6.8
likes per 100 [+4.6, +9.4]; each AI above zero in every set. Feed test (LF-47): when one AI plays the whole crowd,
its own posts get +7.2 likes per 100 (counts hidden) / +4.8 (counts visible) and more of the top spots; visible
counts let the first few people fix the ranking. Taste (LF-43), person vs AI (LF-44), recognition (LF-42).
Report: https://claude.ai/code/artifact/7f61723e-b24b-4c68-871f-3510205cdbd4 · Page v36:
https://claude.ai/artifact/PEMNidbCam72v6qKC3GNBx
**Open (Gordon's call):** sibling test (LD-17 item 3, designed), more feed sets, GPU machine, length rule.

---
*Previous status, 2026-09-28 07:30 — MORNING REPORT. Nothing running (campaign stopped 05:23 after set 42; morning
checks done 07:14). Ollama up.*

**Three AIs, natural posts (LD-14/15; post sets 40-42, 33,750 reactions, 50 pinned people, every world done):**
**every AI favours its own posts when playing a person.** Likes: gemma +8.2 [+3.8, +12.6], llama +5.7
[+2.1, +9.3], mistral +7.2 [+3.9, +10.4], pooled **+7.0 [+4.3, +9.7]**; dislikes pooled −3.6 [−5.8, −1.7]
(llama −6.4, gemma −4.3; mistral ~0 because it almost never dislikes). Positive for every AI in every set.
Not a length artefact (length explains ~16 %). The AIs **cannot reliably recognise** their own posts → shared
taste, not deliberate favouritism (LF-42). Each AI is self-consistent; different AIs play the same person
differently (kappa 0.10-0.26 across vs 0.72-0.88 within).
**Why earlier tests looked weaker:** with two AIs one number covers both directions and single post sets swung
a lot; three AIs give three independent checks per set and a far steadier answer.
Page v32 (PEMNidbCam72v6qKC3GNBx): plain-words results, charts, look-up tool for every test incl. three AIs.

**For Gordon:** (a) continue three-AI sets (post set 43's first world is partial and resumable:
`SEEDS="43 44 45" examples/experiment/llm_bias/v3_campaign.sh`), ~3.9 h each; (b) the natural-length average
across all three AIs is ~147 words (llama 117, mistral 161, gemma 163) if you want the later length rule;
(c) charger: 65 W can't keep up with the sims (needs 96 W+).

**Previous test (A/B, complete):**
**Answer (15 post sets, 140,000 reactions, first 50 of the pinned 99, length-matched posts, every world PASS):**
* **Showing posts side by side does not change self-preference** — format effect on likes −1.8 [−5.0, +1.3].
* **A small own-post preference is real in both formats**: scrolling +5.2 likes [+2.4, +8.1] and −2.3 dislikes
  [−4.3, −0.1] per 100; side by side +3.4 likes [+0.0, +6.8], favourite +2.4 [+0.3, +4.6].
* It is small and needs many post sets to see; matching post length did not remove it.
Page v26 (PEMNidbCam72v6qKC3GNBx) has it all in plain words.

**For you to decide next:** (a) more post sets of this design, or move on? (b) the length rule drops llama's
short posts (17 of 375 briefs) — lower the floor to 55? (c) third model (to tell WHICH model self-prefers) /
GPU machine when ready.

**What got done the night before** (every world PASSes `check_world.py`; everything pushed; page v9):
* Campaign finished: post sets 13-15 → **6 sets, 59,400 reactions** (LF-17..19). Agent sweep 10/25/50/75 done (LF-21).
* **Answer (LF-19): in the scroll design there is no reliable self-preference.** Like +2.7 [−1.2, +6.6];
  dislike −1.5 [−4.6, +1.3]. The mid-campaign "significant" dislike result did not survive sets 14-15.
  Per-set results swing widely (like −3 to +11); the small lean that exists tracks **post length** (gemma
  writes longer posts and gemma-played people like longer posts; where gemma's post is ~21 words longer the
  own-post boost is +8.7, where lengths match it is −0.6; LF-20). Pre-stated held-out test on sets 14-15
  (LD-12): gemma longer — yes; length taste — right direction, not confirmed; no self-preference there at all.
* **Same person, two AIs: they really do behave differently** (LF-22 retest): each AI agrees with itself
  (kappa 0.75 llama, 0.88 gemma) but not with the other (0.18). The model matters more than the persona.
* **~94 % of the uncertainty is which posts got written, not which people** (LF-19): more post sets help,
  more people barely do.
* **Speed (LF-21):** two full sims at once = ~5 % faster (chip already full); llama+gemma at the same time
  inside a world = ~8 %. Time is linear: 0.65 min per person per world. The real lever is the GPU machine.
  Analysis refresh made ~45x faster (same numbers); refreshes run on efficiency cores so runs aren't slowed.
* Harness: `--draw` (retests) and Ollama model digests in every manifest (needed before the GPU move).

**Decisions for Gordon (nothing changed without you):**
1. **Match post lengths** in future post sets: ask 75-85 words, reject outside 65-95 (gap 5 → 2.4 words; LF-22).
2. **More post sets instead of more people** — e.g. the first 50 of the same pinned 99 and twice the post
   sets for the same time (~30 % narrower ranges). You said the 99 must never change; this keeps the same
   people, only fewer of them. Your call.
3. **Add a third model**: with two, the fair test can't say WHICH model favours itself.
4. **Side-by-side vs scrolling**: night 1 (pick a favourite of 7 side by side) found +5.6 [+3.4, +7.8];
   scrolling one at a time finds ~0. A direct A/B on identical posts and people would show whether the
   format itself creates the bias.

**To resume after a stop** (start Ollama first — command below; re-running skips finished worlds and resumes
an unfinished one; set SEEDS to the post sets wanted):

    cd /Users/gordon/research/oasis
    SEEDS="16" nohup caffeinate -i examples/experiment/llm_bias/world_campaign.sh \
      >> data/llm_bias/campaign_v2.log 2>&1 &

Start Ollama like this (LF-14):
`OLLAMA_FLASH_ATTENTION=1 OLLAMA_NUM_PARALLEL=4 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=24h ollama serve > /tmp/ollama_serve.log 2>&1 &`

Night-1 design (pick-a-favourite, 7 models) found +5.6 [+3.4, +7.8] (LF-10).

Pages: design v2 **https://claude.ai/artifact/PEMNidbCam72v6qKC3GNBx** · design v1
**https://claude.ai/artifact/JRWXc8bgCYU6bXaV3okZC9**. Data: `data/llm_bias/export/`,
explained in `LLM_BIAS_DATA_DICTIONARY.md`.

**Next:** Gordon's decisions 1-4 above → next campaign design. After every post set: `check_world.py`,
then the refresh recipe at the end of LF-16. Later: SSH/GPU machine (model digests are now recorded).

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

### LD-13 — Gordon's decisions, 2026-09-26 ~05:50 (before leaving for the day)

1. **Match post lengths** in all new post sets: ask 75-85 words, reject and retry outside 65-95 (LF-21/22).
   Old sets 10-16 stay as they are; length-matched sets are reported separately.
2. **First 50 of the same pinned 99 people** per world (`--agents 50` = `core99()[:50]`), to fit more post
   sets per day (LF-19: posts, not people, drive the uncertainty).
3. **Run the side-by-side vs scroll A/B** (tests whether the display format creates the bias: night 1
   side-by-side +5.6 vs scroll ~0). Not chosen for now: third AI, more sets of the current design.
4. No GPU machine yet — everything stays on this Mac.
"Else keep going all day."

### LF-23 — Post set 16 (7 sets, 69,300 reactions): same answer

v2_s16_w0/w1 PASS (first worlds with Ollama model digests in the manifest). Like +2.4 [−1.3, +6.2] (p 0.18),
dislike −1.2 [−3.9, +1.5] (p 0.39). Length again takes the like term 1.19 → 0.46 (≈ +2.4 → +0.9 headline);
slot-level: gemma much longer +7.2, similar length +0.4 (rho 0.14, p 0.06). Posts still ~95 % of the
uncertainty. Page v10. **This closes the old design (60-120 words, 99 people).** Next: LD-13 A/B.

### LR — A/B campaign (LD-13) launched 2026-09-26 08:52

`ab_campaign.sh`, seeds 20-26, 50 people (first 50 of the pinned 99), length rule "ask 75-85, reject outside
65-95, up to 9 tries", `--complete-slots`. Per seed: scroll w0/w1 + pair w0/w1 (order alternates by seed).
~2 h per seed. Labels `ab_s<seed>_<format>_w<world>`; analysis `analyze_ab.py` → `data/llm_bias/analysis_ab.json`;
export `export_world.py --prefix ab_ --out data/llm_bias/export_ab`; checks appended to `data/llm_bias/ab_checks.txt`.
Smoke tests before launch: scroll regression on set 13 (2 people) 99 % identical answers (new code leaves scroll
unchanged); pair smoke on seed 20 (2 people): 96/96 valid rows, llama 2.2 s and gemma 0.6 s per call (2 posts).
Seed 20 bank: llama 69.3 words (65-84), gemma 74.9 (67-88) — gap 5.6 (llama undershoots; kept Gordon's rule as
approved); 1 llama post failed after 9 tries → slot (cars, r1) dropped from both formats.
Pair format: people pick the post shown first 60 % of the time (smoke); order is shuffled per person and slot.

### LF-24 — A/B post set 20 (first length-matched set; 9,600 reactions, 50 people, 24 briefs)

All 4 worlds PASS (check_world now compares speeds within format; the earlier WARNs were scroll-vs-pair
per-call speed mixing, a checker bug, fixed). Pair speed: llama 2.1-2.2 s and gemma 0.56 s per call (2 posts).

| measure (double difference, points) | estimate | 95 % range | p |
|---|---|---|---|
| scroll likes | **+10.5** | +2.9 to +18.9 | 0.005 |
| scroll dislikes | −5.3 | −12.7 to +0.9 | 0.11 |
| side-by-side likes | +9.3 | −1.6 to +20.5 | 0.09 |
| side-by-side dislikes | +1.0 | −7.4 to +9.1 | 0.74 |
| side-by-side favourite | +5.2 | −2.8 to +12.8 | 0.21 |
| **format effect, likes (pair − scroll)** | −1.2 | −12.0 to +9.8 | 0.83 |
| format effect, dislikes | +6.3 | −1.2 to +14.7 | 0.11 |

One set only — sets have swung from −3 to +11 on likes before (LF-18/19), so +10.5 is not evidence yet.
The favourite number (+5.2) is close to night 1's +5.6. **No format effect so far.**
Other: side by side makes llama far harsher (its people dislike 21 % of posts vs 5 % scrolling; gemma 6 vs 8 %),
and people pick the post shown first 72 % of the time (order shuffled, so noise not bias). Gemma-played
people pick gemma's post 57 %, llama-played pick llama's 48 %.
Page v12 shows the A/B section. Export `data/llm_bias/export_ab/`.

### LF-25 — A/B after 2 post sets (20-21; 18,800 reactions)

Set 21: 2 llama money posts never landed in 65-95 words after 9 tries → slots (personal_finance r1, r2)
dropped from all 4 worlds. All worlds PASS.

| measure | estimate | 95 % range | p |
|---|---|---|---|
| scroll likes | **+7.6** | +1.4 to +14.3 | 0.019 |
| scroll dislikes | −3.3 | −10.2 to +3.1 | 0.32 |
| side-by-side likes | **+10.0** | +1.7 to +18.1 | 0.019 |
| side-by-side dislikes | −2.0 | −8.3 to +3.6 | 0.52 |
| side-by-side favourite | +4.8 | −0.3 to +10.1 | 0.07 |
| **format effect, likes** | +2.3 | −6.2 to +10.7 | 0.59 |
| format effect, dislikes | +1.3 | −5.9 to +8.4 | 0.71 |

**No format effect.** Both formats now show a positive like number with length-matched posts — i.e. matching
length did NOT remove the lean. Caution: the old design also read +4 after its first 2 sets and settled near +2
over 7 (LF-18/19); two sets are two draws. Favourite shares: gemma-played pick gemma 55 %, llama-played pick
llama 50 %. Position 1 picked 73 %. Page v13.
*LF-25 check:* old design (sets 10-16) restricted to the first 50 people: like +2.6 [−1.1, +6.3], dislike −1.1 —
same as all 99 (+2.4 / −1.2). The A/B's higher like numbers are not from using 50 people.

### LF-26 — A/B after 3 post sets (20-22; 28,800 reactions): still no format effect; scroll like lean steady

| measure | estimate | 95 % range | p |
|---|---|---|---|
| scroll likes | **+6.9** | +1.6 to +12.6 | 0.013 |
| scroll dislikes | −2.8 | −8.1 to +2.2 | 0.29 |
| side-by-side likes | +6.2 | −1.1 to +13.4 | 0.11 |
| side-by-side favourite | +3.5 | −1.1 to +8.1 | 0.13 |
| **format effect, likes** | **−0.6** | −7.1 to +5.8 | 0.85 |

Per set (scroll likes / pair likes / pair favourite; words llama vs gemma):
20: +10.5 / +9.3 / +5.2 (69 vs 75) · 21: +4.6 / +10.6 / +4.3 (69 vs 72) · 22: +5.4 / −0.8 / +1.0 (69 vs 72).
The scroll like number is positive in every length-matched set so far, with the word gap down to 3-6 words.
So far: **the display format makes no difference**, and length matching has not removed the own-post like
lean. The earlier "length explains it" reading (LF-15..20) looks at best partial. Page v14.

### LF-27 — A/B after 4 post sets (20-23; 38,800 reactions): the format makes no difference

| measure | estimate | 95 % range | p |
|---|---|---|---|
| scroll likes | **+5.4** | +0.7 to +10.5 | 0.028 |
| scroll dislikes | −2.1 | −5.9 to +1.9 | 0.30 |
| side-by-side likes | +5.8 | −0.8 to +12.5 | 0.075 |
| side-by-side dislikes | −1.3 | −5.4 to +2.2 | 0.50 |
| side-by-side favourite | **+4.3** | +0.2 to +8.5 | 0.042 |
| **format effect, likes** | **+0.4** | **−5.5 to +6.2** | 0.94 |
| format effect, dislikes | +0.8 | −3.8 to +5.3 | 0.73 |

Reading: with length-matched posts, **both formats show the same small own-post like lean (~+5 per 100)**, and
the side-by-side favourite number (+4.3) is close to night 1's +5.6. The format effect is ~0 with a range that
now excludes differences bigger than about ±6. So night 1 vs scroll (+5.6 vs ~0 in the old design) is not
explained by format; the old design's scroll lean (+2.4 over 7 sets) and this one (+5.4 over 4) overlap.
Favourite shares: gemma-played pick gemma 54 %, llama-played pick llama 50 % — the lean is mostly gemma's.
Page v15.

### LF-28 — A/B after 5 post sets (20-24; 48,000 reactions)

Set 24: 2 cooking slots dropped (a llama post outside 65-95 after 9 tries). All worlds PASS.
Scroll likes **+5.4 [+0.9, +10.0]** (p 0.02); scroll dislikes −1.5 [−5.2, +2.4]; side-by-side likes +5.1
[−0.8, +11.0]; favourite +3.6 [−0.1, +7.4] (p 0.058); **format effect likes −0.2 [−5.4, +5.0], dislikes −0.1
[−4.0, +3.9]**. The format makes no difference; the like lean holds at ~+5 with length-matched posts.
Favourite shares: gemma-played pick gemma 52.8 %, llama-played pick llama 50.7 %. Position 1 picked 74 %.
Dropped slots so far: 1 + 2 + 0 + 0 + 2 = 5 of 125 (all llama posts that stayed short). Page v16.

### LF-29 — A/B after 6 post sets (20-25; 58,000 reactions)

Scroll likes **+4.6 [+0.3, +9.0]** (p 0.03); scroll dislikes −0.9 [−4.1, +2.2]; side-by-side likes +4.2
[−0.7, +9.2]; favourite +2.8 [−0.5, +6.2]; **format effect likes −0.4 [−4.8, +4.4], dislikes −0.7 [−4.6, +2.8]**.
The format still makes no difference, and the range keeps narrowing around zero. The like lean with
length-matched posts is drifting down as sets accumulate (+10.5 → +7.6 → +6.9 → +5.4 → +5.4 → +4.6), the same
pattern as the old design (early sets high, settling lower). Favourite shares now 51.7 / 51.1 %. Page v17.
Queued: seeds 27-30 of the same A/B after seed 26 (more sets narrow the answer; within LD-13).

### LF-30 — A/B after 7 post sets (20-26; 65,600 reactions): the format makes no difference

Scroll likes **+4.2 [+0.2, +8.2]** (p 0.04); scroll dislikes −1.0 [−4.0, +1.9]; side-by-side likes +3.2
[−1.5, +8.1]; favourite +2.6 [−0.3, +5.7]; **format effect likes −1.0 [−5.4, +3.3], dislikes −0.7 [−4.1, +2.8]**.
**Set 26 dropped 6 of 25 slots** (llama posts stuck at 47-64 words after 9 tries; llama averaged 4.6 tries per
post in that set vs 1.5-3.3 elsewhere). Checked: same failure mode as before (llama writes short for some
briefs), not a bug; both formats drop the same slots, so the format comparison is unaffected. Dropped so far:
11 of 175 slots, all llama-short. If this rule is reused, lower the floor to 55 or raise llama's retries.
Seeds 27-30 started automatically 22:29 (~2 h each, ETA ~06:30). Page v18.

### LF-31 — A/B after 8 post sets (20-27; 74,400 reactions)

Set 27: 3 slots dropped (llama short). All worlds PASS. Scroll likes **+3.9 [+0.1, +7.5]** (p 0.047); side-by-side
likes +2.1 [−2.4, +6.5]; favourite +1.8 [−1.1, +4.8]; **format effect likes −1.8 [−5.8, +2.1], dislikes −0.9
[−4.1, +2.0]**. No format effect; the like lean keeps drifting down (+4.2 → +3.9 scroll; favourite +2.6 → +1.8).
Favourite shares 50.5 / 51.3 % — essentially even. Page v19.

### LF-32 — A/B after 9 post sets (20-28; 84,000 reactions)

Set 28: 1 slot dropped. All PASS. Scroll likes **+4.6 [+1.2, +8.0]** (p 0.008); scroll dislikes −1.5
[−4.0, +1.1]; side-by-side likes +2.5 [−2.0, +7.1]; favourite +1.6 [−1.0, +4.4]; **format effect likes −2.1
[−6.1, +1.8], dislikes −0.1 [−3.0, +2.7]**. Still no format effect. With length-matched posts, the one-at-a-time
like lean (~+4.6) is now steadier than in the old design — the side-by-side one is smaller and not clear of zero.
Page v20.

### LF-33 — A/B after 10 post sets (20-29; 92,800 reactions)

Set 29: 3 slots dropped. All PASS. Scroll likes **+4.2 [+1.0, +7.4]** (p 0.011); scroll dislikes −1.5
[−3.8, +0.8]; side-by-side likes +1.9 [−2.3, +6.1]; favourite +1.4 [−1.3, +4.0]; **format effect likes −2.2
[−6.1, +1.5], dislikes −0.2 [−3.0, +2.6]**. Stable picture: no format effect; a small one-at-a-time like lean
(~+4) with length-matched posts; side by side smaller and not clear of zero. Page v21. Seed 30 running (last queued).

### LF-34 — A/B after 11 post sets (20-30; 102,000 reactions)

Set 30: 2 slots dropped. All PASS. Scroll likes **+4.3 [+1.1, +7.5]** (p 0.006); scroll dislikes −1.9
[−4.3, +0.5]; side-by-side likes +1.7 [−2.3, +5.5]; favourite +1.6 [−1.0, +4.1]; **format effect likes −2.7
[−6.3, +0.7] (p 0.12), dislikes +0.2 [−2.5, +2.8]**. If anything, side by side shows slightly LESS own-post
liking than one at a time — the opposite of the night-1 idea — but not clearly. Page v22.
Seeds 31-34 queued and started 06:13 (same A/B; ETA ~14:00). Stop with `pkill -f ab_campaign.sh`.

### LF-35 — A/B after 12 post sets (20-31; 111,200 reactions)

Set 31: 2 slots dropped. All PASS. Scroll likes **+5.2 [+2.0, +8.3]** (p < 0.001); scroll dislikes **−2.4
[−4.7, −0.1]** (p 0.046); side-by-side likes +2.5 [−1.4, +6.5]; favourite +2.1 [−0.4, +4.5]; format effect likes
−2.6 [−6.2, +0.7], dislikes +0.4 [−2.4, +3.2]. With length-matched posts the one-at-a-time lean now shows on both
likes and dislikes; still no clear format effect. Page v23.

### LF-36 — A/B after 13 post sets (20-32; 120,800 reactions)

Set 32: 1 slot dropped. All PASS. Scroll likes **+5.1 [+2.1, +8.1]**; scroll dislikes −2.1 [−4.5, +0.1];
side-by-side likes +2.9 [−0.6, +6.9]; favourite +2.3 [−0.1, +4.7] (p 0.054); format effect likes −2.2
[−5.5, +1.2], dislikes +0.3 [−2.2, +2.8]. Stable: no format effect; one-at-a-time like lean ~+5. Page v24.

### LF-37 — A/B after 14 post sets (20-33; 130,400 reactions)

Set 33: 1 slot dropped. All PASS. Scroll likes **+5.4 [+2.5, +8.7]**; scroll dislikes −2.0 [−4.2, +0.1];
side-by-side likes +2.9 [−0.5, +6.7]; favourite **+2.3 [+0.0, +4.5]** (p 0.046); format effect likes −2.5
[−5.9, +0.7], dislikes +0.2 [−2.1, +2.8]. Unchanged picture. Page v25. Seed 34 (last queued) running, ETA ~14:15.

### LF-38 — A/B COMPLETE: 15 post sets (20-34; 140,000 reactions). Format doesn't matter; a small own-post lean is real

Set 34: 1 slot dropped. All 60 A/B worlds PASS. Dropped slots in total: 17 of 375 (all llama posts that stayed
under 65 words after 9 tries; same slots dropped from both formats).

| measure (double difference, points per 100) | estimate | 95 % range | p |
|---|---|---|---|
| scroll likes | **+5.2** | +2.4 to +8.1 | 0.001 |
| scroll dislikes | **−2.3** | −4.3 to −0.1 | 0.038 |
| side-by-side likes | **+3.4** | +0.0 to +6.8 | 0.049 |
| side-by-side dislikes | −1.9 | −3.8 to +0.1 | 0.06 |
| side-by-side favourite | **+2.4** | +0.3 to +4.6 | 0.025 |
| **format effect, likes (pair − scroll)** | **−1.8** | −5.0 to +1.3 | 0.24 |
| format effect, dislikes | +0.4 | −1.9 to +2.7 | 0.71 |

**Conclusions (LD-13 question answered):**
1. **Display format does not create self-preference.** Showing the two sibling posts side by side changes the
   own-post lean by −1.8 [−5.0, +1.3] — no effect, and any effect larger than ~5 points is ruled out.
2. **With length-matched posts, a small own-post preference is real in both formats**: about +5 likes and −2
   dislikes per 100 when scrolling, about +3 likes and +2.4 favourite picks side by side. Length matching did
   NOT remove it (so LF-15..20's "length explains it" was at most partial).
3. It is **small** — a few reactions per 100 — and **needed ~10+ post sets to see**, because which posts get
   written dominates the uncertainty (LF-19). Single post sets swing far more than the effect itself.
4. The old design's +2.4 [−1.3, +6.2] (7 sets, 99 people) is consistent with the same small effect.
Side notes: llama is far harsher side by side (~20 % dislikes vs ~5 %); people pick the post shown first 75 %
of the time (shuffled, so noise not bias); favourite shares are near 50/50 for both models (51 %).
Page v26.

### LD-14 — Gordon's decisions, 2026-09-27 ~14:45: three AIs, natural posts

* **Third AI: mistral:7b** (Mistral AI; strongest self-preference on night 1, +14 [+6, +23]; independent of
  Meta/Google). llama3.1:8b, gemma4:e2b and mistral:7b each write posts AND play people.
* **Posts have no rules except being on the requested topic**: no word limits, no sentence/format limits
  ("pure whatever that LLM is thinking"). A length rule may come later, set to the measured natural average,
  only when Gordon says so. Kept: "don't mention AI / model names, don't sign" (otherwise the author is visible,
  which breaks blinding). Dropped: title/body word limits, plain-text/no-emoji/no-bullets rule, markdown stripping.
* **Format: scroll** (one post at a time; the A/B showed format makes no difference, LF-38).
* **Rotation over 3 worlds** per post set: person i is played by judges[(i + world) % 3], so every person is
  played by every AI on the same posts.
* First 50 of the pinned 99 people; run until 09:00 2026-09-28, then report.

### LR — v3 (three AIs, natural posts) smoke test and launch, 2026-09-27

**Smoke test** (post set 40, world 0, 6 people, 3 judges; `run_world.py --natural-posts`): 75/75 natural posts
on the first or second try (no retries needed), 450/450 valid decisions, 0 cut off, 0 hidden thinking, PASS.
Natural post length (words): **llama 113** (74-164), **mistral 155** (62-306), **gemma 170** (92-311) — far
longer than under the old 60-120 rule; 10-13 of 25 posts per model use paragraphs/formatting.
Judging speed with the longer posts: llama 1.49 s, mistral 1.60 s, gemma 0.40 s per decision (4 parallel).
**Mistral as a judge likes almost everything: 94 % like, 2 % dislike, 4 % nothing; 91 % likes even on topics
the person dislikes** (llama 3 %, gemma 67-80 %). So mistral's own self-preference in likes has little room and
will be imprecise; as an author and as a comparison judge for llama/gemma it is fully usable. Reported, not
hidden; Gordon chose mistral (LD-14).
**Launched 17:58**: `v3_campaign.sh` seeds 40-45, 3 worlds each, ~3.7 h per post set → ~4 sets by 09:00.
Post set 40's bank is the smoke test's (same rule, reused).

### LD-15 — Analysis plan for v3, stated before any v3 result (2026-09-27 18:05)

* **Primary:** for each AI J, the like and dislike self-preference double difference (J's people on J's posts
  vs J's people on the other AIs' posts, minus the same gap for the other AIs' people), plus the pooled mean;
  95 % intervals from the persona x slot cluster bootstrap (`analyze_world.py --prefix v3_`). Only post sets
  with all 3 worlds finished. Reported per AI because, with three AIs, each gets its own number.
* **Stopping:** report whatever sets are complete at 09:00 2026-09-28; no conclusions from fewer than 3 sets
  (single sets swing far more than the effect, LF-18/19).
* **Secondary (labelled exploratory):** post length as a covariate (natural lengths differ a lot); by topic;
  by whether the person cares; mistral's like ceiling noted when reading its own number.
* Health check on every world; page and log refreshed after every post set.

**Artifacts brought up to date (2026-09-27 ~18:30):** Scroll Test page v28 — look-up tool now covers every test
(pick "Which test": test 2, A/B one-at-a-time, A/B side-by-side; the three-AI data joins after its first set),
handles 3 AIs; new "Newest test: three AIs" section (running); mistral colour magenta #c2378f / dark #d65aa4
(validated: CVD ΔE ≥ 10.4 vs blue and orange, all pairs, both themes; purple failed vs blue). Test-1 page v5 —
"later tests" box now summarises the scroll, A/B and three-AI tests. Data dictionary covers export_ab, pair
columns, export_v3 and the page data files.

### LF-39 — Three AIs, post set 40 (first set; 11,250 reactions) — NOT a conclusion (LD-15: wait for ≥3 sets)

3 worlds done 21:41 (~3.7 h). 11,248/11,250 valid (1 answer cut off; check WARN on w2 only for that).
Speed: llama 1.43, gemma 0.40, mistral 1.70 s/decision. Mistral liked 96 % in w2.

| AI | like self-preference | dislike |
|---|---|---|
| gemma | +7.9 [+1.0, +15.5] | −6.4 [−12.7, −1.0] |
| llama | +5.7 [−0.2, +12.3] | −5.4 [−11.2, −0.7] |
| mistral | +6.8 [+1.5, +12.3] | −0.9 [−4.0, +2.5] |
| pooled | **+6.8 [+2.5, +11.6]**, p 0.001 | −4.2 [−8.0, −0.9] |

One set only — single sets have overshot before (LF-18/19). Page v29 shows it with that warning; the three-AI
data is in the look-up tool. Power note: the Mac's 65 W charger can't keep up with sustained inference
(battery −4 to −6 W while plugged in, 78 % at 21:23); Gordon told how to reduce draw.

### LF-40 — Three AIs after 2 post sets (40-41; 22,500 reactions) — still under the 3-set minimum

Set 41 done 01:36 (3.9 h). 22,498/22,500 valid; set 41 worlds PASS.

| AI | like self-preference | dislike |
|---|---|---|
| gemma | +7.0 [+2.2, +12.3] | −4.6 [−8.8, −0.8] |
| llama | +4.4 [+0.4, +8.9] | −5.8 [−9.6, −2.4] |
| mistral | **+8.3 [+4.3, +12.8]** | −0.4 [−3.3, +2.4] |
| pooled | **+6.6 [+3.5, +9.8]** (p < 0.001) | −3.6 [−6.2, −1.2] |

All three lean toward their own posts in likes, including mistral despite liking ~95 % of everything (its
boost comes from liking OTHER AIs' posts a bit less). Llama and gemma also show it in dislikes. Page v30.
Timing: sets take ~3.9 h, so set 43 cannot finish by 09:00 (would end ~09:25).

### LF-41 — Three AIs, natural posts, 3 post sets (40-42; 33,750 reactions): every AI favours its own posts

Minimum of 3 sets met (LD-15). 33,748/33,750 valid; all 9 worlds done (WARNs are only 1-2 answers cut off at
the token limit per world). Campaign stopped 05:23 after set 42 (set 43 could not finish by 09:00; its first
world is partial on disk and resumable).

**Primary (LD-15): per-AI double difference, persona x brief cluster bootstrap**

| AI | like self-preference | dislike self-preference |
|---|---|---|
| gemma4:e2b | **+8.2 [+3.8, +12.6]** | **−4.3 [−7.8, −1.1]** |
| llama3.1:8b | **+5.7 [+2.1, +9.3]** | **−6.4 [−9.5, −3.4]** |
| mistral:7b | **+7.2 [+3.9, +10.4]** | −0.1 [−2.1, +2.0] (mistral almost never dislikes) |
| pooled | **+7.0 [+4.3, +9.7]**, p < 0.001 | **−3.6 [−5.8, −1.7]**, p < 0.001 |

**Consistent across sets** (pooled like: set 40 +6.8, set 41 +6.3, set 42 +7.8; every AI positive in every set)
— unlike the two-AI designs, where single sets swung from −3 to +11.
**Secondary (exploratory): post length.** Natural lengths: llama 117, mistral 161, gemma 163 words. Linear
model with post and person-x-AI fixed effects, clustered by brief: own-post term 4.67 [3.12, 6.22] → 3.92
[2.23, 5.62] after adding each AI's taste for length (gemma +4.2 per SD [+1.6, +6.9], mistral +1.5 [+0.2,
+2.8]). Length explains ~16 % of the like effect; the dislike effect is unchanged (−2.40 → −2.15). Saved in
`data/llm_bias/v3_length_check.json`.
**Reading:** with three AIs writing freely, each AI, when playing a person, likes its own AI's posts about 6-8
more times per 100 than the other AIs do, and dislikes them less (llama, gemma). It is not a length artefact.
Why the two-AI tests looked weaker: with two AIs the double difference pools both directions and set-to-set
noise was large; three AIs give three independent checks per set. Mechanism test (self-recognition) and a
retest are running now (morning chain). Page v31.

**LB-note (2026-09-28 05:40):** post banks for sets 21-34, 41 and 42 had been committed while the next set's
posts were still being written, so git held partial snapshots (+533 lines missing, 0 changed). The files on
disk were always complete and every analysis read the files on disk, so no result changes; the complete banks
are committed now. Rule from now on: commit a set's post bank only after that set's worlds finish.

### LF-42 — Three AIs: they can't reliably spot their own posts; each is self-consistent (morning checks)

**Self-recognition probe** (`recognize.py`, post sets 40-42, 3 posts per brief so guessing = 33 %, k = 4
shuffles per brief, 300 tries per AI; pooled with a brief bootstrap → `recognition_v3_pooled.json`):
gemma claims its own post 44 % (+5.0 vs how often the others claim that post [−1.3, +11.7]); mistral 39 %
(+4.3 [−1.5, +10.2]); llama 24 % (+2.2 [−4.2, +8.2]). **None clearly recognises its own writing** (all ranges
include 0), while all three clearly prefer it (LF-41) → **shared taste, not knowing favouritism** (same as LF-8).

**Retest** (`rt3_s40_w0-2`, people 0-19, `--draw 1`, all 3 worlds; `retest_v3_s40.json`): self-agreement
gemma 95 % (kappa 0.88), llama 85 % (0.72), mistral 97 % (0.73; its chance agreement is 89 % because it likes
nearly everything). Across AIs on the same person and post: llama-gemma 0.26, llama-mistral 0.10, gemma-mistral
0.21. Same pattern as LF-22: each AI is steady, different AIs play the same person differently.
Page v32 shows the length check, recognition and retest under the three-AI section.

**2026-09-28 08:43:** post set 43, world 0 finished (3,750 decisions, resumed from the 05:23 stop; check: 3,748 valid,
8 answers cut off at the 80-token cap, 2 of them still invalid after retries — mostly mistral's long reasons).
Campaign stopped at 08:43 before world 1 got going (world 1's 19 seconds are on disk, resumable). Set 43 needs
worlds 1-2 to count.

### LD-16 — Plan from here (brainstorm logged 2026-09-28 10:05; Gordon: "do these in order")

**Where we stand (LF-41/42):** with three AIs writing freely, every AI favours its own posts when playing a
person (≈ +6-8 likes per 100); steady across sets; not mainly length; not recognition (shared taste). Display
format doesn't matter (LF-38). Which AI plays a person matters far more than the persona text (LF-22/42).

**The plan, in order (each item reports back to Gordon):**
1. **Finish post set 43** (worlds 1-2 resumed 10:04). **Total fixed now, before more results: the three-AI
   campaign is 6 post sets (40-45)**; sets 44-45 follow after items 2-5. Result reported at 6 sets, whatever it is.
2. **What is the "taste"?** Existing data only: post features (length, paragraphs, questions vs statements,
   first person, numbers, exclamation, sentiment words, formatting) per author, and which features each AI's
   people reward. Exploratory.
3. **Same-company AIs:** add llama3.2:3b (llama3.1's sibling). Design + smoke test only until approved.
4. **What the bias does in a real feed:** OASIS feed with visible vote counts and ranking; does one AI's
   writing rise to the top? Design + smoke test only until approved.
5. **Persona vs AI:** variance decomposition of reactions (how much comes from the person's description,
   the AI playing them, the post, the topic) on existing data.
6. **Length rule (later, Gordon's call):** natural averages to report; no change to post writing.
7. **Bigger runs:** GPU machine + qwen/phi as writers and judges — plan and cost estimate only (no machine yet).
8. **Write-up:** plain-language report of the whole project (as a document).
Standing: rebuild the Scroll Test page around the current answer (three-AI result first, then every test in
order, every number with its source, data linked and viewable), 5th-grade language (Gordon, 2026-09-28).

### LF-43 — What is the "taste"? (LD-16 item 2; three-AI sets 40-42, 225 posts; exploratory) → `taste_v3.json`

`taste.py`: 11 simple post features (words, paragraphs, questions, title-is-question, exclamations, first-person
words per 100, numbers, formatting, words per sentence, happy/sad words per 100).
* **Fingerprints (means by author):** llama 117 words, 1.0 paragraph, 1.3 numbers; gemma 163 words, 2.1
  paragraphs, 1.5 questions; mistral 161 words, 2.0 paragraphs, **2.1 exclamations** (others 0.6-0.7), 1.8 numbers.
* **Tastes (like points per SD of the feature, person + topic held fixed, clustered by brief):** gemma's people
  dislike exclamations (−4.4 [−7.0, −1.8]) and first-person-heavy posts (−4.2 [−7.1, −1.3]), like numbers
  (+4.2 [+0.7, +7.7]); mistral's people like exclamations (+1.2 [+0.1, +2.4]), longer sentences (+2.3), happy
  words (+1.6); llama's people barely respond to any feature (all |effect| ≤ 1.2).
* **Taste vs own style** (correlation of each AI's feature tastes with how its own posts differ from the
  others'): gemma 0.38, mistral 0.35, llama −0.03.
* **How much do these features explain?** Own-post term 4.67 [3.12, 6.22] → 3.68 [1.68, 5.68] after giving
  each AI its own taste for all 11 features (post + person-x-AI fixed effects): **~21 % explained; ~79 % is
  something subtler** (word choice, voice) than these surface features.

### LF-44 — Person vs AI: where the variation comes from (LD-16 item 5; sets 40-42; exploratory) → `variance_v3.json`

`variance.py`: exact three-way split (AI x person x post, one reaction per cell; 33,744 reactions, 50 people,
225 posts). Share of the variance in "liked it":
AI 9.9 % · person 11.8 % · post 8.3 % · AI x person 6.1 % · AI x post 5.6 % · **person x post 26.7 %** ·
leftover 31.6 %. The retest (same AI, person and post, new draw; 4,499 pairs) puts pure randomness at **13.1 %**,
so ~18.5 % of the leftover is AI-specific quirks for particular person-post pairs.
Dislikes: AI 2.4 · person 4.3 · post 11.1 · AI x person 3.5 · AI x post 10.1 · person x post 27.6 · leftover 41.0.
**Summary (likes):** the person's description (person + person x post) **38.5 %**; which AI plays them directly
(AI + AI x person + AI x post) **21.6 %**, up to ~40 % if the AI-specific leftover is counted; post 8.3 %;
randomness 13.1 %.
**CORRECTION to LF-15/22/42 wording:** "the model matters more than the persona" was too strong — it came from
low cross-AI agreement (kappa). The decomposition shows the description matters most on its own, and which AI
plays the person matters about as much once its person-post quirks are counted. Pages updated to say
"about as much as".

**Page rebuilt around the answer (2026-09-28 ~10:45), Scroll Test v33:** opens with the three-AI result (one tile per
AI with its range), a "how to read the numbers" box, five key findings (every AI favours its own posts; not on purpose;
not mostly length/simple style; display format doesn't matter; who plays a person matters about as much as who they
are), then every test in order (test 1-4, each with its full details folded underneath), the look-up tool (table now
scrolls in its own box), timing charts (folded), links to every data file on GitHub, and what's next. Every number has a
"Where this comes from" line linking the exact file on the public repo.

**2026-09-28 ~10:55 — STOPPED at Gordon's request (needs the laptop for classes).** Killed the set-43 run (world 1
partial, resumable), Ollama and all background jobs. Nothing running.
Item 3 early result (existing night-1 data, `family_night1.json`): sibling preference llama3.2 -> llama3.1 favourite
picks +5.6 [+0.2, +10.8]; llama3.1 -> llama3.2 +1.8 [-1.8, +5.9]; on upvotes llama3.1 gives llama3.2's posts FEWER
(-11.8 [-23.1, -0.4]). Mixed; no clear "family loyalty". Remaining LD-16 items: 3 (new design), 4, 6, 7, 8.
Resume set 43: start Ollama (LF-14 settings), then `SEEDS="43" examples/experiment/llm_bias/v3_campaign.sh`.

### LD-17 — Designs for LD-16 items 3, 4, 6, 7 (2026-09-28; nothing run — laptop needed for classes)

Speeds used (measured, this Mac, 4 parallel, natural posts): llama3.1 1.43 s, gemma 0.40 s, mistral 1.70 s per
decision; llama3.2 ~0.75 s, qwen2.5 ~1.3 s, phi4-mini ~1.05 s (scaled from night-1 speeds).

**Item 6 — natural post length (sets 40-43, 300 posts):** all three AIs: mean 147, median 132, middle half
103-180 words. llama 117 (94-142), gemma 162 (126-196), mistral 162 (100-214). A later rule, if Gordon wants one,
would target ~130-150 words. No change to post writing until he says so.

**Item 3 — same-company AIs (does llama favour its sibling?).** Existing night-1 data (7 AIs, pick-a-favourite):
llama3.2 → llama3.1 favourite +5.6 [+0.2, +10.8]; llama3.1 → llama3.2 +1.8 [−1.8, +5.9]; upvotes llama3.1 →
llama3.2 −11.8 [−23.1, −0.4]. Mixed, no clear family loyalty (`family_night1.json`).
Proposed new test: add llama3.2:3b as a 4th AI to the three-AI design (writes + plays people), 4 rotation worlds,
natural posts, 100 posts per set. Family preference = llama3.1's people on llama3.2's posts vs how gemma/mistral
people treat those posts (and the reverse). Cost: 50 people ≈ 6 h per set; **25 people ≈ 3 h per set**
(people add little precision, LF-19) → recommend 25 people x 4 sets ≈ 12 h. Smoke test first (4 people, ~15 min).

**Item 4 — what the bias does in a real feed.** The usual real case: ONE AI plays the whole crowd. Design
(`run_feed.py`, to write): reuse the natural posts of sets 40-45 (no new writing). 50 people arrive one at a time
in a random order; each sees the current top 15 of the 75 posts ranked by score (likes − dislikes, visible "▲ 12
▼ 3" counts) and reacts to each; counts update before the next person. Crowds: all-llama, all-gemma, all-mistral;
control: counts hidden and random order. Outcome: share of the final top-10 written by each AI under each crowd —
"when llama runs the crowd, llama's posts take X of the top 10 vs Y under the other crowds", and whether visible
counts make it snowball. Cost: ~750 decisions per run, ~5-10 min; 3 crowds x 2 conditions x 6 post sets x 2
arrival orders = 72 runs ≈ 6-10 h. Smoke test: 1 run (~10 min).

**Item 7 — bigger runs.** Needs an NVIDIA GPU with 24 GB+ (e.g. RTX 4090, A5000, L4/A10G) reachable by SSH with
key login. Use Ollama with the same model digests recorded in every manifest (so it's the same weights), same
settings (LF-14). Before mixing machines: re-run one finished post set (e.g. 40) there and confirm ~99 % of answers
match (like the flash-attention check, LF-14). Then add qwen2.5:7b and phi4-mini:3.8b as writers + judges
(5 AIs → 5 worlds per set, 125 posts): ~10 h per set on this Mac, expected ~1-2 h on a 24 GB GPU.
Gordon to provide: host, username, and add the Mac's SSH key.

**LD-16 item 8 done (2026-09-28):** plain-language report "Do AIs Favour Their Own Writing?" as a Claude Doc:
https://claude.ai/code/artifact/7f61723e-b24b-4c68-871f-3510205cdbd4 — the question, how it works, the answer (per-AI
chart with ranges), five findings with source links, the four tests (table), how to read the numbers + where the data
lives, limits and corrections, what's next. Open question left for Gordon in a doc comment: run the feed test before
or after finishing the three-AI post sets? Items 3, 4, 7 are designed (LD-17) but not run; item 6 numbers in LD-17.

### LF-45 — Three AIs after 4 post sets (40-43; 45,000 reactions): still clear

44,993/45,000 valid. Like self-preference: gemma +6.5 [+2.4, +10.9], llama +4.9 [+1.6, +8.3], mistral +6.7
[+3.9, +9.8], **pooled +6.0 [+3.6, +8.7]**. Dislikes: llama −5.3 [−8.3, −2.7], gemma −3.3 [−6.6, −0.0], mistral
−0.5, pooled −3.0 [−4.9, −1.2]. Page v34. Sets 44-45 running (started 16:16, ETA ~00:15).
**Feed test (LD-17 item 4):** `run_feed.py` smoke on set 40, llama crowd, 6 people: 90/90 valid both modes, counts
shown up to 5 likes, ~2.4 min → 50 people ≈ 20 min (llama), ~6 (gemma), ~24 (mistral). Full run queued after
sets 44-45: sets 40-43 x crowds llama/gemma/mistral x visible/hidden = 24 runs (~7 h, ETA ~07:00),
`data/llm_bias/feeds/`, progress in `data/llm_bias/feed_campaign.log`.

### LF-46 — Three AIs, FINAL (6 post sets 40-45, the pre-fixed total; 67,500 reactions)

67,489/67,500 valid; no world FAILs (WARNs = 1-4 answers per world cut off at the 80-token cap).

| AI | like self-preference | dislike self-preference |
|---|---|---|
| gemma4:e2b | **+6.4 [+3.1, +10.0]** | −3.1 [−5.9, −0.5] |
| llama3.1:8b | **+5.7 [+2.9, +9.0]** | −5.2 [−7.8, −3.1] |
| mistral:7b | **+8.4 [+5.8, +11.6]** | −0.8 [−2.5, +0.6] |
| pooled | **+6.8 [+4.6, +9.4]**, p < 0.001 | **−3.1 [−4.8, −1.6]**, p < 0.001 |

The answer stated in LD-15 terms: **every AI, when it plays a person, likes its own AI's posts ~6-8 more times per
100 than the other AIs do, and (llama, gemma) dislikes them less.** The 3-set result (LF-41, +7.0) held at 6 sets.
Page v35. Feed test running (started 23:52).

### LF-47 — Feed test (LD-17 item 4): one AI plays the whole crowd; its own posts move up

`run_feed.py`, post sets 40-43 (natural three-AI posts, 75 per set), 50 people, feed of 15, crowds llama / gemma /
mistral, like counts visible (feed = current top 15 by likes − dislikes) or hidden (random 15, no counts); 24 runs,
18,000 decisions, **0 invalid**. `analyze_feed.py` → `analysis_feed.json` (intervals resample post sets; only 4).

| | counts hidden | counts visible |
|---|---|---|
| fair like boost for the crowd's own AI (double difference) | **+7.2 [+4.9, +9.6]** per 100 | **+4.8 [+1.9, +8.3]** |
| per crowd (llama / gemma / mistral) | +6.7 / +6.8 / +7.9 | −0.2 / +3.5 / +11.2 |
| extra top-10 places for the crowd's own AI | ~0.9 of 10 [−0.1, +1.8] | ~0.5 of 10 [+0.1, +0.9] |
| share of all likes going to the final top 10 | 22 % | **72 %** |

Reading: when one AI runs the crowd, its own AI's posts get more likes (hidden counts reproduce the main test's
+6.8) and more of the top spots. Visible counts make people follow the crowd — the top 10 soak up 72 % of likes
and the first few arrivals largely fix the ranking — which dilutes each AI's own taste (the boost shrinks to +4.8).
Fix during analysis: the first version compared raw like rates across crowds, which mostly measured how generous
each AI is (mistral likes ~98 %); corrected to the double difference before reporting.
Pages: Scroll Test v36 (finding 6, test 5); report doc updated (6 sets, finding 6, test 5, next steps).
**All LD-16 items done except 3 (sibling test: designed, not run) and 7 (needs a GPU machine). Everything stopped
06:26 2026-09-29: Ollama and all jobs shut down, per Gordon ("stop when you finish all tasks").**

---

### LD-18 — Two AIs, 100 users, new posts every round (Gordon, 2026-09-30 23:00-23:30)

Gordon's spec, in his words where it matters: "100 hard coded users ... never changed or altered"; "5 topics";
"each model will write 5 posts each for each topic"; "the users will then go through ALL posts like a reddit feed,
one by one scroll"; "the AI models will generate new posts every round, nothing about the post should be reused";
"the users will be played by each AI model ... they don't know or care where the post came from, they just judge
the post based off their personality and the AI model controlling them"; "upvote, downvote, nothing"; "add a second
AI, whatever is second fastest, because we need comparisons"; "use the fastest 2 AIs available, free and open
source"; 10-15 rounds; "keep all data and document it thoroughly". Full control until 15:00 2026-10-01.

Answers he picked (23:20): speed-test the small models first; each round's feed is only that round's 50 new posts;
keep the shared per-slot angle (both AIs get the same angle/post-type/voice in a slot, new angles every round).

Design as built:
* **Users:** the 100 pinned users = the pinned 99 + bank #99 (`personas.core100()`, hash f51d2b0a1f7d; refuses to
  run if any of the 100 changed). Same 100 in every round, for both AIs.
* **Round r** uses post seed 200+r: each AI writes 5 natural posts (no length/format rule; only on topic) for each
  of the 5 topics → 50 brand-new posts. A slot is dropped only if an AI fails to write its post after 4 tries.
* **Then AI A plays all 100 users** through all 50 posts (best-loved topic first, posts shuffled per user, one post
  per call, upvote/downvote/nothing + reason; author and vote counts never shown), **then AI B plays the same 100
  users** on the same 50 posts. 10,000 decisions per round. World labels `two_rNN_<model>`.
* Rounds are independent (no memory carried over; users never change).
* Code: `two_ai_campaign.sh` (rounds, stops before starting a round that can't finish by 15:00),
  `two_ai_after_round.sh` (round time, check_world, analyze_world, commit + push each round), `speed_pick.py`.
* Not done: an aborted earlier start (one AI only, old post set 40, 23:00) was killed after ~50 s on Gordon's
  word and deleted; no data from it is kept.
* **Briefs never reused (Gordon 23:35: "each round the AI models should make new posts").** Only 12 angles per
  topic exist (16 finance) and 15 rounds need 75 slots, so `slot_brief` numbers briefs across the campaign for
  seeds > 200: all 12 angles are used before any repeats, and each slot gets its own (post type, voice) pair from the
  84 available, so no full brief is ever reused (checked: 75 unique per topic). Old banks (seed ≤ 200) are byte-for-byte
  unchanged (checked). Posts are always newly written; users have no memory (each vote is one stateless call with
  only the fixed personality + that one post).

### LR-? Speed pick + launch (2026-09-30 23:40-23:54)

`speed_pick.py` (40 votes + 2 natural posts per model, real prompts, 4 in parallel; `data/llm_bias/speed_pick.json`).
Every model gave 100 % readable answers and 2/2 posts. Seconds per vote: gemma3:1b 0.36, gemma4:e2b 0.53,
llama3.2:1b 0.92, granite4.1:3b 1.13, llama3.2:3b 1.19, qwen2.5:1.5b 1.23, qwen2.5:3b 1.47, phi4-mini 1.80,
llama3.1:8b 1.97 (absolute numbers include warm-up at this small size; the ranking is what was used).
**Chosen: gemma4:e2b + gemma3:1b** (the two fastest, per Gordon "use the fastest 2 AIs available"). Caveat to report:
both are Google Gemma models (siblings), so "own AI" here partly means "own family"; llama3.2:1b (next fastest, other
family) would have fitted only ~8 rounds before 15:00.
Smoke (5 users, seed 299, both AIs, deleted after): 480 votes, 0 broken; 49/50 posts (one gemma3 finance post failed
5 tries → that slot dropped for both AIs); 49 unique bodies; gemma3 posts read as normal Reddit posts.
Campaign launched 23:53: `A=gemma4:e2b B=gemma3:1b STOP_AT="2026-10-01 14:30" two_ai_campaign.sh`, rounds 1-15,
seeds 201-215, no new round started unless its measured duration fits before 14:30.

### LR progress, LD-18 rounds (appended as they finish)
| round | finished | minutes | votes valid | gemma4 like/dislike/nothing | gemma3 like/dislike/nothing | checks |
|---|---|---|---|---|---|---|
| 1 | 01:08 | 68 | 10,000/10,000 | 3945/512/543 | 3140/1103/757 | PASS both |
| 2 | 02:22 | 68 | 10,000/10,000 | see analysis | 3787/718/495 | PASS both (4 gemma3 replies cut off at the token limit, all retried OK) |
After 2 rounds: like boost +3.4 pts (both rounds positive), dislike −4.2; same user + post, two AIs agree 66 % (κ 0.21).
Fix 02:30: `two_ai_after_round.sh` now runs check/analysis/page/commit in the background (it held the next round ~4 min).
Results page (rebuilt every round): https://claude.ai/artifact/HPmkfevmeC3LTYWhN4citW. Report doc: new tab "Test 6".

### LD-19 — Final-analysis plan for LD-18, stated 2026-10-01 03:55 (after 3 of ~12 rounds, before the rest)
1. **Primary:** own-AI double difference on upvotes and downvotes, pooled over all finished rounds. 95 % interval =
   the WIDER of (a) whole-round bootstrap and (b) two-way user × slot bootstrap (correction: the page/doc first called
   the round bootstrap "main and strictest"; with 3 rounds it is the narrower one — fixed on page v3 and in the doc).
   "Real" = the wider interval excludes zero.
2. **Secondary:** the length-adjusted boost = intercept of slot double difference ~ word gap (round-clustered).
   Seen after 3 rounds: raw +3.0, at equal length +13.8 — explained by opposite length tastes (author held fixed,
   per +100 words: gemma4-played users +8.3, gemma3-played users −15.8; gemma3 writes ~45 words longer). Will be
   reported whatever it is at the end; not used to pick the headline.
3. Also reported: per-round values, rounds positive, by subreddit (descriptive only, 5 tests, no correction → not
   claimed), agreement (κ), top-10 share, interest gradient, timing, failures.
| 3 | 03:38 | 66 | 10,000/10,000 | — | 3568/759/673 | PASS both |
| 4 | 04:54 | 69 | 10,000/10,000 | — | 3034/884/1082 | PASS both |
| 5 | 06:05 | 63 | 9,600/9,600 (1 slot dropped: gemma3 tech post failed 5 tries) | — | 4238/204/358 | gemma4 PASS; gemma3 WARN (like 88 % vs ~67 % before) |
**Round-5 WARN checked (06:10):** not a harness fault — same context (8192), same prompt sizes (~660 tokens), 0 failed
answers. gemma3:1b's overall generosity simply swings with the post batch (like 61 % in r4 → 88 % in r5; r/cars 40 % →
90 %), while gemma4 went 81 % → 71 %. The double difference compares within a round, so this cancels; it is also why
per-round values vary. After 5 rounds: like +6.4 (5/5 rounds positive; wider 95 % interval [−1.0, +13.9]), dislike −5.5,
at equal length +17.7; length taste per +100 words: gemma4-users +12.5, gemma3-users −16.2.
| 6 | 07:16 | 67 | 10,000/10,000 | — | 4283/406/311 | gemma4 PASS; gemma3 WARN (like 86 %) |
**Drift check (07:25, `drift_check.py two_r01_gemma3 200`):** 200 random round-1 gemma3 votes replayed with the same
seeds and settings at 07:20 → 97.0 % identical answers and identical totals (127 like / 44 dislike / 29 nothing). The
AI has not drifted overnight; the high gemma3 like rates in rounds 5-6 come from those rounds' posts.
**After 6 rounds:** like +6.6, 6/6 rounds positive, wider 95 % interval (user × slot) [+0.7, +13.1] → clears zero
(LD-19 rule); dislike −5.5; at equal length +15.6; κ 0.19.
| 7 | 08:32 | 69 | 10,000/10,000 | — | 3637/816/547 | gemma4 PASS; gemma3 WARN (73 %) |
| 8 | 09:46 | 65 | 9,600/9,600 (1 slot dropped) | — | 3801/695/304 | gemma4 PASS; gemma3 WARN (79 %) — first round with like boost ≤ 0 |
| 9 | 10:57 | 64 | 9,600/9,600 (1 slot dropped) | — | 3687/378/735 | gemma4 PASS; gemma3 WARN (77 %) |
| 10 | 12:06 | 66 | 10,000/10,000 | — | 3989/601/410 | gemma4 PASS; gemma3 WARN (80 %) |
(gemma3 WARNs = its like rate is above the baseline formed by rounds 1-4; drift ruled out at 07:25.)
**After 10 rounds (98,800 votes, 0 invalid, 497 posts, 0 duplicates, 3 slots dropped):** like +6.3, 9/10 rounds positive,
wider 95 % [+1.7, +11.2]; dislike −4.2; at equal length +11.8; κ 0.19; top-10 own posts: gemma4 crowd 6.9, gemma3 crowd 5.4.

| 11 | 13:22 | 70 | 10,000/10,000 | — | 3682/894/424 | PASS both |
Campaign stopped itself 13:22 ("round 12 needs 4167 s, 4089 s left"). gemma4 replay check 13:30: 99.5 % identical.

### LF-48 — LD-18 final: two AIs, 100 users, new posts every round → own-AI boost is real (2026-10-01 13:45)

11 rounds (seeds 201-211), 108,800 votes (0 failed), 547 posts (0 duplicate bodies; 3 gemma3 posts failed → 3 slots
dropped for both AIs), 100 pinned users, gemma4:e2b + gemma3:1b. `analyze_two_ai.py 2000` → data/llm_bias/two_ai/.
Checks: 14 PASS, 8 WARN (gemma3 like-rate swings by batch), 0 FAIL. Replay: gemma3 97.0 %, gemma4 99.5 % identical.

| | estimate | wider 95 % (LD-19 rule) | round bootstrap | rounds |
|---|---|---|---|---|
| own-AI upvote boost | **+7.1** | [+2.9, +11.5] (user×slot), p = 0.002 | [+4.5, +9.9] | 10/11 positive |
| own-AI downvote change | **−4.7** | [−7.6, −1.9], p = 0.001 | [−6.2, −3.4] | 11/11 negative |
| upvote boost at equal length | +12.5 | [+8.0, +17.1] (round-clustered) | | |

* Who: gemma4-users upvote gemma4 posts 81.2 % vs 74.9 % (+6.3) and downvote them 6.2 % vs 14.1 %; gemma3-users
  75.5 % vs 74.7 % (+0.8) and downvote their own AI's posts MORE (13.3 % vs 10.1 %).
* Length (pre-stated LD-19 secondary): gemma3 writes 194 words vs 164; per +100 words, author fixed: gemma4-users
  +10.7 [+6.6, +14.7], gemma3-users −15.1 [−19.8, −10.4] → length hides part of the boost.
* Same user + same post, two AIs: 68.2 % same choice, κ 0.18. Interest gradient: gemma4 56 → 85 %, gemma3 69 → 80 %.
* Top 10 by score: gemma4 crowd 6.8 own posts, gemma3 crowd 5.3 (fair = 5).
* By subreddit (descriptive): farming +9.9, cooking +9.7, cars +8.8, tech +3.9, finance +3.1 — all positive.
* Cost: 66.6 min/round (62.5-69.5); 0.45 s/vote gemma4, 0.37 gemma3; 13.5 h total.
* Matches the earlier three-family test (LF-46 +6.8) in size. Caveat: both AIs are Gemma (siblings).
Pages: results page v11 https://claude.ai/artifact/HPmkfevmeC3LTYWhN4citW (final); report doc tab "Test 6" filled
(answer, design, method, results + 3 charts, quality/cost, limitations + 5 improvements, data); main tab table has a
Test 6 row and says "six tests".
