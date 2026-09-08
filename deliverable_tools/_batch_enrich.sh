#!/bin/bash
cd '${SAPOTE_WORKSPACE_ROOT:-$PWD}'
for j in "sapote_deliverables/roster_v2/"*_roster_v2.json; do
  s=$(basename "$j" _roster_v2.json)
  ./Tools/bin/python3 "sapote_deliverables/tools/enrich_clusterblast.py" --strain "$s"
done
echo "BATCH_ENRICH_DONE"
