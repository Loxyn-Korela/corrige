#!/usr/bin/env python3
"""Judge the --label-repair repeats on runs/seven against the frozen truth and the sealed journal."""
import json, sys, glob, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from corrige import judge as J, canon

t = json.load(open(ROOT / 'truths/truth-eurlex-relations-2026-09-09.json'))
j = json.load(open(ROOT / 'runs/seven/journal.json'))
for f in sorted(glob.glob(str(ROOT / 'runs/seven/candidate-labelrepair-r*.json'))):
    n = re.sub(r'.*candidate-|\.json', '', f)
    c = json.load(open(f))
    v = J.judge(t, c, j)
    canon.write(str(ROOT / f'runs/seven/verdict-{n}.json'), v)
    r = {k: x for k, x in v['repair'].items() if k != 'known_violations_removed'}
    print(n, json.dumps(r, sort_keys=True))
    nodes = c.get('nodes', c) if isinstance(c, dict) else c
    try:
        print(n, 'nodes in candidate:', len(nodes))
    except Exception:
        pass
