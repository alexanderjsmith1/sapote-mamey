import csv
from pathlib import Path

import pytest

from mamey.figure_theme import (
    CLAIM_SAFETY,
    PALETTE,
    PROFILES,
    add_claim_safety_footer,
    exact_locus_identity,
    normalize_workflow_state,
    save_figure_pair,
    workflow_style,
)


def test_exact_locus_identity_is_complete_and_ordered():
    assert exact_locus_identity("SYNTHETIC", "NODE_1_length_10000_cov_25.0", "region001", "BGC001") == (
        "SYNTHETIC / NODE_1_length_10000_cov_25.0 / region001 / BGC001"
    )
    with pytest.raises(ValueError):
        exact_locus_identity("SYNTHETIC", "", "region001", "BGC001")
    with pytest.raises(ValueError):
        exact_locus_identity("SYNTHETIC", "NODE_1", "1", "BGC001")


def test_workflow_states_remain_distinct_and_redundantly_encoded():
    raw_states = {
        "OBSERVED_SIGNIFICANT_EXACT_QUERY_LENGTH_BOUND_TOP_HIT": "OBSERVED",
        "NO_EXACT_QUERY_LENGTH_BOUND_TOP_HIT_IN_FROZEN_SNAPSHOT": "NO_SIGNIFICANT_EXACT_BOUND_HIT",
        "SCAN_NOT_RETURNED": "NOT_RETURNED",
        "SUBJECT_UNBOUND": "UNBOUND",
        "STAGED_PENDING": "NOT_RUN",
    }
    assert {normalize_workflow_state(raw) for raw in raw_states} == set(raw_states.values())
    styles = [workflow_style(raw) for raw in raw_states]
    assert len({s["color"] for s in styles}) == len(styles)
    assert all("hatch" in s and "marker" in s for s in styles)


def test_profiles_and_claim_safety_are_governed():
    assert set(PROFILES) == {"screen", "manuscript", "poster"}
    assert all(profile.dpi == 300 for profile in PROFILES.values())
    assert CLAIM_SAFETY == (
        "Similarity is not identity; capacity is not production; "
        "missing or unbound evidence is not biological absence."
    )
    assert PALETTE["navy"] == "#0B2A3D"


def test_save_figure_pair_emits_png_and_editable_svg(tmp_path: Path):
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from mamey.figure_theme import apply_theme

    apply_theme(plt, "manuscript")
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot([0, 1], [0, 1])
    ax.set_title("Frozen Evidence-Channel Coverage")
    add_claim_safety_footer(
        fig,
        provenance="Synthetic Fixture",
        authority="Design Engineering Candidate",
    )
    footer_text = {item.get_text(): item for item in fig.texts}
    provenance = "Synthetic Fixture | Design Engineering Candidate"
    assert footer_text[CLAIM_SAFETY].get_position()[1] > footer_text[provenance].get_position()[1]
    assert footer_text[CLAIM_SAFETY].get_ha() == "left"
    assert footer_text[provenance].get_ha() == "left"
    assert fig.artists, "Footer separator must remain attached to the figure"
    png, svg = save_figure_pair(fig, tmp_path / "synthetic", profile="manuscript")
    plt.close(fig)
    assert png.exists() and png.stat().st_size > 100
    assert svg.exists() and svg.stat().st_size > 100
    svg_text = svg.read_text(encoding="utf-8")
    assert "Frozen Evidence-Channel Coverage" in svg_text
    assert CLAIM_SAFETY in svg_text
    assert provenance in svg_text
    assert "Judgment Deferred" not in svg_text


def test_cross_strain_renderer_uses_theme_and_writes_source_pairs(tmp_path: Path):
    pytest.importorskip("matplotlib")
    from mamey.cross_strain_figures import build_cross_strain_figures

    source = tmp_path / "synthetic_priority_summary.csv"
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["strain", "raw_bgcs", "corrected_bgcs", "pairs_total", "high_pairs"],
        )
        writer.writeheader()
        writer.writerow({"strain": "SYNTHETIC-A", "raw_bgcs": 5, "corrected_bgcs": 4, "pairs_total": 2, "high_pairs": 1})
        writer.writerow({"strain": "SYNTHETIC-B", "raw_bgcs": 3, "corrected_bgcs": 3, "pairs_total": 1, "high_pairs": 0})

    out = tmp_path / "figures"
    result = build_cross_strain_figures(tmp_path, out, top_n=2, make_zip=False)
    assert result["status"] == "PASS"
    assert result["figure_count"] >= 4
    for item in result["figures"]:
        assert (out / item["png"]).is_file()
        svg = out / item["svg"]
        assert svg.is_file()
        assert (out / item["source_csv"]).is_file()
        text = svg.read_text(encoding="utf-8")
        assert CLAIM_SAFETY in text
        assert "Judgment Deferred" not in text
