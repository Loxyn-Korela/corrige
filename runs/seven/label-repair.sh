#!/bin/bash
# The seven-damages measurement, repeated WITH pgrepair's Step 2 (--label-repair) on the label law.
# Why: repeat.sh and twice.sh ran the label workload without the flag, so pgrepair could only delete
# nodes (its §4.3: "deletes nodes only if errors contain isolated nodes"; Step 2 exists "to include
# the removal of labels", enabled by --label-repair). The 3,930 nodes / 11,200 facts figure is that
# configuration. This run measures the intended one. The label pass commits for real (no --mark):
# in --mark mode a label deletion is written as _PGREPAIR_DELETED__<Label>, which the reader does not
# interpret (label-repair-retracted-2026-09-13.json, second finding). The edge pass keeps --mark as before.
set -e
N=${1:-3}
C="$HOME/dev/corrige"; P="$HOME/Mes claudes/Banc à vérité connue/pgrepair-bonifati/pgrepair"
# The password is never written here: export NEO4J_LOCAL_PASSWORD, or put it alone in
# ~/dev/corrige/.neo4j-password (git-ignored). Nothing prints it.
[ -n "$NEO4J_LOCAL_PASSWORD" ] || [ -f "$C/.neo4j-password" ] && NEO4J_LOCAL_PASSWORD=${NEO4J_LOCAL_PASSWORD:-$(tr -d '\n' < "$C/.neo4j-password")}
[ -n "$NEO4J_LOCAL_PASSWORD" ] || { echo "no password: export NEO4J_LOCAL_PASSWORD or create $C/.neo4j-password"; exit 2; }
export NEO4J_LOCAL_PASSWORD
for r in $(seq 1 "$N"); do
  cd "$C"; python3 -m corrige.neo4j_graph load runs/seven/graph.json --password "$NEO4J_LOCAL_PASSWORD"
  cd "$P"; . .venv/bin/activate
  pg-repair-run -u neo4j --db-password "$NEO4J_LOCAL_PASSWORD" --disable-cache --commit repair --label-repair \
    -a SciPyWeightedILP "$C/workloads/eurlex-labels.toml" > "$C/runs/seven/pgrepair-eurlex-labels-labelrepair-r$r.log" 2>&1
  sed 's/\x1b\[[0-9;]*m//g' "$C/runs/seven/pgrepair-eurlex-labels-labelrepair-r$r.log" | grep -o "found a solution with weight.*\|Repairing by deleting.*" | tail -2
  pg-repair-run -u neo4j --db-password "$NEO4J_LOCAL_PASSWORD" --disable-cache --commit repair --mark \
    -a SciPyWeightedILP "$C/workloads/eurlex-laws.toml" > "$C/runs/seven/pgrepair-eurlex-laws-labelrepair-r$r.log" 2>&1
  sed 's/\x1b\[[0-9;]*m//g' "$C/runs/seven/pgrepair-eurlex-laws-labelrepair-r$r.log" | grep -o "Repairing by deleting.*" | tail -1
  cd "$C"; python3 -m corrige.neo4j_graph read runs/seven/graph.json "runs/seven/candidate-labelrepair-r$r.json" --name pgrepair --password "$NEO4J_LOCAL_PASSWORD"
  echo "== label-repair run $r done"
done
cd "$C"; echo "== judging"; python3 runs/seven/judge_label_repair.py; echo "== done"
