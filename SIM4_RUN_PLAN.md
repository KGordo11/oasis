# Sim 4 — run plan, drafted 2026-09-08

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
