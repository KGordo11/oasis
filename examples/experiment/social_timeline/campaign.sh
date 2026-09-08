#!/bin/zsh
# =============================================================================
# The unconstrained campaign. Resumable, phased, engagement-gated.
#
# WHAT THIS IS FOR
# ----------------
# Settle the efficiency question with enough runs to actually answer it, then
# spend the rest of the time on what efficiency was ever for: replicates.
#
# WHY IT IS SIZED THIS WAY
# ------------------------
# Wall-clock noise on this setup is ~15% of the mean (two runs at an identical
# config came out 355 and 408 s/round). Power arithmetic at alpha .05 /
# power .8:
#
#     to resolve a 40% difference   ~2 runs per arm
#     to resolve a 30% difference   ~4 runs per arm
#     to resolve a 20% difference   ~9 runs per arm
#     to resolve a 10% difference  ~35 runs per arm
#
# `lean` is expected ~1.3x (30%) and `onecall` ~1.24x (24%), so 5 per arm is
# the minimum that can see either, and 3 per arm -- what the earlier script
# used -- could only have seen 30%+. That is why this one is bigger.
#
# ENGAGEMENT IS DIFFERENT AND THE SCRIPT DOES NOT PRETEND OTHERWISE. Baseline
# engagement is ~5.9% of shown posts. Detecting a 1pp shift would take far
# more runs than any campaign affords, so the claim this can support is "no
# gross breakage" (the 0.00% collapses of F-63) and NOT "no behavioural
# effect". Phase 1's report says so in those words.
#
# EVERYTHING HERE IS A REACTION TO SOMETHING THAT WENT WRONG
#   B-22  every run has a 300s request timeout and a 20-minute stall watchdog,
#         because an unguarded hang once cost a full day.
#   B-23  every run is gated on ENGAGEMENT, not activity, because a config
#         that looked healthy on every other metric had 1 engagement in 42,336
#         exposures and burned seven full runs before anyone checked.
#   F-60  nothing is screened below 36 agents; small benchmarks in this project
#         have overpredicted four times running.
#   F-65  OLLAMA_CONTEXT_LENGTH is set explicitly, because NUM_PARALLEL splits
#         the window and silently truncated every prompt of one campaign.
#
# RESUMABLE. Any run whose manifest already exists is skipped, so an interrupt
# costs one run, not the campaign. Results append to $R as they land.
#
# USAGE
#   examples/experiment/social_timeline/campaign.sh [phase]
#     (no arg)  run every phase in order
#     1|2|3     run just that phase
# =============================================================================
cd /Users/gordon/research/oasis || exit 1
P=./oasis-env/bin/python
export OASIS_ALLOW_SERIAL_OLLAMA=1

REPS=5                      # per arm in phase 1; see power note above
R=/tmp/campaign_results.txt
touch $R
log(){ echo "[$(date '+%m-%d %H:%M:%S')] $*"; }

cat > /tmp/c_engage.py <<'PY'
import json, sys
try:
    a = json.load(open(f"data/social_timeline_{sys.argv[1]}_analysis.json")).get("agents") or {}
    h = sum(len(x.get("seen_and_acted") or []) for x in a.values())
    s = h + sum(len(x.get("seen_and_ignored") or []) for x in a.values())
    print(f"{100*h/s:.2f}" if s else "0.00")
except Exception:
    print("0.00")
PY

server () {
  pkill -f "ollama serve" 2>/dev/null; pkill -f "ollama runner" 2>/dev/null
  sleep 6
  OLLAMA_NUM_PARALLEL=8 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_KEEP_ALIVE=600m \
    OLLAMA_FLASH_ATTENTION=true nohup ollama serve > /tmp/c_ollama.log 2>&1 &
  sleep 15
  curl -s -m 10 http://localhost:11434/api/tags >/dev/null
}

watchdog () {   # B-22
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

one () {   # $1=label $2=rounds $3..=flags
  local lbl=$1 rd=$2; shift 2
  if [ -f data/social_timeline_$lbl.json ]; then
    log "  $lbl already done, skipping"; return
  fi
  rm -f data/social_timeline_$lbl.db
  local t0=$(date +%s)
  $P examples/experiment/social_timeline/run_simulation.py \
     --agents 36 --rounds $rd --label $lbl --no-groups --temperature 0.7 \
     --semaphore 8 --request-timeout 300 "$@" > /tmp/c_$lbl.log 2>&1 &
  local pid=$!; watchdog $lbl $pid & local wd=$!
  wait $pid 2>/dev/null; kill $wd 2>/dev/null
  local t=$(( $(date +%s) - t0 ))
  if [ ! -f data/social_timeline_$lbl.json ]; then
    log "  $lbl INCOMPLETE after ${t}s"; echo "$lbl $rd NA NA" >> $R; return
  fi
  $P examples/experiment/social_timeline/analyze.py \
     --db data/social_timeline_$lbl.db > /dev/null 2>&1
  local e=$($P /tmp/c_engage.py "$lbl")
  local flag=""
  # B-23: below 1% is the F-63 collapse, not a quiet run.
  [ "${e%%.*}" -lt 1 ] 2>/dev/null && flag="  <<< ENGAGEMENT COLLAPSE"
  log "  $lbl  ${t}s  engagement ${e}%$flag"
  echo "$lbl $rd $t $e" >> $R
}

# ---------------------------------------------------------------- phase 1
phase1 () {
  log "########## PHASE 1 — efficiency A/B, $REPS replicates x 4 arms x 3 rounds ##########"
  server || { log "ollama will not start"; return 1; }
  for i in $(seq 1 $REPS); do
    log "--- replicate $i of $REPS ---"
    one c1_control_r$i 3
    one c1_lean_r$i    3 --lean-actions
    one c1_onecall_r$i 3 --max-tool-rounds 1
    one c1_both_r$i    3 --lean-actions --max-tool-rounds 1
    server            # fresh server each replicate: guards against drift over hours
  done
  $P /tmp/c_report1.py
}

# ---------------------------------------------------------------- phase 2
# Confirm the phase-1 winner over a FULL 15-round run. A 3-round screen scaled
# by 6.26 is an estimate, and this project's estimates have a poor record.
phase2 () {
  log "########## PHASE 2 — full 15-round validation ##########"
  local win=$($P /tmp/c_winner.py)
  log "  phase-1 winner: $win"
  server
  case $win in
    lean)    F=(--lean-actions) ;;
    onecall) F=(--max-tool-rounds 1) ;;
    both)    F=(--lean-actions --max-tool-rounds 1) ;;
    *)       F=() ;;
  esac
  for i in 1 2 3; do
    one c2_full_${win}_r$i 15 "${F[@]}"
    server
  done
  one c2_full_control_r1 15      # a full-length control to compare against
}

# ---------------------------------------------------------------- phase 3
# What efficiency was always for. F-35's noise floor is the ceiling on every
# behavioural question this project can ask, and the only cure is more runs at
# one fixed configuration.
phase3 () {
  log "########## PHASE 3 — replicate bank at the validated config ##########"
  local win=$($P /tmp/c_winner.py)
  case $win in
    lean)    F=(--lean-actions) ;;
    onecall) F=(--max-tool-rounds 1) ;;
    both)    F=(--lean-actions --max-tool-rounds 1) ;;
    *)       F=() ;;
  esac
  server
  for i in $(seq 1 12); do
    one c3_bank_r$i 15 "${F[@]}"
    [ $((i % 3)) -eq 0 ] && server
  done
}

# ---------------------------------------------------------------- reporting
cat > /tmp/c_winner.py <<'PY'
# Fastest arm that did NOT collapse engagement. Speed alone never wins here.
import collections, statistics
rows=collections.defaultdict(list)
for line in open('/tmp/campaign_results.txt'):
    p=line.split()
    if len(p)==4 and p[2] not in ("NA",) and p[0].startswith("c1_"):
        arm=p[0].split('_')[1]
        rows[arm].append((int(p[2]), float(p[3])))
ok=[]
for arm,v in rows.items():
    if not v: continue
    if statistics.mean(x[1] for x in v) < 1.0:   # B-23 collapse
        continue
    ok.append((statistics.mean(x[0] for x in v), arm))
print(sorted(ok)[0][1] if ok else "control")
PY

cat > /tmp/c_report1.py <<'PY'
import collections, statistics
rows=collections.defaultdict(list)
for line in open('/tmp/campaign_results.txt'):
    p=line.split()
    if len(p)==4 and p[2]!="NA" and p[0].startswith("c1_"):
        rows[p[0].split('_')[1]].append((int(p[2]), float(p[3])))
print(f"\n  {'arm':<10}{'n':>3}{'mean s':>9}{'sd':>8}{'range':>15}{'speedup':>9}{'engagement':>13}")
base=None
for arm in ("control","lean","onecall","both"):
    v=rows.get(arm) or []
    if not v:
        print(f"  {arm:<10}  no completed runs"); continue
    t=[x[0] for x in v]; e=[x[1] for x in v]
    m=statistics.mean(t); base = base or m
    sd=statistics.stdev(t) if len(t)>1 else 0
    print(f"  {arm:<10}{len(v):>3}{m:>9.0f}{sd:>8.0f}{f'{min(t)}-{max(t)}':>15}"
          f"{base/m:>8.2f}x{statistics.mean(e):>11.2f}%")
print()
print("  HOW TO READ THIS")
print("   * Compare the sd and range before the speedup. If arms overlap, the")
print("     difference is not resolvable at this n, which is a real answer.")
print("   * Engagement near 0% is the F-63 collapse: fast and scientifically")
print("     dead. Engagement within ~1pp of control is 'no gross breakage'")
print("     and NOT 'no behavioural effect' -- this n cannot see 1pp.")
PY

case "${1:-all}" in
  1) phase1 ;;
  2) phase2 ;;
  3) phase3 ;;
  *) phase1 && phase2 && phase3
     log "########## EXPORT ##########"
     $P examples/experiment/social_timeline/export_parquet.py --all \
        --data-dir data --out data/parquet > /tmp/c_export.log 2>&1
     log "########## CAMPAIGN COMPLETE ##########"
     $P /tmp/c_report1.py ;;
esac
