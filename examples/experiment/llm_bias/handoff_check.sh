#!/bin/bash
# Handoff check (log 14.32a, 14.52). Run on the Mac.
#   handoff_check.sh read   start of a session: §0.2 top, the newest §14.x entry, git state (the catch-up bundle)
#   handoff_check.sh        end of EVERY change, before the final commit: FAILs if §0.2, §14.32 Status, the change
#                           history (§14.32c) or memory is behind the newest §14.x entry / the newest code change
cd "$(dirname "$0")/../../.." || exit 1
L=RESEARCH_LOG.md MEM=$HOME/.claude/projects/-Users-gordon-research/memory
N=$(grep -o '^## 14\.[0-9]*' $L | tail -1 | cut -c4-)        # e.g. 14.52
RE="14\\.${N#14.}([^0-9]|$)"                                  # 14.52 but not 14.520
if [ "${1:-}" = read ]; then
  sed -n '/^## 0\.2 /,/^## 0\.3 /p' $L | head -45; echo "..."
  echo "======== newest entry: §$N"; awk -v h="## $N " 'index($0,h)==1{p=1} p' $L
  echo "======== git"; git status --short | head -30; git log --oneline -8
  exit 0
fi
bad=0; fail() { echo "FAIL: $*"; bad=1; }
sed -n '/^## 0\.2 /,/^## 0\.3 /p' $L | grep -qE "§$RE" || fail "§0.2 (top of the log) does not mention §$N"
sed -n '/^## 14\.32 /,/^### 14\.32a/p' $L | grep -qE "§$RE" || fail "§14.32 Status does not mention §$N"
# newest change-history row must be dated on/after the newest code change (uncommitted code counts as today)
row=$(sed -n '/^### 14\.32c/,/^### 14\.32d/p' $L | grep '^| ' | tail -1 | cut -d'|' -f3 | grep -oE '[0-9]{2}-[0-9]{2}' | head -1)
code=$(git log -1 --format=%ad --date=format:%m-%d -- examples/experiment/llm_bias)
git status --porcelain -- examples/experiment/llm_bias | grep -v make_report_v2.py | grep -q . && code=$(date +%m-%d)
[[ "$row" < "$code" ]] && fail "change history (§14.32c) newest row is $row, code changed $code: add a row"  # ponytail: MM-DD compare, breaks across New Year
grep -qE "$RE" "$MEM/project_llm_bias_v2.md" || fail "memory project_llm_bias_v2.md does not mention $N"
grep -qE "$RE" "$MEM/MEMORY.md" || fail "MEMORY.md index line does not mention $N"
[ $bad = 0 ] && echo "HANDOFF CURRENT (§$N in §0.2, §14.32 Status, memory; change history $row >= code $code)"
exit $bad
