# Le Corrigé — truth and judge for graphs built from documents (layer 1)

An open measuring instrument. A **truth** is a frozen, self-contained JSON file of facts from a
declared angle (here: the official EUR-Lex/Cellar register, three relations, frozen 2026-09-09),
with its coverage, its known faults, its reserves and its audit. A **candidate** is any program
that produces or repairs a graph; it is judged against the truth, per relation, per dimension,
and its verdict is published beside two **witnesses** (a dumb baseline, a rule without model).
The design, its nine judge rules and its eleven planted-fault tests are in the companion document
(`COUCHE 1 — socle de vérité et juge`, version 4, validated 2026-09-09).

```
python3 -m corrige.truth_eurlex <collection dir> truths/truth-eurlex-relations-2026-09-09.json --toy 200 --seed 7
python3 tests/test_layer1.py                       # 22 assertions: T0-T11 + calibration, on toy-200
python3 -m corrige.inject <truth> <out-dir> --damage repeals:SPURIOUS_EDGE=0.10 --visible 1/2 --seed-file seed.txt
python3 -m corrige.judge <truth> <candidate> <verdict> [--journal <journal>]
```

Rules that do not bend: the file is the truth, a database is a view; no floats in a record
(RFC 8785 canonical JSON, sha256 inside); counts per relation, never pooled; a zero denominator
is `undefined`; known registry faults leave the denominators; a candidate must name the truth
and the journal it ran on; constraints come from the world laws, never from the injection journal.

The full truth (489,223 facts, 202 MB) is not committed: it is rebuilt from the frozen collection
and its sha256 is published here: `4796f91da81289a0…`. The toy truth (200 facts) is committed.

Licence: Apache 2.0 for the tools, CC BY-SA 4.0 for the truth records. Loxyn SAS, Lyon.
