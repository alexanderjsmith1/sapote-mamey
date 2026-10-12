"""Pair a map only after the current call rendered its table images successfully.

Portable fake renderer/composer tests; no optional graphics imports or biological inputs.
"""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gap_rescue_gene_table as gt  # noqa: E402

CORE = "SYNTHETIC / NODE_1_length_900_cov_1 / region001 / BGC001"


def _row():
    return dict(reference_gene="1", name="ref_a", status="PRESENT_IN_CORE", best_locus="gene_a",
                best_protein="q1", best_len_aa="301", reference_len_aa="3050", best_identity_pct="61.2",
                best_contig="NODE_1_length_900_cov_1", best_region_identity=CORE)


def _write(tmp_path, monkeypatch):
    monkeypatch.setattr(gt, "reference_annotations", lambda reference: {})
    return gt.write_gene_table(tmp_path, [_row()], [], CORE, "SYNTHETIC", Path("BGC_REF.gbk"), {},
                               known_tags={"gene_a"})


def _stale(tmp_path):
    names = ["gap_rescue.png", "gap_rescue.pdf", "gene_table.png", "gene_table.pdf",
             "map_and_table.png", "map_and_table.pdf"]
    for name in names:
        (tmp_path / name).write_bytes(("older artifact: " + name).encode())
    return {name: (tmp_path / name).read_bytes() for name in names}


def test_skipped_current_draw_does_not_pair_or_advertise_stale_images(tmp_path, monkeypatch):
    older = _stale(tmp_path)
    calls = []
    monkeypatch.setattr(gt, "_draw", lambda *args: False)
    monkeypatch.setattr(gt, "pair_with_map", lambda out: calls.append(out) or [out / "map_and_table.pdf"])
    result = _write(tmp_path, monkeypatch)
    assert calls == []
    assert result["files"] == [str(tmp_path / "gene_table.tsv"), str(tmp_path / "gene_table_counts.tsv")]
    assert {name: (tmp_path / name).read_bytes() for name in older} == older
    assert "ref_a" in (tmp_path / "gene_table.tsv").read_text()
    assert result["rows"] == 1 and result["counts"]["core"] == 1


def test_successful_fresh_draw_still_pairs_and_advertises_current_outputs(tmp_path, monkeypatch):
    older = _stale(tmp_path)
    calls = []

    def draw(table, title, label, png, pdf, caption):
        png.write_bytes(b"fresh table png")
        pdf.write_bytes(b"fresh table pdf")
        return True

    def pair(out):
        calls.append(out)
        result = [out / "map_and_table.png", out / "map_and_table.pdf"]
        for path in result:
            path.write_bytes(b"fresh pair")
        return result

    monkeypatch.setattr(gt, "_draw", draw)
    monkeypatch.setattr(gt, "pair_with_map", pair)
    result = _write(tmp_path, monkeypatch)
    assert calls == [tmp_path]
    assert [Path(p).name for p in result["files"]] == ["gene_table.tsv", "gene_table_counts.tsv", "gene_table.png",
                                                       "gene_table.pdf", "map_and_table.png", "map_and_table.pdf"]
    assert (tmp_path / "gene_table.png").read_bytes() == b"fresh table png"
    assert (tmp_path / "gene_table.pdf").read_bytes() == b"fresh table pdf"
    assert (tmp_path / "gap_rescue.png").read_bytes() == older["gap_rescue.png"]
    assert (tmp_path / "gap_rescue.pdf").read_bytes() == older["gap_rescue.pdf"]


def test_failed_draw_does_not_reach_pairing_or_rewrite_prior_pair(tmp_path, monkeypatch):
    older = _stale(tmp_path)
    calls = []

    def fail_draw(*args):
        raise OSError("synthetic draw failure")

    monkeypatch.setattr(gt, "_draw", fail_draw)
    monkeypatch.setattr(gt, "pair_with_map", lambda out: calls.append(out) or [])
    with pytest.raises(OSError, match="synthetic draw failure"):
        _write(tmp_path, monkeypatch)
    assert calls == []
    assert {name: (tmp_path / name).read_bytes() for name in older} == older
