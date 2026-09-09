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
    return "\n".join((p.extract_text() or "") for p in r.pages[:60])


def keys_for(celex):
    """Search keys for act B, derived from its CELEX. Loose on purpose: the human confirms."""
    m = re.match(r'^(\d)(\d{4})([A-Z]{1,2})(\d{3,4})', celex)
    if not m:
        return [celex]
    sector, year, typ, num = m.group(1), m.group(2), m.group(3), int(m.group(4))
    yy = year[2:]
    if sector == "1":                                   # treaty article: 11957E198 -> article 198
        return [f"article {num}", f"art. {num}", f"articles {num}"]
    if sector == "5":                                   # preparatory act: 52009DC0557 -> COM(2009) 557
        return [f"COM({year}) {num}", f"COM ({year}) {num}", f"({year}) {num}", f"{num}/{year}", f"{year}/{num}"]
    keys = [f"{num}/{year}", f"{year}/{num}", f"{num}/{yy}", f"{yy}/{num}"]
    if typ in ("L", "D"):
        keys += [f"{year}/{num}/", f"{yy}/{num}/"]
    return keys


def sentences(txt):
    for s in re.split(r'(?<=[.;:!?])\s+|\n+', txt):
        s = s.strip()
        if 12 <= len(s) <= 700:
            yield s


def locate(txt, keys):
    hits = []
    for s in sentences(txt):
        for k in keys:
            if re.search(r'(?<![\d/])' + re.escape(k) + r'(?![\d/])', s, re.I):
                hits.append({"key": k, "sentence": s[:420]}); break
        if len(hits) >= 2:
            break
    return hits


def main():
    truth = json.load(open(sys.argv[1], encoding="utf-8")); out = pathlib.Path(sys.argv[2])
    rec = json.load(open(out / "audit-200.json", encoding="utf-8"))
    avail = json.load(open(out / "eurlex-text-availability.json", encoding="utf-8"))
    facts = {f["id"]: f for f in truth["facts"]}; nodes = {n["id"]: n for n in truth["nodes"]}
    cache = {}

    def text_of(celex):
        if celex in cache: return cache[celex]
        src, txt = "html", ""
        try:
            if avail.get(celex) == "html":
                txt = html_text(celex)
            if len(txt) < 2000:
                src, txt = "pdf", pdf_text(celex)
        except Exception as e:
            src, txt = "error", ""
        cache[celex] = (src, txt); return cache[celex]

    def one(fid):
        f = facts[fid]; a, b = nodes[f["s"]], nodes[f["o"]]
        src, txt = text_of(a["celex"])
        keys = keys_for(b["celex"])
        hits = locate(txt, keys) if txt else []
        return fid, {"a": a["celex"], "b": b["celex"], "source": src, "chars": len(txt), "keys": keys, "hits": hits}

    t0 = time.time(); res = {}
    prev = json.load(open(out / "extracts.json", encoding="utf-8")) if (out / "extracts.json").exists() else {}
    for fid in rec["facts"]:
        if prev.get(fid, {}).get("hits") or prev.get(fid, {}).get("source") in ("html", "pdf"):
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
