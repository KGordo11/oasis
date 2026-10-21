#!/bin/bash
# All single-addition V3 tests in order (log 14.43). Resumable: a rerun skips every step already done.
# Self-healing: after each test its CHECKS must pass (every post read once, right change, ...); if not, the test is
# resumed, up to 3 tries; a test that still fails is listed and the chain moves on, so one bad test can't stall the
# rest. Last line: "CHAIN DONE: all 11 passed" or "CHAIN DONE -- FAILED: <tests>".
cd "$(dirname "$0")/../../.."
TESTS=${TESTS:-"v1 p_think p_menu p_2a p_2b p_2c p_screen r_think r_refresh r_json r_menu"} failed=""
for t in $TESTS; do
  for try in 1 2 3; do
    bash examples/experiment/llm_bias/v3_test.sh "$t"
    if python3 examples/experiment/llm_bias/v3_summary.py "$t" | grep -q "ALL CHECKS PASS"; then
      echo "$(date '+%F %T') TEST $t OK"; continue 2
    fi
    echo "$(date '+%F %T') TEST $t not complete (try $try of 3)"; sleep 60
  done
  failed="$failed $t"
done
[ -z "$failed" ] && echo "CHAIN DONE: all $(echo $TESTS | wc -w | tr -d " ") passed" || echo "CHAIN DONE -- FAILED:$failed"
