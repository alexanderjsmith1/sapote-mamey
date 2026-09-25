"""Figure house rules (v9.7.442): the 2026-09-24 wording ruling and the figure-folder checker."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from caption_guard import check_caption  # noqa: E402
import figure_house_rules as fhr  # noqa: E402


# --- wording: the phrases ruled off figures on 2026-09-24 are refused ---------------------------

@pytest.mark.parametrize("text", [
    "similarity, not identity",
    "capacity not production",
    "not bioactivity",
    "screening values, not potency",
    "not novelty",
    "Descriptive screening of 181 isolates",
    "query strain (AS)",
])
def test_ruled_phrases_are_refused(text):
    assert check_caption(text, raises=False), text


@pytest.mark.parametrize("text", [
    "isolate from this study",
    "percent identity to the nearest reference",
    "class-level composition of BGC classes",
    "production medium ISP2",
    "identity threshold 95%",
])
def test_ordinary_scientific_wording_still_passes(text):
    assert check_caption(text, raises=False) == [], text


# --- pathogen order -------------------------------------------------------------------------------

def test_order_is_fungi_then_gram_negatives_then_mrsa():
    shuffled = ["MRSA", "E. coli", "Candida auris", "Pseudomonas aeruginosa", "Candida albicans"]
    assert fhr.order_pathogens(shuffled) == [
        "Candida albicans", "Candida auris", "E. coli", "Pseudomonas aeruginosa", "MRSA"]


def test_enterobacter_omitted_variant_and_vertical_axis():
    got = fhr.order_pathogens(fhr.PATHOGEN_ORDER, drop_enterobacter=True, vertical=True)
    assert "Enterobacter" not in got
    assert got[0] == "MRSA" and got[-1] == "Candida albicans"


def test_unknown_pathogens_are_kept_after_the_known_ones():
    assert fhr.order_pathogens(["Zeta sp.", "MRSA", "Alpha sp."]) == ["MRSA", "Alpha sp.", "Zeta sp."]


def test_host_group_vocabulary_is_closed():
    assert fhr.unknown_host_groups(["Wasps", "Bumblebees", "", "bee", "Other Apidae"]) == ["Other Apidae", "bee"]


# --- figure folder checker ------------------------------------------------------------------------

def _figure(tmp_path, name="FIG_crude_candida", caption="Figure 1. Inhibition by crude extracts.",
            plot_only=True, svg_text=None, caption_name="CAPTION.md"):
    d = tmp_path / name
    d.mkdir()
    (d / f"{name}.png").write_bytes(b"\x89PNG")
    if plot_only:
        (d / f"{name}_plot_only.png").write_bytes(b"\x89PNG")
    if caption is not None:
        (d / caption_name).write_text(caption)
    if svg_text is not None:
        (d / f"{name}.svg").write_text(f"<svg><text x='1'>{svg_text}</text></svg>")
    return d


def test_a_compliant_folder_has_no_findings(tmp_path):
    assert fhr.check_folder(_figure(tmp_path), bioassay=True) == []


def test_named_caption_sidecar_is_accepted(tmp_path):
    d = _figure(tmp_path, caption_name="FIG_crude_candida_CAPTION.md")
    assert fhr.check_folder(d) == []


def test_missing_caption_is_an_error(tmp_path):
    rules = [f["rule"] for f in fhr.check_folder(_figure(tmp_path, caption=None))]
    assert "CAPTION_MISSING" in rules


def test_ruled_wording_in_the_caption_band_is_an_error(tmp_path):
    d = _figure(tmp_path, caption="Figure 1.\n\n---\nInternal notes: judgment deferred; not identity.")
    assert {f["rule"] for f in fhr.check_folder(d)} == {"FIGURE_WORDING"}


def test_ruled_wording_drawn_in_an_svg_is_an_error(tmp_path):
    d = _figure(tmp_path, svg_text="query strain (AS)")
    assert any(f["rule"] == "FIGURE_WORDING" and f["where"].endswith(".svg") for f in fhr.check_folder(d))


def test_missing_plot_only_copy_warns_but_does_not_fail(tmp_path):
    d = _figure(tmp_path, plot_only=False)
    found = fhr.check_folder(d)
    assert [(f["level"], f["rule"]) for f in found] == [("WARN", "PLOT_ONLY_MISSING")]
    assert fhr.main(["check", str(d)]) == 0


def test_bioassay_figure_must_name_its_material(tmp_path):
    d = _figure(tmp_path, name="FIG_227c_by_host")
    assert fhr.check_folder(d, bioassay=False) == []
    assert [f["rule"] for f in fhr.check_folder(d, bioassay=True)] == ["MATERIAL_UNLABELLED"]
    assert fhr.main(["check", "--bioassay", str(d)]) == 1


def test_a_missing_folder_is_not_reported_clean(tmp_path):
    assert fhr.check_folder(tmp_path / "nope")[0]["rule"] == "FOLDER_MISSING"


# --- renderer source scan: drawn text only, not docstrings ------------------------------------------

def test_scan_source_reports_drawn_text_and_ignores_docstrings(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "r.py").write_text(
        '"""Claim-safety: homology only; judgment deferred."""\n'
        "def f(ax):\n"
        "    ax.set_title('Neighbours (judgment deferred)')\n"
        "    ax.set_xlabel('percent identity')\n")
    hits = fhr.scan_source(tmp_path)
    assert [h["where"] for h in hits] == ["tools/r.py:3"]
