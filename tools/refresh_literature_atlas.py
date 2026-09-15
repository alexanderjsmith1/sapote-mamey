#!/usr/bin/env python3
"""Refresh legacy strain literature atlases against a governed evidence store.

The tool is deliberately additive. It reads legacy Markdown/DOCX reports, binds
every local locus to ``current_locus`` in the supplied SQLite store, and emits a
new report only when the entire strain report resolves one-to-one. Historical
prose is retained as a dated evidence layer; database overlays do not silently
promote candidate or review-only Mode B records.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys
# Keep direct script execution bound to this source tree.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.csv_safety import SafeDictWriter, SafeWriter



HEADING = re.compile(r"^## Rank (\d+): (AS-\d+) (BGC\d+)\s*-\s*(.*)$", re.MULTILINE)
LOCAL_ALIAS = re.compile(r"(?<![A-Za-z0-9])BGC\d{3}(?!\d)")
CLAIM_CEILING = (
    "The refreshed exact-locus and report-corpus links support evidence review only. "
    "They do not establish exact product identity, expression, production, activity, "
    "novelty, stereochemistry, yield, ecological function, or owner acceptance."
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_parts(identity: str) -> tuple[str, str, str, str]:
    parts = tuple(part.strip() for part in identity.split(" / "))
    if len(parts) != 4 or not all(parts):
        raise ValueError(f"invalid exact identity: {identity!r}")
    return parts  # type: ignore[return-value]


def bare_alias_lines(text: str) -> list[str]:
    """Return lines with a local alias outside a complete prose or filename identity."""
    bad = []
    for line in text.splitlines():
        if not LOCAL_ALIAS.search(line):
            continue
        prose_identity = " / region" in line and " / BGC" in line
        filename_identity = "__region" in line and "__BGC" in line and ("__NODE_" in line or "__ctg" in line)
        if not (prose_identity or filename_identity):
            bad.append(line)
    return bad


def source_reports(root: Path, *, require_docx: bool) -> list[tuple[str, Path, Path | None]]:
    rows = []
    for md in sorted(root.glob("AS-*/*.md")):
        strain = md.parent.name
        docx = md.with_suffix(".docx")
        if require_docx and not docx.exists():
            raise FileNotFoundError(f"missing paired DOCX: {docx}")
        rows.append((strain, md, docx if docx.exists() else None))
    if not rows:
        raise ValueError(f"no AS strain reports found under {root}")
    return rows


def open_store(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    required = {"current_locus", "owner_record", "locus_binding", "document", "metadata"}
    present = {row[0] for row in connection.execute("select name from sqlite_master where type='table'")}
    missing = sorted(required - present)
    if missing:
        raise ValueError(f"evidence store missing tables: {', '.join(missing)}")
    return connection


def resolve_report(connection: sqlite3.Connection, markdown: str) -> tuple[list[dict], list[dict]]:
    resolved, unresolved = [], []
    for match in HEADING.finditer(markdown):
        rank, strain, alias, legacy_label = match.groups()
        loci = list(
            connection.execute(
                "select * from current_locus where strain=? and bgc_alias=?",
                (strain, alias),
            )
        )
        if len(loci) != 1:
            unresolved.append(
                {
                    "rank": int(rank),
                    "strain": strain,
                    "reason": "NO_UNIQUE_CURRENT_LOCUS" if not loci else "MULTIPLE_CURRENT_LOCI",
                }
            )
            continue
        locus = dict(loci[0])
        owners = [dict(row) for row in connection.execute(
            "select * from owner_record where exact_identity=? order by owner_state,source_path",
            (locus["exact_identity"],),
        )]
        bound = [dict(row) for row in connection.execute(
            "select d.report_kind,d.format,count(distinct lb.sha256) as n "
            "from locus_binding lb join document d using(sha256) "
            "where lb.exact_identity=? group by d.report_kind,d.format "
            "order by d.report_kind,d.format",
            (locus["exact_identity"],),
        )]
        locus.update(
            {
                "rank": int(rank),
                "legacy_label": legacy_label.strip(),
                "legacy_heading": match.group(0),
                "owners": owners,
                "bound_documents": bound,
            }
        )
        resolved.append(locus)
    return resolved, unresolved


def owner_summary(owners: list[dict]) -> str:
    if not owners:
        return "NO_EXACT_OWNER_MATCH; alias-only card reuse was refused."
    values = []
    for owner in owners:
        source = owner.get("source_path") or "NO_SOURCE_PATH"
        values.append(
            f"{owner['owner_state']} / {owner['binding_state']} / {source}"
        )
    return " | ".join(values)


def document_summary(bound: list[dict]) -> str:
    if not bound:
        return "No exact-locus historical report/card records are bound in this store."
    return "; ".join(f"{row['report_kind']} {row['format']}: {row['n']}" for row in bound)


def overlay_lines(row: dict, store_hash: str, authority: str) -> list[str]:
    return [
        "",
        "**Current exact-locus binding.** " + row["exact_identity"] + ".",
        "",
        "**Fresh-package receipt.** "
        + f"Manifest SHA-256 `{row['manifest_sha256']}`. The manifest path is retained in the machine ledger.",
        "",
        "**Current Mode B owner-index status.** " + owner_summary(row["owners"]),
        "",
        "**Exact-locus report-corpus inventory.** " + document_summary(row["bound_documents"]),
        "",
        "**Evidence-store authority.** "
        + f"`{authority}`; store SHA-256 `{store_hash}`. The historical interpretation below remains review evidence and was not automatically promoted.",
        "",
    ]


def refresh_markdown(
    markdown: str,
    resolved: list[dict],
    store_hash: str,
    authority: str,
    package_label: str,
) -> str:
    by_heading = {row["legacy_heading"]: row for row in resolved}

    def replace(match: re.Match[str]) -> str:
        row = by_heading[match.group(0)]
        heading = f"## Rank {row['rank']}: {row['exact_identity']} — legacy comparison {row['legacy_label']}"
        return heading + "\n" + "\n".join(overlay_lines(row, store_hash, authority))

    refreshed = HEADING.sub(replace, markdown)
    # The legacy Markdown image locators embed bare local aliases and are often
    # broken after the archive moves. The DOCX retains its embedded maps; the
    # refreshed Markdown records this typed omission instead of inventing a join.
    refreshed = re.sub(
        r"^!\[Locus map\]\([^\n]+\)\s*$",
        "*Legacy locus map retained in the paired Word/PDF report; no portable exact-locus image binding was available for this Markdown refresh.*",
        refreshed,
        flags=re.MULTILINE,
    )
    intro = (
        "# Current evidence refresh\n\n"
        f"This additive report binds every ranked locus below to {package_label} and records exact-locus Mode B/report-corpus availability. "
        "The July 2026 literature analysis is retained as a historical layer. Database presence and owner-index status do not constitute scientific or owner acceptance.\n\n"
        + CLAIM_CEILING
        + "\n\n"
    )
    refreshed = intro + refreshed
    remaining = bare_alias_lines(refreshed)
    if remaining:
        raise ValueError(f"bare local aliases remain after refresh: {remaining[:3]}")
    return refreshed


def insert_after(paragraph, text: str, *, bold_label: str = ""):
    from docx.oxml import OxmlElement
    from docx.text.paragraph import Paragraph

    node = OxmlElement("w:p")
    paragraph._p.addnext(node)
    new = Paragraph(node, paragraph._parent)
    if bold_label and text.startswith(bold_label):
        new.add_run(bold_label).bold = True
        new.add_run(text[len(bold_label):])
    else:
        new.add_run(text)
    return new


def visible_docx_text(document) -> str:
    chunks = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                chunks.append(cell.text)
    return "\n".join(chunks)


def refresh_docx(
    source: Path,
    output: Path,
    resolved: list[dict],
    store_hash: str,
    authority: str,
    package_label: str,
) -> None:
    from docx import Document
    from docx.shared import Inches, RGBColor
    from docx.oxml.ns import qn

    def set_table_widths(table, widths: list[float]) -> None:
        """Set both the table grid and cell widths; cell.width alone is ignored by Word."""
        table.autofit = False
        grid_columns = list(table._tbl.tblGrid.gridCol_lst)
        for index, width in enumerate(widths):
            twips = str(int(width * 1440))
            if index < len(grid_columns):
                grid_columns[index].set(qn("w:w"), twips)
            for table_row in table.rows:
                if index >= len(table_row.cells):
                    continue
                cell = table_row.cells[index]
                cell.width = Inches(width)
                tc_width = cell._tc.get_or_add_tcPr().get_or_add_tcW()
                tc_width.set(qn("w:w"), twips)
                tc_width.set(qn("w:type"), "dxa")

    def style_header_cell(cell) -> None:
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)

    document = Document(source)
    by_rank = {row["rank"]: row for row in resolved}
    docx_heading = re.compile(r"^Rank (\d+) \| AS-\d+ BGC\d+ \| .+$")
    matched = 0
    first_heading = True
    for paragraph in list(document.paragraphs):
        heading_match = docx_heading.match(paragraph.text.strip())
        if heading_match is None:
            continue
        row = by_rank.get(int(heading_match.group(1)))
        if row is None:
            raise ValueError(f"DOCX rank absent from resolved Markdown: {paragraph.text}")
        paragraph.text = f"Rank {row['rank']}: {row['exact_identity']} — legacy comparison {row['legacy_label']}"
        paragraph.style = "Heading 2"
        if first_heading:
            paragraph.paragraph_format.page_break_before = False
            first_heading = False
        cursor = paragraph
        for text in overlay_lines(row, store_hash, authority):
            if not text:
                continue
            label = text.split("**", 2)[1] if text.startswith("**") else ""
            clean = text.replace("**", "").replace("`", "")
            cursor = insert_after(cursor, clean, bold_label=(label if label else ""))
        matched += 1
    by_pair = {(row["strain"], row["bgc_alias"]): row for row in resolved}
    for table in document.tables:
        headers = [cell.text.strip() for cell in table.rows[0].cells] if table.rows else []
        is_lead_index = headers[:3] == ["Rank", "Strain", "BGC"]
        if is_lead_index:
            table.rows[0].cells[2].text = "Full contig / region / alias"
            widths = [0.45, 0.65, 3.20, 2.30, 0.80, 2.60]
            set_table_widths(table, widths)
            for cell in table.rows[0].cells:
                style_header_cell(cell)
        for table_row in table.rows:
            joined = " | ".join(cell.text.strip() for cell in table_row.cells)
            strain_match = re.search(r"AS-\d+", joined)
            if strain_match is None:
                continue
            strain = strain_match.group(0)
            for cell in table_row.cells:
                alias = cell.text.strip()
                if re.fullmatch(r"BGC\d{3}", alias):
                    row = by_pair.get((strain, alias))
                    if row is None:
                        raise ValueError(f"DOCX contents-table locus absent from resolved Markdown: {strain} {alias}")
                    _, full_contig, region, bgc_alias = exact_parts(row["exact_identity"])
                    cell.text = f"{full_contig} / {region} / {bgc_alias}"
    if matched != len(resolved):
        raise ValueError(f"DOCX heading match {matched} != {len(resolved)} for {source}")
    first = document.paragraphs[0]
    ceiling = first.insert_paragraph_before(CLAIM_CEILING)
    ceiling.style = document.styles["Normal"]
    intro = first.insert_paragraph_before(
        f"This additive report binds every ranked locus to {package_label} and records exact-locus Mode B and report-corpus availability. The prior literature analysis remains a historical evidence layer."
    )
    intro.style = document.styles["Normal"]
    title = first.insert_paragraph_before("Current Evidence Literature Atlas")
    title.style = document.styles["Title"]
    for style_name in ("Title", "Heading 1", "Heading 2"):
        document.styles[style_name].font.color.rgb = RGBColor(0, 0, 0)
    for section in document.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)
    text = visible_docx_text(document)
    remaining = bare_alias_lines(text)
    if remaining:
        raise ValueError(f"bare local aliases remain in DOCX: {remaining[:3]}")
    output.parent.mkdir(parents=True, exist_ok=True)
    document.save(output)


def write_tsv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = SafeDictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-strain-reports", type=Path, required=True)
    parser.add_argument("--evidence-store", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--package-label",
        default="the checksum-bound current Sapote-Mamey package manifests",
        help="Human-readable source label; authority still comes from evidence-store metadata.",
    )
    parser.add_argument(
        "--artifact-tag",
        default="CURRENT_R001",
        help="Filesystem-safe tag used in generated report filenames.",
    )
    parser.add_argument(
        "--emit-docx",
        action="store_true",
        help="Also update paired legacy DOCX files; requires python-docx and a DOCX beside every Markdown report.",
    )
    args = parser.parse_args()

    legacy_root = args.legacy_strain_reports.resolve()
    store = args.evidence_store.resolve()
    output_root = args.output_root.resolve()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", args.artifact_tag):
        raise ValueError("--artifact-tag must contain only letters, numbers, dot, underscore, or hyphen")
    if output_root == legacy_root or legacy_root in output_root.parents:
        raise ValueError("output root must be additive and outside the immutable legacy report root")
    output_root.mkdir(parents=True, exist_ok=True)
    store_hash = digest(store)
    connection = open_store(store)
    metadata = dict(connection.execute("select key,value from metadata"))
    authority = metadata.get("authority_ceiling", "UNDECLARED")

    index_rows, locus_rows, hold_rows = [], [], []
    for strain, markdown_path, docx_path in source_reports(legacy_root, require_docx=args.emit_docx):
        markdown = markdown_path.read_text(encoding="utf-8")
        resolved, unresolved = resolve_report(connection, markdown)
        if unresolved:
            ranks = ";".join(str(row["rank"]) for row in unresolved)
            hold_rows.append(
                {
                    "strain": strain,
                    "source_markdown_sha256": digest(markdown_path),
                    "unresolved_rank_count": len(unresolved),
                    "unresolved_legacy_ranks": ranks,
                    "state": "REPORT_WITHHELD_UNBOUND_CURRENT_LOCI",
                    "release_condition": "Bind every legacy rank to one fresh four-part locus identity before regeneration",
                }
            )
            index_rows.append(
                {
                    "strain": strain,
                    "source_markdown_sha256": digest(markdown_path),
                    "source_docx_sha256": digest(docx_path) if docx_path else "",
                    "ranked_loci": len(resolved) + len(unresolved),
                    "resolved_loci": len(resolved),
                    "exact_owner_matches": 0,
                    "status": "WITHHELD",
                    "markdown": "",
                    "docx": "",
                }
            )
            continue

        strain_out = output_root / "strain_reports" / strain
        strain_out.mkdir(parents=True, exist_ok=True)
        stem = f"{strain}_CURRENT_EVIDENCE_LITERATURE_ATLAS_{args.artifact_tag}"
        md_out = strain_out / f"{stem}.md"
        md_out.write_text(
            refresh_markdown(markdown, resolved, store_hash, authority, args.package_label),
            encoding="utf-8",
        )
        docx_out = strain_out / f"{stem}.docx"
        if args.emit_docx:
            if docx_path is None:
                raise FileNotFoundError(f"missing paired DOCX for {markdown_path}")
            refresh_docx(docx_path, docx_out, resolved, store_hash, authority, args.package_label)
        exact_owner_matches = sum(bool(row["owners"]) for row in resolved)
        index_rows.append(
            {
                "strain": strain,
                "source_markdown_sha256": digest(markdown_path),
                "source_docx_sha256": digest(docx_path) if docx_path else "",
                "ranked_loci": len(resolved),
                "resolved_loci": len(resolved),
                "exact_owner_matches": exact_owner_matches,
                "status": "GENERATED_REVIEW_ONLY",
                "markdown": str(md_out),
                "docx": str(docx_out) if args.emit_docx else "",
            }
        )
        for row in resolved:
            strain_id, full_contig, region, alias = exact_parts(row["exact_identity"])
            states = sorted({owner["owner_state"] for owner in row["owners"]})
            locus_rows.append(
                {
                    "rank": row["rank"],
                    "strain": strain_id,
                    "full_contig": full_contig,
                    "region": region,
                    "bgc_alias": alias,
                    "exact_identity": row["exact_identity"],
                    "manifest_sha256": row["manifest_sha256"],
                    "owner_states": ";".join(states) if states else "NO_EXACT_OWNER_MATCH",
                    "bound_report_objects": sum(item["n"] for item in row["bound_documents"]),
                    "claim_state": "REVIEW_ONLY",
                }
            )

    write_tsv(
        output_root / "REFRESH_INDEX.tsv",
        index_rows,
        ["strain", "source_markdown_sha256", "source_docx_sha256", "ranked_loci", "resolved_loci", "exact_owner_matches", "status", "markdown", "docx"],
    )
    write_tsv(
        output_root / "LOCUS_REFRESH_LEDGER.tsv",
        locus_rows,
        ["rank", "strain", "full_contig", "region", "bgc_alias", "exact_identity", "manifest_sha256", "owner_states", "bound_report_objects", "claim_state"],
    )
    write_tsv(
        output_root / "UNBOUND_REPORT_HOLDS.tsv",
        hold_rows,
        ["strain", "source_markdown_sha256", "unresolved_rank_count", "unresolved_legacy_ranks", "state", "release_condition"],
    )
    summary = {
        "schema": "sapote_mamey_literature_atlas_refresh/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "legacy_root_sha256_basis": "source Markdown and available DOCX SHA-256 values retained in REFRESH_INDEX; withheld Markdown hashes duplicated in the hold ledger",
        "evidence_store": str(store),
        "evidence_store_sha256": store_hash,
        "evidence_store_authority": authority,
        "package_label": args.package_label,
        "artifact_tag": args.artifact_tag,
        "reports_discovered": len(index_rows),
        "reports_generated": sum(row["status"].startswith("GENERATED") for row in index_rows),
        "reports_withheld": sum(row["status"] == "WITHHELD" for row in index_rows),
        "loci_refreshed": len(locus_rows),
        "exact_owner_matches": sum(row["owner_states"] != "NO_EXACT_OWNER_MATCH" for row in locus_rows),
        "claim_ceiling": CLAIM_CEILING,
    }
    (output_root / "REFRESH_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
