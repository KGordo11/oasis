# LLM Bias data: where every file is

| Folder | What it is |
|---|---|
| **`v1_v2_spark/`** | **The real raw data of the current study** (V1 = rounds 101-102, V2 = rounds 103-104), copied from the DGX Spark. An exact mirror of the Spark's `~/llm_bias/oasis/data/llm_bias/v2/`. Refresh it with the rsync command below. |
| `v2/` | The code's own working folder on this laptop (`run_v2.py` writes here). Holds only laptop test rounds (`r001`, `r900`, `r901`). Not results. |
| `v2_sources/` | The public tables the 100 users were built from (Census, names, education) + `human_pool.jsonl` (real Reddit posts) |
| `old_tests_sep2026/` | The six September tests (a separate, older study; see the bottom of this page) |

The 100 users themselves are `examples/experiment/llm_bias/personas_v2.json` (next to the code, frozen).

## Inside `v1_v2_spark/` (the raw data)

```
v1_v2_spark/
├── r101/  r102/            V1 rounds (the AI gets only the person to play)
├── r103/  r104/            V2 rounds (same, plus "I am <model>, simulating this profile:")
│   ├── posting_<AI>.jsonl                  posting turn: what each of the 100 users did on an empty feed (1 line = 1 user)
│   ├── reading_<posts by>__<read by>.jsonl reading turn: every user's reaction to every post (1 line = 1 user x 1 post)
│   ├── reading_<AI>__<AI>_d1.jsonl         noise floor: the same AI re-reads its own posts with a new random seed
│   ├── <same name>.manifest.json           the step's settings record: model file, prompts fingerprint, sampling, code version
│   └── <same name>.log                     the step's console log
├── r900/ … r904/           small test rounds (not results)
├── export/                 everything flattened to CSV + LLM_bias_v2.xlsx (made by export_v2.py)
├── graphs/                 the charts (made by make_graphs_v2.py)
├── summary.md              plain-text tables (made by analyze_v2.py)
└── night.log               the Spark's run log
```

**One line of a `.jsonl` file** is one answer, word for word. The fields that matter: `user_id`, `post_key` (which post),
`actions` (what the AI chose; `[]` = an empty list = did nothing), `reason`, `raw` (the AI's reply exactly as it came back),
`outcome` (`chose`, or unreadable after 3 tries), `prompt_tokens`. Every column is explained in RESEARCH_LOG.md Part 14.

**Refresh from the Spark** (Mac terminal, not inside ssh):
`rsync -avz honda:llm_bias/oasis/data/llm_bias/v2/ ~/research/oasis/data/llm_bias/v1_v2_spark/`

**Check it is identical to the Spark** (both should print `7ace91dc41c5f431` for rounds 101-104):
`cd data/llm_bias/v1_v2_spark && shasum -a 256 r10[1-4]/*.jsonl | LC_ALL=C sort -k2 | shasum -a 256 | cut -c1-16`

## The September tests (`old_tests_sep2026/`)

| Folder | Dates | Design | Main files |
|---|---|---|---|
| `test1_pick_a_favourite/` | 23-24 Sep | 7 AIs each write a post; 99 people pick a favourite | `runs/` (every run), `postbank_s*.jsonl` (the posts), `analysis_*` |
| `test2_two_ai_scroll/` | 24-26 Sep | 2 AIs; 99 people scroll and vote | `worlds/v2_*` (runs), `export/` (CSVs), speed tests in `worlds/speed_*`, `bench_*` |
| `test3_one_vs_side_by_side/` | 26-27 Sep | one post at a time vs side by side | `worlds/ab_*`, `export_ab/` |
| `test4_three_ai/` | 27-29 Sep | 3 AIs writing freely; 50 people | `worlds/v3_*`, `export_v3/` |
| `test5_one_ai_ranked_feed/` | 29 Sep | one AI plays the whole crowd on a ranked feed | `feeds/` |
| `test6_two_ai_15_rounds/` | 30 Sep-1 Oct | 2 AIs, 100 users, 15 rounds | `two_ai/` (`reactions.csv` = every vote, `test6_every_scroll.xlsx`), `worlds/two_r*`, `post_banks/` |

These folders were reorganised on 2026-10-19. The September programs still expect the old places
(`data/llm_bias/worlds/`, `data/llm_bias/two_ai/`, `data/llm_bias/postbank_s*.jsonl`, …). To rerun one, move its files back there.
