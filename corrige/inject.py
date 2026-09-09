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

RELS = ("repeals", "amends", "based_on")


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
    for den, kind, rate in damages:
        rate = _exact_rate(rate)
        if kind == "SPURIOUS_EDGE":
            if den not in RELS: raise ValueError("SPURIOUS_EDGE needs a relation denominator")
            n = round(rate * sum(1 for f in facts.values() if f["p"] == den))
            n_vis = round(visible * n) if visible is not None else None
            ok_nodes = [nid for nid, nd in nodes.items() if nd.get("date_document_status") == "ok" and not nd.get("gap")]
            existing = set(facts)
            made = {"vis": 0, "inv": 0}
            tries = 0
            while (made["vis"] + made["inv"]) < n:
                tries += 1
                if tries > 200000: raise RuntimeError("cannot reach the requested visible share")
                s, o = rng.choice(ok_nodes), rng.choice(ok_nodes)
                if s == o or (s, den, o) in existing: continue
                v = laws.violations({"s": s, "p": den, "o": o}, nodes)
                bucket = "vis" if v else "inv"
                if n_vis is not None and ((bucket == "vis" and made["vis"] >= n_vis) or (bucket == "inv" and made["inv"] >= n - n_vis)):
                    continue
                made[bucket] += 1
                key = (s, den, o); existing.add(key)
                facts[key] = {"s": s, "p": den, "o": o, "injected": True}
                injected.append({"damage": "SPURIOUS_EDGE", "s": s, "p": den, "o": o, "visible_by_law": v})
            if n_vis is not None and made["vis"] != n_vis:
                raise RuntimeError(f"visible share not met: {made['vis']} of {n_vis}")
        elif kind == "MISSING":
            if den not in RELS: raise ValueError("MISSING needs a relation denominator")
            pool = sorted(k for k, f in facts.items() if f["p"] == den and f["id"] not in fault_facts and not f.get("injected"))
            n = round(rate * len(pool))
            for key in rng.sample(pool, n):
                f = facts.pop(key)
                injected.append({"damage": "MISSING", "s": key[0], "p": key[1], "o": key[2], "truth_fact": f["id"]})
        elif kind == "ANACHRONISM":
            if den != "nodes": raise ValueError("ANACHRONISM is dosed on nodes")
            pool = sorted(nid for nid, nd in nodes.items() if nd.get("date_document_status") == "ok")
            n = round(rate * len(pool))
            for nid in rng.sample(pool, n):
                d = datetime.date.fromisoformat(nodes[nid]["date_document"])
                new = d.replace(year=d.year + 1).isoformat()
                injected.append({"damage": "ANACHRONISM", "node": nid, "truth_date": nodes[nid]["date_document"], "injected_date": new})
                nodes[nid]["date_document"] = new
        else:
            raise ValueError(f"unknown damage {kind}")
    if duplicate:
        key = sorted(k for k, f in facts.items() if not f.get("injected"))[0]
        injected.append({"damage": "DUPLICATE", "s": key[0], "p": key[1], "o": key[2]})
    graph = {"truth_sha256": truth["sha256"],
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
