#!/bin/bash
# Reproduce Test 6 (LD-18): two AIs (gemma4:e2b, gemma3:1b), 100 users, 5 subreddits, 15 rounds of new posts.
# Run from the oasis folder, with Ollama already running (see the guide). Three modes:
#
#   examples/experiment/llm_bias/reproduce_test6.sh analyze   # ~10 min: recompute every result from the saved votes
#   examples/experiment/llm_bias/reproduce_test6.sh check     # ~5 min: test your setup with a 5-person mini-round
#   examples/experiment/llm_bias/reproduce_test6.sh run       # ~17 h: redo the whole experiment from scratch
#
# "run" first moves the saved Test 6 data into data/llm_bias/_original_test6/ (it is also in git), then writes
# new posts and votes in the same places, then runs the analysis. If it stops, run it again: finished runs are
# skipped and a half-finished run continues where it stopped. Nothing is pushed anywhere.
set -eu
cd "$(dirname "$0")/../../.."
P=./oasis-env/bin/python; S=examples/experiment/llm_bias; D=data/llm_bias
MODE=${1:-}
[ -x "$P" ] || { echo "Python environment missing: python3.11 -m venv oasis-env && ./oasis-env/bin/pip install -e . pandas statsmodels"; exit 2; }

analyze() {
  echo "== analysis (2,000 resamples; about 10 minutes)"
  $P $S/analyze_two_ai.py 2000 > $D/two_ai/summary.txt
  cat $D/two_ai/summary.txt
  $P $S/analyze_deep.py > /dev/null
  echo "== independent check of the numbers"
  $P $S/verify_numbers.py | tail -1
  echo "== health checks"
  $P $S/check_world.py --prefix two_r | grep -c "^PASS" | sed 's/$/ runs PASS/'
}

setup() {
  curl -s localhost:11434/api/tags >/dev/null || { echo "Ollama isn't running. Start it (see the guide), then try again."; exit 2; }
  for m in gemma4:e2b gemma3:1b; do ollama list | grep -q "^$m " || ollama pull "$m"; done
  echo "== model fingerprints (the originals were gemma4:e2b 7fbdbf8f5e45, gemma3:1b 8648f39daa8f)"
  ollama list | grep -E "^(gemma4:e2b|gemma3:1b) "
  $P -c "import sys; sys.path.insert(0, '$S'); import personas; u = personas.core100(); print('== the 100 users: fingerprint OK,', len(u), 'users')"
}

one_world() {  # $1 label  $2 seed  $3 AI playing the users  $4 number of users
  local M="$D/worlds/$1/manifest.json" RES=""
  if grep -qs finished_at "$M"; then echo "skip $1 (already finished)"; return; fi
  [ -d "$D/worlds/$1" ] && RES="--resume"
  echo "$(date '+%H:%M') $1 $RES"
  $P $S/run_world.py --label "$1" --seed "$2" --judges "$3" --authors gemma4:e2b,gemma3:1b --agents "$4" \
     --natural-posts --complete-slots --post-retries 4 $RES > "$D/worlds_$1.log" 2>&1
  grep -E "done [0-9]+ in|WARNING" "$D/worlds_$1.log" | tail -3
}

case "$MODE" in
  analyze)
    analyze ;;
  check)
    setup
    echo "== mini-round: round 1's posts, 5 users, both AIs"
    for J in gemma4:e2b gemma3:1b; do one_world "check_two_r01_${J%%:*}" 201 "$J" 5; done
    $P - <<'PY'
import json, collections
for w in ("check_two_r01_gemma4", "check_two_r01_gemma3"):
    d = [json.loads(l) for l in open(f"data/llm_bias/worlds/{w}/decisions.jsonl")]
    print(w, len(d), "votes,", dict(collections.Counter(x["action"] for x in d)), "| broken:", sum(x["outcome"] != "chose" for x in d))
PY
    rm -rf $D/worlds/check_two_r01_* $D/worlds_check_two_r01_*.log
    echo "Setup works. Next: reproduce_test6.sh run" ;;
  run)
    setup
    if [ -d "$D/worlds/two_r01_gemma4" ] && [ ! -f "$D/.reproduction_started" ]; then
      B=$D/_original_test6; mkdir -p $B/worlds
      echo "== moving the saved Test 6 data to $B (it is also in git)"
      mv $D/worlds/two_r* $B/worlds/; mv $D/postbank_s2[01][0-9].jsonl $B/ 2>/dev/null || true; mv $D/two_ai $B/ 2>/dev/null || true
    fi
    mkdir -p $D/two_ai; touch $D/.reproduction_started
    for R in $(seq 1 15); do
      for J in gemma4:e2b gemma3:1b; do one_world "two_r$(printf %02d $R)_${J%%:*}" $((200 + R)) "$J" 100; done
    done
    analyze
    rm -f $D/.reproduction_started
    echo "Done. Compare data/llm_bias/two_ai/summary.txt with data/llm_bias/_original_test6/two_ai/summary.txt" ;;
  *)
    sed -n 2,11p "$0"; exit 1 ;;
esac
