#!/bin/bash
# R10 applied to the seven damages: measure, per damage class, what a repair can reach — three
# runs, so no figure is a single draw. This replaces the Fault Atlas lookup table
# (repair.reachable_by_deletion, written from the damage class in the migration of 2026-09-09)
# with a measurement carrying the journal's sha256 as its provenance.
set -e
C="$HOME/dev/corrige"
P="$HOME/Mes claudes/Banc à vérité connue/pgrepair-bonifati/pgrepair"
cd "$C"
mkdir -p runs/night
[ -f runs/night/seed.txt ] || echo "nuit-2026-09-10" > runs/night/seed.txt
echo "== injection, all seven damages, sealed seed"
python3 -m corrige.inject truths/truth-eurlex-relations-2026-09-09.json runs/night \
  --damage repeals:SPURIOUS_EDGE=0.05 --damage repeals:MISSING=0.03 \
  --damage nodes:ANACHRONISM=0.02 --damage nodes:WRONG_VALUE=0.01 \
  --damage nodes:WRONG_LABEL=0.02 --damage nodes:MERGE=0.02 --damage nodes:SPLIT=0.01 \
  --visible 1/2 --seed-file runs/night/seed.txt
for r in 1 2 3; do
  cd "$C"
  python3 -m corrige.neo4j_graph load runs/night/graph.json
  cd "$P"
  . .venv/bin/activate
  for wl in workloads/eurlex-labels.toml workloads/eurlex-laws.toml; do
    tag=$(basename "$wl" .toml)
    pg-repair-run -u neo4j --db-password "$NEO4J_LOCAL_PASSWORD" --disable-cache --commit repair --mark \
      -a SciPyWeightedILP "$C/$wl" > "$C/runs/night/pgrepair-$tag-r$r.log" 2>&1
    sed 's/\x1b\[[0-9;]*m//g' "$C/runs/night/pgrepair-$tag-r$r.log" | grep -o "Repairing by deleting.*" | tail -1
  done
  cd "$C"
  python3 -m corrige.neo4j_graph read runs/night/graph.json "runs/night/candidate-r$r.json" --name pgrepair
  echo "== run $r done"
done
cd "$C"
echo "== judging"
python3 runs/judge_night.py
echo "== done"
