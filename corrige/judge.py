"""The judge: compares a candidate graph to a truth and writes a verdict.
Rules R1-R9 of the layer-1 design are implemented here and nowhere else.

    python3 -m corrige.judge <truth.json> <candidate.json> <verdict.json> [--journal journal.json]

The verdict is keyed on truth fact ids and, for candidate facts outside the
truth, on the (s, p, o) triple; it carries no candidate-internal id and no
input order (R8). Counts are per relation, never pooled (R6). A count whose
denominator is zero is "undefined", never 0 or 1 (R7).
"""
import sys, json, datetime, collections
from . import canon


def _d(s):
    try:
        return datetime.date.fromisoformat(s) if s else None
    except ValueError:
        return None


def _ratio(num, den):
    """num and den are the record; value is a fixed-point string (no floats in canonical JSON)."""
    return {"num": num, "den": den, "value": (f"{num / den:.4f}") if den else "undefined"}


def judge(truth, cand, journal=None):
    # ── refuse what is not bound to this truth (and journal)
    if cand.get("truth_sha256") != truth["sha256"]:
        raise ValueError("candidate does not name this truth (truth_sha256 mismatch)")
    if journal is not None and cand.get("journal_sha256") != journal["sha256"]:
        raise ValueError("candidate does not name this journal (journal_sha256 mismatch)")
    world = truth["world"]
    tnodes = {n["id"]: n for n in truth["nodes"]}
    tfacts = {(f["s"], f["p"], f["o"]): f for f in truth["facts"]}
    kf = truth.get("known_registry_faults", [])
    fault_facts = {k["fact"]: k["kind"] for k in kf if "fact" in k}
    fault_nodes = {k["node"] for k in kf if "node" in k}
    gaps = {g["node"] for g in truth.get("known_gaps", [])}
    cnodes = {n["id"]: n for n in cand.get("nodes", [])}
    abst = {(a["s"], a["p"], a["o"]) for a in cand.get("abstained", [])}

    # ── candidate facts: dedupe with count (R2), resolve (R1)
    seen = collections.Counter()
    for f in cand["facts"]:
        seen[(f["s"], f["p"], f["o"])] += 1

    per_fact = {}                       # truth fact id -> status
    extra = []                          # candidate facts outside the truth
    counts = {p: collections.Counter() for p in world}

    for key, tf in tfacts.items():
        p = tf["p"]
        kind = fault_facts.get(tf["id"])
        if kind:                        # R5, R9: out of denominators
            st = "found" if seen.get(key) else ("abstained" if key in abst else "missed")
            per_fact[tf["id"]] = {"status": "known_fault", "kind": kind, "known_fault": st if st != "missed" else "corrected" if kind != "law_violation" else "removed"}
            counts[p]["known_fault_" + per_fact[tf["id"]]["known_fault"]] += 1
            continue
        if seen.get(key):
            per_fact[tf["id"]] = {"status": "found"}
            counts[p]["found"] += 1
            if seen[key] > 1:
                counts[p]["duplicate"] += seen[key] - 1
                per_fact[tf["id"]]["duplicate"] = seen[key] - 1
        elif key in abst:
            per_fact[tf["id"]] = {"status": "abstained"}
            counts[p]["abstained"] += 1
        else:
            per_fact[tf["id"]] = {"status": "missed"}
            counts[p]["missed"] += 1

    for key, n in sorted(seen.items()):
        if key in tfacts:
            continue
        s, p, o = key
        if p not in world:
            st = "out_of_coverage"
        elif s not in tnodes or o not in tnodes:
            st = "unresolved"
        elif s in gaps or o in gaps:
            st = "out_of_coverage"         # R4
        elif not world[p]["closed"]:
            st = "out_of_coverage"         # open relation
        else:
            st = "false"
        extra.append({"s": s, "p": p, "o": o, "status": st, "copies": n})
        if p in counts:
            counts[p][st] += n if st == "false" else 1
            if st == "false" and n > 1:
                counts[p]["duplicate"] += 0  # duplicates of a false fact are already counted as false copies

    # ── anachronism on nodes (R3)
    anach = []
    dated = 0
    for nid, cn in cnodes.items():
        tn = tnodes.get(nid)
        if not tn or tn.get("date_document_status") != "ok" or nid in fault_nodes:
            continue
        if cn.get("date_document") is None:
            continue
        dated += 1
        if _d(cn["date_document"]) != _d(tn["date_document"]):
            anach.append({"node": nid, "truth": tn["date_document"], "candidate": cn["date_document"]})

    # ── collateral: truth facts lost because a node was deleted (declared by the candidate)
    deleted_nodes = set(cand.get("deleted_nodes", []))
    collateral = [tf["id"] for key, tf in tfacts.items()
                  if per_fact[tf["id"]]["status"] == "missed" and (tf["s"] in deleted_nodes or tf["o"] in deleted_nodes)]

    # ── per-relation dimensions
    dims = {}
    for p in world:
        c = counts[p]
        n_truth = sum(1 for f in truth["facts"] if f["p"] == p and f["id"] not in fault_facts)
        asserted_in_cov = c["found"] + c["duplicate"] + c["false"]     # R2: duplicates weigh as false in precision
        dims[p] = {
            "precision": _ratio(c["found"], asserted_in_cov) if world[p]["closed"] else "undefined (open relation)",
            "recall": _ratio(c["found"], n_truth),
            "silence": _ratio(c["abstained"], n_truth),
            "out_of_coverage": c["out_of_coverage"],
            "unresolved": c["unresolved"],
            "duplicate": c["duplicate"],
            "false": c["false"],
            "known_fault": {k[12:]: v for k, v in c.items() if k.startswith("known_fault_")},
        }
    dims["nodes"] = {"anachronism": _ratio(len(anach), dated) if cnodes else "undefined (candidate has no nodes)"}
    dims["collateral"] = len(collateral)

    # ── repair sub-counts when a journal is given
    repair = None
    if journal is not None:
        inj = journal["injected"]
        sub = {"visible": collections.Counter(), "invisible": collections.Counter(), "beyond_reach": collections.Counter()}
        anach_inj = collections.Counter()
        for e in inj:
            if e["damage"] == "ANACHRONISM":
                cn = cnodes.get(e["node"])
                fixed = cn is not None and cn.get("date_document") == e["truth_date"]
                anach_inj["caught" if fixed else "missed"] += 1      # beyond the reach of a deletion-only repairer
                continue
            if e["damage"] == "DUPLICATE":
                continue
            key = (e["s"], e["p"], e["o"])
            if e["damage"] == "MISSING":
                bucket = "beyond_reach"
                caught = bool(seen.get(key))       # a repairer cannot re-add; an extractor could
            else:
                bucket = "visible" if e.get("visible_by_law") else "invisible"
                caught = not seen.get(key)         # the spurious edge is gone
            sub[bucket]["caught" if caught else "missed"] += 1
        injected_missing = {(e["s"], e["p"], e["o"]) for e in inj if e["damage"] == "MISSING"}
        wrongly_broken = sum(1 for key, tf in tfacts.items() if per_fact[tf["id"]]["status"] == "missed" and tf["id"] not in fault_facts and key not in injected_missing)
        known_removed = sum(1 for tf in truth["facts"] if fault_facts.get(tf["id"]) == "law_violation" and per_fact[tf["id"]]["known_fault"] == "removed")
        repair = {"visible": dict(sub["visible"]), "invisible": dict(sub["invisible"]), "beyond_reach": dict(sub["beyond_reach"]), "anachronism_injected": dict(anach_inj),
                  "wrongly_broken": wrongly_broken, "collateral": len(collateral), "known_violations_removed": known_removed}

    verdict = {
        "truth": truth["id"], "truth_sha256": truth["sha256"],
        "candidate": cand["candidate"], "journal_sha256": journal["sha256"] if journal else None,
        "dimensions": dims, "repair": repair,
        "facts": dict(sorted(per_fact.items())),
        "extra": sorted(extra, key=lambda e: (e["p"], e["s"], e["o"])),
        "anachronism": sorted(anach, key=lambda a: a["node"]),
        "collateral": sorted(collateral),
    }
    verdict["sha256"] = canon.sha256({k: v for k, v in verdict.items() if k != "sha256"})
    return verdict


def main():
    argv = sys.argv[1:]
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--journal")]
    if len(args) != 3:
        sys.exit(__doc__)
    truth = json.load(open(args[0], encoding="utf-8"))
    cand = json.load(open(args[1], encoding="utf-8"))
    journal = json.load(open(sys.argv[sys.argv.index("--journal") + 1], encoding="utf-8")) if "--journal" in sys.argv else None
    v = judge(truth, cand, journal)
    canon.write(args[2], v)
    for p, d in v["dimensions"].items():
        print(p, json.dumps(d, ensure_ascii=False)[:200])
    if v["repair"]:
        print("repair", json.dumps(v["repair"], ensure_ascii=False))


if __name__ == "__main__":
    main()
