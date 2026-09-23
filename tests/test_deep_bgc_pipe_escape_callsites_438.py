"""The pipe escape has to be wired into the two Markdown tables, not merely defined.

`test_deep_bgc_pipe_escape.py` exercises `_cell` in isolation: every one of its four
assertions is a statement about `str.replace`. Delete `_cell(...)` from the row
f-strings at the component and gene tables and all four still pass, because the helper
is still importable and still correct. These tests render a real report through
`build_deep_report` and read the emitted Markdown, so they fail when the call sites
lose their escaping.

The check is column count. A Markdown row carrying an unescaped `|` splits into more
fields than the header declares, which is exactly the misattribution the defect causes.
"""
import csv
import json

from mamey.deep_bgc_report import build_deep_report

IDENTITY = {
    "strain": "SYNTHETIC-001",
    "full_node_or_contig": "contig_demo_0001_complete",
    "region": "region001",
    "bgc_alias": "BGC007",
}

# A pipe in every field the two tables insert without a numeric guarantee.
PIPED_GENE = "gene|001"
PIPED_ROLE = "core|biosynthetic"
PIPED_PRODUCT = "type|I|PKS"
PIPED_DOMAIN = "PF00001|KS"
PIPED_COMPONENT = "component|A"
PIPED_COMPLETENESS = "complete|core"
PIPED_ORDER = "conserved|collinear"


def _locus():
    return dict(
        IDENTITY,
        canonical_gene_count=1,
        boundary={"status": "OVERMERGED_SUSPECTED", "note": "Flanking genes require review."},
        whole_region_matched_cds=1,
        whole_region_total_cds=4,
        comparator_components=[{
            "name": PIPED_COMPONENT,
            "matched_cds": 1,
            "local_total_cds": 2,
            "core_completeness": PIPED_COMPLETENESS,
            "gene_order": PIPED_ORDER,
        }],
        genes=[{
            "gene_id": PIPED_GENE,
            "start": 100,
            "end": 500,
            "strand": "+",
            "role": PIPED_ROLE,
            "product": PIPED_PRODUCT,
            "domains": [PIPED_DOMAIN],
            "protein_sha256": "a" * 64,
        }],
    )


def _evidence(tmp_path):
    row = dict(IDENTITY, gene_id=PIPED_GENE, protein_sha256="a" * 64,
               channel="MIBiG", result="class comparator")
    path = tmp_path / "evidence.tsv"
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=row, delimiter="\t")
        writer.writeheader()
        writer.writerow(row)
    return path


def _report(tmp_path):
    locus_json = tmp_path / "locus.json"
    locus_json.write_text(json.dumps(_locus()))
    build_deep_report(locus_json, tmp_path / "out", _evidence(tmp_path))
    return (tmp_path / "out" / "DEEP_BGC_REPORT.md").read_text()


def _columns(row: str) -> int:
    """Field count of a Markdown row, honouring backslash-escaped pipes."""
    return len([f for f in _split_unescaped(row.strip()) if f != ""])


def _split_unescaped(row: str) -> list[str]:
    fields, current, i = [], "", 0
    while i < len(row):
        if row[i] == "\\" and i + 1 < len(row) and row[i + 1] == "|":
            current += "|"
            i += 2
            continue
        if row[i] == "|":
            fields.append(current)
            current = ""
            i += 1
            continue
        current += row[i]
        i += 1
    fields.append(current)
    return fields


def _row_starting(text: str, needle: str) -> str:
    for line in text.splitlines():
        if line.startswith("|") and needle in line:
            return line
    raise AssertionError(f"no Markdown row containing {needle!r}")


def test_gene_row_keeps_six_columns(tmp_path):
    text = _report(tmp_path)
    row = _row_starting(text, "gene")
    assert _columns(row) == 6, row


def test_component_row_keeps_four_columns(tmp_path):
    text = _report(tmp_path)
    row = _row_starting(text, "component")
    assert _columns(row) == 4, row


def test_every_pipe_in_a_table_row_is_escaped(tmp_path):
    """No data row may carry a bare `|` outside its own column separators."""
    text = _report(tmp_path)
    for value in (PIPED_GENE, PIPED_ROLE, PIPED_PRODUCT, PIPED_DOMAIN,
                  PIPED_COMPONENT, PIPED_COMPLETENESS, PIPED_ORDER):
        assert value.replace("|", "\\|") in text, f"{value!r} reached Markdown unescaped"
        assert f" {value} " not in text, f"{value!r} present unescaped"
