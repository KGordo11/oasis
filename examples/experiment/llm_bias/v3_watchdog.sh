#!/bin/bash
# cron, every 10 min (log 14.43): restart the V3 chain if it died before finishing (resume is safe, LB-v2-4).
# Gives up after 3 restarts so a real bug cannot loop. Install: (crontab -l; echo "*/10 * * * * bash $HOME/llm_bias/oasis/examples/experiment/llm_bias/v3_watchdog.sh") | crontab -
export USER=$(id -un)
OUT=$HOME/llm_bias/logs/v3_single.txt WD=$HOME/llm_bias/logs/v3_watchdog.txt
tail -1 "$OUT" 2>/dev/null | grep -q "CHAIN DONE" && exit 0
pgrep -u "$USER" -f 'v3_(chain|test)\.sh' > /dev/null && exit 0
[ "$(grep -c restarting "$WD" 2>/dev/null || echo 0)" -ge 3 ] && exit 0
pkill -u "$USER" -f run_v2.py; pkill -u "$USER" -f v2_night.py; sleep 3
echo "$(date '+%F %T') WATCHDOG: chain was dead -> restarting" >> "$WD"
cd "$HOME/llm_bias/oasis" && . "$HOME/llm_bias/env_llamacpp.sh" && \
  setsid nohup bash examples/experiment/llm_bias/v3_chain.sh >> "$OUT" 2>&1 < /dev/null &
