#!/bin/bash
# LD-13 A/B campaign: side-by-side (pair) vs scroll, on the SAME length-matched posts and the SAME 50 people.
#
# IN PLAIN WORDS: each seed is a fresh set of posts written under the length rule (ask 75-85 words, reject
# outside 65-95). The first 50 of the pinned 99 people meet those posts twice: once scrolling one post at a
# time, once seeing the two posts of each brief side by side. Each format runs both rotation worlds, so every
# person is played by both models in both formats. Which format goes first alternates by seed (even: scroll
# first), so a slow drift over the day cannot line up with the format. Finished worlds are skipped and an
# unfinished one is resumed, so this is safe to re-launch. Labels start ab_, never mixed with v2_.
#
#   SEEDS="20 21 22" examples/experiment/llm_bias/ab_campaign.sh
set -u
cd "$(dirname "$0")/../../.."
P=./oasis-env/bin/python; S=examples/experiment/llm_bias
SEEDS=${SEEDS:-"20 21 22 23 24 25 26"}; AGENTS=${AGENTS:-50}
LEN="--length-band 75,85 --length-enforce 65,95 --post-retries 8 --complete-slots"
curl -s localhost:11434/api/tags >/dev/null || { echo "Ollama is down"; exit 2; }
echo "$(date '+%F %T') A/B campaign start seeds=[$SEEDS] agents=$AGENTS"
for SEED in $SEEDS; do
  if [ $((SEED % 2)) -eq 0 ]; then FORMATS="scroll pair"; else FORMATS="pair scroll"; fi
  for F in $FORMATS; do
    for W in 0 1; do
      L="ab_s${SEED}_${F}_w${W}"
      M="data/llm_bias/worlds/$L/manifest.json"
      if [ -f "$M" ] && grep -q finished_at "$M"; then echo "skip $L (finished)"; continue; fi
      R=""; [ -d "data/llm_bias/worlds/$L" ] && R="--resume"
      NP=80; [ "$F" = pair ] && NP=120
      echo "$(date '+%F %T') start $L $R"
      $P $S/run_world.py --label "$L" --seed "$SEED" --world "$W" --agents "$AGENTS" --format "$F" \
         --num-predict $NP $LEN $R > "/tmp/llm_bias_$L.log" 2>&1
      rc=$?
      grep -E "done [0-9]+ in|WARNING|Error" "/tmp/llm_bias_$L.log" | tail -n 3
      echo "$(date '+%F %T') end $L rc=$rc"
    done
  done
  $P $S/check_world.py --prefix "ab_s${SEED}_" >> data/llm_bias/ab_checks.txt 2>&1
  echo "$(date '+%F %T') post set $SEED done (checks in data/llm_bias/ab_checks.txt)"
done
echo "$(date '+%F %T') A/B campaign end"
