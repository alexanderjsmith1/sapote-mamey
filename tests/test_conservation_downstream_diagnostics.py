"""Downstream conservation diagnostics without changing numeric admission or scores."""
import csv
import json

import pytest

from mamey.authored_verify import _bgc_context_from_package
from mamey.genome_explore import (
    _conservation_background_observation,
    exploration_board,
    render_explore,
)
from mamey.modeb_structure_gate import _novelty_conservation_findings


PRIMARY_KEY = "SYNTHETIC-001__NODE_1_length_1000_cov_1__region001__BGC001"
OTHER_KEY = "SYNTHETIC-001__NODE_2_length_1000_cov_1__region002__BGC002"
NOVELTY_CLAIM = "## §11 Product family\nThis represents a novel scaffold with structural novelty.\n"


def _package(tmp_path, *, target=None, other=None, clusterblast=None):
    root = tmp_path / PRIMARY_KEY
    root.mkdir()
    records = [
        {
            "bgc_id": key,
            "bgc_alias": f"BGC00{i}",
            "strain": "SYNTHETIC-001",
            "contig": f"NODE_{i}_length_1000_cov_1",
            "region": f"region00{i}",
            "region_number": i,
            "products": [],
            "ab_score": 80,
            "af_score": 20,
        }
        for i, key in enumerate((PRIMARY_KEY, OTHER_KEY), 1)
    ]
    source_scans = {}
    if clusterblast is not None:
        source_scans = {
            "clusterblast_genes": {
                "per_gene_best_hit": {PRIMARY_KEY: [{"pct_identity": clusterblast}]}
            }
        }
    (root / "manifest.json").write_text(
        json.dumps({"strain_id": "SYNTHETIC-001", "bgcs": records, "source_scans": source_scans}),
        encoding="utf-8",
    )
    for key, value in ((PRIMARY_KEY, target), (OTHER_KEY, other)):
        if value is None:
            continue
        overlay = root / "blastp_online"
        overlay.mkdir(exist_ok=True)
        with (overlay / f"{key}_online_blastp.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["pct_identity", "channel", "source_channel"])
            writer.writerow([value, "nr", "nr"])
    return root


def _presentation_package(tmp_path, value):
    parent = tmp_path / "presentation"
    parent.mkdir()
    root = parent / "SYNTHETIC-001__NODE_1_length_1000_cov_1__region001__BGC001"
    root.mkdir()
    record = {
        "bgc_id": "BGC001",
        "contig": "NODE_1_length_1000_cov_1",
        "node_id": "NODE_1_length_1000_cov_1",
        "antismash_region": "region001",
        "region_number": 1,
        "products": [],
        "ab_score": 80,
        "af_score": 20,
    }
    (root / "manifest.json").write_text(
        json.dumps({"strain_id": "SYNTHETIC-001", "bgcs": [record], "source_scans": {}}),
        encoding="utf-8",
    )
    if value is not None:
        overlay = root / "blastp_online"
        overlay.mkdir()
        (overlay / "BGC001_online_blastp.csv").write_text(
            f"pct_identity,channel,source_channel\n{value},nr,nr\n", encoding="utf-8"
        )
    return root


@pytest.mark.parametrize(
    "prose",
    [NOVELTY_CLAIM, "## §11 Product family\nCapacity remains uncharacterised.\n"],
)
def test_invalid_locus_is_warning_without_invented_median(tmp_path, prose):
    context = _bgc_context_from_package(str(_package(tmp_path, target="NaN")), PRIMARY_KEY)
    assert context["conservation_source_status"] == "INVALID"
    assert context.get("conservation_median_id") is None
    findings = _novelty_conservation_findings(prose, context)
    assert any(
        finding["severity"] == "WARN" and "invalid" in finding["message"].lower()
        for finding in findings
    )
    assert not any(
        finding["severity"] == "ERROR" or finding["code"] == "NOVELTY_CONTRADICTION"
        for finding in findings
    )


@pytest.mark.parametrize("bad_background", ["NaN", "101"])
def test_invalid_background_preserves_target_and_qualifies_warning(tmp_path, bad_background):
    context = _bgc_context_from_package(
        str(_package(tmp_path, target=95, other=bad_background)), PRIMARY_KEY
    )
    assert context["conservation_median_id"] == 95
    assert context["conservation_background_status"] == "INVALID"
    assert context.get("conservation_background_id") is None
    warnings = [
        finding
        for finding in _novelty_conservation_findings(NOVELTY_CLAIM, context)
        if finding["code"] == "NOVELTY_CONTRADICTION"
    ]
    assert warnings and warnings[0]["severity"] == "WARN"
    message = warnings[0]["message"].lower()
    assert "95" in message and "background" in message and "invalid" in message
    assert "genome-relative conservation is not interpretable" in message
    assert "machinery genus-common" not in message


def test_unavailable_background_is_explicit_for_clusterblast_target(tmp_path):
    context = _bgc_context_from_package(
        str(_package(tmp_path, clusterblast=95)), PRIMARY_KEY
    )
    assert context["conservation_median_id"] == 95
    assert context["conservation_background_status"] == "UNAVAILABLE"
    warnings = [
        finding
        for finding in _novelty_conservation_findings(NOVELTY_CLAIM, context)
        if finding["code"] == "NOVELTY_CONTRADICTION"
    ]
    assert warnings
    message = warnings[0]["message"].lower()
    assert "background" in message and "unavailable" in message
    assert "genome-relative conservation is not interpretable" in message
    assert "machinery genus-common" not in message


def test_admitted_background_and_target_are_retained(tmp_path):
    context = _bgc_context_from_package(
        str(_package(tmp_path, target=95, other=60)), PRIMARY_KEY
    )
    assert context["conservation_background_status"] == "ADMITTED"
    assert context["conservation_background_id"] == 77.5
    assert context["conservation_background_n"] == 2
    assert context["conservation_median_id"] == 95
    message = next(
        finding["message"]
        for finding in _novelty_conservation_findings(NOVELTY_CLAIM, context)
        if finding["code"] == "NOVELTY_CONTRADICTION"
    )
    assert "77.5" in message and "+17.5" in message


def test_background_iteration_error_is_invalid_and_target_is_retained(tmp_path, monkeypatch):
    from pathlib import Path

    root = _package(tmp_path, target=95)
    overlay = root / "blastp_online"
    real_iterdir = Path.iterdir

    def fail_for_background(path):
        if Path(path) == overlay:
            raise PermissionError("synthetic directory read failure")
        return real_iterdir(path)

    # Path.iterdir uses different OS primitives across supported Python versions.
    # Intercept the API the production code calls, not its interpreter internals.
    monkeypatch.setattr(Path, "iterdir", fail_for_background)
    observation = _conservation_background_observation(root)
    assert observation["status"] == "INVALID"
    assert observation["median_id"] is None
    context = _bgc_context_from_package(str(root), PRIMARY_KEY)
    assert context["conservation_median_id"] == 95
    assert context["conservation_background_status"] == "INVALID"


def test_background_stat_error_is_invalid_and_target_is_retained(tmp_path, monkeypatch):
    from pathlib import Path

    root = _package(tmp_path, target=95)
    overlay = root / "blastp_online"
    real_stat = Path.stat

    def fail_for_background(path, *args, **kwargs):
        if path == overlay:
            raise PermissionError("synthetic stat failure")
        return real_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fail_for_background)
    context = _bgc_context_from_package(str(root), PRIMARY_KEY)
    assert context["conservation_median_id"] == 95
    assert context["conservation_background_status"] == "INVALID"


def test_wrong_kind_background_is_invalid_without_erasing_clusterblast_target(tmp_path):
    root = _package(tmp_path, clusterblast=95)
    (root / "blastp_online").write_text("synthetic wrong-kind background", encoding="utf-8")
    context = _bgc_context_from_package(str(root), PRIMARY_KEY)
    assert context["conservation_median_id"] == 95
    assert context["conservation_background_status"] == "INVALID"


@pytest.mark.parametrize("value,status", [("NaN", "INVALID"), (None, "UNAVAILABLE")])
def test_human_and_board_diagnostics_preserve_status_without_score_bonus(
    tmp_path, value, status
):
    root = _package(tmp_path, target=value)
    row = next(item for item in exploration_board(root) if item["bgc_id"] == PRIMARY_KEY)
    assert row["exploration_interest"] == 40
    assert row["source_status"] == status
    assert row["invalid_source"] == ("nr" if status == "INVALID" else None)
    assert status.lower() in render_explore(_presentation_package(tmp_path, value)).lower()


def test_valid_divergence_score_is_unchanged(tmp_path):
    root = _package(tmp_path, target=0)
    row = next(item for item in exploration_board(root) if item["bgc_id"] == PRIMARY_KEY)
    assert row["divergence_tier"] == "DIVERGENT"
    assert row["exploration_interest"] == 80
