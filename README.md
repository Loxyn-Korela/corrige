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

The full truth (489,223 facts, 202 MB) is not committed to git: it is **published on Zenodo**,
`doi:10.5281/zenodo.22688808`, with the overlay and the checksums. Download it into `truths/` and
every command below runs on the real thing; its canonical sha256 is `4796f91da81289a0…`. The toy truth (200 facts) is committed.

Licence: Apache 2.0 for the tools, CC BY-SA 4.0 for the truth records. Loxyn SAS, Lyon.

## What each truth declares

A truth is not "the truth": it is a frozen, named body of facts, with two numbers it must state
about itself. Both are measured by human reading, never assumed.

| truth | facts | audited | the register is wrong | **reachable from the documents** | why the rest is not |
|---|---|---|---|---|---|
| EUR-Lex relations, frozen 2026-09-09 | 489,223 | 87 facts, one auditor, 2026-09-10 | 2.3 % | **89.7 %** (±6 pts) | 5.7 % true in law and never stated in the text (expiry, competence, cascade, accomplishment); 2.3 % stated as another relation (derogation, succession) |
| PubMed / Europe PMC | — | — | — | — | no truth built yet: the Atlas observed forms of fault on these corpora, no body of facts was frozen, so there is no figure to give |

**Reachable from the documents** is the ceiling of any extractor that reads the sources: it cannot
find what the sources do not say. A benchmark that ignores this ceiling scores an honest engine as
a failing one. A repairer working on the graph is not concerned by it: it sees the edges.

Every truth built from now on carries the same two numbers in its `audit` block, or says it has
none. A truth with no audit stays `unaudited` and no measurement is published against it.

## Campaign: how much of the register is stated in its own documents (2026-09-10)

The human audit gave a figure on 87 facts. The same question, asked of every fact whose subject
act we hold locally, by plain string search and no model, gives it on 33,612
(`measures/stated-in-text-2026-09-10.json`). The machine only ever answers with a quoted span:
the target's number inside a sentence carrying the relation's verb, or just after it with no other
act number in between, or under a list whose lead-in carries the verb, or in the annex of acts the
relating article points to.

| | repeals | amends |
|---|---|---|
| facts in the truth | 14,411 | 64,290 |
| text of the subject act held locally | 13,614 (94 %) | 19,998 (31 %) |
| **the text states the relation** | **10,305 — 75.7 %** | **18,018 — 90.1 %** |
| the target is never named: the relation is implicit | 1,555 | 667 |
| named, but no sentence states the relation | 992 | 667 |
| no printed number to search (agreement, protocol) | 762 | 646 |

Calibrated against the facts read by hand, excluding those with no local text: on repeals it finds
19 of the 21 the human found and **never claimed one he had refused** (0 of 5); on amends, 13 of
14, with no precision measurement (his only two refusals on amends fall on acts we do not hold).

**One repeal in four that the register asserts is not stated in the act that performs it.** On
amendments the register is far closer to its documents, because an amending act says so in its
own title. `based_on` is not measured: we hold the text of 15 % of its subject acts.

### What the measure changes in the instrument

It is an overlay, never a modification: the truth stays frozen, its hash unchanged. Passed to the
judge with `--stated`, it adds, per relation, the recall computed on the facts the documents
actually state, and counts apart the ones a reader could not have found:

```
python3 -m corrige.judge <truth> <candidate> <verdict> --journal <journal> --stated measures/stated-in-text-2026-09-10.json
```

On the first run (pgrepair, repeals): recall 94.73 % over all facts, 94.57 % over the stated ones,
and 67 of its misses are facts no reader could have found. Without the overlay those 67 look like
failures of the engine; with it, they are a property of the register, stated as such.

## The truth, audited by hand (2026-09-10)

87 facts of the sealed sample were read against the acts' own texts by one human, no model, one
fact at a time (`audit/`). The sample is stratified — 70 repeals, 70 amends, 60 based_on — while
the truth is not (14,411 / 64,290 / 410,522). **A rate over all relations would be an artefact of
the stratification**, and rule R6 forbids it, so everything is per relation:

| of the facts read | repeals (27) | amends (33) | based_on (27) |
|---|---|---|---|
| the register is **wrong** | 2 | 0 | 0 |
| true in law, **not stated in the text** | 4 | 0 | 1 |
| the text states **another relation** | 0 | 2 | 0 |
| the register is right and the text says so | 21 | 31 | 26 |

Both registry errors fall on repeals: a wrong target (an act about staff in Belgium linked to one
about Italy) and a granularity error (one article repealed, the act recorded as repealed).

Reserves, in the truth's `audit` block: **one auditor, who also built the truth**; no agreement
between readers measured yet; both revisions made after review went from NO to YES, the direction
that raises the figure; 27 to 33 facts per relation is a wide interval — a first reading, not a
rate; two facts rest on titles alone, their texts served neither by EUR-Lex nor by Cellar.

Two answers were revised after review, both because the source hid the sentence: an adaptation
inside a table the page renders badly, and a 1990 amendment compared with the 1972 original text
(the amounts had changed in between). The booklet keeps what was ticked; `answers-notes.json`
records what was revised and why.

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

## Second measure (2026-09-10): a two-edge law, where a repairer has to choose

The census of candidate laws on the truth itself rejected every "natural" two-edge law (an act
amended after its repeal: 2,315 real cases; based on an act already repealed: 19,982; both with
end-of-validity dates: 1,443 and 13,720; repeals and amends the same act: 183 — legal practice,
not faults). One strict two-edge law survives: **L4, two acts do not repeal each other** (1 real
cycle in 489,223 facts). The injector can now fabricate cycles: a spurious `repeals` b→a mirroring
a true a→b; both edges violate L4, one is false, and a deletion-only repairer must choose.

Same damages as the first measure plus 2 % cycles (288), laws L1-L4 (`runs/cycles/`):

| | rule without model | **pgrepair** |
|---|---|---|
| cycles: true edge kept / broken (288) | 0 / 288 | **274** / 14 (12 of them removed by the MISSING injection, not by pgrepair) |
| spurious visible edges caught (4,222) | 4,222 | 4,220 |
| true facts wrongly broken, all causes | 602 | 328 |

Here pgrepair separates from the rule, and the reason is stated: 283 of the 288 cycle edges also
violate L1 (the mirrored edge has the wrong date order), so deleting the false edge resolves two
violations and the true edge only one; the minimum-deletion solver picks the false one. The rule
deletes both. This is what an optimising repairer buys when violations overlap, and the instrument
now says whether it chooses well.
