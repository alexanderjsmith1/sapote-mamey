#!/usr/bin/env python3
"""Parse PubMed plain-text exports into provenance-bound literature records.

This module intentionally separates bibliographic intake from BGC admission.
An abstract can describe observations in the paper's studied system; it cannot
by itself identify a product, activity, or physical linkage in a query strain.
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

import argparse
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.409 export-injection: CSV formula-cell guard
except ImportError:  # module loaded by file path without a parent package (tests do this)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = "sapote_pubmed_abstract_intake_v1"
CLAIM_CEILING = (
    "Reference-system literature may support pathway-family, enzyme-role, target-mechanism, "
    "or application context. It does not establish the query strain's exact product identity, "
    "complete pathway, physical linkage, expression, production, activity, novelty, ecology, "
    "stereochemistry, yield, or organism identity."
)


@dataclass(frozen=True)
class LiteratureRecord:
    record_number: int
    citation_line: str
    title: str
    authors: str
    abstract: str
    doi: str
    pmid: str
    pmcid: str
    publication_year: str
    record_class: str
    evidence_scope: str
    abstract_availability: str
    abstract_sha256: str
    source_file_sha256: str
    source_start_line: int
    source_end_line: int
    claim_ceiling: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _paragraphs(lines: list[str]) -> list[str]:
    out: list[str] = []
    current: list[str] = []
    for line in lines:
        clean = line.strip()
        if clean:
            current.append(clean)
        elif current:
            out.append(" ".join(current))
            current = []
    if current:
        out.append(" ".join(current))
    return out


def _record_boundaries(lines: list[str]) -> list[tuple[int, int, int]]:
    """Return sequential PubMed record boundaries.

    PubMed text can contain numbered material inside abstracts/references.  We
    therefore accept only the next monotonically expected record number.
    """
    starts: list[tuple[int, int]] = []
    expected = 1
    for index, line in enumerate(lines):
        match = re.match(r"^(\d+)\.\s+\S", line)
        if match and int(match.group(1)) == expected:
            starts.append((expected, index))
            expected += 1
    if not starts:
        raise ValueError("No sequential PubMed records found")
    return [
        (number, start, starts[pos + 1][1] if pos + 1 < len(starts) else len(lines))
        for pos, (number, start) in enumerate(starts)
    ]


def _identifier(pattern: str, text: str) -> str:
    match = re.search(pattern, text, flags=re.I | re.M)
    return match.group(1).rstrip(". ,;") if match else ""


def _classify(title: str, abstract: str) -> tuple[str, str]:
    text = f"{title} {abstract}".lower()
    if any(term in text for term in ("review", "perspective", "special issue", "recent advances")):
        return "REVIEW_ORIENTATION", "Background and terminology; route to primary papers before a locus assertion"
    if any(term in text for term in (
        "biosynthetic gene cluster", "gene cluster", "heterologous expression", "pathway engineering",
        "biosynthesis", "biosynthetic pathway", "cryptic phosphorylation",
    )):
        return "PATHWAY_BIOSYNTHESIS", "Reference-system pathway architecture or biosynthetic logic"
    if any(term in text for term in (
        "crystal structure", "cryo-em", "structural basis", "enzyme mechanism", "enzymatic",
        "mutational analysis", "catalyzes", "catalysed", "kinetic analysis",
    )):
        return "ENZYME_OR_STRUCTURE", "Reference enzyme role, mechanism, substrate scope, or structure"
    if any(term in text for term in (
        "chitin synthase", "mode of action", "targeting", "inhibitor", "inhibition",
    )):
        return "TARGET_MECHANISM", "Reference target or mode-of-action context; not producer-pathway identity"
    if any(term in text for term in (
        "field", "crop protection", "disease control", "fungicidal activity", "antifungal activity",
        "bioassay", "efficacy", "minimum inhibitory", "ec50", "ic50",
    )):
        return "APPLICATION_OR_ACTIVITY", "Reference-system assay or application context; not query-BGC activity"
    return "OTHER_CONTEXT", "Discovery-routing context only"


def parse_pubmed_text(path: Path) -> list[LiteratureRecord]:
    raw = path.read_text(encoding="utf-8-sig")
    lines = raw.splitlines()
    source_hash = sha256_bytes(raw.encode("utf-8"))
    records: list[LiteratureRecord] = []
    for number, start, end in _record_boundaries(lines):
        block_lines = lines[start:end]
        # Treat the citation as a paragraph, not a single line. PubMed wraps
        # long citations (for example "Online ahead of print") before the
        # blank line that precedes the title.
        normalized = list(block_lines)
        normalized[0] = re.sub(r"^\d+\.\s+", "", normalized[0]).strip()
        paras = _paragraphs(normalized)
        citation = paras[0] if paras else ""
        title = paras[1] if len(paras) > 1 else ""
        authors = paras[2] if len(paras) > 2 else ""

        # Remove metadata paragraphs and retain the abstract/body paragraphs.
        body: list[str] = []
        in_author_info = False
        for paragraph in paras[3:]:
            upper = paragraph.upper()
            if paragraph.startswith("Author information:"):
                in_author_info = True
                continue
            if in_author_info and re.match(r"^\(\d+\)", paragraph):
                continue
            if in_author_info:
                in_author_info = False
            if re.match(r"^(DOI|PMID|PMCID):", paragraph, flags=re.I):
                continue
            if paragraph.startswith("©") or upper.startswith("CONFLICT OF INTEREST"):
                continue
            body.append(paragraph)
        abstract = "\n\n".join(body).strip()
        block = "\n".join(block_lines)
        doi = _identifier(r"^DOI:\s*(\S+)", block)
        pmid = _identifier(r"^PMID:\s*(\S+)", block)
        pmcid = _identifier(r"^PMCID:\s*(\S+)", block)
        year_match = re.search(r"\b(19|20)\d{2}\b", citation)
        publication_year = year_match.group(0) if year_match else ""
        record_class, evidence_scope = _classify(title, abstract)
        records.append(
            LiteratureRecord(
                record_number=number,
                citation_line=citation,
                title=title,
                authors=authors,
                abstract=abstract,
                doi=doi,
                pmid=pmid,
                pmcid=pmcid,
                publication_year=publication_year,
                record_class=record_class,
                evidence_scope=evidence_scope,
                abstract_availability="ABSTRACT_PRESENT" if abstract else "ABSTRACT_MISSING",
                abstract_sha256=sha256_bytes(abstract.encode("utf-8")) if abstract else "",
                source_file_sha256=source_hash,
                source_start_line=start + 1,
                source_end_line=end,
                claim_ceiling=CLAIM_CEILING,
            )
        )
    return records


def write_records(records: list[LiteratureRecord], out_root: Path, source: Path) -> dict:
    out_root.mkdir(parents=True, exist_ok=True)
    rows = [asdict(record) for record in records]
    tsv = out_root / "literature_records.tsv"
    with tsv.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    json_path = out_root / "literature_records.json"
    json_path.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "records": rows}, indent=2) + "\n", encoding="utf-8")
    counts = Counter(record.record_class for record in records)
    summary = out_root / "literature_routing_summary.tsv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeWriter(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["record_class", "record_count"])
        writer.writerows(sorted(counts.items()))
    receipt = {
        "schema_version": "sapote_pubmed_abstract_intake_receipt_v1",
        "status": "PASS_PARSED_NOT_ADMITTED_TO_ANY_BGC",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {"path": str(source), "sha256": sha256_file(source), "bytes": source.stat().st_size},
        "record_count": len(records),
        "record_number_min": min(record.record_number for record in records),
        "record_number_max": max(record.record_number for record in records),
        "unique_pmid_count": len({record.pmid for record in records if record.pmid}),
        "unique_doi_count": len({record.doi.lower() for record in records if record.doi}),
        "class_counts": dict(sorted(counts.items())),
        "claim_ceiling": CLAIM_CEILING,
        "holds": [
            "No record is associated with a query BGC by this parser.",
            "Abstract text is a discovery and scoped-assertion source; full text may still be required.",
            "OpenAlex metadata, citation counts, and OA status are routing metadata, not evidence strength.",
        ],
    }
    receipt_path = out_root / "intake_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    args = parser.parse_args()
    if args.out_root.exists() and any(args.out_root.iterdir()):
        raise FileExistsError(f"Output root is not empty: {args.out_root}")
    records = parse_pubmed_text(args.input)
    receipt = write_records(records, args.out_root, args.input)
    emit(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
