#!/bin/bash
# Apply R10 to a measurement that was only ever run once.
#   NEO4J_LOCAL_PASSWORD=… bash runs/repeat_run.sh <run-dir> <workload.toml> <algo> <n>
set -e
DIR=$1; WL=$2; ALGO=${3:-SciPyWeightedILP}; N=${4:-2}
C="$HOME/dev/corrige"; P="$HOME/Mes claudes/Banc à vérité connue/pgrepair-bonifati/pgrepair"
for r in $(seq 1 "$N"); do
  cd "$C"; python3 -m corrige.neo4j_graph load "runs/$DIR/graph.json"
  cd "$P"; . .venv/bin/activate
  pg-repair-run -u neo4j --db-password "$NEO4J_LOCAL_PASSWORD" --disable-cache --commit repair --mark \
    -a "$ALGO" "$C/$WL" > "$C/runs/$DIR/pgrepair-$ALGO-r$r.log" 2>&1
  grep -o "deleting [0-9]* edge(s), [0-9]* node(s), [0-9]* labels" "$C/runs/$DIR/pgrepair-$ALGO-r$r.log" | tail -1
  cd "$C"; python3 -m corrige.neo4j_graph read "runs/$DIR/graph.json" "runs/$DIR/candidate-$ALGO-r$r.json" --name "pgrepair-$ALGO"
  echo "== $DIR $ALGO run $r done"
done
