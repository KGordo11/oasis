#!/bin/bash
# Gordon 2026-09-30 (LD-18): TWO AIs, 100 pinned users, 5 subreddits.
# Every round: each AI writes 5 NEW natural posts per topic (50 posts, new seed = new briefs = new posts);
# then AI A plays all 100 users through all 50 posts (one by one, upvote/downvote/nothing, author hidden),
# then AI B plays the same 100 users through the same 50 posts. Rounds are independent.
#   A=gemma4:e2b B=llama3.2:3b ROUNDS="1 2 3" STOP_AT="2026-10-01 15:00" two_ai_campaign.sh
set -u
cd "$(dirname "$0")/../../.."
P=./oasis-env/bin/python; S=examples/experiment/llm_bias
STOP=$(date -j -f "%Y-%m-%d %H:%M" "${STOP_AT:-2026-10-01 15:00}" +%s)
curl -s localhost:11434/api/tags >/dev/null || { echo "Ollama is down"; exit 2; }
for R in ${ROUNDS:-$(seq 1 15)}; do
  SEED=$((200 + R))
  for J in "$A" "$B"; do
    L="two_r$(printf %02d $R)_${J%%:*}"
    M="data/llm_bias/worlds/$L/manifest.json"
    grep -qs finished_at "$M" && { echo "skip $L"; continue; }
    LEFT=$(( STOP - $(date +%s) ))
    if [ -f data/llm_bias/two_ai_round_s.txt ] && [ "$J" = "$A" ] && [ ! -d "data/llm_bias/worlds/$L" ]; then
      NEED=$(cat data/llm_bias/two_ai_round_s.txt)
      [ "$LEFT" -lt "$NEED" ] && { echo "$(date '+%F %T') stop: round $R needs ${NEED}s, ${LEFT}s left"; exit 0; }
    fi
    RES=""; [ -d "data/llm_bias/worlds/$L" ] && RES="--resume"
    echo "$(date '+%F %T') start $L seed=$SEED $RES"
    $P $S/run_world.py --label "$L" --seed "$SEED" --judges "$J" --authors "$A,$B" --agents 100 \
       --natural-posts --complete-slots --post-retries 4 $RES > "/tmp/llm_bias_$L.log" 2>&1
    echo "$(date '+%F %T') end $L rc=$?"; grep -E "done [0-9]+ in|WARNING" "/tmp/llm_bias_$L.log" | tail -3
  done
  echo "$(date '+%F %T') round $R done"
  $S/two_ai_after_round.sh "$R" >> data/llm_bias/two_ai_after.log 2>&1
done
echo "$(date '+%F %T') campaign end"
