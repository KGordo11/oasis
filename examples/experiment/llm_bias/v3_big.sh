#!/bin/bash
# The V3 big sim (log 14.46, 14.48), one part at a time (Gordon 10-23: run part 1, examine its data, then part 2):
#   ARM=1  data/llm_bias/v3/          V3 (--v3), V1 menu order: posting, baselines, cross tests, noise floor
#   ARM=2  data/llm_bias/v3_flipped/  the order study: part 1's SAME posts, read with the menu ranked from part 1's
#                                     data (rank_menu.py: least-used actions at the top, most-used at the bottom)
# Resumable: a rerun skips every step already done. Last line: "ARM 1 DONE" / "ARM 2 DONE".
#   ARM=1 ROUNDS="101" AGENTS=100 bash examples/experiment/llm_bias/v3_big.sh
set -eu
cd "$(dirname "$0")/../../.."
B=${V3_ROOT:-$PWD/data/llm_bias}/v3 F=${V3_ROOT:-$PWD/data/llm_bias}/v3_flipped
ARM=${ARM:-1}  # the watchdog restarts with no env: part 1
mkdir -p "$B" "$F"
exec 9>"$B/.lock"; flock -n 9 || { echo "the big sim is already running -- not starting a second copy"; exit 1; }
export SLICES=${SLICES:-0} MANAGE_SERVERS=${MANAGE_SERVERS:-1} PARALLEL=${PARALLEL:-8} PY=${PY:-python3} PUSH=0 CHECKPOINT=0 \
       STOP_OLLAMA=${STOP_OLLAMA:-1} STOP="$(python3 -c "import datetime as d; print((d.datetime.now() + d.timedelta(days=20)).strftime('%Y-%m-%d %H:%M'))")"
for r in ${ROUNDS:-101}; do
  if [ "$ARM" = 1 ]; then
    echo "$(date '+%F %T') round $r part 1: V3"
    DATA_DIR=$B EXTRA="--v3" ROUNDS=$r $PY examples/experiment/llm_bias/v2_night.py
  else
    mkdir -p "$F/r$r"
    for f in "$B/r$r"/posting_*; do [ -e "$F/r$r/${f##*/}" ] || cp "$f" "$F/r$r/"; done
    [ -e "$F/r$r/menu.txt" ] || $PY examples/experiment/llm_bias/rank_menu.py "$B/r$r" "$F/r$r/menu.txt"
    echo "$(date '+%F %T') round $r part 2: V3 + menu ranked from part 1, same posts"
    DATA_DIR=$F EXTRA="--v3 --menu-file $F/r$r/menu.txt" ROUNDS=$r TURNS=read NOISE=0 $PY examples/experiment/llm_bias/v2_night.py
  fi
done
echo "ARM $ARM DONE"
