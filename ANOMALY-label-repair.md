# One anomaly we could not settle, and it should take you a minute

*For whoever wrote `pgrepair/cleaning/conflict_collectors.py`. Loxyn SAS, 10 September 2026.
Everything here is in this repository; nothing needs us.*

## What happened

We ran `pg-repair-run --commit repair --mark -a SciPyWeightedILP` with one label workload
(`workloads/eurlex-labels.toml`, eight constraints, L6: an act's type label matches its CELEX
letter) against an EUR-Lex graph of 264,937 nodes carrying 3,932 deliberately wrong type labels.

The same command, same workload, same graph, gave two different repairs on different days.

```
2026-09-10 13:16   found a solution with weight 3930
                   Repairing by deleting 0 edge(s),    0 node(s), 3930 labels

2026-09-10 17:48   found a solution with weight 34392
                   Repairing by deleting 0 edge(s), 3930 node(s),    0 labels
```

Both satisfy the law: all 3,932 wrong labels are gone either way. The second one takes the nodes
with them, and 11,200 true facts go too.

## Why we do not think this is a tie

A tie would give two solutions of equal cost. These differ by a factor of nine. We reproduced the
34,392 solution **five times** since, in both workload orders and on freshly loaded graphs, and
never got 3,930 again. The five agree with each other exactly. All six runs are on one graph and
one sealed injection journal, sha256 `ced2627844564cfb…`, 3,932 wrong labels; their logs are in
`runs/seven/` with the timestamps above, and the one that gave 3,930 is `pgrepair-label.log`. So this is not the `min()` tie-break
we document in `runs/icij/tie_break.py`.

## The arithmetic we cannot make work

In `conflict_collectors.py`, a labelset vertex is weighted by the size of the labelset:

```python
weights[(token, EntityType.LABELSET)] = len(token[1])
```

The published run deleted 3,930 labels for a total weight of 3,930. That is **weight 1 per label**,
so a labelset of size 1. Every node in our graph carries at least two labels: `:Act`, set when the
graph is loaded, plus its type label (`:Regulation`, `:Directive`, …). We do not know how to produce
a labelset of size 1 here, and therefore we do not know what that run saw.

## What we tested and ruled out

**That the published run was made on a database already marked by an earlier label repair.** It was
our best guess and it is wrong. Marking *adds* `_PGREPAIR_DELETED__<Label>` to the node, so the
labelset grows and its weight rises. Two passes on one fresh load give 34,392 then 38,322
(`runs/seven/twice.sh`). A dirty database makes the label option dearer, never cheaper.

## A second thing, separate from the first, and it took one command to settle

Every one of these label runs logs, at its own `Validating repair` step, eight `Detected conflict
after repair` errors — eight being the number of constraints in the workload. Every *edge* run we
have, in the same `--mark` mode with the same tool, logs none.

It is an artefact of marking labels, and we checked rather than assumed: the same repair committed
for real, without `--mark`, validates with zero conflicts (2026-09-13, weight 34,392, 3,930 nodes).
Marking a label *adds* `_PGREPAIR_DELETED__<Label>` and leaves the original in place, so the
constraint still sees it; marking an edge re-types it, so it does not. You may want `--mark` to say
so, or to mark labels the other way. It costs us nothing — we read the marked graph ourselves — and
it made us doubt a result that was sound.

That run is also a sixth reproduction of 34,392, three days later, on a fresh load and without
`--mark`. The anomaly below is unaffected by any of this.

## The question

When the solver returns 34,392, is the cheap labelset vertex in the hypergraph at all? If it is,
an ILP minimising total weight should never leave 3,930 on the table. If it is not, what removes it,
and what did the 13:16 run have that ours do not?

## How to replay

```
NEO4J_LOCAL_PASSWORD=… bash runs/seven/repeat.sh 2 "workloads/eurlex-labels.toml workloads/eurlex-laws.toml" orig
NEO4J_LOCAL_PASSWORD=… bash runs/seven/twice.sh
```

The graph, the sealed injection journal and both logs are in `runs/seven/`. The full account,
including what the judge makes of each candidate, is in
`measures/label-repair-not-reproducible-2026-09-10.json`.

## Why we are handing you a question and not a diagnosis

We published, after four review passes, that pgrepair repairs 3,932 of 3,932 wrong labels where
neither of our witnesses can act at all. That sentence is true and it was incomplete: as we can
reproduce it today, the same repair costs 11,200 true facts. We have corrected it in our own
README and in the memo. We would rather bring you the anomaly with its logs than a cause we cannot
support, and the code is yours.
