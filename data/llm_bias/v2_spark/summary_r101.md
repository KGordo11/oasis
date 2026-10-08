# LLM Bias v2 results

Rounds: [101]. Screens: 69513 (54 unreadable).

## Table 1. Posting turn (empty feed, every action available, nobody told to post)

| AI playing the users | Users | Users who posted | Posts written | Posts by topic | Other actions taken |
|---|---|---|---|---|---|
| gemma3:12b | 100 | 25 | 25 | r/business 7, politics 6, r/politics 5, r/technology 4, entertainment 2, business 1 | refresh 82, search_posts 1 |
| llama3.1:8b | 100 | 98 | 103 | r/politics 41, r/technology 23, r/business 20, r/entertainment 12, r/sports 7 | follow 33, search_user 30, search_posts 27, trend 18, like_post 10, create_comment 7 |
| qwen3:8b | 100 | 86 | 101 | business 22, politics 21, technology 16, r/politics 14, r/sports 9, sports 8, entertainment 7, r/entertainment 4 | do_nothing 7, refresh 7, create_comment 5, like_post 4, search_user 1 |

## Table 2. Reading turn: reader AI x whose posts -> % of screens with each action

| Reader AI | Posts by | Screens | Did nothing | like_post | dislike_post | create_comment | repost | quote_post | follow | mute | report_post | create_post | search_posts | do_nothing |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma3:12b | gemma3:12b (baseline) | 2475 | 6.5% | 48.0% | 38.0% | 8.6% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.1% |
| gemma3:12b | llama3.1:8b | 10197 | 8.2% | 51.6% | 35.9% | 5.3% | 0.0% | 0.0% | 0.0% | 0.0% | 0.1% | 0.0% | 0.0% | 0.2% |
| gemma3:12b | qwen3:8b | 9999 | 7.3% | 51.7% | 34.9% | 7.4% | 0.0% | 0.0% | 0.0% | 0.0% | 0.1% | 0.0% | 0.0% | 0.1% |
| llama3.1:8b | gemma3:12b | 2475 | 3.4% | 60.9% | 33.9% | 50.3% | 1.1% | 0.4% | 7.2% | 0.0% | 26.9% | 0.0% | 4.1% | 10.4% |
| llama3.1:8b | llama3.1:8b (baseline) | 10197 | 3.5% | 62.2% | 32.7% | 49.1% | 1.5% | 0.3% | 8.8% | 0.0% | 26.5% | 0.1% | 5.3% | 12.6% |
| llama3.1:8b | qwen3:8b | 9949 | 3.4% | 60.2% | 35.1% | 50.5% | 1.5% | 0.4% | 10.2% | 0.0% | 26.4% | 0.2% | 5.3% | 12.6% |
| qwen3:8b | gemma3:12b | 2475 | 3.2% | 45.1% | 20.6% | 61.8% | 0.1% | 0.0% | 0.6% | 0.0% | 1.9% | 0.0% | 0.0% | 4.3% |
| qwen3:8b | llama3.1:8b | 10197 | 14.4% | 48.0% | 15.9% | 37.1% | 0.1% | 0.0% | 0.4% | 0.0% | 3.4% | 0.0% | 0.0% | 15.2% |
| qwen3:8b | qwen3:8b (baseline) | 9999 | 8.9% | 43.3% | 16.8% | 49.3% | 0.1% | 0.0% | 0.9% | 0.0% | 2.5% | 0.0% | 0.0% | 9.8% |

## Table 3. Reading turn: % upvoted by the reader's stance on the post's topic

| Reader AI | Posts by | LOVE | LIKE | NEUTRAL | DISLIKE | HATE |
|---|---|---|---|---|---|---|
| gemma3:12b | gemma3:12b | 88.1% | 87.2% | 59.8% | 2.6% | 4.4% |
| gemma3:12b | llama3.1:8b | 91.3% | 95.3% | 65.5% | 6.6% | 1.0% |
| gemma3:12b | qwen3:8b | 90.9% | 91.4% | 65.1% | 9.5% | 3.4% |
| llama3.1:8b | gemma3:12b | 96.7% | 98.2% | 87.8% | 11.2% | 12.4% |
| llama3.1:8b | llama3.1:8b | 98.4% | 99.3% | 89.2% | 11.1% | 14.9% |
| llama3.1:8b | qwen3:8b | 96.6% | 98.6% | 84.3% | 10.7% | 12.8% |
| qwen3:8b | gemma3:12b | 73.6% | 70.4% | 52.8% | 16.2% | 13.6% |
| qwen3:8b | llama3.1:8b | 83.4% | 80.7% | 50.4% | 16.4% | 10.5% |
| qwen3:8b | qwen3:8b | 72.5% | 72.8% | 46.1% | 15.2% | 11.2% |

## Own-AI bias (derived; read Table 2 first)

For AIs i and j: (i reading i's posts - j reading i's posts) - (i reading j's posts - j reading j's posts). Positive = i favours its own AI's posts beyond simply being more generous. Points per 100 screens.

| i | j | Upvote: bias (95% range) | Did anything: bias (95% range) |
|---|---|---|---|
| gemma3:12b | llama3.1:8b | -2.2 (-7.9 to +3.2) | +1.6 (-1.9 to +5.2) |
| gemma3:12b | qwen3:8b | -5.4 (-12.3 to +1.4) | -4.9 (-8.5 to -1.7) |
| llama3.1:8b | qwen3:8b | -2.7 (-7.0 to +1.5) | +5.4 (+1.7 to +9.0) |

## Noise floor (stage 1b): same AI, same posts, re-read with fresh randomness

| AI | Screens compared | Same upvote decision | Upvote rate first / re-read |
|---|---|---|---|
| gemma3:12b | 400 | 96.5% | 49.2% / 47.8% |
| llama3.1:8b | 400 | 88.8% | 60.2% / 61.5% |
| qwen3:8b | 400 | 79.2% | 40.0% / 38.8% |
