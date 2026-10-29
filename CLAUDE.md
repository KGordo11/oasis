# CLAUDE.md: project digest (written for Claude, not for Gordon)

Distilled from all 16,451 lines of `RESEARCH_LOG.md` (read in full 2026-10-22). The log is still the record of truth,
and Gordon reads that, not this file. **Live state = log §0.2 + §14.32 "Status"**. This file holds the stable
knowledge so a new session can start work without re-reading the log. Update it when a rule, a design fact or the
code map changes. Don't paste results here: they go in the log.

## 0. Start of every session (2 minutes)
1. `cd /Users/gordon/research/oasis && bash examples/experiment/llm_bias/handoff_check.sh read` prints everything to
   read: log §0.2 top, the newest §14.x entry in full, git status + last commits. Then this file. Unrelated dirty files
   are expected and are NOT ours to commit: r001 manifest, summary_test.md, population_v2_validation.md,
   make_report_v2.py, social_timeline/make_graph.py.
2. Also run `bash examples/experiment/llm_bias/handoff_check.sh`. If it FAILs, the last session left the log behind:
   fix that first (backfill from git log + the newest §14.x) and tell Gordon.
3. Never assume a run is going or finished. Ask Gordon for the Spark output, or give him the check command (§4).

## 0b. End of EVERY change (no exceptions; 10-26: a §14.x entry alone is NOT updating the log)
1. Log: new/extended §14.x entry + a **§0.2** bullet (fix its date) + a **§14.32 Status** block + a **§14.32c** row.
2. Memory: `project_llm_bias_v2.md` dated line naming the §14.x + its `MEMORY.md` index line.
3. `bash examples/experiment/llm_bias/handoff_check.sh` must print **HANDOFF CURRENT**. Then commit by file name, push
   to `origin`.

## 1. How Gordon works (hard rules, each one learned from a real mistake)
- **Gordon runs the Spark himself.** Give numbered copy-paste commands with what he should see. Don't drive or poll
  runs over ssh. Use ssh (`ssh honda`) only for a one-off check he asks for.
- **Restate any new design and wait for his "go" before any real sim.** Building and laptop-testing code is fine.
- **Every test = V1 + exactly ONE change** (compare with V1 first, then test vs test; cross-tests last, small scale).
  `run_v2.py` enforces this (refuses >1 change without `--cross`; `--v3` is the named exception).
- **Results go in the chat as plain tables**: counts and % first (reader AI × whose posts), then derived numbers.
  No Excel or artifact unless he asks (10-21: "I want to see it here RIGHT NOW"). Explain every term where it
  appears, at 5th-grade level. **Total engagement** (all actions except do_nothing, per 100 screens) is the main
  measure, and upvotes are only detail.
- **Every run's data: CLEAN, NORMALIZE, AGGREGATE, always, before any analysis** (Gordon 10-29). Run
  `v3_clean.py <part dir>` first (writes `<dir>/clean/`). Clean = noise-floor reruns, unreadable answers and follow-up
  screens kept apart, refresh returns merged, every action marked done/failed with why. Normalize = per 100 posts read.
  Aggregate = start SMALL and merge up: each world (reader x posts_by) tick by tick (tick 0 = like V1), then each world
  all together, then baselines, then totals. Raw counts first, rates second. The gate must reproduce the published numbers.
- **Always finish with: log entry (§14.x + §0.2 + §14.32 Status + §14.32c change-history row), memory update,
  `handoff_check.sh` = HANDOFF CURRENT, commit by file name (never `git commit -a`), push to `origin` (KGordo11/oasis,
  branch `llm-bias`, NEVER `upstream`).** See §0b.
- Local models only (Ollama/llama.cpp: qwen, llama, gemma...). Never Claude/Gemini as authors or personas.
- Posts: the only rule is staying on topic. No length or format limits unless Gordon sets one.
- Don't propose work on the "refusal perform-vs-arrange" project (dormant; Gordon didn't recognise it).
- He types fast with typos; read for intent. He gets frustrated by laziness ("cmon you're being lazy") and by
  partial reading. Be thorough and concrete.

## 2. The current study: LLM Bias on the DGX Spark (Part 14 of the log)
**Question (LD-19):** if one AI writes posts and also plays the readers, do the readers favour that AI's posts?
**Answer so far: NO own-AI bias** in V1, V2 and the V3 tests; **V3 big sim part 1 (§14.53): gemma upvotes gemma's
posts** (pair ranges +9..+21, +2..+15), no total-engagement bias; **§14.57: about half of it is a comment snowball in
the live world** (none in the first 10% of the scroll; gemma follows the tone of the comments it sees). The one solid effect: **qwen engages more with gemma's
posts** (double difference qwen-gemma −17 to −21, mostly comments). It's about gemma's writing, not authorship
(survives topic × stance matching; only partly length).

**One round (LD-25, LD-40):** posting turn (an AI plays all 100 users on an empty feed; the posts become that AI's
post set) → reading turn (a reader AI plays the same 100 users; one post per screen (LD-34/37: pages kill comments);
every user reads every post of a set except their own; any number of the 27 actions per screen) → wipe (no memory,
follows or visible votes). 3 posters × 3 readers = 9 cells. **Baselines (AI reads own set) first**, then the 6 cross
cells in nested slices 16/32/64/all, then a noise floor (each AI re-reads 4 posts/user, fresh seed, `_d1` files).
**Bias for pair i,j** = (i reads i − j reads i) − (i reads j − j reads j). It's symmetric. Ranges come from
resampling users and posts. "Clear" = the 95% range excludes 0.

**Fixed setup:** qwen3:8b, llama3.1:8b, gemma3:12b (std GGUF Q4_K_M; Ollama's gemma file isn't llama.cpp-readable).
llama.cpp b11434/5e03bdd, one server per model (ports 11601/11602/11603), 8 slots × 8192 ctx (**LD-46: studies after
the V3 big sim use 16 slots, `SLOTS=16 PARALLEL=16`; part 2 stays 8**), `--jinja`, flash attn,
**one model in memory at a time** (LD-42, `MANAGE_SERVERS=1`). Uniform sampling: temp 0.7, top_k 40, top_p 0.9,
min_p 0, repeat 1.0. Thinking off except V3 qwen. 100 users `personas_v2.json` SHA `ed110626…` (Census/BLS/Pew quota
sample, Big Five, orthogonal-array stances: 20 users per stance per topic, zero correlation; 50 M / 50 F, nobody
non-binary). Topics: r/politics, r/technology, r/business, r/sports, r/entertainment (Pew top 5). Seeds are
`llm.stable_seed(SEED, round, turn, posts_by, user, post)`, so the round number decides the randomness (round 101
= V1's seeds). Run order never changes an answer.

**Versions:** V1 = rounds 101-102 (persona only). V2 = 103-104 (+ "I am Qwen3 8B, an AI model made by Alibaba,
simulating this profile:"; LD-44). V2 changed nothing about bias; llama/gemma were less active. Never pool V1 with
V2. **V3** = `run_v2.py --v3` = V1 prompts + posting line **2c** ("It's posting time: share whatever you'd post.
Everyone will read the new posts afterwards.") + reading (FINAL, Gordon 10-23, §14.49): live world (`--live`:
actions really happen, results come back as follow-up screens, private messages exist) + refresh loop + two-action
answer example (`FORMAT_TWO`, all 3 AIs), JSON ON, **qwen thinking OFF**. The menu-order study is part 2 of the big
sim, its menu ranked from part 1's data (`rank_menu.py`, `--menu-file`), run only after part 1 is examined.

**What each AI is like (stable across everything):**
- llama: ~225 actions/100 screens, 2+ actions on 70% of screens, upvotes ~61%, reports ~27% (topics it hates),
  searches the author (search_user ~17/100: dead action), long comments (slowest reader per token).
- qwen: ~110-116/100, comments a lot (~45-60%), does_nothing ~10-15%, never sends an empty list (uses do_nothing).
  Thinking (V3) adds +10 engagement and more downvotes, and is ~5-10× slower.
- gemma: **~95/100 in every test; exactly ONE action on 91% of screens**: a vote (up ~50%, down ~35%), comments only
  5-9%, empty list `[]` on ~8-10% (its way of doing nothing). Replies short (median 39 tokens). Follows stances
  strongly. Count probe (§14.48): prompt wording is a small part (2-action example: 1-action 93->85%); it's gemma's
  style ("lazy", low energy). Live world: gemma/qwen never leave the post screen; only llama looks people up and DMs.
  Nobody uses groups (~0 in all data). Posting: V1 only 23-25 users posted (it refreshes the empty feed, "waiting to see what appears"; §14.42c).
  Line 2c → 99/100 post, but always exactly 1 post. JSON mode and Google sampling change nothing (probed). Gemma 3 has
  no system role: the template folds the system text into the first user turn (correct, not a bug).
- Rerun noise (same screen + seed, llama.cpp 8 slots isn't repeatable): total engagement moves gemma ±0.6, llama
  ±2.9, qwen ±4.4 per 100. Smaller changes are not effects.

**Menu order is the biggest lever found** (r_menu: gemma upvotes 56→19% of its actions, comments 7→43%; llama
do_nothing 6→18%; qwen upvotes up). Keep V1 order fixed whenever bias is the question.

**Which of the 27 actions actually do anything in this one-screen design (§14.43 audit):** real: like/dislike post,
comment, repost, quote, report, do_nothing, create_post (posting turn). Recorded but no effect: follow, mute. Nothing
to undo: unlike/undo_dislike/unfollow/unmute. Results never shown back: search_user, search_posts, trend,
listen_from_group. Impossible: comment actions (no comments shown), join/leave/send_to_group (no groups;
the AI invents IDs). 8.6% of V1 actions were dead ones, and they count in total engagement.

## 3. Code map (`examples/experiment/llm_bias/`)
| file | role |
|---|---|
| `run_v2.py` | one turn (`post`/`read`); prompts MENU/MENU_FLIPPED/POST_SCREEN/READ_SCREEN/FORMAT; V3 flags; `changes_from_v1` guard; manifests; resumable (`load_rows` repairs a torn last line); optional OASIS `replay()` (off on the Spark) |
| `llm.py` | backends ollama/llamacpp, `chat_json(think=, json_mode=)`, `stable_seed`, `available_models()` |
| `v2_night.py` | runner. env ROUNDS STOP SLICES NOISE AGENTS PARALLEL MANAGE_SERVERS DATA_DIR EXTRA TURNS CHECKPOINT PUSH |
| `v3_big.sh` | V3 big sim, one part at a time: `ARM=1` `data/llm_bias/v3/` (ends `ARM 1 DONE`); `ARM=2` `v3_flipped/` = same posts, menu ranked from part 1's data (`rank_menu.py`), ends `ARM 2 DONE` |
| **`v3_start.sh`** | start a part safely: preflight (its settings) -> only on ALL CLEAR watchdog cron + `v3_big.sh`; `ARM=2` needs `ARM 1 DONE`, ranks the menu first, logs to `v3_big_part2.txt` (§14.50, §14.51) |
| `v3_big_summary.py <dir> [round]` | big-sim part (or V1 `v1_v2_spark r101`): analyze_v2 tables, one row per post read (all views), gate, follow-up table; writes `<dir>/summary.md` (~4 min) |
| **`v3_clean.py <dir>`** | RUN FIRST on every part: `<dir>/clean/` reads/followups/posts/actions CSVs, `by_cell_tick.csv` (every world x every tick), effort levels, retries, `cleaning.md`; gates vs published numbers (§14.60) |
| `make_v3_workbook.py <xlsx> <p1> [<p2>]`, `make_inside_v3.py <html> <p1> [<p2>]` | workbook (oasis-env) and the "Inside LLM Bias V3" page (KwhpKCngkZUmPxpWV6UEer; republish same file path or pass url); page replays each world to rebuild screens (stops if any saved screen differs); `v3_by_tick.py` = tick groups + bias by tick |
| `check_gemma_own.py <dir>`, `v3_compare_parts.py <part1> <part2>` | gemma's own-post lean by group / comment tone (§14.57); part 1 vs part 2 tables + bias (run after `ARM 2 DONE`) |
| **`handoff_check.sh [read]`** | Mac: `read` = session catch-up bundle; no arg = FAIL if log §0.2/§14.32 Status/§14.32c/memory are behind (§14.52) |
| **`speed_suite.py`**, `speed_summary.py` | speed tests on the Spark (ref + ONE change each, all 3 AIs, ~17 h; §14.59); `llamacpp_servers.sh` takes `LLAMA_BIN` / `SERVER_ARGS`; `run_v2.py --shared-first` = prompt order B |
| `slot_bench.sh` | Spark slot test (8/16/32/64 slots, each AI); only between runs; §14.54 |
| `rank_menu.py` | part 2's menu from part 1's data: least-used actions on top (§14.49) |
| `v3_test.sh`, `v3_chain.sh`, `v3_summary.py`, `v3_ranges.py`, `v3_post_lines.py`, `make_v3_charts.py` | V3 single-addition tests (done 10-21, data `data/llm_bias/v3_tests/`, not in git) |
| `v3_watchdog.sh [script log marker]` | cron restarter, gives up after 3 |
| `preflight_v2.py` | ~110 checks on the Spark, ~25 min; `EXTRA=` passes through; must end ALL CLEAR |
| `llamacpp_servers.sh start/only/stop/status` | servers; writes `~/llm_bias/env_llamacpp.sh` |
| `analyze_v2.py` (stdlib), `export_v2.py`, `make_graphs_v2.py`, `make_report_v2.py <data> <out> V1/V2/ALL`, `make_compare.py`, `make_inside_v2.py` | analysis, workbooks, Inside page (artifact E1eicdgjHpgDzex2qj18hR) |
| `audit_v2_data.py`, `gemma_probe.py`, `check_qwen_gemma.py`, `progress_v2.py` | audits/probes/progress |
| `live_world.py` | `--live` reading turn: World (OASIS rules, stdlib), ticks (others' actions visible next tick), follow-up screens, DMs; resume = re-apply rows in file order |
| `live_summary.py <dir>` | live runs: screens by kind, each action done/failed + step 1/2/3+, words typed, DMs/groups |
| **`smoke_test.py`** | **run after ANY code change, before giving Gordon a command** (~40 s, laptop or Spark): fake AIs + real code, V1 / V3 big sim / live + kill-resume, 50 checks, ends `SMOKE: ALL PASS` |
| `fake_engine.py PORT [log]` | fake llama.cpp server that answers like an AI (posts, votes, searches, groups, DMs); logs each request's think/json/menu |
| `test_llm_bias.py`, `test_live_world.py` | pytest (33 tests, no model calls); test_live_world also runs without pytest (smoke_test calls it) |
Laptop tests use `fake_engine.py` (see `smoke_test.py` for the env: `LLM_BACKEND=llamacpp LLAMACPP_URLS=...`,
`MANAGE_SERVERS=0`, a `flock` shim on macOS). Real models on the laptop: `/opt/homebrew/bin/llama-server` (build 11429)
+ `~/llm_bias_local/models/gemma3-12b.gguf` (same sha 7bb69bff… as the Spark) + Ollama blobs for qwen/llama. But
Gordon wants real runs on the Spark (10-22), and the laptop is his machine (he games on it: the GPU is shared).

Data: Spark results land in `~/llm_bias/oasis/data/llm_bias/<dir>/` → rsync to the Mac `data/llm_bias/v1_v2_spark/`
(V1+V2, fingerprint `7ace91dc41c5f431`), `v3_tests/`. File names: `posting_<model>[_aN].jsonl`,
`reading_<posts_by>__<reader>[_d1][_aN].jsonl` (+ `.manifest.json`, `.log`). Rows have `actions`, `raw`, `reason`,
`outcome` ("chose" = usable), `view` (V3 refresh loop), `thinking`.

## 4. The Spark (honda.csr.uky.edu, ARM GB10, 121 GB shared CPU/GPU memory, NFS home 100 GB quota)
- Layout `~/llm_bias/`: `oasis/` (git clone, local data commits so `git pull --no-edit` merges), `env_llamacpp.sh`,
  `engines/llama.cpp/`, `models/` (+`gguf/gemma3-12b.gguf` sha256 7bb69bff…), `logs/`. No sudo, no docker.
- Shared with user **hsa303** (training jobs ~50 GB): our speed drops 5-35×, and on 10-07/10-08 the machine ran out
  of memory (whole session killed; SSH banner timeouts). Unshared speeds s/screen: qwen 0.41-0.45, llama 0.5-0.65,
  gemma 0.95; qwen thinking ~2.5-5.
- Start detached: `setsid nohup ... < /dev/null &` (survives logout, not a reboot) + cron watchdog. Remove the cron
  after the run (`crontab -l | grep -v watchdog | crontab -`).
- **Never `git pull` on the Spark while a bash runner (`v3_big.sh`, `v3_chain.sh`) is running**: bash reads the
  script by byte offset, so changing the file under it corrupts execution (B-15 lesson).
- Mac `~/.ssh/config` has `Host honda` (ControlMaster). rsync: `rsync -avz honda:llm_bias/oasis/data/llm_bias/<dir>/ ~/research/oasis/data/llm_bias/<dir>/`.

## 5. Bug classes that keep coming back (check every new piece of code against these)
0. **Two things driving the llama.cpp servers at once** (§14.50: preflight + big sim): each `only <AI>` kills the other's
   server. Never give Gordon two server-using commands to run side by side; chain them in one script.
1. **"The system's default response to trouble is to look fine"** (B-12, B-15, B-22, B-23): a step that produces
   nothing must FAIL loudly. Checks must measure the quantity the study uses (engagement on shown posts, every post read
   once), not adjacent activity. `v3_summary.py` fails on empty data; `v2_night` stops on a 0-screen step.
2. **Silent truncation/config drift:** Ollama ctx 4096 default cut the feed (B-28); `--agents` silently truncated
   (B-26); a flag accepted but ignored (B-8); temperature not passed (B-31). Record every setting in the manifest
   and assert it.
3. **Resume and identity bugs:** half-written last line (LB-v2-4), label reused for two runs (B-27/B-35: stale
   partitions merged), post_key not unique across sets (LB-6), unlocalised bash loop var made a run silently skip
   (B-24: `local i`).
4. **Server checks:** `any()` in one try/except failed when the first server was off (LB-v2-3); `pgrep -f` inside
   `sh -c` matches itself (LB-v2-5); stop must wait for exit (LB-v2-7); the guard crashed on a cold server (B-40).
5. **Edits that didn't happen:** a scripted replace reported success but matched nothing (B-30); big-span
   replacements deleted log sections (B-29). After any scripted edit, grep for text only the NEW content has. Anchor
   on the smallest unique span.
6. **Analysis traps:** a generous judge looks self-preferring (LB-4 → double difference); clustered data needs a
   cluster bootstrap; rows/cols swapped in a dict (LF-49 correction); always reproduce a published number before
   computing a new one (B-34 gate); `agent_turns_total` vs `feed_turns` denominators (B-37).
7. **Shell (zsh on the Mac):** cwd resets between Bash calls (use `cd /abs/path && ...`); `$G` holding "git -C …"
   doesn't word-split; `mapfile` doesn't exist and `"${A[@]}"` expanded empty, so a generator wrote an empty page and
   exited 0; BSD xargs has no `-a`; `sed -i ''`; no `flock`, `timeout` or `date -d`.

## 6. OASIS internals that matter (we never edit `oasis/`; subclass or bypass)
- LLM Bias bypasses OASIS's tool-calling agent: our own JSON prompt → actions, then (optionally) `replay()` performs
  them with `perform_action_by_data` on a fresh OASIS reddit platform. gemma3 has no native tool calling, and native
  tool calling would measure tool skill, not social behaviour (§14.3).
- Groups in OASIS: `create_group(name)` (creator is the only member), `join_group` adds yourself, `send_to_group`,
  `listen_from_group`; `get_group_env` shows every agent ALL groups; no recipient field, so there's no real DM. In
  Sim 4 the group env was rendered BEFORE the feed and buried it (action rate 0.469 vs 0.812, F-14), so groups were
  off by default; 76 errors there came from `follow(group_id=)`, and only 45% of follows succeeded (Q-24, never run).
- `reference/MutiAgent4Fraud`: working DMs (`send_private_message(receiver_id, content)` → `private_message`
  table → shown in the receiver's next refresh env, turn limit → banned channel), money transfer, 7 new actions,
  old vendored OASIS (Apr 2025), drives Platform directly. `reference/MultiAgent4Collusion`: shared reflection,
  activation 0.19 (CSV says 0.02). Neither measures time; their personas are mode-collapsed.
- Other OASIS hazards: RecsysType.TWITTER = random feed; TwHIN pooler random per process; `rec` table wiped every
  round; REDDIT recsys = one global feed; `enable_like_score=True` has `pdb.set_trace`; trace `info` payloads are
  non-uniform (comment → comment_id only; quote → string id; follow → no followee).

## 7. Older work (finished; details only if asked)
- Sims 1-3 (Jul-Aug, llama3.1:8b, 36 agents): an 8B model can't narrate + tool-call in one turn; down-voted false
  posts get 62-68% pushback vs <15%; hiding votes (Shield) drops it to 28% (p=0.0009): crowd-following.
- Sim 4 (Aug-Sep 17, paused; Q-24 next): social timeline 12-99 agents; cost 21.44 s × agents × (rounds − 1.7);
  connection 3.5× > repetition 2.6× > position 2.15× > similarity 1.33×; quote actions per agent-turn across
  sizes, not engagement rate. Package `data/sim4_social_timeline/`.
- LLM Bias Tests 1-6 (Sep 23 - Oct 2, laptop Ollama, other models incl. gemma4:e2b): small own-AI lean +5 to +7 per
  100 (Test 6 +6.9, mostly gemma4), not self-recognition (shared taste); ~94% of uncertainty is which posts got
  written. These did NOT replicate on the Spark design.

## 8. Writing style for Gordon-facing text
Short sentences, plain words, numbers with units ("per 100 screens"), a table before prose, every term defined in
place. Lead with the answer. Say what was NOT checked. No "+8.4" without words ("8 more actions per 100 screens").
