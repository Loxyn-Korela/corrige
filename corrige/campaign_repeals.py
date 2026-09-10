"""Campaign: for every repeal of the truth whose repealing act's text we hold locally,
ask the text — by plain string search, no model — whether it states the repeal of the
target, and classify the answer. The point is not to replace the register but to measure
how much of it is stated in its own documents.

    .venv-pdf/bin/python -m corrige.campaign_repeals <truth.json> <collection dir> <out.json> [--limit N]

Sources of text, in order: lot B files (textes/{fr,en}/<CELEX>.html|xml), then the official
Formex dump (LEG_{FR,EN}_FMX zip, entries <uuid>/fmx4/*.xml).

Classes, per fact:
  stated          a sentence names the target AND carries a repeal verb
  stated_in_list  the target is named under a repeal list whose lead-in carries the verb
  stated_in_annex the target is named in the annex of repealed acts that the repealing article points to (recast pattern)
  named_only    a sentence names the target, no repeal verb (reference, footnote, derogation…)
  not_named     the target is never named in the text of the repealing act
  no_key        the target has no searchable number (agreement, protocol): the question is left open
  no_text       the text of the repealing act is not held locally
"""
import sys, os, re, json, zipfile, html, collections, pathlib

REPEAL = re.compile(r"abrog|repeal|cesse(?:nt)? de produire effet|ceases? to (?:have|produce) effect|n'est plus applicable|no longer appl", re.I)
# the target is named but the sentence says something else about it
OTHER = re.compile(r"dérog|derogat|modifié(?:e|s|es)? (?:\w+ )?par|amended by|visé|referred to in", re.I)


def keys_for(celex):
    m = re.match(r"^(\d)(\d{4})[A-Z]{1,2}(\d{3,4})", celex or "")
    if not m:
        return []
    sector, year, num = m.group(1), m.group(2), int(m.group(3))
    if sector in ("2", "1"):                 # agreements, treaties: no reliable printed number
        return []
    yy = year[2:]
    return [f"{num}/{year}", f"{year}/{num}", f"{num}/{yy}", f"{yy}/{num}"]


def clean(raw):
    raw = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", raw)
    raw = re.sub(r"</(P|p|TI|ti|ALINEA|alinea|NP|np|TXT|txt|div|li|tr|td|h\d)>", "\n", raw)
    t = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return re.sub(r"[ \t ]+", " ", t)


class Texts:
    """Local text of an act, by CELEX: lot B first, then the Formex dump."""

    def __init__(self, coll):
        self.coll = pathlib.Path(coll)
        self.zips, self.by_celex = {}, {}
        for lang, name in (("fr", "LEG_FR_FMX"), ("en", "LEG_EN_FMX")):
            z = list((self.coll / "dump").glob(name + "*.zip"))
            if z:
                self.zips[lang] = zipfile.ZipFile(z[0])
        self.entries = {lang: collections.defaultdict(list) for lang in self.zips}
        for lang, z in self.zips.items():
            for n in z.namelist():
                self.entries[lang][n.split("/")[0]].append(n)
        self.uuid = {}
        idx = self.coll / "manifeste" / "dump-index.jsonl"
        if idx.exists():
            for line in open(idx, encoding="utf-8"):
                d = json.loads(line)
                if d.get("celex") and d.get("langues_fmx"):
                    self.uuid[d["celex"]] = (d["uuid"], d["langues_fmx"])
        self.lotb = {}
        for lang in ("fr", "en"):
            d = self.coll / "textes" / lang
            if d.is_dir():
                for f in d.iterdir():
                    self.lotb.setdefault(f.stem.replace("_", "/"), {})[lang] = f

    def get(self, celex):
        for lang in ("fr", "en"):
            f = self.lotb.get(celex, {}).get(lang)
            if f:
                try:
                    return clean(f.read_text(encoding="utf-8", errors="replace")), f"lotB/{lang}"
                except Exception:
                    pass
        u = self.uuid.get(celex)
        if u:
            uuid, langs = u
            for lang in ("fr", "en"):
                if lang in langs and lang in self.zips:
                    parts = []
                    for n in sorted(self.entries[lang].get(uuid, [])):
                        if n.endswith(".xml") and ".toc." not in n:
                            try:
                                parts.append(self.zips[lang].read(n).decode("utf-8", "replace"))
                            except Exception:
                                pass
                    if parts:
                        return clean("\n".join(parts)), f"dump/{lang}"
        return "", "none"


def sentences(t):
    for s in re.split(r"(?<=[.;:!?])\s+|\n+", t):
        s = s.strip()
        if 10 <= len(s) <= 900:
            yield s


LEAD = 1500          # a repeal list: "the following are repealed:" then the numbers, further down
# a recast names its repealed acts in an annex: "ANNEXE VII PARTIE A Directive abrogée avec liste
# de ses modifications successives", tens of thousands of characters after the repealing article
ANNEX = re.compile(r"(?i)(?:ANNEXE|ANNEX)\s+[IVXLC0-9]{1,6}\b[^.]{0,160}?(?:abrog|repeal)")
ANNEX_END = re.compile(r"(?i)TABLEAU DE CORRESPONDANCE|CORRELATION TABLE|TABLE DE CORRESPONDANCE")


def repeal_annexes(text):
    """Spans of the annexes that list the repealed acts."""
    spans = []
    for m in ANNEX.finditer(text):
        start = m.start()
        e = ANNEX_END.search(text, m.end())
        spans.append((start, e.start() if e else min(len(text), m.end() + 8000)))
    return spans


def classify(text, keys):
    """Three passes: the number in a sentence carrying the verb; the number under a repeal
    list whose lead-in carries the verb; the number alone."""
    hits, listed, annexed = [], [], []
    spans = repeal_annexes(text)
    for k in keys:
        for m in re.finditer(r"(?<!\d)" + re.escape(k) + r"(?!\d)", text):
            i = m.start()
            s = text[max(0, i - 300):i + 300].strip()
            sent = next((x for x in sentences(text[max(0, i - 500):i + 500]) if k in x), s)
            if REPEAL.search(sent) and not OTHER.search(sent):
                hits.append((k, sent, True, False))
            else:
                lead = text[max(0, i - LEAD):i]
                if REPEAL.search(lead) and not re.search(r"(?i)\bArticle\s+\d+", lead[lead.rfind(next(iter(REPEAL.findall(lead) or [""]), "")):] or ""):
                    lm = list(REPEAL.finditer(lead))[-1]
                    listed.append((k, (lead[max(0, lm.start() - 80):] + " ⟶ " + text[i:i + 160]).strip(), True, False))
                elif any(a <= i < b for a, b in spans):
                    annexed.append((k, "annexe des actes abrogés ⟶ " + re.sub(r"\s+", " ", text[max(0, i - 120):i + 140]).strip(), True, False))
                else:
                    hits.append((k, sent, False, bool(OTHER.search(sent))))
    verbed = [h for h in hits if h[2]]
    if verbed:
        return "stated", verbed[-1]
    if listed:
        return "stated_in_list", listed[0]
    if annexed:
        return "stated_in_annex", annexed[0]
    if hits:
        return "named_only", hits[0]
    return "not_named", None


def main():
    argv = sys.argv[1:]
    pos = [a for a in argv if not a.startswith("--")]
    truth = json.load(open(pos[0], encoding="utf-8"))
    T = Texts(pos[1])
    out = pathlib.Path(pos[2])
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    nodes = {n["id"]: n for n in truth["nodes"]}
    facts = [f for f in truth["facts"] if f["p"] == "repeals"]
    fault = {k["fact"] for k in truth.get("known_registry_faults", []) if "fact" in k}
    res, cnt, cache = {}, collections.Counter(), {}
    done = 0
    for f in facts:
        a, b = nodes[f["s"]], nodes[f["o"]]
        ca, cb = a.get("celex"), b.get("celex")
        if ca not in cache:
            if len(cache) > 400:
                cache.clear()
            cache[ca] = T.get(ca) if ca else ("", "none")
        text, src = cache[ca]
        if not text:
            cls, hit = "no_text", None
        else:
            keys = keys_for(cb)
            if not keys:
                cls, hit = "no_key", None
            else:
                cls, hit = classify(text, keys)
        cnt[cls] += 1
        res[f["id"]] = {"a": ca, "b": cb, "class": cls, "source": src,
                        "known_fault": f["id"] in fault,
                        "evidence": (hit[1][:400] if hit else None), "key": (hit[0] if hit else None)}
        done += 1
        if done % 2000 == 0:
            print(f"  {done}/{len(facts)} {dict(cnt)}", flush=True)
        if limit and done >= limit:
            break
    json.dump({"truth": truth["id"], "truth_sha256": truth["sha256"], "relation": "repeals",
               "method": "plain string search on the locally held text of the repealing act, no model; a repeal verb list including equivalent wordings",
               "counts": dict(cnt), "facts": res}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(dict(cnt))


if __name__ == "__main__":
    main()
