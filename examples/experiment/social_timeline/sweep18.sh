#!/bin/bash
# =============================================================================
# The agent sweep, in increments of 18.  18 / 36 / 54 / 72 / 90, 7 rounds each.
#
# WHAT IT IS FOR
# --------------
# F-96 settled that cost is linear in agent count -- exponent 0.991, R^2 0.9988,
# 22.7 s per agent-turn -- but it settled that on THREE points: 12, 24 and 36.
# Every claim about what a 1,100-agent run would cost extrapolates that fit ~30x
# beyond its largest measurement. This sweep takes the largest verified point
# from 36 to 90, which is what makes the extrapolation defensible rather than
# hopeful. It is also the data the cost charts have been asking for.
#
# WHY EVERY FLAG BELOW IS PINNED, AND WHY THAT MATTERS MORE THAN IT SOUNDS
# -----------------------------------------------------------------------
# This sweep is only worth running if it is comparable to ctx8192_a12/a24/a36.
# A cost curve assembled from runs at different configurations is not a cost
# curve. So the configuration is not left to defaults -- it is stated, and then
# CHECKED against a reference run before the night is spent.
#
#   --temperature 0.7   THE ONE THAT NEARLY GOT US. Every shell script in this
#                       directory passes 0.7 and 28 of our runs carry it, but
#                       the bare CLI default is 0.9 (changed in 30e6144 on
#                       2026-08-30 and never reconciled). The command originally
#                       drafted for tonight omitted the flag. The whole sweep
#                       would have run at 0.9 and matched nothing.
#   groups ON           ctx8192_* ran with the full 27-action set. Do NOT add
#                       --no-groups here: campaign.sh and overnight.sh use it,
#                       but they are a different run family.
#   --semaphore 4       F-77. Adopted for variance (CV 3.1% vs 15.3%) and 6 GB
#                       of RAM, not for speed; NP=4..8 is a plateau.
#   --recsys twhin-bert, --seed 42, business personas -- as the reference runs.
#
# THE SERVER MUST ALREADY BE RIGHT (B-28)
#   OLLAMA_NUM_PARALLEL=4 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=24h ollama serve
# run_simulation.py refuses to start otherwise. This script does not restart the
# server: R6 records that starting one behind a `pgrep` guard silently reused a
# server at the wrong settings for an entire session, and the fix adopted then
# was to make the operator start it deliberately, not to add another wrapper.
#
# PERSONA SUPPLY (B-26)
# The business file has 99 usable bios. 90 fits; 108 -- the next increment of 18
# -- does not, and as of 2026-09-13 asking for it is a refusal rather than a
# silent 99-agent run. That is why this sweep stops at 90.
#
# ESTIMATE
# Rounds 1-3 cost 0.13 / 0.44 / 0.64 of the plateau round (measured across
# ctx8192_a12/a24/a36), so a 7-round run is plateau x 5.2, not x 7:
#     18 -> ~34 min   36 -> ~68 min   54 -> ~102 min   72 -> ~135 min   90 -> ~169 min
# ~8.5 h total, ASSUMING the linearity this sweep exists to test. If cost turns
# superlinear above 36, the last two runs take longer than that says.
#
# RESUMABLE. Any run whose manifest exists is skipped, so an interrupt costs one
# run, not the night. Safe to re-run.
#
# USAGE
#   examples/experiment/social_timeline/sweep18.sh            # 18 36 54 72 90
#   examples/experiment/social_timeline/sweep18.sh 18 36      # just those
#   ROUNDS=5 examples/experiment/social_timeline/sweep18.sh   # shorter night
# =============================================================================
cd /Users/gordon/research/oasis || exit 1
P=./oasis-env/bin/python
S=examples/experiment/social_timeline

ROUNDS=${ROUNDS:-7}
SEED=${SEED:-42}
REFERENCE=${REFERENCE:-ctx8192_a36}
PERSONAS=data/twitter_dataset/anonymous_topic_200_1h/False_Business_0.csv
PREFIX=${PREFIX:-sweep18}
AGENTS=${@:-18 36 54 72 90}

R=data/sweep18_results.txt
touch $R
log(){ echo "[$(date '+%m-%d %H:%M:%S')] $*"; }

# Engagement, read from the run's own analysis file. Not a /tmp scrape: B-27 was
# one run's timings published under another run's name because of exactly that.
cat > /tmp/s18_engage.py <<'PY'
import json, sys
try:
    a = json.load(open(f"data/social_timeline_{sys.argv[1]}_analysis.json")).get("agents") or {}
    h = sum(len(x.get("seen_and_acted") or []) for x in a.values())
    s = h + sum(len(x.get("seen_and_ignored") or []) for x in a.values())
    print(f"{100*h/s:.2f}" if s else "0.00")
except Exception:
    print("0.00")
PY

run_one () {   # $1 = agent count
  local n=$1 lbl=${PREFIX}_a$1
  if [ -f data/social_timeline_$lbl.json ]; then
    log "  $lbl already done, skipping"; return 0
  fi
  rm -f data/social_timeline_$lbl.db
  local t0=$(date +%s)
  $P $S/run_simulation.py \
     --agents $n --rounds $ROUNDS --label $lbl --seed $SEED \
     --temperature 0.7 --semaphore 4 --recsys twhin-bert \
     --request-timeout 300 --personas $PERSONAS \
     > /tmp/s18_$lbl.log 2>&1 &
  local pid=$!
  watchdog $lbl $pid & local wd=$!
  wait $pid 2>/dev/null; local rc=$?
  { kill $wd && wait $wd; } 2>/dev/null   # silence bash's "Terminated" job notice
  local t=$(( $(date +%s) - t0 ))

  if [ ! -f data/social_timeline_$lbl.json ]; then
    log "  $lbl INCOMPLETE after ${t}s (rc=$rc) -- see /tmp/s18_$lbl.log"
    echo "$lbl $n $ROUNDS NA NA" >> $R
    return 1
  fi
  $P $S/analyze.py --db data/social_timeline_$lbl.db > /dev/null 2>&1
  local e=$($P /tmp/s18_engage.py "$lbl")
  local flag=""
  # B-23: under 1% is the F-63 collapse, not a quiet run. But the gate is only
  # meaningful once agents have been SHOWN something: round 1 has an empty feed
  # by construction, so a 1-round run reports 0.00% and is not a collapse.
  if [ "$ROUNDS" -ge 2 ]; then
    [ "${e%%.*}" -lt 1 ] 2>/dev/null && flag="   <<< ENGAGEMENT COLLAPSE"
  else
    flag="   (engagement not assessable at $ROUNDS round)"
  fi
  log "  $lbl  ${n} agents  ${t}s  $(echo "scale=1; $t/$ROUNDS" | bc)s/round  engagement ${e}%$flag"
  echo "$lbl $n $ROUNDS $t $e" >> $R
}

watchdog () {   # B-22: a stalled run once cost a whole day
  local db=data/social_timeline_$1.db last=0 same=0
  while kill -0 $2 2>/dev/null; do
    sleep 120
    local now=$( [ -f $db ] && stat -f %m $db || echo 0 )
    if [ "$now" = "$last" ]; then
      same=$((same+1))
      [ $same -ge 10 ] && { log "    WATCHDOG killed $1 (20 min static)"; kill -9 $2 2>/dev/null; return; }
    else same=0; last=$now; fi
  done
}

# ------------------------------------------------------------------ preflight
log "########## SWEEP18 -- agents: $AGENTS, $ROUNDS rounds, seed $SEED ##########"

log "preflight 1/3: dependency gate"
$P $S/check_deps.py > /tmp/s18_deps.log 2>&1 || {
  log "  check_deps FAILED -- see /tmp/s18_deps.log"; exit 1; }
log "  8 checks pass"

log "preflight 2/3: 4-agent smoke with tonight's exact flags"
rm -f data/social_timeline_${PREFIX}_smoke.db data/social_timeline_${PREFIX}_smoke.json
$P $S/run_simulation.py --agents 4 --rounds 1 --label ${PREFIX}_smoke \
   --seed $SEED --temperature 0.7 --semaphore 4 --recsys twhin-bert \
   --personas $PERSONAS > /tmp/s18_smoke.log 2>&1 || {
  log "  smoke run FAILED -- see /tmp/s18_smoke.log"; exit 1; }
log "  smoke completed"

log "preflight 3/3: is that configuration comparable to $REFERENCE?"
$P $S/assert_comparable.py \
   --candidate data/social_timeline_${PREFIX}_smoke.json \
   --reference $REFERENCE || {
  log "  CONFIG DRIFT -- refusing to spend the night on runs that match nothing."
  log "  Fix the flags above, or pass REFERENCE= to compare against a different run."
  exit 2; }

# ---------------------------------------------------------------------- sweep
for n in $AGENTS; do
  log "--- $n agents ---"
  run_one $n
done

log "########## DONE ##########"
column -t $R 2>/dev/null || cat $R
log "results: $R"
log "next: $P $S/make_timing_charts.py   then republish the explorer artifact"
