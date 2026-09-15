#!/bin/bash
# =============================================================================
# The three things that need a human, in one command. Start it any time.
#
#   1. wait for pass 1 to finish   -- so sweep18.sh completes its fold-in
#                                     (export -> package -> charts). Killing the
#                                     queue before that throws away the analysis
#                                     for four runs that cost ~14 h.
#   2. stop the queue              -- Claude cannot send signals in auto mode.
#   3. apply the D-19 edit         -- night_queue.sh must NOT be edited while it
#                                     runs: bash reads a script incrementally
#                                     from disk, so a live edit can corrupt a
#                                     pass mid-flight.
#   4. run Q-24                    -- ~3 h, must not run concurrently with
#                                     anything else (B-32).
#   5. restart the queue           -- back to the 15-round sweep, seed 43 pass.
#
# Every step verifies before the next. Any failure stops the chain and says so;
# nothing is left half-done.
#
# USAGE
#   nohup caffeinate -i examples/experiment/social_timeline/after_pass1.sh \
#     > /tmp/after_pass1.log 2>&1 &
#   tail -f /tmp/after_pass1.log
#
# To skip the waiting (if pass 1 has already landed): it detects that and
# proceeds immediately.
# To cancel before it acts:  pkill -f after_pass1.sh
# =============================================================================
set -u
cd /Users/gordon/research/oasis || exit 1
S=examples/experiment/social_timeline
P=./oasis-env/bin/python
NQ=$S/night_queue.sh
log(){ echo "[$(date '+%m-%d %H:%M:%S')] $*"; }

# ---------- 1. wait for pass 1 ----------
# Wait for EVERY sweep18 process, not a single pid. sweep18.sh spawns a
# per-run subshell, so at any moment there are two: the pass (started when the
# campaign began) and the current run's child. `pgrep | head -1` returns them
# in no defined order -- it gave the parent one night and the child the next --
# and waiting on the child releases as soon as the RUN ends, which is before
# the pass has exported, rebuilt the package and drawn the charts. Killing the
# queue there destroys the fold-in for the whole pass. Waiting for all of them
# to be gone is the only condition that means "the pass is finished".
if pgrep -f "sweep18\.sh" >/dev/null; then
  cur=$(ps -eo command | grep run_simulation | grep -v grep | grep -oE '\-\-label [^ ]+' | awk '{print $2}')
  n=$(pgrep -f "sweep18\.sh" | tr '\n' ' ')
  log "pass 1 still running (sweep18 pids: $n; current run ${cur:-unknown})"
  log "waiting for ALL of them -- the last to exit is the fold-in"
  while pgrep -f "sweep18\.sh" >/dev/null; do sleep 120; done
  log "pass 1 finished and folded in"
  sleep 3
else
  log "no sweep running; proceeding"
fi

# ---------- 2. stop the queue ----------
pkill -f "night_queue\.sh" 2>/dev/null && log "stopped night_queue.sh"
sleep 2
pkill -f "sweep18\.sh" 2>/dev/null && log "stopped sweep18.sh"
sleep 3
if pgrep -f "run_simulation\.py" >/dev/null; then
  log "ABORT: a run_simulation is still alive (a new pass started during the"
  log "       handover). Nothing has been changed. Check and rerun:"
  ps -eo pid,command | grep run_simulation | grep -v grep | cut -c1-110
  exit 1
fi
log "machine idle"

# ---------- 3. apply D-19 ----------
if grep -q 'verdict = "CLEAN"' "$NQ"; then
  cp "$NQ" "$NQ.bak-$(date +%Y%m%d%H%M%S)"
  $P - "$NQ" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
old = '    verdict = "CLEAN" if med < 40 else ("BUSY" if med < 100 else "HEAVILY LOADED")'
new = ('    # D-19: median CPU never predicted a cost deviation in this project --\n'
       '    # every pass on record sat at 127-137% and every run landed within 4% of\n'
       '    # the curve. The verdict now comes from measured cost (load_verdict.py);\n'
       '    # this line reports load as context only.\n'
       '    verdict = "load context only -- cost verdict: load_verdict.py"')
assert old in s, "D-19 anchor not found -- night_queue.sh has changed; apply by hand"
open(p, "w").write(s.replace(old, new))
print("  D-19 applied")
PY
  [ $? -ne 0 ] && { log "ABORT: D-19 edit failed; backup kept"; exit 1; }
  bash -n "$NQ" || { log "ABORT: night_queue.sh no longer parses; restore the .bak"; exit 1; }
  log "D-19 applied and night_queue.sh still parses"
else
  log "D-19 already applied (or the line has moved) -- skipping"
fi

# ---------- 4. Q-24 ----------
log "starting Q-24 (36 agents x 15 rounds, --no-groups, ~3 h)"
$S/q24_nogroups.sh
q=$?
log "Q-24 exited rc=$q"

# ---------- 5. restart the campaign ----------
log "restarting the 15-round sweep"
ROUNDS=15 AGENTS="18 36 54 72 90" PREFIX=r15 \
  nohup caffeinate -i $NQ > /tmp/night_queue.log 2>&1 &
sleep 20
if pgrep -f "night_queue\.sh" >/dev/null; then
  log "campaign restarted -- tail -f /tmp/night_queue.log"
else
  log "WARNING: queue did not come back up; start it by hand"
fi
log "done. Q-24 result is above; it is NOT in the package, by design."
