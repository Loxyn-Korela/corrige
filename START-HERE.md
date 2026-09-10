# Start here

A ground truth for graph repair, a judge, and an injector. Built on EUR-Lex/Cellar and on ICIJ
Offshore Leaks, and used to measure pgrepair. Apache 2.0 for the tools, CC BY-SA 4.0 for the
records. Loxyn SAS, Lyon.

## One second, no database, no network

```
git clone https://github.com/Loxyn-Korela/corrige && cd corrige && ./demo.sh
```

Calibration, a sealed injection, two witnesses, the judge, and the tie-break. Everything it prints
replays identically except one line, and that line is the finding.

## Then read, in this order

1. **`README.md`, the section "A second graph, not legislative, with constraints we did not
   write"** — the shortest complete example of what the instrument does.
2. **`ANOMALY-label-repair.md`** — one page. If you wrote pgrepair, read this one first instead.
3. **`README.md` from the top** if you want the four measurements in full.

## The three things we measured

**Where a law separates two edges, pgrepair finds the right one every time.** Eight runs out of
eight on our informed arm.

**Where nothing separates them, the answer is not repeatable.** The same ILP kept 58, 59, 65 and 69
true edges of 130 on four identical runs. A coin gives 65. The cause is one line and so is the fix,
both in `runs/icij/tie_break.py`.

**A graph built from documents has a ceiling.** About one repeal in four that the EUR-Lex register
asserts cannot be found by reading the act that performs it. That is a property of legal drafting,
not an error, and a bench that ignores it marks an honest extractor as a failing one.

## The rule that came out of it

**R10: one run of a repairer establishes nothing.** `python3 -m corrige.spread <truth> <journal>
<candidates…>` judges several runs of one design and labels each arm *stable*, *moves*, or *not
repeated*. We turned it on our own published numbers the day we wrote it, and it killed one of them.

## Where the data is

The frozen EUR-Lex truth, 489,223 facts with its audit: `doi:10.5281/zenodo.22688808`, canonical
sha256 `4796f91da81289a0…`. The ICIJ truth is not published because it needs no publishing: it
rebuilds exactly from the dump ICIJ serves, in one command, and the README says which.

## What we do not measure, said plainly

`based_on` is not measured against the texts, we hold 15 % of its subject acts. The human audit
rests on one reader so far. gamma_4 of the ICIJ workload is out of coverage, our law module cannot
express a variable-length pattern. And the truth is the register of 9 September 2026, not the law.
