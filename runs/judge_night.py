#!/usr/bin/env python3
"""Judge the overnight run: the two witnesses and the three pgrepair repeats, one bucket per damage."""
import json, sys, glob, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from corrige import judge as J, witnesses as W, canon

t = json.load(open(ROOT / 'truths/truth-eurlex-relations-2026-09-09.json'))
g = json.load(open(ROOT / 'runs/night/graph.json'))
j = json.load(open(ROOT / 'runs/night/journal.json'))


def show(name, v):
    print(name, json.dumps({k: x for k, x in v['repair'].items() if k != 'known_violations_removed'}, sort_keys=True))


for name, c in (("dumb-baseline", W.dumb_baseline(g)), ("rule-without-model", W.rule_without_model(g))):
    v = J.judge(t, c, j)
    canon.write(str(ROOT / f'runs/night/verdict-{name}.json'), v)
    show(name, v)
for f in sorted(glob.glob(str(ROOT / 'runs/night/candidate-r*.json'))):
    n = re.sub(r'.*candidate-|\.json', '', f)
    v = J.judge(t, json.load(open(f)), j)
    canon.write(str(ROOT / f'runs/night/verdict-{n}.json'), v)
    show(n, v)
