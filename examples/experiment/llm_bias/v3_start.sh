#!/bin/bash
# Part 1 of the big sim, in a safe order (log 14.49, 10-23 lesson: part 1 was started while the preflight was still
# switching the AI servers, and 30k screens came back "Connection refused"). The real-AI preflight with the V3 settings
# runs first; only on ALL CLEAR is the watchdog cron added and part 1 started.
#   source ~/llm_bias/env_llamacpp.sh && setsid nohup bash examples/experiment/llm_bias/v3_start.sh > ~/llm_bias/logs/v3_big.txt 2>&1 < /dev/null &
set -u
cd "$(dirname "$0")/../../.."
L=$HOME/llm_bias/logs
echo "$(date '+%F %T') preflight with the V3 settings -> $L/preflight_v3.txt"
PREFLIGHT_EXTRA="--v3" PREFLIGHT_SLICES=0 python3 examples/experiment/llm_bias/preflight_v2.py > "$L/preflight_v3.txt" 2>&1 \
  || { echo "$(date '+%F %T') PREFLIGHT NOT SAFE -- part 1 NOT started (see $L/preflight_v3.txt)"; exit 1; }
echo "$(date '+%F %T') preflight ALL CLEAR -> watchdog on, part 1 starts"
W="*/10 * * * * bash $HOME/llm_bias/oasis/examples/experiment/llm_bias/v3_watchdog.sh v3_big.sh v3_big.txt 'ARM 1 DONE'"
(crontab -l 2>/dev/null | grep -v v3_watchdog; echo "$W") | crontab -
exec env ARM=1 ROUNDS=101 AGENTS=100 bash examples/experiment/llm_bias/v3_big.sh
