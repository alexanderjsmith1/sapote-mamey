"""pubmed_ingest.py — scalable PubMed search-result PDF → structured, searchable literature corpus.

Parses a whole folder of PubMed "Search Results" PDFs (each a LIST of abstracts) into ONE record
per unique PMID, deduped across files, and writes:
  - literature_corpus.jsonl   (one JSON record per unique abstract — the portable corpus)
  - literature_corpus.sqlite  (FTS5 full-text search over title+abstract+authors; falls back to a
                               plain table + LIKE if the SQLite build lacks FTS5)
  - _manifest.json            (per-PDF entry counts, total unique PMIDs, query tags)

Reusable: drop more PDFs in the input folder and re-run — dedup by PMID merges cleanly.
Offline, stdlib + pypdf only. No email / personal id. Abstracts are literature CONTEXT (class-level,
similarity not identity, bioactivity extract-level, judgment deferred) — this tool only STORES them.

Usage: python pubmed_ingest.py <pdf_dir> <out_dir>
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
import json, re, sqlite3, sys
from pathlib import Path

from pypdf import PdfReader

_PMID = re.compile(r"PMID:\s*(\d+)")
_DOI = re.compile(r"\bdoi:\s*(\S+?)(?:\.?$|\s)", re.I)
_YEAR = re.compile(r"\b(19|20)\d{2}\b")
# a citation-date line starts each entry: ". 2026 Feb 24:17:1786444." / ". 2025 Apr 22;16(1):3446."
_CITE = re.compile(r"\.\s*(?:19|20)\d{2}\b[^\n]*")


def _query_from_name(name: str) -> str:
    # "streptomyces lasso peptide - Search Results - PubMed 2.pdf" -> "streptomyces lasso peptide"
    base = re.sub(r"\.pdf$", "", name, flags=re.I)
    base = re.split(r"\s*-\s*Search Results", base)[0]
    return base.strip().lower()


def _pdf_text(path: Path) -> str:
    try:
        r = PdfReader(str(path))
        return "\n".join((pg.extract_text() or "") for pg in r.pages)
    except Exception as e:  # noqa: BLE001
        emit(f"  ! {path.name}: {type(e).__name__}: {e}", file=sys.stderr)
        return ""


def _title_from_pre(pre: str) -> tuple[str, str]:
    """pre = text between the previous entry's PMID and this entry's PMID. It ends with this entry's
    citation-date line + title + authors. Return (title, year) from AFTER the last citation line."""
    cites = list(_CITE.finditer(pre))
    seg = pre[cites[-1].end():] if cites else pre
    year = _YEAR.search(cites[-1].group(0)).group(0) if cites else ""
    lines = [ln.strip() for ln in seg.splitlines() if ln.strip()]
    title_parts = []
    for ln in lines:
        if re.search(r"Affiliation|PMID:", ln):
            break
        # authors line: comma-heavy, capitalized, not a sentence -> title ends
        if title_parts and ln.count(",") >= 3 and ln[:1].isupper() and "." not in ln[:40]:
            break
        title_parts.append(ln)
        if len(title_parts) >= 4:
            break
    return " ".join(title_parts).strip(), year


def _abstract_from_post(post: str) -> str:
    """post = text after this entry's PMID up to the next entry's PMID. This entry's abstract is the
    text after 'Abstract', but BEFORE the next entry's citation-date line (which starts entry k+1)."""
    nxt = _CITE.search(post)
    body = post[:nxt.start()] if nxt else post
    am = re.search(r"\bAbstract\b(.*)", body, re.S)
    if not am:
        return ""
    return re.sub(r"\s+", " ", am.group(1)).strip()[:6000]


def parse_text(txt: str) -> list[dict]:
    """PMID-anchored: one record per PMID, pairing the title BEFORE it with the abstract AFTER it."""
    pmids = list(_PMID.finditer(txt))
    out = []
    for k, m in enumerate(pmids):
        pre = txt[(pmids[k - 1].end() if k else 0):m.start()]
        post = txt[m.end():(pmids[k + 1].start() if k + 1 < len(pmids) else len(txt))]
        title, year = _title_from_pre(pre)
        if not title:
            continue
        doi_m = _DOI.search(txt[m.start():m.start() + 200])
        out.append({"pmid": m.group(1), "title": title, "year": year,
                    "doi": doi_m.group(1).rstrip(".") if doi_m else "",
                    "authors": "", "abstract": _abstract_from_post(post)})
    return out


def ingest(pdf_dir: str, out_dir: str) -> dict:
    pdir, odir = Path(pdf_dir), Path(out_dir)
    odir.mkdir(parents=True, exist_ok=True)
    corpus: dict[str, dict] = {}
    per_file = {}
    for pdf in sorted(pdir.glob("*.pdf")):
        q = _query_from_name(pdf.name)
        txt = _pdf_text(pdf)
        n = 0
        for rec in parse_text(txt):
            n += 1
            pid = rec["pmid"]
            if pid in corpus:
                corpus[pid]["source_files"].append(pdf.name)
                if q not in corpus[pid]["queries"]:
                    corpus[pid]["queries"].append(q)
                if len(rec["abstract"]) > len(corpus[pid]["abstract"]):
                    corpus[pid]["abstract"] = rec["abstract"]
            else:
                rec["source_files"] = [pdf.name]
                rec["queries"] = [q]
                corpus[pid] = rec
        per_file[pdf.name] = {"query": q, "entries_parsed": n}
        emit(f"  {pdf.name}: {n} entries (query='{q}')", flush=True)

    recs = list(corpus.values())
    # JSONL
    jl = odir / "literature_corpus.jsonl"
    with jl.open("w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    # SQLite FTS (fallback to plain)
    dbp = odir / "literature_corpus.sqlite"
    if dbp.exists():
        dbp.unlink()
    con = sqlite3.connect(dbp)
    fts = True
    try:
        con.execute("CREATE VIRTUAL TABLE lit USING fts5(pmid, title, authors, year, doi, abstract, queries)")
    except sqlite3.OperationalError:
        fts = False
        con.execute("CREATE TABLE lit(pmid TEXT PRIMARY KEY, title TEXT, authors TEXT, year TEXT, doi TEXT, abstract TEXT, queries TEXT)")
    for r in recs:
        con.execute("INSERT INTO lit(pmid,title,authors,year,doi,abstract,queries) VALUES (?,?,?,?,?,?,?)",
                    (r["pmid"], r["title"], r["authors"], r["year"], r["doi"], r["abstract"], " ".join(r["queries"])))
    con.commit(); con.close()

    manifest = {"unique_pmids": len(recs), "pdfs": len(per_file), "fts5": fts,
                "with_abstract": sum(1 for r in recs if r["abstract"]),
                "per_file": per_file, "queries": sorted({q for r in recs for q in r["queries"]})}
    (odir / "_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    emit(f"\nCORPUS: {len(recs)} unique PMIDs ({manifest['with_abstract']} with abstract) "
          f"from {len(per_file)} PDFs. FTS5={fts}. -> {jl.name}, {dbp.name}, _manifest.json")
    return manifest


if __name__ == "__main__":
    if len(sys.argv) != 3:
        emit("usage: python pubmed_ingest.py <pdf_dir> <out_dir>"); sys.exit(2)
    ingest(sys.argv[1], sys.argv[2])
