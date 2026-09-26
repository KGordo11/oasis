#!/bin/bash
# After each A/B post set: health check, A/B analysis, both exports, exploration of the scroll design, page build.
# Usage: ab_refresh.sh <page_out_dir>    (then publish <dir>/scroll_test.html + world_data.js)
cd "$(dirname "$0")/../../.."
P="taskpolicy -b ./oasis-env/bin/python"; S=examples/experiment/llm_bias; D=${1:?page dir}
$P $S/check_world.py --prefix ab_ | grep -v '^PASS' ; echo "checks done"
$P $S/analyze_ab.py --out data/llm_bias/analysis_ab.json > /dev/null
$P $S/export_world.py --prefix ab_ --out data/llm_bias/export_ab | tail -1
$P $S/make_world_artifact.py --out "$D/scroll_test.html" | tail -1
./oasis-env/bin/python -c "
import json; d=json.load(open('data/llm_bias/analysis_ab.json')); print('sets', d['post_sets'], d['reactions'])
for k,v in d['effects_points'].items(): print(f'{k:22s} {v[\"est\"]:+6.2f}  [{v[\"ci95\"][0]:+.1f}, {v[\"ci95\"][1]:+.1f}]  p={v[\"p\"]}')
print('fav', d['pair']['favourite_share_%'], 'pos1', d['pair']['position_1_picked_%'])"
