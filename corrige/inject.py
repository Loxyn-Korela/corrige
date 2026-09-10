"""The injector: takes a truth, breaks it with known damages, writes the damaged
graph and a sealed journal.

    python3 -m corrige.inject <truth.json> <out-dir> --damage repeals:SPURIOUS_EDGE=0.10 \
        --damage nodes:ANACHRONISM=0.02 --damage repeals:MISSING=0.05 --visible 0.5 --seed-file seed.txt

Denominators are named: repeals|amends|based_on for SPURIOUS_EDGE and MISSING
(share of the facts of that relation), nodes for ANACHRONISM (share of nodes
with date_document_status ok). --visible applies to SPURIOUS_EDGE only. The
seed file's sha256 is published in the journal; the journal's own sha256 is
what a candidate must name. Exact counts, never approximate: the injector
verifies the visible share with the laws and refuses to write otherwise.
"""
import sys, json, random, hashlib, pathlib, collections, datetime
from . import canon, laws
from . import laws_icij


def _laws(truth_or_graph):
    """The law module a truth declares; EUR-Lex by default."""
    return laws_icij if (truth_or_graph or {}).get("laws_module") == "icij" else laws

RELS = ("repeals", "amends", "based_on")          # EUR-Lex; any truth's own relations are accepted


def parse_damage(args):
    out = []
    for i, a in enumerate(args):
        if a == "--damage":
            spec = args[i + 1]
            den, rest = spec.split(":")
            kind, rate = rest.split("=")
            out.append((den, kind, rate))
    return out


def inject(truth, damages, visible=None, seed=b"", duplicate=False):
    """damages: [(denominator, kind, rate)], rate and visible as strings ("0.10", "1/2"):
    the journal keeps them as written, canonical JSON has no floats."""
    visible_s = visible
    visible = _exact_rate(visible) if visible is not None else None
    rng = random.Random(hashlib.sha256(seed).hexdigest())
    nodes = {n["id"]: dict(n) for n in truth["nodes"]}
    facts = {(f["s"], f["p"], f["o"]): dict(f) for f in truth["facts"]}
    fault_facts = {k["fact"] for k in truth.get("known_registry_faults", []) if "fact" in k}
    injected = []
    # node damages first, so that the visibility of a spurious edge is judged on the final nodes
    ORDER = {"ANACHRONISM": 0, "WRONG_VALUE": 0, "WRONG_LABEL": 0, "MERGE": 1, "SPLIT": 1}
    damages = sorted(damages, key=lambda d: ORDER.get(d[1], 2))
    L = _laws(truth)
    RELS_T = tuple(truth.get("world", {})) or RELS      # the relations this truth declares
    idx = L.Index(list(facts.values()))
    for den, kind, rate in damages:
        rate = _exact_rate(rate)
        if kind == "SPURIOUS_EDGE":
            if den not in RELS_T: raise ValueError(f"SPURIOUS_EDGE needs one of {RELS_T} as denominator")
            n = round(rate * sum(1 for f in facts.values() if f["p"] == den))
            n_vis = round(visible * n) if visible is not None else None
            ok_nodes = [nid for nid, nd in nodes.items() if nd.get("date_document_status", "ok") == "ok" and not nd.get("gap")]
            existing = set(facts)
            made = {"vis": 0, "inv": 0}
            tries = 0
            while (made["vis"] + made["inv"]) < n:
                tries += 1
                if tries > 200000: raise RuntimeError("cannot reach the requested visible share")
                s, o = rng.choice(ok_nodes), rng.choice(ok_nodes)
                if s == o or (s, den, o) in existing: continue
                v = L.violations({"s": s, "p": den, "o": o}, nodes, idx)
                bucket = "vis" if v else "inv"
                if n_vis is not None and ((bucket == "vis" and made["vis"] >= n_vis) or (bucket == "inv" and made["inv"] >= n - n_vis)):
                    continue
                made[bucket] += 1
                key = (s, den, o); existing.add(key)
                facts[key] = {"s": s, "p": den, "o": o, "injected": True}
                injected.append({"damage": "SPURIOUS_EDGE", "s": s, "p": den, "o": o, "visible_by_law": v})
            if n_vis is not None and made["vis"] != n_vis:
                raise RuntimeError(f"visible share not met: {made['vis']} of {n_vis}")
        elif kind in ("CYCLE", "CYCLE_BLIND"):
            # a spurious repeals b->a mirroring a true a->b: both edges violate L4 (two acts do not
            # repeal each other) and one of them is false. CYCLE: the mirror also violates a one-edge
            # law, so the choice is INFORMED. CYCLE_BLIND: the mirror violates nothing else, so the
            # two edges are indistinguishable and the choice is BLIND — the experiment that can fail.
            if den != "repeals": raise ValueError("a cycle is dosed on repeals")
            blind = kind == "CYCLE_BLIND"
            pool = []
            for k, f in facts.items():
                if f["p"] != "repeals" or f.get("injected") or f.get("id") in fault_facts: continue
                if (k[2], "repeals", k[0]) in facts: continue
                v = L.violations({"s": k[2], "p": "repeals", "o": k[0]}, nodes)
                if bool(v) != blind: pool.append(k)
            pool.sort()
            n = round(rate * len(pool)) if rate <= 1 else min(int(rate), len(pool))
            for (a, _, b) in rng.sample(pool, min(n, len(pool))):
                key = (b, "repeals", a)
                facts[key] = {"s": b, "p": "repeals", "o": a, "injected": True}
                injected.append({"damage": "SPURIOUS_EDGE", "s": b, "p": "repeals", "o": a,
                                 "visible_by_law": ["L4"] if blind else L.violations({"s": b, "p": "repeals", "o": a}, nodes) + ["L4"],
                                 "arm": "blind" if blind else "informed",
                                 "cycle_with": facts[(a, "repeals", b)]["id"]})
        elif kind == "MISSING":
            if den not in RELS_T: raise ValueError(f"MISSING needs one of {RELS_T} as denominator")
            pool = sorted(k for k, f in facts.items() if f["p"] == den and not f.get("injected") and f.get("id") not in fault_facts)
            n = round(rate * len(pool))
            for key in rng.sample(pool, n):
                f = facts.pop(key)
                injected.append({"damage": "MISSING", "s": key[0], "p": key[1], "o": key[2], "truth_fact": f["id"]})
        elif kind == "RIVAL":
            # a second edge of a relation that must be unique on its target: both edges then violate
            # the two-edge law, one of them is false, and nothing else separates them. On ICIJ this is
            # gamma_3 — an entity has at most one sole director — and it exists in the data already.
            targets = collections.Counter(f["o"] for f in facts.values() if f["p"] == den and not f.get("injected"))
            pool = sorted(t for t, c in targets.items() if c == 1)
            sources = sorted({f["s"] for f in facts.values() if f["p"] == den})
            n = round(rate * len(pool)) if rate <= 1 else min(int(rate), len(pool))
            for t in rng.sample(pool, min(n, len(pool))):
                true_edge = next(f for f in facts.values() if f["p"] == den and f["o"] == t and not f.get("injected"))
                cand = [x for x in rng.sample(sources, min(30, len(sources))) if x != true_edge["s"] and x != t and (x, den, t) not in facts]
                if not cand: continue
                s_ = cand[0]; key = (s_, den, t)
                facts[key] = {"s": s_, "p": den, "o": t, "injected": True}
                injected.append({"damage": "SPURIOUS_EDGE", "s": s_, "p": den, "o": t,
                                 "visible_by_law": ["two-edge law"], "arm": "blind",
                                 "cycle_with": true_edge["id"]})
        elif kind == "WRONG_LABEL":
            # the act's type label contradicts its CELEX: 32019R1020 labelled Directive.
            # This is the damage a label repair can undo, and the only one that exercises it.
            if den != "nodes": raise ValueError("WRONG_LABEL is dosed on nodes")
            pool = sorted(nid for nid, nd in nodes.items() if laws.type_label(nd.get("celex")))
            n = round(rate * len(pool))
            others = sorted(set(laws.CELEX_TYPE.values()))
            for nid in rng.sample(pool, n):
                true_label = laws.type_label(nodes[nid]["celex"])
                wrong = rng.choice([x for x in others if x != true_label])
                injected.append({"damage": "WRONG_LABEL", "node": nid, "truth_label": true_label, "injected_label": wrong, "visible_by_law": ["L6"]})
                nodes[nid]["type_label_injected"] = wrong
        elif kind == "WRONG_VALUE":
            # a property is altered: the CELEX itself, which every identity rests on
            if den != "nodes": raise ValueError("WRONG_VALUE is dosed on nodes")
            pool = sorted(nid for nid, nd in nodes.items() if nd.get("celex"))
            n = round(rate * len(pool))
            for nid in rng.sample(pool, n):
                old = nodes[nid]["celex"]
                new = old[:-1] + str((int(old[-1]) + 1) % 10) if old[-1].isdigit() else old + "X"
                injected.append({"damage": "WRONG_VALUE", "node": nid, "property": "celex", "truth_value": old, "injected_value": new})
                nodes[nid]["celex"] = new
        elif kind == "MERGE":
            # two acts become one node: B's edges are moved onto A, B disappears
            if den != "nodes": raise ValueError("MERGE is dosed on nodes")
            deg = collections.Counter()
            for f in facts.values(): deg[f["s"]] += 1; deg[f["o"]] += 1
            pool = sorted(nid for nid in nodes if 1 <= deg[nid] <= 6)
            n = round(rate * len(pool)) // 2
            taken = set()
            for _ in range(n):
                cand = [x for x in rng.sample(pool, min(40, len(pool))) if x not in taken]
                if len(cand) < 2: break
                a_, b_ = cand[0], cand[1]; taken |= {a_, b_}
                moved = []
                for key in [k for k in list(facts) if b_ in (k[0], k[2])]:
                    f = facts.pop(key)
                    nk = (a_ if f["s"] == b_ else f["s"], f["p"], a_ if f["o"] == b_ else f["o"])
                    if nk[0] != nk[2]: facts[nk] = {"s": nk[0], "p": nk[1], "o": nk[2], "injected": True}
                    moved.append(f.get("id"))
                nodes.pop(b_, None)
                injected.append({"damage": "MERGE", "kept": a_, "absorbed": b_, "moved_facts": moved})
        elif kind == "SPLIT":
            # one act becomes two nodes: half its edges move to a twin
            if den != "nodes": raise ValueError("SPLIT is dosed on nodes")
            deg = collections.Counter()
            for f in facts.values(): deg[f["s"]] += 1; deg[f["o"]] += 1
            pool = sorted(nid for nid in nodes if 2 <= deg[nid] <= 8)
            n = round(rate * len(pool))
            for nid in rng.sample(pool, min(n, len(pool))):
                twin = nid + "#split"
                nodes[twin] = dict(nodes[nid], id=twin)
                keys = [k for k in list(facts) if nid in (k[0], k[2])]
                moved = []
                for key in keys[1::2]:
                    f = facts.pop(key)
                    nk = (twin if f["s"] == nid else f["s"], f["p"], twin if f["o"] == nid else f["o"])
                    facts[nk] = {"s": nk[0], "p": nk[1], "o": nk[2], "injected": True}
                    moved.append(f.get("id"))
                injected.append({"damage": "SPLIT", "node": nid, "twin": twin, "moved_facts": moved})
        else:
            raise ValueError(f"unknown damage {kind}")
    if duplicate:
        key = sorted(k for k, f in facts.items() if not f.get("injected"))[0]
        injected.append({"damage": "DUPLICATE", "s": key[0], "p": key[1], "o": key[2]})
    for nd in nodes.values():                       # the type label: from the CELEX, unless injected
        nd["type_label"] = nd.pop("type_label_injected", None) or laws.type_label(nd.get("celex"))
    graph = {"truth_sha256": truth["sha256"], "laws_module": truth.get("laws_module"),
             "nodes": [nodes[k] for k in sorted(nodes)],
             "facts": [{"s": f["s"], "p": f["p"], "o": f["o"]} for k, f in sorted(facts.items())]}
    if duplicate:
        graph["facts"].append({"s": key[0], "p": key[1], "o": key[2]})
    cnt = collections.Counter()
    for e in injected:
        cnt[("SPURIOUS_EDGE/" + ("visible" if e["visible_by_law"] else "invisible")) if e["damage"] == "SPURIOUS_EDGE" else e["damage"]] += 1
    journal = {"truth_sha256": truth["sha256"], "seed_sha256": hashlib.sha256(seed).hexdigest(),
               "damages": [{"denominator": d, "kind": k, "rate": r} for d, k, r in damages], "visible": visible_s,
               "injected": injected, "counts": dict(sorted(cnt.items()))}
    journal["sha256"] = canon.sha256({k: v for k, v in journal.items() if k != "sha256"})
    graph["journal_sha256"] = journal["sha256"]
    return graph, journal


def _exact_rate(rate):
    if isinstance(rate, (int, float)): return float(rate)
    if rate.isdigit(): return int(rate)          # a plain count, for a small population
    if "/" in rate:
        a, b = rate.split("/"); return int(a) / int(b)
    return float(rate)


def main():
    args = sys.argv[1:]
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or not args[i - 1].startswith("--"))]
    if len(pos) != 2: sys.exit(__doc__)
    truth = json.load(open(pos[0], encoding="utf-8"))
    out = pathlib.Path(pos[1]); out.mkdir(parents=True, exist_ok=True)
    damages = parse_damage(args)
    visible = args[args.index("--visible") + 1] if "--visible" in args else None
    seed = pathlib.Path(args[args.index("--seed-file") + 1]).read_bytes() if "--seed-file" in args else b""
    graph, journal = inject(truth, damages, visible, seed, duplicate="--duplicate" in args)
    canon.write(out / "graph.json", graph); canon.write(out / "journal.json", journal)
    print(json.dumps(journal["counts"]), "journal sha256", journal["sha256"][:16])


if __name__ == "__main__":
    main()
