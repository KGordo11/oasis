# LLM Bias v2 results (SMOKE TEST)

Rounds: [900]. Screens: 543 (0 unreadable).

## Table 1. Posting turn (empty feed, every action available, nobody told to post)

| AI playing the users | Users | Users who posted | Posts written | Posts by topic | Other actions taken |
|---|---|---|---|---|---|
| llama3.1:8b | 10 | 10 | 10 | r/politics 4, r/sports 2, r/technology 2, r/entertainment 1, r/business 1 | search_user 4, search_posts 1, report_post 1, unfollow 1 |
| mistral:7b | 10 | 0 | 0 |  | search_posts 2, refresh 1 |
| qwen3:8b | 10 | 8 | 9 | politics 3, technology 2, sports 1, r/politics 1, r/sports 1, business 1 | do_nothing 1, like_post 1 |

## Table 2. Reading turn: reader AI x whose posts -> % of screens with each action

| Reader AI | Posts by | Screens | Did nothing | like_post | dislike_post | create_comment | repost | quote_post | follow | mute | report_post | create_post | search_posts | do_nothing |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| llama3.1:8b | llama3.1:8b (baseline) | 90 | 3.3% | 62.2% | 27.8% | 57.8% | 0.0% | 0.0% | 5.6% | 0.0% | 16.7% | 0.0% | 0.0% | 4.4% |
| llama3.1:8b | qwen3:8b | 81 | 0.0% | 64.2% | 29.6% | 50.6% | 1.2% | 1.2% | 2.5% | 0.0% | 19.8% | 0.0% | 1.2% | 1.2% |
| mistral:7b | llama3.1:8b | 90 | 21.1% | 20.0% | 1.1% | 60.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 2.2% |
| mistral:7b | qwen3:8b | 81 | 19.8% | 43.2% | 2.5% | 40.7% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 1.2% | 6.2% |
| qwen3:8b | llama3.1:8b | 90 | 14.4% | 53.3% | 12.2% | 47.8% | 0.0% | 0.0% | 0.0% | 0.0% | 4.4% | 0.0% | 0.0% | 15.6% |
| qwen3:8b | qwen3:8b (baseline) | 81 | 11.1% | 54.3% | 21.0% | 27.2% | 0.0% | 0.0% | 1.2% | 0.0% | 1.2% | 0.0% | 0.0% | 11.1% |

## Table 3. Reading turn: % upvoted by the reader's stance on the post's topic

| Reader AI | Posts by | LOVE | LIKE | NEUTRAL | DISLIKE | HATE |
|---|---|---|---|---|---|---|
| llama3.1:8b | llama3.1:8b | 86.7% | 100.0% | 80.0% | 0.0% | 6.7% |
| llama3.1:8b | qwen3:8b | 100.0% | 100.0% | 90.5% | 0.0% | 0.0% |
| mistral:7b | llama3.1:8b | 40.0% | 22.7% | 20.0% | 7.7% | 6.7% |
| mistral:7b | qwen3:8b | 85.7% | 73.7% | 38.1% | 8.3% | 0.0% |
| qwen3:8b | llama3.1:8b | 100.0% | 77.3% | 52.0% | 15.4% | 6.7% |
| qwen3:8b | qwen3:8b | 100.0% | 94.7% | 52.4% | 0.0% | 6.7% |

## Own-AI bias (derived; read Table 2 first)

For AIs i and j: (i reading i's posts - j reading i's posts) - (i reading j's posts - j reading j's posts). Positive = i favours its own AI's posts beyond simply being more generous. Points per 100 screens.

| i | j | Upvote: bias (95% range) | Did anything: bias (95% range) |
|---|---|---|---|
| llama3.1:8b | mistral:7b | - | - |
| llama3.1:8b | qwen3:8b | -1.0 (-19.1 to +15.1) | +0.0 (-16.0 to +17.3) |
| mistral:7b | qwen3:8b | - | - |
