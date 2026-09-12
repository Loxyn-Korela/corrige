#!/bin/bash
# Does an upstream weight do on pgrepair what runs/weights/rival_weights.py shows on the mechanism?
# Same graph, same workload, same 130 blind rivals as runs/arms — the only change is a `conf`
# property carrying an upstream signal of a stated accuracy, read with pgrepair's own
# --custom-weight option.
#
#   NEO4J_LOCAL_PASSWORD=… bash runs/weights/arm.sh 3 0.7
#
# Runs N times per algorithm so R10 applies: one run of a repairer establishes nothing.
set -e
N=${1:-3}
ACC=${2:-1.0}
C="$HOME/dev/corrige"
P="$HOME/Mes claudes/Banc à vérité connue/pgrepair-bonifati/pgrepair"
mkdir -p "$C/runs/weights/out"
for run in $(seq 1 "$N"); do
  for ALGO in SciPyWeightedILP Greedy; do
    cd "$C"
    python3 -m corrige.neo4j_graph load runs/arms/graph.json
    python3 runs/weights/mark.py runs/arms/journal.json --accuracy "$ACC"
    cd "$P"; . .venv/bin/activate
    pg-repair-run -u neo4j --db-password "$NEO4J_LOCAL_PASSWORD" --disable-cache --commit repair --mark \
      --custom-weight conf -a "$ALGO" "$C/workloads/eurlex-laws.toml" \
      > "$C/runs/weights/out/pgrepair-$ALGO-p$ACC-r$run.log" 2>&1
    grep -o "deleting [0-9]* edge(s), [0-9]* node(s)" "$C/runs/weights/out/pgrepair-$ALGO-p$ACC-r$run.log" | tail -1
    cd "$C"
    python3 -m corrige.neo4j_graph read runs/arms/graph.json \
      "runs/weights/out/candidate-$ALGO-p$ACC-r$run.json" --name "pgrepair-$ALGO"
    echo "== $ALGO run $run (accuracy $ACC) done"
  done
done
echo "now judge the spread:"
echo "  python3 -m corrige.spread truths/truth-eurlex-relations-2026-09-09.json runs/arms/journal.json runs/weights/out/candidate-*.json"
