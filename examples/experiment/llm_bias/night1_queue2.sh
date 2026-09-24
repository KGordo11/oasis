#!/bin/bash
# Night 1, part 2: after the cars campaign, extend the recognition probe on seed 1
# from k=4 to k=20 shuffles per slot (resumable: the first 4 are reused).
cd "$(dirname "$0")/../../.."
while pgrep -f night1_queue.sh >/dev/null; do sleep 30; done
echo "$(date '+%F %T') starting recognition k=20"
./oasis-env/bin/python examples/experiment/llm_bias/recognize.py --seed 1 --k 20 > data/llm_bias/recognition_s1.txt 2>&1
echo "$(date '+%F %T') recognition k=20 done rc=$?"
