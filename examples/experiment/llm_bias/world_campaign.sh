#!/bin/bash
# Design v2 campaign: for each post bank (seed), run the two rotation worlds, then analyse.
#
# IN PLAIN WORDS: seed = a fresh set of 50 posts (2 models x 5 topics x 5 posts).
# World 0: even personas played by llama, odd by gemma. World 1: swapped. After
# both, every one of the SAME 99 pinned personas has been played by both models
# on the same posts. A finished world (manifest has "finished_at") is skipped;
# an unfinished one is resumed, never restarted -- so this is safe to re-launch.
#
#   SEEDS="10 11 12" examples/experiment/llm_bias/world_campaign.sh
#
# Standing rules (RESEARCH_LOG Part 5): Ollama at CONTEXT_LENGTH=8192 (B-28);
# no other inference while this runs (B-32); do not edit the harness mid-campaign.
set -u
cd "$(dirname "$0")/../../.."
P=./oasis-env/bin/python; S=examples/experiment/llm_bias
SEEDS=${SEEDS:-"10 11 12 13"}; PREFIX=${PREFIX:-v2}; AGENTS=${AGENTS:-99}
JUDGES=${JUDGES:-llama3.1:8b,gemma4:e2b}
curl -s localhost:11434/api/tags >/dev/null || { echo "Ollama is down"; exit 2; }
echo "$(date '+%F %T') campaign start seeds=[$SEEDS] agents=$AGENTS judges=$JUDGES"
for SEED in $SEEDS; do
  for W in 0 1; do
    L="${PREFIX}_s${SEED}_w${W}"
    M="data/llm_bias/worlds/$L/manifest.json"
    if [ -f "$M" ] && grep -q finished_at "$M"; then echo "skip $L (finished)"; continue; fi
    R=""; [ -d "data/llm_bias/worlds/$L" ] && R="--resume"
    echo "$(date '+%F %T') start $L $R"
    $P $S/run_world.py --label "$L" --seed "$SEED" --world "$W" --agents "$AGENTS" --judges "$JUDGES" \
       --authors "$JUDGES" $R > "/tmp/llm_bias_$L.log" 2>&1
    rc=$?
    grep -E "done [0-9]+ in|WARNING|Error" "/tmp/llm_bias_$L.log" | tail -n 3
    echo "$(date '+%F %T') end $L rc=$rc"
  done
  $P $S/analyze_world.py --prefix "${PREFIX}_" --out "data/llm_bias/analysis_${PREFIX}.json" \
     > "data/llm_bias/analysis_${PREFIX}.txt" 2>&1
  echo "$(date '+%F %T') analysis after seed $SEED: data/llm_bias/analysis_${PREFIX}.txt"
done
echo "$(date '+%F %T') campaign end"
