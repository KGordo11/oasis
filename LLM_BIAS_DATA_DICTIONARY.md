# LLM Bias — data dictionary

Every file the LLM Bias project produces, and every column in it, in plain
words. Design v2 (the scrolling shared world, from 2026-09-24) is first; design v1
(night 1, pick-a-favourite with 7 models) is at the end.

**To rebuild every table from the raw records:**

    ./oasis-env/bin/python examples/experiment/llm_bias/export_world.py

---

## Words used below

- **User / persona** — one of the 99 pinned people (ids 0–98). The same 99 in
  every run, verified by fingerprint `964462b96652` before any run starts.
- **Controlling model** — the AI model that plays a user in a given world: it
  reads the user's personality and decides what that user does.
- **Author model** — the AI model that wrote a post.
- **Same model** — 1 when the post was written by the model controlling the
  user. The whole hypothesis is about these rows: are they liked more?
- **Post set (seed)** — one fresh batch of 50 posts: 2 models × 5 topics × 5
  posts. Every seed is a new batch; the same seed always means the same posts.
- **World** — one OASIS platform where all 99 users scroll one post set. World 0:
  even-numbered users are controlled by llama3.1, odd-numbered by gemma4.
  World 1: swapped. After both, every user has been played by both models on the
  same posts.
- **Round** — one world, numbered in the order it ran (round 1 = the first world
  of the campaign). One round = 99 users × 50 posts = 4,950 decisions.
- **Slot** — the 5 posts per topic are 5 slots. In each slot, both models wrote a
  post from the identical brief (same subject, post type and poster), so the
  pair differs only by which model wrote it.
- **Interest** — how much a user cares about a topic: −2 dislikes, −1 bored,
  0 indifferent, +1 enjoys, +2 loves. Fixed per user.

---

## Design v2 tables — `data/llm_bias/export/`

### `reactions.csv` — one row per user per post

The main table: what every user did with every post.

| column | meaning |
|---|---|
| `round` | which round (world), in the order they ran |
| `world_label` | the run's folder name under `data/llm_bias/worlds/` |
| `post_set_seed` | which batch of 50 posts |
| `world` | 0 or 1 — which way round the users were split between models |
| `user_id` | the user's number, 0–98 (same person in every run) |
| `username`, `user_name` | the user's handle and name |
| `controlling_model` | **the model controlling this user** for this reaction |
| `post_uid` | **the post's unique id across all post sets**: `s<seed>\|r<slot-1>\|<topic>\|<author model>` |
| `post_key` | the post's id within its post set (repeats across sets — use `post_uid` to join or count) |
| `oasis_post_id` | the post's id inside that world's OASIS database |
| `post_author_model` | **the model that wrote the post** |
| `same_model` | 1 if the author model is the controlling model, else 0 |
| `topic` | the post's topic |
| `user_interest_in_topic` | −2 … +2, see above |
| `topic_order` | 1 = the first topic this user scrolled (their best-loved), 5 = the last |
| `position_in_topic` | 1–10: where the post came in that topic's scroll |
| `scroll_position` | 1–50: where the post came in the user's whole scroll |
| `action` | **`like`, `dislike`, `nothing`** (no vote, kept scrolling), or `FAILED` (no readable answer after 3 tries) |
| `reason` | the user's few words of reasoning, in their own voice |
| `seconds` | **how long this one decision took**, from sending the post to the model to getting its answer. Four decisions run at once on the chip, so these overlap: the run as a whole moves about 4× faster than this number suggests (see `world_timing.csv`) |
| `prompt_tokens` | length of what the model read (personality + post), in tokens (~¾ of a word) |
| `output_tokens` | length of the model's answer, in tokens |
| `attempts` | 1 normally; 2–3 if the first answer was unreadable and was asked again |
| `outcome` | `chose` (a readable answer), `unreadable`, `cut_off` (hit the length limit), or `timeout` |
| `stop_reason` | why the model stopped writing: `stop` = finished normally, `length` = hit the limit |

### `posts.csv` — one row per post

| column | meaning |
|---|---|
| `post_uid` | unique id across all post sets (join key to reactions.csv) |
| `post_key` | id within its post set |
| `post_set_seed`, `topic`, `subreddit`, `slot` | where the post belongs |
| `author_model` | **who wrote it** |
| `oasis_post_id` | id inside the OASIS database |
| `post_type`, `subject`, `poster_voice` | the brief both models were given for this slot |
| `title`, `body` | the post as users saw it (plain text) |
| `words` | length of the body |
| `generation_seconds`, `generation_attempts` | how long writing it took, and how many tries |
| `like_by_<model>_users`, `dislike_by_<model>_users`, `nothing_by_<model>_users` | how many users controlled by each model liked / disliked / ignored it, summed over every round that used this post |

### `users.csv` — one row per user (the 99 pinned personas)

| column | meaning |
|---|---|
| `user_id`, `username`, `name`, `age`, `gender`, `place`, `profession` | who they are |
| `voting_style` | `generous`, `typical` or `harsh` — part of the personality text |
| `interest_<topic>` | −2 … +2 for all 15 topics |
| `controlled_by_round_<n>` | **which model controlled this user in round n** |
| `persona_text` | the exact personality text the model was given |

### `world_timing.csv` — one row per round per model

| column | meaning |
|---|---|
| `round`, `world_label`, `post_set_seed`, `world` | which round |
| `model` | the controlling model |
| `users` | how many users that model controlled in that round |
| `decisions` | users × posts |
| `minutes` | wall-clock time that model took to get all its users through all posts |
| `seconds_per_decision` | `minutes × 60 ÷ decisions` — the throughput number |
| `posts` | posts in the world (50) |
| `started_at`, `finished_at` | when the round began and ended |

### `progress_timing.csv` — the time-vs-agents data

One row every 250 decisions (= every 5 users), read from each run's log.

| column | meaning |
|---|---|
| `round`, `world_label`, `model` | which run and model |
| `decisions_done` | decisions finished so far |
| `elapsed_s` | seconds since that model started |
| `users_done_equiv` | `decisions_done ÷ 50` — how many users' worth of scrolling is done |
| `personas_in_run` | users this model controls in the run |

---

## Raw records — `data/llm_bias/worlds/<world_label>/`

| file | what it is |
|---|---|
| `decisions.jsonl` | one line per decision, written the moment it happens: everything in `reactions.csv` plus the model's raw reply text and any errors. Source of truth |
| `manifest.json` | the run's settings (models, seed, world, persona fingerprint and ids, parallelism, temperature), per-model timing and action counts, start/finish times, machine |
| `run.log` | human-readable progress (ignored by git; its timings are copied into `progress_timing.csv`) |
| `oasis.db` | the OASIS reddit database: `user`, `post`, `like`, `dislike` and `trace` tables. Likes and dislikes are real OASIS actions. Not committed (rebuilt by re-running); "nothing" is not stored here, only in `decisions.jsonl` |

Post banks: `data/llm_bias/postbank_s<seed>.jsonl` — every post ever generated
for that seed, with the raw model output, the brief, attempts and timing.
Analysis: `data/llm_bias/analysis_v2.txt` / `.json` (refreshed after every post set).
Only **finished** worlds are exported, and the analysis counts a post set only when **both** of its rotation
worlds are finished (a half-done set has one model's people only). A world that was paused and resumed keeps
all its reactions, but its `world_timing.csv` minutes cover only the part after the restart (compare
`decisions` with users x 50); the page's timing charts leave such rounds out.

Exploration: `data/llm_bias/explore_v2.json` (numbers behind the page's "What else we found": self-preference by
topic and by whether the person cares, same-person agreement, per-post agreement, post length, scroll position,
persona traits, reasons) and `explore_v2_posts.csv` (one row per post: like rate among people who care about the
topic, separately for llama-played and gemma-played people, plus author, topic, words). Made by `explore_world.py`;
exploratory, complete post sets only.

Page data: `world_data.js`, written next to the page by `make_world_artifact.py` and published with it. It is
reactions.csv/posts.csv/users.csv packed for the look-up tool: `posts` (s = post set, t = topic, a = author 0 llama /
1 gemma, ti = title, b = body, w = words, k = kind of post), `users` (i = id, n = name, age, g = gender, pl = place,
job, st = voting style, in = interest -2..+2 per primary topic, d = the exact persona text), `reasons` (every
distinct reason once) and `R` = one row per reaction `[post index, user id, playing model 0/1, action 0 like /
1 dislike / 2 nothing, reason index, seconds]`.

---

## Design v1 (night 1) — `data/llm_bias/runs/<label>/decisions.jsonl`

7 models, pick-a-favourite. One line per user per round: `judge` (controlling
model), `shown_keys` / `shown_authors` (the 7 posts in the order shown),
`favorite_key` / `favorite_author` (the one picked), `votes` (up/down/none per
post), `reason`, `latency_s`. Per-round timings are in each run's `manifest.json`
under `rounds` (`wall_s`, `s_per_decision`). Summaries in
`data/llm_bias/analysis_s<seed>.txt`.

---

## A/B test (LD-13, post sets 20-34) — `data/llm_bias/export_ab/`

Same tables as `export/`, made by `export_world.py --prefix ab_ --out data/llm_bias/export_ab`, for the 60
A/B worlds (`ab_s<set>_<scroll|pair>_w<world>`). Posts were written under the length rule "ask 75-85 words,
reject outside 65-95, up to 9 tries" (`length_rule` in each post-bank record); a brief with a missing post was
dropped from all four worlds of its set (`--complete-slots`). 50 people (first 50 of the pinned 99).

Extra columns in `reactions.csv` (also present, mostly empty, in `export/`):

| column | meaning |
|---|---|
| `format` | `scroll` = one post per decision; `pair` = the two posts of one brief shown side by side |
| `side_by_side_position` | pair only: 1 or 2, where this post appeared on screen (order shuffled per person and brief) |
| `picked_as_favourite` | pair only: 1 if the person picked this post as the one they'd most want to open, else 0 |

In `pair` rows, `seconds`, `prompt_tokens` and `output_tokens` belong to the whole call (both posts), so they
repeat on the two rows of that call. `world_timing.csv` has `format` and `calls` (a pair call covers 2 posts).
`posts.csv` counts are split by format: `like_by_<model>_users_<format>` etc.

Analysis: `data/llm_bias/analysis_ab.json` (`analyze_ab.py`: per-format double differences, the favourite
double difference, and the format effect = pair − scroll, all from one shared people x brief bootstrap).
Checks: `data/llm_bias/ab_checks.txt`.

## Three AIs, natural posts (LD-14, post sets 40+) — `data/llm_bias/export_v3/`

Worlds `v3_s<set>_w<0|1|2>`: llama3.1:8b, gemma4:e2b and mistral:7b each write posts and play people; person i is
played by `judges[(i + world) % 3]`, so three worlds per set give every person every AI. Posts are "natural":
no length or format rules, only the topic brief and "don't mention AI / don't sign" (`length_rule: "natural"`).
Same table layout as `export/`, three models instead of two. Analysis: `data/llm_bias/analysis_v3.json`
(`analyze_world.py --prefix v3_`); checks `data/llm_bias/v3_checks.txt`.

## Two AIs, 100 users, new posts every round (LD-18, from 2026-09-30) — `data/llm_bias/two_ai/`

**Rebuild:** `./oasis-env/bin/python examples/experiment/llm_bias/analyze_two_ai.py` (re-run after every round;
`two_ai_after_round.sh` does it automatically, with 1,000 bootstrap draws instead of 2,000).

Words specific to this test:
- **AI A / AI B** — gemma4:e2b and gemma3:1b. Each one writes posts AND plays users.
- **Round** — here, one fresh batch of 50 posts (post seed 200 + round) plus two worlds on it:
  `two_rNN_gemma4` (gemma4 plays ALL 100 users) and `two_rNN_gemma3` (gemma3 plays the same 100 users on the
  same posts, same order). A round = 100 users × ~50 posts × 2 AIs ≈ 10,000 votes. Rounds are independent.
- **The 100 users** — the pinned 99 (ids 0-98) plus id 99 of the same bank; fingerprint `f51d2b0a1f7d`
  (`personas.core100()`), checked before every run.
- **Brief** — the angle + post type + poster voice both AIs get for one slot. Numbered across the whole campaign
  so no brief is ever reused (all 12 angles used before one repeats; each slot has its own post type × voice pair).
- **Own-AI post** (`own_ai_post`) — 1 when the post was written by the AI playing the user.

### `reactions.csv` — one row per vote (user × post × AI playing the user)
| column | meaning |
|---|---|
| round, seed | round number (1-15) and its post seed (201-215) |
| label | the world the vote happened in (`two_rNN_<ai>`) |
| played_by | the AI controlling the user for this vote |
| user_id, username, voting_style | which of the 100 users (0-99), their handle, their fixed voting habit |
| affinity | the user's fixed interest in this subreddit, −2 … +2 |
| topic, topic_rank, pos_in_topic | subreddit; where it came in the user's scroll (0 = favourite subreddit first); position of the post inside that subreddit's feed |
| post_key, written_by | the post (`<slot>|<topic>|<author>`, unique within a round) and the AI that wrote it |
| own_ai_post | 1 = written_by == played_by |
| action | `like` (upvote), `dislike` (downvote), `nothing` (no vote); empty if the answer failed |
| reason | the user's few words of reason, as the AI wrote them |
| outcome | `chose` (readable answer), `unreadable`, `cut_off`, `timeout` |
| attempts | calls needed (1 = first answer was readable) |
| latency_s | seconds the vote took (one call; 4 calls run at a time) |
| prompt_tokens, eval_tokens | tokens read / written for this vote |

### `posts.csv` — one row per post (also failed ones, `ok` = False)
round, seed, slot_in_topic (0-4), topic, author, key, ok, brief (angle / ptype / voice), title, body (full text,
exactly as written), words (body word count), attempts, latency_s (seconds to write, incl. retries), eval_tokens.

### `users.csv` — the 100 users, every trait
id, username, realname, age, gender, country, place, profession, education, income, mbti, big_five,
topic_affinity (interest −2…+2 for every topic), taste (length / tone / evidence they value), pet_peeve, voting
habit, persona (the exact text the AI is given).

### `timing.csv` — one row per world
world, round, judge (the AI playing users), decisions, vote_wall_min, s_per_vote, post_writing_min (only the
first world of a round writes posts; the second reuses them, so its value is ~0), started, finished, world_wall_min.

### `slots.csv` — one row per slot (a pair of posts from the same brief)
slot, round, topic, like_dd / dislike_dd (that slot's own-AI double difference: see analysis), words_a /
words_b (word counts of the gemma4 and gemma3 posts), gap100 ((words_a − words_b) / 100).

### `analysis.json` — every number on the results page
rate_up/down/nothing (rate[author][player]), sp_up/sp_down (double difference + user × slot bootstrap 95 %),
round_boot_up/down (same estimate, whole rounds resampled: est, ci95, p, rounds_positive), per_round,
length (slot double difference regressed on word gap, round-clustered: at_equal_length, per_100_words_gap, r2),
by_topic, agreement (same user + same post, both AIs: same_choice_%, kappa, crosstab), like_by_interest_pct,
top10 (own-AI posts in each crowd's top 10 per round), timing, posts (counts, duplicates, words, retries),
nothing (per-AI failure / "nothing" report), slots.

### Deep breakdown files (from `analyze_deep.py`, LF-50)
- `deep.json` — every breakdown on the results page: `overall`, `by_topic`, `by_interest`, `by_voting`, `by_scroll_rank`,
  `by_half` (each: up/down double difference in points with 95 % users×slots bootstrap, 1,000 draws, and the four cell
  rates), `leave_one_round_out`, `leave_one_topic_out`, `per_user` (each user's double difference; histogram; sign test),
  `by_position`, `up/down/nothing_by_interest`, `agreement` (crosstab, by topic, per-user), `features_by_author` +
  `what_each_crowd_rewards` (post-level OLS of upvote rate on 14 standardized features + round, clustered by round) +
  `style_explains` (double difference of predicted vs residual rates), `reasons` (top words; own-vs-other log ratios),
  `posts_loved/hated/disputed` (score = upvotes − downvotes per crowd), `latency`, `post_seconds`, `post_attempts`, `users`.
- `deep_posts.json` — one record per shown post: id, round r, topic t, slot s, author a, title ti, body b, words w, job
  card br, votes v[crowd] = [up, down, nothing], sample reasons rs[crowd] = [[action, user, reason], …].
- `deep_users.json` — one record per user: profile, persona text, own-AI boost, agreement, and `acts[crowd]` = one
  character per post in `deep_posts.json` order (u = upvote, d = downvote, n = nothing, . = not shown).

Also: `data/llm_bias/speed_pick.json` (the speed test that chose the two AIs), `two_ai_campaign.log`,
`two_ai_after.log`, `two_ai_checks.txt` (check_world.py per round), raw records in `worlds/two_r*/`.

## Page data files (published next to the Scroll Test page)

`world_data.js` (test 2), `data_ab_scroll.json`, `data_ab_pair.json`, `data_v3.json`: the same packed layout as
`world_data.js` (see above), one per dataset, plus `models` (names in column order) and `cls` (colour classes).
Chart colours: llama blue, gemma orange, mistral magenta (validated for colour-blind separation, both themes).
