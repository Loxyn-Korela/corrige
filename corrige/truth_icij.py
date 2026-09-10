"""Build a frozen truth from the ICIJ Offshore Leaks graph as published, read straight from
Neo4j after the setup queries of Bonifati's own workload have run.

    python3 -m corrige.truth_icij <out.json> [--password …]

Truth by construction: this is not the world, it is the data ICIJ published, frozen with its
dump's identity, and it says so. Coverage is declared: the three relations her constraints
gamma_1 to gamma_3 touch. gamma_4 (a quantified path over officer_of) is out of coverage: its
1.7 million edges and its variable-length pattern are not yet expressible in our law module.
"""
import sys, json, os, hashlib, pathlib, collections
from . import canon, laws_icij
from .neo4j_graph import Db

RELS = ("same_name_as", "sole_director_of", "president_of")
DUMP = {"file": "icij-offshoreleaks-5.13.0.dump",
        "from": "https://offshoreleaks-data.icij.org/offshoreleaks/neo4j/icij-offshoreleaks-5.13.0.dump",
        "bytes": 364517980}


def build(db, frozen="2026-09-10"):
    facts, nodes, seen = [], {}, set()
    for rel in RELS:
        page, i = 20000, 0
        while True:
            rows = db.rows(f"MATCH (a)-[r:{rel}]->(b) RETURN a.node_id AS s, b.node_id AS o, "
                           f"labels(a) AS la, labels(b) AS lb, a.name AS an, b.name AS bn, "
                           f"a.status AS ast, b.status AS bst, a.inactivation_date AS ad, b.inactivation_date AS bd "
                           f"SKIP {i} LIMIT {page}")
            if not rows:
                break
            for r in rows:
                s, o = str(r["s"]), str(r["o"])
                if (s, rel, o) not in seen:
                    seen.add((s, rel, o)); facts.append({"s": s, "p": rel, "o": o})
                for side, lab, nm, st, dt in (("s", "la", "an", "ast", "ad"), ("o", "lb", "bn", "bst", "bd")):
                    nid = s if side == "s" else o
                    if nid not in nodes:
                        nodes[nid] = {"id": nid, "labels": sorted(x for x in r[lab] if not x.startswith("_")),
                                      "name": r[nm], "status": r[st], "inactivation_date": r[dt]}
            i += page
    facts.sort(key=lambda f: (f["p"], f["s"], f["o"]))
    for k, f in enumerate(facts, 1):
        f["id"] = f"i-{k:06d}"
    nodes = [nodes[k] for k in sorted(nodes)]
    ntab = {n["id"]: n for n in nodes}
    idx = laws_icij.Index(facts)
    known = []
    for f in facts:
        v = laws_icij.violations(f, ntab, idx)
        if v:
            known.append({"fact": f["id"], "kind": "law_violation", "laws": v})
    for n in nodes:
        v = laws_icij.node_violations(n)
        if v:
            known.append({"node": n["id"], "kind": "law_violation", "laws": v})
    counts = collections.Counter(f["p"] for f in facts)
    truth = {
        "id": f"truth-icij-offshoreleaks-{frozen}",
        "angle": "construction",
        "laws_module": "icij",
        "source": f"ICIJ Offshore Leaks, Neo4j dump {DUMP['file']} as published by ICIJ, loaded on {frozen}; "
                  "the typed relations come from the setup queries of pgrepair's own icij-qualitative-study workload",
        "dump": DUMP,
        "frozen": frozen,
        "status": "unaudited",
        "world": {r: {"closed": True, "why": "the published dump is the reference by construction: it is not the world, it is what ICIJ published"} for r in RELS},
        "coverage": {
            "covers": "the three relations the published constraints gamma_1 to gamma_3 touch: same_name_as, sole_director_of, president_of, with the name, status and inactivation date of their endpoints",
            "does_not_cover": ["officer_of and the quantified path of gamma_4 (1.7 million edges, a variable-length pattern our law module cannot yet express)",
                               "addresses, intermediaries, and every other relation of the dump",
                               "whether any of this is true of the world: this truth is the published data, frozen"],
            "counts": {**{r: counts[r] for r in RELS}, "resources": len(nodes)}},
        "audit": {"sample_name": None, "sample": 0, "method": "none: this truth is by construction, there is nothing to audit against a document", "truth_error_rate": None, "date": None},
        "world_laws": laws_icij.LAWS,
        "nodes": nodes,
        "facts": [{"id": f["id"], "s": f["s"], "p": f["p"], "o": f["o"], "evidence_status": "not_applicable"} for f in facts],
        "known_registry_faults": known,
        "known_gaps": [],
        "reserves": [],
    }
    truth["sha256"] = canon.sha256({"nodes": truth["nodes"], "facts": truth["facts"]})
    return truth


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pw = sys.argv[sys.argv.index("--password") + 1] if "--password" in sys.argv else os.environ.get("NEO4J_LOCAL_PASSWORD")
    truth = build(Db(password=pw))
    canon.write(args[0], truth)
    c = truth["coverage"]["counts"]
    print(f"{args[0]}: " + " · ".join(f"{k} {v}" for k, v in c.items()) + f" · sha256 {truth['sha256'][:16]}")
    kinds = collections.Counter(tuple(k.get("laws", [])) for k in truth["known_registry_faults"])
    print("known faults of the source:", {"/".join(k): v for k, v in kinds.items()})


if __name__ == "__main__":
    main()
