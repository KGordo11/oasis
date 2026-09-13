# Overnight plan — 8 hours, hard-stopped

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
