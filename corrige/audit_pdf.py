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
    y = wrap(c, f"{n} faits à vérifier dans ce carnet, dont {n_common} communs aux trois auditeurs. L'échantillon complet fait 200 faits (70 abroge · 70 modifie · 60 se fonde sur), tirés au sort avec une graine publiée parmi les faits ordinaires de la vérité : les fautes déjà connues du registre en sont exclues, le taux mesuré est donc celui des faits ordinaires. Vérité {truth['id']}, empreinte {truth['sha256'][:16]}…, gelée le {truth['frozen']}.", M, y, W - 2 * M)
    y -= 6
    c.setFillColor(red); c.rect(M, y - 40, W - 2 * M, 44, fill=1, stroke=0)
    c.setFillColor(white); c.setFont(BOLD, 10.8)
    c.drawCentredString(W / 2, y - 12, "NE PAS UTILISER DE LLM. NI CHATGPT, NI CLAUDE, NI GEMINI, NI AUCUN ASSISTANT.")
    c.setFont(BOLD, 10.5); c.drawCentredString(W / 2, y - 30, "C'est un humain qui lit : c'est ce qui fait la valeur de l'audit.")
    c.setFillColor(black); y -= 56
    rules = [
        "Lisez le TEXTE de l'acte A (lien « ouvrir le texte »). Pour les actes anciens, la page web n'a que le titre : le lien « PDF » ouvre le scan du Journal officiel, qui a une couche texte, on peut y chercher (Cmd+F). Dans ces scans, le signe ° est souvent lu 0 (« n0 3944/87 ») : cherchez le numéro seul (« 3944/87 »). Un PDF du JO contient parfois plusieurs actes à la suite : prenez celui dont le titre est imprimé ici. L'onglet du navigateur affiche « EN » même en français : c'est l'interface, pas le document. Ne regardez JAMAIS le cadre « Relations entre documents » ou « Informations sur le document » d'EUR-Lex : ce cadre, c'est la base qu'on contrôle. S'y fier, c'est faire noter l'élève par lui-même.",
        "OUI seulement si vous avez lu la phrase dans le texte de A ; notez le numéro d'article (ou « titre », ou « visas »). NON si vous avez cherché aux endroits indiqués sans trouver : un NON honnête vaut plus qu'un OUI deviné. ILLISIBLE si le texte est absent ou illisible (scan sans couche texte) : c'est une réponse valable. Pas plus de 5 minutes par fait ; la plupart se règlent en une.",
        "NE JUGEZ JAMAIS SUR LES TITRES. A et B parlent souvent de sujets sans rapport : un avis sur les œufs à couver « se fonde sur » l'article 198 du traité, qui parle du Comité économique et social. La base légale est l'article qui AUTORISE l'acte, pas un texte sur le même thème. La seule question : le texte de A cite-t-il B par son numéro ?",
        "LA MÉTHODE : sous chaque question, le carnet donne l'extrait trouvé par une recherche automatique du numéro de B dans le texte de A (une recherche de texte, aucun modèle). Ouvrez le texte, retrouvez la phrase (Cmd+F avec le numéro). OUI SEULEMENT SI LA PHRASE DIT LA RELATION : « … est abrogé », « … est modifié comme suit », « vu le règlement … ». Un simple renvoi, une note de bas de page, « dérogeant à », « visé à » ne suffisent pas : c'est NON. Si le carnet dit « aucun extrait trouvé », cherchez vous-même ; si rien n'apparaît : NON.",
        "EXEMPLE RÉSOLU : A = avis du Comité économique et social 51989AC0677, B = article 198 du traité CEE. Le PDF de A commence par « Le 9 mars 1989, le Conseil a décidé, conformément à l'article 198 du Traité … de consulter le Comité ». Réponse : OUI, « première phrase ».",
        "Remplissez les cases directement dans ce PDF (Aperçu, Acrobat, ou un navigateur), enregistrez, renvoyez le fichier à contact@loxyn.ai. Si l'enregistrement des cases ne marche pas chez vous, la dernière page est une feuille de réponses à remplir à la main et à photographier.",
    ]
    for r in rules:
        y = wrap(c, "• " + r, M + 4, y, W - 2 * M - 8, size=9.2, leading=11.8); y -= 3
    return y - 6


def act_links(c, act, y, avail, pdfs, is_a=True):
    x = link(c, "ouvrir le texte (FR)", M + 14, y, eurlex(act["celex"], "FR"))
    c.setFont(FONT, 9.5); c.drawString(x + 4, y, "·"); x = link(c, "EN", x + 12, y, eurlex(act["celex"], "EN"))
    pdf = pdfs.get(act["celex"], {})
    shown = []
    for lang in ("FR", "EN"):
        if pdf.get(lang):
            c.setFont(FONT, 9.5); c.drawString(x + 4, y, "·"); x = link(c, f"PDF {lang}", x + 12, y, eurlex_pdf(act["celex"], lang)); shown.append(lang)
    if avail.get(act["celex"]) == "title+pdf" and is_a:
        c.setFont(BOLD, 8.6); c.setFillColor(HexColor("#b45309"))
        if shown:
            c.drawString(x + 10, y, f"← pas de texte en page web : ouvrez le PDF {shown[0]}")
        else:
            c.drawString(x + 10, y, "← aucun texte servi par EUR-Lex, ni page ni PDF : répondez ILLISIBLE")
        c.setFillColor(black)
    return y - 13


def extract_block(c, f, ext, y):
    e = ext.get(f["id"]) if ext else None
    if not e:
        return y
    src = {"html": "page web", "pdf": "PDF", "pdf-en": "PDF EN", "error": "texte non récupéré"}.get(e.get("source"), "")
    keys = ", ".join(f"« {k} »" for k in e.get("keys", [])[:3])
    good = [h for h in e.get("hits", []) if h.get("has_verb") and h.get("readable", True)]
    if good:
        h = good[0]
        c.setFillColor(HexColor("#1d4ed8"))
        y = wrap(c, f"Extrait trouvé par recherche automatique du numéro « {h['key']} » dans le texte de A ({src}) — à vérifier dans le texte, puis OUI seulement si la phrase dit bien la relation :", M, y, W - 2 * M, size=9, leading=11.4)
        c.setFillColor(HexColor("#1e3a8a"))
        y = wrap(c, "« " + h["sentence"].replace("\n", " ") + " »", M + 10, y, W - 2 * M - 10, size=9.2, leading=11.6)
    elif e.get("hits"):
        c.setFillColor(HexColor("#7c2d12"))
        y = wrap(c, f"Le numéro « {e['hits'][0]['key']} » apparaît dans le texte de A ({src}) mais pas dans une phrase qui dit la relation (renvoi, note, dérogation…) : jugez vous-même. Cherchez (Cmd+F) {keys}.", M, y, W - 2 * M, size=9, leading=11.4)
    elif not e.get("keys"):
        c.setFillColor(HexColor("#7c2d12"))
        y = wrap(c, "B est un accord, une annexe ou un protocole sans numéro cherchable : lisez le titre et l'article 1 de A, qui nomment ce qu'ils modifient ou abrogent.", M, y, W - 2 * M, size=9, leading=11.4)
    else:
        c.setFillColor(HexColor("#7c2d12"))
        why = f" ({e['note']})" if e.get("note") else ""
        y = wrap(c, f"Aucun extrait trouvé automatiquement ({src}{why}). Cherchez vous-même dans le texte de A (Cmd+F) : {keys}. Si rien n'apparaît : NON.", M, y, W - 2 * M, size=9, leading=11.4)
    c.setFillColor(black)
    return y - 2


def fact_block(c, f, a, b, titles, common, y, avail, ext=None, pdfs=None):
    pdfs = pdfs or {}
    rel, q, hint = Q[f["p"]]
    ta = titles.get(a["id"]) or "(titre non disponible)"; tb = titles.get(b["id"]) or "(titre non disponible)"
    e = (ext or {}).get(f["id"]) or {}
    ext_len = len(simpleSplit((e.get("hits") or [{"sentence": ""}])[0]["sentence"][:460], FONT, 9.2, W - 2 * M - 10)) + 3 if e else 0
    need = 30 + 12.5 * (len(simpleSplit("A : " + ta, FONT, 9.5, W - 2 * M)) + len(simpleSplit("B : " + tb, FONT, 9.5, W - 2 * M)) + len(simpleSplit(q + " " + hint, FONT, 9.5, W - 2 * M)) + ext_len) + 46
    if y - need < M + 20:
        c.showPage(); y = H - M
    c.setStrokeColor(HexColor("#cccccc")); c.line(M, y + 4, W - M, y + 4); y -= 12
    c.setFont(BOLD, 11); c.drawString(M, y, f"{f['id']}  ·  {rel}")
    if f["id"] in common:
        c.setFont(FONT, 8); c.setFillColor(HexColor("#335599")); c.drawString(M + 150, y, "commun aux trois"); c.setFillColor(black)
    y -= 14
    y = wrap(c, f"A : {ta} — CELEX {a['celex']} · {a.get('date_document') or ''}", M, y, W - 2 * M)
    y = act_links(c, a, y, avail, pdfs)
    y = wrap(c, f"B : {tb} — CELEX {b['celex']} · {b.get('date_document') or ''}", M, y, W - 2 * M)
    y = act_links(c, b, y, avail, pdfs, is_a=False) - 1
    y = wrap(c, q, M, y, W - 2 * M, font=BOLD)
    c.setFillColor(HexColor("#b45309"))          # the advice, in colour so that it is seen
    y = wrap(c, "Conseil : " + hint, M, y, W - 2 * M, size=9.2, leading=11.6)
    c.setFillColor(black); y -= 2
    y = extract_block(c, f, ext, y); y -= 2
    form = c.acroForm
    fid = f["id"].replace("-", "")
    opts = [("OUI", "oui"), ("NON, je ne le trouve pas", "non"), ("ILLISIBLE (absent, scanné, trop long)", "illisible")]
    x = M
    for label, val in opts:
        form.radio(name=f"r_{fid}", tooltip="réponse", value=val, selected=False, x=x, y=y - 3, size=14, buttonStyle="check", borderWidth=1, borderColor=black, fillColor=white, fieldFlags="noToggleToOff radio")
        c.setFont(FONT, 9.5); c.drawString(x + 16, y, label); x += 24 + c.stringWidth(label, FONT, 9.5)
    y -= 20
    c.setFont(FONT, 9.5); c.drawString(M, y, "Si OUI, article n° (ou « titre », « visas ») :")
    form.textfield(name=f"art_{fid}", tooltip="article", x=M + 205, y=y - 4, width=120, height=15, borderWidth=0.6, borderColor=black, fillColor=white, fontSize=9)
    return y - 22


def answer_sheet(c, auditor, facts):
    """Last pages: a hand-fillable table, in case the form fields do not save."""
    c.showPage(); y = H - M
    c.setFont(BOLD, 14); c.drawString(M, y, f"Feuille de réponses — {auditor} (si les cases du PDF ne s'enregistrent pas)"); y -= 16
    c.setFont(FONT, 9); c.drawString(M, y, "Entourez OUI / NON / ILLISIBLE, notez l'article, photographiez, envoyez à contact@loxyn.ai."); y -= 18
    col = (M, M + 70, M + 150, M + 400)
    def head():
        nonlocal y
        c.setFont(BOLD, 9)
        for x, t in zip(col, ("fait", "relation", "réponse", "article")): c.drawString(x, y, t)
        y -= 12; c.setStrokeColor(HexColor("#999999")); c.line(M, y + 4, W - M, y + 4); y -= 6
    head()
    c.setFont(FONT, 9)
    for f in facts:
        if y < M + 20:
            c.showPage(); y = H - M; head(); c.setFont(FONT, 9)
        c.drawString(col[0], y, f["id"]); c.drawString(col[1], y, Q[f["p"]][0]); c.drawString(col[2], y, "OUI   /   NON   /   ILLISIBLE"); c.drawString(col[3], y, "art. ________")
        y -= 14


def main():
    argv = sys.argv[1:]
    pos = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or not argv[i - 1].startswith("--"))]
    truth = json.load(open(pos[0], encoding="utf-8")); out = pathlib.Path(pos[1])
    rec = json.load(open(out / "audit-200.json", encoding="utf-8"))
    titles = json.load(open(out / "titres-fr.json", encoding="utf-8")) if (out / "titres-fr.json").exists() else {}
    facts = {f["id"]: f for f in truth["facts"]}; nodes = {n["id"]: n for n in truth["nodes"]}
    common = set(rec["common"])
    avail = json.load(open(out / "eurlex-text-availability.json", encoding="utf-8")) if (out / "eurlex-text-availability.json").exists() else {}
    ext = json.load(open(out / "extracts.json", encoding="utf-8")) if (out / "extracts.json").exists() else {}
    pdfs = json.load(open(out / "eurlex-pdf-availability.json", encoding="utf-8")) if (out / "eurlex-pdf-availability.json").exists() else {}
    for auditor, ids in rec["per_auditor"].items():
        path = out / f"audit-{auditor}.pdf"
        c = canvas.Canvas(str(path), pagesize=A4)
        c.setTitle(f"Audit de la vérité EUR-Lex — {auditor}"); c.setAuthor("Loxyn SAS — le Corrigé")
        y = header(c, auditor, len(ids), sum(1 for i in ids if i in common), truth)
        for fid in ids:
            f = facts[fid]; y = fact_block(c, f, nodes[f["s"]], nodes[f["o"]], titles, common, y, avail, ext, pdfs)
        answer_sheet(c, auditor, [facts[i] for i in ids])
        c.save(); print(path, len(ids), "faits")


if __name__ == "__main__":
    main()
