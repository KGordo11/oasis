#!/bin/bash
# =============================================================================
# The night queue. Runs sweeps back to back, indefinitely, recording machine
# load alongside every one of them.
#
# WHY IT RECORDS LOAD
# -------------------
# B-32: `sweep18_a36` cost 2.16x its reference run while doing the same work --
# 39 posts against 33 at round 1 -- because the laptop was in use. Nothing in the
# run recorded that, so the contamination had to be reconstructed afterwards from
# `ps` output that happened to still be in a terminal, and even then the culprit
# was misidentified once before the timestamps were checked.
#
# That is the fourth time (F-65, F-77, B-28, B-32) an unrecorded setting produced
# an error attributed to something else. The standing rule in the log is: a
# setting the run does not record will eventually be wrong. Machine load is such
# a setting. So this queue samples it every 30 s for the life of each run and
# writes `data/load_<label>.csv`, and a summary line into `data/night_queue.txt`.
#
# It does NOT refuse to run on a busy machine -- `sweep_when_idle.sh` is the
# gate for that. This one is for when the operator says start now. The point is
# that a run made on a busy machine is then MARKED as such rather than silently
# joining the cost curve.
#
# WHAT IT RUNS
# ------------
# Pass A is the sweep: 18/36/54/72/90 agents at seed 42, which is the curve that
# takes our largest verified cost point from 36 agents to 90 and makes the
# extrapolation to 1,100 defensible instead of hopeful.
#
# Every pass after that is the SAME sweep at a new seed -- replicates. That is
# deliberate and it is the only thing that belongs in an unattended queue:
# replicates always add statistical power, and they need no design decision made
# at 22:30 by whoever wrote the script. F-35 is the reason they are worth the
# hours -- the cross-run noise floor is ~28 pp for posting share, so single runs
# cannot resolve much of anything and replicates are the only cure.
#
# Anything requiring a NEW experimental arm -- activation rate, shuffled feed,
# the Q-15 repeat-exposure design -- stays out of here on purpose. Those need
# brainstorming first, and an unattended script is the worst possible place to
# decide one.
#
# RESUMABLE AND SAFE TO RESTART. sweep18.sh skips any run whose manifest exists,
# so re-running the queue costs nothing already done.
#
# USAGE
#   nohup examples/experiment/social_timeline/night_queue.sh > /tmp/night_queue.log 2>&1 &
#   tail -f /tmp/night_queue.log
#   cat data/night_queue.txt            # one line per completed run, with load
#
#   PASSES=2 ...      stop after two passes instead of running forever
#   AGENTS="18 36" ...  a shorter sweep
#
# To stop: pkill -f night_queue.sh   (also kill the sweep: pkill -f sweep18.sh)
# =============================================================================
cd /Users/gordon/research/oasis || exit 1
S=examples/experiment/social_timeline

AGENTS=${AGENTS:-"18 36 54 72 90"}
PASSES=${PASSES:-0}          # 0 = forever
BASE_SEED=${BASE_SEED:-42}
SUMMARY=data/night_queue.txt

log(){ echo "[$(date '+%m-%d %H:%M:%S')] $*"; }
touch $SUMMARY

# Non-simulation CPU: everything that is neither ollama nor our own processes.
# Same definition as sweep_when_idle.sh, and the same anchoring lesson applies --
# match on paths, not bare substrings, or ".ollama/models/blobs/" gets counted.
other_cpu () {
  ps -A -o %cpu,command \
    | grep -vE "ollama|run_simulation\.py|sweep18\.sh|night_queue\.sh|load_sampler|%CPU" \
    | awk '{s+=$1} END {printf "%.0f", s+0}'
}

# Samples until killed. One row per 30 s.
load_sampler () {   # $1 = csv path
  echo "timestamp,other_cpu_pct" > "$1"
  while true; do
    echo "$(date '+%Y-%m-%dT%H:%M:%S'),$(other_cpu)" >> "$1"
    sleep 30
  done
}

pass=0
while true; do
  pass=$((pass+1))
  [ "$PASSES" -gt 0 ] && [ $pass -gt "$PASSES" ] && { log "PASSES=$PASSES reached, stopping"; break; }

  seed=$((BASE_SEED + pass - 1))
  # Pass 1 keeps the historical prefix so the runs already planned keep their
  # names; later passes are replicates and are labelled by their seed.
  if [ $pass -eq 1 ]; then prefix="sweep18"; else prefix="sweep18_s${seed}"; fi

  log "########## PASS $pass -- prefix=$prefix seed=$seed agents=$AGENTS ##########"

  csv="data/load_${prefix}.csv"
  load_sampler "$csv" & sampler=$!
  log "  load sampler started -> $csv"

  PREFIX="$prefix" SEED="$seed" $S/sweep18.sh $AGENTS
  rc=$?

  { kill $sampler && wait $sampler; } 2>/dev/null
  log "  load sampler stopped"

  # Summarise the load this pass ran under, so a suspect run is visible later
  # without anyone having to remember what was on screen at the time.
  if [ -f "$csv" ]; then
    python3 - "$csv" "$prefix" "$SUMMARY" <<'PY'
import csv, sys, statistics as st
path, prefix, out = sys.argv[1], sys.argv[2], sys.argv[3]
vals = []
with open(path) as f:
    for row in csv.DictReader(f):
        try: vals.append(float(row["other_cpu_pct"]))
        except (ValueError, KeyError): pass
if vals:
    med, mx = st.median(vals), max(vals)
    # 40% is sweep_when_idle.sh's threshold for "the machine is free".
    verdict = "CLEAN" if med < 40 else ("BUSY" if med < 100 else "HEAVILY LOADED")
    line = (f"{prefix}  samples={len(vals)}  median_other_cpu={med:.0f}%  "
            f"peak={mx:.0f}%  {verdict}")
    print("  load: " + line)
    open(out, "a").write(line + "\n")
PY
  fi

  log "########## PASS $pass DONE rc=$rc ##########"
  column -t data/sweep18_results.txt 2>/dev/null | tail -12

  if [ $rc -ne 0 ]; then
    log "  sweep exited non-zero -- pausing 5 min before the next pass"
    sleep 300
  fi
done

log "########## QUEUE FINISHED ##########"
cat $SUMMARY
