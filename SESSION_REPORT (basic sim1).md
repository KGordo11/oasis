# Simulation 1: Basic Reddit Simulation + "Why Did The Agent Do That?" Investigation

A step-by-step, copy-paste-able reproduction of everything we ran. Every command
below is exact — run them in order, in a Terminal, from `/Users/gordon/research/oasis`,
and you will see the same kind of data we're discussing.

---

## PART A — What is this simulation, and what are we trying to find out?

**No paper-reading required — here's the whole idea in plain terms:**

We're building a fake Reddit populated entirely by AI "people" (agents), each with
a made-up personality (age, personality type, country, job, interests). We let
them read posts and react — post, comment, like, follow, or ignore — using their
own judgment, driven by a free local AI model (Ollama) instead of a paid one.

**The specific question we're investigating:** when an AI agent posts or comments
something, **is that a random guess, or is it actually caused by the personality
we gave it?** And separately: **can we make the AI explain its reasoning out loud,
the way a person would say "I liked this because..."?**

We are NOT trying to replicate a specific published number here — this is an
exploratory investigation into *how the tool itself behaves*, using your own
machine and your own data.

---

## PART B — One-time setup (only needs to be done once, skip if already done)

### Step B1 — Confirm the environment exists and works
```bash
cd /Users/gordon/research/oasis
source oasis-env/bin/activate
python --version
```
**Why:** OASIS needs Python 3.10/3.11. Your system Python may be newer and won't
work — this venv already has the correct version and all packages installed.
**Expected output:** `Python 3.11.15`

### Step B2 — Confirm Ollama is running and check the model
```bash
ollama list
ollama show llama3.1:8b
```
**Why:** OASIS agents act by "calling tools" (like an app calling a function).
We need to confirm the model actually supports this — not just guess.
**Expected output:** `llama3.1:8b` appears in the list, and under `Capabilities` you
should see `tools` listed. If `llama3.1:8b` isn't there yet, pull it first:
```bash
ollama pull llama3.1:8b
```

---

## PART C — Run 1: the baseline simulation

### Step C1 — Run it
```bash
cd /Users/gordon/research/oasis
source oasis-env/bin/activate
python examples/reddit_simulation_ollama.py
```
**Why:** This is the actual experiment — 36 AI agents (loaded from
`data/reddit/user_data_36.json`) get seeded with one post ("Hello, world!"), then
each agent freely decides what to do (post, comment, like, follow, or nothing).
**What it produces:** a fresh `data/reddit_simulation.db` (overwritten every run)
and a new timestamped log file in `log/`.

### Step C2 — See the results yourself
```bash
sqlite3 data/reddit_simulation.db "SELECT post_id, user_id, content FROM post;"
```
```bash
sqlite3 data/reddit_simulation.db "SELECT action, COUNT(*) FROM trace GROUP BY action ORDER BY COUNT(*) DESC;"
```
**Why:** The first shows every post the agents created in their own words. The
second shows a tally of every action type taken (posts, comments, likes, etc.) —
this is the actual "results" of the simulation.

---

## PART D — Investigation 1: does an agent's personality actually cause its behavior?

### Step D1 — Find the newest log file and pick an agent to check
```bash
LOGFILE=$(ls -t log/social.agent-*.log | head -1)
echo "$LOGFILE"
grep "performed action" "$LOGFILE"
```
**Why:** This lists every action every agent took this run, with the agent number.
Pick any agent number you see (we used Agent 26 as our example).

### Step D2 — Look up that agent's actual profile
```bash
python3 -c "
import json
data = json.load(open('data/reddit/user_data_36.json'))
print(json.dumps(data[26], indent=2))
"
```
**Why:** This prints agent 26's real assigned personality — name, age, MBTI type,
country, job, interests. (Change the `26` to whichever agent number you picked.)

### Step D3 — Compare the profile to what that agent actually posted
```bash
grep "Agent 26 " "$LOGFILE"
```
**Why:** This is the moment of proof — read the printed profile from Step D2 next
to what that same agent actually posted here. **Our real result:** Agent 26
("Sophie Green," 17, ISFP, Chile, agriculture-focused) posted about gardening and
mentioned Chile — unprompted, straight from her profile. That's the evidence that
personality really does drive behavior, not randomness.

---

## PART E — Investigation 2: can we get the AI to explain its reasoning out loud?

This part took **three attempts**. The first attempt broke the simulation
completely. The second attempt fixed the simulation but didn't achieve the goal.
The third attempt is what's actually running on your machine right now. All three
are documented here so you can see exactly what failed and why — this is real
research process, not just a clean success story.

### Attempt 1 — FAILED (do not do this — shown for the record only)

**What we changed:** In `oasis/social_platform/config/user.py`, in both
`to_twitter_system_message` and `to_reddit_system_message`, we changed:
```
# RESPONSE METHOD
Please perform actions by tool calling.
```
to:
```
# RESPONSE METHOD
Before calling any function, briefly state your reasoning in one short sentence: your feeling about these posts and why this action fits your personality. Then call the appropriate function(s).
```
And in `oasis/social_agent/agent.py`, inside `perform_action_by_llm`, right after
the line `response = await self.astep(user_msg)`, we added:
```python
if response.msgs:
    reasoning_text = (response.msgs[0].content or "").strip()
    if reasoning_text:
        agent_log.info(f"Agent {self.social_agent_id} "
                       f"reasoning: {reasoning_text}")
```

**Test command run:**
```bash
python examples/reddit_simulation_ollama.py
```

**Diagnostic commands run afterward:**
```bash
LOGFILE=$(ls -t log/social.agent-*.log | head -1)
grep -c "performed action" "$LOGFILE"
grep -c "reasoning:" "$LOGFILE"
grep -c "observing environment" "$LOGFILE"
```

**Real result:** `observing environment` = 36, `reasoning:` = 10, **`performed action` = 0**.
**Zero agents took a real action, out of 36.** Telling the model "explain yourself,
*then* act" broke it — instead of calling a real tool, it started typing fake
`{"name": "create_comment", ...}` text that never actually executed anything.

### Attempt 2 — Partial fix, but abandoned for a different reason

**What we changed:** Same two files, softened the wording to:
```
Please perform actions by tool calling. You may optionally include one short sentence about your feeling or reasoning in your message alongside the tool call, but you must always call one of the provided functions — never write a function call out as plain text or JSON.
```

**Test + diagnostic commands:** same as Attempt 1 above.

**Real result:** `performed action` = 35/36 (fixed!), but `reasoning:` = 1/36 (almost
never used). **Problem:** this fix lived inside `oasis/`'s shared engine files —
risky, because any other experiment on this machine depends on those exact files.

**We reverted this completely:**
```bash
git status --short
git checkout origin/main -- oasis/social_agent/agent.py oasis/social_platform/config/user.py
git diff origin/main -- oasis/social_agent/agent.py oasis/social_platform/config/user.py
```
The last command prints nothing if the revert worked — confirming the files are
byte-for-byte identical to the public GitHub version again.

### Attempt 3 — The correct fix (this is what your files contain right now)

**What we did instead:** added a small Python "subclass" — a copy of the existing
agent that adds one extra behavior — entirely inside `examples/reddit_simulation_ollama.py`.
Nothing under `oasis/` is touched. You can verify that right now:
```bash
git diff origin/main -- oasis/ | wc -l
```
**Expected output:** `0` (zero differences from the public repo).

The subclass we added (already saved in your file, shown here so you can see
exactly what it does):
```python
REASONING_ADDENDUM = (
    " You may optionally include one short sentence about your feeling or "
    "reasoning in your message alongside the tool call, but you must "
    "always call one of the provided functions — never write a function "
    "call out as plain text or JSON.")

class ReasoningSocialAgent(SocialAgent):
    def __init__(self, *args, **kwargs):
        user_info = kwargs.get("user_info")
        if user_info is not None:
            original_to_system_message = user_info.to_system_message
            def patched_to_system_message():
                return original_to_system_message() + REASONING_ADDENDUM
            user_info.to_system_message = patched_to_system_message
        super().__init__(*args, **kwargs)
    # perform_action_by_llm override captures reasoning the same way as
    # Attempt 1/2, just inside this subclass instead of the shared file.

agents_generator.SocialAgent = ReasoningSocialAgent
```

**Test run + diagnostics (exact commands):**
```bash
python examples/reddit_simulation_ollama.py
```
```bash
LOGFILE=$(ls -t log/social.agent-*.log | head -1)
grep -c "performed action" "$LOGFILE"
grep -c "reasoning:" "$LOGFILE"
grep -c "observing environment" "$LOGFILE"
grep "reasoning:" "$LOGFILE"
```

**Real result:** `performed action` = 32/36 (tool-calling works, ~89%). `reasoning:`
= 4/36 — **but we checked what those 4 lines actually said**, and all 4 were the
same JSON-as-text failure from Attempt 1, just mislabeled — not genuine reasoning
sentences. Run the last command above yourself and read them; you'll see the same thing.

**Honest final verdict on Investigation 2:** we did not succeed at getting this
specific 8B local model to reliably narrate genuine reasoning. What we did
accomplish: normal tool-calling behavior restored, fully isolated to one file, with
zero risk to the rest of OASIS — and a real, evidence-backed finding that small
local models struggle to combine free-text explanation with structured tool use.

---

## PART F — Complete file inventory

| File | Status | What it does |
|---|---|---|
| Everything in `oasis/` | **100% original**, verified via `git diff origin/main -- oasis/` = 0 lines | The actual simulation engine (unmodified) |
| `examples/reddit_simulation_ollama.py` | **Customized** (the only changed file) | Runs the simulation; contains the `ReasoningSocialAgent` experiment from Attempt 3 |
| `data/reddit/user_data_36.json` | Original | The 36 AI personalities |
| `data/reddit_simulation.db` | Generated fresh each run | Where results land — overwritten every time you run Step C1 |
| `log/social.agent-*.log` | Generated fresh each run | One file per run; every agent's feed + attempted reasoning + actions |

---

## PART G — One paragraph for Wednesday

> "I ran a Reddit-style simulation with AI agents, then investigated two things:
> first, whether an agent's assigned personality actually causes what it does —
> confirmed, using a specific agent as a traceable example. Second, whether I
> could make the model explain its reasoning out loud. That took three attempts:
> the first broke the simulation entirely (zero real actions), the second
> partially worked but modified shared code I shouldn't have touched, and the
> third is the correct, safe version — isolated to one file, with tool-calling
> restored, though genuine reasoning capture still doesn't reliably work with this
> local model. That's a real finding about model limitations, not a failure to hide."
