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
| `post_key` | the post's permanent id: `r<slot-1>\|<topic>\|<author model>` |
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
| `post_key` | permanent id (as above) |
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

---

## Design v1 (night 1) — `data/llm_bias/runs/<label>/decisions.jsonl`

7 models, pick-a-favourite. One line per user per round: `judge` (controlling
model), `shown_keys` / `shown_authors` (the 7 posts in the order shown),
`favorite_key` / `favorite_author` (the one picked), `votes` (up/down/none per
post), `reason`, `latency_s`. Per-round timings are in each run's `manifest.json`
under `rounds` (`wall_s`, `s_per_decision`). Summaries in
`data/llm_bias/analysis_s<seed>.txt`.
