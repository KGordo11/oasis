# LLM Bias v2 results

Rounds: [1]. Screens: 300 (4 unreadable).

## Table 1. Posting turn (empty feed, every action available, nobody told to post)

| AI playing the users | Users | Users who posted | Posts written | Posts by topic | Other actions taken |
|---|---|---|---|---|---|
| llama3.1:8b | 100 | 96 | 96 | r/politics 32, r/technology 20, r/business 20, r/sports 12, r/entertainment 12 | search_user 20, follow 13, create_comment 3, search_posts 3, do_nothing 2, refresh 2 |
| mistral:7b | 100 | 0 | 0 |  | search_posts 32, refresh 6, trend 4 |
| qwen3:8b | 100 | 88 | 101 | politics 22, business 21, sports 15, r/politics 12, technology 12, entertainment 10, r/entertainment 5, r/sports 4 | like_post 7, do_nothing 7, refresh 6, create_comment 4 |

## Table 2. Reading turn: reader AI x whose posts -> % of screens with each action

| Reader AI | Posts by | Screens | Did nothing | like_post | dislike_post | create_comment | repost | quote_post | follow | mute | report_post | create_post | search_posts | do_nothing |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

## Table 3. Reading turn: % upvoted by the reader's stance on the post's topic

| Reader AI | Posts by | LOVE | LIKE | NEUTRAL | DISLIKE | HATE |
|---|---|---|---|---|---|---|

## Own-AI bias (derived; read Table 2 first)

For AIs i and j: (i reading i's posts - j reading i's posts) - (i reading j's posts - j reading j's posts). Positive = i favours its own AI's posts beyond simply being more generous. Points per 100 screens.

| i | j | Upvote: bias (95% range) | Did anything: bias (95% range) |
|---|---|---|---|
| llama3.1:8b | mistral:7b | - | - |
| llama3.1:8b | qwen3:8b | - | - |
| mistral:7b | qwen3:8b | - | - |
