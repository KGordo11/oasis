# LLM Bias v2 results

Rounds: [102]. Screens: 67434 (833 unreadable).

## Table 1. Posting turn (empty feed, every action available, nobody told to post)

| AI playing the users | Users | Users who posted | Posts written | Posts by topic | Other actions taken |
|---|---|---|---|---|---|
| gemma3:12b | 100 | 23 | 23 | politics 9, r/politics 6, r/business 5, entertainment 2, business 1 | refresh 82, search_posts 1 |
| llama3.1:8b | 100 | 99 | 105 | r/politics 36, r/technology 24, r/business 21, r/entertainment 14, r/sports 10 | search_user 28, follow 27, trend 17, create_comment 15, search_posts 13, like_post 10 |
| qwen3:8b | 100 | 85 | 94 | politics 22, business 20, technology 16, r/politics 10, r/sports 8, entertainment 7, r/entertainment 7, sports 4 | do_nothing 7, refresh 7, like_post 2, create_comment 2 |

## Table 2. Reading turn: reader AI x whose posts -> total engagement, % engaged, and % of screens with each action

| Reader AI | Posts by | Screens | **Total engagement (actions per 100 screens)** | **Engaged (any action)** | Did nothing | like_post | dislike_post | create_comment | repost | quote_post | follow | mute | report_post | create_post | search_posts | do_nothing |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gemma3:12b | gemma3:12b (baseline) | 2277 | 95.8 | 93.9% | 6.1% | 51.6% | 34.3% | 9.3% | 0.0% | 0.0% | 0.0% | 0.1% | 0.0% | 0.0% | 0.0% | 0.1% |
| gemma3:12b | llama3.1:8b | 10395 | 93.9 | 91.7% | 8.3% | 51.3% | 35.8% | 5.9% | 0.0% | 0.0% | 0.0% | 0.0% | 0.1% | 0.0% | 0.1% | 0.2% |
| gemma3:12b | qwen3:8b | 8477 | 96.0 | 93.3% | 6.7% | 52.9% | 35.6% | 6.2% | 0.0% | 0.0% | 0.0% | 0.0% | 0.1% | 0.0% | 0.0% | 0.1% |
| llama3.1:8b | gemma3:12b | 2277 | 222.1 | 97.1% | 2.9% | 62.5% | 31.3% | 50.9% | 1.3% | 0.2% | 7.5% | 0.0% | 28.5% | 0.1% | 4.3% | 10.8% |
| llama3.1:8b | llama3.1:8b (baseline) | 10395 | 226.1 | 96.9% | 3.1% | 60.8% | 34.2% | 48.2% | 1.6% | 0.3% | 9.6% | 0.0% | 27.1% | 0.1% | 5.3% | 12.2% |
| llama3.1:8b | qwen3:8b | 9306 | 221.9 | 96.2% | 3.8% | 60.9% | 33.8% | 48.9% | 1.7% | 0.3% | 9.6% | 0.0% | 27.4% | 0.2% | 5.5% | 12.8% |
| qwen3:8b | gemma3:12b | 2277 | 128.6 | 93.7% | 6.3% | 47.7% | 14.0% | 59.9% | 0.7% | 0.0% | 0.9% | 0.0% | 4.1% | 0.0% | 0.0% | 8.5% |
| qwen3:8b | llama3.1:8b | 10395 | 103.2 | 84.4% | 15.6% | 46.8% | 14.3% | 38.9% | 0.2% | 0.0% | 0.6% | 0.0% | 2.1% | 0.0% | 0.0% | 16.7% |
| qwen3:8b | qwen3:8b (baseline) | 9306 | 109.6 | 90.0% | 10.0% | 45.6% | 18.2% | 42.7% | 0.0% | 0.0% | 0.7% | 0.0% | 2.0% | 0.0% | 0.0% | 10.8% |

## Table 3. Reading turn: % upvoted by the reader's stance on the post's topic

| Reader AI | Posts by | LOVE | LIKE | NEUTRAL | DISLIKE | HATE |
|---|---|---|---|---|---|---|
| gemma3:12b | gemma3:12b | 86.7% | 88.3% | 71.7% | 6.7% | 6.5% |
| gemma3:12b | llama3.1:8b | 91.3% | 93.4% | 65.1% | 6.8% | 1.7% |
| gemma3:12b | qwen3:8b | 91.1% | 91.5% | 67.9% | 10.9% | 5.1% |
| llama3.1:8b | gemma3:12b | 97.1% | 98.9% | 85.9% | 13.0% | 19.1% |
| llama3.1:8b | llama3.1:8b | 98.2% | 98.6% | 86.8% | 10.2% | 12.1% |
| llama3.1:8b | qwen3:8b | 96.9% | 98.5% | 85.9% | 12.0% | 12.8% |
| qwen3:8b | gemma3:12b | 80.2% | 75.5% | 49.3% | 18.9% | 16.3% |
| qwen3:8b | llama3.1:8b | 80.9% | 80.0% | 49.9% | 14.1% | 10.6% |
| qwen3:8b | qwen3:8b | 78.7% | 77.4% | 48.5% | 13.9% | 11.0% |

## Own-AI bias (derived; read Table 2 first)

For AIs i and j: (i reading i's posts - j reading i's posts) - (i reading j's posts - j reading j's posts). Positive = i favours its own AI's posts beyond simply being more generous. Points per 100 screens.

**Total engagement** = every action except 'do nothing', per 100 screens (the main measure, LD-43). **Engaged** = % of screens with at least one action.

| i | j | **Total engagement: bias (95% range)** | **Engaged: bias (95% range)** | Upvote: bias (95% range) |
|---|---|---|---|---|
| gemma3:12b | llama3.1:8b | +5.9 (-4.4 to +16.9) | +1.9 (-2.0 to +5.6) | -1.3 (-8.5 to +6.2) |
| gemma3:12b | qwen3:8b | -19.3 (-30.2 to -8.9) | -3.1 (-8.1 to +1.3) | -3.4 (-11.8 to +5.0) |
| llama3.1:8b | qwen3:8b | +10.5 (+0.4 to +20.1) | +6.3 (+2.8 to +9.6) | -1.3 (-5.6 to +2.7) |

## Noise floor (stage 1b): same AI, same posts, re-read with fresh randomness

| AI | Screens compared | Same engaged / not decision | Same number of actions | Total engagement first / re-read (per 100 screens) | Same upvote decision | Upvote rate first / re-read |
|---|---|---|---|---|---|---|
| gemma3:12b | 400 | 95.5% | 92.5% | 96.2 / 96.8 | 96.5% | 55.0% / 54.0% |
| llama3.1:8b | 400 | 95.5% | 28.2% | 229.2 / 224.5 | 89.2% | 60.0% / 61.2% |
| qwen3:8b | 400 | 95.2% | 75.8% | 108.5 / 109.8 | 78.5% | 39.8% / 43.8% |
