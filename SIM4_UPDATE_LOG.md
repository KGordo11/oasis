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
- **Data explorer reviewed properly, and the Sim 4 feed mechanics with it.** Its
  *numbers* are sound — all data-driven, nothing went stale. Its *prose* is not:
  it describes the two-source pre-three-tier feed for all 13 runs including the
  nine the results rest on (**B-18**), and renders the four held-aside runs in the
  three-tier vocabulary the study relies on keeping separate (**B-19**), with an
  unknown source silently rendering as `both` (**B-20**). All three are
  presentation-only — the manifests already hold what is needed (**F-46**). The
  feed logic itself is correct; three unchecked invariants noted as **F-47**.

### In flight

- **B-18/B-19/B-20 are open and unfixed.** Fixing them means editing
  `make_graph.py` and regenerating the 5 MB explorer, which is worth doing in the
  same pass as whatever the new task adds to it rather than twice.
- The new task from the professor is not yet recorded — see §1, deliberately left
  as a stub until it is.

### Next

| # | Task | Cost | Why |
|---|---|---|---|
| — | **Awaiting definition: the professor's new task** (§1) | unknown | Set this week's direction; everything below is the standing backlog |
| 0 | **Fix B-18/B-19/B-20 and regenerate the explorer** | ~30 min, no machine time | Presentation-only per F-46. Do it in the same pass as the new task's explorer changes |
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

### 2026-09-03 (Thu) — review of the data explorer, and of the Sim 4 feed mechanics

**Trigger.** The explorer had only been skimmed on 2026-09-03 (its run list checked,
its prose not). Reviewed properly, along with the feed-construction code the explorer
claims to describe.

**Headline.** The explorer's numbers are all data-driven and correct — unlike the
write-up, nothing is a hardcoded literal, so nothing went stale when the run count
changed. **Its prose is the problem.** It describes the wrong feed for the nine runs
the study's results rest on, and relabels the four runs the study deliberately holds
apart. Recorded as B-18, B-19, B-20; the mechanics review is F-46 and F-47.

**What was checked.** All 13 embedded runs (v4_full…v10_rep6); the seven tabs
(Network, Rounds, Transcript, People, Posts, Timeline, Method & integrity); the
exposure tuple schema and its source encoding; `make_graph.py` against
`timeline_platform.py:491-737` (`refresh`, `_log_exposure`); and the run manifests
in `data/social_timeline_*.json`.

**What is sound, and worth saying.** Every figure in the explorer is computed from
the embedded per-run JSON at render time — the summary stats, the compare table, the
per-agent rows, the timeline, the integrity counters. There are no literal statistics
in its markup. This is the same property that kept the field guide's forest plot
honest while the write-up's drifted (B-17), and it is why the explorer needed no
re-figuring when the study went from five runs to nine. The B-16 disclosure ("draws
N of M interacting pairs") is present and correct.

---

### Mechanics reviewed

`timeline_platform.py:491-737` — the three-tier `refresh()` and `_log_exposure()`.
The implementation matches its documentation: tiers are network (5) > fof (3) >
discovery (4) into a fixed `feed_size` of 12, discovery backfills whatever the graph
does not supply, `explore_slots=2` of the discovery budget are a random draw from
below the top rank, and the tiers are made disjoint by B-14's author-level exclusion.
The backfill rationale (both the practical trap and the methodological confound) is
argued in-code and holds up. No defect found in the feed logic itself.

Two robustness observations that are **not** bugs today are recorded as F-47.

---

## 3. Decisions made in this phase

*Continues the build log's sequence at D-15. None yet.*

---

## 4. Findings

*Continues the build log's sequence at F-46.*

#### F-46 — Every run manifest already records which feed built it; the explorer just never reads it

`run_simulation.py:215-236` writes an `algorithm` block per run, and it is
self-describing across the two eras. The nine three-tier runs carry
`feed_model: "three-tier: network > friend-of-friend > discovery; social ties are
not interest-filtered"` plus `network_slots: 5`, `fof_slots: 3`,
`discovery_slots: 4`, `feed_size: 12`, `explore_slots: 2`. The four pre-three-tier
runs (`v4_full`…`v7_full`) carry none of those fields — only `explore_slots` and
`recency_span_rounds`. Verified across `v4_full`, `v7_full`, `v8_full`, `baseline`,
`v10_rep6`.

`make_graph.py` reads none of them. Its Algorithm box and Method tab read
`config.refresh_rec_post_count` (8), `config.following_post_count` (4) and
`config.max_rec_post_len` (30) instead — upstream knobs that the three-tier
`refresh()` never consults (`timeline_platform.py:574-631` uses the slot fields
exclusively).

**Why this matters more than it looks.** B-18 and B-19 are therefore pure
presentation defects. No re-run, no re-analysis and no new data collection is
needed to fix them — the correct values are sitting in the manifests the explorer
already loads. The presence of `feed_model` is also a ready-made discriminator:
one field decides which vocabulary and which description a run should get.

#### F-47 — Tier attribution is correct today, but rests on three invariants nothing checks

Not a bug — no incorrect row has been produced. Recorded because B-14 was already
a tier-attribution bug, so this is the part of the code with a demonstrated
capacity to be silently wrong.

1. **`fof` travels by side channel.** `refresh()` passes network and discovery
   into `_log_exposure()` as arguments but hands it `fof` through
   `self._last_fof`, an attribute on the shared platform object
   (`timeline_platform.py:667-669`). It is correct today for two independent
   reasons: `_log_exposure` is synchronous and contains no `await`
   (verified: zero `await` tokens in `:703-737`), and the platform is a
   single-consumer loop (`oasis/social_platform/platform.py:128-130`), so
   refreshes are serialised by the channel rather than run concurrently. Both are
   real; neither is stated at the call site, and either changing would corrupt
   tier labels for whichever agent lost the race. The asymmetry is the smell —
   two tiers as parameters, one as instance state.
2. **Disjointness is asserted by construction and verified by nothing.**
   `_log_exposure` labels by first match, `network` → `fof` → `discovery` →
   `unknown` (`:724-728`). B-14 was precisely an overlap — a followee's sixth post
   falling through into the fof tier, 37 exposures mislabelled in R-16. The
   priority order *masks* a recurrence of that class rather than surfacing it.
3. **`"unknown"` is reachable and unmonitored.** `:727` can emit it; no integrity
   counter tracks it. It has never fired — `SELECT source, COUNT(*) FROM
   rec_history GROUP BY source` returns only `discovery`/`fof`/`network` on
   three-tier runs and only `recsys`/`following`/`both` on pre-three-tier runs —
   but see B-20 for what the explorer would do with one if it did.

**Cheap fix for all three:** pass `fof` as a parameter; assert the three sets are
pairwise disjoint before labelling; count `unknown` in `self.stats` so it shows up
in the integrity table the Method tab already renders.

---

## 5. Bugs

*Continues the build log's sequence at B-18. B-17 was logged in the build log
because it concerned an artifact built during that phase.*

#### B-18 — The explorer describes the pre-three-tier feed for all runs, including the nine the results rest on

**Where.** Ours, `make_graph.py:686-690` (Algorithm box) and `:1250-1260`
(Method & integrity tab).

**Symptom.** For every one of the 13 runs, the Method tab states:

> "A feed is the union of **two sources**, and every exposure records which one
> delivered it: **recsys** (the ranking chose it), **following** (the viewer
> follows the author), or **both**. 8 algorithmic posts + 4 from people followed,
> ranked from a pool of 30."

For the nine three-tier runs this is wrong in every particular. The feed is
**three** tiers, not two; it is 5 network + 3 fof + 4 discovery into a fixed
`feed_size` of 12, not 8+4; `both` does not exist in that vocabulary (confirmed:
zero rows); and `fof`, which does, is not mentioned. The Algorithm box repeats the
same 8/4/30. These are the nine runs every published estimate is computed on.

**Cause.** The Method tab was written for the v4–v7 feed and never revisited when
F-25 introduced the three-tier builder. It reads config fields that still exist
but went inert (F-46).

**Why it survived.** The numbers it prints are real config values, so the tab looks
data-driven and internally consistent. Nothing is blank or obviously stale — it is
confidently describing a different experiment.

**Status.** Open. Fix is presentation-only (F-46): branch on `algorithm.feed_model`.

#### B-19 — The explorer renders the held-aside runs in the three-tier vocabulary

**Where.** Ours, `make_graph.py:942` (`SRCNAME`) and `:1111` (`SRCN`), both
`['discovery','network','fof','both','?']`; encoding at `:1384-1391`.

**Symptom.** In the People tab's per-agent exposure table and the Rounds tab's
feed-source breakdown, `v4_full`…`v7_full` exposures are labelled **discovery** and
**network**. Those runs' databases contain no such values — they hold `recsys`
(3,651 rows in v4_full), `following` (889) and `both` (157). The index collapse at
`:1389` maps `recsys`→0→"discovery" and `following`→1→"network".

**Cause.** Deliberate, and documented in the code as *"They are the same concepts
renamed, so both vocabularies map to one index set and runs from either era stay
readable side by side."*

**Why that reasoning does not hold.** The study's own argument contradicts it. The
write-up excludes these runs from every estimate and then presents their pooled
**OR 5.00 [3.83, 6.52]** as an *independent replication* — evidence that carries
weight *because* the feed builder is structurally different, not a renaming. The
build log holds them apart for the same reason. Displaying their exposures under
three-tier names erases, in the artifact, the very distinction the headline
evidence depends on.

It is also the exact failure class as the retracted F-38: a column shown under a
name that is not what it holds. That one stood for a week.

**Status.** Open. Fix is presentation-only (F-46): pick the label set per run from
the presence of `algorithm.feed_model`.

#### B-20 — An unrecognised feed source would silently render as "both"

**Where.** Ours, `make_graph.py:1389` — `SRC.get(e.get("source"), 3)`.

**Symptom.** The default index for an unknown source string is **3**, which
`SRCNAME`/`SRCN` render as `"both"` — a plausible-looking label borrowed from the
pre-three-tier vocabulary. Index **4** (`'?'`), the slot that exists precisely to
mean "unrecognised", is unreachable: nothing ever produces it.

**Why it is live rather than theoretical.** `_log_exposure` can emit the string
`"unknown"` (`timeline_platform.py:727`) whenever a shown post is in none of the
three tier sets. It has never fired, so no wrong row exists today. But the two
halves are already in place: the writer can produce a value the reader will
mislabel, and it will mislabel it as a real category rather than as an error.

This is the project's own catalogued OASIS failure mode — fail silently, produce
quietly meaningless data (see the five upstream bugs in the build log §15) —
reproduced in our code.

**Status.** Open. One-line fix: default to `4`, and count `unknown` in
`self.stats` per F-47 so it surfaces in the integrity table.

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
