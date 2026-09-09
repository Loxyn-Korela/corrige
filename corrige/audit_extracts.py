"""Pre-locate, by plain text search (no model), the sentence of act A that names act B,
so that the human auditor confirms a sentence instead of reading an act.

    .venv-pdf/bin/python -m corrige.audit_extracts <truth.json> <audit dir>

Writes audit/extracts.json: per fact id, the search keys tried, the source read
(HTML text or PDF text layer), and up to two matching sentences with their position.
"""
import sys, json, re, html, pathlib, urllib.request, io, concurrent.futures, time

UA = {"User-Agent": "Mozilla/5.0 (corrige audit; text search only)"}


def fetch(url, timeout=90):
    """Polite: one request at a time, a pause between them, and an HTTP 202 (anti-robot challenge) is an error, not a page."""
    time.sleep(1.5)
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout)
    if r.status == 202:
        raise RuntimeError("EUR-Lex 202 challenge")
    return r.read()


def html_text(celex, lang="FR"):
    h = fetch(f"https://eur-lex.europa.eu/legal-content/{lang}/TXT/?uri=CELEX:{celex}").decode("utf-8", "replace")
    m = re.search(r'(?s)<div[^>]*id="text"[^>]*>(.*)', h)
    body = m.group(1) if m else h
    body = re.sub(r'(?s)<script.*?</script>|<style.*?</style>', ' ', body)
    body = re.sub(r'</(p|div|li|tr|h\d)>', '\n', body)
    txt = html.unescape(re.sub(r'<[^>]+>', ' ', body))
    txt = re.sub(r'[ \t ]+', ' ', txt)
    return txt


def pdf_text(celex, lang="FR"):
    from pypdf import PdfReader
    data = fetch(f"https://eur-lex.europa.eu/legal-content/{lang}/TXT/PDF/?uri=CELEX:{celex}", timeout=180)
    r = PdfReader(io.BytesIO(data))
    if len(r.pages) > 120:
        raise RuntimeError(f"PDF très long, {len(r.pages)} pages")
    return "\n".join((p.extract_text() or "") for p in r.pages)


def keys_for(celex):
    """Search keys for act B, derived from its CELEX. Loose on purpose: the human confirms."""
    m = re.match(r'^(\d)(\d{4})([A-Z]{1,2})(\d{3,4})', celex)
    if not m:
        return [celex]
    sector, year, typ, num = m.group(1), m.group(2), m.group(3), int(m.group(4))
    yy = year[2:]
    if sector == "1":                                   # treaty article: 11957E198 -> article 198
        return [f"article {num}", f"art. {num}", f"articles {num}"]
    if sector == "2":                                   # international agreement / annex / protocol: no reliable numeric key
        return []
    if sector == "5":                                   # preparatory act: 52009DC0557 -> COM(2009) 557
        return [f"COM({year}) {num}", f"COM ({year}) {num}", f"({year}) {num}", f"{num}/{year}", f"{year}/{num}"]
    keys = [f"{num}/{year}", f"{year}/{num}", f"{num}/{yy}", f"{yy}/{num}"]
    if typ in ("L", "D"):
        keys += [f"{year}/{num}/", f"{yy}/{num}/"]
    return keys


VERB = {"repeals": r"abrog|repeal", "amends": r"modifi|amend|remplac|replac|insér|insert|supprim|delet",
        "based_on": r"\bvu\b|having regard|conformément|in accordance|fondé|based on|basé"}
# passive or reverse phrasings where B is the actor or the sentence is a mere reference: not a relation stated by A
PASSIVE = re.compile(r"modifié(?:e|s|es)? (?:\w+ )?(?:en dernier lieu )?par|amended (?:last )?by|(?:a|ont|est|sont)(?: \w+)? été modifi|has been amended|doivent être intégr|dérog|note de bas|\bvisé", re.I)


def sentences(txt):
    for s in re.split(r'(?<=[.;:!?])\s+|\n+', txt):
        s = s.strip()
        if 12 <= len(s) <= 900:
            yield s


def window(s, m, half=210):
    a, b = max(0, m.start() - half), min(len(s), m.end() + half)
    return ("… " if a > 0 else "") + s[a:b] + (" …" if b < len(s) else "")


def locate(txt, keys, relation):
    """Sentences of A that name B (numeric key), each tagged has_verb when it also carries the
    verb of the relation. Verb-bearing sentences first; for repeals the last one (final articles)."""
    hits = []
    verb = re.compile(VERB[relation], re.I)
    for s in sentences(txt):
        words = s.split()
        spaced = (s.count(" ") >= len(s) / 12 and max((len(w) for w in words), default=0) <= 28
                  and not re.search(r"\d[a-zé]{3,}|[a-zé]{3,}\)", s))                       # digits glued to letters, "Commissionf)": a scan, not quotable
        for k in keys:
            m = re.search(r'(?<!\d)' + re.escape(k) + r'(?!\d)', s, re.I)
            if m:
                hv = bool(verb.search(s)) and not (relation == "amends" and PASSIVE.search(s))
                hits.append({"key": k, "sentence": window(s, m), "has_verb": hv, "readable": spaced}); break
    verbed = [h for h in hits if h["has_verb"] and h["readable"]]
    if relation == "repeals": verbed = verbed[::-1]
    rest = [h for h in hits if not (h["has_verb"] and h["readable"])]
    return (verbed + rest)[:2]


def main():
    truth = json.load(open(sys.argv[1], encoding="utf-8")); out = pathlib.Path(sys.argv[2])
    rec = json.load(open(out / "audit-200.json", encoding="utf-8"))
    avail = json.load(open(out / "eurlex-text-availability.json", encoding="utf-8"))
    facts = {f["id"]: f for f in truth["facts"]}; nodes = {n["id"]: n for n in truth["nodes"]}
    cache = {}

    pdfs = json.load(open(out / "eurlex-pdf-availability.json", encoding="utf-8")) if (out / "eurlex-pdf-availability.json").exists() else {}
    titles = json.load(open(out / "titres-fr.json", encoding="utf-8")) if (out / "titres-fr.json").exists() else {}

    def text_of(celex):
        if celex in cache: return cache[celex]
        src, txt, note = "html", "", ""
        try:
            if avail.get(celex) == "html":
                txt = html_text(celex)
            if len(txt) < 2000:
                lang = "FR" if pdfs.get(celex, {}).get("FR", True) else "EN"
                src, txt = ("pdf" if lang == "FR" else "pdf-en"), pdf_text(celex, lang)
        except Exception as e:
            src, txt, note = "error", "", str(e)[:80]
        cache[celex] = (src, txt, note); return cache[celex]

    def one(fid):
        f = facts[fid]; a, b = nodes[f["s"]], nodes[f["o"]]
        src, txt, note = text_of(a["celex"])
        keys = keys_for(b["celex"])
        title = titles.get(a["id"]) or ""
        txt2 = (title + ".\n" + txt) if title else txt          # the title of A is part of its text (« modifiant le règlement … »)
        hits = locate(txt2, keys, f["p"]) if ((txt or title) and keys) else []
        return fid, {"a": a["celex"], "b": b["celex"], "source": src, "note": note, "chars": len(txt), "keys": keys, "hits": hits}

    t0 = time.time(); res = {}
    prev = json.load(open(out / "extracts.json", encoding="utf-8")) if (out / "extracts.json").exists() else {}
    for fid in rec["facts"]:
        if "--fresh" not in sys.argv and (prev.get(fid, {}).get("hits") or prev.get(fid, {}).get("source") in ("html", "pdf", "pdf-en")) and "has_verb" in str(prev.get(fid, {})):
            res[fid] = prev[fid]; continue          # keep what was already located; only retry errors
        res[fid] = one(fid)[1]
    if sum(1 for r in res.values() if r["source"] == "error") == len(res):
        sys.exit("every fetch failed (EUR-Lex challenge?): extracts.json left untouched")
    json.dump(res, open(out / "extracts.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    found = sum(1 for r in res.values() if r["hits"]); src = {}
    for r in res.values(): src[r["source"]] = src.get(r["source"], 0) + 1
    print(f"{found}/{len(res)} facts with a located sentence; sources {src}; {round(time.time()-t0)} s")


if __name__ == "__main__":
    main()
