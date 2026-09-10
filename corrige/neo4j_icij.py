"""Apply an injected ICIJ graph to the live Neo4j database and read the candidate back.
The 2-million-node dump is not reloaded: the journal is applied to it, and undone afterwards.

    python3 -m corrige.neo4j_icij apply <graph.json> <journal.json>
    python3 -m corrige.neo4j_icij read  <graph.json> <candidate.json> --name pgrepair-…
    python3 -m corrige.neo4j_icij undo  <journal.json>
"""
import sys, json, os
from . import canon
from .neo4j_graph import Db

RELS = ("same_name_as", "sole_director_of", "president_of")


def stamp(db):
    """Nothing to stamp: pgrepair's --mark keeps the endpoints and the original type, so an edge
    is identified by (start node_id, original type, end node_id) without touching 141,000 rows."""
    return


def apply(db, journal):
    add = [e for e in journal["injected"] if e["damage"] == "SPURIOUS_EDGE"]
    rm = [e for e in journal["injected"] if e["damage"] == "MISSING"]
    for rel in RELS:
        rows = [{"s": e["s"], "o": e["o"]} for e in add if e["p"] == rel]
        for i in range(0, len(rows), 2000):
            db.run([(f"UNWIND $rows AS r MATCH (a {{node_id: toInteger(r.s)}}), (b {{node_id: toInteger(r.o)}}) "
                     f"CREATE (a)-[:{rel} {{_injected: true}}]->(b)", {"rows": rows[i:i + 2000]})])
        rows = [{"s": e["s"], "o": e["o"]} for e in rm if e["p"] == rel]
        for i in range(0, len(rows), 2000):
            db.run([(f"UNWIND $rows AS r MATCH (a {{node_id: toInteger(r.s)}})-[e:{rel}]->(b {{node_id: toInteger(r.o)}}) DELETE e",
                     {"rows": rows[i:i + 2000]})])
    return len(add), len(rm)


def undo(db, journal):
    db.run([("MATCH ()-[r]->() WHERE r._injected IS NOT NULL DELETE r", None)])
    db.run([("MATCH ()-[r:_PGREPAIR_DELETED]->() DELETE r", None)])


def read_candidate(db, graph, name, version=""):
    deleted = {(str(r["s"]), r["lab"], str(r["o"])) for r in
               db.rows("MATCH (a)-[r:_PGREPAIR_DELETED]->(b) RETURN a.node_id AS s, b.node_id AS o, r._pgrepair_original_label AS lab")}
    marked_nodes = {str(r["id"]) for r in db.rows("MATCH (n:_PGREPAIR_DELETED) RETURN n.node_id AS id")}
    facts = [f for f in graph["facts"]
             if (f["s"], f["p"], f["o"]) not in deleted and f["s"] not in marked_nodes and f["o"] not in marked_nodes]
    return {"candidate": {"name": name, "version": version, "code_sha256": None, "params": {}, "seed": None},
            "truth_sha256": graph["truth_sha256"], "journal_sha256": graph.get("journal_sha256"),
            "nodes": [n for n in graph["nodes"] if n["id"] not in marked_nodes],
            "facts": facts, "abstained": [], "deleted_nodes": sorted(marked_nodes),
            "reconstruction": {"edges_marked_deleted": len(deleted), "nodes_marked_deleted": len(marked_nodes),
                               "facts_removed": len(graph["facts"]) - len(facts)}}


def main():
    a = sys.argv[1:]
    db = Db(password=os.environ.get("NEO4J_LOCAL_PASSWORD"))
    if a[0] == "apply":
        stamp(db)
        n, m = apply(db, json.load(open(a[2], encoding="utf-8")))
        print(f"applied: {n} spurious edges created, {m} true edges removed")
    elif a[0] == "undo":
        undo(db, json.load(open(a[1], encoding="utf-8"))); print("undone")
    elif a[0] == "read":
        g = json.load(open(a[1], encoding="utf-8"))
        name = a[a.index("--name") + 1] if "--name" in a else "pgrepair"
        c = read_candidate(db, g, name)
        canon.write(a[2], c); print(json.dumps(c["reconstruction"]))


if __name__ == "__main__":
    main()
