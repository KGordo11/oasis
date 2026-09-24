#!/bin/bash
# Speed benchmark (2026-09-24): scheduler (interleaved vs per-user) x flash attention (off vs on).
# Same workload every time: users 0-7, post set 10, world 0 (4 users per model, 400 decisions).
cd "$(dirname "$0")/../../.."
P=./oasis-env/bin/python; S=examples/experiment/llm_bias
serve() {  # restart Ollama with flash attention $1
  pkill -f "ollama serve"; sleep 3
  OLLAMA_FLASH_ATTENTION=$1 OLLAMA_NUM_PARALLEL=4 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=24h \
    nohup ollama serve > /tmp/ollama_serve.log 2>&1 &
  until curl -s localhost:11434/api/tags >/dev/null; do sleep 1; done
}
run() {  # label scheduler
  $P $S/run_world.py --label "$1" --overwrite --seed 10 --world 0 --agents 8 --scheduler "$2" --log-every 1000 \
    > "/tmp/$1.log" 2>&1
  grep -E "done [0-9]+ in" "/tmp/$1.log" | sed "s/^/$1 /"
}
serve 0
run speed_A_inter_fa0 interleaved
run speed_B_user_fa0 per-user
serve 1
run speed_C_user_fa1 per-user
run speed_D_inter_fa1 interleaved
serve 0
run speed_A2_inter_fa0 interleaved
echo BENCH_DONE
