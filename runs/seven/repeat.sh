#!/bin/bash
# The seven-damages measurement needs BOTH workloads in sequence on one database:
# the edge laws, then the label law. Repeating only one half is not repeating the measurement.
set -e
N=${1:-2}
ORDER=${2:-"workloads/eurlex-labels.toml workloads/eurlex-laws.toml"}   # the original order: labels first
SUF=${3:-orig}
C="$HOME/dev/corrige"; P="$HOME/Mes claudes/Banc à vérité connue/pgrepair-bonifati/pgrepair"
for r in $(seq 1 "$N"); do
  cd "$C"; python3 -m corrige.neo4j_graph load runs/seven/graph.json
  cd "$P"; . .venv/bin/activate
  for wl in $ORDER; do
    tag=$(basename "$wl" .toml)
    pg-repair-run -u neo4j --db-password "$NEO4J_LOCAL_PASSWORD" --disable-cache --commit repair --mark \
      -a SciPyWeightedILP "$C/$wl" > "$C/runs/seven/pgrepair-$tag-$SUF-r$r.log" 2>&1
    grep -o "deleting [0-9]* edge(s), [0-9]* node(s), [0-9]* labels" "$C/runs/seven/pgrepair-$tag-$SUF-r$r.log" | tail -1
  done
  cd "$C"; python3 -m corrige.neo4j_graph read runs/seven/graph.json "runs/seven/candidate-$SUF-r$r.json" --name pgrepair
  echo "== seven run $r done"
done
