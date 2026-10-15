"""Repeated table headers and short rows are rejected before DictReader conversion."""
import json

import pytest

from mamey.comparator_evidence import read_comparator_source
from mamey.modeb_gap_rescue import _table, load_gap_rescue

MIBIG_HEADER = ["bgc_id", "query_gene", "subject_gene", "mibig_accession",
                "mibig_compound", "pct_identity", "pct_coverage"]


def _write_csv(path, header, rows):
    path.write_text("\n".join(",".join(r) for r in [header] + rows) + "\n", encoding="utf-8")
    return path


def test_comparator_duplicate_required_header_rejected(tmp_path):
    src = _write_csv(tmp_path / "c.csv", MIBIG_HEADER + ["query_gene"],
                     [["BGC001", "ctg1_1", "s1", "BGC0000001", "x", "50", "80", "ctg1_9"]])
    with pytest.raises(ValueError, match=r"duplicate columns: \['query_gene'\]"):
        read_comparator_source(src, "MIBIG_PER_GENE_CSV")


def test_comparator_duplicate_optional_header_rejected(tmp_path):
    src = _write_csv(tmp_path / "c.csv", MIBIG_HEADER + ["note", "note"],
                     [["BGC001", "ctg1_1", "s1", "BGC0000001", "x", "50", "80", "a", "b"]])
    with pytest.raises(ValueError, match="duplicate columns"):
        read_comparator_source(src, "MIBIG_PER_GENE_CSV")


def test_comparator_bom_header_duplicate_rejected(tmp_path):
    src = tmp_path / "c.csv"
    src.write_bytes(b"\xef\xbb\xbf" + (",".join(MIBIG_HEADER + ["bgc_id"]) + "\n"
                    + "BGC001,ctg1_1,s1,BGC0000001,x,50,80,BGC002\n").encode("utf-8"))
    with pytest.raises(ValueError, match="duplicate columns"):
        read_comparator_source(src, "MIBIG_PER_GENE_CSV")


def test_comparator_unique_header_reads_as_before(tmp_path):
    src = _write_csv(tmp_path / "c.csv", MIBIG_HEADER,
                     [["BGC001", "ctg1_1", "s1", "BGC0000001", "x", "50", "80"]])
    rows = read_comparator_source(src, "MIBIG_PER_GENE_CSV")
    assert rows == [dict(zip(MIBIG_HEADER, ["BGC001", "ctg1_1", "s1", "BGC0000001", "x", "50", "80"]))]


def test_gap_rescue_table_duplicate_header_rejected(tmp_path):
    p = tmp_path / "t.tsv"
    p.write_text("reference_gene\tstatus\tstatus\nr1\tPRESENT_IN_CORE\tMISSING_NOT_FOUND\n",
                 encoding="utf-8")
    with pytest.raises(ValueError, match=r"duplicate TSV header\(s\) in t.tsv: \['status'\]"):
        _table(p)


def test_gap_rescue_table_short_row_rejected(tmp_path):
    p = tmp_path / "t.tsv"
    p.write_text("reference_gene\tstatus\tname\nr1\tPRESENT_IN_CORE\n", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed TSV"):
        _table(p)


def test_gap_rescue_table_unique_header_reads_as_before(tmp_path):
    p = tmp_path / "t.tsv"
    p.write_text("reference_gene\tstatus\nr1\tPRESENT_IN_CORE\n", encoding="utf-8")
    fields, rows = _table(p)
    assert fields == {"reference_gene", "status"}
    assert rows == [{"reference_gene": "r1", "status": "PRESENT_IN_CORE"}]


def test_gap_rescue_duplicate_header_is_a_hold(tmp_path):
    identity = "S1 / NODE_1 / region001 / BGC001"
    leaf = tmp_path / "run"
    leaf.mkdir()
    (leaf / "gap_rescue_receipt.json").write_text(json.dumps({"core": identity}),
                                                  encoding="utf-8")
    (leaf / "gap_rescue.tsv").write_text("reference_gene\tstatus\tstatus\nr1\ta\tb\n",
                                         encoding="utf-8")
    result = load_gap_rescue(leaf, identity)
    assert result["state"] == "HOLD"
    assert "duplicate TSV header" in result["reason"], result["reason"]
