"""A damage generator for documents, and the judge that goes with it.

Le Corrigé injects into a graph. This injects into the documents a graph is built from, which is
the only place the information a deletion-only repair cannot reach still exists. Same three organs
and the same discipline: a frozen truth with its sha256, an injection sealed by a seed with a
journal of exactly what was done, and a judge that compares what a reader gets back against what
the document declared.

WHAT IS NOT CLAIMED. Typed, calibrated error injection into a test set is established method — see
LED (Layout Error Detection, arXiv 2507.23295), which injects eight error types with distributions
estimated from real system outputs. Pixel-level degradation is a crowded field: Genalog, DocCreator,
PreP-OCR. Together they cover 43 of the atlas's 170 forms, the ones at the pixel and reading layers,
and this module calls them rather than rebuilding them. What is not covered anywhere is the other
127: faults of the utterance, the extraction, the anchoring, the resolution, the schema, the
coherence, the structure and the retrieval — faults about the FACTS a document supports, not about
its picture or its boxes.

WHY A JATS FILE NEEDS NO ANNOTATION. It declares its own identifiers, its date, its authors. The
truth of a document is therefore readable from the document, and the whole measurement runs with
no human labelling: freeze, damage, read again, compare.

THE RULE THAT MAKES IT HONEST. A damaged document must stay a PLAUSIBLE document. If the injection
leaves a trace a reader can catch by something other than the fault itself — broken XML, an
impossible date, a mismatched tag — the measurement is worthless, because the reader is detecting
the injection and not the fault. Every injector here asserts that the result still parses and that
nothing but the intended field changed.
"""
import datetime, hashlib, json, random, re
from pathlib import Path

# ── the facts a JATS file declares about itself ────────────────────────────────────────────────
FIELDS = {
    "doi":   (r'<article-id[^>]*pub-id-type="doi"[^>]*>([^<]+)</article-id>', 1),
    "pmid":  (r'<article-id[^>]*pub-id-type="pmid"[^>]*>([^<]+)</article-id>', 1),
    "pmc":   (r'<article-id[^>]*pub-id-type="pmc(?:id)?"[^>]*>([^<]+)</article-id>', 1),
    # Bounded to the element on purpose. Unbounded — `<pub-date[^>]*>.*?<year>(\d{4})</year>` with
    # re.S, which is what this read until the generator caught it — the pattern scans past the end
    # of every pub-date and matches the `<year>` of `<history><date date-type="received">`. It then
    # reports the date the manuscript was RECEIVED as the date it was PUBLISHED, and looks right
    # because the two usually share a year. Measured here: 118 documents of 200.
    "year":  (r'<pub-date[^>]*>(?:(?!</pub-date>).)*?<year>(\d{4})</year>', 1),
    "title": (r'<title-group>\s*<article-title>(.*?)</article-title>', 1),
}


# Bounded to its own element, and the boundary is not decoration. Unbounded — `.*?` with re.S —
# a single <contrib> opens a scan that runs to the end of the document and matches a surname in
# the reference list. The first version of this read one author on an article that has twelve,
# and the one it read was a cited author. It is the same fault as the unbounded year pattern that
# read a reception date as a publication date, made twice in one evening by the same hand.
AUTHOR = re.compile(
    r'<contrib[^>]*contrib-type="author"[^>]*>(?:(?!</contrib>).)*?<surname[^>]*>([^<]*)</surname>'
    r'\s*<given-names[^>]*>([^<]*)</given-names>', re.S)


def authors(xml):
    """Every author the document declares, surname then given names, in order of appearance.
    Structured in JATS, so the truth is exact and the judgement needs no annotation."""
    return [f"{g.strip()} {sn.strip()}".strip() for sn, g in AUTHOR.findall(xml)]


def facts(xml):
    """What a reader should get back. One value per field, the first the document declares."""
    out = {}
    for name, (pat, g) in FIELDS.items():
        m = re.search(pat, xml, re.S)
        if m:
            out[name] = re.sub(r"<[^>]+>", "", m.group(g)).strip()
    a = authors(xml)
    if a:
        out["authors"] = " | ".join(a)
    return out


# ── two readers of the same document, so that "a better assembly recovers more" stops being an
# opinion. The plain one is what anybody writes first: one value per field, the first declaration
# it meets. The careful one reads every declaration and keeps the disagreements. Neither is clever;
# the difference between them is entirely in WHERE THEY LOOK.
ALL = {
    "doi":     r'<article-id[^>]*pub-id-type="doi"[^>]*>([^<]+)</article-id>',
    "pmid":    r'<article-id[^>]*pub-id-type="pmid"[^>]*>([^<]+)</article-id>',
    "pmc":     r'<article-id[^>]*pub-id-type="pmc(?:id)?"[^>]*>([^<]+)</article-id>',
    "year":    r'<pub-date[^>]*>(?:(?!</pub-date>).)*?<year>([^<]+)</year>',
    "title":   r'<title-group>\s*<article-title>(.*?)</article-title>',
}
# Where a second spelling of a thing is allowed to live in JATS, and which field it is about.
ALSO = {"authors": [r'<alt-title[^>]*running-head[^>]*>([^<]*)</alt-title>',
                    r'<string-name[^>]*>([^<]*)</string-name>']}


def facts_careful(xml):
    """Every declaration, not the first: a value is returned only if the document agrees with
    itself, and otherwise the disagreement is returned in its place.

    This reader is not smarter than the plain one and knows nothing it does not know. It looks in
    more places, and that is the whole difference — which is the point being measured."""
    out = {}
    for name, pat in ALL.items():
        vals = [re.sub(r"<[^>]+>", "", v).strip() for v in re.findall(pat, xml, re.S)]
        vals = [v for v in vals if v]
        if not vals:
            continue
        uniq = list(dict.fromkeys(vals))
        out[name] = uniq[0] if len(uniq) == 1 else "DISAGREEMENT: " + " ≠ ".join(uniq[:3])
    a = authors(xml)
    extra = [re.sub(r"<[^>]+>", "", v).strip()
             for pat in ALSO["authors"] for v in re.findall(pat, xml, re.S)]
    extra = [v for v in extra if v]
    if a:
        out["authors"] = " | ".join(a) if not extra else "DISAGREEMENT: " + " | ".join(a) + " ≠ " + " ≠ ".join(extra[:2])
    return out


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def truth(path):
    """Freeze a document and what it declares. The sha256 is of the file as read, byte for byte."""
    xml = Path(path).read_text(encoding="utf-8", errors="replace")
    return {"document": Path(path).name, "sha256": sha(xml), "facts": facts(xml),
            "read": datetime.date.today().isoformat(), "characters": len(xml)}


# ── the damages, one per atlas form, each on a real observed shape ──────────────────────────────
# The name is the atlas form it instantiates; the docstring is what the form says the world does.

def _rewrite(xml, field, fn, every=False):
    """Rewrite the value of a field IN THE VERY SPAN THE READER READS.

    The first version of this module aimed at `<year>` directly while the reader read the `<year>`
    inside `<pub-date>`, and a JATS file carries two. The damage was written down as posed and the
    reader got the true value back: a fault the generator invented and then hid from itself. An
    injector must use the reader's own locator or it is measuring nothing. It does now."""
    pat, g = FIELDS[field]
    m = re.search(pat, xml, re.S)
    if not m:
        return None, None
    if not every:
        a, b = m.span(g)
        return xml[:a] + fn(m.group(g)) + xml[b:], m.group(0)
    # A producer's writing convention is uniform: it damages every declaration, not the first.
    # Measured before this was fixed: form-198 reached 10 readers of 200 because a JATS declares
    # its year twice and only one was touched. That figure measured the injector, not the world.
    v = m.group(g)
    out = re.sub(DECLARED[field](v), lambda mm: mm.group(0).replace(v, fn(v)), xml, flags=re.S)
    return out, m.group(0)


def form_198_year_shape(xml, rng):
    """form-198 — one date field, four ways of writing a year. The NLM writes (AAAA), (AA), a bare
    year and an interval; a reader built for one shape finds 12.5 % of them."""
    shape = rng.choice(["two-digit", "interval", "bare-with-season"])
    fn = {"two-digit": lambda y: y[2:],
          "interval": lambda y: f"{y}-{int(y) + 1}",
          "bare-with-season": lambda y: f"Spring {y}"}[shape]
    # every=True: the NLM does not write one date in one shape and the next in another.
    out, was = _rewrite(xml, "year", fn, every=True)
    return out, {"form": "form-198", "damage": "WRONG_VALUE", "field": "year",
                 "shape": shape, "was": was}


def form_192_doi_separator(xml, rng):
    """form-192 — an identifier that contains the separator used to split it, as the NLM writes
    10.1590/1984-0462/;2018;36;4;00019erratum."""
    out, was = _rewrite(xml, "doi", lambda v: f"{v}/;{rng.randint(2015, 2025)};{rng.randint(1, 60)}")
    return out, {"form": "form-192", "damage": "WRONG_VALUE", "field": "doi", "was": was}


def form_191_identifier_family(xml, rng):
    """form-191 — two identifier families in one field: a reader accepting only digits skips the
    PMCID ones in silence, and they are the richest documents in the base."""
    out, was = _rewrite(xml, "pmid", lambda v: "PMC" + v)
    return out, {"form": "form-191", "damage": "MISSING", "field": "pmid", "was": was}


def form_118_invisible(xml, rng):
    """A zero-width character inside an identifier. Measured in the house filter bench: 1,569
    invisibles in a single PDF, and one of them breaks a checksum."""
    def fn(v):
        i = rng.randrange(1, max(2, len(v)))
        return v[:i] + "\u200b" + v[i:]
    out, was = _rewrite(xml, "doi", fn)
    return out, {"form": "form-118", "damage": "WRONG_VALUE", "field": "doi", "was": was}


def form_107_second_doi(xml, rng):
    """form-107 — several DOIs per document, 27 of 272 articles (9 %).

    DERIVED FROM THE OBSERVATION, NOT FROM ANY READER: the form records the real pair
    `10.1371/journal.pcbi.1014325` and `10.1371/journal.pcbi.1014325.r001`, a review-report DOI
    built from the article's own by appending `.rNNN`. The injection writes that second
    declaration and changes nothing else."""
    pat, g = FIELDS["doi"]
    m = re.search(pat, xml, re.S)
    if not m:
        return None, None
    second = m.group(0).replace(m.group(g), f"{m.group(g)}.r{rng.randint(1, 3):03d}")
    return xml[:m.end()] + second + xml[m.end():], {
        "form": "form-107", "damage": "MERGE", "field": "doi",
        "derived_from": "form-107 seen 2026-08-08: 10.1371/journal.pcbi.1014325 and …1014325.r001",
        "was": m.group(0)}


def form_026_homonym(xml, rng):
    """form-026 — strict homonyms, 1,215 surnames of 9,160 (13.3 %) borne by two or more different
    given names.

    DERIVED FROM THE OBSERVATION: the form names the three commonest carriers in the corpus it was
    measured on — Wang by 95 given names, Li by 92, Chen by 88. The injection renames one author's
    surname to one of those three, which is what a corpus does to a resolver keyed on the surname."""
    ms = list(AUTHOR.finditer(xml))
    if not ms:
        return None, None
    m = ms[rng.randrange(len(ms))]
    a, b = m.span(1)
    into = rng.choice(["Wang", "Li", "Chen"])
    # A rename to the name already borne is a blow into the air. Counted as a damage it inflates
    # the denominator and lowers every rate computed from it: six of 300 on the first run.
    if m.group(1).strip() == into:
        return None, None
    return xml[:a] + into + xml[b:], {
        "form": "form-026", "damage": "MERGE", "field": "authors", "into": into,
        "derived_from": "form-026 seen 2026-08-08: Wang borne by 95 given names, Li by 92, Chen by 88",
        "was": m.group(1)}


def form_120_running_head(xml, rng):
    """form-120 — a running head carrying a spelling that appears nowhere else, 23 of 272 (8.5 %).

    DERIVED FROM THE OBSERVATION: the form records `<given-names>Xianyun</given-names>
    <surname>Shao</surname>` on page one against a running head reading `X. Shao et al.`. The
    injection writes that second spelling of the first author as an alt-title, which is the shape
    the corpus was seen to carry."""
    ms = list(AUTHOR.finditer(xml))
    m2 = re.search(r"</title-group>", xml)
    if not ms or not m2:
        return None, None
    sn, g = ms[0].group(1).strip(), ms[0].group(2).strip()
    head = f'<alt-title alt-title-type="running-head">{g[:1]}. {sn} et al.</alt-title>'
    return xml[:m2.start()] + head + xml[m2.start():], {
        "form": "form-120", "damage": "SPLIT", "field": "authors", "wrote": f"{g[:1]}. {sn} et al.",
        "derived_from": "form-120 seen 2026-08-08 on PMC13162546: page one gives Xianyun Shao, the running head gives X. Shao et al.",
        "was": f"{g} {sn}"}


DAMAGES = {"form-198": form_198_year_shape, "form-192": form_192_doi_separator,
           "form-191": form_191_identifier_family, "form-118": form_118_invisible,
           "form-107": form_107_second_doi, "form-026": form_026_homonym,
           "form-120": form_120_running_head}


# Injections that legitimately ADD a declaration rather than rewrite one. The markup guard has
# to know about them, or it refuses a correct injection: form-107 writes a second article-id and
# form-120 writes an alt-title, and both are what the corpus was observed to carry.
DECL_ADDS = {"form-107": '<article-id pub-id-type="doi"></article-id>',
             "form-120": '<alt-title alt-title-type="running-head"></alt-title>'}


def inject(path, kinds, seed):
    """Damage a document, sealed by a seed, and write down exactly what was done.

    Refuses to return a document that stopped being a document: same tag count, same length of
    every field but the one aimed at. A reader that catches the injection by anything other than
    the fault is measuring our clumsiness, not its own skill."""
    xml = Path(path).read_text(encoding="utf-8", errors="replace")
    before_tags = len(re.findall(r"<[a-zA-Z][^>]*>", xml))
    rng = random.Random(f"{seed}|{Path(path).name}")
    journal, out = [], xml
    for k in kinds:
        got, entry = DAMAGES[k](out, rng)
        if got is None:
            journal.append({"form": k, "skipped": "the document does not carry the field"})
            continue
        out, _ = got, journal.append(entry)
    after_tags = len(re.findall(r"<[a-zA-Z][^>]*>", out))
    added = sum(len(re.findall(r"<[a-zA-Z][^>]*>", DECL_ADDS.get(e["form"], ""))) for e in journal
                if "skipped" not in e)
    if after_tags != before_tags + added:
        raise ValueError(f"the injection changed the markup ({before_tags} -> {after_tags} tags): "
                         "a reader would catch the injection and not the fault")
    return out, {"document": Path(path).name, "seed": seed, "truth_sha256": sha(xml),
                 "injected": [j for j in journal if "skipped" not in j],
                 "skipped": [j for j in journal if "skipped" in j],
                 "sha256": sha(json.dumps(journal, sort_keys=True, ensure_ascii=False))}


# How the document DECLARES a field, as opposed to merely containing the string. Counting the bare
# string overcounts wildly: a first run found eleven copies of "2023" in one article, which were the
# bibliography. A declaration is the value inside the element that makes it that field.
DECLARED = {
    "doi":   lambda v: r'<article-id[^>]*pub-id-type="doi"[^>]*>' + re.escape(v) + r'</article-id>',
    "pmid":  lambda v: r'<article-id[^>]*pub-id-type="pmid"[^>]*>' + re.escape(v) + r'</article-id>',
    "pmc":   lambda v: r'<article-id[^>]*pub-id-type="pmc(?:id)?"[^>]*>' + re.escape(v) + r'</article-id>',
    # scoped to pub-date: a reference list declares years too, and they are not this article's
    "year":  lambda v: r'<pub-date[^>]*>(?:(?!</pub-date>).)*?<year>' + re.escape(v) + r'</year>',
    "title": lambda v: r'<article-title>\s*' + re.escape(v) + r'\s*</article-title>',
}


def copies(xml, field, value):
    """How many times the document DECLARES this value as this field.

    Found on the first run of this module: a year was damaged, the journal recorded it, and the
    reader still got the true value back — because a JATS file carries two `<pub-date>` elements
    and only one was damaged. Nothing was wrong with the injection or the reader. The document
    simply says it twice.

    So a measurement of what a reader catches is confounded by how redundant the document is, and
    the redundancy has to be measured before anything else is concluded. It is the same rule as
    the house filter 016 — count the DOCUMENTS that state a fact, not the places it appears — one
    level down: inside one document, count the declarations, because they are what a damage has to
    reach. A fact declared once is a fact one injection destroys."""
    if not value or field not in DECLARED:
        return None
    return len(re.findall(DECLARED[field](value), xml, re.S))


def judge(truth_rec, damaged_xml, journal, clean_xml=None, reader=None):
    """What a plain reader gets back from the damaged document, against what the document declared.

    Per field: `held` if the reader still gets the true value, `lost` if it gets nothing, `wrong`
    if it gets something else. A field nobody damaged and that still moved is a `side effect`, and
    it is the one a generator must never produce.

    `copies` is the count of that value in the clean document. A field damaged once in a document
    that states it twice is not a failed injection and not a skilful reader: it is a redundant
    document, and it belongs in its own bucket or every rate computed here is wrong."""
    got = (reader or facts)(damaged_xml)
    aimed = {e["field"] for e in journal["injected"]}
    verdict = {}
    for field, true_value in truth_rec["facts"].items():
        now = got.get(field)
        # Four states, not three. A reader that returns "the document disagrees with itself"
        # has neither held the truth nor invented a value: it has refused to conclude and said
        # why. That is the `None` of a house filter, and counting it as `wrong` would punish the
        # only honest answer available.
        if now == true_value:
            state = "held"
        elif now is None:
            state = "lost"
        elif isinstance(now, str) and now.startswith("DISAGREEMENT:"):
            state = "flagged"
        else:
            state = "wrong"
        verdict[field] = {"state": state, "aimed_at": field in aimed,
                          "copies": copies(clean_xml, field, true_value) if clean_xml else None,
                          "truth": true_value, "read_back": now}
    def bucket(name):
        return sorted(f for f in aimed if verdict.get(f, {}).get("state") == name)
    _ = bucket
    shielded = sorted(f for f in aimed
                      if verdict.get(f, {}).get("state") == "held"
                      and (verdict[f]["copies"] or 0) > 1)
    return {"document": truth_rec["document"],
            "per_field": verdict,
            "reached the reader as a wrong value": bucket("wrong"),
            "the reader refused to conclude and said why": bucket("flagged"),
            "reached the reader as nothing at all": bucket("lost"),
            "did not reach the reader, the document states it more than once": shielded,
            "did not reach the reader, and the document states it once": [
                f for f in aimed if verdict.get(f, {}).get("state") == "held" and f not in shielded],
            "side_effects": [f for f, v in verdict.items() if not v["aimed_at"] and v["state"] != "held"]}
