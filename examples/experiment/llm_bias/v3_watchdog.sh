#!/bin/bash
# cron, every 10 min (log 14.43): restart a V3 run if it died before finishing (resume is safe, LB-v2-4).
# Gives up after 3 restarts so a real bug cannot loop. Args: script, log, done-marker (defaults = the V3 test chain).
# Install: (crontab -l; echo "*/10 * * * * bash $HOME/llm_bias/oasis/examples/experiment/llm_bias/v3_watchdog.sh") | crontab -
# Big sim:  ... v3_watchdog.sh v3_big.sh v3_big.txt 'BIG DONE'
export USER=$(id -un)
S=${1:-v3_chain.sh} OUT=$HOME/llm_bias/logs/${2:-v3_single.txt} DONE=${3:-CHAIN DONE}
WD=$HOME/llm_bias/logs/$([ "$S" = v3_chain.sh ] && echo v3_watchdog.txt || echo "watchdog_${S%.sh}.txt")
tail -1 "$OUT" 2>/dev/null | grep -q "$DONE" && exit 0
pgrep -u "$USER" -f "$([ "$S" = v3_chain.sh ] && echo 'v3_(chain|test)\.sh' || echo "$S")" > /dev/null && exit 0
[ "$(grep -c restarting "$WD" 2>/dev/null || echo 0)" -ge 3 ] && exit 0
pkill -u "$USER" -f run_v2.py; pkill -u "$USER" -f v2_night.py; sleep 3
echo "$(date '+%F %T') WATCHDOG: $S was dead -> restarting" >> "$WD"
cd "$HOME/llm_bias/oasis" && . "$HOME/llm_bias/env_llamacpp.sh" && \
  setsid nohup bash "examples/experiment/llm_bias/$S" >> "$OUT" 2>&1 < /dev/null &
