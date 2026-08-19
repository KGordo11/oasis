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
