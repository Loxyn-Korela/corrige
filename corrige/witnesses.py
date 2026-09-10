"""The two witnesses of layer 1. Each turns a damaged graph into a candidate file.

- dumb_baseline: returns the damaged graph as is (repairs nothing). The floor.
- rule_without_model: applies the world laws mechanically and deletes every edge
  that violates one. The ceiling of what a constraint-based, deletion-only repair
  can do on this truth. It also removes the true facts that really violate a law
  (known_violations_removed), which the judge counts apart (R9).
"""
from . import laws


def _cand(name, graph, facts, deleted_nodes=()):
    return {"candidate": {"name": name, "version": "layer-1", "code_sha256": None, "params": {}, "seed": None},
            "truth_sha256": graph["truth_sha256"], "journal_sha256": graph.get("journal_sha256"),
            "nodes": graph["nodes"], "facts": facts, "abstained": [], "deleted_nodes": list(deleted_nodes)}


def dumb_baseline(graph):
    return _cand("dumb-baseline", graph, list(graph["facts"]))


def rule_without_model(graph):
    nodes = {n["id"]: n for n in graph["nodes"]}
    idx = laws.Index(graph["facts"])
    kept = [f for f in graph["facts"] if not laws.violations(f, nodes, idx)]   # every edge of every violation goes: no arbitration
    return _cand("rule-without-model", graph, kept)
