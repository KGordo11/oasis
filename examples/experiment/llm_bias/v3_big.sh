#!/bin/bash
# The V3 big sim (log 14.46), per round:
#   arm 1  data/llm_bias/v3/          V3 (--v3), V1 menu order: posting, baselines, cross tests, noise floor (v2_night.py)
#   arm 2  data/llm_bias/v3_flipped/  the order study: arm 1's SAME posts, read with the flipped menu (least-used first)
# Resumable: a rerun skips every step already done. Last line: "BIG DONE".
#   ROUNDS="101" AGENTS=100 bash examples/experiment/llm_bias/v3_big.sh
set -eu
cd "$(dirname "$0")/../../.."
B=${V3_ROOT:-$PWD/data/llm_bias}/v3 F=${V3_ROOT:-$PWD/data/llm_bias}/v3_flipped
mkdir -p "$B" "$F"
exec 9>"$B/.lock"; flock -n 9 || { echo "the big sim is already running -- not starting a second copy"; exit 1; }
export MANAGE_SERVERS=${MANAGE_SERVERS:-1} PARALLEL=${PARALLEL:-8} PY=${PY:-python3} PUSH=0 CHECKPOINT=0 \
       STOP_OLLAMA=${STOP_OLLAMA:-1} STOP="$(python3 -c "import datetime as d; print((d.datetime.now() + d.timedelta(days=20)).strftime('%Y-%m-%d %H:%M'))")"
for r in ${ROUNDS:-101}; do
  echo "$(date '+%F %T') round $r arm 1: V3"
  DATA_DIR=$B EXTRA="--v3" ROUNDS=$r $PY examples/experiment/llm_bias/v2_night.py
  mkdir -p "$F/r$r"
  for f in "$B/r$r"/posting_*; do [ -e "$F/r$r/${f##*/}" ] || cp "$f" "$F/r$r/"; done
  echo "$(date '+%F %T') round $r arm 2: V3 + flipped menu, same posts"
  DATA_DIR=$F EXTRA="--v3 --menu-order flipped" ROUNDS=$r TURNS=read NOISE=0 $PY examples/experiment/llm_bias/v2_night.py
done
echo "BIG DONE"
