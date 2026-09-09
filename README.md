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

## First measure (2026-09-09, full truth, two witnesses, no candidate yet)

Injected with a sealed seed: 10 % spurious `repeals` and `amends` edges, half of them visible by
a law; 5 % `repeals` removed; 2 % of dated nodes shifted by a year. Then the two witnesses judged
(`runs/first/verdict-*.json`):

| | dumb baseline | rule without model | **pgrepair** (SciPyWeightedILP, laws L1-L3 as constraints, `--mark`) |
|---|---|---|---|
| spurious edges visible by a law (3,934) | caught 0 | caught **3,934** | caught **3,934** |
| spurious edges invisible to the laws (3,936) | caught 0 | caught **0** | caught **0** |
| removed true edges (719) | beyond reach | beyond reach | beyond reach |
| shifted dates (5,276) | beyond reach | beyond reach | beyond reach |
| true facts wrongly broken | 0 | **286** (dated noise made them look illegal) | **286** |
| true facts that really violate a law, removed | 0 | 238 of 239 (one was shifted out of violation) | 238 |
| edges deleted in all | 0 | 4,458 | 4,458 (solver weight 8,916, under a second) |

pgrepair, run on this truth through Neo4j 5.26 with the three laws written as its constraints
(`workloads/eurlex-laws.toml`, `pg-repair-run --commit repair --mark`), gives the same verdict as
the rule without model, edge for edge: on these constraints the ILP has nothing to arbitrate,
every violation is a single edge and deleting it is the only minimal repair. Its value would show
on constraints where violations overlap; the instrument is what makes that statement checkable.

This is the ceiling of a deletion-only, constraint-based repair on this truth, before pgrepair
runs: it sees exactly what the laws see and nothing else, and dated noise turns it against the
truth. The census control (`known_violations_removed` = census) holds exactly only when no
ANACHRONISM is injected (T10); with dated noise the small difference is explained, not hidden.
