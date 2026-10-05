# LLM Bias v2 results

Rounds: [1]. Screens: 5100 (6 unreadable).

## Table 1. Posting turn (empty feed, every action available, nobody told to post)

| AI playing the users | Users | Users who posted | Posts written | Posts by topic | Other actions taken |
|---|---|---|---|---|---|
| llama3.1:8b | 100 | 96 | 96 | r/politics 32, r/technology 20, r/business 20, r/sports 12, r/entertainment 12 | search_user 20, follow 13, create_comment 3, search_posts 3, do_nothing 2, refresh 2 |
| mistral:7b | 100 | 0 | 0 |  | search_posts 32, refresh 6, trend 4 |
| qwen3:8b | 100 | 88 | 101 | politics 22, business 21, sports 15, r/politics 12, technology 12, entertainment 10, r/entertainment 5, r/sports 4 | like_post 7, do_nothing 7, refresh 6, create_comment 4 |

## Table 2. Reading turn: reader AI x whose posts -> % of screens with each action

| Reader AI | Posts by | Screens | Did nothing | like_post | dislike_post | create_comment | repost | quote_post | follow | mute | report_post | create_post | search_posts | do_nothing |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama3.1:8b | llama3.1:8b (baseline) | 800 | 1.5% | 58.9% | 34.4% | 47.4% | 0.0% | 0.0% | 5.0% | 0.0% | 15.2% | 0.0% | 0.9% | 3.2% |
| llama3.1:8b | qwen3:8b | 800 | 2.2% | 54.4% | 39.1% | 46.9% | 0.2% | 0.0% | 3.9% | 0.0% | 16.4% | 0.0% | 0.9% | 4.2% |
| mistral:7b | llama3.1:8b | 799 | 30.7% | 26.8% | 2.5% | 41.3% | 0.0% | 0.0% | 0.5% | 0.0% | 0.0% | 0.0% | 0.1% | 6.3% |
| mistral:7b | qwen3:8b | 799 | 29.8% | 27.8% | 1.6% | 41.9% | 0.0% | 0.0% | 0.0% | 0.0% | 0.1% | 0.0% | 0.8% | 7.4% |
| qwen3:8b | llama3.1:8b | 800 | 19.4% | 49.6% | 11.0% | 40.6% | 0.1% | 0.0% | 0.8% | 0.0% | 2.4% | 0.0% | 0.0% | 20.5% |
| qwen3:8b | qwen3:8b (baseline) | 800 | 13.8% | 43.4% | 17.1% | 45.9% | 0.0% | 0.0% | 1.2% | 0.0% | 1.5% | 0.0% | 0.0% | 14.5% |

## Table 3. Reading turn: % upvoted by the reader's stance on the post's topic

| Reader AI | Posts by | LOVE | LIKE | NEUTRAL | DISLIKE | HATE |
|---|---|---|---|---|---|---|
| llama3.1:8b | llama3.1:8b | 91.8% | 94.0% | 83.8% | 9.0% | 13.8% |
| llama3.1:8b | qwen3:8b | 91.1% | 91.9% | 75.5% | 8.5% | 11.8% |
| mistral:7b | llama3.1:8b | 53.4% | 49.4% | 23.3% | 5.8% | 3.1% |
| mistral:7b | qwen3:8b | 50.4% | 50.6% | 28.9% | 7.9% | 4.8% |
| qwen3:8b | llama3.1:8b | 85.6% | 82.5% | 51.4% | 14.7% | 14.5% |
| qwen3:8b | qwen3:8b | 80.7% | 70.3% | 47.8% | 15.8% | 8.9% |

## Own-AI bias (derived; read Table 2 first)

For AIs i and j: (i reading i's posts - j reading i's posts) - (i reading j's posts - j reading j's posts). Positive = i favours its own AI's posts beyond simply being more generous. Points per 100 screens.

| i | j | Upvote: bias (95% range) | Did anything: bias (95% range) |
|---|---|---|---|
| llama3.1:8b | mistral:7b | - | - |
| llama3.1:8b | qwen3:8b | -1.7 (-10.7 to +7.4) | +6.4 (-0.3 to +13.5) |
| mistral:7b | qwen3:8b | - | - |
