#!/bin/bash
# =============================================================================
# Wait for the machine to be idle, then run the agent sweep.
#
# WHY THIS EXISTS
# ---------------
# On 2026-09-13 the sweep was launched at 17:10 on a laptop that was in active
# use. Nothing failed. `sweep18_a36` did the SAME WORK as its reference run --
# 39 posts against 33, 3 comments against 4, 1 like against 2 at round 1 -- and
# took 2.16x as long, 802.5 s against 371.6. Configuration was verified identical
# on 19 keys, Ollama was verified at 8,192 context with the model resident, and
# no server reload had occurred. The difference was RobloxPlayer at 85 % of a
# core, WindowServer at 41 % and Chrome at 27 %.
#
# That is B-32, and it is the same shape as B-26, B-28 and B-31: the run does not
# fail, it does not warn, it just quietly stops measuring what it was asked to
# measure. A cost-versus-agents curve taken while desktop load varies is not a
# cost curve -- it is the `scale99_full` failure the log already records, where
# per-agent cost climbed monotonically because something was degrading rather
# than because the world was getting bigger.
#
# The behavioural results are NOT affected by this and never were. Tier, repeat
# exposure and slot position are odds ratios computed within a run; a slower
# machine produces identical behaviour more slowly. Only wall clock is at risk.
#
# WHAT IT DOES
# ------------
# Polls once a minute. When the machine has looked idle for IDLE_MINUTES
# consecutive checks it starts `sweep18.sh`, which runs its own three preflights
# (dependency gate, smoke run, config-drift check against the reference) before
# spending the night. Until then it does nothing but watch, so it is safe to
# leave running while you use the laptop.
#
# IDLE MEANS, concretely:
#   - no foreground hog: nothing in HOGS is running (Roblox is the one that
#     started this), and
#   - total CPU across all processes, EXCLUDING ollama and our own simulation,
#     is under BUSY_PCT.
# The exclusion matters: once the sweep starts, ollama is deliberately busy, and
# a naive check would call the machine "in use" and never settle.
#
# `caffeinate -i` wraps the sweep so an idle laptop does not sleep mid-run. It
# does NOT override the lid: closing the lid still suspends, and the sweep's own
# 20-minute stall watchdog (B-22) would then kill the current run. Leave the lid
# open.
#
# USAGE
#   nohup examples/experiment/social_timeline/sweep_when_idle.sh > /tmp/idle_sweep.log 2>&1 &
#   tail -f /tmp/idle_sweep.log
#
#   IDLE_MINUTES=5 ...   settle faster (default 10)
#   BUSY_PCT=60 ...      tolerate more background load (default 40)
#   AGENTS="18 36" ...   run a subset
#
# To cancel: pkill -f sweep_when_idle.sh
# Runs already finished are never repeated -- sweep18.sh skips any run whose
# manifest exists -- so cancelling costs at most the run in flight.
# =============================================================================
cd /Users/gordon/research/oasis || exit 1
S=examples/experiment/social_timeline

IDLE_MINUTES=${IDLE_MINUTES:-10}
BUSY_PCT=${BUSY_PCT:-40}
AGENTS=${AGENTS:-"18 36 54 72 90"}
HOGS=${HOGS:-"RobloxPlayer|RobloxStudio|Minecraft|Steam|obs|Final Cut|Premiere|Blender"}

log(){ echo "[$(date '+%m-%d %H:%M:%S')] $*"; }

# Total CPU of everything that is neither ollama nor our own simulation. Uses
# ps rather than top: top's first sample reports cumulative averages and would
# read high for long-lived processes regardless of what they are doing now.
other_cpu () {
  ps -A -o %cpu,command \
    | grep -vE "ollama|run_simulation\.py|sweep18\.sh|sweep_when_idle\.sh|%CPU" \
    | awk '{s+=$1} END {printf "%.0f", s+0}'
}

hog_running () {
  pgrep -f "$HOGS" >/dev/null 2>&1
}

log "########## WAITING FOR AN IDLE MACHINE ##########"
log "  will start when: no {$HOGS}"
log "                   and other-process CPU < ${BUSY_PCT}%"
log "                   sustained for ${IDLE_MINUTES} consecutive minutes"
log "  then runs: agents $AGENTS"
log "  cancel with: pkill -f sweep_when_idle.sh"

streak=0
while true; do
  cpu=$(other_cpu)
  if hog_running; then
    [ $streak -gt 0 ] && log "  reset: a foreground app is running (was ${streak}/${IDLE_MINUTES})"
    streak=0
  elif [ "$cpu" -ge "$BUSY_PCT" ]; then
    [ $streak -gt 0 ] && log "  reset: other-process CPU ${cpu}% >= ${BUSY_PCT}% (was ${streak}/${IDLE_MINUTES})"
    streak=0
  else
    streak=$((streak+1))
    log "  idle ${streak}/${IDLE_MINUTES}  (other CPU ${cpu}%)"
  fi

  if [ $streak -ge $IDLE_MINUTES ]; then
    log "########## MACHINE IDLE -- STARTING SWEEP ##########"
    log "  sweep18.sh runs its own preflights: deps gate, smoke run, drift check"
    caffeinate -i $S/sweep18.sh $AGENTS
    rc=$?
    log "########## SWEEP EXITED rc=$rc ##########"
    exit $rc
  fi
  sleep 60
done
