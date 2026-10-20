#!/bin/bash
# Run ONE V3 test (log 14.43): every test = the V3 baseline (V1 prompts, qwen thinking on, working refresh in the
# reading turn) + exactly one change. Same round number (200) in every test, so every test gets the same random seeds.
#   bash examples/experiment/llm_bias/v3_test.sh check   10-user mini-round of test 0 (code + thinking check, ~20 min)
#   bash examples/experiment/llm_bias/v3_test.sh 0       baseline, full round
#   bash examples/experiment/llm_bias/v3_test.sh 1       posting turn: create_post is the only action   (posting only)
#   bash examples/experiment/llm_bias/v3_test.sh 2a|2b|2c  posting screen: one extra line                (posting only)
#   bash examples/experiment/llm_bias/v3_test.sh 3       JSON-only mode off, full round
#   bash examples/experiment/llm_bias/v3_test.sh 4       menu order flipped, full round
# Results: data/llm_bias/v3_tests/t<test>/r200/ ; summary: python3 examples/experiment/llm_bias/v3_summary.py <test>
set -eu
T=${1:?usage: v3_test.sh check|0|1|2a|2b|2c|3|4}
cd "$(dirname "$0")/../../.."
case $T in
  check|0) X="" ;;
  1) X="--post-menu post_only" ;;
  2a|2b|2c) X="--post-line ${T#2}" ;;
  3) X="--free-text" ;;
  4) X="--menu-order flipped" ;;
  *) echo "unknown test $T"; exit 1 ;;
esac
export DATA_DIR=$PWD/data/llm_bias/v3_tests/t$T EXTRA="--v1 --think --refresh-loop $X" ROUNDS=200 SLICES=0 \
       MANAGE_SERVERS=1 CHECKPOINT=0 PUSH=0 STOP_OLLAMA=1 PARALLEL=8 PY=python3 STOP="$(date -d '+10 days' '+%Y-%m-%d %H:%M')"
case $T in 1|2a|2b|2c) export TURNS=post NOISE=0 ;; check) export AGENTS=10 NOISE=4 ;; esac
mkdir -p "$DATA_DIR"
exec 9>"$DATA_DIR/.lock"; flock -n 9 || { echo "test $T is already running -- not starting a second copy"; exit 1; }
echo "V3 test $T: run_v2.py options: $EXTRA  -> $DATA_DIR" | tee -a "$DATA_DIR/night.log"
python3 examples/experiment/llm_bias/v2_night.py
echo "V3 TEST $T DONE" | tee -a "$DATA_DIR/night.log"
