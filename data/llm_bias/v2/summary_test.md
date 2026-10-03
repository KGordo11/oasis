# LLM Bias v2 results (SMOKE TEST)

Rounds: [900]. Decisions: 800 (0 unreadable). Users' own posts: 0.

## Table 1. Seed posts: who played the users x who wrote the post

| Users played by | Post written by | Decisions | Upvote | Downvote | None |
|---|---|---|---|---|---|
| gemma4:e2b | human | 50 | 46 (92.0%) | 4 (8.0%) | 0 (0.0%) |
| gemma4:e2b | gemma4:e2b (own) | 50 | 46 (92.0%) | 0 (0.0%) | 4 (8.0%) |
| gemma4:e2b | llama3.2:3b | 50 | 43 (86.0%) | 0 (0.0%) | 7 (14.0%) |
| gemma4:e2b | qwen3:4b | 50 | 46 (92.0%) | 0 (0.0%) | 4 (8.0%) |
| granite4.1:3b | human | 50 | 3 (6.0%) | 0 (0.0%) | 47 (94.0%) |
| granite4.1:3b | gemma4:e2b | 50 | 32 (64.0%) | 0 (0.0%) | 18 (36.0%) |
| granite4.1:3b | llama3.2:3b | 50 | 18 (36.0%) | 0 (0.0%) | 32 (64.0%) |
| granite4.1:3b | qwen3:4b | 50 | 15 (30.0%) | 0 (0.0%) | 35 (70.0%) |
| llama3.2:3b | human | 50 | 48 (96.0%) | 2 (4.0%) | 0 (0.0%) |
| llama3.2:3b | gemma4:e2b | 50 | 50 (100.0%) | 0 (0.0%) | 0 (0.0%) |
| llama3.2:3b | llama3.2:3b (own) | 50 | 48 (96.0%) | 2 (4.0%) | 0 (0.0%) |
| llama3.2:3b | qwen3:4b | 50 | 50 (100.0%) | 0 (0.0%) | 0 (0.0%) |
| qwen3:4b | human | 50 | 40 (80.0%) | 1 (2.0%) | 9 (18.0%) |
| qwen3:4b | gemma4:e2b | 50 | 38 (76.0%) | 0 (0.0%) | 12 (24.0%) |
| qwen3:4b | llama3.2:3b | 50 | 36 (72.0%) | 2 (4.0%) | 12 (24.0%) |
| qwen3:4b | qwen3:4b (own) | 50 | 39 (78.0%) | 2 (4.0%) | 9 (18.0%) |

## Table 2. Seed posts: other actions (% of decisions)

| Users played by | Post written by | comment | follow | mute | share | report |
|---|---|---|---|---|---|---|
| gemma4:e2b | human | 100.0% | 8.0% | 0.0% | 8.0% | 0.0% |
| gemma4:e2b | gemma4:e2b | 100.0% | 2.0% | 0.0% | 20.0% | 0.0% |
| gemma4:e2b | llama3.2:3b | 100.0% | 16.0% | 0.0% | 8.0% | 0.0% |
| gemma4:e2b | qwen3:4b | 100.0% | 2.0% | 0.0% | 16.0% | 0.0% |
| granite4.1:3b | human | 10.0% | 14.0% | 10.0% | 0.0% | 0.0% |
| granite4.1:3b | gemma4:e2b | 64.0% | 66.0% | 0.0% | 0.0% | 0.0% |
| granite4.1:3b | llama3.2:3b | 40.0% | 44.0% | 0.0% | 0.0% | 0.0% |
| granite4.1:3b | qwen3:4b | 44.0% | 40.0% | 14.0% | 0.0% | 0.0% |
| llama3.2:3b | human | 82.0% | 92.0% | 2.0% | 38.0% | 0.0% |
| llama3.2:3b | gemma4:e2b | 72.0% | 90.0% | 0.0% | 32.0% | 0.0% |
| llama3.2:3b | llama3.2:3b | 56.0% | 76.0% | 4.0% | 24.0% | 0.0% |
| llama3.2:3b | qwen3:4b | 76.0% | 92.0% | 2.0% | 36.0% | 0.0% |
| qwen3:4b | human | 78.0% | 0.0% | 0.0% | 20.0% | 0.0% |
| qwen3:4b | gemma4:e2b | 74.0% | 2.0% | 0.0% | 18.0% | 0.0% |
| qwen3:4b | llama3.2:3b | 64.0% | 2.0% | 0.0% | 36.0% | 0.0% |
| qwen3:4b | qwen3:4b | 80.0% | 2.0% | 0.0% | 28.0% | 0.0% |

## Table 3. Seed posts: % upvoted, by the user's stance on the topic

| Users played by | Post written by | LOVE | LIKE | NEUTRAL | DISLIKE | HATE |
|---|---|---|---|---|---|---|
| gemma4:e2b | human | 100.0% | 100.0% | 92.9% | 85.7% | 71.4% |
| gemma4:e2b | gemma4:e2b | 100.0% | 100.0% | 85.7% | 85.7% | 85.7% |
| gemma4:e2b | llama3.2:3b | 91.7% | 100.0% | 71.4% | 85.7% | 85.7% |
| gemma4:e2b | qwen3:4b | 100.0% | 100.0% | 92.9% | 85.7% | 71.4% |
| granite4.1:3b | human | 16.7% | 10.0% | 0.0% | 0.0% | 0.0% |
| granite4.1:3b | gemma4:e2b | 83.3% | 70.0% | 57.1% | 28.6% | 71.4% |
| granite4.1:3b | llama3.2:3b | 33.3% | 50.0% | 35.7% | 14.3% | 42.9% |
| granite4.1:3b | qwen3:4b | 25.0% | 50.0% | 28.6% | 14.3% | 28.6% |
| llama3.2:3b | human | 100.0% | 100.0% | 100.0% | 85.7% | 85.7% |
| llama3.2:3b | gemma4:e2b | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| llama3.2:3b | llama3.2:3b | 100.0% | 100.0% | 100.0% | 100.0% | 71.4% |
| llama3.2:3b | qwen3:4b | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| qwen3:4b | human | 100.0% | 100.0% | 92.9% | 42.9% | 28.6% |
| qwen3:4b | gemma4:e2b | 100.0% | 100.0% | 71.4% | 42.9% | 42.9% |
| qwen3:4b | llama3.2:3b | 100.0% | 100.0% | 64.3% | 28.6% | 42.9% |
| qwen3:4b | qwen3:4b | 100.0% | 100.0% | 78.6% | 28.6% | 57.1% |

## Table 4. Users writing their own posts, and reactions to them (pass 2)

| Model | Users asked | Wrote a post | Pass-2 decisions | Upvote | Downvote | Comment |
|---|---|---|---|---|---|---|
| gemma4:e2b | 10 | 0 (0.0%) | 0 | - | - | - |
| granite4.1:3b | 10 | 0 (0.0%) | 0 | - | - | - |
| llama3.2:3b | 10 | 0 (0.0%) | 0 | - | - | - |
| qwen3:4b | 10 | 0 (0.0%) | 0 | - | - | - |

## Own-AI boost (derived; read Table 1 first)

Own-AI boost = how often a model's users upvote that model's posts, minus how often the OTHER models' users upvote those same posts. It cancels 'this AI just writes better posts'. Own vs human = the same model's users, its own posts minus the human posts.

| Model | Its users upvote its posts | Other models' users upvote its posts | Own-AI boost (points per 100) | Its users upvote human posts | Own vs human |
|---|---|---|---|---|---|
| gemma4:e2b | 92.0% | 80.0% | +12.0 | 92.0% | +0.0 |
| llama3.2:3b | 96.0% | 64.7% | +31.3 | 96.0% | +0.0 |
| qwen3:4b | 78.0% | 74.0% | +4.0 | 80.0% | -2.0 |
