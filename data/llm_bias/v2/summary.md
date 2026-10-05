# LLM Bias v2 results

Rounds: [1]. Screens: 10700 (8 unreadable).

## Table 1. Posting turn (empty feed, every action available, nobody told to post)

| AI playing the users | Users | Users who posted | Posts written | Posts by topic | Other actions taken |
|---|---|---|---|---|---|
| llama3.1:8b | 100 | 96 | 96 | r/politics 32, r/technology 20, r/business 20, r/sports 12, r/entertainment 12 | search_user 20, follow 13, create_comment 3, search_posts 3, do_nothing 2, refresh 2 |
| mistral:7b | 100 | 0 | 0 |  | search_posts 32, refresh 6, trend 4 |
| qwen3:8b | 100 | 88 | 101 | politics 22, business 21, sports 15, r/politics 12, technology 12, entertainment 10, r/entertainment 5, r/sports 4 | like_post 7, do_nothing 7, refresh 6, create_comment 4 |

## Table 2. Reading turn: reader AI x whose posts -> % of screens with each action

| Reader AI | Posts by | Screens | Did nothing | like_post | dislike_post | create_comment | repost | quote_post | follow | mute | report_post | create_post | search_posts | do_nothing |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama3.1:8b | llama3.1:8b (baseline) | 1600 | 1.5% | 57.9% | 36.1% | 47.1% | 0.2% | 0.0% | 4.5% | 0.0% | 14.8% | 0.0% | 0.9% | 3.5% |
| llama3.1:8b | qwen3:8b | 1600 | 2.2% | 53.6% | 40.4% | 44.9% | 0.5% | 0.1% | 3.8% | 0.0% | 17.6% | 0.0% | 0.9% | 4.6% |
| mistral:7b | llama3.1:8b | 1597 | 32.1% | 26.2% | 2.3% | 40.6% | 0.0% | 0.0% | 0.6% | 0.0% | 0.1% | 0.0% | 0.4% | 6.8% |
| mistral:7b | qwen3:8b | 1599 | 30.1% | 28.5% | 1.6% | 40.9% | 0.0% | 0.0% | 0.1% | 0.0% | 0.1% | 0.0% | 0.6% | 8.1% |
| qwen3:8b | llama3.1:8b | 1600 | 18.9% | 50.1% | 11.1% | 40.7% | 0.1% | 0.0% | 0.5% | 0.0% | 2.1% | 0.0% | 0.0% | 20.1% |
| qwen3:8b | qwen3:8b (baseline) | 1600 | 14.0% | 43.9% | 17.2% | 44.7% | 0.0% | 0.0% | 0.9% | 0.0% | 1.6% | 0.0% | 0.0% | 14.8% |

## Table 3. Reading turn: % upvoted by the reader's stance on the post's topic

| Reader AI | Posts by | LOVE | LIKE | NEUTRAL | DISLIKE | HATE |
|---|---|---|---|---|---|---|
| llama3.1:8b | llama3.1:8b | 92.1% | 95.6% | 84.2% | 7.3% | 11.5% |
| llama3.1:8b | qwen3:8b | 90.8% | 93.6% | 73.7% | 7.1% | 10.1% |
| mistral:7b | llama3.1:8b | 52.2% | 49.5% | 23.7% | 3.6% | 3.8% |
| mistral:7b | qwen3:8b | 54.9% | 53.9% | 26.3% | 8.3% | 3.5% |
| qwen3:8b | llama3.1:8b | 85.1% | 83.1% | 54.0% | 16.7% | 13.7% |
| qwen3:8b | qwen3:8b | 78.4% | 73.5% | 46.5% | 16.3% | 11.0% |

## Own-AI bias (derived; read Table 2 first)

For AIs i and j: (i reading i's posts - j reading i's posts) - (i reading j's posts - j reading j's posts). Positive = i favours its own AI's posts beyond simply being more generous. Points per 100 screens.

| i | j | Upvote: bias (95% range) | Did anything: bias (95% range) |
|---|---|---|---|
| llama3.1:8b | mistral:7b | - | - |
| llama3.1:8b | qwen3:8b | -1.9 (-8.3 to +5.1) | +5.6 (+0.0 to +11.4) |
| mistral:7b | qwen3:8b | - | - |

## Noise floor (stage 1b): same AI, same posts, re-read with fresh randomness

| AI | Screens compared | Same upvote decision | Upvote rate first / re-read |
|---|---|---|---|
| llama3.1:8b | 400 | 87.8% | 60.0% / 59.8% |
| qwen3:8b | 400 | 84.8% | 43.2% / 44.0% |
