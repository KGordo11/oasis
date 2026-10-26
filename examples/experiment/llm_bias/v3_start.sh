#!/bin/bash
# One part of the big sim, in a safe order (log 14.49, 10-23 lesson: part 1 was started while the preflight was still
# switching the AI servers, and 30k screens came back "Connection refused"). The real-AI preflight with the part's
# settings runs first; only on ALL CLEAR is the watchdog cron added and the part started.
#   part 1:  source ~/llm_bias/env_llamacpp.sh && setsid nohup bash examples/experiment/llm_bias/v3_start.sh > ~/llm_bias/logs/v3_big.txt 2>&1 < /dev/null &
#   part 2:  ... ARM=2 ... v3_start.sh > ~/llm_bias/logs/v3_big_part2.txt ...   (needs "ARM 1 DONE"; menu ranked first)
set -u
cd "$(dirname "$0")/../../.."
L=$HOME/llm_bias/logs ARM=${ARM:-1} EXTRA="--v3" LOG=v3_big.txt
if [ "$ARM" = 2 ]; then
  tail -1 "$L/v3_big.txt" | grep -q "ARM 1 DONE" || { echo "part 1 is not done (no 'ARM 1 DONE') -- part 2 NOT started"; exit 1; }
  M=$PWD/data/llm_bias/v3_flipped/r101/menu.txt LOG=v3_big_part2.txt EXTRA="--v3 --menu-file $M"
  [ -e "$M" ] || python3 examples/experiment/llm_bias/rank_menu.py data/llm_bias/v3/r101 "$M" || exit 1
  [ -e "$L/watchdog_v3_big.txt" ] && mv "$L/watchdog_v3_big.txt" "$L/watchdog_v3_big_part1.txt"  # fresh 3-restart budget
fi
echo "$(date '+%F %T') part $ARM: preflight with '$EXTRA' -> $L/preflight_v3_part$ARM.txt"
PREFLIGHT_EXTRA="$EXTRA" PREFLIGHT_SLICES=0 python3 examples/experiment/llm_bias/preflight_v2.py > "$L/preflight_v3_part$ARM.txt" 2>&1 \
  || { echo "$(date '+%F %T') PREFLIGHT NOT SAFE -- part $ARM NOT started (see $L/preflight_v3_part$ARM.txt)"; exit 1; }
echo "$(date '+%F %T') preflight ALL CLEAR -> watchdog on, part $ARM starts"
W="*/10 * * * * ARM=$ARM bash $HOME/llm_bias/oasis/examples/experiment/llm_bias/v3_watchdog.sh v3_big.sh $LOG 'ARM $ARM DONE'"
(crontab -l 2>/dev/null | grep -v v3_watchdog; echo "$W") | crontab -
exec env ARM=$ARM ROUNDS=101 AGENTS=100 bash examples/experiment/llm_bias/v3_big.sh
