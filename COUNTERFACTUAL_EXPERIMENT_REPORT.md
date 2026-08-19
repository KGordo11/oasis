# Simulation 2: The Up/Control/Down Misinformation Experiment

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
