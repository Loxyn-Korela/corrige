"""Build the EUR-Lex truth file from the frozen lot A (relations) and lot A2
(node properties) of the collection, as N-Triples on disk. Nothing is
transformed: a fact is a triple as served; a node property is a value as served.

    python3 -m corrige.truth_eurlex <collection dir> <out.json> [--toy 200 --seed 7]

The collection dir holds graphe/A1/{repeals,amends,based_on}/page-*.nt,
graphe/A2/proprietes/paquet-*.nt and manifeste/A2_cibles_absentes.txt.
"""
import sys, re, pathlib, collections, datetime, random
from . import canon, laws

CDM = "http://publications.europa.eu/ontology/cdm#"
CELLAR = "http://publications.europa.eu/resource/cellar/"
EMPTY_CELEX_URI = "http://publications.europa.eu/resource/celex/"
PRED = {CDM + "resource_legal_repeals_resource_legal": "repeals",
        CDM + "resource_legal_amends_resource_legal": "amends",
        CDM + "resource_legal_based_on_resource_legal": "based_on"}
PROP = {CDM + "resource_legal_id_celex": "celex",
        CDM + "work_date_document": "date_document",
        CDM + "resource_legal_date_entry-into-force": "date_entry_into_force",
        CDM + "resource_legal_date_end-of-validity": "date_end_of_validity",
        CDM + "resource_legal_in-force": "in_force",
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": "types",
        CDM + "work_has_resource-type": "types",
        CDM + "resource_legal_type": "types"}
NT = re.compile(r'^<([^>]*)>\t<([^>]*)>\t(?:<([^>]*)>|"((?:[^"\\]|\\.)*)"(?:\^\^<[^>]*>|@[a-z-]+)?) \.$')


def short(uri):
    if uri.startswith(CELLAR):
        return "cellar:" + uri[len(CELLAR):]
    return uri


_ESC = re.compile(r'\\(u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8}|[tnr"\\])')

def unescape(lit):
    """N-Triples string escapes: backslash-u XXXX, backslash-U XXXXXXXX, tab, newline, return, quote, backslash."""
    def one(m):
        e = m.group(1)
        if e[0] in "uU": return chr(int(e[1:], 16))
        return {"t": "\t", "n": "\n", "r": "\r", '"': '"', "\\": "\\"}[e]
    return _ESC.sub(one, lit)


def read_nt(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = NT.match(line.rstrip("\n"))
            if m:
                s, p, o_uri, o_lit = m.groups()
                yield s, p, o_uri if o_uri is not None else None, (unescape(o_lit) if o_lit is not None else None)


def celex_year(celex):
    m = re.match(r'^[0-9]([0-9]{4})[A-Z]', celex or "")
    return int(m.group(1)) if m else None


def date_status(node):
    d = node.get("date_document")
    if not d:
        return "missing"
    try:
        y = datetime.date.fromisoformat(d).year
    except ValueError:
        return "sentinel"
    if y < 1950:
        return "sentinel"          # an impossible value (1003-03-03): a registry fault
    cy = celex_year(node.get("celex"))
    if cy is not None and abs(cy - y) > 10:
        return "inconsistent"     # a real date that disagrees with the CELEX year (consolidated versions, treaties): a reserve, not a fault; excluded from L1/L2
    return "ok"


def build(coll, frozen="2026-09-09"):
    coll = pathlib.Path(coll)
    facts = []
    seen = set()
    for pred_dir in ("repeals", "amends", "based_on"):
        for page in sorted((coll / "graphe" / "A1" / pred_dir).glob("page-*.nt")):
            for s, p, o, _ in read_nt(page):
                key = (short(s), PRED[p], short(o))
                if key in seen:
                    continue
                seen.add(key)
                facts.append({"s": key[0], "p": key[1], "o": key[2]})
    facts.sort(key=lambda f: (f["p"], f["s"], f["o"]))
    for i, f in enumerate(facts, 1):
        f["id"] = f"f-{i:06d}"
    node_ids = {f["s"] for f in facts} | {f["o"] for f in facts}
    props = collections.defaultdict(lambda: collections.defaultdict(set))
    for paq in sorted((coll / "graphe" / "A2" / "proprietes").glob("paquet-*.nt")):
        for s, p, o_uri, o_lit in read_nt(paq):
            if p not in PROP:
                continue
            sid = short(s)
            if sid not in node_ids:
                continue
            val = o_lit if o_lit is not None else (o_uri.rsplit("/", 1)[-1] if PROP[p] == "types" else o_uri)
            props[sid][PROP[p]].add(val)
    gaps = set()
    gap_file = coll / "manifeste" / "A2_cibles_absentes.txt"
    if gap_file.exists():
        for line in gap_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("http"):
                gaps.add(short(line))
    nodes = []
    multi = collections.Counter()
    for nid in sorted(node_ids):
        pr = props.get(nid, {})
        node = {"id": nid, "celex": None, "date_document": None, "date_entry_into_force": None,
                "date_end_of_validity": None, "in_force": None, "types": sorted(pr.get("types", []))}
        for k in ("celex", "date_document", "date_entry_into_force", "date_end_of_validity", "in_force"):
            vals = sorted(pr.get(k, []))
            if vals:
                node[k] = vals[0]
                if len(vals) > 1:
                    node[k + "_all"] = vals
                    multi[k] += 1
        if node["in_force"] is not None:
            node["in_force"] = node["in_force"] in ("true", "1")
        if nid == "http://publications.europa.eu/resource/celex/" or nid == short(EMPTY_CELEX_URI):
            node["celex"] = ""
        if nid in gaps:
            node["gap"] = True
        node["date_document_status"] = date_status(node)
        nodes.append(node)
    ntab = {n["id"]: n for n in nodes}
    known_faults = []
    for n in nodes:
        if n["date_document_status"] == "sentinel" and n["date_document"]:
            known_faults.append({"node": n["id"], "kind": "sentinel_date", "atlas": "form-184", "value": n["date_document"]})
    reserves = [{"node": n["id"], "kind": "date_inconsistent_with_celex_year", "value": n["date_document"], "celex": n["celex"]}
                for n in nodes if n["date_document_status"] == "inconsistent"]
    for f in facts:
        if f["o"] == short(EMPTY_CELEX_URI) or f["o"] == EMPTY_CELEX_URI:
            known_faults.append({"fact": f["id"], "kind": "empty_target", "atlas": "form-182"})
    # census of real law violations (step 2b), before any injection
    viol = 0
    for f in facts:
        v = laws.violations(f, ntab)
        v = [x for x in v if not (x == "L3" and any(k.get("fact") == f["id"] and k["kind"] == "empty_target" for k in known_faults))]
        if v:
            known_faults.append({"fact": f["id"], "kind": "law_violation", "laws": v})
            viol += 1
    known_gaps = [{"node": g, "kind": "absent_from_cellar",
                   "seen_as_target_in": [f["id"] for f in facts if f["o"] == g]} for g in sorted(gaps)]
    counts = collections.Counter(f["p"] for f in facts)
    truth = {
        "id": f"truth-eurlex-relations-{frozen}",
        "angle": "registry",
        "source": "Cellar SPARQL (publications.europa.eu/webapi/rdf/sparql), three predicates, frozen as N-Triples by the collection session on 2026-09-09 (lot A1); node properties from lot A2",
        "frozen": frozen,
        "status": "unaudited",
        "world": {
            "repeals": {"closed": True, "why": "an official register of repeals is exhaustive for the acts it lists; targets absent from Cellar are in known_gaps"},
            "amends": {"closed": True, "why": "same"},
            "based_on": {"closed": False, "why": "legal bases are declared unevenly (43 empty targets): a candidate's extra based_on is out_of_coverage, never false"}},
        "coverage": {
            "covers": "acts that take part in resource_legal_repeals|amends|based_on_resource_legal, as served on 2026-09-09",
            "does_not_cover": ["work_cites_work", "consolidations", "case law", "acts whose text is not served"],
            "counts": {"repeals": counts["repeals"], "amends": counts["amends"], "based_on": counts["based_on"], "resources": len(nodes)}},
        "audit": {"sample_name": "audit-200", "sample": 200, "method": "facts read against the act's text by a human", "truth_error_rate": None, "date": None},
        "world_laws": laws.LAWS,
        "nodes": nodes,
        "facts": [{"id": f["id"], "s": f["s"], "p": f["p"], "o": f["o"], "evidence_status": "not_in_lot_B"} for f in facts],
        "known_registry_faults": known_faults,
        "known_gaps": known_gaps,
        "reserves": reserves,
        "notes": {"multi_valued_properties": dict(multi), "rule": "when a property has several values, the smallest is kept and the list is in <prop>_all"},
    }
    truth["sha256"] = canon.sha256({"nodes": truth["nodes"], "facts": truth["facts"]})
    return truth


def toy(truth, n=200, seed=7):
    """Deterministic sample: at least 5 facts per relation, 2 empty-target facts,
    2 facts touching a sentinel node, 2 known_gaps nodes; all nodes of the facts."""
    rng = random.Random(seed)
    facts = truth["facts"]
    by_id = {f["id"]: f for f in facts}
    kf = truth["known_registry_faults"]
    sentinel_nodes = {k["node"] for k in kf if k["kind"] == "sentinel_date"}
    empty = [by_id[k["fact"]] for k in kf if k["kind"] == "empty_target"][:2]
    sent = [f for f in facts if f["s"] in sentinel_nodes or f["o"] in sentinel_nodes]
    rng.shuffle(sent); sent = sent[:2]
    gaps = truth["known_gaps"][:2]
    gap_facts = [by_id[g["seen_as_target_in"][0]] for g in gaps if g["seen_as_target_in"]]
    chosen = {f["id"]: f for f in empty + sent + gap_facts}
    for p in ("repeals", "amends", "based_on"):
        pool = [f for f in facts if f["p"] == p and f["id"] not in chosen]
        rng.shuffle(pool)
        for f in pool[:5]:
            chosen[f["id"]] = f
    pool = [f for f in facts if f["id"] not in chosen]
    rng.shuffle(pool)
    for f in pool:
        if len(chosen) >= n:
            break
        chosen[f["id"]] = f
    tf = sorted(chosen.values(), key=lambda f: f["id"])
    ids = {f["s"] for f in tf} | {f["o"] for f in tf} | {g["node"] for g in gaps}
    tn = [nd for nd in truth["nodes"] if nd["id"] in ids]
    fid = {f["id"] for f in tf}
    t = dict(truth)
    t["id"] = truth["id"] + f"-toy-{n}"
    t["toy_of"] = truth["sha256"]
    t["seed"] = seed
    t["nodes"], t["facts"] = tn, tf
    t["known_registry_faults"] = [k for k in kf if k.get("fact") in fid or k.get("node") in ids]
    t["reserves"] = [r for r in truth.get("reserves", []) if r["node"] in ids]
    t["known_gaps"] = [g for g in gaps]
    t["coverage"] = dict(truth["coverage"], counts={"repeals": sum(f["p"] == "repeals" for f in tf), "amends": sum(f["p"] == "amends" for f in tf), "based_on": sum(f["p"] == "based_on" for f in tf), "resources": len(tn)})
    t["sha256"] = canon.sha256({"nodes": tn, "facts": tf})
    return t


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        sys.exit(__doc__)
    coll, out = args[0], args[1]
    truth = build(coll)
    canon.write(out, truth)
    c = truth["coverage"]["counts"]
    print(f"{out}: {c['repeals']} repeals, {c['amends']} amends, {c['based_on']} based_on, {c['resources']} nodes, sha256 {truth['sha256'][:16]}")
    kinds = collections.Counter(k["kind"] for k in truth["known_registry_faults"])
    print("known registry faults:", dict(kinds), "| known gaps:", len(truth["known_gaps"]))
    st = collections.Counter(n["date_document_status"] for n in truth["nodes"]); print("date_document_status:", dict(st), "| reserves:", len(truth["reserves"]))
    if "--toy" in sys.argv:
        n = int(sys.argv[sys.argv.index("--toy") + 1])
        seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 7
        t = toy(truth, n, seed)
        top = pathlib.Path(out).with_name(pathlib.Path(out).stem + f"-toy-{n}.json")
        canon.write(top, t)
        print(f"{top}: {len(t['facts'])} facts, {len(t['nodes'])} nodes, {len(t['known_registry_faults'])} known faults, {len(t['known_gaps'])} gaps, sha256 {t['sha256'][:16]}")


if __name__ == "__main__":
    main()
