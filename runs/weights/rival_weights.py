"""Does a weight from upstream do what a law does?

Our two EUR-Lex arms measured the two ends of this question on pgrepair
(`measures/eurlex-arms-spread-2026-09-10.json`):

    130 rivals, nothing separates them   Greedy 64·66·70   ILP 69·59·65   a coin gives 65
    150 rivals, a law separates them     Greedy 150·150·150   ILP 150·150·150

The law is a constraint the repairer can evaluate. A filter upstream of the graph has no such
law: it has read the document and holds an opinion, which is a weight. This asks whether a
weight buys what a law buys, and it separates two effects that are easy to confuse:

    is the answer REPEATABLE?   and   is the answer RIGHT?

Both matter, and the first is the one that decides whether the second can even be measured.

Run it: python3 runs/weights/rival_weights.py       (no database, no network, ~2 s)

The greedy is reproduced as pgrepair writes it — `min(hyperedge, key=lambda v: weights[v])`
over a Python `set` of `(element_id, EntityType)` pairs, whose iteration order depends on
`hash(str)` and therefore on the process. Each arm is run in several fresh processes, exactly
as the real non-determinism arises. The ILP is solved with scipy's `milp`, the solver
`SciPyWeightedILP` is named after.
"""
import json, os, random, subprocess, sys, collections
from pathlib import Path

N_PAIRS   = 130          # the blind arm of the EUR-Lex experiment
KEEP, DEL = 8, 7         # a weight the repairer will keep, and one it will delete
SEEDS     = range(8)     # eight fresh processes per arm

# ── the arms ────────────────────────────────────────────────────────────────────────────
# Each is a rule that, given a rival pair, says what weight the true and the false edge carry.
# `accuracy` is the upstream signal's own accuracy: how often it points at the true edge.
ARMS = [
    ("blind",       None, "nothing separates them: both edges carry the same weight"),
    ("weight p=.5", 0.50, "a filter with an opinion that carries no information, but a distinct weight"),
    ("weight p=.7", 0.70, "a filter right seven times in ten"),
    ("weight p=.9", 0.90, "a filter right nine times in ten"),
    ("law",         1.00, "a law that identifies the true edge, the informed arm we measured"),
]

def pairs(accuracy, seed=20260912):
    """The 130 rival pairs and their weights. The weight assignment is drawn once and does not
    change between runs: a filter that has read a document gives the same answer next time."""
    rng = random.Random(seed)
    out = []
    for i in range(N_PAIRS):
        # element ids shaped like Neo4j's, which is where the hash randomisation enters
        t = f"4:9e5f7a1c-0000-4000-8000-{i:012d}:{2*i}"      # the true edge
        f = f"4:9e5f7a1c-0000-4000-8000-{i:012d}:{2*i+1}"    # the false one
        if accuracy is None:
            wt = wf = DEL
        else:
            right = rng.random() < accuracy
            wt, wf = (KEEP, DEL) if right else (DEL, KEEP)
        out.append((t, f, wt, wf))
    return out

# ── the worker: one process, one arm, the greedy choice ─────────────────────────────────
WORKER = r'''
import sys, json
data = json.loads(sys.stdin.read())
kept = 0
for t, f, wt, wf in data:
    # pgrepair, greedy_cleaner.py:37 — the conflict is a set, the vertex deleted is the lightest
    hyperedge = {(t, "EDGE"), (f, "EDGE")}
    weights = {(t, "EDGE"): wt, (f, "EDGE"): wf}
    deleted = min(hyperedge, key=lambda v: weights[v])
    if deleted[0] == f:
        kept += 1        # it deleted the false edge: the true one survives
print(kept)
'''

def greedy_runs(data):
    """The same arm in several fresh processes, hash seed left random as in production."""
    env = dict(os.environ); env.pop("PYTHONHASHSEED", None)
    out = []
    for _ in SEEDS:
        r = subprocess.run([sys.executable, "-c", WORKER], input=json.dumps(data),
                           capture_output=True, text=True, env=env)
        out.append(int(r.stdout.strip()))
    return out

# ── the ILP, and the reason the blind arm has no single answer ───────────────────────────
def ilp_keeps(data):
    """Minimum-weight vertex cover over disjoint 2-element conflicts, solved as pgrepair's
    SciPyWeightedILP does. Returns (true edges kept, optimum is unique)."""
    import numpy as np
    from scipy.optimize import milp, LinearConstraint, Bounds
    n = len(data)
    c = np.array([w for _, _, wt, wf in data for w in (wt, wf)], dtype=float)
    A = np.zeros((n, 2 * n)); 
    for i in range(n): A[i, 2*i] = A[i, 2*i+1] = 1.0      # delete at least one of each pair
    res = milp(c=c, constraints=LinearConstraint(A, lb=1, ub=2),
               integrality=np.ones(2*n), bounds=Bounds(0, 1))
    x = np.round(res.x).astype(int)
    kept = sum(1 for i, (_, _, wt, wf) in enumerate(data) if x[2*i] == 0)
    # On disjoint pairs the problem separates: the optimum is unique exactly when no pair is tied.
    unique = all(wt != wf for _, _, wt, wf in data)
    return kept, unique, res.fun

if __name__ == "__main__":
    print(f"{N_PAIRS} rival pairs. One edge of each is true; a law says at most one may stay.")
    print(f"Each arm is run in {len(SEEDS)} fresh processes, hash seed left random as in production.\n")
    print(f"  {'arm':<12} {'greedy, one figure per process':<42} {'ILP':>18}  {'repeatable':>10}  {'optimum':>10}")
    print("  " + "-" * 100)
    records = {}
    for name, acc, note in ARMS:
        data = pairs(acc)
        runs = greedy_runs(data)
        kept, unique, cost = ilp_keeps(data)
        repeatable = len(set(runs)) == 1
        shown = "·".join(str(r) for r in runs)
        if len(shown) > 40: shown = shown[:38] + "…"
        ilp_cell = f"{kept}" if unique else f"0-{N_PAIRS} all optimal"
        print(f"  {name:<12} {shown:<42} {ilp_cell:>18}  {'yes' if repeatable else 'NO':>10}  {'unique' if unique else 'degenerate':>10}")
        records[name] = {"note": note, "accuracy_of_the_signal": acc,
                         "greedy_true_edges_kept_per_process": runs,
                         "greedy_repeatable": repeatable,
                         "ilp_true_edges_kept": kept if unique else None,
                         "ilp_note": None if unique else
                             f"the optimum is degenerate: every one of the 2^{N_PAIRS} selections costs the"
                             f" same, so any figure from 0 to {N_PAIRS} is optimal and the {kept} this solver"
                             " returned is not a score",
                         "ilp_cost": cost, "ilp_optimum_unique": unique}
    print("""
  Read it in two columns, because they answer two different questions.

  REPEATABLE is decided by whether the two weights differ at all, not by whether the weight is
  right. `weight p=.5` is a filter whose opinion carries no information: it lands where a coin
  lands, inside the coin's own band around 65. And yet every process returns the very same
  figure, while the blind arm returns a different one each time and none of them is a score.

  RIGHT tracks the signal's own accuracy and nothing else, at 130 x p within sampling.

  The optimum column says why. On disjoint rival pairs the problem separates, and the minimum
  is unique exactly when no pair carries two equal weights. The blind arm is not a solver
  defect: every selection costs the same, so the whole range is optimal and no figure the solver
  returns is a score. Something with no information in it then picks one — in the greedy, the
  iteration order of a Python set.

  So an upstream mark buys repeatability whether or not it is right, and buys accuracy in
  proportion to how right it is. The first is what makes the second measurable at all: a
  repairer that answers differently on the same input cannot be scored, however good it is.""")
    out = Path(__file__).resolve().parent.parent.parent/"measures"/"rival-weights-2026-09-12.json"
    out.write_text(json.dumps({
        "question": "does a weight from upstream do what a law does, on a rival the graph cannot separate",
        "pairs": N_PAIRS, "processes_per_arm": len(SEEDS),
        "weights": {"kept": KEEP, "deleted": DEL},
        "greedy": "pgrepair greedy_cleaner.py:37, min(hyperedge, key=weights) over a Python set",
        "ilp": "scipy.optimize.milp, minimum-weight vertex cover over disjoint 2-element conflicts",
        "measured_on": "a standalone reproduction, no database and no network; the two end points"
                       " it is calibrated against are measures/eurlex-arms-spread-2026-09-10.json",
        "date": "2026-09-12", "arms": records,
    }, ensure_ascii=False, indent=1) + "\n")
    print(f"\n  written: {out.relative_to(out.parent.parent)}")
