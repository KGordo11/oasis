# Simulation 4 — Update Log

**What this document is.** The running record of work on Simulation 4 *after* the
build was complete. `SIM4_BUILD_LOG.md` records how the thing was built and what
the nine analysed runs established; this file records everything done to it since,
week by week, in the same conventions.

**Why it is separate.** The build log had grown past 2,900 lines and its §0 STATUS
was doing two jobs at once — describing a finished study and tracking live work.
Splitting them keeps the build log a stable reference and gives ongoing work a
place to accumulate without burying it.

**Related documents**
- Build log: `SIM4_BUILD_LOG.md` — environment, sources, the three results, F-1..F-45, B-1..B-17, D-1..D-14, R-1..R-24, Q-1..Q-15
- Design spec: `docs/superpowers/specs/2026-08-24-social-timeline-design.md`
- Project-wide running log: `PROJECT_LOG.md`
- Prior simulations: `SESSION_REPORT (basic sim1).md`, `COUNTERFACTUAL_EXPERIMENT_REPORT(sim 2, groups).md`, `SHIELD_EXPERIMENT_REPORT.md`

---

## Conventions

Identical to the build log, and the id sequences **continue** rather than restart —
so a search for any id lands in exactly one place across both files:

| Kind | Build log holds | This log starts at |
|---|---|---|
| Findings `F-n` | F-1 … F-45 | **F-46** |
| Bugs `B-n` | B-1 … B-17 | **B-18** |
| Decisions `D-n` | D-1 … D-14 | **D-15** |
| Runs `R-n` | R-1 … R-24 | **R-25** |
| Open questions `Q-n` | Q-1 … Q-15 | **Q-16** |

Other rules carried over unchanged:

- Every claim about OASIS behavior cites `file:line` so it can be re-verified.
- Reversed decisions are struck through and kept, never deleted — the reasoning
  behind a wrong turn is worth as much as the correction.
- Each id is its own heading whose title states the claim, so searching an id
  lands on a sentence rather than a cross-reference.
- A pooled estimate is never reported without its per-run breakdown (F-40).
- A null is never reported without its MDE (F-35).
- Judge any change against **baseline**, never against the previous run.

---

## 0. STATUS — read this first when resuming

*Last updated 2026-09-03. Update this section at the end of every working session.*

**Week of 2026-08-31 (week 1 of updates). Nothing is mid-flight; no run in
progress; working tree clean at `5359411` on branch `social-timeline-sim`.**

### Where the study stands

Unchanged from the build log: three results over 9 runs / 54,444 exposures —
connection beats content (network vs discovery **OR 3.51** [3.06, 4.04], 9/9 runs),
repetition beats both (**OR 2.62** [2.18, 3.15], 8/9 runs), and a cross-run noise
floor of ~28 pp that swamps every prompt intervention tried. F-38 remains
**retracted**. See `SIM4_BUILD_LOG.md` §0 for the full statement.

### Done this week

- **Both artifacts re-figured from 5-run to 9-run numbers** and republished. See
  the 2026-09-03 entry below. One claim changed in substance, not just value; two
  numbers were wrong rather than stale; one chart was drawing superseded estimates
  under current labels (**B-17**).

### In flight

- **Nothing yet.** The new task from the professor is not yet recorded — see
  §1 below, which is deliberately left as a stub until it is.

### Next

| # | Task | Cost | Why |
|---|---|---|---|
| — | **Awaiting definition: the professor's new task** (§1) | unknown | Set this week's direction; everything below is the standing backlog |
| 1 | **A designed repeat-exposure run** (Q-15): re-inject a fixed post set at controlled intervals | ~1 run (2 h) | The top standing item. F-44 made repeat exposure the best-evidenced effect (OR 2.62, 8/9 runs); only assignment can make it experimental |
| 2 | Optional: a `follow`-targeted designed experiment | ~1 run | F-36 — `follow` has ICC 0.000, ~35 agent-pairs for 5 pp |
| 3 | Open, unexplained: 14 of 21 actions never fire (Q-11) | unscoped | Limits any claim about the action surface being exercised |
| 4 | Open, unexplained: F-24, ~32% of posts echo the author's own bio (Q-12) | unscoped | Per F-35 do **not** attack it with prompt tweaks |

**Do not** run another prompt-intervention experiment at 36 agents. F-35 shows it
cannot resolve anything at this scale.

---

## 1. This week's task — from the professor

*Meeting: week of 2026-08-31. **Not yet recorded.***

> **STUB — fill this in before starting work.** Record here, in the professor's
> own framing rather than a paraphrase: what he asked to be *looked at*, what he
> asked to be *confirmed*, and anything he pushed back on. "Confirm" and
> "investigate" imply different work and different standards of evidence, so
> keep them separate.

**What he asked us to look at.**
_(pending)_

**What he asked us to confirm.**
_(pending)_

**What this implies for method.**
_(pending — but note in advance: anything framed as "confirm X" on the existing
nine runs is a re-analysis and costs no machine time; anything requiring a new
condition costs ~2 h per run and must be judged against baseline with `compare.py`
so the correction and MDE are reported automatically.)_

---

## 2. Chronological log

Newest last. Every session gets an entry, even one that produced nothing.

### 2026-09-03 (Thu) — both artifacts still carried five-run numbers

**Trigger.** Read the three published artifacts end to end to re-establish context
before starting the week. The write-up, the field guide and the data explorer.

**What was wrong.** When R-21..R-24 took the study from five runs to nine on
2026-09-02, the *headline* figures in both prose artifacts were updated and the
rest was not. Roughly thirty stale values across the two documents, in three
categories:

1. **Substantive.** The write-up claimed cosine is null "inside every one of the
   eight recency levels thick enough to fit". On nine runs that is false — level
   0.857 (n=6,670) returns **OR 3.14 [1.26, 7.87], p=0.014**. It is positive
   rather than negative, uncorrected across eight tests, and not reproduced at any
   other level, so it is *not* evidence that similarity works. But the sentence as
   written could not stand and was rewritten to say what the data says.
2. **Wrong, not merely stale.** §04 said "86 distinct posts get this far" in a
   table and "81 distinct posts are ever shown a sixth time" in the paragraph under
   it — two different numbers for the same quantity, neither correct. Computed
   directly from the nine databases via `recency_check.load_scored_exposures`:
   **39**, for both readings (`seen_posts[k+1] ⊆ seen_posts[k]`, so the union at
   `prior>=5` is just the `prior=5` set).
3. **Stale values.** cosine 1.544 → **1.143** [0.524, 2.495] p=0.74; blended score
   0.305 → **0.267**; recency 0.176 → **0.120**; fof 1.97 → **2.34** and "1 of 4"
   → **"3 of 7"**; network feed-only 11.07 → **12.76** and slot-fixed 3.54 →
   **3.51**; the full cosine decile table; tier exposure counts (6,396/3,022/20,822
   → 11,459/5,317/37,668); round-1 and round-14 rates (5.65/1.86 → **5.56/1.35**);
   mean cosine 0.798 → **0.796**; minimum cosine 0.198 → **0.212**; decision count
   30,240 → **54,444**; run count 20 → **24**; and the explorer described as
   9-run when it in fact carries **13**.

**B-17 — the forest plot was drawing the old estimates.** Recorded in the build
log's bug ledger. Its four unchanged bars were *positioned* at the superseded
5-run values while their printed labels read the current ones. Decoding the
published `left`/`width` percentages against the plot's own log axis recovers
3.55 / 1.97 / 2.13 / 2.33 — exactly the old numbers. The labels had been edited;
the hand-written CSS geometry had not.

**How it was caught.** Not by reading. By recomputing every bar's position from
the axis calibration (`pos(x) = (log10(x)+1) × 45.35`, derived from the plot's own
0.1 / 0.3 / 1 / 3 / 10 ticks) and comparing against the printed labels. The check
was written to verify one hand-edited bar and incidentally caught four that
nobody had touched.

**Generalisation worth keeping.** The field guide's equivalent forest plot builds
its geometry from a data array and was internally consistent throughout; the
write-up's stores each position as a literal and drifted silently. Same content,
same week, two implementations — one self-checking, one not. **Prefer derived
geometry for any chart whose numbers get re-estimated.**

**Also corrected.** `SIM4_BUILD_LOG.md` §0: "20 runs" → **24** (R-1..R-24), and
the explorer relabelled from "9-run" to 13-run.

**Verification.** All five forest rows recomputed from `exposure_model.py` /
`recency_check.py` output and checked programmatically against the axis scale —
max placement error **0.05%**. Both artifacts diffed against their live versions
before publishing; only intended changes present.

**Artifacts republished** (same URLs, so links already circulated still resolve):
- Write-up — https://claude.ai/code/artifact/55d7c5a5-4a69-406c-bc4f-8f14a94f710b
- Field guide — https://claude.ai/code/artifact/b878972f-ab95-4d0c-ba12-e1b1684467ba

**Commit.** `5359411` — *Sim 4: both artifacts still carried five-run numbers (B-17)*

**Cost.** No machine time. No run started.

---

### 2026-09-03 (Thu) — this update log created

Split ongoing work out of `SIM4_BUILD_LOG.md`, which had reached ~2,950 lines and
whose §0 STATUS was tracking live work and describing a finished study at the same
time. Id sequences continue rather than restart (see Conventions) so cross-file
search still resolves to exactly one entry.

Awaiting the professor's task before the week's substantive work begins.

---

## 3. Decisions made in this phase

*Continues the build log's sequence at D-15. None yet.*

---

## 4. Findings

*Continues the build log's sequence at F-46. None yet.*

---

## 5. Bugs

*Continues the build log's sequence at B-18. B-17 was logged in the build log
because it concerned an artifact built during that phase.*

---

## 6. Run ledger

*Continues the build log's sequence at R-25. No runs this phase.*

| Run | Config | Outcome | Wall clock |
|---|---|---|---|
| — | — | no runs yet this phase | — |

---

## 7. Open questions

*Continues the build log's sequence at Q-16. Q-11, Q-12, Q-13 and Q-15 remain
open in the build log and are not restated here.*
