# Research agenda — what to study next, and why

*Written 2026-09-11, overnight. Status: candidate directions, nothing approved.
Supersedes nothing; the Sim 4 results stand as published.*

**The constraint this document is written against.** A run at the current design
point costs about 2.8 hours and the machine is one M2 Max. Everything below is
priced in runs. Anything needing more than about forty runs is not a project,
it is a wish.

---

## 0. What changed tonight, and why it reorders everything

F-94. Slot position is worth an odds ratio of **2.15** after conditioning on the
ranker's own relevance score, replicating in 9 of 9 runs. Tightening the score
control from 5 bins to 80 does not weaken it.

Put that beside the three results already published, all measured on the same
runs:

| what was measured | odds ratio | what kind of thing it is |
|---|---|---|
| network vs discovery | 3.07 | **structural** — who you follow |
| repeat exposure | 2.62 | **structural** — how often you are shown it |
| slot position | 2.15 | **structural** — where it sits on the screen |
| content similarity | 1.14, CI spans 1 | **semantic** — what the post is about |

**Everything structural works. The one semantic thing does not.** That is not
four findings. That is one finding stated four times, and it has a name.

---

## 1. FLAGSHIP — Is the recommender doing anything, or is it only allocating attention?

### The claim to test

A recommender system is built to match content to people. This one does not
detectably do that: cosine similarity predicts nothing, and its composite score
does not explain the position effect. What it does do is decide *where things
go*, and where things go turns out to matter enormously.

**Hypothesis: the ranker's contribution to engagement is almost entirely the
allocation of attention, not the matching of content. Its ordering could be
replaced by an arbitrary one with little loss.**

If true, this is a strong and slightly uncomfortable claim about
recommender systems in LLM-agent societies, and it is testable in one run.

### The experiment

Three arms, identical in every other respect:

| arm | feed construction | what it isolates |
|---|---|---|
| **control** | rank as now | the status quo |
| **shuffled** | rank as now, then randomise the order before display | ordering, holding *selection* fixed |
| **random-select** | fill slots by uniform sample from the candidate pool | selection, holding nothing fixed |

The shuffled arm is the sharp one. The same twelve posts reach the same agent;
only their order changes. Predictions, stated in advance:

- If the ranker's ordering carries real information the score does not capture,
  shuffling should **reduce total engagement** and flatten the slot gradient.
- If position is pure attention, shuffling should leave total engagement
  **roughly unchanged** while flattening the per-slot gradient — the same
  engagement, redistributed.

Those two outcomes are distinguishable and both are interesting. There is no
null result here, which is the property a good experiment has.

### Cost

At the measured run-level noise floor of 0.52pp, a configuration comparison
needs 2 to 5 runs per arm. Three arms, four runs each, twelve runs, about
**34 hours of machine time** — three overnights. Feasible this month.

### Why nobody has done it

Both OASIS-derived projects surveyed (arXiv 2507.14660, arXiv 2511.06448)
disable the follow-graph feed entirely and run recommender-only worlds, and
neither records feed position at all. The exposure ledger that makes this
measurable is not standard equipment. It is ours.

### What it needs built

One flag, `--shuffle-feed`, applied after ranking and before display, plus a
manifest field recording it. The exposure ledger already stores the displayed
position, so the analysis is F-94's, unchanged.

---

## 2. SECOND STRAND — How much memory does it take to stop broadcasting?

### The claim to test

An agent with no memory between rounds engages at 2.30 % and its actions are
almost entirely `create_post`. An agent with full memory engages at 6.94 % and
likes and replies. Same model, same personas, same feed (F-88).

**Memory is what converts a speaker into a participant.** Nobody has asked where
the threshold is, or whether there is one.

### The experiment

Memory window as a dose: 0, 1, 2, 3, 5 rounds, and unbounded. Six arms, three
replicates each, 18 runs — but the short-memory arms are *cheap*, because short
context is fast. The zero arm runs in 55 minutes against 170. Estimated
**28 hours** for the whole sweep, less than the flagship.

Outcomes: engagement rate, the create_post / react ratio, and whether the curve
is gradual or has a knee.

### Why it is interesting beyond the simulation

It is a claim about what memory *does socially* rather than computationally, and
it is the kind of thing that generalises past this system.

### What it needs built

`--fresh-context` already exists and is the zero arm. A windowed version is a
small generalisation of it.

---

## 3. THIRD — Does personalisation destroy the persona?

Sharpest form: a strongly personalised feed shows each agent what it already
likes, so every decision collapses to "react to what I was fed" and the persona
stops doing work. Turn personalisation down and the persona has to carry it.

**If that is right, the recommender does not amplify identity. It replaces it.**

Blocked on measurement: it needs a way to score whether prose is plausibly a
40-year-old ESTJ, which is S-2 in the deferred queue and is unsolved. Park it
until the flagship is done; the shuffled arm produces exactly the data it needs.

---

## 4. What each of these is NOT

- Not a correction of anyone else's paper. All three start from this system.
- Not a methods paper. Each has a phenomenon at its centre.
- Not dependent on scale. Every one is answerable at 36 agents, which is the
  only scale this hardware can replicate at.

---

## 5. Sequencing, if all three run

    weeks 1-2   flagship, three arms x 4 runs          12 runs, ~34 h
    weeks 3-4   memory dose-response, six arms x 3     18 runs, ~28 h
    week 5      re-analysis; persona scoring if the flagship supports it
    week 6+     whichever of the two produced the sharper result, extended

The flagship goes first because it is cheaper to interpret, because F-94 already
half-supports it, and because it produces the data the third study needs.

---

## 5b. How to price an arm

*Rewritten three times on the night of 2026-09-11. The first version asserted a
cost-versus-engagement law, refuted by its own data. The second was built on a
sweep that turned out to be truncated (B-28). This is the version that survived.*

### The one rule that matters before any of the numbers

**Start the inference server with the context length set explicitly, and verify
it.** B-28: an entire six-point sweep was run at Ollama's 4,096-token default,
every prompt was truncated, the feed was the part cut, and engagement fell from
6.8 % to 2.5 % **while the wall clock improved**. It read as a clean scaling
result for four hours.

    OLLAMA_NUM_PARALLEL=4 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=24h ollama serve

This is now enforced: `check_deps.py` fails below 8,192 and `run_simulation.py`
refuses to start and records the server's real window in every manifest. But the
habit matters more than the guard, because **a truncated run does not fail. It
gets faster and quietly stops being the experiment.**

### What is measured, at the correct context

| agents | plateau | per agent-turn |
|---|---|---|
| 12 | 276.0 s | 23.0 s |
| 24 | ~537 s | 22.4 s |
| 36 (the 9-run bank) | 793 s | 22.0 s |

**Per-agent-turn cost is flat at ~22.5 s and cost is linear in agent count.**
The exponent measured across 12-99 agents is **1.081** (R² 0.998) -- that sweep
was truncated, so read its *shape* and take the *level* from the table above.

**Round count:** a three-round ramp, then flat (F-81), and the ramp is the
context window filling (F-86). Both confirmed by B-28 from the other side: at a
4,096 window the ramp vanishes because the window fills in one round.

    wall clock  ~=  agents x rounds x ~22.5 s     after the ramp

At 36 x 15 that is the bank's observed **170 minutes**, which is the number to
budget with.

### What is NOT measured, and must not be assumed

**There is no usable cost-versus-engagement relationship.** Within a sweep,
engagement varies threefold while per-agent cost does not move. A line fitted
across families gives R² 0.595 with one point running backwards.

### The rule that survives

Price arms in **engagement events per hour**, not wall clock. F-88 is the
standing example: `--fresh-context` is three times faster, returns a third of the
engagement, and yields 1.02x the evidence per hour. **An arm that looks cheap is
usually producing less of the thing being measured** -- which is exactly what
B-28 was, accidentally.

### What that does to the two proposals above

**The flagship is unaffected and its costing stands.** Shuffling changes where
posts land, not what is shown. Budget all three arms at ~2.8 hours per run at 36
agents; twelve runs is about 34 hours.

**The memory sweep's costing in section 2 remains wrong and optimistic.** It
priced the short-memory arms as cheap because fresh-context runs in a third of
the time. It does, but F-88 shows it engages a third as much and F-95 shows it
also weakens the connection effect from 3.07 to 2.05. Those arms need more
replicates for the same precision. **Re-plan in events per hour before
committing a night to it.**

## 6. The Spark machine, when it arrives## 6. The Spark machine, when it arrives## 6. The Spark machine, when it arrives

128 GB of RAM changes which constraint binds. Today the ceiling is GPU memory:
four inference slots at 11 GB, and eight slots costs five times the variance
because the machine starts swapping. Questions to answer on day one there, in
this order:

1. **Is there a GPU, and what is it?** If Spark is CPU-only, none of the local
   optimisation work transfers — the bottleneck moves from memory bandwidth to
   cores, and the right serving stack changes.
2. **Does more RAM buy more slots?** The memory formula is `4.9 GB + 1.55 GB per
   slot`. At 128 GB that is ~79 slots by arithmetic. It will not hold — compute
   binds first — but the crossover is worth measuring, because it sets the
   maximum useful concurrency.
3. **Does vLLM run there?** Both surveyed projects use vLLM with continuous
   batching and treat 32 to 40 concurrent requests as routine. That is the single
   biggest available speedup and Ollama does not offer it.

**What to prepare now, so no time is wasted there.** The run driver already takes
concurrency as a flag and records the server's actual state in the manifest.
What is missing is an inference backend abstraction: today the Ollama URL is
threaded through directly. One interface with two implementations, Ollama and an
OpenAI-compatible endpoint, makes the move a config change rather than a port.
That is maybe a day's work and it can be done while runs are going.

---

## 7. Ideas considered and set aside

- **Ranking interventions against harmful spread.** Strong, but it requires
  building a harm model this project does not have, and it lands squarely in the
  surveyed lab's territory.
- **Activation rate as a variable.** Genuinely unexamined — one surveyed project
  activates 2 % of agents per step, the other 100 %, and neither asks whether it
  changes the conclusion. Cheap to test. Held back only because it is a
  methodological question rather than a phenomenon, and it would strengthen the
  flagship rather than stand alone.
- **The cost-of-realism frontier.** We have the only instrumented OASIS and could
  write the paper nobody else can. It is a methods contribution and reads as one.
  Better as a section of whatever else we publish than as the thing itself.
