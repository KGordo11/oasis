# LLM Bias — start here

**The question:** when an AI pretends to be people scrolling Reddit, do those people favour posts written by that same AI?
**The answer so far:** yes. Across six tests, people played by an AI give its own posts about 5–7 more upvotes per 100.
The latest test (Test 6, 15 rounds, 147,600 votes) found **+6.9 upvotes and −4.2 downvotes per 100** for the AI's own posts.

Everything for this project is reachable from this folder. The real files stay where the code expects them
(moving them would break the programs and the links in the pages). The entries here are **shortcuts** to them.

| In this folder | What it is |
|---|---|
| [`test6_two_ai/`](test6_two_ai/) | **The latest test, only the files it used**: code, results, post banks, every run, logs |
| [`LOG.md`](LOG.md) | The lab notebook: every decision (LD-), finding (LF-) and run, with times. Section 0 = current status |
| [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) | What every file and column means |
| [`all_code/`](all_code/) | Every program from all six tests (`examples/experiment/llm_bias/`) |
| [`all_data/`](all_data/) | Every data file from all six tests (`data/llm_bias/`) |

## The pages (open in a browser)

| Page | What's on it |
|---|---|
| [Inside the Two-AI Feed](https://claude.ai/artifact/G9ofxKT7gC2M2fdezFcKFU) | How Test 6 works end to end: the machine, users, posts, one vote traced through every layer, every file, every command, all code |
| [The Two-AI Feed](https://claude.ai/artifact/HPmkfevmeC3LTYWhN4citW) | All Test 6 results: every breakdown, why it happens, browsers for every post and every user |
| [How the Two-AI Reddit Test Works](https://claude.ai/code/artifact/b35c46ac-9e48-4096-a798-0bd00138a4f5) | The 5th-grade guide for a professor, with all the code (Claude Doc) |
| [Do AIs Favour Their Own Writing?](https://claude.ai/code/artifact/7f61723e-b24b-4c68-871f-3510205cdbd4) | The report on all six tests (Claude Doc; Test 6 has its own tab) |
| [Scroll Test](https://claude.ai/artifact/PEMNidbCam72v6qKC3GNBx) | The older page for Tests 2–5 |
| [GitHub, branch llm-bias](https://github.com/KGordo11/oasis/tree/llm-bias) | Everything above, saved |

## Test 6 in one table (30 Sep – 1 Oct 2026)

Two AIs (gemma4:e2b, gemma3:1b) each write 25 new posts per round; each AI then plays the same 100 users, who scroll all
the posts and upvote, downvote or do nothing. 15 rounds.

| Look in | For |
|---|---|
| [`test6_two_ai/code/two_ai_campaign.sh`](test6_two_ai/code/two_ai_campaign.sh) | The script that ran every round (start here when reading the code) |
| [`test6_two_ai/code/run_world.py`](test6_two_ai/code/run_world.py) | One AI's turn in one round: posts, pretend Reddit, every vote |
| [`test6_two_ai/code/authors.py`](test6_two_ai/code/authors.py), [`scroll.py`](test6_two_ai/code/scroll.py), [`llm.py`](test6_two_ai/code/llm.py), [`personas.py`](test6_two_ai/code/personas.py), [`topics.py`](test6_two_ai/code/topics.py) | Post writing, the voting question, talking to the AIs, the 100 users, the subreddits |
| [`test6_two_ai/code/analyze_two_ai.py`](test6_two_ai/code/analyze_two_ai.py), [`analyze_deep.py`](test6_two_ai/code/analyze_deep.py) | All the math |
| [`test6_two_ai/results/`](test6_two_ai/results/) | `reactions.csv` (every vote), `posts.csv` (every post), `users.csv`, `analysis.json`, `deep.json`, `summary.txt` |
| [`test6_two_ai/post_banks/`](test6_two_ai/post_banks/) | Every post of each round, word for word (one file per round) |
| [`test6_two_ai/runs/`](test6_two_ai/runs/) | 30 runs (15 rounds × 2 AIs): `decisions.jsonl` = every vote with its reason, `manifest.json` = every setting |
| [`test6_two_ai/logs_and_checks/`](test6_two_ai/logs_and_checks/) | The speed test that picked the AIs, the campaign log, the health checks |

**To rebuild the numbers:** from the `oasis` folder run
`./oasis-env/bin/python examples/experiment/llm_bias/analyze_two_ai.py 2000` then
`./oasis-env/bin/python examples/experiment/llm_bias/analyze_deep.py`.
**To run more rounds:** start Ollama
(`OLLAMA_FLASH_ATTENTION=1 OLLAMA_NUM_PARALLEL=4 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=24h ollama serve`), then
`A=gemma4:e2b B=gemma3:1b ROUNDS="16 17" STOP_AT="2026-12-31 23:59" examples/experiment/llm_bias/two_ai_campaign.sh`.
Stop Ollama when done (`pkill -f "ollama serve"`).

## All six tests and their files

All code is in [`all_code/`](all_code/), all data in [`all_data/`](all_data/). Results are "extra upvotes per 100 for
the AI's own posts" (95% interval).

| # | Dates | Design | Result | Code (in all_code/) | Data (in all_data/) |
|---|---|---|---|---|---|
| 1 | 23–24 Sep | 7 AIs each write a post; 99 people pick a favourite | +5.6 [+3.4, +7.8] | `run_bias.py`, `judge.py`, `authors.py`, `analyze.py`, `recognize.py`, `campaign.sh`, `night1_queue*.sh` | `runs/`, `postbank_s1`, `s2`, `s101`, `analysis_s1*`, `analysis_s2*`, `analysis_combined_s1_s2*`, `recognition_s1*` |
| 2 | 24–26 Sep | 2 AIs (llama3.1, gemma4); 99 people scroll and vote | +2.4 [−1.3, +6.2] | `run_world.py`, `scroll.py`, `world_campaign.sh`, `analyze_world.py`, `export_world.py`, `check_world.py`, `explore_world.py`, `length_test.py`, `retest_compare.py`, `agent_sweep.sh`, `bench_*.sh` | `worlds/v2_*`, `worlds/rt*`, `worlds/sweep_*`, `postbank_s10`–`s16`, `export/`, `analysis_v2*`, `explore_v2*`, `heldout_*`, `lengthtest*` |
| 3 | 26–27 Sep | One post at a time vs side by side; length-matched | +5.2 [+2.4, +8.1] | `ab_campaign.sh`, `ab_refresh.sh`, `pair.py`, `analyze_ab.py` | `worlds/ab_*`, `postbank_s20`–`s34`, `export_ab/`, `analysis_ab.json`, `ab_checks.txt` |
| 4 | 27–29 Sep | 3 AIs (llama3.1, gemma4, mistral) writing freely; 50 people | +6.8 [+4.6, +9.4] | `v3_campaign.sh`, `v3_refresh.sh`, `taste.py`, `variance.py`, `recognize.py` | `worlds/v3_*`, `postbank_s40`–`s45`, `export_v3/`, `analysis_v3*`, `taste_v3.json`, `variance_v3.json`, `recognition_s4*`, `retest_v3_s40.json` |
| 5 | 29 Sep | One AI plays the whole crowd on a ranked feed | +7.2 [+4.9, +9.6] | `run_feed.py`, `analyze_feed.py` | `feeds/`, `analysis_feed.json`, `feed_campaign.log` |
| 6 | 30 Sep – 1 Oct | 2 AIs (gemma4, gemma3); 100 users; new posts each round; 15 rounds | **+6.9 [+2.9, +10.6]** | see [`test6_two_ai/code/`](test6_two_ai/code/) | see [`test6_two_ai/`](test6_two_ai/) |

Shared by several tests: `llm.py`, `personas.py` + `personas_bank.json`, `topics.py`, `authors.py`, `analyze.py`,
`check_world.py`. Page builders for the older pages: `make_artifact.py`, `make_world_artifact.py`.
Not part of any result: `postbank_s900.jsonl` (a smoke test), `bench_*` worlds and `speed_*` worlds (speed tests).

## Where things live (don't move these)

```
oasis/
├── 00_LLM_BIAS_START_HERE/        ← this folder (shortcuts only)
├── LLM_BIAS_LOG.md                 the lab notebook
├── LLM_BIAS_DATA_DICTIONARY.md     every file and column
├── examples/experiment/llm_bias/   all LLM Bias code
├── data/llm_bias/                  all LLM Bias data
│   ├── two_ai/                     Test 6 results (CSVs, analysis)
│   ├── worlds/                     every run: two_r* (Test 6), v3_* (4), ab_* (3), v2_* (2)
│   ├── feeds/                      Test 5 runs
│   ├── runs/                       Test 1 runs
│   └── postbank_s*.jsonl           every post, one file per post set / round
└── (everything else)               OASIS itself and the older Sim 1–4 projects (RESEARCH_LOG.md)
```
