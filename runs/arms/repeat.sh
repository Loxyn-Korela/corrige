#!/bin/bash
# Repeat the EUR-Lex two-arm cycle experiment N times per algorithm, to measure the spread of a
# choice we now know is not repeatable (see runs/icij/tie_break.py). One clean run per arm:
# reload the injected graph into Neo4j, repair, read the candidate back.
#   NEO4J_LOCAL_PASSWORD=… bash runs/arms/repeat.sh 3
set -e
N=${1:-3}
C="$HOME/dev/corrige"
P="$HOME/Mes claudes/Banc à vérité connue/pgrepair-bonifati/pgrepair"
for run in $(seq 1 "$N"); do
  for ALGO in SciPyWeightedILP Greedy; do
    cd "$C"
    python3 -m corrige.neo4j_graph load runs/arms/graph.json
    cd "$P"; . .venv/bin/activate
    pg-repair-run -u neo4j --db-password "$NEO4J_LOCAL_PASSWORD" --disable-cache --commit repair --mark \
      -a "$ALGO" "$C/workloads/eurlex-laws.toml" > "$C/runs/arms/pgrepair-$ALGO-r$run.log" 2>&1
    grep -o "deleting [0-9]* edge(s), [0-9]* node(s)" "$C/runs/arms/pgrepair-$ALGO-r$run.log" | tail -1
    cd "$C"
    python3 -m corrige.neo4j_graph read runs/arms/graph.json "runs/arms/candidate-$ALGO-r$run.json" --name "pgrepair-$ALGO"
    echo "== $ALGO run $run done"
  done
done
