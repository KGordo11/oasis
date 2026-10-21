#!/bin/bash
# Run ONE V3 test (log 14.43). Gordon's rule: every test = V1 + exactly ONE addition, never stacked; run_v2.py refuses
# more than one. All tests use round 101 = V1's own random seeds, so every answer pairs with the V1 run screen by screen.
#   v1                      the baseline, run once: posting (100 users) + reading (30 users) + noise floor
#   p_think p_menu p_2a p_2b p_2c p_screen   posting turn only, 100 users (a few minutes each)
#   r_think r_refresh r_json r_menu          reading turn only, 30 users, reading V1's own round-101 posts
# Results: data/llm_bias/v3_tests/<test>/r101/ ; compare with V1: python3 examples/experiment/llm_bias/v3_summary.py <test>
# (The first V3 tests -- check, 0, 1, 2a-c, 3, 4 -- stacked several additions; their script is in git at 092b6c0.)
set -eu
T=${1:?usage: v3_test.sh v1|p_think|p_menu|p_2a|p_2b|p_2c|p_screen|r_think|r_refresh|r_json|r_menu}
cd "$(dirname "$0")/../../.."
case $T in
  v1) X="" ;;
  p_think|r_think) X="--think" ;;
  p_menu) X="--post-menu post_only" ;;
  p_2a|p_2b|p_2c) X="--post-line ${T#p_2}" ;;
  p_screen) X="--post-screen v3" ;;
  r_refresh) X="--refresh-loop" ;;
  r_json) X="--free-text" ;;
  r_menu) X="--menu-order flipped" ;;
  *) echo "unknown test $T"; exit 1 ;;
esac
V1_SRC=${V1_SRC:-$PWD/data/llm_bias/v2/r101}  # V1's own round-101 files (the Spark's copy)
export DATA_DIR=${V3_ROOT:-$PWD/data/llm_bias/v3_tests}/$T EXTRA="$X" ROUNDS=101 SLICES=0 MANAGE_SERVERS=${MANAGE_SERVERS:-1} \
       CHECKPOINT=0 PUSH=0 STOP_OLLAMA=${STOP_OLLAMA:-1} PARALLEL=8 PY=${PY:-python3} \
       STOP="$(python3 -c "import datetime as d; print((d.datetime.now() + d.timedelta(days=10)).strftime('%Y-%m-%d %H:%M'))")"
mkdir -p "$DATA_DIR/r101"
exec 9>"$DATA_DIR/.lock"; flock -n 9 || { echo "test $T is already running -- not starting a second copy"; exit 1; }
echo "V3 test $T: V1 + [${X:-nothing}]  -> $DATA_DIR" | tee -a "$DATA_DIR/night.log"
if [ "$T" = v1 ] || [ "${T:0:2}" = p_ ]; then  # posting turn, 100 users
  TURNS=post AGENTS=100 NOISE=0 $PY examples/experiment/llm_bias/v2_night.py
fi
if [ "$T" = v1 ] || [ "${T:0:2}" = r_ ]; then  # reading turn, 30 users, on V1's own posts by users 0-29
  for m in gemma3-12b llama3.1-8b qwen3-8b; do
    [ -e "$DATA_DIR/r101/posting_${m}_a30.jsonl" ] && continue
    head -30 "$V1_SRC/posting_$m.jsonl" > "$DATA_DIR/r101/posting_${m}_a30.jsonl"
    cp "$V1_SRC/posting_$m.manifest.json" "$DATA_DIR/r101/posting_${m}_a30.manifest.json"
  done
  NOISE=$([ "$T" = v1 ] && echo 4 || echo 0) AGENTS=30 $PY examples/experiment/llm_bias/v2_night.py
fi
echo "V3 TEST $T DONE" | tee -a "$DATA_DIR/night.log"
