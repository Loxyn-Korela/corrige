"""Human audit of the truth: draw the audit sample, write one PDF-ready HTML per
auditor. The auditors read the TEXT of the acts, never the "relationships"
box of EUR-Lex (that box is Cellar, the very thing being checked).

    python3 -m corrige.audit <truth.json> <collection dir> <out dir> --auditors "Sébastien,Coralie,Yoline" [--n 200 --shared 30 --seed 11]

Writes audit-200.json (the sample, sealed), and audit-<name>.html per auditor
(convert with Chrome: --headless --print-to-pdf). Answers come back as a list
"fact-id: OUI article N | NON | ILLISIBLE", one per line, e-mailed.
"""
import sys, json, random, pathlib, re, html
from . import canon, truth_eurlex as T

Q = {
    "repeals": ("abroge", "Le texte de A dit-il que B est abrogé ?",
                "Cherchez dans les derniers articles de A une phrase du type « Le règlement … est abrogé » / « … is repealed »."),
    "amends": ("modifie", "Le texte de A dit-il qu'il modifie B ?",
               "Souvent dans le titre de A (« modifiant le règlement … ») ou à l'article 1 (« Le règlement … est modifié comme suit »)."),
    "based_on": ("se fonde sur", "B apparaît-il dans les visas de A ?",
                 "Les visas sont les lignes « vu le traité … », « vu le règlement … » tout au début du texte de A, avant les considérants."),
}


def eurlex(celex, lang="FR"):
    return f"https://eur-lex.europa.eu/legal-content/{lang}/TXT/?uri=CELEX:{celex}"


def titles_for(coll, ids):
    """expression_title of the English expression, keyed on the work id."""
    want = {i: None for i in ids}
    for paq in sorted((pathlib.Path(coll) / "graphe" / "A2" / "titres_en").glob("paquet-*.nt")):
        for s, p, o_uri, o_lit in T.read_nt(paq):
            if p.endswith("#expression_title") and o_lit is not None:
                work = T.short(re.sub(r'\.\d+$', '', s))
                if work in want and want[work] is None:
                    want[work] = o_lit
    return want


def draw(truth, n=200, shared=30, seed=11, auditors=("A", "B", "C")):
    rng = random.Random(seed)
    fault = {k["fact"] for k in truth["known_registry_faults"] if "fact" in k}
    nodes = {x["id"]: x for x in truth["nodes"]}
    pool = {p: [f for f in truth["facts"] if f["p"] == p and f["id"] not in fault
               and nodes[f["s"]].get("celex") and nodes[f["o"]].get("celex")] for p in Q}
    quota = {"repeals": 70, "amends": 70, "based_on": n - 140}
    sample = []
    for p, k in quota.items():
        sample += rng.sample(pool[p], k)
    rng.shuffle(sample)
    common, rest = sample[:shared], sample[shared:]
    per = {a: list(common) for a in auditors}
    for i, f in enumerate(rest):
        per[auditors[i % len(auditors)]].append(f)
    return sample, common, per


def page(auditor, facts, common_ids, titles, nodes, truth):
    rows = []
    for f in facts:
        a, b = nodes[f["s"]], nodes[f["o"]]
        rel, q, hint = Q[f["p"]]
        tag = " <span class='shared'>commun aux trois</span>" if f["id"] in common_ids else ""
        rows.append(f"""<section class="fact">
<h2>{html.escape(f['id'])} · <em>{rel}</em>{tag}</h2>
<p><b>A</b> : {html.escape(titles.get(a['id']) or '(titre non disponible)')} — CELEX {html.escape(a['celex'])} · {html.escape(a.get('date_document') or '')}
 → <a href="{eurlex(a['celex'],'FR')}">texte FR</a> · <a href="{eurlex(a['celex'],'EN')}">texte EN</a></p>
<p><b>B</b> : {html.escape(titles.get(b['id']) or '(titre non disponible)')} — CELEX {html.escape(b['celex'])} · {html.escape(b.get('date_document') or '')}
 → <a href="{eurlex(b['celex'],'FR')}">texte FR</a> · <a href="{eurlex(b['celex'],'EN')}">texte EN</a></p>
<p class="q">{q} <span class="hint">{hint}</span></p>
<p class="boxes">☐ OUI, à l'article n° ______ &nbsp;&nbsp; ☐ NON, je ne le trouve pas &nbsp;&nbsp; ☐ ILLISIBLE (texte absent, scanné, ou trop long)</p>
</section>""")
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Audit de la vérité EUR-Lex — {html.escape(auditor)}</title>
<style>
body{{font-family:-apple-system,Helvetica,Arial,sans-serif;max-width:820px;margin:24px auto;padding:0 20px;font-size:13.5px;line-height:1.45;color:#111}}
h1{{font-size:22px;margin:0 0 6px}} h2{{font-size:15px;margin:0 0 6px}} .warn{{color:#fff;background:#c00;font-weight:800;font-size:18px;padding:10px 14px;text-align:center;margin:14px 0}}
.rules{{border:1px solid #999;padding:10px 14px;margin:12px 0}} .rules li{{margin:4px 0}}
.fact{{border-top:1px solid #ccc;padding:10px 0 8px;page-break-inside:avoid}} .fact p{{margin:3px 0}} .q{{font-weight:700;margin-top:6px!important}} .hint{{font-weight:400;color:#444}}
.boxes{{font-size:14px;margin-top:6px!important}} .shared{{font-size:11px;background:#eef;border:1px solid #99c;padding:1px 6px;border-radius:8px;font-weight:400}}
a{{color:#0645ad}} .answer{{page-break-before:always}} table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #bbb;padding:5px 8px;font-size:13px}}
</style></head><body>
<h1>Audit de la vérité EUR-Lex — {html.escape(auditor)}</h1>
<p>{len(facts)} faits à vérifier, dont {len([f for f in facts if f['id'] in common_ids])} communs aux trois auditeurs. Vérité : <code>{html.escape(truth['id'])}</code>, empreinte <code>{truth['sha256'][:16]}…</code>, gelée le {html.escape(truth['frozen'])}. Échantillon tiré au sort (graine publiée), 70 abroge · 70 modifie · 60 se fonde sur.</p>
<div class="warn">NE PAS UTILISER DE LLM. NI CHATGPT, NI CLAUDE, NI GEMINI, NI AUCUN ASSISTANT.<br>C'est un humain qui lit, c'est ce qui fait la valeur de l'audit.</div>
<div class="rules"><b>Les règles</b><ul>
<li><b>Lisez le texte de l'acte A</b> (lien « texte FR » ou « texte EN »). Ne regardez <b>jamais</b> le cadre « Relations entre documents » ou « Informations sur le document » d'EUR-Lex : ce cadre, c'est la base qu'on contrôle. S'y fier, c'est faire noter l'élève par lui-même.</li>
<li><b>OUI</b> seulement si vous avez lu la phrase dans le texte de A. Notez le numéro de l'article (ou « titre », ou « visas »).</li>
<li><b>NON</b> si vous avez cherché aux endroits indiqués et ne l'avez pas trouvé. Un NON honnête vaut plus qu'un OUI deviné.</li>
<li><b>ILLISIBLE</b> si le texte n'est pas disponible, est un scan sans texte, ou dépasse ce que vous pouvez lire en 5 minutes. C'est une réponse valable.</li>
<li>2 à 3 minutes par fait. Pas de recherche ailleurs, pas d'interprétation : ce que le texte dit, ou pas.</li>
<li>Renvoyez vos réponses par mail à contact@loxyn.ai, une ligne par fait : <code>f-000123: OUI art. 24</code> / <code>f-000456: NON</code> / <code>f-000789: ILLISIBLE</code>. La feuille de réponses est en dernière page.</li>
</ul></div>
{''.join(rows)}
<section class="answer"><h2>Feuille de réponses — {html.escape(auditor)}</h2>
<table><tr><th>fait</th><th>relation</th><th>réponse (OUI art. n° / NON / ILLISIBLE)</th></tr>
{''.join(f"<tr><td>{html.escape(f['id'])}</td><td>{html.escape(Q[f['p']][0])}</td><td>&nbsp;</td></tr>" for f in facts)}
</table></section>
</body></html>"""


def main():
    argv = sys.argv[1:]
    pos = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or not argv[i - 1].startswith("--"))]
    if len(pos) != 3:
        sys.exit(__doc__)
    truth = json.load(open(pos[0], encoding="utf-8"))
    coll, out = pos[1], pathlib.Path(pos[2]); out.mkdir(parents=True, exist_ok=True)
    opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d
    auditors = [a.strip() for a in opt("--auditors", "A,B,C").split(",")]
    n, shared, seed = int(opt("--n", 200)), int(opt("--shared", 30)), int(opt("--seed", 11))
    sample, common, per = draw(truth, n, shared, seed, auditors)
    nodes = {x["id"]: x for x in truth["nodes"]}
    ids = {f["s"] for f in sample} | {f["o"] for f in sample}
    titles = titles_for(coll, ids)
    rec = {"sample_name": f"audit-{n}", "truth": truth["id"], "truth_sha256": truth["sha256"], "seed": seed, "shared": shared,
           "auditors": auditors, "facts": [f["id"] for f in sample], "common": [f["id"] for f in common],
           "per_auditor": {a: [f["id"] for f in fs] for a, fs in per.items()},
           "question": {p: Q[p][1] for p in Q}, "rule": "read the text of act A; never the EUR-Lex relationships box; no LLM"}
    rec["sha256"] = canon.sha256({k: v for k, v in rec.items() if k != "sha256"})
    canon.write(out / f"audit-{n}.json", rec)
    cids = set(rec["common"])
    for a, fs in per.items():
        (out / f"audit-{a}.html").write_text(page(a, fs, cids, titles, nodes, truth), encoding="utf-8")
        print(a, len(fs), "faits")
    print("titles found:", sum(1 for v in titles.values() if v), "of", len(titles))


if __name__ == "__main__":
    main()
