#!/bin/bash
# Can two sims share the machine? (Gordon, 2026-09-25: "can you not run 2 full sims at the same time")
#
# IN PLAIN WORDS: the same 8 people and the same posts, run four ways, timing each:
#   A  llama alone              B  gemma alone
#   C  llama AND gemma at once  (two processes; a world today runs them one after the other)
#   D  two llama jobs at once   (two different post sets, so the requests are not identical)
# If C takes about as long as A alone, running both models together would cut a world from
# ~65 to ~51 minutes. If D takes twice as long as A, the chip is already full and a second
# full sim gains nothing. Labels start bench_cc_, so no analysis or chart ever mixes them in.
# Waits until no campaign, sweep or world is running (B-32: never time two jobs at once).
cd "$(dirname "$0")/../../.."
P=./oasis-env/bin/python; S=examples/experiment/llm_bias; N=${N:-8}
OUT=data/llm_bias/bench_concurrency.txt
while pgrep -f "world_campaign.sh|agent_sweep.sh|run_world.py" >/dev/null; do sleep 60; done
run() { # label seed judge
  $P $S/run_world.py --label "$1" --seed "$2" --world 0 --agents "$N" --judges "$3" \
     --authors llama3.1:8b,gemma4:e2b --overwrite > "/tmp/llm_bias_$1.log" 2>&1; }
stamp() { date +%s.%N | cut -c1-14; }
echo "$(date '+%F %T') bench start N=$N" | tee -a $OUT
t0=$(stamp); run bench_cc_A_llama 10 llama3.1:8b; t1=$(stamp)
echo "A llama alone: $(echo "$t1 - $t0" | bc) s" | tee -a $OUT
t0=$(stamp); run bench_cc_B_gemma 10 gemma4:e2b; t1=$(stamp)
echo "B gemma alone: $(echo "$t1 - $t0" | bc) s" | tee -a $OUT
t0=$(stamp); run bench_cc_C_llama 10 llama3.1:8b & run bench_cc_C_gemma 10 gemma4:e2b & wait; t1=$(stamp)
echo "C llama+gemma together: $(echo "$t1 - $t0" | bc) s" | tee -a $OUT
t0=$(stamp); run bench_cc_D_llama10 10 llama3.1:8b & run bench_cc_D_llama11 11 llama3.1:8b & wait; t1=$(stamp)
echo "D two llama jobs together: $(echo "$t1 - $t0" | bc) s" | tee -a $OUT
for L in bench_cc_A_llama bench_cc_B_gemma bench_cc_C_llama bench_cc_C_gemma bench_cc_D_llama10 bench_cc_D_llama11; do
  $P -c "import json;j=json.load(open('data/llm_bias/worlds/$L/manifest.json'));print('$L',{m:(v['decisions'],v['wall_s'],v['s_per_decision']) for m,v in j['judges'].items()})" | tee -a $OUT
done
echo "$(date '+%F %T') bench end" | tee -a $OUT
