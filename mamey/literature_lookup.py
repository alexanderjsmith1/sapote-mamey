"""literature_lookup.py — retrieve full PubMed abstracts (and search them) from the in-bundle corpus.

The bundle ships a portable, PURGEABLE literature corpus at
`mamey/data/literature/_corpus/literature_corpus.jsonl` — one JSON record per unique PMID with the
FULL abstract text. The per-genus/`_families/*.md` KB files are a curated INDEX (PMID-cited bullets)
into this corpus. This module is the reader side: pull a full abstract by PMID for a Mode B card or
the ecological synthesis, or keyword-search the corpus.

Stdlib only; no SQLite dependency (linear scan over a few thousand records is instant). If the corpus
is absent (e.g. purged for a public release) every function degrades cleanly to empty results.

CLAIM CEILING: abstracts are class-level literature CONTEXT — similarity not identity, capacity not
production, bioactivity extract/strain-level, no structure/novelty claim; judgment deferred. This
module only STORES and RETRIEVES literature; it makes no claim.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit
import json
import re
from functools import lru_cache
from pathlib import Path

_CORPUS_REL = "data/literature/_corpus/literature_corpus.jsonl"


def corpus_path() -> Path:
    """Resolve the literature corpus JSONL.

    v9.7.371 fix: was hardcoded to the legacy in-tree path only, bypassing external_data.py's
    registered "literature" dataset (env_var MAMEY_LITERATURE_CORPUS -> $MAMEY_DATA_ROOT/literature
    -> legacy in-tree path, in that order). external_data.py's own docstring warns that a caller
    which cannot find its dataset "must then render NOT MEASURED, never an empty result that reads
    like a measured zero" -- but this module silently returned an empty corpus regardless of
    whether an operator had correctly re-provisioned it via MAMEY_LITERATURE_CORPUS/MAMEY_DATA_ROOT
    (e.g. after purging the in-tree copy for a public release, since PubMed abstracts are not
    redistributable per external_data.py's own licence note). Falls back to the legacy in-tree path
    if external_data resolution fails for any reason, preserving prior behavior exactly when no
    dataset is provisioned at all.
    """
    try:
        from .external_data import resolve
        p = resolve("literature")
        if p is not None:
            return p / "literature_corpus.jsonl"
    except Exception:
        pass
    return Path(__file__).resolve().parent / _CORPUS_REL


@lru_cache(maxsize=1)
def load_corpus(path: str | None = None) -> dict[str, dict]:
    """{pmid: record}. Cached. Empty dict if the corpus is absent (purged/public tier)."""
    p = Path(path) if path else corpus_path()
    if not p.exists():
        return {}
    out: dict[str, dict] = {}
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("pmid"):
                out[str(r["pmid"])] = r
    return out


def lookup(pmid: str | int, path: str | None = None) -> dict | None:
    """Full record for a PMID (title, year, doi, abstract, queries, source_files) or None."""
    return load_corpus(path).get(str(pmid))


def abstract_for(pmid: str | int, path: str | None = None) -> str:
    """The full abstract text for a PMID, or '' if unknown / no abstract in the export."""
    r = lookup(pmid, path)
    return r.get("abstract", "") if r else ""


def _terms(query: str) -> tuple[list[str], bool]:
    """Parse a simple query: 'a AND b' (all), 'a OR b' (any), or bare terms (all). Returns (terms, all_)."""
    q = query.strip()
    if re.search(r"\bOR\b", q, re.I):
        return ([t.lower() for t in re.split(r"\bOR\b", q, flags=re.I) if t.strip()], False)
    parts = re.split(r"\bAND\b", q, flags=re.I) if re.search(r"\bAND\b", q, re.I) else q.split()
    return ([t.strip().lower() for t in parts if t.strip()], True)


def search(query: str, limit: int = 20, path: str | None = None) -> list[dict]:
    """Keyword search over title+abstract+queries. 'AND'/'OR' supported (default AND). Ranked by
    match count then recency. Returns lightweight hits: {pmid, year, title, snippet}."""
    terms, all_ = _terms(query)
    if not terms:
        return []
    hits = []
    for r in load_corpus(path).values():
        blob = (r.get("title", "") + " " + r.get("abstract", "") + " " + " ".join(r.get("queries", []))).lower()
        present = [t for t in terms if t in blob]
        ok = (len(present) == len(terms)) if all_ else bool(present)
        if not ok:
            continue
        yr = int(r["year"]) if str(r.get("year", "")).isdigit() else 0
        hits.append((len(present), yr, r))
    hits.sort(key=lambda x: (-x[0], -x[1]))
    out = []
    for _, _, r in hits[:limit]:
        ab = r.get("abstract", "")
        out.append({"pmid": r["pmid"], "year": r.get("year", ""), "title": r.get("title", ""),
                    "snippet": (ab[:240] + " …") if len(ab) > 240 else ab})
    return out


def stats(path: str | None = None) -> dict:
    c = load_corpus(path)
    return {"records": len(c), "with_abstract": sum(1 for r in c.values() if r.get("abstract")),
            "corpus_present": bool(c), "path": str(path or corpus_path())}


def literature_command(args) -> int:
    sub = getattr(args, "lit_cmd", None)
    if sub == "lookup":
        r = lookup(args.pmid)
        if not r:
            emit(f"PMID {args.pmid}: not in corpus"); return 1
        emit(f"PMID {r['pmid']} · {r.get('year','')} · {r.get('doi','')}", r.get("title", ""), sep="\n")
        emit()
        emit(r.get("abstract", "") or "(no abstract in this export entry)")
        return 0
    if sub == "search":
        rows = search(args.query, limit=getattr(args, "limit", 20))
        emit(f"{len(rows)} hit(s) for {args.query!r}:")
        for h in rows:
            emit(f"  {h['year']}  PMID {h['pmid']}  {h['title'][:80]}")
        return 0
    s = stats()
    emit(f"literature corpus: {s['records']} records, {s['with_abstract']} with abstract "
          f"(present={s['corpus_present']}) -> {s['path']}")
    return 0
