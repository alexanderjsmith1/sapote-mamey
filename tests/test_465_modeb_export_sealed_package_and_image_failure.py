"""modeb-export must not write into a sealed package, and one unreadable figure fails one card only.

It used to write .docx/.pdf files next to the cards inside the package (which then failed validate)
and to stop the whole batch with a PDF_IMAGE_UNAVAILABLE traceback on the first SVG figure.
"""
from pathlib import Path

import pytest

from mamey import modeb_export as X


def _sealed_pkg(tmp_path):
    pkg = tmp_path / "S1" / "package"
    (pkg / "mode_b").mkdir(parents=True)
    (pkg / "checksums_sha256.txt").write_text("", encoding="utf-8")
    card = pkg / "mode_b" / "S1_BGC001_card.md"
    card.write_text("# S1 / NODE_1 / region001 / BGC001\n\nText.\n", encoding="utf-8")
    return pkg, card


def test_default_output_inside_a_sealed_package_is_refused(tmp_path, capsys):
    pkg, card = _sealed_pkg(tmp_path)
    assert X.main([str(pkg / "mode_b")]) == 2
    assert "inside the sealed package" in capsys.readouterr().err
    assert sorted(p.name for p in (pkg / "mode_b").iterdir()) == ["S1_BGC001_card.md"]


def test_outdir_inside_the_package_is_refused(tmp_path, capsys):
    pkg, card = _sealed_pkg(tmp_path)
    assert X.main([str(card), "--outdir", str(pkg / "exports")]) == 2
    assert not (pkg / "exports").exists()


def test_outdir_outside_the_package_is_allowed(tmp_path):
    pkg, card = _sealed_pkg(tmp_path)
    assert X._refuse_sealed_target(card, str(tmp_path / "out")) is None


def test_unsealed_folder_keeps_the_default(tmp_path):
    card = tmp_path / "loose" / "card.md"
    card.parent.mkdir()
    card.write_text("# t\n", encoding="utf-8")
    assert X._refuse_sealed_target(card, None) is None


def test_unreadable_figure_fails_this_card_without_a_traceback(tmp_path):
    pytest.importorskip("reportlab")
    card = tmp_path / "loose" / "card.md"
    card.parent.mkdir()
    (card.parent / "fig.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    card.write_text("# t\n\n![figure](fig.svg)\n", encoding="utf-8")
    res = X.export_card_pdf(card, tmp_path / "out" / "card.pdf")
    if res["status"] == "SKIPPED_NO_REPORTLAB":
        pytest.skip("packaged PDF renderer unavailable")
    assert res["status"] == "FAILED_IMAGE_UNAVAILABLE"
    assert "PNG" in res["detail"] and res["path"] is None
    assert not (tmp_path / "out" / "card.pdf").exists()
