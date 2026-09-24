#!/bin/bash
# Night 1 follow-on queue (2026-09-23). Waits for the main campaign, then:
#   1. self-recognition probe on seed 1 (LQ-2), ~20 min
#   2. second topic: cars, seed 2, 99 personas x 3 rounds x 7 judges, ~2 h
# One thing at a time: no two inference jobs ever overlap (B-32).
cd "$(dirname "$0")/../../.."
P=./oasis-env/bin/python; S=examples/experiment/llm_bias
while pgrep -f "llm_bias/campaign.sh" >/dev/null; do sleep 30; done
echo "$(date '+%F %T') main campaign finished; starting recognition probe"
$P $S/recognize.py --seed 1 --k 4 > data/llm_bias/recognition_s1.txt 2>&1
echo "$(date '+%F %T') recognition done rc=$?"
SEED=2 AGENTS=99 ROUNDS=3 PREFIX=cars TOPICS=cars $S/campaign.sh > data/llm_bias/campaign_cars_s2.log 2>&1
echo "$(date '+%F %T') cars campaign done"
