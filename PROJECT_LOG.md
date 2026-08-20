# Project Log

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

## Sim 1 — reasoning capture (`SESSION_REPORT (basic sim1).md`)

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

## Sim 2 — herd behavior (`COUNTERFACTUAL_EXPERIMENT_REPORT(sim 2, groups).md`)

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

## Sim 3 — the iAgent Shield (`SHIELD_EXPERIMENT_REPORT.md`)

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
