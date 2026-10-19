# Start here

**`RESEARCH_LOG.md` is the one log for everything** (Part 0 = where things stand, §0.2 = read first).

## Where things are

| You want | Go to |
|---|---|
| **LLM Bias raw data (V1 + V2, every answer word for word)** | **`data/llm_bias/v1_v2_spark/`** (rounds `r101`-`r104`; map in `data/llm_bias/README.md`) |
| LLM Bias code | `examples/experiment/llm_bias/` (`run_v2.py` runs a round, `llm.py` talks to the AIs, `personas_v2.json` = the 100 users) |
| LLM Bias September tests 1-6 (older study) | `data/llm_bias/old_tests_sep2026/` |
| Simulation 4 (social timeline) data / code | `data/sim4_social_timeline/` / `examples/experiment/social_timeline/` |
| Simulation 3 (Shield) code | `examples/experiment/reddit_simulation_counterfactual/` |
| Persona inputs (original OASIS) | `data/reddit/`, `data/twitter_dataset/` |
| Excel workbooks and graphs | `~/Desktop/LLM_Bias/` (made from `data/llm_bias/v1_v2_spark/`) |

## Not ours (the original OASIS project; leave alone)

`oasis/` (the simulator the code imports), `assets/`, `docs/` (except `docs/superpowers/` = our Sim 4 design notes), `generator/`, `visualization/`, `licenses/`, `test/`,
`.container/`, `.github/`, `deploy.py`, `CONTRIBUTING.md`, `LICENSE`, `README.md`, `pyproject.toml`, `poetry.lock`,
`log/` (OASIS writes engine logs here), and every other folder in `examples/`. `oasis-env/` is the laptop's Python.
