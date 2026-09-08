"""Desired behavior for native Good Guesses board/evidence identity association."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from mamey import good_guesses as gg
from mamey.crosswalk import infer_node_id
from mamey.exact_identity import ExactLocusIdentityError


STRAIN = "TEST-NATIVE"
REGION = "region001"


def _write(path: Path, name: str, rows: list[dict]) -> None:
    with (path / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _row(alias: str, contig: str) -> dict:
    return {
        "BGC_ID": alias,
        "Contig": contig,
        "Node_ID": infer_node_id(contig, ""),
        "antiSMASH_Region": REGION,
        "Products": "NRPS",
        "Arch_Capacity": "NRPS",
        "Lead_tier_auto": "High",
    }


def _anchor(alias: str, contig: str, **extra: str) -> dict:
    return {
        "strain": STRAIN,
        "assembly_locator": "assembly://native",
        "contig": infer_node_id(contig, ""),
        "region": REGION,
        "bgc_id": alias,
        **extra,
    }


def _package(tmp_path: Path, board_rows: list[dict], profiles: list[dict], convergence: list[dict]) -> Path:
    package = tmp_path / "package"
    package.mkdir()
    (package / "manifest.json").write_text(json.dumps({"strain_id": STRAIN}), encoding="utf-8")
    _write(package, f"{STRAIN}_4_triage_board.csv", board_rows)
    _write(package, f"{STRAIN}_3_mibig_profile.csv", profiles)
    _write(package, f"{STRAIN}_3_mibig_convergence.csv", convergence)
    return package


def _convergence(anchor: dict) -> dict:
    return {
        **anchor,
        "class_concordance": "CONCORDANT",
        "convergence_tier": "H4_REPEATED_SUPPORT",
        "dominance_status": "CLEAR_DOMINANT",
        "dominant_reference": "True",
    }


def _profile(anchor: dict) -> dict:
    return {
        **anchor,
        "query_gene_count": "10",
        "recognizable_gene_fraction": "0.5",
        "interpretation_class": "KNOWN_ANCHORED",
    }


def test_native_board_and_lowercase_evidence_anchor_render_full_contig(tmp_path: Path) -> None:
    contig = "NODE_7_length_9000_cov_12.345"
    anchor = _anchor("BGC001", contig)
    package = _package(tmp_path, [_row("BGC001", contig)], [_profile(anchor)], [_convergence(anchor)])
    out = tmp_path / "out"
    result = gg.run(package, out_dir=out, pdf=False, docx=False)
    assert result["guesses"] == 1
    assert result["rows"][0]["exact_locus"] == (
        "TEST-NATIVE / NODE_7_length_9000_cov_12.345 / region001 / BGC001"
    )
    assert (out / "GOOD_GUESSES.csv").is_file()


@pytest.mark.parametrize(
    ("edit", "match"),
    [
        (lambda row: row.update(contig="NODE_8_length_9000_cov_12"), "normalized contig conflicts"),
        (lambda row: row.pop("region"), "missing legacy evidence region"),
        (lambda row: row.update(Node_ID="NODE_7_length_9000_cov_12"), "missing native inventory Contig"),
    ],
)
def test_native_legacy_anchor_refusals_create_no_outputs(tmp_path: Path, edit, match: str) -> None:
    contig = "NODE_7_length_9000_cov_12.345"
    anchor = _anchor("BGC001", contig)
    edit(anchor)
    package = _package(tmp_path, [_row("BGC001", contig)], [_profile(anchor)], [_convergence(_anchor("BGC001", contig))])
    out = tmp_path / "out"
    with pytest.raises(ExactLocusIdentityError, match=match):
        gg.run(package, out_dir=out, pdf=False, docx=False)
    assert not out.exists()


def test_native_normalization_collision_stays_separate_by_alias(tmp_path: Path) -> None:
    first = "NODE_7_length_9000_cov_12.345"
    second = "NODE_7_length_9000_cov_12.987"
    assert infer_node_id(first, "") == infer_node_id(second, "")
    first_anchor, second_anchor = _anchor("BGC001", first), _anchor("BGC002", second)
    package = _package(
        tmp_path,
        [_row("BGC001", first), _row("BGC002", second)],
        [_profile(first_anchor), _profile(second_anchor)],
        [_convergence(first_anchor), _convergence(second_anchor)],
    )
    rows = gg.run(package, pdf=False, docx=False)["rows"]
    assert {row["exact_locus"] for row in rows} == {
        "TEST-NATIVE / NODE_7_length_9000_cov_12.345 / region001 / BGC001",
        "TEST-NATIVE / NODE_7_length_9000_cov_12.987 / region001 / BGC002",
    }


@pytest.mark.parametrize(
    "rows",
    [
        [_row("BGC001", "NODE_7_length_9000_cov_12.345"), _row("BGC001", "NODE_8_length_9000_cov_12.345")],
        [_row("BGC001", "NODE_7_length_9000_cov_12.345"), _row("BGC002", "NODE_7_length_9000_cov_12.345")],
    ],
)
def test_native_duplicate_alias_or_physical_locus_refuses_before_association(tmp_path: Path, rows: list[dict]) -> None:
    anchor = _anchor("BGC001", "NODE_7_length_9000_cov_12.345")
    package = _package(tmp_path, rows, [_profile(anchor)], [_convergence(anchor)])
    out = tmp_path / "out"
    with pytest.raises(ExactLocusIdentityError, match="repeats (an alias|physical locus)"):
        gg.run(package, out_dir=out, pdf=False, docx=False)
    assert not out.exists()


def test_duplicate_native_alias_refusal_does_not_echo_unadmitted_alias(tmp_path: Path) -> None:
    rows = [_row("BGC001", "NODE_7_length_9000_cov_12.345"), _row("BGC001", "NODE_8_length_9000_cov_12.345")]
    anchor = _anchor("BGC001", "NODE_7_length_9000_cov_12.345")
    package = _package(tmp_path, rows, [_profile(anchor)], [_convergence(anchor)])
    with pytest.raises(ExactLocusIdentityError, match="row 3") as error:
        gg.run(package, pdf=False, docx=False)
    assert "BGC001" not in str(error.value)


def test_duplicate_generic_physical_locus_refuses_before_association(tmp_path: Path) -> None:
    rows = [
        {"BGC_ID": "BGC001", "Contig": "NODE_9_length_9000_cov_1", "antiSMASH_Region": REGION,
         "Products": "NRPS", "Arch_Capacity": "NRPS", "Lead_tier_auto": "High"},
        {"BGC_ID": "BGC002", "Contig": "NODE_9_length_9000_cov_1", "antiSMASH_Region": REGION,
         "Products": "NRPS", "Arch_Capacity": "NRPS", "Lead_tier_auto": "High"},
    ]
    package = _package(tmp_path, rows, [{"bgc_id": "BGC001", "recognizable_gene_fraction": "0.5"}],
                       [{"bgc_id": "BGC001", "dominant_reference": "True"}])
    out = tmp_path / "out"
    with pytest.raises(ExactLocusIdentityError, match="repeats physical locus"):
        gg.run(package, out_dir=out, pdf=False, docx=False)
    assert not out.exists()
