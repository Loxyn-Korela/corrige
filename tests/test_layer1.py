#!/usr/bin/env python3
"""The eleven planted-fault tests of layer 1, on the toy truth. Exit 1 on the first failure."""
import sys, json, copy, pathlib, datetime
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from corrige import judge as J, inject as I, witnesses as W, canon, laws

truth = json.load(open(ROOT / "truths" / "truth-eurlex-relations-2026-09-09-toy-200.json", encoding="utf-8"))
tnodes = {n["id"]: n for n in truth["nodes"]}
fault_ids = {k["fact"] for k in truth["known_registry_faults"] if "fact" in k}
clean = [f for f in truth["facts"] if f["id"] not in fault_ids]
N = {p: sum(1 for f in clean if f["p"] == p) for p in ("repeals", "amends", "based_on")}


def perfect(name="perfect"):
    return {"candidate": {"name": name, "version": "t", "code_sha256": None, "params": {}, "seed": None},
            "truth_sha256": truth["sha256"], "journal_sha256": None,
            "nodes": copy.deepcopy(truth["nodes"]),
            "facts": [{"s": f["s"], "p": f["p"], "o": f["o"]} for f in truth["facts"]], "abstained": []}


def run(cand, journal=None):
    return J.judge(truth, cand, journal)


results = []
def check(name, cond, detail=""):
    results.append((name, cond))
    print(("ok    " if cond else "FAIL  ") + name + (("  — " + detail) if detail and not cond else ""))


# T0: the perfect candidate scores 1 everywhere, undefined nowhere it should not
v = run(perfect())
d = v["dimensions"]
check("T0 perfect: recall 1 on the three relations", all(d[p]["recall"]["num"] == d[p]["recall"]["den"] > 0 for p in N))
check("T0 perfect: precision 1 on closed relations, undefined on based_on",
      d["repeals"]["precision"]["num"] == d["repeals"]["precision"]["den"] and d["amends"]["precision"]["num"] == d["amends"]["precision"]["den"] and d["based_on"]["precision"] == "undefined (open relation)")
check("T0 perfect: anachronism 0", d["nodes"]["anachronism"]["num"] == 0 and d["nodes"]["anachronism"]["den"] > 0)

# T1: one true relation removed from the candidate
c = perfect(); f0 = next(f for f in clean if f["p"] == "repeals")
c["facts"] = [x for x in c["facts"] if (x["s"], x["p"], x["o"]) != (f0["s"], f0["p"], f0["o"])]
v = run(c); d = v["dimensions"]["repeals"]
check("T1 missed = 1, recall = (N-1)/N, false = 0", d["recall"]["num"] == N["repeals"] - 1 and d["recall"]["den"] == N["repeals"] and d["false"] == 0 and v["facts"][f0["id"]]["status"] == "missed")

# T2: an invented repeals between two existing nodes, outside known_gaps
c = perfect(); ids = [n["id"] for n in truth["nodes"] if not n.get("gap") and n["celex"]]
existing = {(f["s"], f["p"], f["o"]) for f in truth["facts"]}
pair = next((a, b) for a in ids for b in ids if a != b and (a, "repeals", b) not in existing)
c["facts"].append({"s": pair[0], "p": "repeals", "o": pair[1]})
v = run(c); d = v["dimensions"]["repeals"]
check("T2 false = 1, precision = N/(N+1)", d["false"] == 1 and d["precision"]["num"] == N["repeals"] and d["precision"]["den"] == N["repeals"] + 1 and d["out_of_coverage"] == 0)

# T3: date_document of one ok node advanced by a year in the candidate
c = perfect(); nd = next(n for n in c["nodes"] if n["date_document_status"] == "ok" and any(f["s"] == n["id"] for f in clean))
dd = datetime.date.fromisoformat(nd["date_document"]); nd["date_document"] = dd.replace(year=dd.year + 1).isoformat()
v = run(c)
ftouch = next(f for f in clean if f["s"] == nd["id"])
check("T3 anachronism = 1 on the node, its fact stays found", v["dimensions"]["nodes"]["anachronism"]["num"] == 1 and v["facts"][ftouch["id"]]["status"] == "found")

# T4: a based_on (open relation) asserted by the candidate and absent from the truth
c = perfect(); pair = next((a, b) for a in ids for b in ids if a != b and (a, "based_on", b) not in existing)
c["facts"].append({"s": pair[0], "p": "based_on", "o": pair[1]})
v = run(c); d = v["dimensions"]
check("T4 out_of_coverage = 1 on based_on, false = 0, closed precisions unchanged",
      d["based_on"]["out_of_coverage"] == 1 and d["based_on"]["false"] == 0 and d["repeals"]["precision"]["num"] == d["repeals"]["precision"]["den"] and d["amends"]["precision"]["num"] == d["amends"]["precision"]["den"])

# T5: a repeals aimed at a known_gaps node
gap = truth["known_gaps"][0]["node"]; c = perfect()
src = next(n["id"] for n in truth["nodes"] if n["celex"] and (n["id"], "repeals", gap) not in existing and n["id"] != gap)
c["facts"].append({"s": src, "p": "repeals", "o": gap})
v = run(c); d = v["dimensions"]["repeals"]
check("T5 gap target -> out_of_coverage, not false", d["out_of_coverage"] == 1 and d["false"] == 0)

# T6: a true edge duplicated in the injected graph, three candidates
graph, journal = I.inject(truth, [], seed=b"t6", duplicate=True)
dup = next(e for e in journal["injected"] if e["damage"] == "DUPLICATE"); key = (dup["s"], dup["p"], dup["o"])
tid = next(f["id"] for f in truth["facts"] if (f["s"], f["p"], f["o"]) == key)
def cand_from(graph, facts, name):
    c = W.dumb_baseline(graph); c["candidate"]["name"] = name; c["facts"] = facts; return c
both = cand_from(graph, list(graph["facts"]), "keeps-both")
one_a = list(graph["facts"]); one_a.remove({"s": key[0], "p": key[1], "o": key[2]})
one = cand_from(graph, one_a, "removes-one")
none_ = cand_from(graph, [f for f in graph["facts"] if (f["s"], f["p"], f["o"]) != key], "removes-both")
vb, vo, vn = run(both, journal), run(one, journal), run(none_, journal)
p = key[1]
check("T6 keeps both: found, duplicate = 1, precision counts it", vb["facts"][tid]["status"] == "found" and vb["dimensions"][p]["duplicate"] == 1 and vb["dimensions"][p]["precision"]["den"] == vb["dimensions"][p]["precision"]["num"] + 1 if p != "based_on" else vb["dimensions"][p]["duplicate"] == 1)
vo2 = run(cand_from(graph, one_a[::-1], "removes-one"), journal)   # the "other" copy removed: same name, different order
def body(v): return {k: x for k, x in v.items() if k not in ("sha256", "candidate")}
check("T6 removes one: found, duplicate = 0; original or copy indistinguishable (same verdict body)", vo["facts"][tid]["status"] == "found" and vo["dimensions"][p]["duplicate"] == 0 and canon.sha256(body(vo)) == canon.sha256(body(vo2)) and vo["sha256"] == vo2["sha256"])
check("T6 removes both: missed = 1", vn["facts"][tid]["status"] == "missed")

# T7: deletion of a node carrying 3 true edges
deg = {}
for f in clean: deg[f["s"]] = deg.get(f["s"], 0) + 1; deg[f["o"]] = deg.get(f["o"], 0) + 1
node3 = next(n for n, k in sorted(deg.items()) if k >= 3)
c = perfect(); c["facts"] = [x for x in c["facts"] if node3 not in (x["s"], x["o"])]; c["deleted_nodes"] = [node3]
lost = sum(1 for f in clean if node3 in (f["s"], f["o"]))
v = run(c)
check(f"T7 collateral = {lost} (edges of the deleted node), recall falls by that much", v["dimensions"]["collateral"] == lost and sum(v["dimensions"][p]["recall"]["den"] - v["dimensions"][p]["recall"]["num"] for p in N) == lost)

# T8: empty candidate; all-abstained candidate
c = perfect(); c["facts"] = []; c["nodes"] = []
v = run(c); d = v["dimensions"]
check("T8 empty: precision undefined, recall 0", d["repeals"]["precision"]["value"] == "undefined" and d["repeals"]["recall"]["num"] == 0 and d["nodes"]["anachronism"].startswith("undefined"))
c = perfect(); c["abstained"] = c["facts"]; c["facts"] = []
v = run(c); d = v["dimensions"]
check("T8 all-abstained: silence 1, precision undefined", all(d[p]["silence"]["num"] == d[p]["silence"]["den"] for p in N) and d["repeals"]["precision"]["value"] == "undefined")

# T9: same candidate, facts shuffled -> identical verdict and sha
import random
c1 = perfect(); c2 = perfect(); random.Random(3).shuffle(c2["facts"]); random.Random(4).shuffle(c2["nodes"])
v1, v2 = run(c1), run(c2)
check("T9 order-invariant verdict", v1["sha256"] == v2["sha256"])

# T10: injection --visible 1/2 on 40 spurious repeals edges (rate 40/N), sealed seed
graph, journal = I.inject(truth, [("repeals", "SPURIOUS_EDGE", f"40/{sum(1 for f in truth['facts'] if f['p']=='repeals')}")], visible="1/2", seed=b"sealed-seed-t10")
vis = sum(1 for e in journal["injected"] if e["visible_by_law"]); tot = len(journal["injected"])
check("T10 journal: exactly 20 visible of 40, verified by the laws", tot == 40 and vis == 20)
gnodes = {n["id"]: n for n in graph["nodes"]}
check("T10 every visible edge violates a law, no invisible one does", all(bool(laws.violations(e, gnodes)) == bool(e["visible_by_law"]) for e in journal["injected"]))
vr = run(W.rule_without_model(graph), journal); r = vr["repair"]
census = sum(1 for k in truth["known_registry_faults"] if k["kind"] == "law_violation")
check("T10 rule-without-model: catches the 20 visible, 0 invisible, wrongly_broken 0, known_violations_removed = census",
      r["visible"].get("caught", 0) == 20 and r["invisible"].get("caught", 0) == 0 and r["wrongly_broken"] == 0 and r["known_violations_removed"] == census,
      json.dumps(r))
vd = run(W.dumb_baseline(graph), journal)
check("T10 dumb baseline: catches nothing", vd["repair"]["visible"].get("caught", 0) == 0 and vd["repair"]["invisible"].get("caught", 0) == 0)

# T11: a known-fault fact removed from the candidate
kfact = next(k["fact"] for k in truth["known_registry_faults"] if k["kind"] == "empty_target")
kf = next(f for f in truth["facts"] if f["id"] == kfact)
c = perfect(); c["facts"] = [x for x in c["facts"] if (x["s"], x["p"], x["o"]) != (kf["s"], kf["p"], kf["o"])]
v0, v = run(perfect()), run(c)
check("T11 known fault removed: known_fault = corrected, denominators unchanged",
      v["facts"][kfact]["known_fault"] == "corrected" and all(v["dimensions"][p]["recall"]["den"] == v0["dimensions"][p]["recall"]["den"] for p in N) and v["dimensions"]["based_on"]["false"] == 0)

# permanent calibration: a candidate naming another truth is refused
c = perfect(); c["truth_sha256"] = "0" * 64
try:
    run(c); check("calibration: foreign truth refused", False)
except ValueError:
    check("calibration: foreign truth refused", True)
check("calibration: truth sha256 recomputes", canon.sha256({"nodes": truth["nodes"], "facts": truth["facts"]}) == truth["sha256"])

bad = [n for n, ok in results if not ok]
print(f"{len(results) - len(bad)}/{len(results)} assertions hold")
sys.exit(1 if bad else 0)
