#!/bin/bash
# =============================================================================
# Hand the night queue over to a differently-shaped campaign, WITHOUT losing the
# run in flight.
#
# WHY THIS EXISTS
# ---------------
# night_queue.sh reads AGENTS, ROUNDS and PREFIX once at startup, so changing
# the campaign means restarting it. Restarting it naively is destructive in a
# way that is easy to miss: sweep18.sh does the fold-in -- export_parquet ->
# build_package -> make_timing_charts -> make_engagement_charts -- AFTER the
# simulation finishes. Killing the queue mid-run therefore throws away the
# analysis for a run that may already have cost seven hours, and the run's
# database is left un-exported and out of the package.
#
# So: wait for the current sweep to exit on its own, then switch. It holds a
# caffeinate assertion the whole time, so the laptop will not sleep during the
# wait or the handover.
#
# USAGE
#   ROUNDS=15 AGENTS="18 36 54 72 90" PREFIX=r15 \
#     nohup caffeinate -i examples/experiment/social_timeline/switch_campaign.sh \
#     > /tmp/switch_campaign.log 2>&1 &
#
#   tail -f /tmp/switch_campaign.log
#
# Safe to start at any time, including while a run is mid-round. It never
# signals run_simulation.py; it waits for sweep18.sh, which owns it.
# To cancel before the handover happens: pkill -f switch_campaign.sh
# =============================================================================
cd /Users/gordon/research/oasis || exit 1
S=examples/experiment/social_timeline

ROUNDS=${ROUNDS:-15}
AGENTS=${AGENTS:-"18 36 54 72 90"}
PREFIX=${PREFIX:-r15}

log(){ echo "[$(date '+%m-%d %H:%M:%S')] $*"; }

log "will switch to: ROUNDS=$ROUNDS AGENTS='$AGENTS' PREFIX=$PREFIX"

# --- 1. wait for the in-flight sweep, if any -------------------------------
# Wait for EVERY sweep18 process. There are always two -- the pass, and a
# per-run subshell -- and `pgrep | head -1` returns them in no defined order.
# This script originally took head -1 and happened to get the parent; the same
# line in after_pass1.sh later got the child, which exits when the RUN ends
# rather than when the pass does, i.e. before the fold-in. Waiting for all of
# them is the only condition that means "the pass has finished".
if pgrep -f "sweep18\.sh" >/dev/null; then
  cur=$(ps -o command= -p "$(pgrep -f 'run_simulation\.py' | head -1)" 2>/dev/null \
        | grep -oE '\-\-label [^ ]+' | awk '{print $2}')
  log "sweep18.sh running as pids: $(pgrep -f "sweep18\.sh" | tr '\n' ' ')(current run: ${cur:-unknown})"
  log "waiting for ALL of them -- the last to exit is the fold-in"
  while pgrep -f "sweep18\.sh" >/dev/null; do sleep 60; done
  log "every sweep18 exited; the pass is folded in"
  # night_queue starts its next pass within seconds of sweep18 exiting, so give
  # it no chance to launch a simulation we are about to orphan.
  sleep 2
else
  log "no sweep in flight"
fi

# --- 2. stop the old queue -------------------------------------------------
# Kill the queue first, then any sweep it managed to start in the gap. Do NOT
# kill run_simulation directly -- if one just started, killing its sweep parent
# is enough and leaves no half-written database being appended to.
pkill -f "night_queue\.sh" 2>/dev/null && log "stopped night_queue.sh"
sleep 1
pkill -f "sweep18\.sh"    2>/dev/null && log "stopped sweep18.sh"
sleep 2
if pgrep -f "run_simulation\.py" >/dev/null; then
  log "WARNING: a run_simulation.py is still alive -- a new pass started during"
  log "         the handover. Not killing it. Check before relaunching:"
  log "         ps -eo pid,command | grep run_simulation"
  exit 1
fi

# --- 3. start the new campaign ---------------------------------------------
log "starting new queue"
ROUNDS="$ROUNDS" AGENTS="$AGENTS" PREFIX="$PREFIX" \
  nohup caffeinate -i $S/night_queue.sh > /tmp/night_queue.log 2>&1 &
log "launched (pid $!). sweep18.sh skips any run whose manifest exists, so"
log "finished runs are not repeated. Watch: tail -f /tmp/night_queue.log"
