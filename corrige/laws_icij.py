"""World laws for the ICIJ Offshore Leaks graph, written from the constraints Bonifati's team
published with pgrepair (`workloads/icij-qualitative-study.toml`), not invented here.

I1 and I2 are one-edge (or one-node) laws: a violation names exactly one thing to delete.
I3 is a two-edge law: an entity has at most one sole director, so a violation involves two
edges and deleting either repairs it — the case where an optimising repairer has to choose.
"""
import datetime

LAWS = [
    {"id": "I1", "kind": "one_edge", "source": "gamma_1 of icij-qualitative-study.toml",
     "text": "two nodes linked by same_name_as carry the same name",
     "cypher": "MATCH p=(o)-[r:same_name_as]->(e) WHERE o.name IS NOT NULL AND e.name IS NOT NULL AND o.name <> e.name RETURN p"},
    {"id": "I2", "kind": "node", "source": "gamma_2",
     "text": "an entity with an inactivation date in the past is not Active",
     "cypher": "MATCH (e:Entity) WHERE e.inactivation_date IS NOT NULL AND date(e.inactivation_date) <= date('2025-07-01') AND e.status = 'Active' RETURN e"},
    {"id": "I3", "kind": "two_edges", "source": "gamma_3",
     "text": "an entity has at most one sole director",
     "cypher": "MATCH p1=(x:Officer)-[:sole_director_of]->(y:Entity), p2=(z:Officer)-[:sole_director_of]->(y) WHERE x <> z RETURN p1, p2"},
]

CUTOFF = datetime.date(2025, 7, 1)


class Index:
    """Edges by target node, for the two-edge law."""
    def __init__(self, facts):
        self.into = {}
        for f in facts:
            self.into.setdefault(f["o"], []).append(f)

    def targets(self, o, p):
        return [f for f in self.into.get(o, []) if f["p"] == p]


def _d(s):
    try:
        return datetime.date.fromisoformat(s[:10]) if s else None
    except (ValueError, TypeError):
        return None


def violations(fact, nodes, index=None):
    """Law ids this fact violates. I2 is a node law and is reported by node_violations."""
    out = []
    a, b = nodes.get(fact["s"]), nodes.get(fact["o"])
    if fact["p"] == "same_name_as" and a and b:
        # her pattern is (o:Officer|Entity)-[:same_name_as]->(e:Officer|Entity): the labels are part of the law
        ok = {"Officer", "Entity"} & set(a.get("labels", [])) and {"Officer", "Entity"} & set(b.get("labels", []))
        if ok and a.get("name") and b.get("name") and a["name"] != b["name"]:
            out.append("I1")
    if index is not None and fact["p"] == "sole_director_of":
        others = [g for g in index.targets(fact["o"], "sole_director_of") if g["s"] != fact["s"]]
        if others:
            out.append("I3")
    return out


def node_violations(node):
    """I2: an entity whose inactivation date has passed cannot be Active."""
    if "Entity" not in node.get("labels", []):
        return []
    d = _d(node.get("inactivation_date"))
    return ["I2"] if d and d <= CUTOFF and node.get("status") == "Active" else []
