#!/bin/bash
# The instrument, end to end, on a laptop, with no database and no network.
# Four steps, about ten seconds. Everything here uses the 200-fact toy truth that ships with the
# repository; the published measurements use the full 489,223-fact truth from Zenodo.
set -e
cd "$(dirname "$0")"
P() { printf '\n\033[1m── %s\033[0m\n' "$1"; }

P "1. The instrument is calibrated before it measures anything"
python3 tests/test_layer1.py | tail -3

P "2. Damage the graph, and seal what was damaged (the seed is in demo-seed.txt: this replays)"
rm -rf /tmp/corrige-demo && mkdir -p /tmp/corrige-demo
python3 -m corrige.inject truths/truth-eurlex-relations-2026-09-09-toy-200.json /tmp/corrige-demo \
  --damage repeals:SPURIOUS_EDGE=0.40 --damage amends:SPURIOUS_EDGE=0.30 \
  --damage repeals:MISSING=0.10 --visible 1/2 --seed-file demo-seed.txt

P "3. Two witnesses repair it, and the judge scores them against the truth"
python3 - <<'PY'
import json, sys
sys.path.insert(0, ".")
from corrige import judge as J, witnesses as W
t = json.load(open("truths/truth-eurlex-relations-2026-09-09-toy-200.json"))
g = json.load(open("/tmp/corrige-demo/graph.json"))
j = json.load(open("/tmp/corrige-demo/journal.json"))
for name, c in (("dumb baseline", W.dumb_baseline(g)), ("rule without model", W.rule_without_model(g))):
    r = J.judge(t, c, j)["repair"]
    v, i, b = r.get("visible", {}), r.get("invisible", {}), r.get("beyond_reach", {})
    print(f"  {name:20} visible {v.get('caught',0)} caught / {v.get('missed',0)} missed"
          f" · invisible {i.get('caught',0)}/{i.get('caught',0)+i.get('missed',0)}"
          f" · beyond a deletion {b.get('missed',0)} · true facts wrongly broken {r['wrongly_broken']}")
print("\n  A constraint sees exactly what it is written to see, and nothing else.")
print("  What an injection removed cannot be recovered by deleting. The judge says so")
print("  instead of counting it against the repairer.")
PY

P "4. And when nothing separates two edges, the choice is not a choice"
python3 runs/icij/tie_break.py

printf '\n\033[1mThe published measurements, already computed, are in measures/.\033[0m\n'
ls measures/*.json | sed 's/^/  /'
