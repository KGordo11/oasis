#!/bin/bash
# Gordon 2026-09-30: ONE AI (gemma4:e2b, fastest) plays all 100 pinned users; each user scrolls 5 subreddits
# (15 posts each: 5 by llama, 5 by gemma, 5 by mistral, natural posts) and upvotes / downvotes / does nothing.
#   SEEDS="40 41" examples/experiment/llm_bias/one_ai_campaign.sh
set -u
cd "$(dirname "$0")/../../.."
P=./oasis-env/bin/python; S=examples/experiment/llm_bias
for SEED in ${SEEDS:-40 41 42 43 44 45}; do
  L="one_s${SEED}"; R=""; [ -d "data/llm_bias/worlds/$L" ] && R="--resume"
  grep -qs finished_at "data/llm_bias/worlds/$L/manifest.json" && { echo "skip $L"; continue; }
  echo "$(date '+%F %T') start $L $R"
  $P $S/run_world.py --label "$L" --seed "$SEED" --judges gemma4:e2b --authors llama3.1:8b,gemma4:e2b,mistral:7b \
     --natural-posts --complete-slots --agents 100 $R > "/tmp/llm_bias_$L.log" 2>&1
  echo "$(date '+%F %T') end $L rc=$?"
done
