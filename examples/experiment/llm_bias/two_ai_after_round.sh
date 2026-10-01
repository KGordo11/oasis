#!/bin/bash
# After each round of two_ai_campaign.sh: record the round's wall time (for the stop-before-3pm rule),
# check + analyse every finished round so far, commit and push the data (worlds + post bank; oasis.db is ignored).
set -u
cd "$(dirname "$0")/../../.."
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
$P $S/analyze_world.py --prefix two_r --out data/llm_bias/analysis_two_ai.json > data/llm_bias/analysis_two_ai.txt 2>&1 || true
git add data/llm_bias/worlds/two_r${RR}_* data/llm_bias/postbank_s$((200 + R)).jsonl data/llm_bias/analysis_two_ai.* \
        data/llm_bias/two_ai_* data/llm_bias/two_ai_checks.txt 2>/dev/null
git commit -qm "Two-AI round $R data (100 users x 50 posts x 2 AIs)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q origin llm-bias
echo "$(date '+%F %T') round $R committed"
