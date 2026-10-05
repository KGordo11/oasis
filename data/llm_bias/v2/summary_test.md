# LLM Bias v2 results (SMOKE TEST)

Rounds: [900, 901]. Screens: 1676 (0 unreadable).

## Table 1. Posting turn (empty feed, every action available, nobody told to post)

| AI playing the users | Users | Users who posted | Posts written | Posts by topic | Other actions taken |
|---|---|---|---|---|---|
| command-r7b:latest | 10 | 1 | 1 | r/sports 1 | trend 6, refresh 5, search_posts 4, do_nothing 2, follow 1 |
| falcon3:7b | 10 | 3 | 3 | r/technology 3 | refresh 4, like_post 4, create_comment 3, search_user 2, dislike_post 1, follow 1 |
| gemma3:12b | 20 | 6 | 6 | r/politics 2, r/technology 2, politics 2 | refresh 14, search_posts 1 |
| granite3.3:8b | 10 | 0 | 0 |  | do_nothing 1 |
| llama3.1:8b | 20 | 18 | 18 | r/politics 8, r/sports 3, r/technology 3, r/entertainment 2, r/business 2 | search_user 9, search_posts 2, follow 2, report_post 1, unfollow 1 |
| mistral:7b | 10 | 0 | 0 |  | search_posts 2, refresh 1 |
| olmo2:7b | 10 | 0 | 0 |  |  |
| qwen3:8b | 20 | 16 | 19 | technology 5, politics 4, business 4, r/politics 3, sports 2, r/sports 1 | do_nothing 2, like_post 1, create_comment 1 |

## Table 2. Reading turn: reader AI x whose posts -> % of screens with each action

| Reader AI | Posts by | Screens | Did nothing | like_post | dislike_post | create_comment | repost | quote_post | follow | mute | report_post | create_post | search_posts | do_nothing |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| falcon3:7b | qwen3:8b | 81 | 12.3% | 84.0% | 3.7% | 8.6% | 2.5% | 1.2% | 2.5% | 0.0% | 0.0% | 0.0% | 0.0% | 1.2% |
| gemma3:12b | gemma3:12b (baseline) | 27 | 0.0% | 44.4% | 55.6% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| gemma3:12b | llama3.1:8b | 72 | 1.4% | 48.6% | 43.1% | 1.4% | 0.0% | 0.0% | 0.0% | 0.0% | 2.8% | 0.0% | 0.0% | 1.4% |
| gemma3:12b | qwen3:8b | 171 | 1.8% | 59.1% | 31.6% | 4.7% | 0.0% | 0.0% | 0.0% | 0.0% | 4.1% | 0.0% | 0.0% | 1.8% |
| granite3.3:8b | qwen3:8b | 81 | 77.8% | 6.2% | 0.0% | 18.5% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 2.5% |
| llama3.1:8b | gemma3:12b | 27 | 0.0% | 48.1% | 48.1% | 40.7% | 0.0% | 0.0% | 0.0% | 0.0% | 25.9% | 0.0% | 0.0% | 3.7% |
| llama3.1:8b | llama3.1:8b (baseline) | 162 | 1.9% | 57.4% | 33.3% | 49.4% | 0.0% | 0.0% | 4.9% | 0.0% | 29.0% | 0.0% | 0.6% | 3.1% |
| llama3.1:8b | qwen3:8b | 171 | 0.0% | 64.9% | 29.2% | 55.6% | 1.2% | 0.6% | 1.8% | 0.0% | 19.9% | 0.0% | 0.6% | 2.3% |
| mistral:7b | llama3.1:8b | 90 | 21.1% | 20.0% | 1.1% | 60.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 2.2% |
| mistral:7b | qwen3:8b | 81 | 19.8% | 43.2% | 2.5% | 40.7% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 1.2% | 6.2% |
| olmo2:7b | qwen3:8b | 81 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| qwen3:8b | gemma3:12b | 27 | 14.8% | 40.7% | 11.1% | 59.3% | 0.0% | 0.0% | 0.0% | 0.0% | 14.8% | 0.0% | 0.0% | 14.8% |
| qwen3:8b | llama3.1:8b | 162 | 19.1% | 48.8% | 9.3% | 38.3% | 0.0% | 0.0% | 0.6% | 0.0% | 8.6% | 0.0% | 0.0% | 21.0% |
| qwen3:8b | qwen3:8b (baseline) | 171 | 9.9% | 53.8% | 19.3% | 38.6% | 0.0% | 0.0% | 0.6% | 0.0% | 1.2% | 0.0% | 0.0% | 10.5% |

## Table 3. Reading turn: % upvoted by the reader's stance on the post's topic

| Reader AI | Posts by | LOVE | LIKE | NEUTRAL | DISLIKE | HATE |
|---|---|---|---|---|---|---|
| falcon3:7b | qwen3:8b | 100.0% | 100.0% | 90.5% | 58.3% | 60.0% |
| gemma3:12b | gemma3:12b | 100.0% | 87.5% | 28.6% | 0.0% | 0.0% |
| gemma3:12b | llama3.1:8b | 72.7% | 100.0% | 52.2% | 0.0% | 0.0% |
| gemma3:12b | qwen3:8b | 97.0% | 89.2% | 81.8% | 0.0% | 0.0% |
| granite3.3:8b | qwen3:8b | 21.4% | 10.5% | 0.0% | 0.0% | 0.0% |
| llama3.1:8b | gemma3:12b | 100.0% | 62.5% | 57.1% | 33.3% | 0.0% |
| llama3.1:8b | llama3.1:8b | 84.6% | 100.0% | 66.7% | 0.0% | 7.1% |
| llama3.1:8b | qwen3:8b | 100.0% | 97.3% | 90.9% | 3.8% | 3.2% |
| mistral:7b | llama3.1:8b | 40.0% | 22.7% | 20.0% | 7.7% | 6.7% |
| mistral:7b | qwen3:8b | 85.7% | 73.7% | 38.1% | 8.3% | 0.0% |
| olmo2:7b | qwen3:8b | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| qwen3:8b | gemma3:12b | 100.0% | 50.0% | 28.6% | 66.7% | 0.0% |
| qwen3:8b | llama3.1:8b | 96.2% | 78.4% | 43.8% | 8.7% | 7.1% |
| qwen3:8b | qwen3:8b | 93.9% | 89.2% | 54.5% | 3.8% | 9.7% |

## Own-AI bias (derived; read Table 2 first)

For AIs i and j: (i reading i's posts - j reading i's posts) - (i reading j's posts - j reading j's posts). Positive = i favours its own AI's posts beyond simply being more generous. Points per 100 screens.

| i | j | Upvote: bias (95% range) | Did anything: bias (95% range) |
|---|---|---|---|
| command-r7b:latest | falcon3:7b | - | - |
| command-r7b:latest | gemma3:12b | - | - |
| command-r7b:latest | granite3.3:8b | - | - |
| command-r7b:latest | llama3.1:8b | - | - |
| command-r7b:latest | mistral:7b | - | - |
| command-r7b:latest | olmo2:7b | - | - |
| command-r7b:latest | qwen3:8b | - | - |
| falcon3:7b | gemma3:12b | - | - |
| falcon3:7b | granite3.3:8b | - | - |
| falcon3:7b | llama3.1:8b | - | - |
| falcon3:7b | mistral:7b | - | - |
| falcon3:7b | olmo2:7b | - | - |
| falcon3:7b | qwen3:8b | - | - |
| gemma3:12b | granite3.3:8b | - | - |
| gemma3:12b | llama3.1:8b | +5.1 (-22.2 to +42.4) | -0.5 (-5.6 to +6.4) |
| gemma3:12b | mistral:7b | - | - |
| gemma3:12b | olmo2:7b | - | - |
| gemma3:12b | qwen3:8b | -1.6 (-30.1 to +30.8) | +6.6 (-11.8 to +38.4) |
| granite3.3:8b | llama3.1:8b | - | - |
| granite3.3:8b | mistral:7b | - | - |
| granite3.3:8b | olmo2:7b | - | - |
| granite3.3:8b | qwen3:8b | - | - |
| llama3.1:8b | mistral:7b | - | - |
| llama3.1:8b | olmo2:7b | - | - |
| llama3.1:8b | qwen3:8b | -2.5 (-17.0 to +13.7) | +7.3 (-5.9 to +23.4) |
| mistral:7b | olmo2:7b | - | - |
| mistral:7b | qwen3:8b | - | - |
| olmo2:7b | qwen3:8b | - | - |

## Noise floor (stage 1b): same AI, same posts, re-read with fresh randomness

| AI | Screens compared | Same upvote decision | Upvote rate first / re-read |
|---|---|---|---|
| qwen3:8b | 162 | 84.6% | 54.3% / 51.2% |
