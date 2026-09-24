#!/bin/bash
# Run every judge model over ONE post bank (seed), one after another.
#
# IN PLAIN WORDS: this is the crossover. Each judge model plays the same N
# personas on the same posts in the same order; only the judge changes. A run
# whose manifest already has "finished_at" is skipped, so this is safe to
# re-launch after a crash -- it never repeats finished work. An unfinished run
# is started again from scratch (--overwrite), never half-merged.
#
#   SEED=1 AGENTS=99 ROUNDS=8 PREFIX=main examples/experiment/llm_bias/campaign.sh
#
# Rules carried over from Sim 4 (RESEARCH_LOG Part 5):
#   * Ollama must be started with OLLAMA_CONTEXT_LENGTH=8192 (B-28); llm.py also
#     sets num_ctx on every request and flags any prompt near the limit.
#   * No other inference while this runs (B-32: a busy machine cost a run 2.16x).
#   * Do not change the harness mid-campaign; a changed run is a different condition.
set -u
cd "$(dirname "$0")/../../.."
P=./oasis-env/bin/python
S=examples/experiment/llm_bias
SEED=${SEED:-1}; AGENTS=${AGENTS:-99}; ROUNDS=${ROUNDS:-8}; PREFIX=${PREFIX:-main}
TOPICS=${TOPICS:-personal_finance}
AUTHORS=${AUTHORS:-llama3.1:8b,gemma4:e2b,granite4.1:3b,qwen2.5:7b,mistral:7b,phi4-mini:3.8b,llama3.2:3b}
JUDGES=${JUDGES:-$AUTHORS}

if ! curl -s localhost:11434/api/tags >/dev/null; then
  echo "Ollama is down. Start: OLLAMA_NUM_PARALLEL=4 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=24h ollama serve"; exit 2
fi

echo "$(date '+%F %T') campaign start seed=$SEED agents=$AGENTS rounds=$ROUNDS topics=$TOPICS judges=$JUDGES"
for J in ${JUDGES//,/ }; do
  L="${PREFIX}_s${SEED}_a${AGENTS}_r${ROUNDS}_$(echo "$J" | tr ':.' '__')"
  M="data/llm_bias/runs/$L/manifest.json"
  if [ -f "$M" ] && grep -q finished_at "$M"; then echo "skip $L (finished)"; continue; fi
  echo "$(date '+%F %T') start $L"
  $P $S/run_bias.py --label "$L" --overwrite --seed "$SEED" --judge "$J" --agents "$AGENTS" \
     --rounds "$ROUNDS" --topics "$TOPICS" --authors "$AUTHORS" > "/tmp/llm_bias_$L.log" 2>&1
  rc=$?
  grep -E " round [0-9]+:| done:|WARNING" "/tmp/llm_bias_$L.log" | tail -n 3
  echo "$(date '+%F %T') end $L rc=$rc"
done
echo "$(date '+%F %T') campaign end"
$P $S/analyze.py --seed "$SEED" --out "data/llm_bias/analysis_s${SEED}.json" > "data/llm_bias/analysis_s${SEED}.txt" 2>&1
echo "analysis written: data/llm_bias/analysis_s${SEED}.txt"
