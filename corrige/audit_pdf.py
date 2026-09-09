"""Fillable audit booklets (AcroForm): one PDF per auditor, with real checkboxes,
a text field for the article number, and clickable links to the acts' texts.

    .venv-pdf/bin/python -m corrige.audit_pdf <truth.json> <audit dir> [--auditors "A,B,C"]

Reads audit-200.json and titres-fr.json written by corrige.audit. Needs reportlab.
"""
import sys, json, pathlib
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black, white, red
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import simpleSplit
from .audit import Q, eurlex

W, H = A4
M = 46
FONT, BOLD = "Helvetica", "Helvetica-Bold"
for path, name in (("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "ArialU"),):
    try:
        pdfmetrics.registerFont(TTFont(name, path)); FONT = name; BOLD = name
    except Exception:
        pass


def wrap(c, text, x, y, width, size=9.5, font=None, leading=12.5):
    font = font or FONT
    c.setFont(font, size)
    lines = simpleSplit(text, font, size, width)
    for ln in lines:
        c.drawString(x, y, ln); y -= leading
    return y


def eurlex_pdf(celex, lang="FR"):
    return f"https://eur-lex.europa.eu/legal-content/{lang}/TXT/PDF/?uri=CELEX:{celex}"


def link(c, text, x, y, url, size=9.5):
    c.setFont(FONT, size); c.setFillColor(HexColor("#0645ad"))
    c.drawString(x, y, text); w = c.stringWidth(text, FONT, size)
    c.linkURL(url, (x, y - 2, x + w, y + size), relative=0, thickness=0)
    c.setFillColor(black)
    return x + w


def header(c, auditor, n, n_common, truth):
    y = H - M
    c.setFont(BOLD, 17); c.drawString(M, y, f"Audit de la vérité EUR-Lex — {auditor}"); y -= 22
    y = wrap(c, f"{n} faits à vérifier, dont {n_common} communs aux trois auditeurs. Vérité {truth['id']}, empreinte {truth['sha256'][:16]}…, gelée le {truth['frozen']}. Échantillon tiré au sort (graine publiée) : 70 abroge · 70 modifie · 60 se fonde sur.", M, y, W - 2 * M)
    y -= 6
    c.setFillColor(red); c.rect(M, y - 40, W - 2 * M, 44, fill=1, stroke=0)
    c.setFillColor(white); c.setFont(BOLD, 10.8)
    c.drawCentredString(W / 2, y - 12, "NE PAS UTILISER DE LLM. NI CHATGPT, NI CLAUDE, NI GEMINI, NI AUCUN ASSISTANT.")
    c.setFont(BOLD, 10.5); c.drawCentredString(W / 2, y - 30, "C'est un humain qui lit : c'est ce qui fait la valeur de l'audit.")
    c.setFillColor(black); y -= 56
    rules = [
        "Lisez le TEXTE de l'acte A (lien « ouvrir le texte »). Pour les actes anciens, la page web n'a que le titre : le lien « PDF » ouvre le scan du Journal officiel, qui a une couche texte, on peut y chercher (Cmd+F). L'onglet du navigateur affiche « EN » même en français : c'est l'interface, pas le document. Ne regardez JAMAIS le cadre « Relations entre documents » ou « Informations sur le document » d'EUR-Lex : ce cadre, c'est la base qu'on contrôle. S'y fier, c'est faire noter l'élève par lui-même.",
        "OUI seulement si vous avez lu la phrase dans le texte de A ; notez le numéro d'article (ou « titre », ou « visas »). NON si vous avez cherché aux endroits indiqués sans trouver : un NON honnête vaut plus qu'un OUI deviné. ILLISIBLE si le texte est absent, scanné, ou trop long pour 5 minutes : c'est une réponse valable.",
        "2 à 3 minutes par fait. Pas de recherche ailleurs, pas d'interprétation : ce que le texte dit, ou pas.",
        "Remplissez les cases directement dans ce PDF (Aperçu, Acrobat, ou un navigateur), enregistrez, renvoyez le fichier à contact@loxyn.ai.",
    ]
    for r in rules:
        y = wrap(c, "• " + r, M + 4, y, W - 2 * M - 8, size=9.2, leading=11.8); y -= 3
    return y - 6


def act_links(c, act, y, avail):
    x = link(c, "ouvrir le texte (FR)", M + 14, y, eurlex(act["celex"], "FR"))
    c.setFont(FONT, 9.5); c.drawString(x + 4, y, "·"); x = link(c, "EN", x + 12, y, eurlex(act["celex"], "EN"))
    c.setFont(FONT, 9.5); c.drawString(x + 4, y, "·"); x = link(c, "PDF", x + 12, y, eurlex_pdf(act["celex"], "FR"))
    if avail.get(act["celex"]) == "title+pdf":
        c.setFont(BOLD, 8.6); c.setFillColor(HexColor("#b45309"))
        c.drawString(x + 10, y, "← pas de texte en page web : ouvrez le PDF (scan du JO, avec texte)")
        c.setFillColor(black)
    return y - 13


def fact_block(c, f, a, b, titles, common, y, avail):
    rel, q, hint = Q[f["p"]]
    ta = titles.get(a["id"]) or "(titre non disponible)"; tb = titles.get(b["id"]) or "(titre non disponible)"
    need = 30 + 12.5 * (len(simpleSplit("A : " + ta, FONT, 9.5, W - 2 * M)) + len(simpleSplit("B : " + tb, FONT, 9.5, W - 2 * M)) + len(simpleSplit(q + " " + hint, FONT, 9.5, W - 2 * M))) + 40
    if y - need < M + 20:
        c.showPage(); y = H - M
    c.setStrokeColor(HexColor("#cccccc")); c.line(M, y + 4, W - M, y + 4); y -= 12
    c.setFont(BOLD, 11); c.drawString(M, y, f"{f['id']}  ·  {rel}")
    if f["id"] in common:
        c.setFont(FONT, 8); c.setFillColor(HexColor("#335599")); c.drawString(M + 150, y, "commun aux trois"); c.setFillColor(black)
    y -= 14
    y = wrap(c, f"A : {ta} — CELEX {a['celex']} · {a.get('date_document') or ''}", M, y, W - 2 * M)
    y = act_links(c, a, y, avail)
    y = wrap(c, f"B : {tb} — CELEX {b['celex']} · {b.get('date_document') or ''}", M, y, W - 2 * M)
    y = act_links(c, b, y, avail) - 1
    y = wrap(c, q, M, y, W - 2 * M, font=BOLD)
    c.setFillColor(HexColor("#b45309"))          # the advice, in colour so that it is seen
    y = wrap(c, "Conseil : " + hint, M, y, W - 2 * M, size=9.2, leading=11.6)
    c.setFillColor(black); y -= 4
    form = c.acroForm
    fid = f["id"].replace("-", "")
    opts = [("OUI", "oui"), ("NON, je ne le trouve pas", "non"), ("ILLISIBLE (absent, scanné, trop long)", "illisible")]
    x = M
    for label, val in opts:
        form.radio(name=f"r_{fid}", tooltip=label, value=val, selected=False, x=x, y=y - 3, size=12, buttonStyle="check", borderWidth=1, borderColor=black, fillColor=white)
        c.setFont(FONT, 9.5); c.drawString(x + 16, y, label); x += 24 + c.stringWidth(label, FONT, 9.5)
    y -= 20
    c.setFont(FONT, 9.5); c.drawString(M, y, "Si OUI, article n° (ou « titre », « visas ») :")
    form.textfield(name=f"art_{fid}", tooltip="article", x=M + 205, y=y - 4, width=120, height=15, borderWidth=0.6, borderColor=black, fillColor=white, fontSize=9)
    return y - 22


def main():
    argv = sys.argv[1:]
    pos = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or not argv[i - 1].startswith("--"))]
    truth = json.load(open(pos[0], encoding="utf-8")); out = pathlib.Path(pos[1])
    rec = json.load(open(out / "audit-200.json", encoding="utf-8"))
    titles = json.load(open(out / "titres-fr.json", encoding="utf-8")) if (out / "titres-fr.json").exists() else {}
    facts = {f["id"]: f for f in truth["facts"]}; nodes = {n["id"]: n for n in truth["nodes"]}
    common = set(rec["common"])
    avail = json.load(open(out / "eurlex-text-availability.json", encoding="utf-8")) if (out / "eurlex-text-availability.json").exists() else {}
    for auditor, ids in rec["per_auditor"].items():
        path = out / f"audit-{auditor}.pdf"
        c = canvas.Canvas(str(path), pagesize=A4)
        c.setTitle(f"Audit de la vérité EUR-Lex — {auditor}"); c.setAuthor("Loxyn SAS — le Corrigé")
        y = header(c, auditor, len(ids), sum(1 for i in ids if i in common), truth)
        for fid in ids:
            f = facts[fid]; y = fact_block(c, f, nodes[f["s"]], nodes[f["o"]], titles, common, y, avail)
        c.save(); print(path, len(ids), "faits")


if __name__ == "__main__":
    main()
