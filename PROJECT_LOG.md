# Project Log

Running log of setup decisions, what's been run, what was found, and
what's still open — for this fork's local-Ollama experiment work. The
three full write-ups (`SESSION_REPORT (basic sim1).md`,
`COUNTERFACTUAL_EXPERIMENT_REPORT(sim 2, groups).md`,
`SHIELD_EXPERIMENT_REPORT.md`) are the detailed reports; this file is the
shorter, chronological "what happened and why" that ties them together,
so a new session (or a new reader) doesn't have to re-derive context from
git history or re-read all three reports cover to cover.

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
