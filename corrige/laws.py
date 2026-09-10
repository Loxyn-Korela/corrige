"""World laws, written before any injection and without looking at any journal.
Each law has a plain sentence, a Cypher form for pgrepair, and a Python form
the judge and the census apply to a truth or a candidate in memory."""
import datetime

def _d(s):
    try:
        return datetime.date.fromisoformat(s) if s else None
    except ValueError:
        return None

LAWS = [
    {"id": "L1", "kind": "date_order",
     "text": "an act cannot repeal or amend an act whose date_document is later than its own",
     "cypher": "MATCH p=(a:Act)-[r:REPEALS|AMENDS]->(b:Act) WHERE a.date_document_status = 'ok' AND b.date_document_status = 'ok' AND date(a.date_document) < date(b.date_document) RETURN p"},
    {"id": "L2", "kind": "date_order",
     "text": "an act does not amend anything dated after its own end of validity",
     "cypher": "MATCH p=(a:Act)-[r:AMENDS]->(b:Act) WHERE a.date_end_of_validity IS NOT NULL AND b.date_document_status = 'ok' AND date(b.date_document) > date(a.date_end_of_validity) RETURN p"},
    {"id": "L3", "kind": "identifier",
     "text": "a legal basis is an act with a CELEX, never an empty identifier",
     "cypher": "MATCH p=(a:Act)-[r:BASED_ON]->(b) WHERE (b.celex IS NULL OR b.celex = '') AND coalesce(b.gap, false) = false RETURN p"},
    # the one strict two-edge law the census allows on this truth (1 real violation in 489,223 facts):
    # a violation involves two edges and deleting either one repairs it — a repairer has to choose
    {"id": "L4", "kind": "two_edges",
     "text": "two acts do not repeal each other: if A repeals B, B does not repeal A",
     "cypher": "MATCH p1=(a:Act)-[r1:REPEALS]->(b:Act), p2=(b)-[r2:REPEALS]->(a) RETURN p1, p2"},
]


class Index:
    """Edges by target node, for the two-edge law."""
    def __init__(self, facts):
        self.into = {}
        for f in facts:
            self.into.setdefault(f["o"], []).append(f)

    def targets(self, o, p):
        return [f for f in self.into.get(o, []) if f["p"] == p]


def violations(fact, nodes, index=None):
    """Return the ids of the laws this fact violates, given a node table {id: node} and,
    for the two-edge laws, an Index of the graph's edges (None = one-edge laws only)."""
    a, b = nodes.get(fact["s"]), nodes.get(fact["o"])
    out = []
    if index is not None and fact["p"] == "repeals":
        if any(g["s"] == fact["o"] for g in index.targets(fact["s"], "repeals")):
            out.append("L4")
    if fact["p"] in ("repeals", "amends") and a and b:
        if a.get("date_document_status") == "ok" and b.get("date_document_status") == "ok":
            if _d(a["date_document"]) < _d(b["date_document"]):
                out.append("L1")
    if fact["p"] == "amends" and a and b:
        if a.get("date_end_of_validity") and b.get("date_document_status") == "ok":
            if _d(b["date_document"]) > _d(a["date_end_of_validity"]):
                out.append("L2")
    if fact["p"] == "based_on":
        if b is None or (not b.get("celex")) and not b.get("gap"):
            out.append("L3")
    return out
