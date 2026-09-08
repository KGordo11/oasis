#!/bin/zsh
# =============================================================================
# Paired A/B for the two remaining efficiency levers, WITH REPLICATES.
#
# WHY REPLICATES, AND WHY THIS SCRIPT EXISTS
# ------------------------------------------
# Every efficiency claim in this project that was made from a single pair of
# runs has been wrong. F-51 (concurrency), F-55 (prefill share), F-66 (persona
# hoisting) all predicted large wins from one measurement and delivered
# roughly nothing at 36 agents. F-35 is the reason: run-to-run noise on this
# setup is ~28pp on behaviour and ~15% on wall clock, and a single pair cannot
# see past it.
#
# So each condition runs N times, and the comparison is made on the means with
# the spread reported next to them. If the spread overlaps, the answer is "not
# resolvable at this N", which is a real answer and the one this project has
# most often needed.
#
# WHAT IS BEING TESTED
# --------------------
#   control        the current default: terse tools, uncapped output
#   lean           control minus the 8 actions F-48 found never fire.
#                  Expected ~1.3x from a smaller tool block. RISK: a single
#                  earlier pair showed engagement 4.31% -> 3.87%, the wrong
#                  direction, inside noise. That is exactly what replicates
#                  are for.
#   onecall        control with camel's tool loop capped at one model call.
#                  Expected ~24% from removing the follow-up call (Q-23).
#                  RISK: an agent wanting a second action in a second
#                  round-trip loses it.
#
# EVERY run is checked for ENGAGEMENT, not just speed. B-23: a config that
# halves runtime by making agents stop reacting to their feed is not an
# optimisation, and the gate that only counted activity waved exactly that
# through for seven full runs.
#
# USAGE
#   examples/experiment/social_timeline/ab_efficiency.sh [replicates] [rounds]
#   defaults: 3 replicates, 3 rounds, 36 agents  (~2.5 h)
# =============================================================================
cd /Users/gordon/research/oasis || exit 1
P=./oasis-env/bin/python
export OASIS_ALLOW_SERIAL_OLLAMA=1

REPS=${1:-3}
ROUNDS=${2:-3}
R=/tmp/ab_efficiency.txt
: > $R
log(){ echo "[$(date '+%H:%M:%S')] $*"; }

# F-65: NUM_PARALLEL splits the context window, so raising it without raising
# OLLAMA_CONTEXT_LENGTH silently truncates prompts. 8192 per slot at NP=8 is
# ~7 GiB of KV against 21.3 GiB available.
log "starting ollama: NUM_PARALLEL=8, CONTEXT_LENGTH=8192"
pkill -f "ollama serve" 2>/dev/null; pkill -f "ollama runner" 2>/dev/null; sleep 6
OLLAMA_NUM_PARALLEL=8 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=600m \
  OLLAMA_FLASH_ATTENTION=true nohup ollama serve > /tmp/ab_ollama.log 2>&1 &
sleep 15

# Heredocs inside $( ) are not portable in zsh, so the two python helpers are
# written to files first and invoked normally.
cat > /tmp/ab_engagement.py <<'PY'
import json, sys
try:
    a = json.load(open(f"data/social_timeline_{sys.argv[1]}_analysis.json")).get("agents") or {}
    h = sum(len(x.get("seen_and_acted") or []) for x in a.values())
    s = h + sum(len(x.get("seen_and_ignored") or []) for x in a.values())
    print(f"{100*h/s:.2f}" if s else "0.00")
except Exception:
    print("0.00")
PY

watchdog () {   # B-22: a stall and a slow round look identical from outside
  local db=data/social_timeline_$1.db last=0 same=0
  while kill -0 $2 2>/dev/null; do
    sleep 120
    local now=$( [ -f $db ] && stat -f %m $db || echo 0 )
    if [ "$now" = "$last" ]; then
      same=$((same+1))
      [ $same -ge 10 ] && { log "  WATCHDOG killed $1"; kill -9 $2 2>/dev/null; return; }
    else same=0; last=$now; fi
  done
}

one () {   # $1=label  $2..=extra flags
  local lbl=$1; shift
  rm -f data/social_timeline_$lbl.db data/social_timeline_$lbl.json
  local t0=$(date +%s)
  $P examples/experiment/social_timeline/run_simulation.py \
     --agents 36 --rounds $ROUNDS --label $lbl --no-groups --temperature 0.7 \
     --semaphore 8 --request-timeout 300 "$@" > /tmp/ab_$lbl.log 2>&1 &
  local pid=$!; watchdog $lbl $pid & local wd=$!
  wait $pid 2>/dev/null; kill $wd 2>/dev/null
  local t=$(( $(date +%s) - t0 ))
  if [ ! -f data/social_timeline_$lbl.json ]; then
    log "  $lbl INCOMPLETE"; echo "$lbl NA NA" >> $R; return
  fi
  $P examples/experiment/social_timeline/analyze.py \
     --db data/social_timeline_$lbl.db > /dev/null 2>&1
  local eng=$($P /tmp/ab_engagement.py "$lbl")
  log "  $lbl  ${t}s  engagement ${eng}%"
  echo "$lbl $t $eng" >> $R
}

log "############ A/B: $REPS replicates x 3 conditions x ${ROUNDS} rounds ############"
for i in $(seq 1 $REPS); do
  log "--- replicate $i of $REPS ---"
  one ab_control_r$i
  one ab_lean_r$i    --lean-actions
  one ab_onecall_r$i --max-tool-rounds 1
done

log "############ RESULTS ############"
cat > /tmp/ab_report.py <<'PY'
import collections, statistics
rows=collections.defaultdict(list)
for line in open('/tmp/ab_efficiency.txt'):
    p=line.split()
    if len(p)==3 and p[1]!="NA":
        cond=p[0].rsplit('_r',1)[0]
        rows[cond].append((int(p[1]), float(p[2])))
base=None
print(f"  {'condition':<14}{'n':>3}{'mean s':>9}{'spread':>16}{'speedup':>9}{'engagement':>13}")
for cond in ("ab_control","ab_lean","ab_onecall"):
    v=rows.get(cond) or []
    if not v: print(f"  {cond:<14}  no completed runs"); continue
    t=[x[0] for x in v]; e=[x[1] for x in v]
    mt=statistics.mean(t); base = base or mt
    sp=f"{min(t)}-{max(t)}"
    print(f"  {cond:<14}{len(v):>3}{mt:>9.0f}{sp:>16}{base/mt:>8.2f}x"
          f"{statistics.mean(e):>11.2f}%")
print()
print("  Read the spread before the speedup. If the ranges overlap, the")
print("  difference is not resolvable at this n -- which is the honest answer,")
print("  and the one four earlier 'wins' in this project turned out to need.")
PY
$P /tmp/ab_report.py
