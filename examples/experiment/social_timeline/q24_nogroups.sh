#!/bin/bash
# =============================================================================
# Q-24: do group actions break `follow`, and therefore the social graph?
#
# THE CASE FOR THIS RUN
# ---------------------
# `follow` is the action the model fumbles most. Across the runs whose logs
# survive, 111 of 193 malformed tool calls are `follow`, and 76 of those pass
# `group_id` -- a parameter `follow` has never had. The agent is reaching for a
# group action and landing on `follow`. B-9 already records that the group
# environment hijacks the prompt: `$groups_env` renders before `$posts_env`
# regardless of `available_actions`.
#
# It is not cosmetic. In `r15_a90` only 45.2 % of attempted follows succeeded
# (71 landed, 77 malformed, 9 named nobody), so the follow graph is under half
# what the agents tried to build -- and that graph is the network tier, which is
# the substrate of F-92/F-108, the project's headline result. A thinner tier
# costs statistical power on exactly the contrasts that are short of it.
#
# The observational evidence is suggestive but cannot settle it: the two runs
# with zero group actions have zero `group_id` errors (2/2), Spearman rho=+0.67
# p=0.07 across eight runs -- but `sweep18_a90` has 30 group actions and zero
# such errors. Only a controlled run separates the two.
#
# WHAT THIS RUNS
#   36 agents x 15 rounds, --no-groups, everything else pinned to the bank
#   configuration. 36x15 because that is where the deepest comparison set is
#   (nine identical control runs) and it costs ~3 h rather than ~7.
#
# READ THE RESULT AS
#   malformed `follow` calls per follow attempt, this run vs the group-enabled
#   runs. If `group_id` errors vanish, groups cost roughly half of all follows.
#
# THREE THINGS THIS DELIBERATELY DOES NOT DO
#   1. It does NOT rebuild the package or the charts. `--no-groups` is a
#      different action surface and therefore a different experimental
#      condition (the B-26/B-28 lesson). This run must never silently join the
#      cost bank or any pooled estimate.
#   2. It does NOT run if a simulation is already active. Two runs at once cost
#      B-32 a 2.16x inflated measurement.
#   3. It does NOT delete its log. The log is the ONLY record of a fumbled tool
#      call (F-111); `/tmp` is volatile, so the error lines are extracted at the
#      end into data/logs/.
#
# USAGE
#   examples/experiment/social_timeline/q24_nogroups.sh
# =============================================================================
set -u
cd /Users/gordon/research/oasis || exit 1
S=examples/experiment/social_timeline
P=./oasis-env/bin/python
LBL=q24_nogroups
LOG=/tmp/s18_${LBL}.log

if pgrep -f "run_simulation\.py" >/dev/null; then
  echo "REFUSING: a simulation is already running. Q-24 must not run concurrently (B-32)."
  ps -eo command | grep run_simulation | grep -v grep | grep -oE '\-\-label [^ ]+'
  exit 1
fi
if [ -f "data/social_timeline_${LBL}.json" ]; then
  echo "REFUSING: ${LBL} already has a manifest. Delete it first if you mean to redo the run."
  exit 1
fi

echo "[$(date '+%H:%M:%S')] dependency gate"
$P $S/check_deps.py || { echo "dependency gate FAILED"; exit 1; }

echo "[$(date '+%H:%M:%S')] Q-24: 36 agents x 15 rounds, --no-groups, log kept at $LOG"
$P $S/run_simulation.py \
    --agents 36 --rounds 15 --label "$LBL" \
    --seed 42 --temperature 0.7 --semaphore 4 \
    --recsys twhin-bert --request-timeout 300 \
    --no-groups \
    --personas data/reddit/user_data_36.json > "$LOG" 2>&1
rc=$?
echo "[$(date '+%H:%M:%S')] run exited rc=$rc"
[ $rc -ne 0 ] && exit $rc

$P $S/analyze.py --db data/social_timeline_${LBL}.db --log "$LOG" > /dev/null 2>&1

# Preserve the error evidence; the raw lines carry whole argument dumps (F-111).
mkdir -p data/logs
grep -a "Error executing async tool" "$LOG" \
  | sed -E "s/.*Error executing async tool '([a-z_]+)':[[:space:]]*/\1\t/" \
  | cut -c1-250 > "data/logs/${LBL}_toolerrors.txt"

echo
echo "===== Q-24 RESULT ====="
$P - <<'PY'
import json, collections
lbl="q24_nogroups"
m=json.load(open(f"data/social_timeline_{lbl}.json"))
j=json.load(open(f"data/social_timeline_{lbl}_analysis.json"))
errs=[l.split("\t")[0] for l in open(f"data/logs/{lbl}_toolerrors.txt") if l.strip()]
gid=sum(1 for l in open(f"data/logs/{lbl}_toolerrors.txt") if "group_id" in l)
ok=j["totals"]["action_counts"].get("follow",0)
bad=sum(1 for e in errs if e=="follow")
inv=m["platform_stats"]["invalid_follow_targets"]
att=ok+bad+inv
print(f"  follow: {ok} succeeded, {bad} malformed, {inv} invalid target -> {att} attempted")
print(f"  follow success rate {100*ok/att:.1f}%   follow(group_id=) errors: {gid}")
print(f"  all malformed calls: {len(errs)}   action mix: {j['totals']['action_counts']}")
src=collections.Counter()
for a in j["agents"].values():
    for k,v in (a.get("exposure_by_source") or {}).items(): src[k]+=v
t=sum(src.values())
print("  feed tiers: " + "  ".join(f"{k} {100*v/t:.2f}%" for k,v in src.most_common()))
print()
print("  COMPARE -- group-enabled runs at the same configuration:")
print("    r15_a90       45.2% follow success, 54 group_id errors")
print("    r15_s43_a90   77/99 = 77.8%,        11 group_id errors")
print("    sweep18_a72   59.6%,                11 group_id errors")
print("    bank runs (36x15, groups on): follow success not measurable, logs gone")
PY
echo
echo "NOT folded into the package or the cost bank -- different action surface, on purpose."
