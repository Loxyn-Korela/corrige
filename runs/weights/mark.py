"""Write an upstream confidence onto the graph, as a property pgrepair already knows how to read.

pgrepair takes `--custom-weight <property>`: a number held on each node and each edge, used
instead of its own. That is the interface an upstream filter needs and it exists already; what
has never been supplied is the property.

This writes it, and writes it so that the ONLY difference from a default run is the signal:

  every node  the weight pgrepair would compute itself, 2 * degree + labels + 1
  every edge  EDGE_WEIGHT, which is 2
  a rival     3 on the edge the upstream signal points at, 2 on the other

A property that is absent reads as 0 — the cheapest thing in the graph — so every node and every
edge is written, not only the rivals.

  python3 runs/weights/mark.py <journal.json> --accuracy 0.7 [--seed 20260912] --password …

Accuracy is the signal's own: how often it points at the true edge. 1.0 is a filter that is never
wrong, 0.5 one whose opinion carries no information at all. Both are worth running.
"""
import json, random, sys
sys.path.insert(0, __file__.rsplit("/runs/", 1)[0])
from corrige.neo4j_graph import _db_from_args


def rivals(journal, arm="blind"):
    """The blind rival pairs. A cycle injection writes (b repeals a) against a true (a repeals b),
    so the pair is the mirror and needs nothing but the journal entry."""
    out = []
    for e in journal["injected"]:
        if e.get("arm") != arm or e["damage"] != "SPURIOUS_EDGE":
            continue
        out.append({"false": (e["s"], e["o"]), "true": (e["o"], e["s"])})
    return out


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    db = _db_from_args(args)
    journal = json.load(open(args[0], encoding="utf-8"))
    acc = float(args[args.index("--accuracy") + 1]) if "--accuracy" in args else 1.0
    seed = int(args[args.index("--seed") + 1]) if "--seed" in args else 20260912
    arm = args[args.index("--arm") + 1] if "--arm" in args else "blind"

    db.run([("MATCH (n:Act) SET n.conf = 2 * COUNT { (n)--() } + size(labels(n)) + 1", None)])
    db.run([("MATCH ()-[e]->() SET e.conf = 2", None)])

    pairs = rivals(journal, arm)
    rng = random.Random(seed)
    rows, right = [], 0
    for p in pairs:
        points_at_the_truth = rng.random() < acc
        right += points_at_the_truth
        s, o = p["true"] if points_at_the_truth else p["false"]
        rows.append({"s": s, "o": o})
    db.run([("UNWIND $rows AS r MATCH (a:Act {id: r.s})-[e:REPEALS]->(b:Act {id: r.o}) SET e.conf = 3",
             {"rows": rows})])

    n = db.rows("MATCH ()-[e]->() WHERE e.conf = 3 RETURN count(e) AS n")[0]["n"]
    print(json.dumps({"arm": arm, "pairs": len(pairs), "accuracy_asked": acc,
                      "signal_points_at_the_truth": right, "edges_marked_3": n, "seed": seed}))
    if n != len(pairs):
        sys.exit(f"expected {len(pairs)} marked edges, the database holds {n}: the pair rule is wrong")


if __name__ == "__main__":
    main()
