#!/bin/bash
# After each v3 post set: health check, analysis, export, page build (then publish the files in publish_files.json).
cd "$(dirname "$0")/../../.."
S=examples/experiment/llm_bias; D=${1:?page dir}
taskpolicy -b ./oasis-env/bin/python $S/check_world.py --prefix v3_ | grep -v '^PASS'; echo "checks done"
taskpolicy -b ./oasis-env/bin/python $S/analyze_world.py --prefix v3_ --out data/llm_bias/analysis_v3.json > data/llm_bias/analysis_v3.txt 2>/dev/null
taskpolicy -b ./oasis-env/bin/python $S/export_world.py --prefix v3_ --out data/llm_bias/export_v3 | tail -1
taskpolicy -b ./oasis-env/bin/python $S/make_world_artifact.py --out "$D/scroll_test.html" | tail -1
sed -n '1,3p;/SELF-PREF/,/p =/p' data/llm_bias/analysis_v3.txt
