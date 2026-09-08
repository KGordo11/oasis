#!/bin/zsh
# =============================================================================
# Overnight efficiency campaign — 8 hour budget, fully unattended.
#
# WHAT THIS IS FOR
# ----------------
# 99.9% of a run is the language model generating tokens (Q-16, measured
# in-run). No configuration change touches that. The only real levers are the
# model itself and how many tokens it emits, so this night measures exactly
# those, at full agent scale, and then spends whatever time is left on the
# thing the science actually needs: replicates.
#
# DESIGN RULES, EACH ONE PAID FOR
# -------------------------------
#  * Screening runs use 36 agents, never fewer. F-60: micro-benchmarks
#    predicted 1.9-3.1x for the concurrency fix and the true figure at full
#    scale was +0.6%. A saturated 36-agent queue behaves nothing like a small
#    one. Fewer ROUNDS is a fair economy; fewer AGENTS is not.
#  * Every config is gated on behaviour, not just speed. A config that halves
#    runtime by making agents stop acting is not an optimisation, it is a
#    broken experiment. Gates below.
#  * Nothing is assumed about how long anything takes. Phase B reads the
#    measured screen times and packs the remaining budget from them.
#  * A hard deadline. The script stops starting new work when it cannot
#    finish, rather than being killed mid-run and losing the data.
#  * B-22 guards on every run: a 300s per-request timeout, and a watchdog that
#    kills a run whose database stops growing for 20 minutes. An unguarded
#    stall cost a full day on 2026-09-05.
#  * analyze.py after every run, so compare.py can speak at the end. The night
#    should produce conclusions, not a pile of databases.
#
# WHAT WAS CONSIDERED AND REJECTED
# --------------------------------
#  * Removing the `refresh` action. It looked like the biggest lever going --
#    56% of all recorded actions. It is not a model choice at all: the 504
#    refresh rows in `baseline` are exactly 36 agents x 14 rounds, because
#    `to_text_prompt()` calls `action.refresh()` itself to build the prompt.
#    Removing the tool would save its schema and nothing else.
#  * Suppressing camel's follow-up call after tool execution. Real cost is
#    1.31 LLM calls per turn, so this is worth ~24% -- genuinely large. It
#    also means changing how tool calls are handled, which is what D-2 exists
#    to forbid. Recorded as Q-23, not attempted at 2am unattended.
#  * More concurrency. F-61 settled it: 8 is optimal, 16 is 10% worse, and
#    past 16 the KV cache spills to CPU and throughput falls threefold.
#
# USAGE
#   examples/experiment/social_timeline/overnight.sh [budget_minutes]
# =============================================================================
cd /Users/gordon/research/oasis || exit 1
P=./oasis-env/bin/python
export OASIS_ALLOW_SERIAL_OLLAMA=1

BUDGET_MIN=${1:-480}
START=$(date +%s)
DEADLINE=$(( START + BUDGET_MIN * 60 ))
R=/tmp/overnight_results.txt
: > $R

log(){ echo "[$(date '+%m-%d %H:%M:%S')] $*"; }
left(){ echo $(( (DEADLINE - $(date +%s)) / 60 )); }

server () {
  pkill -f "ollama serve" 2>/dev/null; pkill -f "ollama runner" 2>/dev/null
  sleep 6
  OLLAMA_NUM_PARALLEL=8 OLLAMA_KEEP_ALIVE=600m OLLAMA_FLASH_ATTENTION=true \
    nohup ollama serve > /tmp/ov_ollama.log 2>&1 &
  sleep 15
  curl -s -m 8 http://localhost:11434/api/tags >/dev/null
}

# B-22. A stalled run and a slow run look identical from outside unless
# something compares progress against elapsed time. Worst observed round is
# ~9 minutes, so 20 minutes of a completely static database is a stall.
watchdog () {   # $1=label $2=pid
  local db=data/social_timeline_$1.db last=0 same=0
  while kill -0 $2 2>/dev/null; do
    sleep 120
    local now=$( [ -f $db ] && stat -f %m $db || echo 0 )
    if [ "$now" = "$last" ]; then
      same=$((same+1))
      if [ $same -ge 10 ]; then
        log "    WATCHDOG: $1 static for 20 min -- killing"
        kill -9 $2 2>/dev/null; return
      fi
    else same=0; last=$now; fi
  done
}

# Behavioural gate. Speed means nothing if the agents stopped behaving.
# Thresholds are deliberately loose -- this catches a broken condition, not a
# subtly different one, which at F-35's ~28pp noise floor no single run could
# resolve anyway.
gate () {   # $1=label -> prints "PASS ..." or "FAIL ..."
  $P - "$1" <<'PY'
import json, sqlite3, sys
lbl = sys.argv[1]
try:
    m = json.load(open(f"data/social_timeline_{lbl}.json"))
except Exception as e:
    print(f"FAIL  no manifest ({e})"); raise SystemExit
c = sqlite3.connect(f"data/social_timeline_{lbl}.db")
q = lambda s: c.execute(s).fetchone()[0]
agents  = m["config"]["agents"]; rounds = len(m.get("rounds") or [])
turns   = agents * max(rounds - 1, 1)
acts    = q("SELECT COUNT(*) FROM trace WHERE action NOT IN ('sign_up','refresh')")
posts   = q("SELECT COUNT(*) FROM post")
exps    = q("SELECT COUNT(*) FROM rec_history")
kinds   = q("SELECT COUNT(DISTINCT action) FROM trace")
malf    = (m.get("platform_stats") or {}).get("blind_actions_rejected", 0)
c.close()

# B-23. THE check, and the one the first version of this gate did not make.
# This study measures engagement with a post the agent was SHOWN. A config can
# keep every other number healthy -- actions per turn, posts written, a full
# 12-slot feed -- while agents never react to anything, and then it answers no
# research question at all. `max_tokens=512` did exactly that: it looked 1.9x
# faster and had 1 engagement in 42,336 exposures, and seven full runs were
# spent on it before anyone looked.
#
# Taken from analyze.py's own seen_and_acted, so the gate and the analysis
# cannot drift apart on the definition.
eng_rate = None
try:
    a = json.load(open(f"data/social_timeline_{lbl}_analysis.json")).get("agents") or {}
    hit  = sum(len(x.get("seen_and_acted") or []) for x in a.values())
    seen = hit + sum(len(x.get("seen_and_ignored") or []) for x in a.values())
    eng_rate = hit / seen if seen else 0.0
except Exception:
    pass

rate = acts / turns if turns else 0
feed = exps / turns if turns else 0
bad = []
if rate < 0.25: bad.append(f"action rate {rate:.2f}/turn (baseline ~0.75)")
if posts < agents * 0.5: bad.append(f"only {posts} posts")
if feed > 13.0: bad.append(f"{feed:.1f} exposures/turn -- double-logged?")
if feed <= 0.0: bad.append("no exposures logged at all")
if posts >= agents and feed < 11.0: bad.append(f"{feed:.1f} exposures/turn on {posts} posts, expected ~12")
if kinds < 3: bad.append(f"only {kinds} distinct actions")
# baseline 2.40%, s_ctrl 4.31%; the broken configs sit at 0.00%. 1.0% splits
# them with room on both sides.
if eng_rate is None: bad.append("no analysis json -- cannot check engagement")
elif eng_rate < 0.010: bad.append(f"engagement {100*eng_rate:.2f}% of seen posts (baseline 2.40%)")

verdict = "FAIL" if bad else "PASS"
er = "n/a" if eng_rate is None else f"{100*eng_rate:.2f}%"
print(f"{verdict}  actions/turn {rate:.2f} | posts {posts} | exposures/turn {feed:.1f} "
      f"| ENGAGE {er} | kinds {kinds} | blind-rejects {malf}"
      + ("  << " + "; ".join(bad) if bad else ""))
PY
}

sim () {  # $1=label $2=rounds $3..=flags ; echoes elapsed seconds
  local lbl=$1 rd=$2; shift 2
  rm -f data/social_timeline_$lbl.db data/social_timeline_$lbl.json
  local t0=$(date +%s)
  $P examples/experiment/social_timeline/run_simulation.py \
     --agents 36 --rounds $rd --label $lbl --no-groups --temperature 0.7 \
     --semaphore 8 --request-timeout 300 "$@" > /tmp/ov_$lbl.log 2>&1 &
  local pid=$!; watchdog $lbl $pid & local wd=$!
  wait $pid 2>/dev/null; kill $wd 2>/dev/null
  local t=$(( $(date +%s) - t0 ))
  if [ -f data/social_timeline_$lbl.json ]; then
    $P examples/experiment/social_timeline/analyze.py \
       --db data/social_timeline_$lbl.db > /tmp/ov_analyze_$lbl.log 2>&1
    local g=$(gate $lbl)
    # Log to STDERR. sim() is called inside $( ) during screening, so anything
    # on stdout would be captured as the return value instead of the elapsed
    # seconds -- which silently made every screen "time" a wall of log text.
    log "  $lbl: ${t}s ($(echo "scale=1; $t/$rd" | bc)s/round)  $g" >&2
    echo "$lbl $rd $t ${g%% *}" >> $R
  else
    log "  $lbl: INCOMPLETE after ${t}s" >&2
    echo "$lbl $rd FAILED -" >> $R
  fi
  echo $t
}

# ---------------------------------------------------------------- phase A
log "############ PHASE A — screen the levers, 36 agents x 3 rounds ############"
log "budget ${BUDGET_MIN} min, deadline $(date -r $DEADLINE '+%H:%M')"
server || { log "ollama would not start"; exit 1; }

sim s_ctrl   3 --max-tokens 999999999                                  >/dev/null
sim s_cap    3 --max-tokens 512                                        >/dev/null
sim s_lean   3 --max-tokens 512 --lean-actions                         >/dev/null
sim s_3b     3 --max-tokens 512 --model llama3.2:3b                    >/dev/null
sim s_3blean 3 --max-tokens 512 --model llama3.2:3b --lean-actions     >/dev/null

log "############ SCREEN COMPLETE — $(left) min left ############"
cat $R

# Winner is needed by the scaling phase too, so resolve it here.
BEST_EARLY=$($P - <<'PY'
rows=[]
for line in open('/tmp/overnight_results.txt'):
    p=line.split()
    if len(p)==4 and p[2].isdigit() and p[3]=="PASS":
        rows.append((int(p[2]), p[0]))
print(sorted(rows)[0][1] if rows else "s_ctrl")
PY
)
case $BEST_EARLY in
  s_ctrl)    WIN_FLAGS_EARLY="--max-tokens 999999999" ;;
  s_cap)     WIN_FLAGS_EARLY="--max-tokens 512" ;;
  s_lean)    WIN_FLAGS_EARLY="--max-tokens 512 --lean-actions" ;;
  s_3b)      WIN_FLAGS_EARLY="--max-tokens 512 --model llama3.2:3b" ;;
  s_3blean)  WIN_FLAGS_EARLY="--max-tokens 512 --model llama3.2:3b --lean-actions" ;;
esac
log "screen winner: $BEST_EARLY ($WIN_FLAGS_EARLY)"

# ------------------------------------------------------- phase A2: scaling
# Does cost grow linearly with agent count, or worse? This is the question
# "is it scalable" actually asks, and nothing in the project has ever measured
# it -- every run has been 36 agents.
#
# What the answer distinguishes:
#   linear      -> the GPU is saturated and each agent is a fixed cost. Bigger
#                  worlds are affordable in proportion, and nothing else is
#                  broken.
#   super-linear-> something in OUR code is quadratic in agents. That would be
#                  a real bug worth hunting, and it is exactly what F-57 found
#                  hiding in the ranking loop before it was vectorised.
#   sub-linear  -> the GPU was NOT saturated at 36 and there is headroom.
#
# Held at 3 rounds so post accumulation does not confound the agent-count
# effect, and run at the winning config so it measures the system as it will
# actually be used.
log "############ PHASE A2 — does cost scale with agent count? ############"
scale () {   # $1=agents
  local lbl=sc_$1 t0=$(date +%s)
  rm -f data/social_timeline_$lbl.db data/social_timeline_$lbl.json
  $P examples/experiment/social_timeline/run_simulation.py \
     --agents $1 --rounds 3 --label $lbl --no-groups --temperature 0.7 \
     --semaphore 8 --request-timeout 300 ${=WIN_FLAGS_EARLY} \
     > /tmp/ov_$lbl.log 2>&1 &
  local pid=$!; watchdog $lbl $pid & local wd=$!
  wait $pid 2>/dev/null; kill $wd 2>/dev/null
  local t=$(( $(date +%s) - t0 ))
  log "  ${1} agents: ${t}s  ($(echo "scale=2; $t/$1" | bc)s per agent)"
  echo "SCALE $1 $t" >> $R
}
for A in 12 24 36 72; do
  [ $(left) -lt 60 ] && { log "  skipping ${A} agents, only $(left) min left"; break; }
  scale $A
done

# ---------------------------------------------------------------- decide
# Pick the fastest config that also PASSED its behavioural gate. Speed alone
# is not a winner; a broken condition that runs fast is worth nothing.
BEST=$($P - <<'PY'
import re
rows=[]
for line in open('/tmp/overnight_results.txt'):
    p=line.split()
    if len(p)==4 and p[2].isdigit() and p[3]=="PASS":
        rows.append((int(p[2]), p[0]))
print(sorted(rows)[0][1] if rows else "s_ctrl")
PY
)
FLAGS_s_ctrl="--max-tokens 999999999"
FLAGS_s_cap="--max-tokens 512"
FLAGS_s_lean="--max-tokens 512 --lean-actions"
FLAGS_s_3b="--max-tokens 512 --model llama3.2:3b"
FLAGS_s_3blean="--max-tokens 512 --model llama3.2:3b --lean-actions"
eval "WIN_FLAGS=\$FLAGS_$BEST"
SCREEN_T=$(grep "^$BEST " $R | awk '{print $3}')
# Measured on `baseline`: its first three rounds are 1,164s and the full
# fifteen are 7,279s -- a factor of 6.26, not the 5.0 a naive per-round scaling
# would give, because each round ranks more posts and feeds more history.
# Using 5.0 here would have under-booked every full run by 25% and left the
# script starting work it could not finish before the deadline.
EST_FULL=$(( SCREEN_T * 63 / 10 / 60 ))    # minutes for a 36x15 run
log "############ WINNER: $BEST  (${WIN_FLAGS}) — est ${EST_FULL} min per full run ############"

# ---------------------------------------------------------------- phase B
# One full run at the best 8b-family config so there is always an
# 8b-comparable dataset, then as many replicates of the winner as fit.
# Replicates are the point: F-35's noise floor means a single run cannot
# resolve any behavioural question, and replicates are what the study has
# never been able to afford.
log "############ PHASE B — full runs, $(left) min left ############"
server
N=0
while [ $(left) -gt $(( EST_FULL + 25 )) ] && [ $N -lt 8 ]; do
  N=$((N+1))
  log "  full run $N of the winner ($BEST), $(left) min left"
  sim ov_${BEST}_r${N} 15 ${=WIN_FLAGS} > /dev/null
done
log "############ PHASE B done: $N full run(s) ############"

# ---------------------------------------------------------------- phase C
log "############ PHASE C — compare and export ############"
CTRL_REF=baseline
for f in data/social_timeline_ov_*.json; do
  [ -e "$f" ] || continue
  lbl=$(basename $f .json); lbl=${lbl#social_timeline_}
  $P examples/experiment/social_timeline/compare.py --runs $CTRL_REF $lbl \
     --data-dir data --out data/overnight_cmp_$lbl.txt > /dev/null 2>&1 \
     && log "  compared $CTRL_REF -> $lbl"
done
$P examples/experiment/social_timeline/export_parquet.py --all --data-dir data \
   --out data/parquet > /tmp/ov_export.log 2>&1
log "  parquet export done"

log "############ NIGHT COMPLETE — $(( ($(date +%s)-START)/60 )) min used ############"
cat $R
