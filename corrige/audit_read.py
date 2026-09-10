"""Read the filled audit booklets, compute the truth's error rate per relation and the
agreement between auditors on the shared facts, and write the audit into the truth file.

    .venv-pdf/bin/python -m corrige.audit_read <truth.json> <audit dir> [--write]

Reads audit-<name>.pdf for every auditor named in audit-200.json (form fields r_<fact>
= oui|non|illisible, art_<fact> = free text). Without --write, only prints the report.
With --write, sets truth.audit (sample, answers, error rate, agreement, date) and turns
truth.status from "unaudited" to "audited"; the truth's sha256 does not change (it
covers nodes and facts only) — the audit is metadata about that same frozen truth.
"""
import sys, json, pathlib, collections, datetime
from pypdf import PdfReader
from . import canon


def read_booklet(path):
    r = PdfReader(str(path))
    fields = r.get_fields() or {}
    answers = {}
    for name, fld in fields.items():
        v = fld.get("/V")
        if v is None:
            continue
        v = str(v).lstrip("/")
        if name.startswith("r_") and v in ("oui", "non", "illisible"):
            fid = "f-" + name[3:] if name[2] == "f" and name[3:].isdigit() else name[2:]
            answers.setdefault(fid, {})["answer"] = v
        elif name.startswith("art_") and v.strip():
            fid = "f-" + name[5:] if name[4] == "f" and name[5:].isdigit() else name[4:]
            answers.setdefault(fid, {})["article"] = v.strip()
    return answers


def report(truth, rec, per_auditor, notes=None):
    notes = notes or {}
    facts = {f["id"]: f for f in truth["facts"]}
    common = set(rec["common"])
    # one verdict per fact: majority on shared facts, the single auditor elsewhere
    votes = collections.defaultdict(list)
    for aud, ans in per_auditor.items():
        for fid, a in ans.items():
            if "answer" in a:
                votes[fid].append((aud, a["answer"], a.get("article", "")))
    for c in notes.get("corrections", []):          # a revision after review, with its reason; the PDF is left untouched
        if c["fact"] in votes:
            votes[c["fact"]] = [(a, c["to"], c.get("article", "")) for a, _, _ in votes[c["fact"]]]
    verdict = {}
    for fid in rec["facts"]:
        v = votes.get(fid, [])
        if not v:
            verdict[fid] = "unanswered"; continue
        c = collections.Counter(x[1] for x in v)
        top, n = c.most_common(1)[0]
        verdict[fid] = top if (n > len(v) / 2) else "disagreement"
    by_rel = collections.defaultdict(collections.Counter)
    for fid, vd in verdict.items():
        by_rel[facts[fid]["p"]][vd] += 1
    rates = {}
    for p, c in by_rel.items():
        judged = c["oui"] + c["non"]
        rates[p] = {"oui": c["oui"], "non": c["non"], "illisible": c["illisible"], "disagreement": c["disagreement"], "unanswered": c["unanswered"],
                    "error_rate": {"num": c["non"], "den": judged, "value": f"{c['non']/judged:.4f}" if judged else "undefined"}}
    # agreement on shared facts
    agree = collections.Counter()
    for fid in common:
        v = [x[1] for x in votes.get(fid, [])]
        if len(v) >= 2:
            agree["unanimous" if len(set(v)) == 1 else "split"] += 1
        else:
            agree["not enough answers"] += 1
    nons = [(fid, facts[fid]["p"], [x for x in votes[fid]]) for fid in rec["facts"] if verdict.get(fid) == "non"]
    cats = notes.get("categories", {})
    by_cat = collections.Counter(cats.get(fid, {}).get("category", "not categorised") for fid, _, _ in nons)
    # R6: never a pooled rate. The sample is stratified (70/70/60) while the truth is not
    # (14,411 / 64,290 / 410,522): a pooled figure would be an artefact of the stratification.
    per_rel = {}
    for p, r in rates.items():
        den = r["oui"] + r["non"]
        cats_p = collections.Counter(cats.get(fid, {}).get("category", "not categorised") for fid, pp, _ in nons if pp == p)
        per_rel[p] = {"read": den,
                      **{k: {"num": cats_p.get(k, 0), "den": den, "value": f"{cats_p.get(k,0)/den:.4f}" if den else "undefined"}
                         for k in ("registry_wrong", "not_in_text", "requalified")}}
    return {"verdict": verdict, "rates": rates, "agreement_on_shared": dict(agree), "non_facts": nons,
            "by_category": dict(by_cat), "judged": sum(r["oui"] + r["non"] for r in rates.values()),
            "per_relation": per_rel,
            "corrections": notes.get("corrections", []),
            "answered": sum(1 for v in verdict.values() if v != "unanswered"), "total": len(rec["facts"])}


def main():
    argv = sys.argv[1:]
    pos = [a for a in argv if not a.startswith("--")]
    truth_path, out = pathlib.Path(pos[0]), pathlib.Path(pos[1])
    truth = json.load(open(truth_path, encoding="utf-8"))
    rec = json.load(open(out / "audit-200.json", encoding="utf-8"))
    if rec["truth_sha256"] != truth["sha256"]:
        sys.exit("the audit sample was drawn on another truth (sha256 mismatch)")
    per = {}
    for aud in rec["auditors"]:
        p = out / f"audit-{aud}.pdf"
        per[aud] = read_booklet(p) if p.exists() else {}
        print(f"{aud}: {sum(1 for a in per[aud].values() if 'answer' in a)} answers of {len(rec['per_auditor'][aud])}")
    notes_path = out / "answers-notes.json"
    notes = json.load(open(notes_path, encoding="utf-8")) if notes_path.exists() else {}
    rep = report(truth, rec, per, notes)
    print(f"answered {rep['answered']}/{rep['total']}")
    for p, r in rep["rates"].items():
        print(f"  {p}: oui {r['oui']} · non {r['non']} · illisible {r['illisible']} · disagreement {r['disagreement']} · error rate {r['error_rate']['value']} ({r['error_rate']['num']}/{r['error_rate']['den']})")
    print("  agreement on shared facts:", rep["agreement_on_shared"])
    print("  by category:", rep["by_category"])
    for p, r in rep["per_relation"].items():
        print(f"  {p} ({r['read']} read): " + " · ".join(f"{k} {r[k]['num']}" for k in ("registry_wrong", "not_in_text", "requalified")))
    for fid, p, v in rep["non_facts"]:
        print(f"  NON {fid} ({p}): " + " | ".join(f"{a}: {ans} {art}" for a, ans, art in v))
    if "--write" in argv:
        truth["audit"] = {"sample_name": rec["sample_name"], "sample": len(rec["facts"]), "sample_sha256": rec["sha256"],
                          "method": "each fact read against the act's own text by a human, no model; a NO is not a registry error until it is categorised (see category_meaning); revisions after review are recorded in answers-notes.json with their reason, the booklet itself is left as it was ticked",
                          "date": datetime.date.today().isoformat(), "auditors": [a for a in rec["auditors"] if per.get(a)],
                          "answered": rep["answered"], "judged": rep["judged"], "rates": rep["rates"],
                          "agreement_on_shared": rep["agreement_on_shared"], "by_category": rep["by_category"],
                          "per_relation": rep["per_relation"],
                          "no_pooled_rate": "the sample is stratified (70 repeals / 70 amends / 60 based_on) while the truth is not (14,411 / 64,290 / 410,522): a rate over all relations would be an artefact of the stratification, and rule R6 forbids it. Read per relation, with the count of facts read.",
                          "category_meaning": notes.get("category_meaning", {}), "corrections": rep["corrections"],
                          "categories": notes.get("categories", {}), "verdicts": rep["verdict"],
                          "reserves": ["one auditor, who also built the truth: no agreement between readers measured yet; the 30 shared facts are still open, and both revisions made after review went from NO to YES, the direction that raises the figure",
                                       "27 to 33 facts per relation: a wide interval, a first reading rather than a rate",
                                       "two facts (f-483026, f-477942) rest on the auditor's reading of the titles: the texts of a 1954 ECSC decision and a 1970 Euratom regulation are served neither by EUR-Lex nor by Cellar",
                                       "the sample excludes the faults the register already declares (sentinel dates, empty targets): the rate is that of ordinary facts"]}
        truth["status"] = "audited" if rep["answered"] == rep["total"] else "partially_audited"
        canon.write(truth_path, truth)
        print("written:", truth["status"])


if __name__ == "__main__":
    main()
