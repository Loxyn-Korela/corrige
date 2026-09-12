"""Load a graph (truth or injected) into Neo4j and read it back after a repair.
Stdlib only: the Neo4j HTTP transactional API. The database is a disposable view;
every node and edge carries `_corrige_id` as a property, which survives pgrepair's
`--mark` (it deletes an edge and recreates it as `_PGREPAIR_DELETED`, properties copied).

    python3 -m corrige.neo4j_graph load  <graph.json>  [--url http://localhost:7474 --user neo4j --password …]
    python3 -m corrige.neo4j_graph read  <graph.json> <candidate.json> --name pgrepair [--version …]

Mapping (design §2.1): node -> (:Act {…}), repeals -> [:REPEALS], amends -> [:AMENDS],
based_on -> [:BASED_ON]; a known-gap node -> (:Act {celex: null, gap: true}).
Reconstruction (design §3): (1) an edge of type _PGREPAIR_DELETED is deleted; (2) a node
marked deleted is deleted and every edge incident to it counts deleted (collateral);
(3) candidate = graph minus (1) and (2).
"""
import sys, json, os, base64, urllib.request, pathlib, collections
from . import canon, laws

REL = {"repeals": "REPEALS", "amends": "AMENDS", "based_on": "BASED_ON"}
REL_INV = {v: k for k, v in REL.items()}


class Db:
    def __init__(self, url="http://localhost:7474", user="neo4j", password=None, db="neo4j"):
        self.url = url.rstrip("/") + f"/db/{db}/tx/commit"
        self.auth = base64.b64encode(f"{user}:{password}".encode()).decode()

    def run(self, statements):
        body = json.dumps({"statements": [{"statement": s, "parameters": p or {}} for s, p in statements]}).encode()
        req = urllib.request.Request(self.url, data=body, method="POST",
                                     headers={"Content-Type": "application/json", "Accept": "application/json", "Authorization": "Basic " + self.auth})
        with urllib.request.urlopen(req, timeout=3600) as r:
            out = json.loads(r.read())
        if out.get("errors"):
            raise RuntimeError(out["errors"])
        return out["results"]

    def rows(self, cypher, params=None):
        res = self.run([(cypher, params)])[0]
        return [dict(zip(res["columns"], d["row"])) for d in res["data"]]


def wipe(db, batch=20000):
    """Empty the database in bounded transactions. A single DETACH DELETE over a large graph
    (the ICIJ dump leaves 2M nodes behind) exceeds dbms.memory.transaction.total.max and fails."""
    total = 0
    while True:
        n = db.rows(f"MATCH (n) WITH n LIMIT {batch} DETACH DELETE n RETURN count(*) AS n")[0]["n"]
        total += n
        if n == 0:
            return total


def load(db, graph, batch=5000):
    wipe(db)
    for stmt in ("CREATE INDEX act_id IF NOT EXISTS FOR (n:Act) ON (n.id)",
                 "CREATE INDEX act_cid IF NOT EXISTS FOR (n:Act) ON (n._corrige_id)"):
        db.run([(stmt, None)])
    nodes = graph["nodes"]
    for i in range(0, len(nodes), batch):
        rows = []
        for n in nodes[i:i + batch]:
            rows.append({"id": n["id"], "cid": "n:" + n["id"], "celex": n.get("celex"), "date_document": n.get("date_document"),
                         "type_label": n.get("type_label"), "celex_type": laws.type_label(n.get("celex")),
                         "date_document_status": n.get("date_document_status", "missing"), "date_entry_into_force": n.get("date_entry_into_force"),
                         "date_end_of_validity": n.get("date_end_of_validity"), "in_force": n.get("in_force"), "gap": bool(n.get("gap", False))})
        db.run([("UNWIND $rows AS r CREATE (n:Act {id: r.id, _corrige_id: r.cid, celex: r.celex, celex_type: r.celex_type, date_document: r.date_document, date_document_status: r.date_document_status, date_entry_into_force: r.date_entry_into_force, date_end_of_validity: r.date_end_of_validity, in_force: r.in_force, gap: r.gap})", {"rows": rows})])
        # the type label the graph claims: a real Neo4j label, so that a label repair can act on it
        for lab in sorted({r["type_label"] for r in rows if r["type_label"]}):
            ids = [r["id"] for r in rows if r["type_label"] == lab]
            db.run([(f"UNWIND $ids AS i MATCH (n:Act {{id: i}}) SET n:{lab}", {"ids": ids})])
    facts = graph["facts"]
    by_rel = collections.defaultdict(list)
    for k, f in enumerate(facts):
        # `conf` is where an upstream filter's opinion lands: one number per fact, carried onto the
        # edge, read back by pgrepair with --custom-weight. A fact without one gets EDGE_WEIGHT, the
        # weight pgrepair would have computed itself, so an unmarked graph behaves exactly as before.
        by_rel[REL[f["p"]]].append({"s": f["s"], "o": f["o"], "conf": f.get("conf", 2),
                                    "cid": f"e:{k}:{f['s']}|{f['p']}|{f['o']}"})
    for rel, rows_all in by_rel.items():
        for i in range(0, len(rows_all), batch):
            db.run([(f"UNWIND $rows AS r MATCH (a:Act {{id: r.s}}), (b:Act {{id: r.o}}) CREATE (a)-[:{rel} {{_corrige_id: r.cid, conf: r.conf}}]->(b)", {"rows": rows_all[i:i + batch]})])
    n = db.rows("MATCH (n:Act) RETURN count(n) AS n")[0]["n"]
    e = db.rows("MATCH ()-[r]->() RETURN count(r) AS e")[0]["e"]
    return n, e


def read_candidate(db, graph, name, version="", params=None):
    """Rebuild the candidate file from the marked database."""
    deleted_edges = {r["cid"] for r in db.rows("MATCH ()-[r:_PGREPAIR_DELETED]->() RETURN r._corrige_id AS cid")}
    # a label repair MARKS: it adds _PGREPAIR_DELETED__<Label> and leaves the original in place.
    # The candidate is the graph minus the marked labels.
    labels = {}
    for r in db.rows("MATCH (n) WHERE n.id IS NOT NULL RETURN n.id AS id, labels(n) AS labs"):
        gone = {l[len("_PGREPAIR_DELETED__"):] for l in r["labs"] if l.startswith("_PGREPAIR_DELETED__")}
        labels[r["id"]] = [l for l in r["labs"] if l != "Act" and not l.startswith("_PGREPAIR") and l not in gone]
    # a NODE deleted carries the exact label _PGREPAIR_DELETED; _PGREPAIR_DELETED__<Label> means
    # that one label was deleted, and the node itself stays.
    marked_nodes = {r["id"] for r in db.rows("MATCH (n:_PGREPAIR_DELETED) RETURN n.id AS id")}
    facts, removed = [], 0
    for k, f in enumerate(graph["facts"]):
        cid = f"e:{k}:{f['s']}|{f['p']}|{f['o']}"
        if cid in deleted_edges or f["s"] in marked_nodes or f["o"] in marked_nodes:
            removed += 1
            continue
        facts.append({"s": f["s"], "p": f["p"], "o": f["o"]})
    cand = {"candidate": {"name": name, "version": version, "code_sha256": None, "params": params or {}, "seed": None},
            "truth_sha256": graph["truth_sha256"], "journal_sha256": graph.get("journal_sha256"),
            "nodes": [dict(n, labels=[l for l in labels.get(n["id"], []) if not l.startswith("_PGREPAIR")],
                           type_label=next((l for l in labels.get(n["id"], []) if l in laws.CELEX_TYPE.values()), None))
                      for n in graph["nodes"] if n["id"] not in marked_nodes],
            "facts": facts, "abstained": [], "deleted_nodes": sorted(marked_nodes),
            "reconstruction": {"edges_marked_deleted": len(deleted_edges), "nodes_marked_deleted": len(marked_nodes), "facts_removed": removed}}
    return cand


def _db_from_args(args):
    def opt(name, default):
        return args[args.index(name) + 1] if name in args else default
    pw = opt("--password", os.environ.get("NEO4J_LOCAL_PASSWORD"))
    return Db(opt("--url", "http://localhost:7474"), opt("--user", "neo4j"), pw)


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    db = _db_from_args(args)
    if args[0] == "load":
        graph = json.load(open(args[1], encoding="utf-8"))
        n, e = load(db, graph)
        print(f"loaded {n} nodes, {e} edges")
    elif args[0] == "read":
        graph = json.load(open(args[1], encoding="utf-8"))
        name = args[args.index("--name") + 1] if "--name" in args else "pgrepair"
        version = args[args.index("--version") + 1] if "--version" in args else ""
        cand = read_candidate(db, graph, name, version)
        canon.write(args[2], cand)
        print(json.dumps(cand["reconstruction"]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
