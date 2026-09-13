"""From documents to a graph, and what a filter upstream changes about it.

The projection at the end of measures/filters-p-2026-09-13.json joined two measurements made on
two corpora — a filter on JATS articles, a repairer on an EUR-Lex graph — and said so. This closes
that gap on one corpus that is both: JATS articles are documents a filter can read, and the facts
they declare are a graph a repairer can act on.

THE TRUTH NEEDS NO ANNOTATION, FOR THIS FORM. A running head is generated from the author list of
page one, so `I. García-Torres` in the running head of an article whose first author is
`Itzhel García-Torres` IS that person, by construction and not by guess. That is what makes this
form the right vehicle: identity is usually a judgement, and here it is a documentary fact.

WHAT IS COUNTED. A naive assembly collects author mentions wherever it finds them, which is what
an assembly does when nobody has told it where to look. Each distinct string becomes a node. The
21 documents of this corpus whose running head is abbreviated then contribute two nodes for one
person: a SPLIT, injected by the corpus itself and not by us. A deletion-only repair reaches 0 of
1,355 splits — measured 2026-09-10, three identical runs, measures/reachability-by-damage. So
every split left standing here is one nothing downstream will ever mend.
"""
import re
from pathlib import Path

HEAD = re.compile(r'<alt-title[^>]*running-head[^>]*>([^<]*)</alt-title>', re.S)
ABBREV = re.compile(r"^\s*([A-ZÀ-Ý])\.\s*(?:[A-ZÀ-Ý]\.\s*)*([A-ZÀ-Ýa-zà-ÿ'’-]+)\s*$")


def mentions(xml, authors_of):
    """Every author mention the document carries: page one, and the running head if it has one."""
    out = list(authors_of(xml))
    h = HEAD.search(xml)
    if h:
        g = h.group(1).replace("et al.", "").strip().rstrip(",").strip()
        if g and ABBREV.match(g):
            out.append(g)
    return out


def reconcile(mention, page_one):
    """The house rule, restated here so this module runs without the filter bench: an abbreviated
    spelling resolves to the page-one author it can only be, and refuses when it could be two."""
    m = ABBREV.match(mention)
    if not m:
        return mention
    ini, name = m.group(1).upper(), m.group(2)
    cand = [c for c in page_one
            if c.strip().split()[-1].casefold() == name.casefold() and c.strip()[:1].upper() == ini]
    return cand[0] if len(cand) == 1 else mention


def build(files, authors_of, with_filter=False):
    """Return (nodes, splits) — the identities the assembly creates, and the ones that are two
    nodes for one person because the corpus wrote the name twice."""
    nodes, splits = set(), []
    for f in files:
        xml = Path(f).read_text(encoding="utf-8", errors="replace")
        page_one = authors_of(xml)
        if not page_one:
            continue
        seen = mentions(xml, authors_of)
        if with_filter:
            seen = [reconcile(m, page_one) for m in seen]
        nodes.update(seen)
        extra = [m for m in seen if m not in page_one]
        for m in extra:
            mm = ABBREV.match(m)
            if mm:
                same = [c for c in page_one
                        if c.strip().split()[-1].casefold() == mm.group(2).casefold()
                        and c.strip()[:1].upper() == mm.group(1).upper()]
                if same:
                    splits.append((Path(f).name, same[0], m))
    return nodes, splits
