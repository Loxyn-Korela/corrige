# Le Corrigé — truth and judge for graphs built from documents (layer 1)

An open measuring instrument. A **truth** is a frozen, self-contained JSON file of facts from a
declared angle (here: the official EUR-Lex/Cellar register, three relations, frozen 2026-09-09; and the
published ICIJ Offshore Leaks dump, three relations, frozen 2026-09-10),
with its coverage, its known faults, its reserves and its audit. A **candidate** is any program
that produces or repairs a graph; it is judged against the truth, per relation, per dimension,
and its verdict is published beside two **witnesses** (a dumb baseline, a rule without model).
The design, its nine judge rules and its eleven planted-fault tests are in the companion document
(`COUCHE 1 — socle de vérité et juge`, version 4, validated 2026-09-09).

```
python3 -m corrige.truth_eurlex <collection dir> truths/truth-eurlex-relations-2026-09-09.json --toy 200 --seed 7
python3 tests/test_layer1.py                       # 24 assertions: T0-T12 + calibration, on toy-200
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

The ICIJ truth is not committed either (42 MB) and needs no publishing: it is truth *by
construction* and rebuilds exactly from the public dump in one command, after loading it and
running the setup queries of pgrepair's own `icij-qualitative-study.toml`:

```
python3 -m corrige.truth_icij truths/truth-icij-offshoreleaks-2026-09-10.json
```

A rebuild that does not print sha256 `b14fa984ba4286ee…` is not the same graph, and the judge will
refuse any candidate that names a different one.

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

## The seven damages, and the half of pgrepair nobody had exercised (2026-09-10)

The injector produced only four of the seven damages the Fault Atlas classifies. It now produces
all seven, on the same frozen truth: spurious edge, missing, anachronism, **wrong value** (the
CELEX itself), **wrong label**, **merge** (two acts become one node) and **split** (one act becomes
two). The wrong label rests on a real law of the domain, L6: *an act's type label says what its
CELEX says* — `32019R1020` is a Regulation, `32019L1020` a Directive — and it is the only damage a
**label repair** can undo, which is the half of pgrepair no measurement had touched.

One run, 5 % spurious repeals (half visible to a law), 3 % repeals removed, 2 % wrong labels, 1 %
wrong CELEX values, 506 merges, 271 splits (`runs/seven/`):

| damage | dumb baseline | rule without model | pgrepair |
|---|---|---|---|
| spurious edge, visible to an edge law | 0 / 360 | 360 / 360 | 360 / 360 |
| spurious edge, invisible to every law | 0 / 361 | 0 / 361 | 0 / 361 |
| **wrong label, visible to the label law** | 5 / 3,932 | 5 / 3,932 | **3,932 / 3,932** |
| split: reachable by deleting the twin | 0 / 271 | 0 / 271 | 0 / 271 |
| missing, anachronism, wrong value, merge | 0 / 3,549 | 0 / 3,549 | 0 / 3,549 |
| true facts wrongly broken | 0 | 0 | 0 |

Two findings worth stating. **A label repair satisfies every constraint of its workload by deleting
labels** — run with our edge laws in the same file, it removed the `:Act` label of an endpoint to
make a date violation disappear, 521 times. The two kinds of law must be run as two workloads, and
they now are (`eurlex-laws.toml`, `eurlex-labels.toml`). **A marked node is not a deleted node**:
`--mark` writes `_PGREPAIR_DELETED__<Label>` for a label and the bare `_PGREPAIR_DELETED` for a
node; reading the first as the second turned 3,930 label repairs into 3,930 phantom node deletions
and 11,888 phantom lost facts in our first attempt.

Neither witness can touch the label damage — a rule that deletes edges has nothing to say about a
label — so on this damage pgrepair stands alone, exactly and completely.

## Does an optimising repairer buy anything? Two arms, one of which can fail (2026-09-10)

The first cycle experiment was a straw man: 283 of its 288 injected edges also violated the
one-edge date law, so the right edge could be chosen without any solver. This one has two arms in
the same graph, the same sealed journal (`measures/optimising-repair-two-arms-2026-09-10.json`):

- **informed** — 150 cycles whose false edge *also* violates the date law; the choice exists
  without the two-edge law;
- **blind** — 130 cycles whose false edge violates *nothing but* the two-edge law; the two edges
  are indistinguishable, and there is no information to choose between them. Only 159 pairs in the
  whole truth allow this, which is why the arm is small.

Each arm was run four times per algorithm, because a single run turned out to establish nothing
(see R10 below and `measures/eurlex-arms-spread-2026-09-10.json`):

| true edges kept | informed (150) | blind (130) |
|---|---|---|
| rule without model | **0** | 0 |
| pgrepair, SciPyWeightedILP, 4 runs | **150, 150, 150, 150** | 58, 59, 65, 69 |
| pgrepair, Greedy, 4 runs | **150, 150, 150, 150** | 64, 66, 66, 70 |

Read the two columns against each other, because that contrast is the whole result. **The informed
arm is identical on all eight runs.** Where the date law separates the two edges, both algorithms
find the same answer every time, and it is the right one. **The blind arm never repeats.** The same
ILP gives 59 on one run and 69 on the next; a fair coin on 130 pairs gives 65 with a 95 % band of 54
to 76, and all eight figures sit inside it. The spread *within* one algorithm is wider than any gap
*between* the two.

Three readings, and the second and third are not what we claimed before.

**Against a plain rule the gain is real and large.** A rule that deletes every edge of every
violation destroys all 150 true edges; both pgrepair algorithms keep all 150. That is what
choosing buys over deleting, and it is worth stating on its own.

**Between the ILP and the greedy nothing can be measured from single runs, and we withdraw our
earlier "no difference".** They are identical on the informed arm, eight runs out of eight. On the
blind arm neither is measured at all: repeating the arm moves the figure by more than the choice of
algorithm does. The ILP may still earn its keep on constraint sets where violations overlap more
richly than ours do, and our bench cannot yet produce those.

**On the blind arm both are at chance, as they must be**: 44.6 % and 50.8 %, with a 95 % interval
of ±8.6 points on 130 cycles. When two edges carry the same violation and nothing else separates
them, no repairer can do better than a coin. The instrument's job is to say so rather than to hide
it behind an average.

**Why the draw is not repeatable.** The tie between two edges of equal weight is broken by the
iteration order of a Python `set` of `(element_id, EntityType)` pairs, and `element_id` is a string,
so the order changes from one process to the next. `runs/icij/tie_break.py` reproduces it in four
lines: twenty processes, two different answers. A second key in `min()` that does not depend on the
process — `(weights[v], v[0], v[1].value)`, since `EntityType` is a plain `Enum` and is not orderable
on its own — makes the greedy reproducible without changing what it computes.

**R10, a tenth judge rule, comes out of this.** One run of a repairer establishes nothing.
`python3 -m corrige.spread <truth> <journal> <candidates…>` judges several runs of one design and
prints each arm's figure beside the coin's, labelled *stable*, *MOVES*, or *NOT REPEATED*. An arm
that is stable is one where information existed and the repairer used it. An arm that moves is a
tie-break, and a single run published as a score reads as skill. The rule costs one flag and it is
what turned our own "no difference" from a claim into a question.

## A second graph, not legislative, with constraints we did not write (2026-09-10)

Everything above is EUR-Lex. One corpus is a case study, not a bench. So the same instrument was
pointed at the **ICIJ Offshore Leaks** graph, loaded from the dump ICIJ publishes
(2,016,523 nodes, 3,339,267 edges), with the typed relations created by the setup queries of
pgrepair's *own* workload, and with three of its laws taken verbatim from
`workloads/icij-qualitative-study.toml` — gamma_1, gamma_2, gamma_3 — not written by us:

| | |
|---|---|
| I1, one edge | two nodes linked by `same_name_as` carry the same name |
| I2, one node | an entity whose inactivation date has passed is not `Active` |
| I3, two edges | an entity has at most one sole director |

The truth is by construction (`truths/truth-icij-offshoreleaks-2026-09-10.json`, sha256
`b14fa984ba4286ee…`): `same_name_as` 104,162 · `sole_director_of` 116 · `president_of` 36,537 over
161,119 nodes. It is not a claim about the world; it is what ICIJ published, frozen, and it says so.

**A cross-check we did not arrange.** Our census of I1 on the untouched dump finds **18,000**
violations. pgrepair, run on the same untouched dump with her own gamma_1, collects the same
18,000. Two independent implementations of one sentence, agreeing to the edge.

Injection (`runs/icij/journal.json`, sealed seed): 1,042 spurious `same_name_as` edges, half of
them visible by I1; 731 `president_of` edges removed; and 60 **rival** `sole_director_of` edges —
a second sole director for an entity that has one. The rival arm is *blind* by construction: the
false edge violates nothing but the two-edge law, so the two edges are indistinguishable and there
is no information with which to choose.

| | spurious visible by I1 (521) | spurious invisible (521) | rival pairs: true edge kept (60) | removed edges (731) |
|---|---|---|---|---|
| dumb baseline | 0 | 0 | 60 (deletes nothing) | beyond reach |
| rule without model | **521** | 0 | **0** | beyond reach |
| pgrepair, SciPyWeightedILP | **521** | 0 | 24, then 29 | beyond reach |
| pgrepair, Greedy | **521** | 0 | 25, 30, 31, 29 | beyond reach |

Every run of both algorithms catches all 521 one-edge violations and none of the 521 invisible ones.
Every run returns the same cost: solver weight 37,206, 18,603 deletions. The only thing that moves
between runs is which edge of a tied pair is dropped, and the six figures above sit inside the band
a coin would produce: 30 expected, 22 to 38 at 95 % on 60 pairs. *(Reserve: the arm script
overwrites its own candidate file, and runs 1 of each algorithm were judged before we knew that, so
25 and 24 are reported from the verdicts computed at the time and cannot be re-judged from disk.
Runs 2 to 4 can.)*

The three readings of EUR-Lex come back unchanged on a graph that shares nothing with it:

**On one-edge laws pgrepair and a rule without a model are the same object.** 521 of 521 caught,
0 of 521 invisible ones, on both, on either algorithm.

**The gain on the two-edge law is minimality, not discrimination.** The rule deletes every edge of
every violation and so destroys all 60 true edges; pgrepair deletes one edge per violation and
keeps 24. But *which* one it keeps is a coin: 40 % and 41.7 %, a 95 % interval of about
±12.5 points on 60 pairs. It is right that it cannot do better — nothing separates the two edges —
and the instrument's job is to say so instead of reporting the 24 as a success.

**The greedy's choice is not stable across identical runs, and we can say why.** The same
algorithm, on the same graph, with the same sealed journal, kept 25 true edges on one run and 30 on
the next. Nothing in the input changed. The mechanism is one line: the greedy picks the vertex to
delete with `min(hyperedge, key=…weights…)` over a Python `set` whose members are
`(element_id, EntityType)` pairs, and Neo4j's `element_id` is a string. When two vertices carry the
same weight — exactly the blind rival case, where nothing separates the true edge from the false
one — the set's iteration order decides, and Python randomises `hash(str)` per process.
`runs/icij/tie_break.py` reproduces it in four lines, outside pgrepair and outside Neo4j: twenty
processes, two different answers. We do not claim this is the only source of the variation between
two arms; a fresh dump load can also hand back different element ids. We claim the tie is broken by
something that carries no information about which edge is true. A second key in `min()` that does
not depend on the process — `(weights[v], v[0], v[1].value)`, since `EntityType` is a plain `Enum`
and is not orderable on its own — would make the greedy reproducible without changing what it
computes.

**The ILP and the greedy are again indistinguishable, and now we can say what that means.** Six
runs, four of the greedy and two of the ILP, span 24 to 31 true edges kept of 60. A coin gives 30.
Repeating the arm moves the figure by as much as the choice of algorithm does, so no comparison
between the two can be read off a single run.

The deletions reconcile exactly: 18,603 = 18,000 known I1 violations the source itself carries
+ 22 (one edge of each of the 22 known I3 pairs) + 521 injected visible edges + 60 rival edges.
The known faults of the source are counted apart (R9) and never scored as repairs.

Reserves: gamma_4 (a quantified path over 1.7 million `officer_of` edges) is out of coverage — our
law module cannot yet express a variable-length pattern. The blind arm injects rivals onto 60 of
the 72 `sole_director_of` edges the truth holds outside its known faults: the rate is high because
the relation is small, and what is measured is the arbitration, not the rate.

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

**R10 applied to this measurement, 2026-09-10: it repeats exactly.** Three runs of the ILP on the
same graph produced a candidate graph identical to the byte — same 491,916 facts, same sha256
`6d93013739bbf435…`, no node deleted on any run. This is the one place where we can say pgrepair is
reproducible, and it is worth saying: every conflict here has a forced minimum, so there is no tie
to break and nothing for the process hash seed to decide. It also refutes a guess we made before
measuring. We had reasoned that a one-edge law leaves nothing to arbitrate, and that was the wrong
reason to be confident: the conflict collector puts the edge *and both its endpoint nodes* in the
same hyperedge, and a node of degree 1 weighs the same as an edge, so a tie is available even here.
It simply did not occur on this graph. R10 exists because that difference — between a proof and a
guess that happened to hold — is not visible without repeating.

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
