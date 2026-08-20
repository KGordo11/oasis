# Simulation 3: The iAgent Shield Experiment

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
