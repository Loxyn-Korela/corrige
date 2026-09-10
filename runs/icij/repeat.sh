#!/bin/bash
# Repeat an arm to test whether the repairer's choice is stable across identical runs.
set -e
for spec in "Greedy run3" "SciPyWeightedILP run2" "Greedy run4"; do
  set -- $spec
  bash "$HOME/dev/corrige/runs/icij/arm.sh" "$1"
  cp "$HOME/dev/corrige/runs/icij/candidate-$1.json" "$HOME/dev/corrige/runs/icij/candidate-$1-$2.json"
  echo "== $1 $2 done"
done
