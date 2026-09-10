#!/bin/bash
# Hypothesis: the published label run (weight 3930) was made on a database already marked by an
# earlier label repair, not on a fresh load. Load once, run the SAME label workload twice in a row,
# and read the weight each time.
set -e
C="$HOME/dev/corrige"; P="$HOME/Mes claudes/Banc à vérité connue/pgrepair-bonifati/pgrepair"
cd "$C"; python3 -m corrige.neo4j_graph load runs/seven/graph.json
for pass in 1 2; do
  cd "$P"; . .venv/bin/activate
  pg-repair-run -u neo4j --db-password "$NEO4J_LOCAL_PASSWORD" --disable-cache --commit repair --mark \
    -a SciPyWeightedILP "$C/workloads/eurlex-labels.toml" > "$C/runs/seven/pgrepair-twice-p$pass.log" 2>&1
  sed 's/\x1b\[[0-9;]*m//g' "$C/runs/seven/pgrepair-twice-p$pass.log" | grep -o "found a solution with weight [0-9]*\|Repairing by deleting.*"
  echo "== pass $pass"
done
cd "$C"; python3 -m corrige.neo4j_graph read runs/seven/graph.json runs/seven/candidate-twice.json --name pgrepair
