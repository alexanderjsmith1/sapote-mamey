"""Actual explain and native PDF-table readers: complete identity or visible hold."""
import argparse
import csv
import hashlib
import json

import pytest
from reportlab.platypus import Table

from mamey.package_inspector import explain_command
from mamey.compile_report import _triage_board
from mamey.markdown_pdf import parse

STRAIN = "SYNTHETIC-READER"
CONTIG = "NODE_1_length_1000_cov_1.5"


def row(**changes):
    return dict(Strain=STRAIN, BGC_ID="BGC001", Contig=CONTIG,
                Node_ID="NODE_1_length_1000_cov_1", antiSMASH_Region="region001",
                Region="1", AB_auto="0", AF_auto="12", **changes)


def board(pkg, rows):
    path = pkg / f"{STRAIN}_4_triage_board.csv"
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def package(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    board(pkg, [row()])
    lead = dict(bgc_id="BGC001", contig=CONTIG, ab_score=0, af_score=12)
    summary = dict(strain_id=STRAIN, top_3_ab=[lead], top_3_af=[lead])
    (pkg / "manifest_short.json").write_text(json.dumps(summary))
    (pkg / "manifest.json").write_text(json.dumps(dict(strain_id=STRAIN)))
    return pkg, summary


def snapshot(pkg):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in pkg.iterdir() if p.is_file()}


def explain(pkg, capsys):
    before = snapshot(pkg)
    assert explain_command(argparse.Namespace(package_dir=str(pkg))) == 0
    text = capsys.readouterr().out
    assert snapshot(pkg) == before
    return [line.strip() for line in text.splitlines() if line.lstrip().startswith("1.")]


def test_explain_complete_native_identity_preserves_zero_and_source_bytes(tmp_path, capsys):
    pkg, summary = package(tmp_path)
    label = f"{STRAIN} / {CONTIG} / region001 / BGC001"
    assert explain(pkg, capsys) == [f"1. {label}  AB=0", f"1. {label}  AF=12"]


@pytest.mark.parametrize("field,value", [
    ("Strain", "OTHER"), ("Strain", ""), ("Contig", "NODE_1"),
    ("Node_ID", "NODE_2"), ("antiSMASH_Region", ""),
    ("antiSMASH_Region", "region1"), ("Region", "2"), ("BGC_ID", ""),
    ("region", "region002"), ("Full_Node_ID", "OTHER.1"),
])
def test_invalid_native_board_cannot_supply_explain_identity(tmp_path, capsys, field, value):
    pkg, summary = package(tmp_path)
    bad = row()
    bad[field] = value
    board(pkg, [bad])
    lines = explain(pkg, capsys)
    assert len(lines) == 2 and all("IDENTITY_HOLD" in line for line in lines)
    assert not any(" / " in line for line in lines)


@pytest.mark.parametrize("field,value", [
    ("bgc_id", "BGC002"), ("contig", "NODE_1_length_1000_cov_1.9"),
    ("region", "region002"), ("region", ""), ("region", "unknown"),
    ("Strain", "OTHER"), ("node_id", "NODE_2"), ("Contig", "OTHER.1"),
    ("antiSMASH_Region", "region002"), ("Full_Node_ID", "OTHER.1"),
])
def test_lead_conflict_holds_only_affected_channel(tmp_path, capsys, field, value):
    pkg, summary = package(tmp_path)
    summary["top_3_ab"] = [dict(summary["top_3_ab"][0], **{field: value})]
    (pkg / "manifest_short.json").write_text(json.dumps(summary))
    ab, af = explain(pkg, capsys)
    assert "IDENTITY_HOLD" in ab and " / " not in ab
    assert f"{STRAIN} / {CONTIG} / region001 / BGC001" in af


@pytest.mark.parametrize("kind", ["missing", "duplicate_board", "duplicate_alias", "empty",
                                  "conflicting_manifest", "no_manifest_strain", "symlink"])
def test_board_and_package_ambiguity_remains_held(tmp_path, capsys, kind):
    pkg, summary = package(tmp_path)
    path = pkg / f"{STRAIN}_4_triage_board.csv"
    if kind == "missing":
        path.unlink()
    elif kind == "duplicate_board":
        (pkg / "OTHER_4_triage_board.csv").write_bytes(path.read_bytes())
    elif kind == "duplicate_alias":
        other = dict(row(), Contig="NODE_1_length_1000_cov_1.9")
        board(pkg, [row(), other])
    elif kind == "empty":
        path.write_text("Strain,BGC_ID,Contig,Node_ID,antiSMASH_Region\n")
    elif kind == "conflicting_manifest":
        (pkg / "manifest.json").write_text(json.dumps(dict(strain_id="OTHER")))
    elif kind == "no_manifest_strain":
        summary.pop("strain_id")
        (pkg / "manifest_short.json").write_text(json.dumps(summary))
        (pkg / "manifest.json").write_text("{}")
    else:
        outside = tmp_path / path.name
        path.rename(outside)
        path.symlink_to(outside)
    assert all("IDENTITY_HOLD" in line for line in explain(pkg, capsys))


def test_consistent_rich_lead_fields_use_native_normalized_node_role(tmp_path, capsys):
    pkg, summary = package(tmp_path)
    summary["top_3_ab"] = [dict(summary["top_3_ab"][0], region="region001",
                                node_id="NODE_1_length_1000_cov_1", Strain=STRAIN)]
    (pkg / "manifest_short.json").write_text(json.dumps(summary))
    assert all("IDENTITY_HOLD" not in line for line in explain(pkg, capsys))


def test_malformed_lead_is_held_without_breaking_other_channel(tmp_path, capsys):
    pkg, summary = package(tmp_path)
    summary["top_3_ab"] = [None]
    (pkg / "manifest_short.json").write_text(json.dumps(summary))
    ab, af = explain(pkg, capsys)
    assert "IDENTITY_HOLD" in ab and "IDENTITY_HOLD" not in af


def table_values(md):
    tables = [flow for flow in parse(md) if isinstance(flow, Table)]
    assert len(tables) == 1
    return [[cell.getPlainText() for cell in r] for r in tables[0]._cellvalues]


def test_actual_pdf_reader_preserves_cells_headers_zero_empty_and_excluded_row(tmp_path):
    fields = ["BGC_ID", "Title|source", "AB_auto", "Empty", "Standing_rule"]
    rows = [["BGC001", r"gi|123|ref|WP_1| a\|b", "0", "", ""],
            ["BGC002", "first\r\nsecond\rthird\nfourth\\", "7", "", "excluded|retained"]]
    path = tmp_path / f"{STRAIN}_4_triage_board.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerows(rows)
    before = path.read_bytes()
    values = table_values(_triage_board(tmp_path))
    # These deliberately incomplete records have no admitted locus authority.
    holds = [f"REPORT_IDENTITY_HOLD[ROW_COMPONENT_INVALID] (unbound alias: {alias})"
             for alias in ("BGC001", "BGC002")]
    assert values == [["Report_locus_identity", *fields], [holds[0], *rows[0]],
                      [holds[1], "BGC002", "first second third fourth\\", "7", "", "excluded|retained"]]
    assert [r[1:] for r in values] == [fields, rows[0],
        ["BGC002", "first second third fourth\\", "7", "", "excluded|retained"]]
    assert path.read_bytes() == before


def test_actual_wide_table_reader_keeps_every_original_field_and_value(tmp_path):
    fields = ["BGC_ID", *[f"Field {i}|label" for i in range(9)]]
    values = ["BGC001", *[f"value {i}|x\\|y" for i in range(9)]]
    path = tmp_path / f"{STRAIN}_4_triage_board.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        writer.writerow(values)
    before = path.read_bytes()
    ledger = table_values(_triage_board(tmp_path))
    hold = "REPORT_IDENTITY_HOLD[ROW_COMPONENT_INVALID] (unbound alias: BGC001)"
    assert ledger[0] == ["Record", "Original field", "Value"]
    assert len(ledger) == len(fields) + 2
    assert [r[0] for r in ledger[1:]] == [f"1: {hold}"] * (len(fields) + 1)
    assert ledger[1][1:] == ["Report_locus_identity", hold]
    assert [r[1:] for r in ledger[2:]] == [[k, v] for k, v in zip(fields, values)]
    assert path.read_bytes() == before


def test_pdf_reader_even_backslashes_do_not_hide_a_real_table_delimiter():
    values = table_values("| First | Second |\n|---|---|\n| tail\\\\| next |\n")
    assert values == [["First", "Second"], ["tail\\", "next"]]
