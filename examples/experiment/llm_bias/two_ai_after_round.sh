#!/bin/bash
# After each round of two_ai_campaign.sh: record the round's wall time (for the stop-before-3pm rule),
# check + analyse every finished round so far, commit and push the data (worlds + post bank; oasis.db is ignored).
set -u
cd "$(dirname "$0")/../../.."; mkdir -p data/llm_bias/two_ai
P=./oasis-env/bin/python; S=examples/experiment/llm_bias; R=$1; RR=$(printf %02d $R)
$P - "$RR" <<'PY'
import json, glob, sys
from datetime import datetime
ms = [json.load(open(f)) for f in glob.glob(f"data/llm_bias/worlds/two_r{sys.argv[1]}_*/manifest.json")]
t = [datetime.fromisoformat(m[k]) for m in ms for k in ("started_at", "finished_at") if k in m]
s = int((max(t) - min(t)).total_seconds())
open("data/llm_bias/two_ai_round_s.txt", "w").write(str(s))
print(f"round {sys.argv[1]}: {s / 60:.0f} min")
PY
$P $S/check_world.py --prefix two_r >> data/llm_bias/two_ai_checks.txt 2>&1 || true
taskpolicy -b $P $S/analyze_two_ai.py 1000 > data/llm_bias/two_ai/summary.txt 2>&1 || true  # background QoS: don't slow the run
$P $S/make_two_ai_page.py /private/tmp/claude-501/-Users-gordon-research/19a036d6-ce9e-41eb-bda1-be700f315042/scratchpad/two_ai_page || true
git add data/llm_bias/worlds/two_r${RR}_* data/llm_bias/postbank_s$((200 + R)).jsonl data/llm_bias/two_ai \
        data/llm_bias/two_ai_* data/llm_bias/two_ai_checks.txt 2>/dev/null
git commit -qm "Two-AI round $R data (100 users x 50 posts x 2 AIs)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q origin llm-bias
echo "$(date '+%F %T') round $R committed"
