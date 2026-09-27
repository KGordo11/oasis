#!/bin/bash
# LD-14 campaign: three AIs (llama3.1, gemma4, mistral) each write NATURAL posts (no length/format rules) and
# play people; scroll format; first 50 of the pinned 99; 3 rotation worlds per post set so every person is
# played by every AI on the same posts. Finished worlds are skipped, unfinished ones resumed. Labels v3_.
#   SEEDS="40 41 42" examples/experiment/llm_bias/v3_campaign.sh
set -u
cd "$(dirname "$0")/../../.."
P=./oasis-env/bin/python; S=examples/experiment/llm_bias
SEEDS=${SEEDS:-"40 41 42 43 44 45"}; AGENTS=${AGENTS:-50}
M3=llama3.1:8b,gemma4:e2b,mistral:7b
curl -s localhost:11434/api/tags >/dev/null || { echo "Ollama is down"; exit 2; }
echo "$(date '+%F %T') v3 campaign start seeds=[$SEEDS] agents=$AGENTS"
for SEED in $SEEDS; do
  for W in 0 1 2; do
    L="v3_s${SEED}_w${W}"
    M="data/llm_bias/worlds/$L/manifest.json"
    if [ -f "$M" ] && grep -q finished_at "$M"; then echo "skip $L (finished)"; continue; fi
    R=""; [ -d "data/llm_bias/worlds/$L" ] && R="--resume"
    echo "$(date '+%F %T') start $L $R"
    $P $S/run_world.py --label "$L" --seed "$SEED" --world "$W" --agents "$AGENTS" --judges $M3 --authors $M3 \
       --natural-posts --complete-slots --post-retries 4 $R > "/tmp/llm_bias_$L.log" 2>&1
    rc=$?
    grep -E "done [0-9]+ in|WARNING|Error" "/tmp/llm_bias_$L.log" | tail -n 4
    echo "$(date '+%F %T') end $L rc=$rc"
  done
  $P $S/check_world.py --prefix "v3_s${SEED}_" >> data/llm_bias/v3_checks.txt 2>&1
  echo "$(date '+%F %T') post set $SEED done"
done
echo "$(date '+%F %T') v3 campaign end"
