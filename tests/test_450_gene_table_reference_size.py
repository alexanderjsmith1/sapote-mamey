"""Saved reference lengths supplement the gene table without reclassifying matches.

The size ratio compares full-protein lengths; it is not alignment coverage or functional evidence.
"""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gap_rescue_gene_table as gt  # noqa: E402

CORE = "SYNTHETIC / NODE_1_length_900_cov_1 / region001 / BGC001"
OLD_COLS = ["CDS", "Size (aa)", "Protein family (antiSMASH)", "Reference gene", "Reference annotation",
            "Identity (%)", "Location"]


def _row(status="PRESENT_IN_CORE", ref_len="3050", local_len="301", tag="gene_a"):
    return dict(reference_gene="1", name="ref_a", status=status, reference_len_aa=ref_len,
                best_len_aa=local_len, best_locus=tag, best_protein="q1", best_identity_pct="61.2",
                reciprocal_best="True", best_contig="NODE_1_length_900_cov_1", best_region_identity=CORE,
                reference_product="Saved reference annotation")


def _table(row, splits=()):
    return gt.table_rows([row], splits, CORE, {"q1": "Saved family", "gene_a": "Saved family", "gene_b": "Other family"},
                         {}, known_tags={"gene_a", "gene_b"})


def test_new_columns_sit_beside_reference_gene_with_stable_row_order():
    assert gt.COLS == OLD_COLS[:4] + ["Reference size (aa)", "Local/reference size ratio"] + OLD_COLS[4:]
    assert list(_table(_row())[0]) == gt.COLS


def test_found_row_preserves_every_old_cell_and_displays_stored_lengths():
    row = _table(_row())[0]
    assert {key: row[key] for key in OLD_COLS} == {
        "CDS": "gene_a", "Size (aa)": "301", "Protein family (antiSMASH)": "Saved family",
        "Reference gene": "ref_a", "Reference annotation": "Saved reference annotation", "Identity (%)": "61.2",
        "Location": "BGC001, NODE_1 (core)"}
    assert row["Reference size (aa)"] == "3050"
    assert row["Local/reference size ratio"] == "0.10"


def test_not_found_row_keeps_reference_length_without_local_length_or_ratio():
    row = _table(_row("MISSING_NOT_FOUND", "412", "", ""))[0]
    assert {key: row[key] for key in OLD_COLS} == {
        "CDS": "not found", "Size (aa)": "", "Protein family (antiSMASH)": "", "Reference gene": "ref_a",
        "Reference annotation": "Saved reference annotation", "Identity (%)": "", "Location": "not found"}
    assert row["Reference size (aa)"] == "412" and row["Local/reference size ratio"] == ""


def test_split_row_keeps_reference_length_and_has_no_combined_length_ratio():
    split = dict(reference_gene="1", name="ref_a", status="SPLIT_ACROSS_CONTIG_ENDS", split_call="CLEAR",
                 piece1_locus="gene_a", piece2_locus="gene_b", piece1_region_identity=CORE,
                 piece2_region_identity="SYNTHETIC / NODE_2_length_800_cov_1 / region001 / BGC002",
                 piece1_identity_pct="80", piece2_identity_pct="65")
    row = _table(_row("MISSING_NOT_FOUND", "1000", "", ""), [split])[0]
    assert {key: row[key] for key in OLD_COLS} == {
        "CDS": "gene_a + gene_b", "Size (aa)": "", "Protein family (antiSMASH)": "Saved family / Other family",
        "Reference gene": "ref_a", "Reference annotation": "Saved reference annotation", "Identity (%)": "80.0 / 65.0",
        "Location": "split across BGC001, NODE_1 (core) + BGC002, NODE_2"}
    assert row["Reference size (aa)"] == "1000" and row["Local/reference size ratio"] == ""


def test_missing_saved_reference_length_is_blank_without_changing_old_cells():
    absent = _table(_row(ref_len=""))[0]
    present = _table(_row())[0]
    assert {key: absent[key] for key in OLD_COLS} == {key: present[key] for key in OLD_COLS}
    assert absent["Reference size (aa)"] == "" and absent["Local/reference size ratio"] == ""


@pytest.mark.parametrize("invalid", ["nan", "inf", "-1", "0", "412.5", "n/a"])
def test_invalid_reference_length_is_blank_and_never_emits_nonfinite_ratio(invalid):
    assert gt._len(invalid) == ""
    assert gt._ratio("300", invalid) == ""


def test_decimal_integer_length_and_large_local_length_ratio_are_display_values():
    assert gt._len("412.0") == "412"
    assert gt._ratio("405", "267") == "1.52"
    assert gt._ratio("", "412") == ""
    assert gt._ratio("inf", "412") == ""


def test_rendered_caption_explains_ratio_and_tsv_heading_without_rendering(tmp_path, monkeypatch):
    import csv

    captured = {}
    monkeypatch.setattr(gt, "reference_annotations", lambda reference: {})

    def capture_draw(table, title, label, png, pdf, caption):
        captured["caption"] = caption
        return False

    monkeypatch.setattr(gt, "_draw", capture_draw)
    monkeypatch.setattr(gt, "pair_with_map", lambda out: [])
    result = gt.write_gene_table(tmp_path, [_row()], [], CORE, "SYNTHETIC", Path("BGC_REF.gbk"), {},
                                 known_tags={"gene_a"})
    explanation = "Size ratio = local/reference full-protein length; not alignment coverage."
    assert captured["caption"].endswith(explanation)
    assert result["rendered_caption"] == captured["caption"]
    from gap_rescue_locus_map import count_sentence
    assert result["caption"] == count_sentence(result["counts"], CORE) + "."
    assert captured["caption"] == result["caption"] + " " + explanation
    with (tmp_path / "gene_table.tsv").open() as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        assert reader.fieldnames == gt.COLS + gt.POSITION_COLS   # gene positions follow in the TSV only
        row = next(reader)
    assert row["Local/reference size ratio"] == "0.10"
    assert "Size ratio" not in row
    assert not (tmp_path / "gene_table.png").exists()
    assert not (tmp_path / "gene_table.pdf").exists()
