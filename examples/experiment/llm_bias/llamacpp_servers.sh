#!/bin/bash
# Start / stop one llama.cpp server per model for LLM Bias v2 (LD-41), using the model files Ollama already downloaded.
#   examples/experiment/llm_bias/llamacpp_servers.sh start     (then:  source ~/llm_bias/env_llamacpp.sh)
#   examples/experiment/llm_bias/llamacpp_servers.sh stop | status
# Same settings for every model: 8 slots of 8192 tokens each (as Ollama), flash attention, all layers on the GPU,
# the model file's own chat template (--jinja). Ports: qwen 11601, llama 11602, gemma 11603.
set -u
ROOT=${LLM_BIAS_HOME:-$HOME/llm_bias}
BIN=$ROOT/engines/llama.cpp/build/bin/llama-server
MAN=$ROOT/models/manifests/registry.ollama.ai/library
SLOTS=${SLOTS:-8}
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH:-}
declare -A PORT=([qwen3:8b]=11601 [llama3.1:8b]=11602 [gemma3:12b]=11603)

blob() {  # model name -> its model file, read from Ollama's manifest (no Ollama server needed)
  python3 -c "import json,sys; m=json.load(open(sys.argv[1])); print([l['digest'] for l in m['layers'] if l['mediaType'].endswith('.model')][0].replace(':','-'))" "$MAN/${1%%:*}/${1#*:}"
}

stop_all() {  # LB-v2-7: ask every server to stop, WAIT until it has exited (GPU memory released), force any straggler
  pkill -u "$USER" -f "llama-server -m" || return 0
  for i in $(seq 1 30); do pgrep -u "$USER" -f "llama-server -m" >/dev/null || return 0; sleep 1; done
  pkill -9 -u "$USER" -f "llama-server -m"; sleep 2
}

start_one() {  # start one model's server and wait until it answers (3-min limit)
  local m=$1 p=${PORT[$1]} f alt=$ROOT/models/gguf/${1/:/-}.gguf
  if [ -f "$alt" ]; then f=$alt; else f=$ROOT/models/blobs/$(blob "$m"); fi
  [ -f "$f" ] || { echo "missing model file for $m: $f"; exit 1; }
  nohup "$BIN" -m "$f" --alias "$m" --host 127.0.0.1 --port "$p" -np "$SLOTS" -c $((SLOTS * 8192)) \
    -fa on --jinja -ngl 99 > "$ROOT/logs/llamacpp_${m%%:*}.log" 2>&1 &
  for i in $(seq 1 90); do curl -s "127.0.0.1:$p/health" | grep -q ok && break; sleep 2; done
  curl -s "127.0.0.1:$p/health" | grep -q ok && echo "READY $m (only this model loaded)" || { echo "FAILED $m"; exit 1; }
}

case "${1:-status}" in
only)
  # LD-42: keep ONE model in memory (the one the current step uses) so the shared Spark keeps ~95 GB free
  m=${2:?usage: $0 only <model>}
  if curl -s "127.0.0.1:${PORT[$m]}/health" | grep -q ok && [ "$(pgrep -u "$USER" -fc "llama-server -m")" = "1" ]; then
    echo "already only $m"; exit 0; fi
  stop_all
  start_one "$m" ;;
start)
  if pgrep -u "$USER" -f "llama-server -m" >/dev/null; then echo "servers already running -- run: $0 stop   first"; exit 1; fi
  urls="{"
  for m in qwen3:8b llama3.1:8b gemma3:12b; do
    p=${PORT[$m]}
    # a standard GGUF in models/gguf/<name>.gguf (e.g. gemma3-12b.gguf) wins over Ollama's file -- for a model whose
    # Ollama file llama.cpp cannot read
    alt=$ROOT/models/gguf/${m/:/-}.gguf
    if [ -f "$alt" ]; then f=$alt; else f=$ROOT/models/blobs/$(blob "$m"); fi
    [ -f "$f" ] || { echo "missing model file for $m: $f"; exit 1; }
    nohup "$BIN" -m "$f" --alias "$m" --host 127.0.0.1 --port "$p" -np "$SLOTS" -c $((SLOTS * 8192)) \
      -fa on --jinja -ngl 99 > "$ROOT/logs/llamacpp_${m%%:*}.log" 2>&1 &
    echo "starting $m on port $p ($f)"
    urls="$urls\"$m\": \"http://127.0.0.1:$p\", "
  done
  urls="${urls%, }}"
  for m in qwen3:8b llama3.1:8b gemma3:12b; do
    for i in $(seq 1 90); do curl -s "127.0.0.1:${PORT[$m]}/health" | grep -q ok && break; sleep 2; done
    if curl -s "127.0.0.1:${PORT[$m]}/health" | grep -q ok; then echo "READY $m"
    else echo "FAILED $m -- see: tail -30 $ROOT/logs/llamacpp_${m%%:*}.log"; exit 1; fi
  done
  printf 'export LLM_BACKEND=llamacpp\nexport LLAMACPP_URLS=%q\n' "$urls" > "$ROOT/env_llamacpp.sh"
  echo "wrote $ROOT/env_llamacpp.sh -- now run:  source $ROOT/env_llamacpp.sh" ;;
stop)
  stop_all; pgrep -u "$USER" -f "llama-server -m" >/dev/null && echo "STILL RUNNING" || echo "stopped" ;;
status)
  for m in qwen3:8b llama3.1:8b gemma3:12b; do
    printf '%-12s port %s: %s\n' "$m" "${PORT[$m]}" "$(curl -s 127.0.0.1:${PORT[$m]}/health || echo down)"
  done ;;
esac
