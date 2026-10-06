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

case "${1:-status}" in
start)
  urls="{"
  for m in qwen3:8b llama3.1:8b gemma3:12b; do
    p=${PORT[$m]}; f=$ROOT/models/blobs/$(blob "$m")
    [ -f "$f" ] || { echo "missing model file for $m: $f"; exit 1; }
    nohup "$BIN" -m "$f" --alias "$m" --host 127.0.0.1 --port "$p" -np "$SLOTS" -c $((SLOTS * 8192)) \
      -fa on --jinja -ngl 99 > "$ROOT/logs/llamacpp_${m%%:*}.log" 2>&1 &
    echo "starting $m on port $p ($f)"
    urls="$urls\"$m\": \"http://127.0.0.1:$p\", "
  done
  urls="${urls%, }}"
  for m in qwen3:8b llama3.1:8b gemma3:12b; do
    until curl -s "127.0.0.1:${PORT[$m]}/health" | grep -q ok; do sleep 2; done; echo "READY $m"
  done
  printf 'export LLM_BACKEND=llamacpp\nexport LLAMACPP_URLS=%q\n' "$urls" > "$ROOT/env_llamacpp.sh"
  echo "wrote $ROOT/env_llamacpp.sh -- now run:  source $ROOT/env_llamacpp.sh" ;;
stop)
  pkill -u "$USER" -f "llama-server -m" && echo "stopped" || echo "none running" ;;
status)
  for m in qwen3:8b llama3.1:8b gemma3:12b; do
    printf '%-12s port %s: %s\n' "$m" "${PORT[$m]}" "$(curl -s 127.0.0.1:${PORT[$m]}/health || echo down)"
  done ;;
esac
