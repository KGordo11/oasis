#!/bin/bash
# Slot test on the Spark (log 14.51, 14.54): seconds per screen with 8 / 16 / 32 / 64 users answered at once, screens
# like the sim (800 tokens in, 80 out), each AI in turn. For future runs only: part 2 keeps 8 slots to match part 1.
# Refuses while anything of ours uses the AI servers (14.50 lesson); run it between parts.
#   setsid nohup bash examples/experiment/llm_bias/slot_bench.sh > ~/llm_bias/logs/slot_bench.txt 2>&1 < /dev/null &
set -u
ROOT=${LLM_BIAS_HOME:-$HOME/llm_bias}
BIN=${BENCH_BIN:-$ROOT/engines/llama.cpp/build/bin/llama-batched-bench}
MAN=$ROOT/models/manifests/registry.ollama.ai/library
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}
pgrep -u "$(id -un)" -f "llama-server -m|v2_night.py|run_v2.py|preflight_v2.py|v3_big.sh" > /dev/null \
  && { echo "something of ours is using the AI servers -- slot test NOT run"; exit 1; }
[ -x "$BIN" ] || { echo "missing $BIN -- build it: cd $ROOT/engines/llama.cpp && cmake --build build --target llama-batched-bench -j"; exit 1; }
echo "$(date '+%F %T') slot test start"; nvidia-smi 2>/dev/null | grep -E 'MiB|%' | head -8  # other users' load
for m in qwen3:8b llama3.1:8b gemma3:12b; do
  f=$ROOT/models/gguf/${m/:/-}.gguf
  [ -f "$f" ] || f=$ROOT/models/blobs/$(python3 -c "import json,sys; m=json.load(open(sys.argv[1])); print([l['digest'] for l in m['layers'] if l['mediaType'].endswith('.model')][0].replace(':','-'))" "$MAN/${m%%:*}/${m#*:}")
  echo "== $m ($(date '+%T'))"
  "$BIN" -m "$f" -c 57344 -npp 800 -ntg 80 -npl 8,16,32,64 -fa on -ngl 99 2>&1 | grep -E '^\||error|failed' \
    || echo "FAILED $m (no result table)"
done
echo "$(date '+%F %T') SLOT TEST DONE"
