#!/bin/bash
# Time-vs-agents sweep (design v2): the same post set (seed 10), world 0, at 10/25/50/75 users.
# Each size is a full standalone run, so the chart shows what a run of N agents really costs.
# Waits for world_campaign.sh to finish first -- never two inference jobs at once (B-32).
# Labels start sweep_, so analyze_world.py (prefix v2_) never mixes them into the result.
cd "$(dirname "$0")/../../.."
while pgrep -f world_campaign.sh >/dev/null; do sleep 60; done
for N in ${SIZES:-10 25 50 75}; do
  L="sweep_a${N}"
  M="data/llm_bias/worlds/$L/manifest.json"
  if [ -f "$M" ] && grep -q finished_at "$M"; then echo "skip $L"; continue; fi
  R=""; [ -d "data/llm_bias/worlds/$L" ] && R="--resume"
  echo "$(date '+%F %T') start $L"
  ./oasis-env/bin/python examples/experiment/llm_bias/run_world.py --label "$L" --seed 10 --world 0 --agents "$N" $R \
     > "/tmp/llm_bias_$L.log" 2>&1
  echo "$(date '+%F %T') end $L rc=$?"
done
echo "$(date '+%F %T') sweep done"
