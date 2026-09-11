"""v9.7.410 hostile audit, round 3 — external text in markdown table cells.

A `|` inside a cell splits a markdown table row; every later value lands under the wrong header.
BLAST subject titles in the classic NCBI form carry pipes (`gi|123|ref|WP_…`), so the compiled
report's BLASTP evidence tables were breakable by ordinary input. The tools inventory generator
had the same hole via a `|` in a tool docstring.
"""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import mamey
from mamey import compile_report as cr

ROOT = Path(mamey.__file__).resolve().parent.parent
PIPED = "gi|123456|ref|WP_000001.1| hypothetical protein [Streptomyces sp.]"


def _cells(line: str) -> list[str]:
    """Split a markdown row the way a renderer does: on unescaped pipes only."""
    return [c for c in __import__("re").split(r"(?<!\\)\|", line.strip())[1:-1]]


def test_blastp_summary_csv_table_keeps_column_alignment_with_piped_titles(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    csvp = pkg / "BLASTP_BGC_summary.csv"
    with csvp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["bgc_id", "top_titles", "best_pct_identity", "best_query_coverage",
                                           "current_claim_level", "recommended_next_action"])
        w.writeheader()
        w.writerow({"bgc_id": "BGC001", "top_titles": PIPED, "best_pct_identity": "66.1",
                    "best_query_coverage": "98", "current_claim_level": "similarity",
                    "recommended_next_action": "re-run | with coverage"})
    found = cr._find_blastp_summary(pkg)
    assert found is not None, "fixture name did not match _find_blastp_summary — adjust the fixture"
    md = cr._blastp_summary(pkg)
    row = [ln for ln in md.splitlines() if ln.startswith("| BGC001")][0]
    cells = _cells(row)
    assert len(cells) == 6, row
    assert cells[2].strip() == "66.1" and cells[4].strip() == "similarity"
    assert "\\|" in cells[1]


def test_md_cell_escapes_pipes_and_newlines():
    assert cr._md_cell("a|b\nc") == "a\\|b c"
    assert cr._md_cell(None) == ""


def test_review_request_validator_routes_pathological_json_to_hold(tmp_path):
    """A 200k-deep `[[[[…]]]]` request file raised RecursionError out of the validator (a crash,
    not a HOLD). json.loads recursion is now caught alongside the decode errors."""
    from mamey.mode_b_receipt import validate_finished_review_request
    (tmp_path / "pkg").mkdir()
    (tmp_path / "root").mkdir()
    req = tmp_path / "deep.json"
    req.write_text("[" * 200000 + "]" * 200000, encoding="utf-8")
    result = validate_finished_review_request(tmp_path / "pkg", req, tmp_path / "root")
    codes = [f["code"] for f in result["findings"]]
    assert "REVIEW_REQUEST_JSON_INVALID" in codes
    assert result.get("route", result.get("status")) != "READY_FOR_OWNER_REVIEW"


def test_gbk_shim_never_yields_an_inverted_feature_span():
    from mamey._gbk_shim import parse_genbank_text
    for loc in ("9..1", "complement(join(9..1,abc))", "-5..3", "1..9"):
        text = (f"LOCUS       X 10 bp DNA\nFEATURES             Location/Qualifiers\n     CDS             {loc}\n"
                "                     /product=\"p\"\nORIGIN\n        1 acgtacgtac\n//\n")
        (rec,) = parse_genbank_text(text)
        (feat,) = rec.features
        assert 0 <= feat.location.start <= feat.location.end, (loc, feat.location)
    (rec,) = parse_genbank_text("LOCUS       X 10 bp DNA\nFEATURES             Location/Qualifiers\n     CDS             1..9\n"
                                "                     /product=\"p\"\nORIGIN\n        1 acgtacgtac\n//\n")
    assert (rec.features[0].location.start, rec.features[0].location.end) == (0, 9)  # well-formed: unchanged


def test_tools_inventory_summary_escapes_pipes(tmp_path):
    spec = importlib.util.spec_from_file_location("gti", ROOT / "tools" / "gen_tools_inventory.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tool = tmp_path / "zz_probe.py"
    tool.write_text('"""zz_probe.py — summary with a pipe | inside.\n"""\n', encoding="utf-8")
    summary = mod._first_doc_line_py(tool)
    assert summary == "summary with a pipe \\| inside."
