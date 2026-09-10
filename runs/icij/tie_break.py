"""Why the same repairer, on the same graph, returns a different answer twice.

pgrepair's greedy picks the vertex to delete out of a conflict with
    vertex = min(hyperedge, key=lambda v: weights[v])          # greedy_cleaner.py:37
where `hyperedge` is a Python `set` and a vertex is the pair
    (element_id, EntityType)                                   # conflict_collectors.py:236
Neo4j's `element_id` is a string, so the pair's hash goes through `hash(str)`, which Python
randomises per process unless PYTHONHASHSEED is fixed. When two vertices carry the SAME weight —
exactly our blind rival case, where nothing separates the true edge from the false one — the set's
iteration order decides, and that order changes from one process to the next.

    python3 runs/icij/tie_break.py

This reproduces the mechanism in isolation, outside pgrepair and outside Neo4j. It does not by
itself prove that the variation we measured between two ICIJ arms comes only from here: a fresh
dump load can also hand back different element ids and a different row order. It proves the tie is
broken by something that carries no information about which edge is true.
"""
import subprocess, sys, collections

SNIPPET = (
    "ids=[f'4:9e5f7a1c-0000-4000-8000-00000000{i:04d}:{i}' for i in range(2)];"
    "e={(ids[0],'EDGE'),(ids[1],'EDGE')};w={v:7 for v in e};"
    "print(min(e,key=lambda v:w[v])[0][-1])"
)


def run(env_seed=None):
    import os
    env = dict(os.environ)
    if env_seed is None:
        env.pop("PYTHONHASHSEED", None)
    else:
        env["PYTHONHASHSEED"] = str(env_seed)
    return subprocess.run([sys.executable, "-c", SNIPPET], capture_output=True, text=True, env=env).stdout.strip()


if __name__ == "__main__":
    print("two edges of equal weight; which one does min() pick?\n")
    for s in range(6):
        print(f"  PYTHONHASHSEED={s}  -> edge {run(s)}")
    c = collections.Counter(run() for _ in range(20))
    print(f"\n  hash seed left random (the default), 20 processes -> {dict(c)}")
    print("\n  A repairer whose choice depends on the process it runs in is not choosing.")
    print("  A fix that changes nothing it computes: give min() a second key that does not depend")
    print("  on the process, e.g. key=lambda v: (weights[v], v[0], v[1].value) — EntityType is a")
    print("  plain Enum and is not orderable on its own.")
