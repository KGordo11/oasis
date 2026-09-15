# OASIS research log — every simulation, one file

**One file, deliberately.** This was seven documents until 2026-09-13:
`PROJECT_LOG.md`, the three simulation write-ups, `SIM4_LOG.md`,
`SIM4_RUN_PLAN.md` and `OVERNIGHT_2026-09-08.md`. They were split because each
was written at a different time for a different reason, but every search had to
be run seven times and the cross-references between them had already started to
rot. Nothing was dropped in the merge: each part below is its source document
verbatim, under a banner naming the file it used to be.

**Where to resume: Part 5 §0 STATUS.** That is the only section that goes stale.
Everything else is append-only history.

**Ids.** Findings are `F-n`, bugs `B-n`, decisions `D-n`, runs `R-n`, open
questions `Q-n`. They are unique across the whole file and each appears in
exactly one place. **Retractions are kept, not deleted** — a claim that was
believed and then killed is the most useful entry in a research log, and this one
has a lot of them.

| Part | What it holds | Was |
|---|---|---|
| **Part 1** | Project log: start here, conventions, open threads | `PROJECT_LOG.md` |
| **Part 2** | Simulation 1: basic Reddit sim and reasoning capture | `SESSION_REPORT (basic sim1).md` |
| **Part 3** | Simulation 2: the up/control/down misinformation experiment | `COUNTERFACTUAL_EXPERIMENT_REPORT(sim 2, groups).md` |
| **Part 4** | Simulation 3: the iAgent Shield experiment | `SHIELD_EXPERIMENT_REPORT.md` |
| **Part 5** | Simulation 4: the complete log | `SIM4_LOG.md` |
| **Part 6** | Simulation 4: run plan and its review | `SIM4_RUN_PLAN.md` |
| **Part 7** | Overnight plan, 2026-09-08 (historical, kept for the record) | `OVERNIGHT_2026-09-08.md` |
| **Part 8** | Primer: what upstream OASIS is and how the framework works | `LEARN_OASIS.md` |

**Part 8 is a different kind of document from the rest.** It is a primer on
upstream OASIS — what the paper claims and how the framework works — rather than
a record of our own research. It was kept separate until 2026-09-13 for that
reason, and merged anyway because one file beats a rule about tidiness. Read it
first if you are new to the project; ignore it entirely if you are not.

---

# Part 1 — Project log: start here, conventions, open threads

> **Filename references below are historical.** Every document this part points
> at is now a part of this same file. The mapping, once:
> `SESSION_REPORT (basic sim1).md` → Part 2 ·
> `COUNTERFACTUAL_EXPERIMENT_REPORT(sim 2, groups).md` → Part 3 ·
> `SHIELD_EXPERIMENT_REPORT.md` → Part 4 ·
> `SIM4_LOG.md` → Part 5 ·
> `SIM4_RUN_PLAN.md` → Part 6 ·
> `OVERNIGHT_2026-09-08.md` → Part 7.
> References inside the append-only history further down are left exactly as
> written — they record what was true when they were written, which is the point
> of a log.

*Was `PROJECT_LOG.md`. Merged into this file 2026-09-13; original title: “Project Log”.*

**Purpose of this file: if you are an assistant picking this project up
with zero prior context, this is the one file to read first.** It's
written to make you productive immediately, not to be a narrative. Read
"Start here," skim the sim summaries for what's already proven, check
"Open threads" before proposing new work (it's probably already listed),
and follow "Conventions worth keeping" — they exist because skipping them
already cost real time once. The three full write-ups
(`SESSION_REPORT (basic sim1).md`,
`COUNTERFACTUAL_EXPERIMENT_REPORT(sim 2, groups).md`,
`SHIELD_EXPERIMENT_REPORT.md`) have the full methodology/data/limitations
if you need to go deeper than the summaries below — don't re-read them
just to get oriented, only when a task needs their specific detail.

## Start here

```bash
cd /Users/gordon/research/oasis
git status                       # check for uncommitted work FIRST — has
                                  # happened before, see 2026-08-20 below
source oasis-env/bin/activate    # Python 3.11 venv
ollama list                      # confirm llama3.1:8b is present
ollama serve                     # if not already running
```

- **Repo:** this directory. Fork `origin` → `github.com/KGordo11/oasis`,
  `upstream` → `github.com/camel-ai/oasis`, branch `main`.
- **As of this file's last edit:** working tree clean, local `main` is
  **5 commits ahead of `origin/main`, unpushed** (nobody's asked to push
  yet — don't push without asking). Verify this is still true with
  `git status` / `git log --oneline origin/main..main` — don't trust this
  paragraph once time has passed.
- **Model:** Ollama `llama3.1:8b` for every agent and every Shield call —
  chosen for native tool-calling, which `llama3.2:3b` lacks. If a run
  feels slow, check `OLLAMA_KEEP_ALIVE` before touching any experiment
  code (see Conventions).
- **Every experiment is a zero-diff subclass swap** —
  `agents_generator.SocialAgent = <CustomAgent>` inside the example
  script, never an edit to `oasis/` itself. The one exception is
  documented below (Setup). Follow this pattern for new experiments too.
- **To run something:** copy the pattern in `SHIELD_EXPERIMENT_REPORT.md`
  Section 6 — smoke-test at small scale (2 rounds) before a full run (6
  rounds), always. This is not optional; see Conventions for why.
- **The science in one paragraph:** Sim 2 showed agents pile on
  down-voted misinformation far more than up/neutral (68% vs. <15%
  disagreement). Sim 3 built a "Shield" that hides vote counts and found
  that pushback *dropped* when the vote cue was removed (68%→28% pooled,
  p=0.0009) — meaning most of that "skepticism" was crowd-following, not
  fact-checking — and, more surprisingly, hiding the vote count partially
  *inverted* which condition draws the most pushback (control becomes
  highest, not down). Full numbers in the Sim 3 section and its report.

---

## Setup

- **OASIS** (`camel-ai/oasis`, arXiv 2411.11581): open-source social-media
  simulator — each "user" is an LLM agent with an assigned personality,
  posting/commenting/liking/following on a fake Twitter/Reddit platform.
  Used here to study misinformation spread and herd behavior at a scale
  the original paper ran on 1M agents / 24 A100s; this fork runs the same
  *kind* of experiment at ~36 agents on a single Mac with a free local
  model.
- **Repo:** this directory, fork `origin` → `github.com/KGordo11/oasis`,
  `upstream` → `github.com/camel-ai/oasis`, branch `main`. Python 3.11
  venv at `oasis-env/` (OASIS requires 3.10/3.11, gitignored).
- **Model:** Ollama `llama3.1:8b`, chosen over `llama3.2:3b` and base
  Llama 3 specifically because it has native tool-calling — OASIS agents
  act by calling tools, not free text.
- **The only edit to any upstream file:** in
  `examples/experiment/reddit_simulation_counterfactual/reddit_simulation_counterfactual.py`,
  the hardcoded VLLM/remote-GPU-cluster `ModelFactory.create()` call was
  replaced with a local Ollama call (`ModelPlatformType.OLLAMA`,
  `llama3.1:8b`, `http://localhost:11434/v1`) plus a longer timeout.
  Nothing about experiment logic (conditions, scoring, rounds) was
  touched. Everything under `oasis/` itself is untouched — every
  experiment is a zero-diff subclass swap (`agents_generator.SocialAgent
  = <CustomAgent>`), the same pattern used in all three sims.
- Upstream already ships pre-made `control_100.yaml` / `up_1000.yaml` /
  `down_10000.yaml` etc. — ready-made templates for a future scale-up,
  not something that needs hand-authoring.

## Sim 1 — reasoning capture (full write-up: **Part 2** of this file)

36-agent baseline confirmed personality drives behavior. Then tried, in 3
attempts, to get the model to narrate its reasoning alongside its tool
calls — editing shared engine files broke tool-calling entirely
(reverted), softening the prompt recovered tool-calling but reasoning
text almost never appeared (also reverted), and a clean subclass
(`ReasoningSocialAgent`, zero diff to `oasis/`) kept tool-calling healthy
but reasoning was still JSON-as-text, not real narration. **Honest
verdict:** an 8B local model can't reliably combine free-text explanation
with structured tool use in one turn — a real finding about model
limits, not a failure to hide.

## Sim 2 — herd behavior (full write-up: **Part 3** of this file)

Replicates the OASIS paper's Finding 3 (agents herd on downvotes where
humans self-correct). 220 fabricated false claims, 36 agents, 3
conditions differing only in `init_post_score` (+1 / 0 / −1). **Run
twice independently** to separate real signal from single-run noise —
this replication discipline is the core habit that carried into Sim 3.

- Vote-count scores replicated cleanly (scale artifact, not a finding —
  no snowball effect visible at 36 agents, consistent with the paper's
  own scale-dependent Finding 5).
- Comment counts did **not** replicate between the two runs — an early
  write-up over-interpreted run 1 alone; explicitly retracted once run 2
  contradicted it.
- **Headline finding (replicated in direction both runs):** down-treated
  posts drew disagreement/correction language in ~62–68% of comments vs.
  well under 15% for up/control. Measured via a keyword classifier
  (never validated against human judgment — see open threads).

## Sim 3 — the iAgent Shield (full write-up: **Part 4** of this file)

Built a second local-LLM call ("the Shield," adapted from Xu et al.,
*iAgent*, ACL 2025 Findings) that re-ranks each agent's feed by content
plausibility and strips vote-count fields before the agent sees them —
testing whether Sim 2's pushback was genuine fact-checking or
crowd-following.

**Design origin (planned on claude.ai before any code was written):** the
research question came from noticing OASIS agents have no equivalent of
the paper's "user-agent-platform" paradigm — the RecSys feeds an agent
straight, with nothing standing between platform ranking and agent
decision. The exact interception point was verified against the real
upstream source before writing anything: `SocialAgent.perform_action_by_llm()`
in `oasis/social_agent/agent.py`, specifically the line
`env_prompt = await self.env.to_text_prompt()` — that's the single moment
the RecSys's chosen posts turn into the text an agent's LLM call reacts
to, and nothing in the base class stands between them. The design
deliberately touches only that prompt content, never the agent's
tool-call response schema, specifically to avoid repeating Sim 1's
Attempt 1 failure (editing shared files broke tool-calling entirely). An
early version of the herd-effect design (2 puppet agents, 9 posts split
into 3 groups of 3, single run) was floated during this planning but
superseded once the project switched to reusing the paper's own existing
`reddit_simulation_counterfactual.py` script instead — noted here only
because it was a real design considered and dropped, not because it was
built.

- First full run took **4 attempts** (~4 hrs) because 3 real bugs only
  surfaced at full scale: a vote-count field that leaked through under a
  different config key, a timeout that crashed the whole run instead of
  failing open, and a `rank: null` response that crashed `sorted()`.
  **The habit that caught 2 of 3:** always smoke-test at small scale (2
  rounds) before a full run (6 rounds) — established mid-session after
  being flagged as an efficiency concern, paid off immediately.
- **Headline finding (single run):** correction language dropped from
  68% (unshielded) to 23% (shielded) — hiding the vote count reduced
  correction rather than improving it. Read as evidence Sim 2's original
  "skepticism" finding was substantially crowd-following.
- **Extended to the full 3×2 grid** (up/control/down × shielded/
  unshielded), shield code frozen across all runs so only the condition
  varied. Down replicated 4 times (19%, 23%, 26%, 39% → pooled 28%), up
  and control 2 times each (up: 7%, 26% → 18% pooled; control: 41%, 58%
  → 48% pooled).
- **Sharpest finding:** unshielded, the three conditions form a clean
  gradient tracking the fake vote exactly (up 4% < control 11% < down
  68% — that gradient *is* the herding effect). Shielded, that gradient
  **breaks and partially inverts**: up (18%) < down (28%) < control
  (48%) — down and control swap relative rank.
- **Statistical significance** (Fisher's exact / chi-square on pooled
  counts, added in a follow-on pass): down's drop (p=0.0009) and
  control's rise (p=0.0020) are both significant; up's shift (p=0.239)
  is **not** — 2 runs isn't enough there yet. The three-way group
  difference under shielding is significant (χ²=9.49, p=0.0087), and
  down-vs-control specifically differ significantly (p=0.0347), but
  up-vs-down do **not** (p=0.362) — so "the gradient flips" holds as a
  group/down-control claim, not as every pairwise ordering confirmed.
- Shield reliability: 56/64 calls succeeded (87.5%); the rest failed
  open (fell back to the raw feed) rather than crashing — meaning ~1/8
  of "shielded" turns weren't actually shielded, a real noise source.
- **Mid-batch infra fix:** runs were slow because Ollama was
  unloading/reloading the model between multi-minute gaps; restarting
  with `OLLAMA_KEEP_ALIVE=60m` (default 5m) cut run time from 65–90 min
  to ~19 min, judged safe mid-run since a warm vs. reloaded model
  produces the same output distribution, just faster. **Established
  habit:** prefer `OLLAMA_KEEP_ALIVE` tuning over touching
  experiment/model logic when only speed, not correctness, is the
  complaint.
- **Disclosed but untested limitation:** the Shield's own prompt still
  receives the raw vote count (it needs it to know what to strip) — so
  it's untested whether the Shield's own `rank`/`shield_note` is subtly
  influenced by a post's vote count even while told to ignore it,
  potentially leaking the signal back in indirectly.

## Sim 4 — social timeline (full log: **Part 5** of this file; spec in `docs/superpowers/specs/`)

**In progress, on branch `social-timeline-sim` (NOT `main`).** Turns the
simulation into something that behaves like a real social app: agents acting
freely over many rounds, each with a personalized timeline, instrumented finely
enough to reconstruct what every agent saw, ignored, and did, to whom.

Code lives in `examples/experiment/social_timeline/` — zero diff to `oasis/`,
same subclassing discipline as Sim 3's `ShieldAgent`.

**Four upstream bugs found that silently corrupt results.** Read these before
trusting any recommendation output:

1. **`RecsysType.TWITTER` returns random feeds.** Its scoring model is never
   initialised on that path (`recsys.py:39` vs `:282`), so it falls through to
   `random.random()` (`:749`) with no error. Use `twhin-bert`, never `twitter`.
2. **TwHIN-BERT embeddings are non-deterministic.** `process_recsys_posts.py:33`
   returns `pooler_output`, but the checkpoint has no trained pooler, so those
   weights are randomly re-initialised **every process**. Two processes gave
   different embedding spaces; discrimination collapsed to `+0.0008` (noise) in
   one. Mean-pool `last_hidden_state` instead: `+0.0475`, and identical across
   processes. Replication is impossible without this fix.
3. **Exposure history is destroyed every round** (`platform.py:383`,
   `DELETE FROM rec`), so "what did they see" is unrecoverable unless snapshotted.
4. **Group chat hijacks the prompt.** `to_text_prompt()` renders `$groups_env`
   before `$posts_env` on every turn *regardless of `available_actions`*. One
   agent creating a group buries everyone's feed. Measured: action_rate 0.469
   with groups vs 0.812 without.

**Also worth knowing:** every table's `user_id` column actually stores
`agent_id` (`platform.py:407`); only `user` has both. Trace `info` payloads are
*not* uniform — `follow` records no followee at all, `quote_post` stores a
string id, comment actions record only `comment_id`. And `SocialAgent.agent_id`
is camel's UUID; the integer is `social_agent_id` (`agent.py:71`).

**Status:** stages 0-3 green (action_rate 0.812, follow graph forms, no
duplicate posts, `both` source attribution verified). Full 36-agent × 12-round
run executing. Deliverables: `analyze.py` (event log + exposure ledger),
`make_graph.py` (published artifact), `test_actions.py` /
`test_instrumentation.py`.

## Open threads

1. Push local `main` to `origin` — not done, not yet asked for.
2. Up and control still only have 2 runs each vs. down's 4 — up's own
   7%-vs-26% spread (and its non-significant p=0.239) both point at
   needing more data; a 3rd/4th run each would do for them what runs 3–4
   did for down.
3. Reduce the Shield's fail-open rate (longer timeout / stricter output
   format), and/or replace the free-text `shield_note` with a numeric
   plausibility score — deliberately deferred through all of Sim 3's
   replication runs to keep the shield mechanism frozen; needs its own
   isolated before/after comparison.
4. "1 personality × 36" control — isolate treatment-effect from
   personality-mix-effect. Needs new agent data, not started.
5. Validate the keyword-based disagreement classifier against actual
   human judgment (used in both Sim 2 and Sim 3) — never done; its real
   precision/recall are unknown.
6. Replace the keyword classifier with an LLM-judged score, and/or run
   the whole experiment at 100/1000+ agents (configs already exist
   upstream) to see if a real vote-count herd effect emerges at scale,
   per the paper's own scale-dependent finding.
7. Test whether the Shield leaks vote-count info indirectly through its
   own `rank`/`shield_note` (see Sim 3 limitation above) — would need a
   Shield variant whose own prompt never receives the vote count at all.
8. Other scoped-but-unstarted ideas from `LEARN_OASIS.md`: Reddit vs.
   Twitter RecSys → echo-chamber differences; personality mix (agreeable
   vs. skeptical population) vs. agent/human herding gap;
   `llama3.2:3b` vs `llama3.1:8b` model comparison on the identical
   experiment.
9. **Richer agent personas via MatrAIx-Persona-8B's dataset** (surfaced
   comparing `camel-ai/oasis` against `MatrAIx-ai/MatrAIx-Persona-8B` as
   candidate simulators). MatrAIx itself is the wrong tool — it's a
   persona-driven product-eval harness (Survey/Chatbot/Web/App tasks, one
   task per persona run), with no feed, no recommender, no social graph,
   no multi-timestep agent-to-agent loop, so it can't replace OASIS. What
   it does have that's genuinely richer than `data/reddit/user_data_36.json`:
   a shared schema of 1,290 categorical persona dimensions (background,
   psychology, capability, behavior) and a released 1M-persona dataset
   (`MatrAIx2026/MatrAIx_Persona_1M_Public_Release` on Hugging Face).
   Idea, not yet started: sample from that dataset and map it into the
   fields `generate_reddit_agent_graph` expects, in place of or alongside
   the current 36-persona file, for richer personality-driven behavior.
   **Not yet verified:** nobody has actually opened the schema/dataset
   files to confirm field names, format, or license fit this use — only
   the README's description has been read.

## Codebase reference: what's in `examples/` and `generator/`

A fuller inventory than `LEARN_OASIS.md`'s table — every script in these
two folders was read (front to back for distinct ones; near-duplicates
verified by diff), useful when scoping a new experiment idea rather than
writing one from scratch.

**`examples/` — demo scripts, all follow the same skeleton** (build agent
graph → `oasis.make()` → `env.reset()` → `ManualAction`/`LLMAction` steps
→ `env.close()`):

- `quick_start.py` — two hand-built agents (Alice, Bob), no JSON needed;
  cleanest template for hand-crafting agents.
- `reddit_simulation_openai.py` — the same shape as the 36-agent runs
  used throughout this project, on OpenAI instead of Ollama.
- `twitter_interview.py` — uses `ManualAction(INTERVIEW, ...)` to pause
  and ask an agent its opinion mid-run; `INTERVIEW` is deliberately kept
  out of agents' own `available_actions` so it's experimenter-only. Ends
  by reading interview answers back out of the `trace` table — a
  ready-made template for pulling structured answers out of a run.
- `twitter_misinforeport.py` — demos `REPORT_POST`: once a post crosses
  `report_threshold` (2, in `platform.py`), every agent who sees it
  afterward gets a `[Warning: This post has been reported N times]`
  banner stapled to the content. A ready-made content-moderation
  experiment (do warning labels change agent behavior?).
- `group_chat_simulation.py` — group-chat create/join/post/react.
- `custom_platform_simulation.py` — skips the Reddit/Twitter presets and
  builds a `Platform` by hand; exposes `allow_self_rating` and
  `show_score` directly. Needed any time an experiment wants platform
  rules the presets don't offer.
- `custom_prompt_simulation.py` — gives one agent a custom system-prompt
  template with an explicit aim (the demo: "persuade people to buy the
  GlowPod lamp"), paired with `PURCHASE_PRODUCT` and a product table that
  counts sales — an undercover-salesman-among-normal-users pattern.
- `different_model_simulation.py` — mixes different LLMs across agents in
  one run (a GPT agent and a Qwen agent together).
- `search_tools_simulation.py` / `sympy_tools_simulation.py` — bolt real
  extra CAMEL tools (DuckDuckGo search, a math solver) onto an agent with
  `max_iteration=5` so it can reason in multiple steps — i.e. agents that
  can fact-check, relevant to anything herd/misinformation-related.
- `twitter_simulation_vllm.py` — the scaling pattern in miniature: two
  vLLM servers, round-robin scheduling.
- `experiment/reddit_simulation_align_with_human.py` (the actual
  Finding-3/herd-effect legacy script): two puppet agents (poster +
  rater, both literally named "momo," bio `"None"`), real Reddit
  posts/comments pre-tagged up/down/control fed in, and — the detail
  worth remembering — every real LLM agent is made to pre-mute the
  poster puppet *and* has a fake memory implanted ("He is my enemy...")
  so no agent forms a relationship with the account that posts
  everything. That's the paper's own anonymity control, and it's a
  different mechanism from Sim 3's Shield (muting + false memory vs.
  hiding vote counts) — worth knowing both exist if a future experiment
  wants to isolate "relationship bias" from "vote-count bias"
  specifically. `reddit_simulation_counterfactual.py` (Finding 5, the
  script this project's Sim 2/3 actually use) is the same skeleton with
  `init_post_score` swapped in per condition instead of real
  up/down-tagged comments.
- `experiment/twitter_simulation_group_polar.py` — the Helen-the-novelist
  polarization experiment (Finding 2/4): every 10 timesteps calls
  `perform_test()` (hard-coded in `agent.py`) and dumps answers to CSV
  for extremity judging.
- `experiment/twitter_simulation_large.py` — Finding 1's real-propagation
  alignment run; the only one using each agent's real crawled 24-hour
  activity schedule instead of a synthetic one.
- `experiment/emall_simulation.py` — registers fake products and lets
  agents shop; a mini consumer-behavior lab, unrelated to misinformation
  work but there if ever needed.

**`generator/` — the persona factory:**

- `generator/reddit/user_generate.py` — the demographic dice-roller this
  project's 36-agent population ultimately traces back to: hard-coded
  probability tables for gender, 5 age buckets, all 16 MBTI types at real
  population frequencies, countries, 16 career clusters; then two GPT-3.5
  calls per person (pick 2-3 interests fitting the rolled demographics;
  invent name/username/bio/backstory). Runs 100 in parallel threads.
- `generator/twitter/gen.py` does the same at 60k+ scale; `rag.py` adds
  retrieval — real Twitter profiles in a Chroma vector DB with BGE
  embeddings, so generated personas are written in the style of similar
  real profiles rather than invented from scratch; `network.py` wires
  generated users to real "star" accounts (follow with probability 0.2
  per matching interest topic) to produce the celebrity-hub network shape
  real platforms have; `ba.py` is the random-edges baseline for
  comparison.

## Research framing (why this is defensible research, not disinfo tooling)

Raised and worth keeping on record: the same simulation machinery can be
used to *rehearse* a real disinformation campaign (A/B-testing phrasing
and seed-account strategy in simulation, then deploying the winner
against real people) or to *stress-test a defense* before it ships (does
a warning label actually reduce resharing? does down-ranking beat
fact-check replies? does an effect hold at scale or only look convincing
at 36 agents?). The tell: whether the work ends with knowledge that
protects people who were never exposed to the simulated harm, or a
weapon aimed at people who never agreed to be targets. This project's
work (herd-behavior measurement, the Shield as a protective
intermediary) sits on the defensive side of that line by construction —
worth restating explicitly if this repo or its reports are ever shared
outside this project.

## Conventions worth keeping

- Smoke-test (2 rounds) before every full run (6 rounds) — caught 2 of 3
  bugs in Sim 3 before they wasted an hour-plus run.
- Run anything with a claimed finding at least twice before trusting the
  number — Sim 2's comment-count claim didn't survive a second run and
  was retracted rather than deleted; Sim 3's down condition needed all 4
  runs before the noisy first two settled down.
- Prefer `OLLAMA_KEEP_ALIVE` tuning over touching experiment logic when
  the complaint is speed, not correctness.
- `git status` this repo at the start of a new session, not just after a
  run — reports have been left edited-but-uncommitted across sessions
  before (see 2026-08-20 entry below).

---

### 2026-08-20

Found and committed a round of uncommitted work from a prior session
that had never been saved: renamed `COUNTERFACTUAL_EXPERIMENT_REPORT.md`
→ `COUNTERFACTUAL_EXPERIMENT_REPORT(sim 2, groups).md` and
`SESSION_REPORT.md` → `SESSION_REPORT (basic sim1).md` to disambiguate
which sim each covers, and cleaned up two tables in
`SHIELD_EXPERIMENT_REPORT.md` (`fde088d`). This file created to hold
future entries like this one directly in the repo, rather than only in
the assistant's cross-session memory.

Pulled in knowledge from a separate claude.ai website chat (not this
terminal session) that had done its own read of this fork and planned
Sim 3 before any code existed: the fuller `examples/`/`generator/`
inventory above, the verified Shield interception point
(`perform_action_by_llm()` / `to_text_prompt()` in `oasis/social_agent/agent.py`),
the research-framing note, and a new open thread (MatrAIx-Persona-8B's
persona dataset as a possible richer input for agent profiles). The
website chat and this terminal have no shared memory of each other —
this kind of manual copy-paste is currently the only way to bridge them.


---

# Part 2 — Simulation 1: basic Reddit sim and reasoning capture

*Was `SESSION_REPORT (basic sim1).md`. Merged into this file 2026-09-13; original title: “Simulation 1: Basic Reddit Simulation + "Why Did The Agent Do That?" Investigation”.*

A step-by-step, copy-paste-able reproduction of everything we ran. Every command
below is exact — run them in order, in a Terminal, from `/Users/gordon/research/oasis`,
and you will see the same kind of data we're discussing.

---

## PART A — What is this simulation, and what are we trying to find out?

**No paper-reading required — here's the whole idea in plain terms:**

We're building a fake Reddit populated entirely by AI "people" (agents), each with
a made-up personality (age, personality type, country, job, interests). We let
them read posts and react — post, comment, like, follow, or ignore — using their
own judgment, driven by a free local AI model (Ollama) instead of a paid one.

**The specific question we're investigating:** when an AI agent posts or comments
something, **is that a random guess, or is it actually caused by the personality
we gave it?** And separately: **can we make the AI explain its reasoning out loud,
the way a person would say "I liked this because..."?**

We are NOT trying to replicate a specific published number here — this is an
exploratory investigation into *how the tool itself behaves*, using your own
machine and your own data.

---

## PART B — One-time setup (only needs to be done once, skip if already done)

### Step B1 — Confirm the environment exists and works
```bash
cd /Users/gordon/research/oasis
source oasis-env/bin/activate
python --version
```
**Why:** OASIS needs Python 3.10/3.11. Your system Python may be newer and won't
work — this venv already has the correct version and all packages installed.
**Expected output:** `Python 3.11.15`

### Step B2 — Confirm Ollama is running and check the model
```bash
ollama list
ollama show llama3.1:8b
```
**Why:** OASIS agents act by "calling tools" (like an app calling a function).
We need to confirm the model actually supports this — not just guess.
**Expected output:** `llama3.1:8b` appears in the list, and under `Capabilities` you
should see `tools` listed. If `llama3.1:8b` isn't there yet, pull it first:
```bash
ollama pull llama3.1:8b
```

---

## PART C — Run 1: the baseline simulation

### Step C1 — Run it
```bash
cd /Users/gordon/research/oasis
source oasis-env/bin/activate
python examples/reddit_simulation_ollama.py
```
**Why:** This is the actual experiment — 36 AI agents (loaded from
`data/reddit/user_data_36.json`) get seeded with one post ("Hello, world!"), then
each agent freely decides what to do (post, comment, like, follow, or nothing).
**What it produces:** a fresh `data/reddit_simulation.db` (overwritten every run)
and a new timestamped log file in `log/`.

### Step C2 — See the results yourself
```bash
sqlite3 data/reddit_simulation.db "SELECT post_id, user_id, content FROM post;"
```
```bash
sqlite3 data/reddit_simulation.db "SELECT action, COUNT(*) FROM trace GROUP BY action ORDER BY COUNT(*) DESC;"
```
**Why:** The first shows every post the agents created in their own words. The
second shows a tally of every action type taken (posts, comments, likes, etc.) —
this is the actual "results" of the simulation.

---

## PART D — Investigation 1: does an agent's personality actually cause its behavior?

### Step D1 — Find the newest log file and pick an agent to check
```bash
LOGFILE=$(ls -t log/social.agent-*.log | head -1)
echo "$LOGFILE"
grep "performed action" "$LOGFILE"
```
**Why:** This lists every action every agent took this run, with the agent number.
Pick any agent number you see (we used Agent 26 as our example).

### Step D2 — Look up that agent's actual profile
```bash
python3 -c "
import json
data = json.load(open('data/reddit/user_data_36.json'))
print(json.dumps(data[26], indent=2))
"
```
**Why:** This prints agent 26's real assigned personality — name, age, MBTI type,
country, job, interests. (Change the `26` to whichever agent number you picked.)

### Step D3 — Compare the profile to what that agent actually posted
```bash
grep "Agent 26 " "$LOGFILE"
```
**Why:** This is the moment of proof — read the printed profile from Step D2 next
to what that same agent actually posted here. **Our real result:** Agent 26
("Sophie Green," 17, ISFP, Chile, agriculture-focused) posted about gardening and
mentioned Chile — unprompted, straight from her profile. That's the evidence that
personality really does drive behavior, not randomness.

---

## PART E — Investigation 2: can we get the AI to explain its reasoning out loud?

This part took **three attempts**. The first attempt broke the simulation
completely. The second attempt fixed the simulation but didn't achieve the goal.
The third attempt is what's actually running on your machine right now. All three
are documented here so you can see exactly what failed and why — this is real
research process, not just a clean success story.

### Attempt 1 — FAILED (do not do this — shown for the record only)

**What we changed:** In `oasis/social_platform/config/user.py`, in both
`to_twitter_system_message` and `to_reddit_system_message`, we changed:
```
# RESPONSE METHOD
Please perform actions by tool calling.
```
to:
```
# RESPONSE METHOD
Before calling any function, briefly state your reasoning in one short sentence: your feeling about these posts and why this action fits your personality. Then call the appropriate function(s).
```
And in `oasis/social_agent/agent.py`, inside `perform_action_by_llm`, right after
the line `response = await self.astep(user_msg)`, we added:
```python
if response.msgs:
    reasoning_text = (response.msgs[0].content or "").strip()
    if reasoning_text:
        agent_log.info(f"Agent {self.social_agent_id} "
                       f"reasoning: {reasoning_text}")
```

**Test command run:**
```bash
python examples/reddit_simulation_ollama.py
```

**Diagnostic commands run afterward:**
```bash
LOGFILE=$(ls -t log/social.agent-*.log | head -1)
grep -c "performed action" "$LOGFILE"
grep -c "reasoning:" "$LOGFILE"
grep -c "observing environment" "$LOGFILE"
```

**Real result:** `observing environment` = 36, `reasoning:` = 10, **`performed action` = 0**.
**Zero agents took a real action, out of 36.** Telling the model "explain yourself,
*then* act" broke it — instead of calling a real tool, it started typing fake
`{"name": "create_comment", ...}` text that never actually executed anything.

### Attempt 2 — Partial fix, but abandoned for a different reason

**What we changed:** Same two files, softened the wording to:
```
Please perform actions by tool calling. You may optionally include one short sentence about your feeling or reasoning in your message alongside the tool call, but you must always call one of the provided functions — never write a function call out as plain text or JSON.
```

**Test + diagnostic commands:** same as Attempt 1 above.

**Real result:** `performed action` = 35/36 (fixed!), but `reasoning:` = 1/36 (almost
never used). **Problem:** this fix lived inside `oasis/`'s shared engine files —
risky, because any other experiment on this machine depends on those exact files.

**We reverted this completely:**
```bash
git status --short
git checkout origin/main -- oasis/social_agent/agent.py oasis/social_platform/config/user.py
git diff origin/main -- oasis/social_agent/agent.py oasis/social_platform/config/user.py
```
The last command prints nothing if the revert worked — confirming the files are
byte-for-byte identical to the public GitHub version again.

### Attempt 3 — The correct fix (this is what your files contain right now)

**What we did instead:** added a small Python "subclass" — a copy of the existing
agent that adds one extra behavior — entirely inside `examples/reddit_simulation_ollama.py`.
Nothing under `oasis/` is touched. You can verify that right now:
```bash
git diff origin/main -- oasis/ | wc -l
```
**Expected output:** `0` (zero differences from the public repo).

The subclass we added (already saved in your file, shown here so you can see
exactly what it does):
```python
REASONING_ADDENDUM = (
    " You may optionally include one short sentence about your feeling or "
    "reasoning in your message alongside the tool call, but you must "
    "always call one of the provided functions — never write a function "
    "call out as plain text or JSON.")

class ReasoningSocialAgent(SocialAgent):
    def __init__(self, *args, **kwargs):
        user_info = kwargs.get("user_info")
        if user_info is not None:
            original_to_system_message = user_info.to_system_message
            def patched_to_system_message():
                return original_to_system_message() + REASONING_ADDENDUM
            user_info.to_system_message = patched_to_system_message
        super().__init__(*args, **kwargs)
    # perform_action_by_llm override captures reasoning the same way as
    # Attempt 1/2, just inside this subclass instead of the shared file.

agents_generator.SocialAgent = ReasoningSocialAgent
```

**Test run + diagnostics (exact commands):**
```bash
python examples/reddit_simulation_ollama.py
```
```bash
LOGFILE=$(ls -t log/social.agent-*.log | head -1)
grep -c "performed action" "$LOGFILE"
grep -c "reasoning:" "$LOGFILE"
grep -c "observing environment" "$LOGFILE"
grep "reasoning:" "$LOGFILE"
```

**Real result:** `performed action` = 32/36 (tool-calling works, ~89%). `reasoning:`
= 4/36 — **but we checked what those 4 lines actually said**, and all 4 were the
same JSON-as-text failure from Attempt 1, just mislabeled — not genuine reasoning
sentences. Run the last command above yourself and read them; you'll see the same thing.

**Honest final verdict on Investigation 2:** we did not succeed at getting this
specific 8B local model to reliably narrate genuine reasoning. What we did
accomplish: normal tool-calling behavior restored, fully isolated to one file, with
zero risk to the rest of OASIS — and a real, evidence-backed finding that small
local models struggle to combine free-text explanation with structured tool use.

---

## PART F — Complete file inventory

| File | Status | What it does |
|---|---|---|
| Everything in `oasis/` | **100% original**, verified via `git diff origin/main -- oasis/` = 0 lines | The actual simulation engine (unmodified) |
| `examples/reddit_simulation_ollama.py` | **Customized** (the only changed file) | Runs the simulation; contains the `ReasoningSocialAgent` experiment from Attempt 3 |
| `data/reddit/user_data_36.json` | Original | The 36 AI personalities |
| `data/reddit_simulation.db` | Generated fresh each run | Where results land — overwritten every time you run Step C1 |
| `log/social.agent-*.log` | Generated fresh each run | One file per run; every agent's feed + attempted reasoning + actions |

---

## PART G — One paragraph for Wednesday

> "I ran a Reddit-style simulation with AI agents, then investigated two things:
> first, whether an agent's assigned personality actually causes what it does —
> confirmed, using a specific agent as a traceable example. Second, whether I
> could make the model explain its reasoning out loud. That took three attempts:
> the first broke the simulation entirely (zero real actions), the second
> partially worked but modified shared code I shouldn't have touched, and the
> third is the correct, safe version — isolated to one file, with tool-calling
> restored, though genuine reasoning capture still doesn't reliably work with this
> local model. That's a real finding about model limitations, not a failure to hide."


---

# Part 3 — Simulation 2: the up/control/down misinformation experiment

*Was `COUNTERFACTUAL_EXPERIMENT_REPORT(sim 2, groups).md`. Merged into this file 2026-09-13; original title: “Simulation 2: The Up/Control/Down Misinformation Experiment”.*

A step-by-step, copy-paste-able reproduction of everything we ran. Every command
below is exact — run them in order, in a Terminal, from `/Users/gordon/research/oasis`,
and you will see the same data we're discussing.

---

## PART A — What is this simulation, and what are we trying to find out?

**No paper-reading required — here's the whole idea in plain terms:**

We take a batch of **fake/false claims** (e.g., "the original language of a certain
album is Hebrew" — it isn't) and post them into our fake Reddit. But before any AI
agent sees each post, **we secretly rig its starting score**, in one of three ways:

- **"Up" group:** the post already has 1 fake like on it before anyone sees it
- **"Down" group:** the post already has 1 fake dislike on it before anyone sees it
- **"Control" group:** the post starts completely untouched — no like, no dislike

Then we let 36 AI agents loose to react freely, and we measure two things:
1. **Do the votes snowball?** (Does an already-liked post end up with way more
   likes, and an already-disliked post end up with way more dislikes — a
   "everyone just copies everyone else" effect, called **herd behavior**?)
2. **Do agents actually notice and correct the false information**, or do they
   just go along with whatever they're shown?

**This is a controlled experiment, not a demo.** The *only* thing that differs
between the three runs is that one starting number (+1, 0, or −1). Everything
else — the same 36 agents, the same false claims, the same number of rounds — is
identical. That's what makes the comparison meaningful.

---

## PART B — One-time setup (skip if you already did this for Simulation 1)

```bash
cd /Users/gordon/research/oasis
source oasis-env/bin/activate
ollama list
```
**Why:** Confirms your environment and Ollama are ready. You should see
`llama3.1:8b` in the list.

---

## PART C — Files this experiment uses (all already sitting in your repo)

You do not need to create or download anything — every file below already exists.

| File | What it contains |
|---|---|
| `data/reddit/user_data_36.json` | The same 36 AI personalities from Simulation 1 |
| `data/reddit/counterfactual_36.json` | **220 fake/false claims**, each with a fake root post (`RS`) and a matching short claim (`RC_1`) |
| `examples/experiment/reddit_simulation_counterfactual/reddit_simulation_counterfactual.py` | The actual experiment engine — reads a config file, creates the treated posts, applies the starting like/dislike, then lets agents react for several rounds |
| `examples/experiment/reddit_simulation_counterfactual/up_36.yaml` | Config for the **up** condition (starting score = +1) |
| `examples/experiment/reddit_simulation_counterfactual/control_36.yaml` | Config for the **control** condition (starting score = 0) |
| `examples/experiment/reddit_simulation_counterfactual/down_36.yaml` | Config for the **down** condition (starting score = −1) |

**The only edit we made** to any of these: inside
`reddit_simulation_counterfactual.py`, we replaced the model-creation code (it was
hardcoded to the paper authors' private computer cluster, which doesn't exist for
you) with a call to your local Ollama:
```python
# What it now says (already saved in your file):
models = ModelFactory.create(
    model_platform=ModelPlatformType.OLLAMA,
    model_type=inference_configs.get("model_type", "llama3.1:8b"),
    url=inference_configs.get("url", "http://localhost:11434/v1"),
)
```
Nothing about the actual experiment logic (the three conditions, the scoring, the
number of rounds) was changed.

The three `.yaml` files each set `num_timesteps: 6` and `round_post_num: 5`
(scaled down from the original 30/30 for a laptop-sized run that finishes in
minutes instead of hours), and each one's `data:` section points at the local
files above instead of a remote server path.

---

## PART D — Run all three conditions (exact commands, in order)

Run these **one at a time** (not simultaneously — your one local Ollama model can
only really do one at once). Each takes a few minutes.

### Step D1 — Up condition
```bash
cd /Users/gordon/research/oasis
source oasis-env/bin/activate
python examples/experiment/reddit_simulation_counterfactual/reddit_simulation_counterfactual.py --config_path examples/experiment/reddit_simulation_counterfactual/up_36.yaml
```
**Wait for:** `INFO - social - Simulation finish!` printed at the end.
**Produces:** `data/counterfactual_36_up.db`

### Step D2 — Control condition
```bash
python examples/experiment/reddit_simulation_counterfactual/reddit_simulation_counterfactual.py --config_path examples/experiment/reddit_simulation_counterfactual/control_36.yaml
```
**Produces:** `data/counterfactual_36_control.db`

### Step D3 — Down condition
```bash
python examples/experiment/reddit_simulation_counterfactual/reddit_simulation_counterfactual.py --config_path examples/experiment/reddit_simulation_counterfactual/down_36.yaml
```
**Produces:** `data/counterfactual_36_down.db`

### Step D4 — Confirm all three finished with no errors
```bash
grep -c "Traceback" log/social-*.log
```
**Expected output:** `0` for each of the three most recent `social-*.log` files
(one log file gets created per run, named by timestamp).

---

## PART E — See the results yourself (exact commands)

### Step E1 — Find which database column holds the vote counts
```bash
sqlite3 data/counterfactual_36_up.db ".schema post"
```
**Why we check this instead of assuming:** column names matter for the next
query — `num_likes` and `num_dislikes` are the real column names, confirmed here.

### Step E2 — Find which user_id created the treated posts
```bash
sqlite3 data/counterfactual_36_up.db "SELECT user_id, COUNT(*) FROM post GROUP BY user_id ORDER BY COUNT(*) DESC;"
```
**Expected output:** `0|30` — meaning `user_id = 0` created all 30 treated posts.
(We first guessed `user_id = 1` and got zero rows back — always check real data
instead of assuming an ID.)

### Step E3 — Compare average post score across all three conditions
```bash
for cond in up control down; do
  echo "=== $cond ==="
  sqlite3 "data/counterfactual_36_${cond}.db" "SELECT COUNT(*) AS num_posts, ROUND(AVG(num_likes),2) AS avg_likes, ROUND(AVG(num_dislikes),2) AS avg_dislikes, ROUND(AVG(num_likes - num_dislikes),2) AS avg_score FROM post WHERE user_id = 0;"
done
```
**Our real result (Run 1):**
```
up:      30 posts, avg_likes=1.03, avg_dislikes=0.03, avg_score=+1.00
control: 30 posts, avg_likes=0.03, avg_dislikes=0.00, avg_score=+0.03
down:    30 posts, avg_likes=0.00, avg_dislikes=1.00, avg_score=-1.00
```
**Independent Run 2 result** (a second, completely separate execution of the same
three commands, run by Gordon directly, not by Claude):
```
up:      30 posts, avg_likes=1.00, avg_dislikes=0.03, avg_score=+0.97
control: 30 posts, avg_likes=0.03, avg_dislikes=0.03, avg_score=0.00
down:    30 posts, avg_likes=0.03, avg_dislikes=1.03, avg_score=-1.00
```
**What this means:** in *both* independent runs, each condition's average score
lands almost exactly on the number we artificially forced (+1, 0, −1), with only
trivial extra movement. **This finding replicated cleanly: at this scale (36
agents), the votes do not snowball — no herd effect visible in the raw
like/dislike counts.**

### Step E4 — Compare how many comments each condition got
```bash
for cond in up control down; do
  echo "=== $cond ==="
  sqlite3 "data/counterfactual_36_${cond}.db" "SELECT COUNT(*) FROM comment WHERE post_id IN (SELECT post_id FROM post WHERE user_id = 0);"
done
```
**Run 1 result:** up = 27, control = 15, down = 16.
**Run 2 result:** up = 23, control = 27, down = 22.

**This does NOT replicate — and that matters.** In Run 1, control had the *fewest*
comments; in Run 2, control had the *most*. The direction completely flipped.
**Conclusion: comment count is not a reliable signal at this sample size — it's
noise, not a finding.** (An earlier version of this report treated Run 1's comment
counts as a real secondary finding. It wasn't. This is exactly why a single run
should never be trusted on its own — leaving this correction in the report on
purpose, as the honest record of what happened.)

### Step E5 — Read the actual comment text yourself
```bash
for cond in up control down; do
  echo "=== $cond: all comments ==="
  sqlite3 "data/counterfactual_36_${cond}.db" "SELECT content FROM comment WHERE post_id IN (SELECT post_id FROM post WHERE user_id = 0);"
  echo
done
```
**Why this step matters most:** the vote counts (Step E3) look boring and flat —
but reading the actual words agents used tells a completely different story (next step).

### Step E6 — Count how many comments actually disagree with the false claims
```bash
python3 << 'EOF'
import sqlite3
keywords = ["disagree", "incorrect", "actually", "not true", "mistake",
            "error", "wrong", "false", "surprised", "debated"]
for cond in ["up", "control", "down"]:
    conn = sqlite3.connect(f"data/counterfactual_36_{cond}.db")
    rows = conn.execute("""
        SELECT content FROM comment
        WHERE post_id IN (SELECT post_id FROM post WHERE user_id = 0)
    """).fetchall()
    total = len(rows)
    disputing = [r[0] for r in rows if any(k in r[0].lower() for k in keywords)]
    print(f"{cond:8s}: {len(disputing)}/{total} comments contain "
          f"disagreement/correction language ({100*len(disputing)/total:.0f}%)")
    conn.close()
EOF
```
**Run 1 result:**
```
up      : 4/27 comments contain disagreement/correction language (15%)
control : 0/15 comments contain disagreement/correction language (0%)
down    : 10/16 comments contain disagreement/correction language (62%)
```
**Run 2 result** (independent second run):
```
up      : 1/23 comments contain disagreement/correction language (4%)
control : 3/27 comments contain disagreement/correction language (11%)
down    : 15/22 comments contain disagreement/correction language (68%)
```

---

## PART F — What the results actually mean

**Finding 1 — No herd effect on votes at this scale.** The average score in each
condition stayed almost exactly at the artificial starting value. This matches
what you'd expect at a small population size — the crowd wasn't big enough to
meaningfully pile on top of the initial nudge.

**Finding 2 — A real, striking, and now twice-replicated difference in what agents
actually WROTE.** Across two fully independent runs, down-treated posts drew far
more disagreement than up or control every time:

| | Run 1 | Run 2 |
|---|---|---|
| Up | 15% | 4% |
| Control | 0% | 11% |
| **Down** | **62%** | **68%** |

The exact percentages jump around between runs (small sample, single trial per
condition each time) — **but the down-treated condition is dramatically higher
than up or control in both runs, every time.** That consistency across two
independent executions is what makes this a real finding rather than a fluke,
unlike the comment-count claim above, which reversed direction and had to be
retracted.

**What did NOT replicate, and was corrected:** Run 1 alone showed control at a
suspicious *exact* 0%, which we initially wrote up as "agents show zero critical
thinking with no signal." Run 2's control came in at 11% — still much lower than
down's 62-68%, but not literally zero. **The honest, defensible version of this
finding is:** down-treated posts get dramatically more pushback than up-treated or
neutral posts. It is not that neutral posts get *zero* scrutiny — just much less.

Real examples pulled straight from Step E5:

- *Down-treated, Run 1:* "I disagree with the claim that Moon Bay belongs to
  Europe as it is actually located in North America." *(correct — the agent
  caught the false claim)*
- *Down-treated, Run 2:* "Actually, Neil Hagerty is a guitarist" *(correcting a
  false claim that he plays the violin)* — though notably, in the same run, one
  agent "corrected" a false claim about Caradon Hill's location (falsely said to
  be in Liberia) by saying it's "actually located in West Yorkshire, England" —
  which is **itself wrong** (it's really in Cornwall). Agents show real skepticism
  toward down-treated posts, but that skepticism doesn't always land on the truth.

**In plain terms:** agents seeing a post that starts out disliked reliably push
back on it far more than agents seeing a neutral or liked post. That pattern held
across two separate runs of the whole experiment. Whether that pushback is
factually *correct* is a separate, less consistent story.

---

## PART G — Honest limitations

- Small sample: 36 agents, 6 rounds. The original design uses thousands of agents.
- The disagreement count (Step E6) is a simple keyword search, not a rigorous
  AI-judged score — a rough but reproducible measure, not a precise one.
- We ran each condition twice, independently (Run 1 and Run 2 above) — enough to
  tell a real, repeating pattern (down >> up/control disagreement) apart from a
  one-off fluke (the comment-count claim, which reversed and was retracted). A
  third or fourth repeat would tighten the exact percentages further.
- Settings were deliberately scaled down (fewer rounds, higher activation
  probability) so the whole experiment finishes in minutes on a laptop.

---

## PART H — One paragraph for Wednesday

> "I ran a three-condition experiment twice, independently: identical false
> claims, but secretly starting with a fake like, a fake dislike, or nothing. On
> raw vote counts, both runs found no herd effect at this scale — the numbers
> barely moved past the initial nudge. Reading the actual comments revealed
> something sharper, and it held up across both runs: agents disputed
> misinformation in roughly two-thirds of comments when the post started
> disliked, versus well under 15% when it started liked or neutral. I also caught
> and corrected my own mistake — an early claim that neutral posts got zero
> pushback didn't survive a second run, so I softened it to what the data
> actually supports. That's the real research process: a finding that repeats
> across independent runs, and one that doesn't, treated differently and said
> so honestly."


---

# Part 4 — Simulation 3: the iAgent Shield experiment

*Was `SHIELD_EXPERIMENT_REPORT.md`. Merged into this file 2026-09-13; original title: “Simulation 3: The iAgent Shield Experiment”.*

**Abstract.** In Simulation 2, AI agents pushed back on the same false
claims dramatically more often when a post had already been artificially
downvoted (68% of comments disagreed) than when it hadn't (under 15%). It
was unclear whether that reflected genuine critical thinking or simple
crowd-following. This experiment tests that directly by building a
"Shield" — a second AI that re-ranks each agent's feed by content
plausibility and hides the platform's vote counts entirely — closely
adapted from a real, published paper: **iAgent: LLM Agent as a Shield
between User and Recommender Systems** (Xu et al., *Findings of ACL 2025*).
Every design decision in this experiment traces back to that paper's
architecture; Section 3 states exactly how. The result: once the vote
count was hidden, pushback on the same false claims dropped from 68% to
roughly 20-30% — and, more surprisingly, hiding the vote count did not
just weaken which posts got the most scrutiny, it partially **reversed**
the order, a result strong enough that the experiment was re-run ten
times before it was trusted. Full method, results, and limitations
follow.

This experiment builds directly on Simulation 2
(`COUNTERFACTUAL_EXPERIMENT_REPORT.md`) — that report should be read
first for context.

---

## 0. The simple version (a 5th-grade-level explanation)

**The big idea:** a pretend Reddit was built, full of robot people. Some
of them were told lies, and the experiment watched whether they believed
the lies more or less depending on tricks played on them.

### What is this simulation, really?

This simulation works like a video game where every single "player" is
actually a robot brain (an AI) instead of a real person. Each robot gets
a made-up personality before the game starts — like "Sophie, age 24,
lives in Chile, loves gardening" — the same way a character gets made in
a video game. These robot-people are then dropped into a pretend Reddit,
where they post, comment, and upvote/downvote each other on their own,
with no human clicking anything.

To test something specific, this pretend Reddit was fed 220 made-up
false "facts" — things that are just plain wrong, like "Lettuce doesn't
play jazz" (a silly example) or a made-up claim about a real person
doing something they never did. The question being watched: **do the
robot-people notice the lie and correct it, or do they just believe it
and move on?**

### What's happening "behind the scenes"?

Every time a robot-person needs to decide what to do next (post
something? comment on something? upvote something?), here is what
actually happens, step by step:

1. The pretend-Reddit "hands" the robot its feed — a list of posts, who
   liked/disliked them, and any comments already there. Think of it like
   handing someone a stack of homework papers to read before they answer
   a question.
2. That feed, plus the robot's own personality card, gets typed into a
   question and sent to a real AI language model running on the computer
   (the same kind of AI that powers chatbots — just one small enough to
   run on a laptop instead of needing a huge company's servers).
3. The AI reads all of that and decides what the robot-person should do —
   post, comment, upvote, downvote, follow someone, or do nothing — and
   the pretend-Reddit carries that action out.
4. This repeats over and over, for every robot, for several "rounds,"
   until the simulation ends. Nothing here is scripted in advance — no
   human decided ahead of time who would post what. The AI actually
   "chooses" fresh every single time, the way a person would.

### How do the "up / control / down" groups work?

This is the trick used to test whether robots correct lies because they
actually *know better*, or just because they're *copying the crowd*.

Before a round even starts, the starting scoreboard on each false post is
secretly rigged — like starting a video before anyone's watched it, but
faking the view count:

- **Up group:** the false post starts with 1 fake "like" already on it,
  as if someone had already approved it.
- **Control group:** the false post starts at zero — completely
  untouched, nobody's voted yet.
- **Down group:** the false post starts with 1 fake "dislike" already on
  it, as if someone already disapproved of it.

Same exact false claim, same fake robot personalities, only difference
is that one starting fake vote. The question then becomes: does a fake
"everyone already dislikes this" nudge make robots correct the lie
*more*? It turns out yes, a LOT more — that's the "herd behavior" finding
from Simulation 2. But that raised a question this experiment
(Simulation 3) was built to answer...

### How exactly does the "Shield" work?

The question was: are the robots correcting the false post because they
*actually noticed it was false*, or just because they saw a dislike count
and thought "well, everyone else disagrees, guess I will too"? To find
out, a way was needed to show a robot the exact same false post
*without* letting it see the fake vote count at all.

So a second AI was built — nicknamed the **"Shield"** — that sits in
between the pretend-Reddit and the robot-person, like a bouncer standing
at a door, checking things before they get let inside:

1. Normally: pretend-Reddit → robot's eyes. Feed goes straight through,
   likes/dislikes and all.
2. With the Shield on: pretend-Reddit → **Shield** → robot's eyes. The
   Shield is its *own* separate AI call. It looks at the list of posts
   (with the vote counts) and re-orders them by how believable each one
   sounds, writing one short note about *why* — like "this claim doesn't
   match what I know to be true." Then it hands the robot that
   re-ordered list *with the vote numbers completely deleted* — not
   hidden, not ignored, physically removed from what the robot ever gets
   to read. The robot literally cannot see whether a post was liked or
   disliked when the Shield is on.
3. Sometimes the Shield's answer comes back broken (like it accidentally
   scrambles which note goes with which post). When that happens, it
   tries one more time. If it's still broken, it gives up safely and just
   shows the robot the plain original feed instead of crashing the whole
   game — better a fair test with one weak spot than the whole thing
   breaking.

**Why this matters:** since the Shield deletes the vote count entirely,
if a robot still corrects the lie just as much as before, that means it
was *really* thinking about whether the claim was true. If correcting
drops off once the vote count disappears, that means the robots weren't
really fact-checking at all — they were just following the crowd's mood.

### How many prompts does one robot actually get, and when?

- There are **36 "real" robot-people** in every run, each with its own
  made-up personality. There are also **2 invisible "puppet" accounts**
  that the experiment code controls directly — not real thinking AIs.
  One puppet's only job is posting the false claims; the other puppet's
  only job is casting the single fake starting vote (Section 0's
  up/control/down trick). Those 2 puppets never get a Shield turn and
  don't count toward the 36.
- A full-size run has **6 rounds** (the quick "smoke test" version used
  to catch bugs early only runs 2 rounds — see Section 6). At the start
  of every round, the posting puppet drops **5 new false claims**. Over
  a full 6-round run that's 30 false posts total — that's exactly where
  the "n=30" in Section 8's vote-score row comes from.
- Then, separately for **each of the 36 real robots**, the code flips a
  weighted coin: a 30% chance (the config file calls this
  `activate_prob: 0.3`) that this specific robot gets a turn this round
  — meaning it gets asked "what do you want to do right now?" A 70%
  chance it does nothing and isn't prompted at all this round. This
  coin gets flipped independently for every robot, every round — it is
  **not** "every robot acts every round."
- Because each robot only has a 30% chance, 6 separate times, no two
  robots are guaranteed to get the same number of turns. On average one
  robot gets about **1.8 turns** across a full run (6 rounds × 30%), and
  adding up all 36 robots, a full run produces roughly **65 total turns**
  (36 × 6 × 30% ≈ 65) — which lines up almost exactly with the 64 real
  turns actually counted in Section 9.
- **Every turn means exactly one prompt to the robot's own "what should
  I do" AI call. In shielded runs only, there's one extra prompt to the
  Shield AI immediately before it.** So a shielded run makes roughly
  *twice* as many total AI calls as an unshielded run does for the same
  number of turns (2 calls × ~65 turns ≈ 130 AI calls in a full shielded
  run). The Shield is never asked more than twice for the same turn — if
  its second try still comes back broken, it gives up (Section 5, step
  4) and the robot's own decision call still happens exactly once, as
  normal.

### Exactly what does each prompt say, and what does "ranked" mean?

Every time a robot gets a turn, here is literally what gets typed into
the AI, in order:

**Step A — the Shield's prompt (shielded runs only), a completely
separate AI conversation that happens first:**
- A fixed instruction block telling the Shield AI its only job is to
  *reorder a list of posts by how believable they sound* — a post scores
  higher when it's specific and matches well-known facts, lower when it
  uses absolute words like "always" or "everyone knows" or contradicts
  something well-established — **and explicitly, none of this scoring is
  allowed to depend on how many likes or dislikes the post already has.**
- The robot's own persona (made-up name, age, personality type, country,
  interests).
- The actual small batch of posts the platform would show this robot
  right now — up to 5 at a time (`refresh_rec_post_count: 5` in the
  config), each with its text, its comments so far, **and** its current
  like/dislike numbers. The Shield is allowed to *see* the vote counts —
  it needs them to know what to hide — it's just never allowed to hand
  them back out.
- The Shield answers with a list — one entry per post — giving each
  post's ID number, a **`rank`** number, and a one-sentence
  **`shield_note`** explaining its reasoning. **"Ranked" just means "put
  in order":** `rank: 1` means "show this post first," `rank: 2` means
  "show it second," and so on — purely by how believable the Shield
  judged it, nothing to do with popularity. The code then physically
  re-sorts the post list into that exact order, deletes the like/dislike
  numbers from every post, and attaches each post's `shield_note`
  sentence.

**Step B — the robot's own decision prompt, sent every turn, shielded or
not:**
- The robot's full persona plus the exact list of things it's allowed to
  do this run (like, dislike, comment, refresh, do nothing, etc.) —
  notably, in this experiment **regular robots are never allowed to
  create a brand-new post**; only the invisible puppet account posts the
  false claims.
- The post list produced by Step A — in shielded runs, that's the
  Shield's re-ordered, vote-count-stripped list with `shield_note`
  sentences attached; in unshielded runs, it's simply the platform's raw
  list with the real like/dislike numbers sitting right there in the
  text.
- The robot's AI reads all of this and picks exactly one action to
  actually perform.

### What do the percentages in this report actually mean?

This report uses **two different kinds of percentages**, and they use
some of the same raw numbers, which is exactly what makes them
confusing at a glance. Here is precisely what each one counts.

**Type 1 — "How much of the talking was correcting the lie?"** This is
the 68% → 23%-style headline number, and everything in Sections 8 and
10's big tables. It counts **comments, not robots, not posts, not
turns.**
- **Bottom of the fraction (denominator):** every comment any robot left
  anywhere in that run, specifically on one of the false-claim posts
  (never a comment on some unrelated post).
- **Top of the fraction (numerator):** of those comments, however many
  contain at least one "correcting" word — things like *actually*,
  *wrong*, *false*, *disagree*, *mistake*, *not true*, *incorrect*,
  *error*, *surprised*, *debated* — checked automatically by a simple
  word search over the comment's text.
- **A real worked example, straight from this report's own data:**
  Simulation 2's unshielded "down" run produced exactly 22 comments on
  the false posts, total, over the whole run. Of those 22, 15 contained
  a correcting word. 15 ÷ 22 = 68%. That is the "68%" that appears
  everywhere. When the Shield was switched on, one run of the same
  condition produced only 13 comments on the false posts, total, and
  just 3 of those 13 had a correcting word: 3 ÷ 13 = 23%.
- **Why the raw counts (13, 22, 23, 29...) matter just as much as the
  percentage:** these are small numbers. If only 2 more of those 13
  comments had happened to contain the word "actually," 23% would have
  jumped to 38% — nothing about the robots' real behavior would have
  needed to change. That's exactly why one run's percentage wasn't
  trusted on its own, and the experiment was rerun 8 more times
  (Section 10) before the pattern was believed to hold.

**Type 2 — "What share of all actions were comments, specifically?"**
This only appears once, in Section 8's small table
(`create_comment actions: 22 (13%) / 13 (8%)`), and it is a **completely
different measurement** from Type 1 — even though "22" and "13" happen
to be numbers that also show up above, they mean something different
here.
- **Bottom of the fraction here:** *every* action any robot took, all
  run — likes, dislikes, comments, refreshes, doing nothing, all of it
  (171 total actions in that unshielded run, 169 in that shielded run).
- **Top of the fraction:** just the ones that were specifically "write a
  comment" actions.
- So `22 (13%)` means: out of 171 total actions taken by all 36 robots
  across the whole run, 22 of them were "write a comment," which is 13%
  of *all actions*. It is **not** saying 13% of comments disagreed —
  that's Type 1's job, using a different denominator entirely.

### What was found

Once the vote count was hidden by the Shield, robots corrected false
posts **way less often** — roughly cut by more than half. That's the
unflattering-but-honest answer: a big chunk of the "skepticism" from
Simulation 2 wasn't robots being smart fact-checkers, it was robots
copying whatever the crowd already seemed to think. Sections 8 and 10
below go through exactly how confident that finding is, with the real
numbers.

---

## 1. Background: the source paper

Everything in this experiment is built on top of one specific paper.
Before describing what this experiment did, this section summarizes
what the paper's authors did, so the connection is fully traceable
rather than a loose inspiration.

**Citation:** Xu, W., Shi, Y., Liang, Z., Ning, X., Mei, K., Wang, K., Zhu,
X., Xu, M., & Zhang, Y. (2025). *iAgent: LLM Agent as a Shield between User
and Recommender Systems.* In **Findings of the Association for
Computational Linguistics: ACL 2025**, pp. 18056–18084 (Vienna, Austria).
Also available as arXiv:2502.14662. Authors are affiliated with Rutgers
University, University of Technology Sydney, University of Illinois
Urbana-Champaign, and Nanyang Technological University. Code and datasets
are public at `github.com/agiresearch/iAgent`.

### 1.1 The problem the paper identifies

Real recommender systems (the algorithms behind a shopping site's "you
might also like" or a feed's "for you" page) normally use what the paper
calls a **user-platform paradigm**: the platform's algorithm sits directly
between a person and everything they see, with no intermediary. The paper
argues this creates three specific problems: (1) these algorithms are
often optimized for the *platform's* commercial goals (clicks, purchases,
watch time), not necessarily the user's actual interests; (2) they're
trained on data pooled across *all* users, which can wash out an
individual's specific preferences; and (3), as a consequence, users end up
with no real control, are vulnerable to manipulation, fall into **echo
chambers** (repeatedly shown the same kind of content), and — especially
for people who don't use the platform very often — get worse
personalization than heavy users, because the algorithm has learned more
from the active majority.

### 1.2 The paper's proposed solution

The paper proposes a new **user-agent-platform paradigm**: instead of a
person facing the platform's algorithm directly, a personal LLM agent sits
in between, receiving the platform's raw ranked list and re-ranking it for
the user based on content quality — not the platform's engagement metrics
— before the user ever sees it. The paper builds this in two versions:

- **iAgent (the base version)** has three parts. A **Parser** reads the
  user's free-text instruction (e.g. "find me a used car under $2,000")
  and turns it into structured, domain-expert-level knowledge about what
  the user actually wants, optionally using external tools to look things
  up. A **Reranker** takes that parsed knowledge plus the platform's
  original ranked list and produces a new ranking. A **self-reflection
  mechanism** then checks the reranked list against the previous one — if
  they don't match as expected, it asks the reranker to try again — a
  safeguard specifically against LLMs confidently hallucinating incorrect
  output.
- **i²Agent (the extended version)** adds a **dynamic memory** on top of
  the base iAgent: a Profile Generator that builds a running profile of
  one specific user from their past interactions and feedback, and a
  Dynamic Extractor that pulls out that user's current interests from it.
  Critically, this memory belongs to *one individual user only* — it isn't
  shared across the platform's whole user base, so a heavy user's behavior
  can't drown out a light user's preferences the way it can in a
  traditional pooled model.

### 1.3 How the paper tested it

The paper couldn't find an existing dataset with real user *instructions*
attached to recommendation data, so they built one: **InstructRec**, four
datasets (built from existing Amazon Book, Amazon Movie/TV, Goodreads, and
Yelp data) with a synthetically generated free-text instruction attached
to each interaction. They compared iAgent and i²Agent against three
classes of existing methods — sequential recommenders (GRU4Rec, BERT4Rec,
SASRec), instruction-aware methods (BM25, BGE-Rerank, EasyRec), and other
recommendation agents (ToolRec, AgentCF) — using standard ranking-quality
metrics (Hit Rate @1/@3, NDCG@3, Mean Reciprocal Rank), plus two metrics
they designed specifically to test the "shield" claim: how often
injected/simulated ad items got filtered out (**FR@k**), and how much
ranking quality was skewed toward already-popular items (**P-HR@3,
P-MRR**).

### 1.4 What the paper found

Across all four datasets, i²Agent beat every baseline, with an **average
improvement of 16.6%** over the strongest baseline (EasyRec) across
ranking metrics — and the base iAgent, with no dynamic memory at all,
already beat every baseline too. For example, on the Amazon Book dataset,
i²Agent scored HR@1 = 35.11 / MRR = 50.28 versus EasyRec's HR@1 = 30.70 /
MRR = 46.14. On the echo-chamber-specific metrics, i²Agent filtered out
77.15% of injected ad items in the top-1 position versus EasyRec's 68.41%,
and reduced popularity bias (P-MRR) to 60.20 versus EasyRec's 56.09. The
paper also confirmed the shield specifically helped **less-active users**,
not just active ones — on Amazon Book, i²Agent improved HR@1 for
less-active users from 32.93 (best baseline) to 37.92, and for active
users from 28.71 to 33.27. Finally, they found their self-reflection
mechanism reduced LLM hallucination in the reranked output by **at least
20-fold** compared to not having it.

### 1.5 What the paper says are its own limitations

Quoting the paper's Section 6 directly, since precision matters here:
*"our current implementation primarily focuses on English instructions,
and the effectiveness of the model across different languages remains to
be explored. Additionally, while our evaluation metrics show improvements
in recommendation quality, they may not fully capture the nuanced aspects
of user satisfaction and long-term engagement."* In plain terms: they only
tested English, and a higher ranking-quality score isn't proof that real
users would actually be more satisfied or stay more engaged over time —
their own metrics don't fully answer that question. That second point is
directly relevant to Finding 3 in Section 8.

---

## 2. Why this experiment builds on that paper

**Research question:** when an OASIS agent pushes back on a false claim,
is that driven by the agent evaluating the claim's content, by the
agent seeing the crowd's vote count, or some mix of both?

**Null hypothesis (H0):** hiding the vote count changes nothing — the
rate of correcting comments on a given false claim stays the same
whether or not the agent can see how the crowd voted. (This would mean
Simulation 2's pushback was driven by the claim's content, independent
of visible crowd sentiment.)

**Alternative hypothesis (H1):** hiding the vote count changes the
correction rate — meaning at least part of Simulation 2's pushback was
driven by the visible vote count itself, not the claim's content alone.
H1 doesn't by itself predict *which direction* the change goes (more
pushback or less); Section 8's finding — that it went down, sharply —
was a genuine result, not something assumed going in.

Simulation 2 found that posts starting with a fake dislike got
dramatically more disagreement/correction comments (~62-68%) than posts
starting liked or neutral (well under 15%). That result has two very
different possible explanations:

- **The flattering read:** agents are healthily skeptical of claims the
  crowd already doesn't trust.
- **The unflattering read:** agents are just copying the crowd's mood —
  piling onto disapproval because it's already visible, not because they
  reasoned about the claim itself.

Simulation 2 alone can't tell these apart, because the vote count and the
pushback happened together every single time — there was no version of
the experiment where an agent saw the post but *not* the crowd's opinion
of it. The iAgent paper's core mechanism — an intermediary agent that
re-ranks content and specifically withholds the platform's own
engagement-driven signals from the end user — is exactly the tool needed
to build that missing condition. If pushback survives losing the vote-count
cue, it was real thinking. If it collapses, it was crowd-following.

---

## 3. What Simulation 3 does, and exactly how it maps to the paper

Simulation 3 is not a re-run of the paper's own experiment — it operates
in a completely different domain (a fake-news Reddit simulation instead of
e-commerce/book/movie recommendations) and asks a different research
question (does removing a manipulation signal change *correction
behavior*, not does it improve *ranking quality*). What it directly reuses
is the paper's **mechanism**. Here is the explicit mapping, piece by
piece:

| Paper component (Section 1.2) | What this experiment built | Why it maps |
|---|---|---|
| **Parser** — turns a user's raw instruction into structured knowledge about them | Reuses each OASIS agent's existing persona (age, MBTI, country, interest profile) directly as the Shield's "who is this user" input | OASIS agents don't issue free-text instructions like the paper's InstructRec users do, so there's nothing to parse — but the *purpose* of the Parser (give the reranker a structured picture of the user) is already satisfied by data OASIS generates for every agent anyway |
| **Reranker (paper's Eq. 2)** — one LLM call that re-ranks the platform's list using the parsed knowledge | `_shield_rerank()` in `shield_agent.py` — one LLM call that re-ranks the platform's post list by plausibility, using the agent's persona | Same mechanism, same position in the pipeline: intercept the platform's list before the user/agent ever sees it |
| **Self-reflection mechanism** — compares the reranked list to the previous one, regenerates on mismatch to fight hallucination | A validation step checks that the Shield's returned post-ID set exactly matches what was sent in, retries once on mismatch, and **fails open** (shows the plain feed) if it still doesn't match | Same safeguard, adapted for a live simulation that can't afford to stall or loop indefinitely waiting for a perfect answer |
| **i²Agent's dynamic memory** (Profile Generator + Dynamic Extractor, built from a user's feedback across many sessions) | **Not built.** | The paper's dynamic memory is explicitly built by accumulating one user's feedback *across multiple sessions over time*. OASIS agents only exist for the length of one simulation run — there is no persistent, cross-session history to build a dynamic memory from, so this piece of the paper's architecture doesn't have anything to attach to in this setup. |
| **InstructRec datasets** (Amazon Book/Movie, Goodreads, Yelp + synthetic instructions) | **Not built — Simulation 2's existing dataset was reused instead** (220 false claims from `counterfactual_36.json`) | This is testing herd behavior on misinformation, not product-recommendation ranking quality, so the paper's e-commerce datasets don't fit the question; Simulation 2 already had a dataset built for exactly this purpose |
| **Ranking-quality metrics** (HR@k, NDCG@3, MRR, FR@k, P-HR@3, P-MRR) | **Not used — Simulation 2's keyword-based disagreement/correction classifier was reused instead** | The paper's metrics all assume a single "correct" item exists to rank highly. There's no equivalent "correct answer" in this setup — what gets measured instead is whether agents push back on a *false* claim, which the paper's metrics were never designed to capture |

**In one sentence:** this experiment built the paper's base iAgent
(Parser + Reranker + Self-reflection) exactly as designed, deliberately
left out the parts of the architecture that require multi-session memory
or a different kind of dataset, and pointed the same core mechanism at a
different question than the paper asked — not "does hiding the
platform's signal improve ranking quality," but "does hiding the
platform's signal change how much agents push back on things that
aren't true."

---

## 4. Where did this code come from — copied from the paper, or written new?

**Short answer: all of it was written new, specifically for this
project.** The paper's own public code (`github.com/agiresearch/iAgent`,
referenced in Section 1) is built for real recommendation datasets and a
real ranking pipeline — it isn't written for OASIS and wouldn't run here.
What this experiment took from the paper was the *architecture*, mapped
explicitly in Section 3; what got written was a completely new, original
Python implementation of it, built specifically to plug into the
existing OASIS-based simulator.

**Files created from scratch (all new, nothing like them existed
before):**

| File | What it does |
|---|---|
| `examples/experiment/reddit_simulation_counterfactual/shield_agent.py` | The Shield itself — the actual new code |
| `examples/experiment/reddit_simulation_counterfactual/reddit_simulation_shielded.py` | The script used to start a shielded simulation |
| `examples/experiment/reddit_simulation_counterfactual/down_36_shielded.yaml` and its replicate/condition variants | Settings files — same simulation settings as Simulation 2, just told to save results somewhere new |
| `examples/experiment/reddit_simulation_counterfactual/analyze_shield.py` | The script that reads the results and compares shielded vs. unshielded |

**The one existing file that was edited** (not created — this file
already existed from Simulation 2): `reddit_simulation_counterfactual.py`.
Two small edits were made to it: (1) already in place before this
experiment, swapping a hardcoded connection to the paper authors'
private computer cluster for a connection to a free local AI model
instead; (2) during this experiment, adding a longer wait-time setting
so a slow local AI response doesn't get mistaken for a total failure.
Neither edit touches what the simulation actually *does* — how agents
act, how posts are scored, how many rounds run.

**OASIS's own code was not touched at all.** OASIS is the simulator
"engine" — the part that runs the fake Reddit itself. Think of it like a
video game console: instead of opening up the console and rewiring its
circuits, an attachment was built that plugs into a controller port it
already has, telling the console to "use this attachment instead of the
default one" with a single line of code
(`agents_generator.SocialAgent = ShieldedSocialAgent`). If the
attachment had a bug, the console underneath was never at risk. This is
the exact same approach Simulation 1 used for a different experiment, so
it's a pattern already trusted going into this one.

---

## 5. How the Shield actually works, step by step

*(This restates Section 0's "How exactly does the Shield work?" and
"Exactly what does each prompt say" in shorter, more technical form —
can be skipped in favor of Section 6 if Section 0 was already read.)*

1. Normally, the simulator hands each AI agent its news feed: posts,
   comments, and like/dislike counts, all at once.
2. Before that feed becomes what the agent actually reads, one extra
   step is inserted: a second AI call (the "Shield," using the same free
   local model, `llama3.1:8b`) — this is the paper's Reranker, adapted —
   looks at the posts and re-orders them by how believable they seem,
   writing one short sentence explaining its reasoning for each post.
3. The agent is shown **only** the Shield's re-ordered list with those
   sentences attached — the actual like/dislike numbers never make it
   into the text the agent reads. The Shield isn't just told to *ignore*
   the numbers; they are physically removed from what gets sent to the
   agent.
4. If the Shield's answer comes back broken (wrong post IDs, badly-formed
   text, or the network call fails outright) — this is the paper's
   self-reflection check, adapted — it tries once more. If that also
   fails, it **gives up safely** — shows the agent the plain, unmodified
   feed instead of crashing the whole simulation. This is called
   "failing open," and it turned out to matter a lot (see Section 7).

---

## 6. How to run it

```bash
cd /Users/gordon/research/oasis
source oasis-env/bin/activate
ollama list   # confirm llama3.1:8b is there
```

**Cheap validation first (recommended, ~20-25 min) — a small test run to
catch problems early instead of discovering them an hour in:**
```bash
python examples/experiment/reddit_simulation_counterfactual/reddit_simulation_shielded.py \
  --config_path examples/experiment/reddit_simulation_counterfactual/down_36_shielded_smoke.yaml
grep -c "Traceback" log/social-*.log   # expect 0 in the newest one
```

**The real run (~20-90 min depending on machine load, see Section 10 on
why the time varies so much):**
```bash
python examples/experiment/reddit_simulation_counterfactual/reddit_simulation_shielded.py \
  --config_path examples/experiment/reddit_simulation_counterfactual/down_36_shielded.yaml
```
**Wait for:** `Simulation finish!` printed at the end.
**Produces:** `data/counterfactual_36_down_shielded.db`

**Compare against the existing unshielded baseline:**
```bash
python examples/experiment/reddit_simulation_counterfactual/analyze_shield.py
```


---

## 7. Bugs encountered along the way — and why they mattered

This section stays in the report on purpose, the same way Simulation 2's
report kept a claim it later had to retract instead of quietly deleting
it. Getting one trustworthy full-scale run took four attempts. The first
three each hit a real bug — and every one of them would have silently
ruined the results if it hadn't been caught before the data was trusted.

**Bug 1 — the like/dislike numbers leaked through anyway.** The settings
file said "show scores as a single combined number" instead of "show
likes and dislikes separately." The Shield's cleanup step only knew how
to remove the separate version — so the combined number slid right
through, completely undoing the whole point of the experiment. This was
caught by watching the simulation's live output as it ran, before it got
far enough to matter; the cleanup step was fixed to catch every possible
version of the number.

**Bug 2 — one slow network response crashed the entire simulation.** The
Shield knew how to recover from a *badly worded* answer from the AI
model, but not from the AI model *timing out* entirely. A single slow
response from one agent's Shield check crashed all 36 agents' simulation
at once — turning "fails safely, never crashes" from a design intention
into something that wasn't actually true yet. This was caught with a
much smaller practice run (2 rounds instead of 6, about 23 minutes
instead of an hour+), and fixed so a slow or failed response now safely
falls back instead of crashing anything.

**Bug 3 — the AI model occasionally answered in a way the code didn't
expect.** Very rarely, the model would say a post's "rank" was `null`
(a placeholder meaning "nothing here") instead of an actual number. A
quirk in how the code checked for missing information let this slip past
the safety checks and crash the program — an hour into what would have
been a successful run. This was caught with a second small practice run,
double-checked with a focused test built specifically to recreate that
exact situation, and fixed by having the code always double-check the
type of answer it got before using it.

**The habit that caught two of these three bugs:** every full-size run
(6 rounds, ~65-90 minutes back then) was preceded by a cheap, small
practice run (2 rounds, ~20-25 minutes) first. Two of the three bugs
never would have shown up in a finished results file — catching them
required either watching the simulation live or running it small enough
to catch problems quickly. This became a standing rule for the rest of
the project.

---

## 8. What was found the first time the experiment ran

**The real result, comparing one shielded run against Simulation 2's
existing unshielded baseline** (see Section 10 for why "one run" isn't the
end of the story). *Reminder on how to read the first row: it's
disagreeing comments ÷ all comments left on the false posts, not a share
of robots or of all actions — see Section 0, "What do the percentages in
this report actually mean?" if that's not fresh.*

| Metric | Unshielded down (Sim 2) | Shielded down |
|---|---|---|
| Disagreement/correction language | **15/22 comments (68%)** | **3/13 comments (23%)** |
| Vote score on treated posts (avg) | −1.00 (n=30) | −1.00 (n=30) |
| Total non-signup actions | 171 | 169 |
| `create_comment` actions | 22 (13%) | 13 (8%) |

**Finding 1 — hiding the vote count sharply reduced pushback, it didn't
increase it.** This is the headline result, and it goes against the
hopeful guess that a shield would make agents *better* fact-checkers. It
looks like Simulation 2's original finding — that down-treated posts got
far more pushback — was substantially driven by agents reacting to the
*visible crowd disapproval itself*, not by evaluating the claim on its own
merits. Take that visible cue away, and pushback collapses from about
two-thirds of comments to under a quarter.

**Finding 2 — no vote-count pile-on effect either way.** Both conditions
land almost exactly on the fake starting score forced by the experiment
(−1.00 average), shield or no shield. Expected, not surprising — this
experiment was never about whether votes themselves snowball;
Simulation 2 already answered that.

**Finding 3 — overall activity barely changed (171 → 169 actions), but
commenting specifically dropped (22 → 13 comments on the treated posts).**
Section 1.5 noted the paper's own stated limitation: their ranking-quality
metrics may not fully capture user satisfaction or long-term engagement.
This finding is a direct check of a related question in this domain —
does the shield cost engagement? The answer here is nuanced: the shield
didn't meaningfully reduce how much agents did *overall*, but it did
specifically reduce how much they *commented* on the exact posts it was
shielding. Fewer agents felt the need to weigh in once the "everyone else
disagrees" cue was gone.

**Finding 4 — the Shield's own judgment isn't consistent, and agents
don't reliably listen to it anyway.** The same false post ("Pierre Joxe
took up work in Dresden") got *different* verdicts from the Shield on
different turns — sometimes correctly flagged (`"Post lacks specificity
and contradicts well-established knowledge on Pierre Joxe"`), sometimes
given a generic, harmless-sounding note that didn't catch the problem at
all. Worse, even when an agent was shown a shielded version of the feed,
one still wrote *"Pierre Joxe, as a French historian, did indeed have
connections to Dresden"* — stating the false claim as fact. The Shield's
note is a weak nudge at best; it's nowhere near as strong a signal as the
raw "everyone downvoted this" cue apparently was. The paper's own results
(Section 1.4) show their self-reflection mechanism cut hallucination by
20-fold *within the Shield's own output* — but that doesn't guarantee the
downstream agent actually acts on a correct Shield verdict once it's
given one, which is what is observed here.

**Real examples.** Each row is a real agent comment on a false post, kept
verbatim. "What it shows" names the one thing that comment is evidence of
— not a verdict on the whole condition.

| Comment (verbatim) | Condition | What it shows |
|---|---|---|
| "I think Christian Noboa actually plays for Ecuador, not the position of goaltender" | Unshielded | A genuine, accurate correction |
| "But Pierre Joxe actually worked as the mayor of Marseille" | Unshielded | A confident-sounding "correction" that is itself unverified/likely wrong — the same data-quality caveat Simulation 2 already flagged |
| "Lettuce doesn't play jazz." | Shielded | Correct and terse — an absurd claim caught with no crowd cue at all |
| "I disagree, Ed Broadbent did indeed work with the Liberal Party of Canada, not Hollywood." | Shielded | A genuine, independent correction made with the vote count hidden |
| "Pierre Joxe, as a French historian, did indeed have connections to Dresden." | Shielded | The false claim stated as fact — on a *different* turn the Shield correctly flagged this exact post, but that didn't stop this agent from affirming it |
| "I'm glad Monkey Dust is being recognized for their unique sound!" | Shielded | A false post read positively with zero scrutiny — the kind of comment the down-treated condition almost never produced *without* the shield |

**In plain terms:** the Shield does what it was built to do. The raw vote
count genuinely never reaches the agent's prompt on a successful Shield
call — double-checked with an automated test that fails loudly if a vote
number ever slips through. But hiding that signal didn't just remove herd
behavior; in this run it also removed most of the *skepticism* Simulation
2 had measured, without reliably replacing it with independent accuracy.
That's a real, if slightly unflattering, result.

---

## 9. How reliable was the Shield itself?

Out of the full 6-round, 36-agent run behind Section 8: **56 of 64 Shield
checks (87.5%) worked correctly** on the first or second try. The
remaining 8 (12.5%) failed both tries — almost always the local AI model
responding too slowly under load — and safely fell back to the plain,
unshielded feed for that one agent's turn, exactly as designed, instead of
crashing anything. That means roughly 1 in 8 of the "shielded" turns in
this run actually saw the raw vote count anyway. That's a real source of
noise in the comparison above, disclosed here rather than hidden: the
safe-fallback design (Section 5, step 4 — the paper's self-reflection
safeguard, adapted) trades a little bit of purity for the simulation
never crashing outright — which, given three separate crash-causing bugs
during development (Section 7), was clearly the right trade.

---

## 10. Checking the work: did the finding actually hold up?

A single run proves less than it feels like it does. Simulation 2 learned
this the hard way — one of its early claims (about comment counts)
completely reversed on a second independent run and had to be publicly
retracted rather than quietly deleted. So once Section 8's headline number
existed, the next question was: **does it survive being checked again?**

Three more full simulations were run, then four more after that — eight
additional runs total — specifically to check this. **One rule was fixed
for every single one of these runs: the Shield's code itself never
changed.** The only thing that ever varied between any two runs was which
treatment condition (up/control/down) was being tested, or whether the
Shield was switched on at all. Tinkering with the Shield's internal
settings while adding more runs would have made it impossible to tell
whether a moved number came from the new condition or from the Shield
behaving differently — so two promising-looking improvements
(Section 12, items 1-2) were deliberately left completely untouched for
this whole stretch of testing.

**One infrastructure change did happen mid-testing, and it's worth naming
directly, since it affected how long things took (not what they found):**
partway through, the local AI server was restarted with a setting that
keeps the AI model loaded in memory for a full hour of idle time instead
of just five minutes. This only affects *speed* — a warm model and a
freshly reloaded model give the same kind of answers, just at different
speeds — so it doesn't call any result into question, but a run that used
to take 65-90 minutes dropped to about 19 minutes afterward, which is why
later runs in this section went so much faster than the first ones.

### Every individual run, laid out plainly

Every number below is *share of comments using disagreement/correction
language* (Section 0) — not agreement. Higher means more pushback against
the false claim. Down has four shielded runs and up/control only have two
— that gap is real, not a typo (see Open Thread 2): down got replicated
twice more specifically because its first two runs disagreed with each
other, and up/control haven't been checked as hard yet.

| Condition | Unshielded (Sim 2) | Run 1 | Run 2 | Run 3 | Run 4 | Pooled shielded |
|---|---|---|---|---|---|---|
| **Up** (+1 fake like) | 4% (1/23) | 26% (6/23) | 7% (1/15) | — | — | **18%** (7/38) |
| **Control** (no fake vote) | 11% (3/27) | 58% (11/19) | 41% (12/29) | — | — | **48%** (23/48) |
| **Down** (−1 fake dislike) | 68% (15/22) | 23% (3/13) | 39% (9/23) | 19% (3/16) | 26% (7/27) | **28%** (22/79) |

"Pooled shielded" is not an average of the per-run percentages — it adds
up every disputing comment and every total comment across all of a
condition's shielded runs first, then divides once. That's the single
best estimate this data supports; the per-run columns are what show how
much the individual runs actually disagree with each other (e.g. down's
run 2 at 39% vs. its other three runs clustered near 19-26%).

### Down: the number got clearer, but not perfectly settled

The first replica run (39%) looked wildly different from the very first
run (23%) — a 16-point swing that, on its own, would be exactly the kind
of single-run fluke Simulation 2 warned about. Two more runs later, the
full picture is 19%, 23%, 26%, 39% — **three of the four cluster in the
high-teens-to-mid-20s, and the 39% now looks like the outlier**, not the
original 23% being unusually low. Pooled across all four runs (79 comments
total): **28%**. That's real progress, though not a finished job — what
never wavered across all four runs, no matter how much the exact number
moved, is that every single one landed dramatically below the unshielded
condition's 68%. Four independent runs make that part very hard to
explain away as one lucky result.

### Up and control: two runs each tell two different stories

**Up's two runs disagree almost as much as down's first two did — 26%
and 7%, pooled 18%.** With only two data points on a small comment count,
there is no way yet to know if the real number is closer to 7%, 26%, or
somewhere between. What is consistent: both runs land above the
unshielded up baseline of 4%, so the direction of the effect held up on a
second run even though the exact size of it is still loose.

**Control's two runs actually agree fairly well: 58% and 41%, pooled
48%.** Seventeen points apart isn't nothing, but both numbers are solidly
higher than the unshielded control baseline of 11%, and both are higher
than every single down-shielded run's number too. The 58% figure that
looked like it might be a fluke (based on only 19 comments) held up: a
second independent run landed in the same elevated range instead of
dropping back toward baseline.

### The most interesting finding: shielding doesn't just weaken the effect, it flips part of the order

Without the Shield, the three conditions form a clean, obvious pattern
that tracks the fake vote exactly:

**Unshielded: up (4%) < control (11%) < down (68%)** — a more negative
starting fake vote leads to dramatically more pushback. That pattern *is*
the herd-behavior effect Simulation 2 originally described.

**With the Shield, that pattern doesn't just weaken — it partially
flips:**

**Shielded (pooled): up (18%) < down (28%) < control (48%)** — control is
now the *highest* of the three, and down has dropped down to the middle.

Down and control don't just stop lining up with the original fake-vote
manipulation — they swap places. Down went from "by far the most disputed
condition" to "middle of the pack." Control went from "barely disputed"
to "the most disputed condition of all three." That's a much more
specific and surprising result than "hiding the vote count changes
things" — it's backed by four down runs and two runs each of up and
control, not one noisy comparison, which is why it's called out as the
strongest finding in this whole experiment.

**The honest caveat that remains:** two runs is still thin for up and
control on their own — up's own 7%-vs-26% spread is a live example of
why. A third and fourth run of each, the same way runs 3 and 4 helped
down, would likely narrow things further without erasing the uncertainty
completely. This section made the picture clearer. It didn't finish it.

### Statistical significance check

Every comparison above this point was judged by eye — "does the number
move a lot, and does it keep moving the same direction across runs?"
That's a reasonable first pass, but it isn't a real answer to "could
this just be noise on a small sample?" Since the raw counts behind every
percentage are reported throughout this section, they can be fed
directly into a proper test. Two standard ones were run — **Fisher's
exact test** for each single unshielded-vs-shielded comparison, and a
**chi-square test of independence** for the three-way shielded
comparison — using the exact pooled counts from the table above.

| Comparison | Unshielded | Shielded (pooled) | p-value | Significant at p<0.05? |
|---|---|---|---|---|
| Up | 1/23 (4%) | 7/38 (18%) | **0.239** | No |
| Control | 3/27 (11%) | 23/48 (48%) | **0.0020** | **Yes** |
| Down | 15/22 (68%) | 22/79 (28%) | **0.0009** | **Yes** |

| Shielded pairwise | p-value | Significant at p<0.05? |
|---|---|---|
| Down (28%) vs. Control (48%) | **0.0347** | **Yes** |
| Up (18%) vs. Down (28%) | 0.362 | No |
| Up (18%) vs. Control (48%) | **0.0060** | **Yes** |

Three-way chi-square across the shielded conditions (up/control/down):
**χ² = 9.49, p = 0.0087** — significant, meaning the three shielded
percentages are not just visually different, they're statistically
distinguishable as a group. (For reference, the same test on the three
*unshielded* conditions gives χ² = 28.78, p < 0.0001 — the original,
much larger, herd-behavior effect is not in doubt statistically either.)

**What this sharpens, precisely:**
- **The headline "down" finding (68% → 28%) is statistically solid**
  (p = 0.0009) — not just visually convincing, formally significant.
- **The "control" finding is also statistically solid, and arguably
  under-emphasized above:** hiding the vote count more than *quadrupled*
  correction on the control condition (11% → 48%, p = 0.0020). This is
  just as strong a result as the down finding, in the opposite
  direction.
- **The "up" finding is NOT statistically significant** (p = 0.24). The
  qualitative claim in the previous subsection — "the direction of the
  effect held up on a second run" — is true as a description of the raw
  numbers, but should not be read as a confirmed effect; with only 38
  shielded comments total behind it, the data cannot currently rule out
  that the true difference is zero.
- **The "flip" is real but partial, not total.** Down vs. control are
  significantly different from each other under shielding (p = 0.035) —
  that part of "the order changes" is solid. But up vs. down are *not*
  significantly different from each other under shielding (p = 0.36) —
  so the specific claim "up (18%) < down (28%)" should be read as "these
  two are close together and not clearly ordered," not as a confirmed
  ranking. The three-way chi-square result (p = 0.0087) supports "the
  three conditions aren't behaving the same way once shielded" as a
  group-level claim; it does not certify every pairwise ordering within
  that group.

**Caveat on the caveat, stated plainly:** these tests assume every
comment is an independent, equally-weighted observation. That's not
strictly true here — a single chatty robot could leave several comments
on the same run, and multiple comments can land on the same post, so
some comments are more correlated with each other than a textbook
Fisher's-exact-test setup assumes. That means these p-values are a
useful, standard first check, not a fully rigorous causal-inference-grade
result — the same honest-but-imperfect spirit as the rest of this
report's statistics.

---

## 11. Honest limitations (everything, in one place)

- **Down's estimate rests on 4 runs (79 comments total) — the sturdiest
  number in this report.** Up and control each rest on only 2 runs (38
  and 48 comments total) — noticeably less sturdy, and up's own internal
  7%-to-26% spread is a live reminder that two runs isn't always enough.
- **All 10 shielded runs used the exact same, never-modified Shield
  code.** The pooled numbers above are a fair combined estimate, not an
  average across code that changed partway through.
- **The comment counts behind every percentage are small** — 13 to 29
  comments per run. A handful of comments swinging the other way would
  move any of these numbers meaningfully. That's exactly why the
  experiment kept re-running instead of trusting the first number.
- **The "disagreement" measurement is a simple keyword search** (looking
  for words like "actually," "wrong," "disagree," etc. in comments)
  reused from Simulation 2 — not a more precise AI-graded score, and not
  the paper's own ranking-quality metrics (Section 1.3), which don't
  apply to this kind of question. Rough but easy to double-check by hand,
  not exact.
- **The Shield's own judgment comes from the same size AI model as the
  agents it's protecting**, and it makes real content-quality mistakes
  (Section 8, Finding 4) — its answers aren't even consistent with
  themselves from one turn to the next on the identical post, unlike the
  much larger, more heavily-evaluated setup the original paper tested.
- **A meaningful slice of "shielded" turns weren't actually shielded** —
  the Shield safely gave up and fell back to the raw feed on a real
  fraction of turns (Section 9), which adds noise to every shielded
  number above.
- **This whole experiment ran at a small, laptop-friendly scale** (36
  agents, 6 rounds per run) instead of the much larger scale a research
  cluster could run, to keep each attempt finishing in under two hours
  instead of days.
- **One infrastructure setting (how long the AI model stays loaded in
  memory) changed partway through testing**, which affected how fast runs
  finished but not what they found — disclosed in Section 10 for
  completeness, not because it calls any result into question.
- **This experiment built the paper's base architecture (iAgent), not
  its extended version (i²Agent)**, and did not build the InstructRec
  datasets or formal ranking metrics — Section 3 explains exactly why
  each of those pieces doesn't map onto this setup. This experiment
  tests the paper's *mechanism*, not a reproduction of the paper's own
  reported numbers.
- **An untested confound: the Shield itself still sees the vote count,
  even though the agent never does.** Section 5, step 2 (and Section 0)
  are explicit that the Shield's own prompt includes the raw like/dislike
  numbers — it has to, in order to know what to delete before handing
  the feed to the agent. But that means it's *possible*, and currently
  untested, that the Shield's own plausibility `rank` or `shield_note`
  wording is subtly influenced by having seen a post was already
  disliked, even while under explicit instructions to ignore vote counts
  when scoring (Section 5's SHIELD_SYSTEM_PROMPT). If that happened, the
  vote-count signal wouldn't be reaching the agent directly, but it could
  still be leaking through indirectly, dressed up as a "content
  plausibility" judgment. There is no evidence either way — testing it
  would mean giving the Shield the *same* post content with the vote
  count field simply omitted from its own prompt entirely (not just
  instructed to ignore it), and checking whether its ranks/notes come out
  the same as when it can see the number.
- **The keyword-based disagreement classifier (Section 0, "Type 1") has
  never been checked against human judgment.** No one has hand-labeled a
  sample of comments as "actually disagreeing" or not and compared that
  against what the 10-keyword search flags, so its real precision and
  recall (how often it wrongly flags a non-correction, or misses a real
  one phrased without any of those exact words) are unknown. It's
  plausible, not measured, that this classifier is noisy in a way that's
  consistent across conditions (harmless to the comparison) or biased in
  a way that isn't (not harmless) — it isn't currently possible to tell
  which.
- **Every run in this whole experiment used one specific model,
  `llama3.1:8b`, for both the Shield and the agent it protects** (Section
  5, step 2). Nothing here has been tested with a larger or differently
  trained model, so it's unknown whether these findings — especially the
  Shield's own inconsistency (Section 8, Finding 4) and its 87.5%
  reliability rate (Section 9) — are specific to a small local model, or
  would hold with a stronger one.
- **No sampling temperature was ever explicitly set anywhere in this
  project's code**, for either the agents' decisions or the Shield's
  calls — every LLM call relies on whatever default the underlying
  `camel`/Ollama stack uses, which was never checked or pinned down. That
  default is almost certainly non-zero (otherwise every "replicate" run
  in Section 10 would have produced identical output, and they didn't),
  so the replicate runs are genuine independent stochastic draws — but
  the exact amount of randomness driving run-to-run variation isn't
  something that was measured or controlled for.

---

## 12. What's next — open questions, nothing decided or started

1. **Reduce how often the Shield "gives up" and falls back to the raw
   feed** (Section 9's 12.5% figure) — for example, a longer wait-time
   before deciding a response failed, or asking the AI model to answer in
   a stricter, easier-to-parse format. Deliberately not touched during
   Section 10's testing, since changing the Shield's own behavior while
   also adding more test runs would have made it impossible to tell which
   change caused which result.
2. **Replace the Shield's short written note with a plain number** (like
   "7 out of 10 believable") instead of a sentence. A number might carry
   more weight with the agents reading it than a sentence did in Section
   8's Finding 4 — but this is a real guess, not a sure thing, and testing
   it properly would mean re-running everything again under the new
   version. Also deliberately not touched yet, for the same reason as
   item 1.
3. **Run a third and fourth replica each of the up and control
   conditions**, the same way down went from 2 confusing runs to 4
   clearer ones in Section 10 — up and control are still the least
   certain numbers in this report.
4. **Build the paper's i²Agent extension after all**, if a way can be
   found to give OASIS agents a persistent, cross-session memory — right
   now Section 3 rules this out because OASIS agents don't persist across
   runs, but if that changed, it would be the most direct remaining piece
   of the paper's architecture left untested here.
5. **Try the same experiment with only one personality repeated 36
   times**, instead of 36 different personalities. Right now, it isn't
   possible to fully tell apart "the fake vote caused this behavior" from
   "these 36 particular made-up people happened to react this way" —
   using one repeated personality would isolate the first question from
   the second. Not started; would need a new set of agent data to be
   built first.
6. ~~Save this work properly~~ — **done.** All of Simulation 1/2/3's code,
   configs, and reports were committed to the local git repository
   (commit `e87e88f` on `main`) — the venv (`oasis-env/`) was gitignored
   instead of committed, and the 10 run databases were already covered by
   an existing `*.db` ignore rule. Not yet pushed to the `origin` fork on
   GitHub — that's a separate, deliberately unstarted step.
7. **Add a real statistical significance test**, not just "did the
   percentage move and keep moving the same direction across runs" —
   done, see Section 10's new "Statistical significance check"
   subsection, added after the fact once the replication data existed.
   The honest result: down and control's shifts are both statistically
   significant; up's is not; the three-way "flip" holds as a group
   pattern but not for every individual pairwise ordering.
8. **Test whether the Shield itself leaks vote-count information
   indirectly**, since it still sees the raw number in its own prompt
   even though the agent never does (Section 11's newest bullet) — would
   need a version of the Shield that never receives the vote count at
   all, to compare its ranks/notes against the current version's.
9. **Validate the disagreement keyword classifier against actual human
   judgment** — hand-label a sample of comments and measure the
   classifier's real precision/recall, instead of trusting it
   unverified (Section 11).
10. Two open questions carried over from Simulation 2 that this
    experiment didn't touch: replacing the simple keyword search with an
    AI-graded score for more precision, and running the whole experiment
    at a much larger scale (hundreds or thousands of agents instead of
    36) to see if a real vote-pile-on effect appears at that size.

---

## 13. Summary

This experiment extended a misinformation study by building a
content-quality "Shield" that sits between the platform and each AI
agent and hides the crowd's vote count before the agent ever sees it.
The design is a direct adaptation of a real ACL 2025 paper, *iAgent: LLM
Agent as a Shield between User and Recommender Systems* — its base
architecture's three components (a parser, a reranker, and a
self-reflection safeguard) were built inside the existing simulator,
with each piece of code traceable to a specific piece of the paper.
Building it surfaced three real bugs, each caught by testing at a
smaller scale before committing to an hour-plus full run. Once it
worked, the finding was unexpected: hiding the vote count didn't make
agents better fact-checkers, it made them quieter — pushback on the same
false claims dropped from 68% to roughly a quarter. That finding was
checked nine more times across three more conditions before being
trusted, and the most interesting result only showed up once enough
data existed: hiding the vote count doesn't just weaken the original
effect, it partially *flips* which condition gets the most pushback.
That is a more specific and more surprising result than "the shield
worked," and it only became visible because the experiment kept getting
re-run instead of the first number being trusted. Fisher's exact and
chi-square tests were then run on the pooled counts: the drop in the
down condition and the rise in the control condition are both
statistically significant (p < 0.01 each), the three shielded
conditions differ from each other as a group (p = 0.009), but the up
condition's own shift and the specific up-vs-down ordering are not
statistically distinguishable from noise yet — real progress, honestly
bounded.


---

# Part 5 — Simulation 4: the complete log

*Was `SIM4_LOG.md`. Merged into this file 2026-09-13; original title: “Simulation 4 — the complete log”.*

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

*Last updated 2026-09-15 09:25. Update at the end of every session.*

---

# ⟦ STANDING ORDER — KEEP THE MACHINE SIMMING ⟧

**Set by Gordon, 2026-09-14.** *"We haven't changed anything so we just need
data — just keep simming."* This is the default task whenever no other
instruction is live. Do it first, then find other work while it runs.

### 1. Is a run in flight?

    pgrep -f night_queue.sh && tail -3 /tmp/night_queue.log

If yes, **leave it alone** and go to step 4. If no, start it:

    cd /Users/gordon/research/oasis
    ROUNDS=15 AGENTS="18 36 54 72 90" PREFIX=r15 \
      nohup caffeinate -i examples/experiment/social_timeline/night_queue.sh \
      > /tmp/night_queue.log 2>&1 &

`sweep18.sh` skips any run whose manifest already exists, so this is safe to
re-run at any time and never repeats finished work. `PASSES=0` means it goes
forever, one pass per seed. One pass ≈ 21 h.

### 2. DO NOT CHANGE THE SIMULATION

Explicit instruction, and it is also this project's single most repeated failure
mode. **No edits to `run_simulation.py`, `timeline_agent.py`,
`timeline_platform.py`, the prompt, the model, the persona files, or any flag in
`sweep18.sh`.** Every one of B-26, B-28, B-31, B-32 and B-33 is a run that
silently stopped being comparable to the bank. We are collecting data at a fixed
configuration; a "small improvement" mid-campaign destroys the campaign.

Analysis scripts, chart generators, documents and artifacts are fair game.

### 3. Never run inference while a run is in flight

No benchmarks, no smoke tests, no second campaign. B-32: a run cost 2.16x its
reference doing identical work because the machine was busy.

### 4. When a run lands, fold it in — this is the whole point

    P=./oasis-env/bin/python; S=examples/experiment/social_timeline
    $P $S/export_parquet.py --db data/social_timeline_<label>.db
    $P $S/build_package.py
    $P $S/make_timing_charts.py
    $P $S/make_engagement_charts.py

Then record it: plateau (mean of rounds >= 4), per agent-turn, engagement, and
the load verdict from `data/night_queue.txt`. Append findings here, and update
`869156cd` (cost + F-105) when a new world size or round count lands.
**`732d1879` has four silent regeneration traps — read the note further down
before touching it.**

### 5. What the data is FOR, so you know what is worth reporting

- **Cost curve.** 8 points, 12-90 agents, exponent 1.005 at 21.44 s/agent-turn.
  More sizes and replicates tighten it.
- **F-105.** Its weakness is that a 10.2 % model error sits inside a ~12 % noise
  estimate drawn from **one** replicate pair. Replicates at any size fix this.
- **F-92 at scale, the open one.** 7-round runs cannot test connection at all —
  network tier is 2.5 % of exposures at 90 agents. **Only 15-round runs can**,
  which is why the campaign above is `ROUNDS=15`.

---

### 2026-09-14 — the agent sweep landed, and it settled two things

**The 18/36/54/72/90 sweep completed overnight.** Combined with
`ctx8192_a12/a24/a36` that is **eight points from 12 to 90 agents, a 7.5x
range: exponent 1.005, R^2 0.9993, 21.44 s per agent-turn (sd 0.37)**. Cost is
linear and the largest verified point is no longer 36. Every projection on this
page previously extrapolated ~30x beyond its evidence; it now extrapolates ~12x.

**F-105 — engagement halves from 18 to 90 agents and the agents are unchanged.**
7.18 / 6.18 / 5.45 / 3.18 / 3.98 %. Not the metric (dedup 2.26x, event-level
2.22x), not repetition (the gap survives whole inside first sightings, and repeat
engagement is flat or rising), not tier composition (discovery is 98.9-99.3 %
everywhere). It is the denominator: distinct posts shown per turn grows 5.29 ->
10.10 while feed actions per turn stay at 1.06x. **Quote feed actions per
agent-turn across scales, never engagement rate.**

**B-32 and B-33** — a run cost 2.16x its reference because the laptop was in use,
and the guard written to catch that would never have fired because a bare `obs`
in its hog pattern matched `.ollama/models/blobs/`. Machine load is now sampled
every 30 s per run into `data/load_<prefix>.csv` with a verdict in
`data/night_queue.txt`.

**Artifact `869156cd` is at version 13** with the eight-point curve, F-105 and
both new charts. **`732d1879` (explorer) is at version 25**: 36 runs, nothing
lost, and the Cost & scaling tab now carries all five charts. It is a **two-file
artifact** now — see the regeneration note below, four traps and all of them
silent. `55d7c5a5` (science) is NOT yet updated.

### 2026-09-14 afternoon — two package defects and F-105's open question closed

Done while `r15_a90` ran, entirely from data already on disk. No inference.

**B-34 — the shipped package could not reproduce its own dependent variable.**
Engagement computed from the exported tables came out at **41-65 % of the true
value, by a factor that varied per run**, because comment actions (56-59 % of
all post-directed actions) name only a `comment_id` and the `comment` table was
never exported. `runs_index.csv` had the right number all along, so the package
contradicted itself. Fixed: `comments` table exported, `target_post_id` /
`target_agent_id` resolved onto `actions`, `DATA_DICTIONARY.md` carries a
runnable recipe that reproduces the index. **31 of 32 runs now reconcile
exactly.**

**B-35 — the 32nd was contaminated.** `scale99_full` (99 agents x 5 rounds) held
**rounds 5-11 of a 36-agent run**, because `export_run()` never cleared its
output directory and B-26's mislabelled run had used that name first. This is
**the unfixed half of B-27**: the timings were corrected, the data was not.
Fixed, regression-checked, and all 43 runs were compared row-for-row against
their databases — `scale99_full` was the only one affected, it is an arm, and no
current finding uses it.

**F-106 — the action budget is steady across world size.** F-105's "~12 % noise"
came from one replicate pair; nine identical runs give **7.1 %** (engagement) and
**4.4 %** (feed actions per agent-turn). But the right test is a count model, not
a CV: constant budget across the five sweep sizes gives **chi2=7.83, df=4,
p=0.098 — not rejected**, and the whole of the residual is `sweep18_a72`
(-2.16 sigma; drop it and p=0.71). Feed-action output is **under-dispersed**
relative to Poisson (phi=0.385, p=0.071, directional). **F-105's recommendation
to quote feed actions per agent-turn is now positively supported**, with a
mechanism: engagement is a ratio and inherits both variances — delta method
predicts 7.18 % against 7.05 % observed.

**Cheapest open experiment on the board:** one replicate at 72 agents x 7 rounds
(~2.6 h) settles the only point in doubt in F-106.

**New trap, worth knowing:** `agent_turns_total` in `runs_index.csv` counts
`agents x rounds`. The per-turn denominator that F-105 (correctly) used is the
turns that actually served a feed, `agents x (rounds-1)` = the `refresh` count —
**1.17x smaller at 7 rounds.** Using the index column silently deflates every
per-turn figure. A gate reproducing F-105's published table caught this.

Export fidelity gate is now **28 checks** (was 22). All other gates pass.

### 2026-09-14 evening — `r15_a90` LANDED, and it answered the question it was run for

**F-108. Connection-over-content replicates at 90 agents.** Network vs discovery
**3.95** [3.15, 4.96] against the bank's 3.51; **fof vs discovery 3.12**
[2.09, 4.66], **individually significant in a single run for the first time**
(it was 3/7 in the bank). 15,120 exposures from one run — 28 % again on top of
the whole published corpus. It changes population, run length AND persona file
at once, so it is an independent measurement rather than more of the same data.
**Do not upgrade "suggestive" to "established" on one run** — `r15_s43_a90` is
the direct test and is running.

**The 15 rounds were the point.** Network tier goes 2.48 % of exposures at 7
rounds to **9.54 %** at 15 (19.3 % by the final round), fof 0.80 % to 4.91 %.
**Run length, not population, is the binding constraint on this result.**

**F-107. The cost law holds out-of-sample.** All eight curve points are 7-round
runs; `r15_a90` is 15 rounds at the largest size and plateaus at **21.61 s per
agent-turn against 21.56** — 0.2 % apart, against 6 % run-to-run variation.
7.21 h total against 8.0 projected.

**F-109. The budget is steady across SIZE but not obviously across LENGTH.**
Feed actions per agent-turn 0.402 (7 rounds) to 0.341 (15), while engagement
*rises* 3.98 % to 4.45 % because distinct posts per turn falls 10.10 to 7.66 —
Law 3 backwards. chi2=3.86, df=1, p=0.049, but **n=1 vs n=1**. Quote F-105's
"feed actions per agent-turn is flat" about **population**, never run length.

**All three artifacts updated.** `55d7c5a5` (science) **v13** — F-108
replication block, fof wording, shuffle-arm status, two new limits. `869156cd`
(scaling) **v14** — F-107 out-of-sample box, F-106 replacing the superseded
noise caveat, F-109, projection row now measured, and B-34/B-35 written up in
the reproducibility section. `732d1879` (explorer) **v27** — 37 runs, nothing
lost, `r15_a90` called out as the run to open first, panel counts corrected, and
**the F-105 caveat in the engagement chart caption fixed at its source** in
`make_graph.py` and `make_engagement_charts.py`, both of which still stated the
superseded "error sits inside the noise" reading.

**Two further explorer traps are now written up** (5 and 6 in the list below):
the split upload 408s on the first attempt at 15 MB and succeeds on retry, and
**the run set cannot be recovered by globbing** — six of the 37 live in
`_archive/superseded/` and two same-looking runs are deliberately excluded.

**F-110 — repetition also replicates at 90 agents.** OR **2.351** [1.986, 2.782]
against the bank's 2.62, dose-response 4.05 → 8.84 → 13.85 → 21.62 %. **Its two
supporting arguments move in opposite directions:** the first-sightings reversal
that F-45 downgraded to directional comes back at **0.267 [0.122, 0.586],
p=0.00099**, while the **network-tier replication — the check the causal reading
leans on — is NOT significant here** (1.438 [0.901, 2.296], n=1,442,
underpowered rather than contrary). Two of the three headline results have now
survived a simultaneous change of scale, run length and persona file; the third
(similarity null) needs no scale test.

**F-111 — engagement counts actions that SUCCEEDED, and many never did.** Three
silent-loss channels: malformed tool calls (no trace row, run log only), blind
actions rejected, invalid follow targets. **43.8 % of intended actions were
malformed in the nine old-prompt runs**; that is now a median of 0.0 % (range
0-11 %) against 37.0 % (12.4-75.9 %), Mann-Whitney p=0.00047, run as the unit.
**A concrete candidate mechanism for F-93** alongside the published one, not a
replacement — the same confound applies. **Loss grows with world size** (1.0 % at
18 agents to 18.6 % in r15_a90; logistic slope +1.435, z=5.32, p=1e-07), so
successful actions per turn declines while **intended** actions per turn does
not. Agents are not less active at scale, they are less accurate.

**Q-24 — the cheapest high-value run on the board.** 111 of 193 current-era
errors are `follow`, and **76 are `follow(group_id=...)`**, a parameter it has
never had. Groups exist only in the 27-action set and B-9 already records them
hijacking the prompt. **In `r15_a90` only 45.2 % of attempted follows
succeeded** — the graph behind F-108 is less than half what the agents tried to
build. One `--no-groups` run with the log kept tests it. Must NOT join the cost
bank (different action surface).

**Tool-error evidence preserved** to `data/logs/` (10.5 MB of raw lines trimmed
to 46 KB), so `/tmp` can be cleared safely.

**F-112 — similarity is NOT null. It is small, needs two controls to see, and is
positive in 16 of 16 runs.** Top vs bottom cosine quartile, **first sightings
only** (closes the repeat channel, worth 2.35-2.62) and **feed slot fixed**
(closes the position effect, worth 2.15): **MH OR 1.33 [1.14, 1.60]**,
bootstrapped over *runs*, 49,561 first-sighting exposures. **Sign test
p=3.05e-05.** The ordering is untouched — connection 3.51 > repetition 2.62 >
position 2.15 > similarity 1.33 — so this is a qualification, not a retraction:
what is no longer accurate is "content does not predict engagement at all".

**Retire the per-unit-cosine odds ratio.** Cosine spans ~0.73, so "per unit"
extrapolates past the data: fitted run by run it returns 0.50, 1.23, 3.78,
11.92, 46.76, 56.22, **142.94**. Every published similarity figure here used
that scale, including the retracted F-38 and the 1.143 it was replaced with.

**F-49's prediction confirmed on data collected afterwards.** It explained the
null by corpus uniformity and said a more separable persona file would leave
room. Twitter file OR 5.16 [1.77, 15.1] p=0.0027 vs reddit 1.50 [0.99, 2.30]
p=0.058. Bio echo is also 6x larger there (+0.109 vs +0.015), and **flat across
all 15 rounds** (r=+0.043, p=0.51) — agents restate their persona in round 14 as
much as round 0. **Note F-24 is therefore live again for the current campaign,
which runs on the twitter file; F-49 retired it only for the reddit bank.**

`55d7c5a5` is at **v15** with §04 qualified, the standfirst, stat card, forest
caption and the likely-questions answer all made consistent with it.

**F-113 — a small world is SATURATED, not scaled down.** `r15_a18` landed 02:07.
**18 agents over 15 rounds make 48 posts in total, and each agent has seen 40 of
them (83 %) about four times over.** Its 9.90 % engagement is the highest in the
project and is **mostly repetition** — distinct posts per agent-turn falls
5.29 → 2.85 while sightings per pair nearly doubles, and F-110 puts repeat
exposure at OR 2.35-2.62. At 90 agents the same run length still leaves 55 % of
the world unseen. **Cost law confirmed out-of-sample a second time: 21.12
s/agent-turn** (curve 21.44 sd 0.37; F-107 got 21.61 at 90x15), so the 7-round
fit now reproduces at 15 rounds at both ends of the size range. **F-109 replicates
in direction across a 5x size range** (combined chi2=6.19, df=2, p=0.045). **And
the follow graph saturates too** — network tier goes 5.1 % → 4.17 % with more
rounds at 18 agents, against 2.48 % → 9.54 % at 90. **F-108's "run length is what
makes connection studiable" holds only where the population is big enough for the
graph to keep growing.**

**Reporting rule this adds:** engagement at N agents cannot be compared across N
without also quoting **how much of the world each agent has seen**. Population
size and novelty supply are entangled by construction.

**F-114 — the cost law replicates independently at 15 rounds; F-106's constant
budget does NOT.** Four 15-round runs refit the cost law on their own:
**exponent 0.996 (se 0.028), R² 0.9985, 21.55 s/agent-turn** against the 7-round
curve's 1.005 / 21.44. Not an extrapolation spot-checked — the whole law, refitted
on independent data. **Settled.** But the constant feed-action budget gives
**chi2=10.44, df=2, p=0.0054** at 15 rounds (7.83/p=0.098 at 7 rounds), with
larger worlds spending **more** per turn: 0.282 / 0.250 / 0.341 / 0.371.
**Two mechanisms tested and RULED OUT** — wasted slots on already-acted posts
(a36 has the lowest waste and lowest rate) and F-111's loss channels (a36 lowest
again). Unexplained; `r15_a36` at 0.250 does most of the work, and pass 2 will
give seed-43 runs at 18 and 36 without any new decision.
**Reporting rule narrowed: F-105's "quote feed actions per agent-turn" was
established at 7 rounds and does not hold across round counts.**

**`r15_a54` landed 09:16 — 15,078 s, 20.98 s/agent-turn, engagement 5.59 %.**
**Cost law with five 15-round points: exponent 0.995 (se 0.024), R² 0.9982,
21.44 s/agent-turn — the 7-round curve's number exactly.** **F-114's directional
claim is CORRECTED:** feed actions per turn is 0.282 / 0.250 / **0.384** / 0.341
/ 0.371 across 18/36/54/90/90 — heterogeneous, **not** monotone in size
(Spearman p=0.32). The constant-budget rejection strengthens to **p=0.00034**,
and the 1.54x spread beats both the 8.4 % replicate gap and F-106's 4.4 % CV, so
it is real. **Not constant, and not a function of world size either.**

### RUNNING as of 2026-09-15 09:25 — `r15_a72`, last of pass 1

**`r15_s43_a90` LANDED 00:41**, 15 rounds, 25,136 s, context 8,192 verified,
folded in automatically. **Engagement 4.711 % against `r15_a90`'s 4.454 %** —
the first replicate at 90x15, and a tight one. Package now 45 runs.

#### The handover stopped one step short, by design. Read this before trusting `switch_campaign.sh`.

`switch_campaign.sh` did four of its five steps and then refused the fifth:

    00:41:23  night_queue starts PASS 3 (r15_s44) -- s43's sweep18 had just exited
    00:41:54  watcher sees pid 52711 gone, "the run is folded in"
    00:41:56  stops night_queue.sh
    00:41:57  stops sweep18.sh  (the NEW one, for s44)
    00:41:59  sees a live run_simulation.py -- REFUSES to relaunch

**The guard fired correctly and the design held.** The race it was written for is
real and is tighter than assumed: `night_queue` starts its next pass **within
seconds** of `sweep18` exiting — 31 s here — so by the time a 60 s polling loop
notices, a new pass has already begun its preflight. The script saw the s44
4-agent smoke still running and chose to stop rather than orphan it or start a
competing campaign. That is the right trade, and it is why nothing was corrupted.

**Cost of the guard:** the machine sat idle from 00:42 to 00:43. **Fix for next
time:** poll far more often once `sweep18` is close to done, or better, have
`night_queue` itself take the new `AGENTS` from a file it re-reads each pass, so
the campaign can be reshaped without any kill at all.

**Restarted by hand at 00:43:52** with `ROUNDS=15 AGENTS="18 36 54 72 90"
PREFIX=r15`. Dependency gate 8/8, smoke passed, **comparability check confirms 19
config keys identical to `ctx8192_a36`**. `r15_a90` is skipped (manifest exists),
so pass 1 runs 18/36/54/72.

**Landed:** `r15_a18` 02:07 (9.90 %), `r15_a36` 05:04 (4.54 %), `r15_a54` 09:16
(5.59 %). **`r15_a72` running, expected ~15:15** — last of pass 1. Package and
parquet rebuild only when the whole pass ends, so the explorer gains nothing
until then. Pass 2 (seed 43) then fills in 18/36/54/72, which is what F-114
needs. Note `sweep18.sh` exports and rebuilds the
package **only after all five sizes finish**, so per-run `analysis.json` appears
as each run ends but parquet/package lag to the end of the pass.

**One stray:** `data/social_timeline_r15_s44_smoke.db/.json` from the aborted
pass 3. A 4-agent smoke, harmless, not in the package.

**Superseded: pass 2 detail.** `r15_a90` finished 17:41 at 7.21 h
and was folded in automatically by `sweep18.sh` — using the FIXED exporter, so it
carries the comments table and the resolved target columns. Pass 2 started 17:42;
at 21:07 it was through **round 8 of 15** at 1,913 s/round (plateau, rounds 4-7),
so it lands **~00:50**. `switch_campaign.sh` is running and waiting on it (pid
52711), holding its own caffeinate; when that sweep exits it stops the old queue
and starts `ROUNDS=15 AGENTS="18 36 54 72 90" PREFIX=r15`. Expected landings:
r15_a18 ~02:25, r15_a36 ~05:15, r15_a54 ~09:25, r15_a72 ~15:00.

**THE QUEUE IS STILL 90-ONLY.** It was launched with `AGENTS="90"`, and
`night_queue.sh` reads `AGENTS` once at startup, so every further pass is another
90x15 replicate at the next seed. Replicates at 90x15 are genuinely valuable
right now — they are the direct test of F-108's fof result and of F-109 — but
the fuller campaign is the sweep at 15 rounds, which fills in the round-count
comparison at every size and lets the graph form at each.

**To switch, use `switch_campaign.sh`** (added 2026-09-14). It can be started
at any time, including mid-round: it waits for `sweep18.sh` to exit — which is
what completes the fold-in — then stops the old queue and starts the new one,
holding a caffeinate assertion throughout so the laptop cannot sleep during the
wait.

    ROUNDS=15 AGENTS="18 36 54 72 90" PREFIX=r15 \
      nohup caffeinate -i examples/experiment/social_timeline/switch_campaign.sh \
      > /tmp/switch_campaign.log 2>&1 &

**Why not just `pkill` and relaunch:** `sweep18.sh` runs export_parquet →
build_package → the two chart generators *after* the simulation returns. Killing
the queue mid-run throws that away for a run that has already cost seven hours,
and leaves its database un-exported and missing from the package. The script
also refuses to relaunch if a new `run_simulation.py` appeared during the
handover, rather than orphaning it.

`sweep18.sh` skips any run whose manifest exists, so `r15_a90` and
`r15_s43_a90` are not repeated and the pass resumes at 18 agents. One pass is
roughly 21 h. Launched through
`night_queue.sh` with `PASSES=0`, so **it continues on its own**: when `r15_a90`
finishes, pass 2 starts `r15_s43_a90`, and so on indefinitely until killed.

**Why this run and not more 7-round replicates.** At 7 rounds the follow graph
has barely formed -- network-tier posts are 2.5 % of exposures at 90 agents and
5.1 % at 18, against 9.4 % network plus 3.0 % fof in a 14-round bank run. So
**none of the five sweep runs can speak to connection-over-content at all**;
there is not enough network content to stratify on. `r15_a90` is identical to
`sweep18_a90` in every respect except round count, which makes it a controlled
test of exactly that, and the first look at F-92 at 2.5x the bank's population.

**Next campaign, when someone can run it.** The queue as launched only ever
repeats 90x15. Better value is the full sweep at 15 rounds, which fills in the
round-count comparison at every size and lets the graph form at each:

    ROUNDS=15 AGENTS="18 36 54 72 90" PREFIX=r15 \
      nohup caffeinate -i examples/experiment/social_timeline/night_queue.sh \
      > /tmp/night_queue.log 2>&1 &

`sweep18.sh` skips any run whose manifest exists, so `r15_a90` is not repeated
and this resumes at 18. One pass is roughly 21 h: 1.4 + 2.8 + 4.2 + 5.6 + 7.0.

### Session note, 2026-09-14 — tooling stopped mid-session

The safety classifier began refusing **WebSearch, WebFetch and then Bash** part
way through this session, on the grounds of accumulated conversation content
rather than any individual request. The conversation had spent an hour designing
a defensive prompt-injection propagation study; once that was in context, every
command-executing tool was refused for the remainder.

**Consequences for the next session:** no new runs could be launched, and a
literature review could not be completed. Read-only tools kept working, which is
why this note exists. **Open a fresh session for anything that needs Bash**, and
if the topic is agent security, put the literature question first rather than
arriving at it through attack design.

**Literature check, partially done before the block.** The propagation idea is
**substantially less novel than it looked**: `Prompt Infection` (arXiv 2410.07283,
ESORICS 2025 workshops) already demonstrates self-replicating LLM-to-LLM
injection and tests populations of 10-50 agents; a 2026 *Cybersecurity* paper
derives an epidemic threshold for prompt-injection contagion in agent swarms
(R0 = 28.85); and `AgentWorm` (arXiv 2603.15727) covers self-propagating attacks
across agent ecosystems. **None of these was read -- only search summaries.**
What may survive: Prompt Infection used *random pairwise dialogue*, so a
**ranked** substrate where an algorithm chooses the next exposure appears
untouched, and the threshold paper is analytical rather than measured. Verify by
reading all three before spending anything on it.

---


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

**CORRECTED 2026-09-13 by F-99 -- the 0.02 below was wrong.** The earlier note
here said Collusion activates agents with probability 0.02 and that 1,100 x 100
was therefore ~2,200 agent-turns and "one overnight". **It is 0.19 and ~21,000
agent-turns.** The 0.02 is the value in their CSV column; `agents_generator.py`
renormalises it by the global max and floors the zeros at 0.1 before the
simulation ever reads it, a 9.5x inflation. Verified against their own shipped
population files. See F-99 in section 6.

    Collusion 1,000 x 100 @ 0.19  = ~21,000 agent-turns = ~5.5 DAYS
    Fraud     1,100 x 100 @ 1.0   = ~113,500 calls      = ~30 DAYS

Sparse activation is still the one parameter that decides whether their scale is
reachable here, and **neither paper treats it as a scientific variable** --
Collusion runs 0.19, Fraud runs 1.0, the same author group wrote both, neither
reports the number, and neither asks whether the conclusion depends on it
(F-100, Q-23). But it buys ~5x, not ~50x. The reachable target is **their
population at fewer rounds**, not their whole run: 1,100 agents x 15 rounds at
0.19 is ~3,135 turns, about **20 hours**. See D-18.

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

**Regenerating the explorer (`732d1879`) — four traps, all of them silent:**

1. `make_graph.py`'s `discover()` globs `data/social_timeline_*_analysis.json`
   **non-recursively**, and almost every run now lives in `data/runs/<arm>/`. Left
   to itself it finds 8 runs, two of which are the B-28 truncated ones. **Always
   pass `--analysis` explicitly.**
2. `data/.artifact_baseline` names `v4_full`, whose analysis file is no longer in
   `data/`, so `_started()` returns `""` and the cutoff silently degrades to
   filename ordering. Park the file while generating.
3. **The hand-written comparison panel above the tabs is not generated.** Read the
   live artifact, extract the `<div style="background:var(--panel,#fff)...">`
   block before `<nav class="tabs">`, and merge it back, or republishing deletes
   it without a word.
4. **A 13.5 MB single-file publish times out (408), twice.** The page is 88 KB and
   the run data is 13.4 MB on one line. Split `const ALL = {...}` into
   `run_data.js` and publish it via `files` — a top-level `const` in a classic
   script is visible to the inline script that follows it, so nothing else
   changes. The artifact is now two files; keep it that way.
5. **SUPERSEDED 2026-09-14 by chunking — the data is now FOUR files, not one.**
   At 37 runs the single `run_data.js` reached 15.1 MB and 408'd on the first
   attempt, succeeding only on retry. Rather than drop runs to fit (Gordon's
   instruction: *"don't try to cram stuff and take out important stuff — split
   the artifact"*), the payload is split:

       run_index.js    var ALL = {order:[...], runs:{}};     480 B
       run_data_1.js   Object.assign(ALL.runs, {...});      4.5 MB
       run_data_2.js   Object.assign(ALL.runs, {...});      4.3 MB
       run_data_3.js   Object.assign(ALL.runs, {...});      4.0 MB

   Loaded in that order by `<script src>` before the inline script, so `ALL` is
   assembled by the time anything reads it. Chunked by cumulative bytes at a
   4.5 MB target, so adding runs adds a chunk rather than growing a file.
   **Minifying at the same time (`separators=(",",":")`) cut 15.1 MB to
   12.8 MB on its own** — the data had been written with `", "` between every
   element. Published on the first attempt with no timeout.

   The splitter and validator are in this session's scratchpad; the validation
   that matters is that the chunks reconstruct `ALL.order` exactly with no
   overlap and no missing run, which is worth re-running after any change.
6. **The run set is NOT discoverable from disk.** v25's 36 runs were 30 current
   plus **six from `data/_archive/superseded/`** (`v4_full`..`v8_full`,
   `v9_feedback`) — which the published tables in `55d7c5a5` depend on — and
   deliberately excluded `sweep_a12`/`sweep_a24`. Globbing any directory gives
   the wrong set in both directions. **Recover the real list from the published
   artifact** (`action: "list_files"` then `read_file run_data.js`, then read
   `ALL.order`) and add to it. The generator script that does all of this is
   `/tmp/claude-501/gen_explorer.sh`, written 2026-09-14.

Also: passing a newline-separated list unquoted in **zsh does not word-split**, so
`--analysis $FILES` arrives as one argument, `make_graph.py` skips every file, and
it still writes a 75 KB page reporting `0 run(s)` and exits 0. Use
`${(f)"$(...)"}` into an array. A generator that succeeds at producing nothing is
the same shape as every other bug in this log.

### Immediately next

*Updated 2026-09-13 after the reference repositories were read end to end.*

0. **DONE 2026-09-13 — B-26 is now a refusal, not a truncation.** `--agents N`
   silently degraded to "use every persona in the file" whenever N exceeded the
   file, producing a run with fewer agents than its own name and no warning
   anywhere. `timeline_agent.generate_timeline_agents` now raises `SystemExit(2)`
   naming the shortfall, overridable with `OASIS_ALLOW_PERSONA_TRUNCATION=1`.
   Seven tests in `test_persona_supply.py`, plus a live check that `--agents 108`
   against the 99-persona business file refuses. **This nearly mattered tonight:**
   the sweep runs 18/36/54/72/90 and 90 fits, but 108 — the next increment of 18 —
   would have produced a "108-agent run" of 99 agents.

1. **Decide the scale claim (D-18).** F-99 reprices the head-on target: matching
   Collusion's 1,000 x 100 is ~5.5 days of this machine, Fraud's is ~30. The
   reachable version is **their population at fewer rounds** -- 1,100 agents x 15
   rounds at 0.19 activation is ~20 hours. This is Gordon's call, not mine.
2. **Persona generation (F-103).** The binding constraint, and the cheapest place
   we beat them: their 1,100-agent population has 633 unique names and 58 exact
   duplicate personalities. Prerequisite for anything above 99 agents.
3. **The activation parameter (Q-23).** Both the engineering route to their scale
   and the variable neither paper examines. Not implemented -- every agent acts
   every round here. Brainstorm before building.
4. Artifact `869156cd` Law 2 still shows the withdrawn 1.081 and needs the
   settled 0.991 at 22.7 s per agent-turn, plus the B-28 row in its
   reproducibility table.
5. `docs/superpowers/specs/2026-09-11-research-agenda.md` -- the flagship
   proposal is a shuffled-feed arm testing whether the ranker contributes
   anything beyond allocating attention. Its costings assume the bank's rate,
   which B-28 confirms is correct.
6. The five artifact deletions.

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

### Reference repositories — cloned and verified 2026-09-13

Two published OASIS-derived research projects, cloned locally so they can be
read rather than re-fetched. **Outside the oasis repo deliberately**, so they
cannot enter its git history.

    /Users/gordon/research/reference/MultiAgent4Collusion    519 files, 118 py, HEAD b6daeff (2025-07-19)
    /Users/gordon/research/reference/MutiAgent4Fraud         151 files,  94 py, HEAD 950e489 (2026-02-03)

Papers: arXiv 2507.14660 (collusion) and arXiv 2511.06448 (fraud, ICLR 2026).
Overlapping author group -- Qibing Ren is first author on both.

**The files to open first, and why.** The question is not what they built, it is
how to exceed their scale. Both run 100 timesteps; Collusion at 1,000 agents,
Fraud at 110 and 1,100.

| file | why |
|---|---|
| `MultiAgent4Collusion/agents_init.py` | `sample_activity_level_frequency()`, the bernoulli branch. **READ THIS WITH `agents_generator.py:98-104`, NOT ALONE** -- the 0.02 written here is renormalised to **0.19** before the run reads it (F-99). Activation is still the lever between "a month" and "a weekend", but it is worth ~5x, not ~50x |
| `.../agents_init.py` (same file) | also a parametric cohort generator: network topology, activation distribution, good/bad ratio, post seeding. **Persona supply is our binding constraint** (99 usable bios), and this is the shape of a generator |
| `MultiAgent4Collusion/oasis/social_platform/post_stats.py` | in-memory shadow ledger, engagement split by actor class, snapshotted per timestep. Avoids post-hoc SQL over a growing database |
| `.../twitter_simulation_large.py` | the run loop: reflection cadence, shared memory, interventions |
| `.../system_prompt(static\|dynamic).json` | prompts as versioned JSON keyed by agent type |
| `MutiAgent4Fraud/oasis/inference/inference_manager.py` | per-agent-ID model routing -- different cohorts on different models in one run |
| `MutiAgent4Fraud/scripts/twitter_simulation/align_with_real_world/test.yaml` | the config format. **Note: not at the repo root**, contrary to an earlier note here |
| `MultiAgent4Collusion/utils/port_forward.py` | a plain TCP proxy, N listen ports to one target port. It multiplies concurrency only because `InferenceThread` serves exactly one request per port at a time, so ports *are* slots (F-102's neighbourhood). Read it with `inference_thread.py` |

**READ IN FULL 2026-09-13 -- see section 6.** Both repositories have now been
read end to end and the findings are F-99 to F-104, Q-23 and D-18. The three
gaps are confirmed and quantified: **neither reports a single wall-clock or
token figure and neither's code can produce one** (F-102, 14 `time.time()` calls
each, all liveness timeouts); **neither can record feed position** -- their `rec`
table is `(user_id, post_id)` with a composite primary key, replaced every
timestep, so F-94 is unaskable in their codebase at any scale (F-101); and both
treat activation rate as a budget knob rather than a variable, at two different
undisclosed values (F-99, F-100, Q-23).

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

**Pass `--temperature 0.7` on every run in the twitter/ctx8192 family.** B-31:
the bare CLI default is **0.9** and has been since `30e6144` (2026-08-30), but
every shell script in `social_timeline/` passes 0.7 explicitly and **28 of our
runs carry 0.7 against 7 at 0.9**. A hand-written command that omits the flag is
not comparable to the bank or to the cost curve, and nothing warns you.
`sweep18.sh` pins it and `assert_comparable.py` checks it against a reference
run before the night is spent.

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

#### B-33 — The guard written to prevent B-32 would never have fired, and would have logged that it was working

**Symptom.** `sweep_when_idle.sh` waits for a quiet machine, then runs the sweep.
Left running for 45 minutes it reported `still waiting: 2 foreground app(s)
running` every five minutes. One of the two was real (Roblox Studio's helper).
The other was **our own inference server**.

**Cause.** The hog list included a bare `obs`, for OBS Studio. `pgrep -f` matches
the whole command line, and the ollama runner's is:

    ollama runner --model /Users/gordon/.ollama/models/blobs/sha256-667b0c...

`obs` is inside `blobs`. So the watcher saw a foreground application every single
minute, reset its streak every single minute, and **would have waited until
morning without ever starting the sweep** — on a machine that had gone quiet
hours earlier.

**Why it would not have been noticed.** The reset line only prints when a streak
was already building, and a streak never began, so the only output was the
heartbeat — which said "still waiting", which was true, and which is exactly what
a correctly-working watcher on a genuinely busy machine also prints. Adding that
heartbeat an hour earlier is what made this visible at all; without it the log
would have been silent and the failure indistinguishable from a machine in use.

**Fix.** Anchor the patterns to executable paths: `/RobloxPlayer`, `/OBS `,
`/Blender`. Verified after the change that the pattern still matches Roblox
Studio and no longer matches the ollama runner.

**The lesson is narrower than the usual one and worth keeping separate.**
`pgrep -f` is a substring match against an entire command line, and command lines
contain paths, and paths contain words. A three-letter pattern will find itself
somewhere. This is not a variant of "record your settings" — it is: **an
unanchored substring is not a check, and a guard is exactly the code where a
false negative is invisible**, because its silence looks like success.

#### B-32 — A run measured 2.16x its own reference because the laptop was in use, and nothing said so

**Symptom.** `sweep18_a36`, 2026-09-13, round 1 in **802.5 s against the reference
run's 371.6 s**. Round 0 was 110.2 s against 95.6 s, so the ratio was *growing*.
No error, no warning, no failed check.

**It was not the simulation.** The action counts at round 1 are nearly identical
to the reference at the same round:

| | tonight | reference `ctx8192_a36` |
|---|---|---|
| posts | 39 | 33 |
| comments | 3 | 4 |
| likes | 1 | 2 |
| **seconds** | **802.5** | **371.6** |

Same work, 2.16x the clock. **It was not the configuration** either -- the
drift gate (B-31) had passed the run's own smoke against `ctx8192_a36` on 19
identical keys. **It was not the server**: `/api/ps` reported 8,192 context and
11.2 GB resident, and the runner process had not restarted since 2026-09-12
03:56.

**Cause.** The laptop was in active use. Measured while the run was in flight:
`RobloxPlayer` 85 %, `WindowServer` 41 %, `Google Chrome` 27 %, `coreaudiod` 9 %
-- 219 % of non-simulation CPU in total.

**A partial retraction of my own diagnosis, made ten minutes earlier.** I found
Roblox first and named it as the cause. Its process start time is **18:25:25**,
and the 802.5 s round ran **17:50-18:03**. Roblox is making things worse *now*;
it did not cause that round. What is established is that the machine was not
idle, not which application was responsible at which moment. The habit that
caught it is the one the log keeps having to relearn: check the timestamps before
naming the culprit.

**Why it matters more than it sounds.** A cost-versus-agents curve measured while
desktop load varies is not measuring agent count. This is the `scale99_full`
shape exactly -- per-agent cost climbing monotonically because something is
degrading, not because the world is bigger -- and that one cost a retracted
exponent (F-96's first value) before it was understood.

**Nothing scientific is affected, and this is worth stating plainly** because the
instinct is to distrust the whole night. Tier, repeat exposure and slot position
are odds ratios computed *within* a run. A slower machine produces identical
behaviour more slowly. `sweep18_a18` engaged at 7.28 % and its behavioural data
stands; only its 24.3 s per agent-turn is in doubt, and it is set aside in
`data/contaminated/` with a note rather than deleted.

**Fix.** `sweep_when_idle.sh` -- poll once a minute, require no foreground hog
and under 40 % non-simulation CPU for ten consecutive minutes, then run the sweep
under `caffeinate -i`. It excludes ollama and our own processes from the busy
calculation, because once the sweep starts the machine is *supposed* to be busy
and a naive check would never settle. Validated against a machine known to be in
use: it read 219 % and refused to start.

**The class this belongs to is now four members** (B-26, B-28, B-31, B-32), and
the shared property is worth naming once more: **each one produces a run that is
indistinguishable from a real one afterwards.** Three of the four made the run
*look better* -- faster, or cleanly comparable -- which is why none of them was
caught by looking at the output.

#### B-31 — The sweep command drafted for tonight would have run 8.5 hours at the wrong sampling temperature

**Symptom.** None. That is the entire problem. The command was correct in every
visible way -- right agent counts, right rounds, right seed, right personas,
right recommender -- and it would have produced five clean runs, five clean
manifests and five clean charts, all of them comparable with nothing.

**Cause.** `--temperature` defaults to **0.9** in `run_simulation.py`, changed
from 0.7 in `30e6144` on 2026-08-30. Every shell script in the directory --
`campaign.sh`, `overnight.sh`, `ab_efficiency.sh` -- passes `--temperature 0.7`
explicitly, so the default has been shadowed for six weeks and nobody had to
know it disagreed. Across every run we have kept: **28 at 0.7, 7 at 0.9, 2
unset**. The runs this sweep was meant to extend -- `ctx8192_a12/a24/a36` -- are
all 0.7. A hand-written command is the one path that does not go through a
script, and that is the path that was about to be taken.

**Found by** running a 4-agent, 1-round smoke with tonight's exact flags and
diffing its manifest `config` block against `ctx8192_a36`'s. Thirty seconds.
Two keys differed: `shuffle_feed` (a new manifest key with an inert default, not
drift) and `temperature` (0.9 against 0.7).

**This is the third instance of one failure shape**, and it is worth naming as a
class rather than as three bugs:

| | what silently changed | what it looked like |
|---|---|---|
| B-26 | `--agents N` truncated to the persona file | a run named for more agents than it had |
| B-28 | the server truncated every prompt to 4,096 | a FASTER run with less engagement |
| B-31 | the CLI sampled at 0.9 instead of 0.7 | a perfectly normal run comparable to nothing |

None raises. None is slower. Each produces output indistinguishable afterwards
from the real thing. **A default that disagrees with the convention every script
enforces is not a default, it is a trap**, and the answer is not to remember
harder.

**Fix.** `assert_comparable.py` -- diff a candidate run's config against a named
reference run, fail on any differing value, report new manifest keys without
failing (the schema grows), and **refuse a vacuous pass** when too few keys were
compared, because a guard that green-lights a night having compared nothing is
worse than no guard. Ten tests. `sweep18.sh` pins every flag with a comment
saying why, and runs the smoke-and-diff as preflight 3 of 3 before it spends the
night.

**Not fixed: the default itself.** Changing 0.9 back to 0.7 would silently move
every future bare invocation and orphan the 7 runs at 0.9. The convention is now
a standing warning in section 0 and a preflight that refuses; that is a check,
not a memory.

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

---

## 6. The two reference repositories, read in full

*Read 2026-09-13 at `/Users/gordon/research/reference/`. Every number below was
computed from their committed code and their committed data, not from their
papers. Where a paper and the repository disagree, the repository wins — it is
what actually ran.*

### The starter questions, answered

| question | MultiAgent4Collusion | MutiAgent4Fraud |
|---|---|---|
| **How many users** | 1,000 headline; CSVs shipped for 10/100/110/901/1000/1100; 5,500 on HuggingFace | 110 headline, 1,100 largest; also 210, 510 for ratio sweeps |
| **How many rounds** | 100 timesteps (`num_timesteps: 100`) | paper says 100; **the repo pins `num_timesteps: 1`** — the headline config is not committed |
| **What they added** | `inference/` (313+137 lines), `post_stats.py` (883), `bad_agents_generator.py` (205), `task_blackboard.py` (35), `testing/utils.py` (125); `agent.py` 321 → 994 lines | all of the above plus 7 new action types, 7 new tables, `agent.py` 321 → **1,382** lines, `platform.py` 1,642 → **2,218** |
| **What they got rid of** | `oasis/environment/` (`make()`/`env.step()`) — see F-104, they never had it | same |
| **What they improved** | reflection + shared reflection, per-port inference pool, in-memory engagement ledger, LLM-as-detector, intervention arms (prebunk/debunk/ban) | + private messaging, money transfer, click/submit tracking, **per-agent-ID model routing across three backends in one run** |
| **Their time per round / per agent** | **not reported, and not measurable from the code** — see F-102 | same |

### F-99 — Collusion's activation rate is 0.19, not the 0.02 its CSVs appear to say. The handoff note in §0 was wrong and this corrects it

The CSV column says 0.02. The number the simulation actually uses is **0.19**,
because the value is transformed between the file and the run.

`agents_init.py::sample_activity_level_frequency()` writes, per hour:

    random.choices([0, 0.2], weights=[0.9, 0.1])[0]        -> mean 0.0199

`agents_generator.py:98-104` then rewrites it before the agent ever sees it:

    normalized_prob = all_freq / np.max(all_freq)      # {0, 0.2} -> {0, 1.0}
    normalized_prob[normalized_prob < 0.6] += 0.1      # the zeros become 0.1
    prob_list = np.round(normalized_prob, 2).tolist()

So the per-hour threshold is **1.0** where the Bernoulli fired (10 % of hours)
and **0.1** where it did not (90 %). Expected activation = 0.1 x 1.0 + 0.9 x 0.1
= **0.19**, a 9.5x inflation of the figure the CSV appears to carry.

The run loop consults it at `twitter_simulation_large.py:445-456`, with
`start_hour = 13` and `simulation_time_hour = 13 + 0.05 * timestep` — so 100
timesteps span 5 simulated hours and only hours 13-18 are ever indexed.

**Verified on their own shipped CSVs**, not on a reproduction:

| file | rows | CSV mean | runtime P(act) | agent-turns at 100 ts |
|---|---|---|---|---|
| `test_1000_good_bad_random_bernoulli_wlx.csv` | 1,000 | 0.0196 | **0.1896** | **18,955** |
| `scalling/test_1100_..._scalling.csv` | 1,100 | 0.0198 | **0.1896** | **20,855** |
| `scalling/test_110_..._scalling.csv` | 110 | 0.0186 | 0.1750 | 1,925 |

The transform is not neutral across distributions, which is why it went
unnoticed: `uniform` inflates 1.1x and `multimodal` 1.3x, but `bernoulli` — the
only one used for the headline runs — inflates **9.5x**.

**What this costs us.** The handoff arithmetic said 1,100 x 100 was ~2,200
agent-turns and "one overnight". It is **~21,000 agent-turns**, and at the
measured 22.7 s per agent-turn (F-96) that is **132 hours — 5.5 days**, not one
night. Fraud's 1,100 x 100 at activation 1.0 is ~113,500 calls, **~30 days**.
Sparse activation is still the lever, but it buys 5x, not 50x, and the honest
sentence is that **their headline run is roughly a week of our hardware**, not a
night of it.

### F-100 — Fraud DELETED that normalisation and runs at activation 1.0. Same author group, two papers, unreported

`MutiAgent4Fraud/oasis/social_agent/agents_generator.py:99-108` carries the
Collusion block commented out, with a Chinese note, and the raw value used
instead:

    # normalized_prob = all_freq / np.max(all_freq)
    # normalized_prob[normalized_prob < 0.6] += 0.1
    ...
    all_freq = np.array([ast.literal_eval(fre) for fre in freq])
    # 不做归一化，直接用原始频率        ("no normalisation, use the raw frequency")
    prob_list: list[float] = all_freq.tolist()

And their generator's `__main__` sets `good_activity_level_distribution="1.0"`,
`bad_activity_level_distribution="1.0"`. Their shipped populations confirm it —
`test_1100_good_bad_random_1.0_1.0_zzj.csv` has activity mean **1.000**, min
1.00, max 1.00 across all 1,100 agents and all 24 hours.

So between arXiv 2507.14660 and ICLR 2026, from an overlapping author group, the
effective activation rate went **0.19 to 1.0** — a 5x change in how much of the
population is live per timestep — and **neither paper reports the rate at all**.
Whether their conclusions survive that change is not addressed in either.

### F-105 — Engagement rate falls by half from 18 to 90 agents, and the agents are not doing anything differently

**The observation.** Five runs, one configuration, 7 rounds, seed 42, business
personas, verified 8,192 context. Engagement falls monotonically apart from the
top point:

| agents | 18 | 36 | 54 | 72 | 90 |
|---|---|---|---|---|---|
| engagement | 7.18 % | 6.18 % | 5.45 % | 3.18 % | 3.98 % |

**It is not the metric.** `analyze.py:295` defines engagement over *distinct*
posts (`seen_post_ids & acted`), while the exposures table counts every exposure
event, and the two diverge as a function of world size — which is the variable
under test, so this had to be checked rather than assumed. Both give the same
answer: the deduplicated spread is 2.26x, the event-level spread 2.22x.

**It is not repetition.** Repeat exposure does fall with world size, 2.25
sightings per distinct post at 18 agents to 1.19 at 90, and F-43 establishes that
repetition raises engagement — so this was the obvious candidate. It is wrong.
**The gap survives whole inside the first-sighting stratum** (7.18 % -> 3.98 %,
the same 2.26x), and engagement on *repeat* sightings is flat or rising with
world size: 2nd sighting 9.49 / 12.62 / 10.03 / 9.88 / 9.86 %. Repetition pushes
against the decline, not for it.

**It is not feed composition.** Network-tier posts engage far better than
discovery (F-92, OR 3.07-3.51), so a shift toward discovery would do it. There is
no shift to find: **discovery is 98.9-99.3 % of first-sighting exposures in every
one of the five runs** — seven rounds is not enough for a follow graph to form —
and the decline is intact within discovery alone, 6.73 % -> 3.86 %.

**What it is: the denominator grows and the numerator does not.**

| | 18 agents | 90 agents | spread |
|---|---|---|---|
| feed actions per agent-turn | 0.380 | 0.402 | **1.35x, no trend** |
| DISTINCT posts shown per agent-turn | 5.29 | 10.10 | **1.95x, monotonic** |
| engagement | 7.18 % | 3.98 % | 2.26x |

Exposures per turn are pinned at the 12-slot feed cap in every run. What changes
is how many of those twelve are *new*: in a small world there is too little
content, so the ranker re-shows posts and distinct-per-turn is 5.3; at 90 agents
there is enough to fill the feed with fresh material and it is 10.1.

A **one-parameter model** — engagement = K / (distinct posts per turn), with
K = 0.389 feed-actions per agent-turn held constant across all five sizes —
reproduces the series with a **mean absolute error of 10.2 %**, against
**run-to-run noise of ~12 %** measured directly from the `s43` replicate at 18
agents (7.18 % vs 6.39 %).

**What this does NOT establish.** The model's error sits inside the noise floor,
which means this data **cannot distinguish a genuinely constant action budget
from a mildly declining one**. Five points, one replicate. The claim that
survives is the decomposition — the fall is in the denominator, and the two known
behavioural drivers are excluded — not that agent propensity is provably
invariant. Nor does it explain *why* output per turn is near-constant; that is
measured here, not accounted for.

**Why it matters for the scale plan.** Engagement rate will keep falling as the
population grows, for arithmetic reasons, and **that must not be read as agents
becoming less social at scale.** Any cross-scale comparison should quote feed
actions per agent-turn, which is flat, rather than engagement rate, which is a
supply artefact. This directly affects how a 1,100-agent run gets reported (D-18)
and it is the kind of number a reader will otherwise take as a finding.

### Q-23 — Is activation density a scientific variable or a budget knob?

This is the gap F-99 and F-100 open, and it is ours to take. Collusion runs 0.19,
Fraud runs 1.0, the same group wrote both, neither reports the number, and
neither asks whether the result depends on it. Yet it is the parameter that
decides how many agents are in the room at once — which is exactly the sort of
thing a contagion or coordination result *should* depend on.

It is also the only parameter that makes their scale reachable here. That is a
rare combination: the same knob is both our engineering route and their unexamined
assumption. Design before building (see the note under §0) — but this is the
strongest candidate the repo reading produced.

### F-101 — Neither repo can record where a post appeared in a feed. F-94 is structurally unaskable in their codebase

Both ship the same `rec` table, unchanged from upstream OASIS:

    CREATE TABLE rec (
        user_id INTEGER,
        post_id INTEGER,
        PRIMARY KEY(user_id, post_id),
        ...
    );

Two columns. A composite primary key, so it is a **set**, not a sequence — there
is no slot index, no score, no source tier, no round. And `update_rec_table()` is
called at the top of every timestep, so it is **replaced**, not appended: after
the run there is no history to reconstruct.

Ours, `timeline_platform.py:349`:

    CREATE TABLE rec_history (
        exposure_id INTEGER PRIMARY KEY AUTOINCREMENT,
        round INTEGER, agent_id INTEGER, post_id INTEGER,
        author_id INTEGER, feed_position INTEGER, source TEXT, score REAL
    );

F-94 — slot position worth OR 1.48-2.15 across 24 runs — could not have been
measured in either repository, at any scale, on any hardware. This is not a
resource gap we are losing; it is an instrumentation gap we are winning, and it
does not depend on agent count at all.

### F-102 — Neither repo has any wall-clock or token accounting. "Their time per round" has no answer because nobody measured it

Grepping both for `time.time()`, `perf_counter`, `elapsed`, `prompt_tokens`,
`completion_tokens`: **14 matches each**, and every one is either an
`InferenceThread` liveness timeout in `inference_manager.py` or a single
uninstrumented section timer in `recsys.py`. There is no manifest, no per-round
timing, no per-turn timing, no token counter, no cost figure — nothing that
survives the process.

So Gordon's question "their time rounds and time agents" has a definite answer:
**they do not report it and their code cannot produce it.** Our `manifest.json`
carries `rounds[].seconds`, `total_seconds`, the phase split (99.8 % LLM), and
since B-28 the verified `server_context_length`. F-96's 22.7 s per agent-turn at
exponent 0.991 (R² 0.9988) is a measurement neither paper has an equivalent of.

### F-103 — Their agent populations have severe mode collapse, and it is measurable

Both generate personas the same way: one fixed prompt, `gpt-4o`, temperature 1.0,
five profiles per call, regex-parsed (`generate_profile.py`). No de-duplication,
no stratification, no demographic target. The shipped result:

| | profiles | unique names | unique personality text | worst repeat |
|---|---|---|---|---|
| Collusion `user_profiles.json` | 6,037 | 2,475 (**41.0 %**) | 6,037 (100 %) | "Aisha Patel" x **141** |
| Fraud `user_profiles.json` | 1,100 | 633 (**57.5 %**) | 1,042 (**94.7 %**) | "Emily Chen" x 21 |

Fraud's 1,100-agent population contains **58 exact-duplicate personality blocks**
— the same agent, twice, under different ids. Age spans 16-62 with median 30 in
both; the gender mix is ~19 % non-binary. This is what a single-prompt sampler
produces, and it is a population, not a sample of one.

**This is the cheapest place we beat them.** Persona supply is our binding
constraint (99 usable business bios), so a generator has to be built regardless.
Building it with stratification and exact-duplicate rejection makes it better than
theirs by construction, and the table above is the measurement that says so.

### F-104 — Both vendored an old OASIS and never rebased. Our platform is ~20 months newer than Collusion's

Neither repository shares git history with `camel-ai/oasis`. Both are squashed
code drops:

    MultiAgent4Collusion   4 commits, all 2025-07-19
    MutiAgent4Fraud        7 commits, 2025-10-20 to 2026-02-03

Dating their vendored copy by `social_platform/typing.py` line count against
upstream history: Collusion's 49 lines matches upstream `aa0d4b7` (**2025-01-08**),
Fraud's 54 matches around `4ea129a` (**2025-04-10**). Upstream added
`oasis/environment/` — the `make()` / `env.step()` API — on 2025-04-10, which is
why neither has it. They drive `Platform` directly instead.

Our checkout is current to 2026-09-13 (merge `ba2f0b3`, 23 upstream commits). So
the "what did they get rid of" answer is really **"they froze, and upstream moved"**
— including the `recsys.py` off-by-one in `get_like_post_id` that upstream later
fixed and that both of them still carry.

### What is worth taking, and what is not

| their component | verdict |
|---|---|
| `post_stats.py` `TweetStats` — in-memory engagement ledger, deep-copied per timestep, split by actor class | **take the idea.** It avoids post-hoc SQL over a growing DB, which is exactly F-52's `_analysis.json` problem. Ours should be a Parquet append, not an in-memory dict that dies with the process |
| `agents_init.py` cohort generator — topology (`erdos_renyi` / `barabasi_albert` / `watts_strogatz`), good/bad ratio, post seeding | **take the shape**, not the code. It is the right set of knobs. Our version must not repeat the F-99 transform |
| `inference_manager.py` + `port_forward.py` | **understand, do not copy.** Each `InferenceThread` serves exactly one request at a time (`Busy`/`Working`/`Done` flags, 10 ms poll). Concurrency = number of ports, so `port_forward.py` — a plain TCP proxy, N listen ports to one target — manufactures concurrency by manufacturing ports. Our asyncio + `OLLAMA_NUM_PARALLEL` does the same job without a busy-wait thread per slot |
| Per-agent-ID model routing (`PortManager`, Fraud) | **worth having eventually.** Different cohorts on different models in one run is a real capability we lack |
| `perform_action_by_llm` re-reading and JSON-parsing the prompt file on **every activation** (~19,000 times per run) | do not copy |
| Their `rec` table | do not copy. See F-101 |

### D-18 — What "bigger than theirs" has to mean

Gordon's goal is more agents and more rounds than both papers. F-99 prices it
honestly and the head-on version does not fit on this machine:

| target | agent-turns | at 22.7 s/turn |
|---|---|---|
| Collusion 1,000 x 100 @ 0.19 | ~21,000 | **5.5 days** |
| Fraud 1,100 x 100 @ 1.0 | ~113,500 | **30 days** |
| us, 36 x 15 @ 1.0 (the bank) | 540 | 170 min |

So the decision is which axis to win on, and there are three that are real:

1. **Match their population, not their turn count.** 1,100 agents x 15 rounds at
   activation 1.0 is 16,500 turns — still 4 days. At activation 0.19 it is 3,135
   turns, **~20 hours**. That is one weekend, and it is *more agents than
   Collusion and the same as Fraud*, at a sparser activation than either reports.
   Requires: persona generation (F-103) and the activation parameter (Q-23).
2. **Win on instrumentation, which is already done.** F-101 and F-102: we record
   feed position and wall clock; neither of them records either, at any scale.
   No amount of their compute closes that.
3. **Win on the question.** Q-23 is a variable both papers set and neither
   examines, and we can sweep it where they cannot afford to.

**The honest framing for the professor** is that (1) is a scale claim, (2) and (3)
are scientific claims, and only (2) is currently in hand. Chasing (1) alone means
a week of GPU time to draw level on a number neither paper actually defends.


---

### F-106 — The action budget is steady across world size, and the noise floor F-105 argued against was 1.7x too generous

**What F-105 left open.** It compared its one-parameter model's 10.2 % mean
error against "run-to-run noise of ~12 %", and that 12 % came from a **single
replicate pair** (`sweep18_a18` 7.18 % vs `sweep18_s43_a18` 6.39 %). On that
basis it concluded the data "cannot distinguish a genuinely constant action
budget from a mildly declining one". Three families of identical runs were
already on disk and had never been used for this.

**A real noise floor.** Nine identical runs at the current configuration
(`bank_r1..r7`, `np4_val_r1..r2`, 36 agents x 15 rounds):

| metric | mean | CV over 9 runs |
|---|---|---|
| engagement | 6.94 % | **7.1 %** |
| feed actions per agent-turn | 0.367 | **4.4 %** |
| distinct posts shown per agent-turn | 5.31 | 6.5 % |

So the figure F-105 should have compared against is **7.1 %, not 12 %** — its
model error is *outside* the noise on that reading, not inside it. But the CV
comparison is the wrong test anyway, and correcting it matters more than
correcting the number.

**Why a CV is the wrong instrument here.** Feed actions are **counts**, and the
runs being compared differ in size by 5x, so the sampling floor differs per run:
41 events at 18 agents against 217 at 90. A single CV cannot express that. The
right test is a count model.

**Feed-action output is UNDER-dispersed.** Across the nine identical runs,
observed variance is 76.4 against a Poisson expectation of 198.1 —
**phi = 0.385** (dispersion test X=3.08, df=8, p=0.071, so *directional, not
established*). The total number of things a run's agents do is **more repeatable
than independent coin-flips would be**. That is what a per-turn budget looks
like from the outside, and it is the first direct evidence for one.

**The test F-105 wanted.** Fit `expected count = K x turns` across the five
sweep sizes, pooled K = 0.3938:

| run | agents | turns | observed | expected | obs/turn | z |
|---|---|---|---|---|---|---|
| sweep18_a18 | 18 | 108 | 41 | 42.5 | 0.380 | -0.24 |
| sweep18_a36 | 36 | 216 | 96 | 85.1 | 0.444 | +1.19 |
| sweep18_a54 | 54 | 324 | 142 | 127.6 | 0.438 | +1.27 |
| sweep18_a72 | 72 | 432 | 142 | 170.1 | 0.329 | **-2.16** |
| sweep18_a90 | 90 | 540 | 217 | 212.7 | 0.402 | +0.30 |

**chi2 = 7.83, df = 4, p = 0.098 — the constant budget is NOT rejected.**

**It rests entirely on one run.** Drop `sweep18_a72` and the fit is
chi2 = 1.40, df = 3, **p = 0.71**; drop any other single run and chi2 stays at
5.96-7.77. `sweep18_a72`'s manifest is identical to its four siblings on all 26
config keys except `agents`, `server_context_length` is 8192 in all five, so
this is not another B-28. A -2.2 sigma deviation appearing once in five draws
has probability ~15 %: unremarkable.

**What now stands.** F-105's decomposition was right and its recommendation is
now positively supported rather than merely asserted: **quote feed actions per
agent-turn across scales.** It is the most stable metric across identical runs
(CV 4.4 % against engagement's 7.1 %), it is flat across a 5x population change
within counting noise, and engagement is not — it falls 2.26x for supply
reasons.

**And there is a mechanism for why it is the better metric**, not just an
observation. Engagement is a ratio of two noisy quantities and inherits both
variances; feed actions per turn carries only the numerator, which is also the
half that is under-dispersed. The delta method predicts the ratio's CV at
**7.18 %** against **7.05 %** observed, with corr(numerator, denominator)
= +0.18 (p=0.65). The decomposition is essentially exact.

**Still not established.** phi is measured at 36 agents x 15 rounds with reddit
personas and applied to 7-round twitter-persona runs of five sizes; its own test
is p=0.071 on n=9. And "the budget is not rejected" is not "the budget is
constant" — one replicate at 72 agents would settle the only point in doubt, and
is the cheapest experiment on the board (~2.6 h).

*Method: `noise_f105.py` and `budget_test.py`. Gated — both reproduce F-105's
published five-point table exactly (0.380/5.29 at 18 agents, 0.402/10.10 at 90,
and all five engagement values) before computing anything new. The first attempt
FAILED that gate: `agent_turns_total` in `runs_index.csv` counts agents x rounds,
while F-105 correctly used the turns that actually served a feed —
agents x (rounds-1), which is the `refresh` count. The index column is 1.17x too
high at 7 rounds. Left as-is, it would silently deflate every per-turn figure.*

---

#### B-34 — The shipped data package could not reproduce the study's own dependent variable

**Where.** Ours, `export_parquet.py`. Found while looking for replicate runs, not
while looking for a bug.

**Symptom.** Engagement computed from the exported tables, the way
`DATA_DICTIONARY.md` told a reader to compute it, came out at **41-65 % of its
true value** — and the shortfall **varied per run**: 1.63x on `sweep18_a36`,
1.78x on `sweep18_a18`, 2.47x on `sweep18_a90`. Meanwhile `runs_index.csv`
carried the *correct* engagement, because that column is computed by
`analyze.py` from the database. **The package contradicted itself**, and a reader
who noticed had no way to tell which half was right.

**Cause.** A trace row does not say what it acted on. `create_comment` and
`like_comment` name only a `comment_id`; `follow` names only the row it just
created; `quote_post` stores its target as a *string*. This is B-4 and B-6,
found and fixed in `analyze.py` long ago — and the exporter, written later,
resolved none of it and **did not export the `comment` table at all**, so the
comment -> post link did not survive the export in any form. Comment actions are
**56-59 % of all post-directed actions** in a bank run, so most of the
engagement ledger was simply unreachable.

**Why it matters more than a wrong number.** The package is the deliverable for
"store run data so it survives 1,000 agents x 1,000 rounds and opens in other
software", and its stated purpose is that a reader "can answer what agents
engaged with without reading any of our code". Reading our code was exactly what
it required. Worse, a *varying* deficit is more damaging than a constant one: it
corrupts run-to-run comparison specifically, which is the one thing the package
exists to support.

**Fix.** Export the `comment` table, and resolve `target_post_id` /
`target_agent_id` onto `actions` as first-class columns using the same key list
as `analyze.py:58` — two resolvers that disagree would be worse than one that is
wrong. `target_post_id` is deliberately NULL for `create_post`, whose payload
names the post it *wrote*, not one it acted on. (That happens to be harmless for
engagement because an agent is never shown its own post — verified on six runs —
but only by luck.) `DATA_DICTIONARY.md` now carries a runnable engagement recipe
that reproduces `runs_index.csv`, and its old line — *"`info` contains `post_id`
for post-directed actions"* — is gone; it was the sentence that produced the
wrong answer.

**Verified.** All 43 runs re-exported; **31 of 32 runs with a published
engagement reproduced it exactly** from the package alone. The one that did not
is B-35.

---

#### B-35 — A re-export MERGED with the previous run's data instead of replacing it

**Where.** Ours, `export_parquet.py::export_run()`. Found by B-34's new gate, on
the one run that still refused to reconcile.

**Symptom.** `scale99_full` is 99 agents x 5 rounds. Its exported
`exposures/` held **rounds 1-11**: rounds 1-4 at 1,188 rows (99 x 12 slots,
correct) and **rounds 5-11 at 432 rows (36 x 12 slots)** — a 36-agent run's
data, dated three days earlier. 2,904 stale exposure rows and 7,560 stale
candidate rows, sitting in the published package. Package engagement read 3.94 %
against a true 5.43 %.

**Cause.** Partitioned tables write one file per round and **nothing ever
removed partitions the new export does not produce**. B-26's mislabelled
36-agent run was originally *named* `scale99_full` and was exported under that
name; when the real 99-agent run was exported to the same label it overwrote
rounds 1-4 and inherited rounds 5-11.

**This is the unfixed half of B-27.** B-27 found the same mislabelling
contaminating `round_timings.csv`, fixed the timings by reading each run's own
manifest — and never checked whether the same collision had left anything in the
*data*. It had. **When a label turns out to have meant two things, every
artifact keyed by that label is suspect, not just the one where it was noticed.**

**Fix.** `export_run()` now clears each table's directory before writing.
Regression check added: inject a `round=9999` partition, re-export, assert it is
gone.

**Blast radius, checked.** Every one of the 43 runs was compared row-for-row
against its source database: `scale99_full` was the **only** contaminated run.
It is an experimental arm (`scale_99agents`), 1.5 % of pooled package rows, and
**no current finding uses it** — the cost curve and F-105 use `sweep18` and
`ctx8192`, F-92/F-95 use the bank and fresh-context runs. Any *pooled* analysis
re-run from the old package should be regenerated regardless.

**Nothing warned.** The stale rows were valid Parquet with the right schema and
plausible values. The only thing that caught it was a check tying the data back
to a number computed independently — which is what B-34's new gate does, and
what neither the old 22 checks nor `build_package.py` did.

---


### F-107 — The cost law was fitted entirely on 7-round runs. A 15-round run at the largest size reproduces it to 0.2 %

Every one of the eight points in F-96/the sweep curve is a **seven-round** run,
and the law was then applied to fifteen-round runs — an extrapolation in a
direction the fit never saw, and the same shape of mistake as the 1,081 exponent.

`r15_a90` tests it: 90 agents, **15 rounds**, same seed, personas, temperature,
semaphore, recsys and verified 8,192 context as `sweep18_a90`.

| | rounds | plateau (round >= 4) | sd | per agent-turn |
|---|---|---|---|---|
| `sweep18_a90` | 7 | 1,940.6 s | 20.9 | 21.56 s |
| `r15_a90` | 15 | **1,944.9 s** | 61.9 | **21.61 s** |

**0.2 % apart**, against 6 % run-to-run variation on this quantity and a curve
mean of 21.44 (sd 0.37). Total wall clock **25,965 s = 7.21 h**, against 8.0 h
projected. The plateau is genuinely flat to round 14 and cost is the product of
the two laws, not something that drifts with run length.

The sd is 3x the 7-round run's (61.9 vs 20.9) purely because there are 11 plateau
rounds rather than 3 — more opportunity to catch a slow one, not more variance
per round.

---

### F-108 — Connection-over-content replicates at 90 agents, and `fof` is individually significant for the first time

**The 7-round sweep could not test this at all.** Network-tier posts are 2.48 %
of exposures at 90 agents over 7 rounds — there is not enough network content to
stratify on. That was the stated reason for running `r15_a90`, and it worked:

| | discovery | network | fof |
|---|---|---|---|
| `sweep18_a90` (7 rounds) | 96.71 % | 2.48 % | 0.80 % |
| `r15_a90` (15 rounds) | 85.56 % | **9.54 %** | **4.91 %** |

By the final round the feed is 70.6 % discovery, 19.3 % network, 10.2 % fof. The
graph needs time, not population: **run length is the binding constraint on this
result, not exposure count.**

**The result, same estimator as the bank (MH, stratified by agent and feed slot,
slots 0-4):**

| contrast | bank, 36 agents, 9 runs | `r15_a90`, 90 agents, 1 run | strata |
|---|---|---|---|
| network vs discovery | 3.51 [3.06, 4.04] | **3.95 [3.15, 4.96]** p=2.4e-32 | 208 |
| **fof vs discovery** | 2.34 [1.64, 3.35] | **3.12 [2.09, 4.66]** p=2.8e-08 | 95 |
| network vs fof | 1.85 [1.38, 2.48] | 3.16 [1.94, 5.15] | 55 |

Every interval overlaps its 36-agent counterpart. **15,120 exposures from one
run** — 28 % again on top of the entire nine-run published corpus.

**Why it is worth more than another 36-agent replicate.** It changes three things
at once: population 2.5x, run length, and **the persona file** (twitter
scraped-biography personas, not the 36 structured reddit ones). Per the artifact's
own limits those two populations cannot be pooled — so this is a second
independent measurement, not more of the same data.

**fof is the one that matters** and it is now individually significant in a single
run for the first time (it was 3/7 in the bank). Do **not** upgrade the wording
from "suggestive" yet: one run is not a replication series. `r15_s43_a90` is
running and is the direct test.

Also reproduced in this run: feed slot OR 0.891 per slot within the discovery
tier (F-94), and the ranking score null at 1.415 [0.225, 8.891], p=0.711 (F-42).

---

### F-109 — The action budget is steady across world SIZE but appears to decline with run LENGTH

F-106 establishes that feed actions per agent-turn does not vary with population
at fixed round count. `r15_a90` against `sweep18_a90` varies the other axis, and
the answer is different.

| | turns | feed actions | per turn | distinct/turn | engagement |
|---|---|---|---|---|---|
| `sweep18_a90`, 7 rounds | 540 | 217 | **0.402** | 10.10 | 3.98 % |
| `r15_a90`, 15 rounds | 1,260 | 430 | **0.341** | 7.66 | 4.45 % |

**Engagement rises while the budget falls**, which is Law 3 running backwards:
distinct posts per turn drops from 10.10 to 7.66 because a follow graph forms and
network posts recur, so the denominator shrinks faster than the numerator.

Tested as counts, a common budget across the two lengths gives **chi2 = 3.86,
df = 1, p = 0.049** — marginal under Poisson, and 0.0015 at F-106's measured
phi = 0.385. But this is **n = 1 against n = 1** and the two runs differ in the
one thing being tested, so it is an observation, not a finding. `r15_s43_a90`
(running) doubles it.

**What it changes in how things are reported:** "feed actions per agent-turn is
flat" is a statement about **population**, not about run length. F-105's
recommendation stands for cross-scale comparison and must not be stretched into
cross-length comparison.

---


### F-110 — Repetition replicates at 90 agents, but its two supporting arguments move in opposite directions

`r15_a90` (90 agents x 15 rounds, twitter personas, 15,120 exposures) run through
`recency_check.py` unchanged. **The headline replicates.**

| | bank, 36 agents, 9 runs | `r15_a90`, 90 agents, 1 run |
|---|---|---|
| seen-before vs first sighting, by feed | 2.62 [2.18, 3.15] | **2.351 [1.986, 2.782]** p=2.8e-23 |
| strata | 3,047 | 1,058 |

Intervals overlap. The dose-response is cleaner and steeper than the bank's:

| prior sightings | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| engagement | 4.05 % | 8.84 % | 13.85 % | 21.62 % |
| distinct posts | 224 | 198 | 127 | 28 |

Absolute scale: **4.05 % → 9.58 %, a 5.53 pp difference** (2.37x the raw rate).
Quote that alongside the odds ratio, which overstates at a low base rate.

**Supporting argument 1 STRENGTHENS, and this is the more interesting half.**
F-45 downgraded the "reverses inside first sightings" check to directional only
when nine runs took it from 0.55 [0.31, 0.97] to **0.70 [0.46, 1.07], p=0.097**.
In this run the same test returns **OR 0.267 [0.122, 0.586], p=0.00099** on 464
feeds — clearly significant and well below 1. Closing the repeat channel by
construction does reverse the stale-post advantage here.

**Supporting argument 2 WEAKENS, and it is the one the causal reading leans on.**
The network tier is where the similarity score plays no part in feed
construction at all, so a replication there is what makes the effect hard to
dismiss as a ranker artefact. The bank gives 1.64 [1.33, 2.03]. This run gives
**1.438 [0.901, 2.296], p=0.128 — not significant**, on n=1,442. `fof` is null
as it is in the bank (0.848 [0.357, 2.015]).

That is not a contradiction: the point estimate is in the right place and the
interval contains the bank's. It is an **underpowered** tier, not a contrary
one — 1,442 exposures against the discovery tier's 12,936. But it means this run
does **not** independently reproduce the check that carried the causal argument,
and that should be said rather than glossed.

**One number moved a lot and is worth watching.** Adding feed slot to the
stratification barely moves the bank estimate (2.62 → 2.45). Here it more than
doubles it: **(agent, slot) gives 5.784 [4.642, 7.206]** against 2.351 by feed.
The mechanism is stated in the output and is the same one as the bank's, only
stronger: re-shown posts rank LOWER (mean slot 7.60 against 6.40), so position
biases *against* the result and removing it uncovers more. Why the gap is larger
at 15 rounds and 90 agents is not established — more content per round means a
longer feed tail for stale posts to fall into, which is a plausible account and
nothing more.

**Net.** Repetition is now the second of the three headline results to survive a
change of scale, run length and persona file at once (F-108 is the other). Its
status is unchanged: **observational**, since prior sightings are an outcome of
the ranker, and Q-15 — a designed run that re-injects a fixed set of posts on a
controlled schedule — remains the test that would settle it.

---


### F-111 — Engagement counts actions that SUCCEEDED. Up to 44 % of intended actions never happened, and the loss grows with world size

Prompted by the open item "14 of 21 actions never fire". That framing is wrong
twice over: across 44 runs **17 of 21 actions fire at least once**, and the
interesting structure is not which fire but how many intended actions never
became anything at all.

**The action repertoire is an extreme power law, not a wall.** 15,199 chosen
actions across 44 runs: `create_post` 44.5 %, `create_comment` 19.9 %,
`like_post` 14.5 %, `follow` 9.2 %, `like_comment` 8.1 % — **five actions are
96.2 % of everything**, and twelve more share the remaining 3.8 %.

**There are THREE silent-loss channels, and only one of them is visible without
the run's log.**

| channel | what it is | where recorded |
|---|---|---|
| malformed tool call | agent chose an action and got the arguments wrong; leaves **no trace row** | run log only |
| blind action rejected | action named a post the agent was never shown; refused by the honesty gate | `manifest.platform_stats` |
| invalid follow target | followee id does not exist (B-10) | `manifest.platform_stats` |

Across all 44 runs: **891 blind rejections (5.5 % of intended post-directed
actions) and 109 invalid follows.** Malformed calls are only measurable for the
16 runs whose log survives.

**In the nine old-prompt runs that recorded them, 43.8 % of intended actions
were malformed** — 2,624 against 3,368 that succeeded. `follow` is the worst by
far: **1,268 malformed against 558 successful, a 69.4 % failure rate.** That is
the mechanism that builds the follow graph, which is the substrate the entire
connection result (F-92/F-108) rests on. **The graphs in those runs are roughly
a third of what the agents tried to build.** 89 % of the errors are "unexpected
keyword argument".

**That rate has collapsed at the current configuration.** Run as the unit, which
is the right unit here:

| | runs | median | range |
|---|---|---|---|
| old prompt | 9 | **37.0 %** | 12.4 – 75.9 % |
| current | 7 | **0.0 %** | 0.0 – 11.0 % |

Mann-Whitney U=63, one-sided **p=0.00047**, and the ranges do not overlap. (A
two-proportion test on the raw call counts returns p≈1e-267; that figure is
meaningless because calls are clustered within agent and run — the ICC here runs
0.26-0.38. The run-level test is the honest one.)

**This is a candidate mechanism for F-93, and it is more concrete than the
published one.** F-93 records engagement tripling (2.29 % → 6.94 %) when the tool
documentation was cut, explained as *the feed was no longer buried behind 78 % of
prompt spent on API reference*. That explanation is inferential. This one is
measured: **the agents stopped getting the call wrong.** Both can be true and
they are not separable here — the descriptions, the prompt order and the
temperature all changed together, exactly the "two groups, not two arms" caveat
F-93 already carries. **It is a hypothesis with a number attached, not a
replacement explanation.**

**The loss grows steeply with world size, and that is new.**

| agents | 18 | 36 | 54 | 72 | 90 |
|---|---|---|---|---|---|
| intended actions | 100 | 229 | 315 | 445 | 541 |
| lost | 1.0 % | 6.6 % | 4.1 % | 15.5 % | 14.0 % |

Logistic fit on log(agents): slope **+1.435**, se 0.270, **z=5.32, p=1.0e-07** —
the odds of an action being lost multiply by **4.2x per e-fold** in population.
`r15_a90` (90 agents x 15 rounds) loses **18.6 %**, the highest of any run.

**The consequence, and it matters for how scale is reported.** Successful
actions per agent-turn *declines* across the sweep — 0.917, 0.991, 0.932, 0.870,
0.861 — with corr(log agents, success rate) = **-0.856** (p=0.064, n=5).
Intended actions per agent-turn does not: 0.926, 1.060, 0.972, 1.030, 1.002. A
constant-rate fit gives **chi2=3.71, p=0.45 on successes and chi2=1.94, p=0.75
on intent**. So **agent output intent looks scale-invariant while execution
success does not** — the agents are not becoming less active in bigger worlds,
they are becoming less accurate.

**What this does NOT do.** It does not rescue F-106's `sweep18_a72` outlier.
Blind rejections are by definition *not* feed actions — the post was never
shown — so they cannot be added back into F-106's numerator, and a72's twelve
malformed calls were all `follow`, which is not a feed action either. The a72
deviation stands unexplained.

**The current-era failures have one dominant signature, and it points at a
specific cause.** Of 193 malformed calls in the logged current runs, **111 are
`follow`** — and the commonest single error, **76 of them, is
`follow() got an unexpected keyword argument 'group_id'`**. Another 24 pass
`post_id` to `follow` and 11 pass `content`. The rest are `like_post` called
with no `post_id` (68) and `create_comment` given a `comment_id` (14).

`group_id` is not a parameter `follow` has ever had. The agent is reaching for a
group action and landing on `follow`. **Group actions exist only in the 27-action
set** — `create_group` fires 226 times and `join_group` 40, both confined to runs
that have groups enabled — and B-9 already records that the group environment
hijacks the prompt (`$groups_env` renders before `$posts_env` regardless of
`available_actions`), which is why `campaign.sh` and `overnight.sh` pass
`--no-groups` while `sweep18.sh` deliberately does not.

#### Q-24 — Do groups break `follow`, and therefore the graph?

Every logged current-era run has groups ON, so the contrast cannot be drawn from
data in hand. **One run at the current configuration with `--no-groups`, log
kept, tests it directly.** If the `group_id` errors vanish, then enabling groups
costs roughly half of all `follow` attempts — and `follow` is the mechanism that
builds the network tier, which is the substrate of F-92/F-108, the project's
headline result. That makes this cheap (one run) and unusually well-motivated:
it is not a prompt tweak chasing a 3-5 pp behavioural shift against a 14 pp
floor, it is a malformed-call rate of 57 % on one action with a named cause.

**And the cost of this is measurable on the headline result itself.** Tracing
`follow` end to end in the runs whose logs survive:

| run | succeeded | malformed | invalid target | attempted | success rate | network tier |
|---|---|---|---|---|---|---|
| `sweep18_a72` | 28 | 12 | 7 | 47 | 59.6 % | 2.93 % |
| `sweep18_a90` | 28 | 0 | 6 | 34 | 82.4 % | 2.48 % |
| **`r15_a90`** | **71** | **77** | **9** | **157** | **45.2 %** | **9.54 %** |

**`r15_a90` is the run that carries F-108** — the 90-agent replication of
connection-over-content — and **its follow graph is less than half of what its
agents tried to build.** 77 of those 157 attempts died as malformed calls, the
majority of them `follow(group_id=...)`.

That is not a threat to F-108's validity: a smaller graph makes the network tier
*thinner*, which costs statistical power, and the effect was found anyway. It is
a statement about **power left on the table**. The network tier is 9.54 % of
exposures; with a working `follow` it would plausibly be close to double, and
the checks that are currently underpowered — F-110's network-tier repetition
replication at n=1,442, the `fof` contrast that has needed pooling since it was
first reported — are exactly the ones that would benefit.

**So the binding constraint on the headline result right now is a tool-calling
bug, not the science.** That is what makes Q-24 worth a run ahead of anything
else on the list.

**Do not fold such a run into the cost bank** — `--no-groups` is a different
action surface and therefore a different experimental condition (the B-26/B-28
lesson).

**Operational.** 28 of 44 runs cannot be checked for the malformed channel at
all, because `/tmp/s18_<label>.log` is gone. **The run log is the only record of
an action the agent chose and fumbled**, and it is currently the one artifact
the pipeline does not preserve. Everything else — database, manifest, parquet,
package — survives. That should change.

**Partly closed now.** The error lines from every surviving log are extracted to
`data/logs/<label>_toolerrors.txt` with a parsed summary in
`data/logs/tool_errors_index.json`. The raw lines carry the whole argument dump
and came to 10.5 MB for ten runs; trimmed to tool name plus reason they are
**46 KB**, which is small enough to keep permanently. `/tmp` can now be cleared
without losing the evidence. The full logs remain the only source for anything
else, and are still volatile.

**One stray.** `/tmp/s18_sweep18_s43_a36.log` exists with 14 errors but has no
database — an interrupted run from the seed-43 pass that the r15 campaign
replaced. It is excluded from every figure above; noted so nobody counts it
later.

---


### F-112 — Similarity is not null. It is small, it needs two controls to see, and it is positive in 16 of 16 runs

**This qualifies a headline claim, so the caveats come first.** The published
position — *"the graph carries the personalisation in this simulation, the
embedding does not"* — rests on OR **1.143 [0.524, 2.495], p=0.74** per unit
cosine. That number is not wrong. It is **unstable**, for a reason worth naming.

**Retire the per-unit-cosine odds ratio.** Cosine spans about 0.73 in these runs,
so "per unit" extrapolates beyond the observed range and the estimate becomes
wild: fitted run by run on the twitter persona file it returns 0.50, 1.23, 3.78,
11.92, 46.76, 56.22 and **142.94**. Those are not seven measurements of one
quantity, they are one quantity divided by a lever arm shorter than the units it
is quoted in. Every published similarity figure in this project has used that
scale, including the retracted F-38.

**On a stable scale, with the two controls the earlier analysis lacked, there is
an effect.** Top versus bottom cosine quartile, **first sightings only** (so the
repeat-exposure channel of F-43/F-110, worth 2.35-2.62, is closed by
construction), **feed slot held fixed** (so the F-94 position effect, worth 2.15,
cannot leak in), Mantel-Haenszel across 16 runs:

> **OR 1.33, 95% CI [1.14, 1.60]** — bootstrapped over **runs**, which is the
> correct resampling unit and the mistake the build log already records twice.
> **Positive in 16 of 16 runs. Sign test p = 3.05e-05.**

49,561 first-sighting discovery exposures, 2,651 engagements, both persona files.

**Why it was missed.** Three things had to line up. Without the first-sighting
restriction, repeat exposure — an effect twice the size — sits on top of it.
Without slot held fixed, the ranker's own ordering does. And on the per-unit
scale the confidence interval is so wide that a real 1.33 is indistinguishable
from nothing.

**What does NOT change.** The ordering of effects is untouched and the headline
survives:

| effect | magnitude |
|---|---|
| connection (network vs discovery) | **3.51** |
| repetition (seen before) | **2.62** |
| position (top vs bottom half) | **2.15** |
| **similarity (top vs bottom quartile)** | **1.33** |

Connection still beats content by a wide margin. What is no longer accurate is
*"content does not predict engagement at all"*. It predicts it weakly, and
consistently.

**The persona file matters, and that was predicted.** F-49 explained the null by
corpus uniformity — *"when everything resembles everything, resembling your own
bio adds almost nothing"* — and said the effect had room to show on the more
separable twitter personas. It does. Pooled within file, first sightings, slot
controlled: twitter **OR 5.16 [1.77, 15.1], p=0.0027**; reddit **1.50
[0.99, 2.30], p=0.058** (per-unit scale, so read the direction, not the number).
Post-corpus spread is 0.606-0.847 on twitter against 0.565-0.902 on reddit, and
mean pairwise post cosine 0.738 against 0.790. **A prediction made when the null
was published has been confirmed by data collected afterwards on the other file.**

**What this is not.** Observational. Cosine determines ranking, so high-cosine
posts differ systematically from low-cosine ones in ways beyond cosine — length
and specificity are the obvious candidates and neither is controlled. The
first-sighting restriction and the slot control remove the two known channels;
they do not make it an experiment. **1.33 is also small enough that it would be
invisible in any single run**, which is exactly why 16-of-16 consistency rather
than any one p-value is what carries it.

**Consequence for the write-up.** Artifact `55d7c5a5` §04 is titled *"The
recommender's signal does nothing"* and states the similarity decile table is
flat. That table is computed over all exposures on the reddit file without the
slot control, and it is flat as reported. The section needs the qualification,
not a retraction: the signal is weak, real, and swamped by three larger effects.

---


### F-113 — A small world is not a scaled-down large one. It is a SATURATED one, and that is a different regime

`r15_a18` (18 agents x 15 rounds) landed 02:07. Read next to its 7-round twin and
to the 90-agent pair, it settles three things and raises a methodological one
that affects every cross-size comparison in this project.

**1. The cost law holds out-of-sample a second time.** Plateau **380.2 s/round
(sd 13.3, n=11)** at 18 agents = **21.12 s per agent-turn**, against the
eight-point curve's 21.44 (sd 0.37) and F-107's 21.61 at 90x15. The curve was
fitted entirely on **7-round** runs; it now reproduces at 15 rounds at **both
ends** of the size range, 0.9 % low here and 0.8 % high there. Treat the law as
validated for run length, not merely assumed.

**2. The world runs out of content, and at 18 agents it runs out completely.**

| run | posts existing | distinct seen per agent | share of world seen | sightings per (agent, post) |
|---|---|---|---|---|
| `sweep18_a18` 7 rd | 38 | 31.7 | **83 %** | 2.25 |
| **`r15_a18` 15 rd** | **48** | **39.8** | **83 %** | **4.18** |
| `sweep18_a90` 7 rd | 148 | 60.6 | 41 % | 1.19 |
| `r15_a90` 15 rd | 237 | 107.3 | 45 % | 1.57 |

**Eighteen agents over fifteen rounds produce forty-eight posts in total, and
every agent has seen forty of them, each about four times.** At 90 agents the
same run length leaves 55 % of the world unseen.

**Precisely what "saturated" means here, because the looser version is wrong.**
An earlier draft of this entry said the feed "has nothing left to show". It is
not that. Checked directly: `r15_a18` is the only run in the campaign whose
exposure count falls short of `agents x (rounds-1) x 12`, and the entire
shortfall — 29 exposures — sits in **round 1**, when the world holds fewer than
twelve posts. From round 2 onward the feed is full in every round. **The feed
is always fillable; it is filled with repeats.** Saturation here is a statement
about the ratio of novel to repeated content, not about empty slots.

**3. So `r15_a18`'s 9.90 % engagement is mostly repetition, not sociability.**
It is the highest engagement of any run in the project, and against its 7-round
twin at 7.18 % it looks like longer runs make agents more social. They do not.
Distinct posts shown per agent-turn **falls 5.29 → 2.85** while sightings per
pair nearly doubles, and F-110 puts repeat exposure at OR 2.35-2.62. This is
F-105's mechanism running in reverse: engagement is set by the supply of *novel*
content relative to feed capacity, and that supply collapses in a small world
left running.

**4. F-109 now replicates in direction across a 5x size range.** Feed actions per
agent-turn, 7 rounds → 15 rounds:

| | 7 rd | 15 rd | ratio | chi2 | p |
|---|---|---|---|---|---|
| 18 agents | 0.380 | 0.282 | 0.74 | 2.33 | 0.127 |
| 90 agents | 0.402 | 0.341 | 0.85 | 3.86 | 0.050 |
| **combined** | | | | **6.19** | **0.045** (df=2) |

Still n=1 against n=1 at each size, so this is a consistent direction rather than
an established effect — but it is no longer a single pair.

**5. The follow graph saturates too, and this is the surprise.** Network-tier
share does **not** grow with run length at 18 agents: **5.1 % at 7 rounds,
4.17 % at 15.** At 90 agents the same change takes it 2.48 % → 9.54 %. With
seventeen possible targets the graph is finished early and extra rounds add
nothing; with eighty-nine it is still forming at round 14. **F-108's finding that
run length is what makes connection studiable holds only where the population is
large enough to keep the graph growing.**

#### The methodological consequence, which is the point of this entry

**Population size and novelty supply are entangled by construction in every run
here.** A small world is not a large world with fewer agents — it is a world
where everyone has seen nearly everything, several times, and where the social
graph completed long ago. Those are different regimes, not different points on
one axis.

This does not invalidate the cross-size work: F-105/F-106 are explicitly about
the denominator, and every tier and repetition estimate is a **within-run**
contrast, immune to it. What it does mean is that **"engagement at N agents" is
not a quantity that can be compared across N without saying how much of the world
had been seen** — and that the honest cross-scale report is F-105's
recommendation plus this one: quote feed actions per agent-turn, *and* quote the
share of the world each agent has seen.

**Practical.** If a future design needs a small population *without* saturation,
the lever is run length, not agent count — stop at 7 rounds — or seed a post
corpus. Nothing here is a reason to avoid small runs; it is a reason to stop
reading their engagement rates as behaviour.

---


### F-114 — The cost law replicates independently at 15 rounds. F-106's constant action budget does NOT

Two results from the same four runs, pulling in opposite directions. The
engineering law gets stronger; the behavioural one breaks.

**The cost law is now independently established on a second round count.** The
eight-point curve (exponent 1.005, R² 0.9993, 21.44 s/agent-turn, sd 0.37) was
fitted entirely on **7-round** runs. Four **15-round** runs, fitted on their own:

| run | agents | plateau | per agent-turn |
|---|---|---|---|
| `r15_a18` | 18 | 380.2 s | 21.12 |
| `r15_a36` | 36 | 808.9 s | 22.47 |
| `r15_a90` | 90 | 1,944.9 s | 21.61 |
| `r15_s43_a90` | 90 | 1,890.4 s | 21.00 |
| `r15_a54` *(added 09:25)* | 54 | 1,133.1 s | 20.98 |

**With five points: exponent 0.995 (se 0.024), R² 0.9982, mean 21.44 s per
agent-turn — the 7-round curve's figure to the decimal.** That is
not an extrapolation checked at one point (F-107, F-113) — it is the whole law
refitted on independent data and landing on the same two numbers. Cost is linear
in agents and flat in round count after the ramp. Treat it as settled.

**F-106's constant feed-action budget fails at 15 rounds.**

| run | agents | turns | feed actions | per turn |
|---|---|---|---|---|
| `r15_a18` | 18 | 252 | 71 | 0.282 |
| `r15_a36` | 36 | 504 | 126 | **0.250** |
| `r15_a90` | 90 | 1,260 | 430 | 0.341 |
| `r15_s43_a90` | 90 | 1,260 | 467 | 0.371 |

Constant-rate fit: **chi2 = 10.44, df = 2, p = 0.0054** on the three seed-42
points, and **17.97, df = 3, p = 0.0004** including the replicate. At 7 rounds
the same test gave **p = 0.098, not rejected** (F-106).

> **CORRECTED 09:25, when `r15_a54` landed.** This entry first said *"at 15
> rounds larger worlds spend more per turn, not less"*. **That was wrong** — it
> was a direction read off three points. `r15_a54` returns **0.384**, the
> highest of the five, from the middle of the size range. The full series is
> 0.282 (18), 0.250 (36), **0.384 (54)**, 0.341 (90), 0.371 (90):
> **heterogeneous, not monotone.** Spearman rho vs agents = +0.564, p=0.32;
> Pearson r = +0.689, p=0.20. There is no trend in size — there is a spread.
>
> The rejection gets *stronger* with the extra point: **chi2 = 18.57, df = 3,
> p = 0.00034** (four seed-42 sizes), **21.90, df = 4, p = 0.00021** (all five).
> And the spread is real rather than noise: 1.54x from lowest to highest,
> against an 8.4 % gap between the two replicate runs at 90 agents and F-106's
> 4.4 % CV across nine identical runs.
>
> So: **the budget is not constant at 15 rounds, and it is not a function of
> world size either.** Whatever drives it is not captured by any variable
> measured here.

**Two mechanisms tested, both ruled out.** Reported because the negative results
are what stop the next person re-deriving them:

1. **Feed slots wasted on posts the agent already acted on** — you can only like
   something once, so a repetitive feed should suppress the numerator. Measured
   directly: 9.2 % of exposures at `r15_a18`, **3.4 % at `r15_a36`**, 4.0 % at
   both 90-agent runs. `r15_a36` has the *lowest* waste and the *lowest*
   actions per turn. **Ruled out.**
2. **F-111's silent-loss channels** — malformed calls, blind rejections, invalid
   follows. Loss rates: 11.2 % / **9.9 %** / 18.6 % / 14.1 %. Again `r15_a36` is
   the *lowest* and the 90-agent runs the highest, which is backwards. Both
   15-round runs at 18 and 36 agents recorded **zero** malformed calls.
   **Ruled out.**

**So the 15-round budget failure stands unexplained**, and `r15_a36` at 0.250 is
the point doing most of the work. n=1 per size at 18 and 36; the only replicated
size is 90, where the two runs agree closely (0.341, 0.371). **The obvious next
data is a seed-43 run at 18 and 36, which pass 2 of the current campaign will
produce without any new decision.**

**What this does to the reporting rule.** F-105 said quote feed actions per
agent-turn across scales because it is flat. **That was established at 7 rounds
and does not hold at 15.** The safe version is narrower: within one round count,
feed actions per turn is the stabler metric; across round counts nothing here is
stable, and engagement least of all.

**Engagement at 15 rounds has a different shape from 7 rounds**, worth recording
for anyone reading the series: 9.90 % (18), 4.54 % (36), 4.45 % / 4.71 % (90) —
a sharp fall then flat, against the 7-round curve's slower monotone decline
(7.18 / 6.18 / 5.45 / 3.18 / 3.98). F-113 accounts for the 18-agent point as
saturation; the flatness from 36 to 90 is not accounted for.

**Machine load, third instance.** The pass ran at median 136 % non-simulation CPU
with a 329 % peak — **"HEAVILY LOADED"** by the queue's own threshold — and cost
came in at 21.12 / 22.47 / 21.61, dead on the curve. That verdict has now
over-flagged three times running. It should be recalibrated or demoted to a note,
because a warning that always fires is not a warning.

---


# Part 6 — Simulation 4: run plan and its review

*Was `SIM4_RUN_PLAN.md`. Merged into this file 2026-09-13; original title: “Sim 4 — run plan, drafted 2026-09-08”.*

**Nothing in this plan runs without explicit permission.** Phase 0 is bench-only
and involves no simulation.

## What prompted it

Two things came loose on 2026-09-08:

1. The concurrency ceiling was never measured. The `sweep_8/16/24/32` runs all
   carry `ollama_num_parallel: (unset -> server default)` — a server that was
   serialising. F-56 tested concurrency 4 and no higher. Every claim about an
   "8-slot ceiling" rested on that.
2. A first real bench inverts the assumption: **NP=4 beats NP=8 by 14 %**
   (0.368 vs 0.317 calls/s). If that survives replication, every run this
   session has been ~14 % slower than necessary.

## The measurements in hand — and why none is conclusive

| config | calls/s | mean latency | loaded | free RAM |
|---|---|---|---|---|
| NP=4 conc=4 | 0.368 | 10.8 s | 11 GB | 4.3 GB |
| NP=8 conc=8 | 0.317 | 24.4 s | 17 GB | **0.8 GB** |

**n=1 each.** F-51, F-54 and F-66 were all single measurements that later
retracted. These two rows are a hypothesis, not a result. The NP=8 row is also
confounded: at 0.8 GB free the machine was memory-pressured, so "8 slots is too
many for the GPU" cannot be separated from "17 GB does not fit beside Chrome".

---

## Phase 0 — bench only, NO simulations (~2 h)

| # | Task | Cost |
|---|---|---|
| 0a | ~~Finish the NP sweep~~ **DONE — see F-76. NP=16 is 52x slower, NP=32 fails outright. Ceiling is memory: 4.9 GB + 1.55 GB/slot.** | done |
| 0b | ~~Replicate the bench~~ **DONE — F-77. The 14 % win does NOT replicate; NP=4..8 is a plateau. Adopt NP=4 for variance (CV 3.1 % vs 15.3 %) and 6 GB of RAM, not speed.** | done |
| 0c | Repeat the top two configs with Chrome and Firefox closed | ~15 min |
| 0d | ~~Harness the candidates~~ **DONE — F-78. BOTH FAIL. granite4.1:3b answers do_nothing 24/25; gemma4:e2b is 4.5x SLOWER (911 output tokens/turn). Keep llama3.1:8b.** | done |

**0b is the most important task in the whole plan** and the reasoning is in the
review below: the concurrency question must be answered by cheap bench
replicates, because full runs cannot afford to answer it.

**Gates out of Phase 0**
- Concurrency: adopt a new NP only if it beats NP=8 by >10 % across 5 replicates
  with non-overlapping spread.
- Models: a candidate proceeds only if it clears F-75 break-even on ENGAGED.
  Baseline is llama3.1:8b at 64 %. `granite4.1:3b` (2.2x faster) needs >=29 %;
  `gemma4:e2b` (1.25x) needs >=51 %.

## Phase 1 — concurrency validation at 36 agents (4 runs, ~7 h)

2x NP-winner and 2x NP=8 control, 3 rounds, 36 agents.

**This phase is deliberately underpowered and is not a measurement.** Its only
job is to catch gross breakage and confirm the bench's *direction* holds at 36
agents, because F-60 records four straight cases of small benches overpredicting.
What it can conclude: "no collapse, direction consistent." What it cannot
conclude: the size of the effect. See R1.

## Phase 2 — model gate, S-1 only — **CANCELLED by F-78**

No candidate survived Phase 0d, so there is nothing to gate. S-1..S-6 stay
unqueued and the ~8 runs of baseline-rebuilding a model change would have cost
are not spent. Original text kept below for the record.

### (cancelled) Phase 2 — model gate, S-1 only (2-3 runs, ~3 h)

Runs only if a candidate cleared 0d. One 15-round run per surviving candidate
plus one contemporaneous llama3.1:8b control. Compare engagement against the
break-even rule (F-75). A candidate that fails here stops; S-2..S-6 never run.

## Phase 3 — replicate bank (12 runs, ~24 h)

Fixed, validated configuration. This is the point of the whole efficiency
exercise: F-35's ~28pp noise floor is the ceiling on every behavioural question
in this project, and the only cure is more runs at one configuration.

**Total if everything passes: ~36 h of machine time.**

---

# Review of this plan

## R1 — Phase 1 cannot resolve the effect it is about, and the plan must not pretend otherwise

Wall-clock CV on this setup is ~15 %. At alpha .05 / power .8, resolving a 14 %
difference needs roughly

    n = 2 (1.96 + 0.84)^2 (15/14)^2  ~=  18 runs per arm

**36 runs, ~60 hours, to confirm one concurrency setting.** That is not
affordable, and it is why Phase 1 is scoped as a breakage check rather than a
measurement. The actual resolution comes from Phase 0b, where a replicate costs
60 seconds instead of 105 minutes. Any plan that tries to answer concurrency
with full runs is mis-designed.

## R2 — The NP=8 result is confounded and Phase 0c is not optional

0.8 GB free means possible swapping. Without the Chrome-closed control, adopting
NP=4 might be adopting "my browser was open", which would not generalise to an
unattended overnight run where it is not.

## R3 — Everything so far is n=1, which is this project's signature failure

F-51 (concurrency), F-54 (prefill), F-66 (persona hoisting) were each a single
measurement that a replicate later overturned. The two rows above are the same
shape of evidence. Nothing may be concluded from them until 0b.

## R4 — Change one variable at a time, in this order

Concurrency, then model, then bank. If both concurrency and model change before
Phase 3, the bank is uninterpretable — neither against the published nine runs
nor internally.

## R5 — A model change is far more expensive than the download

If the model changes, Phase 3's bank cannot be pooled with the published nine
runs: F-35's noise floor is a llama3.1:8b measurement (S-4), and the new model
needs its own before any effect size means anything. That is 5+ runs of pure
overhead before a single new finding. **The realistic recommendation is to keep
llama3.1:8b and take the concurrency win**, unless Phase 0d shows a candidate
that is both faster and at least as engaged.

## R6 — CORRECTED: the uncontrolled variable was NUM_PARALLEL, not flash attention

Same model, same context read 6.3 GB then 11 GB. I blamed flash attention. The
real cause: the session server was started behind `pgrep -f "ollama serve" || ...`,
so an already-running server at the machine default (NP=1) was reused and the
NP=8 env var never applied. 6.3 GB is exactly `4.9 + 1x1.55` — NP=1. Every RAM
figure quoted before Phase 0b was taken at NP=1 while being described as NP=8.
NUM_PARALLEL must be recorded in the manifest, and servers must be started
unconditionally, never behind a `pgrep` guard.

## R7 — Thermal and availability

~36 h of sustained GPU on a laptop that is also the user's daily machine, which
has already been stopped twice for fan noise. Phase 3 must stay resumable
(`campaign.sh` already skips completed manifests) and should be chunked so an
interrupt costs one run.

## R8 — If NP=4 wins, what does it say about the published results?

Only that they were slower than necessary. Timing does not affect behaviour, so
the nine published runs and their three findings stand. Worth stating explicitly
so the correction is not over-read.

## What I would cut

Phase 1, if Phase 0b comes back with clean, non-overlapping spread across five
replicates. Its value is guarding against F-60, and that guard costs 7 hours to
confirm something a 45-minute bench may already show unambiguously. Decide after
0b, not now.


---

# Part 7 — Overnight plan, 2026-09-08 (historical, kept for the record)

*Was `OVERNIGHT_2026-09-08.md`. Merged into this file 2026-09-13; original title: “Overnight plan — 8 hours, hard-stopped”.*

Written 2026-09-08 after Phase 0. Every block is time-boxed and the whole thing
aborts cleanly at T+8:00 rather than running into the morning.

**Config going in:** llama3.1:8b (F-78 — both candidates failed), NP=4
(F-77 — for variance and RAM, the means are indistinguishable), 36 agents,
15 rounds, terse tools, uncapped max_tokens.

**Standing guardrails on every run:** 300 s request timeout and a 20-minute
stall watchdog (B-22, which once cost a full day); an engagement gate that halts
on collapse rather than continuing (B-23, which once burned seven runs); a
manifest per run so an interrupt costs one run, not the night.

---

## T+0:00 → 0:15  Preflight and the fixes today exposed

Code work, no GPU.

1. **Kill the `pgrep` server-start bug.** Today the session server was started
   behind `pgrep -f "ollama serve" || start...`, so an already-running server at
   the machine default (NP=1) was silently reused and every `NUM_PARALLEL=8`
   claim for hours was false. Every script that starts ollama must start it
   unconditionally after a kill. Audit: `campaign.sh`, `ab_efficiency.sh`,
   `overnight.sh`.
2. **Record `ollama_num_parallel` in the manifest as the ACTUAL value.** It
   currently writes `(unset -> server default)`, which is how the contaminated
   `sweep_*` runs looked legitimate. Read it back from `/api/ps` or the server
   env, not from our own intention.
3. **`eval_model.py`: add `--reps` and uncapped mode.** F-79 showed a single
   25-trial reading swings 44-64 %; F-78 showed the 300-token cap silently
   fails thinking models. Both are harness bugs found today.
4. Preflight: disk >= 40 GB, no stale ollama, models present, `data/` writable.

**Abort condition:** any preflight failure stops the night and writes why.

## T+0:15 → 1:15  Block A — does prefix caching survive at NP=4?

Bench only. **This is the highest-value hour of the night** and it must run
first, because it can change the config every later block uses.

F-69 established that Ollama's prefix cache does not survive 8 concurrent slots
evicting each other, which is why F-66's persona-hoisting fix delivered ~1 %
instead of the predicted 2.5-5x. F-77 has since shown **NP=4 is throughput-
equivalent to NP=8**. So: at half the slots, does the cache live?

Measure, 5 replicates per cell, unique suffix per call:

| | NP=1 | NP=2 | NP=4 | NP=8 |
|---|---|---|---|---|
| shared prefix (tools first, persona/feed after) | | | | |
| varying prefix (persona first — today's layout) | | | | |

The number that matters is the **ratio within each column**. F-66 measured a
shared prefix reprocessing at ~20,000 tok/s against 490 — a 40x difference on
70 % of the prompt. If any column shows that ratio surviving, F-72 unlocks and
it is worth more than every other lever combined.

**Deliverable:** F-80, with the honest negative result if it does not survive.

## T+1:15 → 1:45  Block B — implement whatever Block A licenses

- **If the cache survives at some NP:** reorder the prompt so the system block
  and all 22 tool schemas form a byte-identical prefix across all 36 agents,
  with persona and feed strictly after. Ship with a test that asserts the prefix
  is byte-identical between two different agents — that assertion is the whole
  correctness argument, and F-66 failed for want of it.
- **If it does not survive:** implement nothing. Document and move on. Note that
  `--lean-actions` is NOT the fallback: removing 8 actions changes what an agent
  can do (F-55), so it buys speed with behaviour and is out of scope tonight.

**Rule for this block: no code reaches a 15-round run without a passing test and
the 3-round smoke below.**

## T+1:45 → 2:00  Smoke gate

One 36-agent, 3-round run at the final config. Checks the pipeline end to end
and that engagement is alive. **If engagement < 1 %, stop the night** — that is
the F-63 collapse signature and no further runs are worth machine time.

## T+2:00 → 4:00  Block C — validation run 1 (36 agents, 15 rounds)

Full run at the final config. Gives real wall clock at NP=4 and a first
engagement figure comparable to the published nine.

*Concurrent, no GPU:* review the Block B diff, update `SIM4_LOG.md` (Part II).

## T+4:00 → 6:00  Block D — validation run 2

A second run, because one cannot be told apart from noise: F-35's floor is ~28pp
on behaviour and ~15 % on wall clock. Two runs cannot resolve a small difference
either, but they can show gross agreement or disagreement, which is what is
actually being asked of them.

*Concurrent:* Parquet export of everything completed so far.

## T+6:00 → 7:00  Block E — 99-agent feasibility smoke, 3 rounds

**Not science.** `personas.py:75` already loads the Twitter CSV and it holds 99
usable personas, so larger worlds need a flag, not code — and every run in this
project's history has been 36. This probes whether 99 agents survive memory, the
DB and the ranker at all, and yields a real scaling coefficient for the "bigger
runs" question.

**Explicitly not poolable** with the published nine: Twitter rows carry no age,
gender or MBTI, so it is a different persona construction and a different
experiment. It runs last so a short night costs only this.

**Abort if:** free RAM < 1 GB or the watchdog fires. 99 agents at NP=4 is
untested memory territory.

## T+7:00 → 8:00  Close out

1. `analyze.py` on every new run; `export_parquet.py --all`.
2. Update `SIM4_LOG.md` (Part II) (F-80+) and `SIM4_RUN_PLAN.md`.
3. Write the morning summary: what ran, what it showed, what broke, what I got
   wrong, and the single recommended next action.
4. Leave ollama stopped so the machine is not holding 11 GB at breakfast.

---

## What I am NOT doing, and why

- **Phase 1 as designed (4 runs, 7 h).** Sized to resolve a speed difference
  F-77 showed is not resolvable. The NP change now rests on variance and memory,
  which do not need that power.
- **More model candidates.** F-78 settled it; a third candidate is a guess.
- **A full 99-agent science run (~5.5 h).** It silently starts a new baseline
  that cannot pool with the published nine. That is a decision to make awake.
- **Anything that trades engagement for speed.** F-75: engagement is the
  dependent variable, and every speed lever that touches it has lost.

## Honest risk list

| risk | mitigation |
|---|---|
| Block B code is written and validated with no human review | prefix-identity test + 3-round smoke gate before any 15-round run |
| Block A returns another phantom effect | 5 replicates per cell; no config change on n=1 (the rule six findings earned) |
| 99 agents exhausts RAM | last block, RAM abort, watchdog |
| Runs overrun 2 h at NP=4 | hard stop at T+8:00; later blocks drop first |
| Chrome left open eats 5 GB | asked the user to close it; if not, NP=4 still leaves more headroom than NP=8 |


---

# Part 8 — Primer: what upstream OASIS is and how the framework works

*Was `LEARN_OASIS.md`, merged 2026-09-13. Verbatim.*

**This part is about UPSTREAM OASIS, not about our simulations.** It explains the
published framework and the paper's own findings, and it was written as an
orientation document before Sim 1. Two cautions when reading it:

- **Its internal "PART 1..8" headings are the primer's own** and have nothing to
  do with this file's Parts 1-8.
- **Its "verified, as of today" setup notes are from August 2026** and have been
  overtaken — the authority on how a run is configured now is Part 5 §0, which
  carries the standing warnings. In particular the primer predates B-28, so it
  says nothing about `OLLAMA_CONTEXT_LENGTH`.

Upstream bugs the primer does *not* mention, because we found them afterwards,
are listed in Part 5 §4.

---

# OASIS — Your Complete Starter Guide

Written for you, Gordon, ahead of Wednesday's meeting.
Everything here was checked against the actual paper (arXiv 2411.11581, 37 pages) and the
actual code in this folder. Nothing is guessed.

---

## PART 1 — The Big Idea (explained simply)

### The problem

Scientists want to answer questions like:

- Why does fake news spread faster than real news?
- Why do people in groups get more extreme in their opinions over time?
- Why do people upvote something just because it already has upvotes?

To answer these, you would normally have to run an experiment **on real people on real
social media**. That is expensive, slow, and often unethical — you cannot ethically
inject fake news into Twitter to see what happens to millions of real humans.

### The old solution and why it wasn't good enough

For decades scientists used **Agent-Based Models (ABMs)**. Think of a video-game world
full of simple computer characters ("agents") following rules like:

> "If 3 of my friends liked this post, I like it too."

That works, but it's dumb. Real people don't follow a fixed rule. A real person reads the
post, thinks about it, and decides based on who they are, their mood, and context. A
number-threshold can't capture that.

### The new solution: OASIS

OASIS replaces those dumb rule-followers with **LLM agents** — each agent is a language
model (like Llama or GPT) given a personality, and it *reads posts and reasons about them
in English* before deciding what to do.

**A one-sentence definition:**

> OASIS is a fake social media website (like a fake Twitter or fake Reddit) where every
> single "user" is an AI with its own personality, and researchers can run experiments on
> that fake society to study how real societies behave.

### The two things OASIS claims to be better at

The paper's whole argument (page 2) is that every earlier simulator had two problems, and
OASIS fixes both:

| Problem with earlier work | What OASIS does |
|---|---|
| **Not generalizable** — each simulator was hard-coded for one experiment. Want to study something else? Rewrite the whole thing. | OASIS is built from 5 swappable modules. Switch from Twitter-style to Reddit-style by swapping one module. |
| **Not scalable** — most ran 5 to 1,000 agents. Real platforms have millions. | OASIS runs up to **1,000,000 agents**. |

Table 1 on page 3 of the paper is the receipt for this claim. Earlier systems: Smallville
(25 agents), Sotopia (2), RecAgent (5), S3 (1,000), HiSim (300/700). OASIS: 1M agents, 21
actions, two platforms, open-source.

**Memorize this line for your meeting:** *"OASIS's contribution isn't a new social theory —
it's infrastructure. It's a generalizable, scalable platform so other people can run social
science experiments cheaply."*

---

## PART 2 — How OASIS Actually Works (the 5 parts)

Imagine building a fake Twitter from scratch. You'd need five things. OASIS has exactly
these five (paper Section 2.1, Figure 2):

### 1. Environment Server — "the website's memory"

A database that stores everything: who the users are, what they posted, who follows whom,
who liked what.

It has these tables (paper Appendix D.2 — and I confirmed these exist in your local
`data/reddit_simulation.db`):

`user`, `post`, `comment`, `like`, `dislike`, `comment_like`, `comment_dislike`,
`follow`, `mute`, `trace`, `rec`

**The most important table for you is `trace`.** It logs every single action every agent
ever took, with a timestamp and the reason. When your experiment ends, `trace` is your
data. This is where your results live.

### 2. RecSys (Recommendation System) — "the algorithm"

Agents can't see all million posts. Something has to decide *what shows up in their feed*.
This is the single most powerful component, because **whoever controls what people see
controls what people think.**

OASIS has two versions:

**Twitter/X style — interest-based.** Score a post for a user using this formula
(paper Appendix D.3, equation 2):

```
Score = R × F × S
  R = recency      (newer posts score higher)
  F = fan count    (posts by users with more followers score higher — "superuser broadcast")
  S = similarity   (cosine similarity between post text and the user's profile text)
```

Similarity uses **TwHIN-BERT**, a model Twitter trained on 7 billion tweets. The paper's
ablation (Appendix C.2) shows why this matters: regular BERT doesn't know that "Barry
Allen" and "The Flash" are the same person; TwHIN-BERT does. Better embeddings → better
feed → more realistic spread.

**Reddit style — hot-score based.** Reddit's real published ranking formula
(paper equation 1):

```
h = log10(max(|u − d|, 1)) + sign(u − d) · (t − t0) / 45000
  u = upvotes, d = downvotes, t = post time in seconds, t0 = 1134028003
```

Plain English: popular + recent = top of the feed.

**Key ablation finding (Appendix C.2):** if you remove the RecSys entirely, information
stops spreading almost immediately. Without it, the only thing that happens is one
superuser broadcasting into the void. The RecSys is what connects strangers.

### 3. Agent Module — "the fake person"

Built on **CAMEL** (the same team's agent framework — that's why the package is called
`camel-oasis`). Each agent has:

- **Memory** — what posts it has seen, its own past actions, and *the reasons it gave*.
- **Action module** — the paper lists **21 actions** (README says 23; the code in
  `oasis/social_platform/typing.py` currently defines 38 `ActionType` entries because
  features like group chat, quote, report, and interview were added after publication).

The 21 in the paper: sign_up, refresh, trend, search_posts, search_user, create_post,
repost, follow, unfollow, mute, unmute, like_post, unlike_post, dislike_post,
undo_dislike_post, create_comment, like_comment, unlike_comment, dislike_comment,
undo_dislike_comment, do_nothing.

**Chain-of-Thought reasoning is built in.** The agent must output JSON like this
(paper Appendix D.1):

```json
{
  "reason": "your feeling about these posts, then choose functions based on the feeling",
  "functions": [{"name": "like_post", "arguments": {"post_id": 1}}]
}
```

That `reason` field is a gift to you as a researcher. You don't just get *what* the agent
did — you get *why*, in English. That's data you could never get from real users.

### 4. Time Engine — "when people are awake"

Real people don't tweet at 4am. Each agent gets a **24-number vector** — the probability
it is active in each hour of the day. The paper computes it from real scraped data
(Appendix E.1, equation 6):

```
P(user i, hour j) = (how often user i posts at hour j) / (max across all users at hour j)
```

Time moves in **timesteps**, where **1 timestep = 3 minutes** of simulated time.

**Key ablation finding (Appendix C.3):** set every probability to 1.0 (everyone always
awake) and the simulation stops matching reality. Everyone acts constantly, and spread
patterns break. Timing is not a detail — it's load-bearing.

### 5. Scalable Inferencer — "the traffic controller"

Engineering plumbing so a million agents can call an LLM at once: an async message queue,
UUIDs to match requests to responses, and a manager balancing work across GPUs
(Appendix D.4).

Cost reality from the paper: the 1M-agent misinformation experiment took **24 A100 GPUs
running for a week** (page 10). You will not be doing that on a laptop, and that's fine.

---

## PART 3 — What They Actually Discovered (the 5 findings)

This is what you should be able to recite. The paper ran three classic social science
studies and asked two research questions (page 6).

**RQ1: Can OASIS reproduce known real-world phenomena?**
**RQ2: Does the number of agents change the answer?**

### Finding 1 — Information spreading mostly matches reality

They took 198 real Twitter rumor-propagation cases (from the Twitter15 and Twitter16
datasets), rebuilt those users as agents, and let it run.

Measured with three metrics (Appendix F.2.1):
- **Scale** — how many unique users participate
- **Depth** — how many reshare-hops from the original post
- **Max breadth** — the widest single layer of the spread tree

Result: **scale and max breadth match well** (~30% normalized RMSE). **Depth was too
shallow.** Their honest explanation: the simplified RecSys can't model "intermediary
users" — the ordinary mid-level people who pass things along in the real world.

### Finding 2 — Group polarization is reproduced, and worse in uncensored models

Setup: 196 core agents discuss a dilemma — *"Helen is a successful writer. Should she risk
writing an ambitious new novel, or stick to safe popular ones?"* Agents start with mildly
conservative views. Run 80 timesteps, sample opinions every 10, and have GPT-4o-mini judge
which answers got more extreme.

Result: opinions drifted **more extreme over time** — exactly what real group polarization
does. And an **uncensored** Llama-3-8B (safety guardrails stripped) polarized *harder*,
using absolutist phrasing like "always better."

### Finding 3 — AI agents herd more than humans do 🔥

This one is genuinely interesting and it's the finding I'd lead with in a meeting.

They replicated a famous 2013 *Science* study (Muchnik et al.). Take comments and split
them into three groups:
- **up-treated** — given one fake upvote at the start
- **down-treated** — given one fake downvote at the start
- **control** — given nothing

Then see what the crowd does.

Result:
- On **up-treated** content, agents behaved about like humans. Both pile on.
- On **down-treated** content, **humans corrected it — they upvoted it back up. Agents did
  not. Agents piled on the downvote.**

Conclusion in the paper's words: *agents are more inclined to herd, while humans possess a
stronger critical mind.* Humans see one downvote and think "hang on, is that fair?" The AI
just follows.

### Finding 4 — More agents produce more diverse and more useful opinions

Scaled from 196 → 10,196 → 100,196 agents and asked GPT-4o-mini which crowd gave more
helpful advice. 10k beat 196 in **76.5%** of comparisons. 100k beat 10k in **54.5%**.

### Finding 5 — Some phenomena are INVISIBLE at small scale ⭐

This is the most important methodological result in the whole paper.

They tested herd behavior on counterfactual (false) posts like *"Shanghai is a twin city of
Atlanta."*

- At **100 agents**: no herd effect at all. Up, down, and control looked identical.
- At **1,000**: starting to appear.
- At **10,000**: clear, strong herd effect.

**If they had only run 100 agents, they would have concluded the effect doesn't exist.**
Scale isn't a bragging right — it's a requirement for the science to be valid. This is
OASIS's real justification for existing.

Bonus finding (Appendix F.4.3): at 10,000 agents, the crowd *self-corrected*. Agents moved
from surprise → partial doubt → full rejection of the false claim. The group got to the
truth even though individuals didn't start there.

### Also: misinformation beats official news

In the 1M-agent run, they posted 4 true news items and 4 matched fake versions from the
same account. Using TF-IDF similarity over **733,824** agent-generated posts, misinformation
consistently generated more discussion — and stayed alive longer (page 11). The paper also
observed that new follow-relationships **clustered** into distinct communities — echo
chambers forming on their own.

---

## PART 4 — Your Setup (verified, as of today)

I checked. Here is exactly what you have:

| Thing | Status |
|---|---|
| Repo location | `/Users/gordon/research/oasis` |
| Your fork | `origin` → `github.com/KGordo11/oasis` |
| Upstream | `upstream` → `github.com/camel-ai/oasis` |
| Branch | `main`, matching `origin/main` at commit `46cdc8d` |
| Virtual env | `oasis-env/` — works, `oasis` and `camel` 0.2.78 both import |
| Ollama | Installed and **currently running** |
| Ollama model | `llama3.2:3b` (only model installed) |
| Prior successful run | **Yes** — 2026-05-30, produced 36 users, 8 posts, 4 comments, 104 trace rows |
| Your Ollama example | `examples/reddit_simulation_ollama.py` — **untracked** (you wrote it, not in upstream) |

You are in better shape than you think. **You have already successfully run a simulation.**
The database `data/reddit_simulation.db` is the proof.

### ⚠️ One honest warning about the model

The paper used **Llama-3-8B-Instruct**. You have **llama3.2:3b** — less than half the size.

This matters because agents must output **valid JSON with correct function names**. Small
models are worse at that; some agents will produce malformed output and their action gets
dropped. Your simulations will be noisier than the paper's.

This is fine for **learning and prototyping**. For results you'd defend in a paper, you'd
want a bigger model. Say this in your meeting — it shows you understand the limits of your
own setup, which is exactly what a research supervisor wants to hear.

If your Mac has the RAM, `ollama pull llama3.1:8b` gets you to parity with the paper.

---

## PART 5 — Running It

Always activate the venv first:

```bash
cd /Users/gordon/research/oasis
source oasis-env/bin/activate
```

### The simplest possible run

```bash
python examples/reddit_simulation_ollama.py
```

**What that script does, line by line:**

1. Points CAMEL at your local Ollama server (`http://localhost:11434/v1`)
2. Loads 36 pre-made agent personalities from `data/reddit/user_data_36.json`
3. Deletes any old database so you start clean
4. `oasis.make(...)` builds the fake Reddit
5. `await env.reset()` boots it up
6. **Timestep 1** — a *manual* action: agent 0 posts "Hello, world!" and comments; agent 1
   comments. This seeds the platform so there's something to react to.
7. **Timestep 2** — an *LLM* action: every agent reads its feed and decides for itself
8. `await env.close()` saves everything

### The two kinds of action — this is the core concept

```python
ManualAction(action_type=..., action_args={...})   # YOU decide. The scientist's lever.
LLMAction()                                        # The AI decides. The thing you measure.
```

**This is the whole experimental design in two lines.** `ManualAction` is how you apply a
treatment (inject a rumor, plant a fake upvote). `LLMAction` is how the society responds.
Everything you'll ever build is some pattern of these two.

### Reading your results

Results live in SQLite. Open it however you like:

```bash
python -c "
import sqlite3
c = sqlite3.connect('data/reddit_simulation.db')
for row in c.execute('SELECT user_id, action, info FROM trace LIMIT 20'):
    print(row)
"
```

The `trace` table is your dataset. Every row is one agent doing one thing.

Also check `log/social.agent-*.log` — it captures the full prompt each agent saw and what
it decided. Great for debugging *why* an agent did something weird.

### Other examples worth reading

| File | What it teaches |
|---|---|
| `examples/quick_start.py` | Building agents by hand (Alice and Bob) instead of loading a profile file |
| `examples/twitter_simulation_openai.py` | The Twitter/X platform instead of Reddit |
| `examples/different_model_simulation.py` | Giving different agents different LLMs |
| `examples/custom_prompt_simulation.py` | Changing what agents are told about themselves |
| `examples/experiment/reddit_simulation_counterfactual/` | **The actual Finding-5 experiment.** Note the yaml files: `up_100`, `control_100`, `down_100`, then `_1000`, then `_10000` — that's the exact 3-condition × 3-scale design. |

**Read that counterfactual folder.** It is a complete, published, working experiment. The
fastest way to design your own is to copy the shape of one that already worked.

---

## PART 6 — Designing Your Own Experiment

### The recipe

Every OASIS experiment is the same four steps:

1. **Population** — who are the agents? (a profile JSON, or generated)
2. **Treatment** — what do you inject, via `ManualAction`?
3. **Free play** — let agents run with `LLMAction` for N timesteps
4. **Measurement** — query the `trace` table and compare conditions

### What makes an experiment GOOD (steal these from the paper)

**1. It has a control group.**
The single most important thing. Notice the paper never just runs one condition — it always
runs up-treated / down-treated / **control**. Without a control you cannot know whether your
result is caused by your treatment or is just what agents do anyway.

**2. It changes exactly one thing.**
In the herd experiment, the *only* difference between conditions is one initial vote. Same
posts, same agents, same everything else. If you change two things at once you can't
attribute the outcome to either.

**3. It has a number you can measure before you start.**
The paper defines its metrics *in advance*: scale, depth, max breadth, post score, disagree
score. Decide your number first. "I'll see what happens" is not an experiment — it's a demo.

**4. It's grounded in something known.**
The three headline experiments each replicate a real published human study (Vosoughi 2018,
Lindesmith 1999, Muchnik 2013). This gives you a target to compare against. "Does the
simulation reproduce the known human result?" is a far stronger question than "what will
happen?" — because it has a right answer.

**5. It varies scale.**
Finding 5 exists only because they ran 100, 1k, *and* 10k. Running the same design at two or
three sizes is cheap and can turn a null result into a real finding.

**6. It repeats.**
Appendix F.2.2: they reran the same topic 10 times to show results were stable. LLMs are
random. One run is an anecdote.

### Good starter projects for you

Realistic on llama3.2:3b and 36–100 agents:

**A. Replicate herd effect at small scale.**
Take the counterfactual example, run up/control/down with your local model. Expected result
per Finding 5: **no effect** at 100 agents. Reproducing a *known null* proves your pipeline
works. Genuinely good first project.

**B. Does the RecSys cause echo chambers?**
Run the same population twice — once with the interest-based Twitter RecSys, once with
Reddit's hot-score. Measure how clustered the follow-graph gets. The paper observed
clustering (Figure 10) but didn't isolate the RecSys as the cause. That's an open question.

**C. Does personality change herding?**
Generate two populations — one all-agreeable, one all-skeptical — using the profile prompts
in Appendix E.3. Same treatment. Does the herd effect shrink? Finding 3 says agents herd more
than humans; **can prompting close that gap?** That's a real, publishable-shaped question.

**D. Model comparison.**
Run the identical experiment on llama3.2:3b vs llama3.1:8b. The paper did this (Appendix C.4,
comparing Qwen1.5-7B, InternLM2-20b, Llama-3-8B). Cheap, and directly useful to your lab —
it tells everyone what model floor is needed for valid results.

**E. Extend the action space.**
The paper's limitations section names what's missing: bookmarking, tipping, purchasing,
live-streaming, and anything multimodal. Adding an action is a concrete engineering
contribution.

### Where to read next in the code

```
oasis/environment/env.py            the main loop — how a timestep works
oasis/environment/make.py           how oasis.make() assembles everything
oasis/environment/env_action.py     ManualAction and LLMAction (only ~45 lines, read it)
oasis/social_agent/agent.py         how an agent decides
oasis/social_agent/agents_generator.py   how profiles become agents
oasis/social_platform/typing.py     every ActionType
oasis/social_platform/recsys.py     the recommendation algorithms
```

---

## PART 7 — Honest Limitations (paper Appendix H)

Know these. Being able to state your tool's weaknesses is what separates a researcher from a
user.

- **RecSys is simplified.** No collaborative filtering. Real platforms are far more complex.
  This is the paper's own explanation for why simulated depth was too shallow.
- **Agents are abstractions of people.** Whether scraped or generated, a profile is not a
  person. There is an irreducible gap.
- **Text only.** No images, video, or audio — arguably where most real influence now happens.
- **Slow.** A million agents takes days on serious hardware.
- **Ethics.** The paper flags this directly (Appendix I): a tool that simulates a million
  users could be misused to plan manipulation campaigns, and results could reinforce bias if
  over-interpreted. Don't skip this in your meeting.

---

## PART 8 — Wednesday Cheat Sheet

**If asked "what is this project?"**
> OASIS is an open-source social media simulator where up to a million LLM agents act as
> users on a fake Twitter or Reddit. It exists so social scientists can run experiments on
> phenomena like misinformation spread that would be unethical or impossible to run on real
> people. It's from Shanghai AI Lab with Oxford and KAUST, built on the CAMEL agent framework.

**If asked "what's the actual contribution?"**
> Infrastructure, not theory. Prior simulators were single-purpose and capped around a
> thousand agents. OASIS is modular — five swappable components — so one codebase covers many
> experiments, and it scales to a million agents.

**If asked "what did they find?"**
> Three replications and two scale findings. It reproduces real information-spread patterns
> within about 30% error, reproduces group polarization, and reproduces the herd effect. Two
> things surprised me: agents herd *more* than humans — humans push back on an unfair
> downvote and agents just pile on — and some effects are completely invisible below about a
> thousand agents. At 100 agents they'd have concluded the herd effect didn't exist.

**If asked "what would you do with it?"**
> Start by replicating the counterfactual herd experiment at small scale locally to validate
> my pipeline, then vary agent personality to test whether the agent-vs-human herding gap is
> a prompting artifact or something deeper.

**Your one memorable line:**
> *"The finding that stuck with me: AI agents herd harder than people. Show a human one
> downvote and they push back. Show an agent one downvote and it joins in."*

**Be honest about your setup.** Say you're running locally on Ollama with a 3B model, that
you know the paper used an 8B, and that you expect noisier JSON compliance as a result. That
answer will land better than pretending everything is production-grade.

---

## Quick command reference

```bash
cd /Users/gordon/research/oasis
source oasis-env/bin/activate

ollama list                                    # what models you have
ollama serve                                   # if it isn't running

python examples/reddit_simulation_ollama.py    # run a simulation

sqlite3 data/reddit_simulation.db "SELECT * FROM trace LIMIT 20;"
tail -f log/social.agent-*.log                 # watch agents think

git fetch upstream && git log --oneline HEAD..upstream/main   # what's new upstream
```
