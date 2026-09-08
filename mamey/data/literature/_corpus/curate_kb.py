"""curate_kb.py — derive claim-safe, PMID-cited genus/family KB markdown from literature_corpus.jsonl.

Reproducible (re-run when the corpus grows) and provenance-rich (every bullet cites its PMID).
Ranks each target's abstracts by PROJECT relevance (antifungal/anti-Candida, bee/insect symbiont,
the cohort's warhead classes, biosynthetic/genome-mining) + recency, emits the top-N as bullets in
the exact bundle-KB format (portable/purgeable header + claim ceiling). Abstracts are literature
CONTEXT only: capacity/class-level, similarity not identity, bioactivity extract-level, judgment
deferred — nothing here is a production/structure/novelty claim.

Usage: python curate_kb.py <corpus.jsonl> <literature_dir> [--only Streptomyces,lassopeptide]
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from ....console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))
    from mamey.console import emit
import json, re, sys
from pathlib import Path

# project-relevance keywords (weighted). higher = more central to the bee-antifungal thesis + cohort.
_KW = {
    "antifungal": 5, "candida": 5, "anti-candida": 6, "antimicrobial": 2, "antibacterial": 2,
    "mrsa": 3, "staphylococc": 2, "bioactiv": 2, "inhibit": 1,
    "bee": 5, "wasp": 4, "insect": 3, "symbio": 4, "honey": 3, "hymenopter": 4,
    "biosynthetic gene cluster": 3, "bgc": 3, "genome min": 3, "antismash": 3, "novel": 2,
    "lanthipeptide": 3, "lasso": 3, "ripp": 2, "hsaf": 4, "maltophilin": 3, "tetramate": 3,
    "polycyclic tetramate": 4, "phosphonate": 3, "enediyne": 4, "spirotetronate": 3,
    "glycopeptide": 3, "halogenat": 3, "siderophore": 2, "metallophore": 2, "macrolide": 2,
    "polyene": 3, "nystatin": 3, "amphotericin": 2,
}
# target -> (queries that feed it, optional header note, is_family)
_TARGETS = {
    "Streptomyces": (["streptomyces", "streptomyces candida", "bee streptomyces",
                      "streptomyces lasso peptide", "streptomyces ptm"], None, False),
    "Micromonospora": (["micromonospora", "verrucosispora"],
                       "Verrucosispora is reclassified INTO *Micromonospora* (Micromonosporaceae); its "
                       "chemistry is recorded here as *Micromonospora* sensu lato.", False),
    "Nocardia": (["nocardia"], None, False),
    "Saccharopolyspora": (["saccharopolyspora"], None, False),
    "Actinophytocola": (["actinophytocola"], None, False),
    "hsaf": (["hsaf", "streptomyces ptm"],
             "HSAF (heat-stable antifungal factor / dihydromaltophilin) is a POLYCYCLIC TETRAMATE "
             "MACROLACTAM (PTM); PTM is the broader warhead family. Hybrid iterative PKS-NRPS + OX "
             "tailoring; antifungal via membrane/sterol + ROS.", True),
    "lassopeptide": (["streptomyces lasso peptide"],
                     "Lasso peptides are RiPPs with a threaded rotaxane topology (protease/thermal "
                     "stable); class-level capacity only.", True),
    "actinomycete_biosynthesis": (["actinomycete biosynthesis"],
                     "Genus-agnostic general KB; manual authoring reference (not auto-injected).", True),
}

_HDR = ("<!-- PURGEABLE for public release: open-access PubMed abstract CONTEXT, corpus-derived "
        "(curate_kb.py). Class-level literature only — similarity not identity, capacity not "
        "production, bioactivity is extract/strain-level, judgment deferred. -->\n")


def _score(rec) -> int:
    blob = (rec.get("title", "") + " " + rec.get("abstract", "")).lower()
    s = sum(w for k, w in _KW.items() if k in blob)
    y = rec.get("year", "")
    if y.isdigit() and int(y) >= 2023:
        s += 2
    if rec.get("abstract"):
        s += 1
    return s


_STOP = {"the", "and", "of", "a", "in", "for", "to", "with", "from", "on", "by", "as", "an",
         "novel", "new", "study", "here", "we", "report", "using", "via", "their", "its"}


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", s.lower()) if w not in _STOP}


def _is_junk_title(title: str) -> bool:
    letters = re.sub(r"[^A-Za-z]", "", title)
    return len(letters) < 15  # a real title has ≥15 letters; page-number artifacts don't


def _takeaway(rec, queries) -> str:
    """Show an abstract snippet ONLY if it coheres with the title or a query term (guards against
    the export interleaving a neighbouring entry's abstract). Otherwise a title-level note."""
    ab = rec.get("abstract", "")
    ab = re.sub(r"^(Background|Introduction|Abstract|Objective[s]?)\s*:?\s*", "", ab).strip()
    if not ab:
        return "title-level literature context (no abstract in this export entry)"
    tw, aw = _words(rec.get("title", "")), _words(ab[:400])
    # The parser is now PMID-anchored (abstract paired to its own PMID), so a light backstop suffices:
    # require >=1 shared content word between title and abstract; else fall back to title-level.
    if not (tw & aw):
        return "title-level literature context (full abstract by PMID in _corpus/)"
    # keep the first ~2 sentences (fuller takeaway); the FULL abstract lives in _corpus/ keyed by PMID.
    sents = re.split(r"(?<=[.!?])\s+", ab)
    snip = " ".join(sents[:2])
    if len(snip) > 520:
        snip = snip[:520].rsplit(" ", 1)[0] + " …"
    return snip


def curate_one(name, cfg, recs) -> str:
    queries, note, is_family = cfg
    qs = set(queries)
    sel = [r for r in recs if (qs & set(r.get("queries", []))) and not _is_junk_title(r.get("title", ""))]
    sel.sort(key=lambda r: (-_score(r), -(int(r["year"]) if r.get("year", "").isdigit() else 0)))
    top = sel[:28]
    disp = name.replace("_", " ")
    L = [_HDR]
    if is_family:
        L.append(f"# Family literature context — {disp}\n")
    else:
        L.append(f"# Genus literature context — *{name}*\n")
    L.append("**Claim ceiling:** class-level capacity, similarity not identity, bioactivity "
             "extract/strain-level, no structure/novelty claim, judgment deferred.\n")
    if note:
        L.append(f"> {note}\n")
    L.append(f"\n_Corpus-derived: top {len(top)} of {len(sel)} project-relevant abstracts (PMID-cited)._\n")
    for r in top:
        title = re.sub(r"\s+", " ", r.get("title", "")).strip().rstrip(".")
        title = re.sub(r"([a-z]{2})([A-Z][a-z])", r"\1 \2", title)  # fix pypdf line-join "inStreptomyces"
        cite = f"{r.get('year','')}, PMID {r['pmid']}"
        L.append(f"- **{title}** ({cite}) — {_takeaway(r, queries)}.")
    return "\n".join(L) + "\n"


def main(corpus, litdir, only=None):
    recs = [json.loads(l) for l in Path(corpus).open(encoding="utf-8")]
    litdir = Path(litdir); (litdir / "_families").mkdir(parents=True, exist_ok=True)
    targets = _TARGETS if not only else {k: v for k, v in _TARGETS.items() if k in only}
    written = []
    for name, cfg in targets.items():
        md = curate_one(name, cfg, recs)
        sub = cfg[2]
        path = (litdir / "_families" / f"{name}.md") if sub else (litdir / f"{name}.md")
        path.write_text(md, encoding="utf-8")
        written.append((str(path.relative_to(litdir)), md.count("\n- **")))
    for p, n in written:
        emit(f"  wrote {p}: {n} bullets")
    return written


if __name__ == "__main__":
    a = sys.argv[1:]
    only = None
    if "--only" in a:
        i = a.index("--only"); only = set(a[i + 1].split(",")); a = a[:i] + a[i + 2:]
    if len(a) != 2:
        emit("usage: python curate_kb.py <corpus.jsonl> <literature_dir> [--only A,B]"); sys.exit(2)
    main(a[0], a[1], only)
