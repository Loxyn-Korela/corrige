#!/bin/bash
# One clean arm: reload the published dump, run her setup, apply our journal, repair, read back.
set -e
ALGO=$1
docker stop neo4j-pgrepair >/dev/null
docker run --rm -v ~/dev/neo4j-pgrepair/data:/data -v ~/dev/neo4j-pgrepair/dumps:/dumps neo4j:5.26-community \
  neo4j-admin database load neo4j --from-path=/dumps --overwrite-destination=true >/dev/null 2>&1
docker start neo4j-pgrepair >/dev/null; sleep 25
cd "$HOME/Mes claudes/Banc à vérité connue/pgrepair-bonifati/pgrepair"
. .venv/bin/activate
pg-repair-run -u neo4j --db-password "$NEO4J_LOCAL_PASSWORD" setup --commit workloads/icij-qualitative-study.toml >/dev/null 2>&1
cd "$HOME/dev/corrige"
python3 -m corrige.neo4j_icij apply runs/icij/graph.json runs/icij/journal.json
cd "$HOME/Mes claudes/Banc à vérité connue/pgrepair-bonifati/pgrepair"
pg-repair-run -u neo4j --db-password "$NEO4J_LOCAL_PASSWORD" --disable-cache --commit repair --mark -a "$ALGO" \
  "$HOME/dev/corrige/workloads/icij-g1-g3.toml" > "$HOME/dev/corrige/runs/icij/pgrepair-$ALGO.log" 2>&1
grep -o "deleting [0-9]* edge(s), [0-9]* node(s)" "$HOME/dev/corrige/runs/icij/pgrepair-$ALGO.log" | tail -1
cd "$HOME/dev/corrige"
python3 -m corrige.neo4j_icij read runs/icij/graph.json "runs/icij/candidate-$ALGO.json" --name "pgrepair-$ALGO"
