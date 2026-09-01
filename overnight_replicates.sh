#!/bin/bash
# Overnight replicate runs -- scheduled for 2026-09-01 23:59 by launchd.
#
# WHY THIS CONFIG. It reproduces v10_register / v10_replicate exactly: prompt
# version 10, temperature 0.9, seed 0, 36 agents, 15 rounds, twhin-bert,
# --no-groups. Every other setting is an argparse default and was verified
# against both manifests before scheduling. Adding four gives SIX runs at one
# identical configuration -- the first homogeneous set in this project. The
# existing five "three-tier" runs span prompt versions 6/8/9/10 and two
# temperatures, so every pooled estimate so far averages over settings that
# were not identical.
#
# WHAT IT BUYS
#   1. F-43 currently reproduces in 4 of 5 runs; v9_feedback is null at 0.89.
#      But v9_feedback is the ONLY prompt-v9 run, so "fails in that run" is
#      confounded with "fails at that prompt version". Six runs at a fixed
#      config separate run-to-run noise from configuration.
#   2. A real noise floor. F-35 rests on ONE replicate pair (Q-14). Six
#      identical runs give a proper variance estimate.
#
# Each run is analysed the moment it finishes, so an interrupted night still
# leaves every completed run fully usable.

set -uo pipefail

REPO="/Users/gordon/research/oasis"
PY="$REPO/oasis-env/bin/python"
SIM="$REPO/examples/experiment/social_timeline/run_simulation.py"
ANALYZE="$REPO/examples/experiment/social_timeline/analyze.py"
LOG_DIR="$REPO/data/overnight_logs"
MAIN_LOG="$LOG_DIR/overnight.log"

mkdir -p "$LOG_DIR"
cd "$REPO" || exit 1

# D-5: the model must stay resident or every round pays a reload.
export OLLAMA_KEEP_ALIVE=60m

say() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$MAIN_LOG"; }

say "================================================================"
say "overnight replicates starting"
say "config: 36 agents, 15 rounds, prompt v10, temp 0.9 (default), --no-groups"

# Keep the machine awake for the whole batch, but only from here -- no point
# holding it up during the hours before the scheduled start.
caffeinate -dimsu -w $$ &
CAFF=$!
say "caffeinate holding the machine awake (pid $CAFF)"

if ! curl -s -m 10 http://localhost:11434/api/tags > /dev/null 2>&1; then
    say "FATAL: Ollama is not responding on :11434. Nothing was run."
    exit 1
fi
say "ollama responding"

# Confirmed practice: never launch full runs without a smoke test first.
# Two minutes here has caught real breakage before.
say "smoke test (4 agents, 2 rounds)..."
if "$PY" "$SIM" --agents 4 --rounds 2 --label overnight_smoke --no-groups \
        >> "$LOG_DIR/smoke.log" 2>&1; then
    say "smoke test PASSED"
else
    say "FATAL: smoke test failed -- see $LOG_DIR/smoke.log. No full runs started."
    exit 1
fi

COMPLETED=0
for i in 3 4 5 6; do
    LABEL="v10_rep$i"
    say "---- starting $LABEL (run $((i-2)) of 4, expect ~2h) ----"
    START=$(date +%s)

    if "$PY" "$SIM" --agents 36 --rounds 15 --label "$LABEL" --no-groups \
            >> "$LOG_DIR/$LABEL.log" 2>&1; then
        MINS=$(( ($(date +%s) - START) / 60 ))
        say "$LABEL finished in ${MINS}m"

        # Analyse immediately, so an interrupted night still leaves usable runs.
        if "$PY" "$ANALYZE" "data/social_timeline_$LABEL.db" \
                >> "$LOG_DIR/$LABEL.analyze.log" 2>&1; then
            say "$LABEL analysed"
            COMPLETED=$((COMPLETED + 1))
        else
            say "$LABEL ran but analysis FAILED -- see $LOG_DIR/$LABEL.analyze.log"
        fi
    else
        # Keep going: three good runs beat stopping at the first failure.
        say "$LABEL FAILED -- see $LOG_DIR/$LABEL.log. Continuing to next run."
    fi
done

say "================================================================"
say "batch done: $COMPLETED of 4 runs completed and analysed"
say "next: re-run recency_check.py and exposure_model.py over all runs, e.g."
say "  oasis-env/bin/python examples/experiment/social_timeline/recency_check.py \\"
say "      --runs baseline v10_register v10_replicate v8_full v9_feedback \\"
say "             v10_rep3 v10_rep4 v10_rep5 v10_rep6 --data-dir data"
kill "$CAFF" 2>/dev/null
