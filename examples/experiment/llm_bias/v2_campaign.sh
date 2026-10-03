#!/bin/bash
# LLM Bias v2 overnight campaign (log Part 14). Each round: every model plays all 100 pinned users on the same
# seed posts (run_v2.py). Model order rotates each round so no model always runs first or last in the night.
# Stops before starting a run that would not finish by STOP_AT. Safe to re-run: finished runs are skipped and an
# interrupted run resumes where it stopped.
#   ROUNDS="1 2 3" STOP_AT="2026-10-03 08:00" examples/experiment/llm_bias/v2_campaign.sh
set -u
cd "$(dirname "$0")/../../.."
P=./oasis-env/bin/python; S=examples/experiment/llm_bias
MODELS=(${MODELS:-qwen3:4b gemma4:e2b llama3.2:3b})
STOP=$(date -j -f "%Y-%m-%d %H:%M" "${STOP_AT:?set STOP_AT, e.g. 2026-10-03 08:00}" +%s)
curl -s localhost:11434/api/tags >/dev/null || { echo "Ollama is down"; exit 2; }
for R in ${ROUNDS:-$(seq 1 30)}; do
  N=${#MODELS[@]}
  for ((i = 0; i < N; i++)); do
    M=${MODELS[$(( (i + R) % N ))]}
    L="v2_r$(printf %03d $R)_${M/:/-}"
    [ -f "data/llm_bias/v2/runs/$L/manifest.json" ] && { echo "skip $L"; continue; }
    NEED=$(cat "data/llm_bias/v2/run_s_${M/:/-}.txt" 2>/dev/null || echo 0)
    LEFT=$(( STOP - $(date +%s) ))
    [ "$LEFT" -lt "$NEED" ] && { echo "$(date '+%F %T') stop: $L needs ~${NEED}s, ${LEFT}s left"; exit 0; }
    echo "$(date '+%F %T') start $L"
    T0=$(date +%s)
    $P $S/run_v2.py --round "$R" --model "$M" --no-replay > "/tmp/$L.log" 2>&1
    RC=$?
    # the OASIS database is rebuilt from the records in the background (no model calls), so the next run starts now
    [ $RC -eq 0 ] && (taskpolicy -b $P $S/run_v2.py --round "$R" --model "$M" --replay-only >> "/tmp/$L.log" 2>&1 &)
    echo "$(date '+%F %T') end $L rc=$RC"; grep -E "^[0-9:]+ done " "/tmp/$L.log" | tail -1
    [ $RC -eq 0 ] && echo $(( $(date +%s) - T0 )) > "data/llm_bias/v2/run_s_${M/:/-}.txt"
  done
  (  # analysis + commit in the background, at low priority, so the next round starts at once
  taskpolicy -b $P $S/analyze_v2.py > /dev/null 2>&1 || true
  git add data/llm_bias/v2/runs/v2_r$(printf %03d $R)_* data/llm_bias/v2/seedbank_r$(printf %03d $R).jsonl \
          data/llm_bias/v2/summary.md data/llm_bias/v2/run_s_*.txt 2>/dev/null
  git commit -qm "LLM Bias v2 round $R (100 users x 3 models)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q origin llm-bias
  echo "$(date '+%F %T') round $R committed"
  ) >> data/llm_bias/v2/campaign_after.log 2>&1 &
  echo "$(date '+%F %T') round $R done"
done
echo "$(date '+%F %T') campaign end"
