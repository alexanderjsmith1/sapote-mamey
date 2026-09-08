"""Independent downstream diagnostics; no change to numeric admission or scores."""
import csv
import json
import pytest
from mamey.authored_verify import _bgc_context_from_package
from mamey.genome_explore import exploration_board, render_explore
from mamey.modeb_structure_gate import _novelty_conservation_findings

KEY = "SYNTHETIC-001__NODE_1_length_1000_cov_1__region001__BGC001"
OTHER = "SYNTHETIC-001__NODE_2_length_1000_cov_1__region002__BGC002"
IDENTITY = "SYNTHETIC-001 / NODE_1_length_1000_cov_1 / region001 / BGC001"
OTHER_IDENTITY = "SYNTHETIC-001 / NODE_2_length_1000_cov_1 / region002 / BGC002"
CLAIM = "## §11 Product family\nThis represents a novel scaffold with structural novelty.\n"

def package(tmp_path, target=None, other=None, cb=None):
    root = tmp_path / KEY
    root.mkdir()
    records = []
    for i, key in enumerate([KEY, OTHER], 1):
        records.append({"bgc_id": key, "bgc_alias": f"BGC00{i}", "strain": "SYNTHETIC-001",
                        "contig": f"NODE_{i}_length_1000_cov_1", "region_number": i,
                        "products": [], "ab_score": 80, "af_score": 20})
    manifest = {"strain_id": "SYNTHETIC-001", "bgcs": records, "source_scans": {}}
    if cb is not None:
        manifest["source_scans"] = {"clusterblast_genes": {"per_gene_best_hit": {KEY: [{"pct_identity": cb}]}}}
    (root / "manifest.json").write_text(json.dumps(manifest))
    for key, value in [(KEY, target), (OTHER, other)]:
        if value is None:
            continue
        folder = root / "blastp_online"
        folder.mkdir(exist_ok=True)
        with (folder / (key + "_online_blastp.csv")).open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["pct_identity", "channel", "source_channel"])
            writer.writerow([value, "nr", "nr"])
    return root


def presentation_package(tmp_path, value):
    parent = tmp_path / "presentation"
    parent.mkdir()
    root = parent / "SYNTHETIC-001__NODE_1_length_1000_cov_1__region001__BGC001"
    root.mkdir()
    record = {
        "bgc_id": "BGC001", "contig": "NODE_1_length_1000_cov_1",
        "node_id": "NODE_1_length_1000_cov_1", "antismash_region": "region001",
        "region_number": 1, "products": [], "ab_score": 80, "af_score": 20,
    }
    (root / "manifest.json").write_text(
        json.dumps({"strain_id": "SYNTHETIC-001", "bgcs": [record], "source_scans": {}})
    )
    if value is not None:
        overlay = root / "blastp_online"
        overlay.mkdir()
        (overlay / "BGC001_online_blastp.csv").write_text(
            f"pct_identity,channel,source_channel\n{value},nr,nr\n"
        )
    return root

@pytest.mark.parametrize("prose", [CLAIM, "## §11 Product family\nCapacity remains uncharacterised.\n"])
def test_invalid_locus_is_a_warning_without_invented_median(tmp_path, prose):
    root = package(tmp_path, target="NaN")
    context = _bgc_context_from_package(str(root), KEY)
    assert context["conservation_source_status"] == "INVALID"
    assert context.get("conservation_median_id") is None
    findings = _novelty_conservation_findings(prose, context)
    assert any(f["severity"] == "WARN" and "invalid" in f["message"].lower() for f in findings)
    assert not any(f["severity"] == "ERROR" or f["code"] == "NOVELTY_CONTRADICTION" for f in findings)

@pytest.mark.parametrize("bad_background", ["NaN", "101"])
def test_invalid_background_preserves_target_and_qualifies_warning(tmp_path, bad_background):
    root = package(tmp_path, target=95, other=bad_background)
    context = _bgc_context_from_package(str(root), KEY)
    assert context["conservation_median_id"] == 95
    assert context.get("conservation_background_status") == "INVALID"
    assert context.get("conservation_background_id") is None
    warnings = [f for f in _novelty_conservation_findings(CLAIM, context) if f["code"] == "NOVELTY_CONTRADICTION"]
    assert warnings and warnings[0]["severity"] == "WARN"
    message = warnings[0]["message"].lower()
    assert "95" in message and "background" in message and "invalid" in message
    assert "machinery genus-common" not in message


def test_unavailable_background_is_explicit_for_clusterblast_target(tmp_path):
    context = _bgc_context_from_package(str(package(tmp_path, cb=95)), KEY)
    assert context["conservation_median_id"] == 95
    assert context.get("conservation_background_status") == "UNAVAILABLE"
    warnings = [f for f in _novelty_conservation_findings(CLAIM, context) if f["code"] == "NOVELTY_CONTRADICTION"]
    assert warnings and "background" in warnings[0]["message"].lower()
    assert "unavailable" in warnings[0]["message"].lower()
    assert "machinery genus-common" not in warnings[0]["message"].lower()


def test_admitted_background_and_target_are_retained(tmp_path):
    context = _bgc_context_from_package(str(package(tmp_path, target=95, other=60)), KEY)
    assert context.get("conservation_background_status") == "ADMITTED"
    assert context["conservation_background_id"] == 77.5
    assert context["conservation_background_n"] == 2
    assert context["conservation_median_id"] == 95
    message = next(f["message"] for f in _novelty_conservation_findings(CLAIM, context) if f["code"] == "NOVELTY_CONTRADICTION")
    assert "77.5" in message and "17.5" in message

@pytest.mark.parametrize("value,status", [("NaN", "INVALID"), (None, "UNAVAILABLE")])
def test_human_and_board_diagnostics_preserve_status_without_score_bonus(tmp_path, value, status):
    root = package(tmp_path, target=value)
    row = next(r for r in exploration_board(root) if r["bgc_id"] == KEY)
    assert row["exploration_interest"] == 40
    assert row.get("source_status") == status
    text = render_explore(presentation_package(tmp_path, value)).lower()
    assert status.lower() in text


def test_valid_divergence_score_is_unchanged(tmp_path):
    root = package(tmp_path, target=0)
    row = next(r for r in exploration_board(root) if r["bgc_id"] == KEY)
    assert row["divergence_tier"] == "DIVERGENT"
    assert row["exploration_interest"] == 80


def test_directory_iteration_denial_does_not_become_unavailable(tmp_path, monkeypatch):
    from pathlib import Path
    root = package(tmp_path, target=95)
    original = Path.iterdir
    def denied(path):
        if Path(path) == root / "blastp_online":
            raise PermissionError("synthetic scandir denial")
        return original(path)
    monkeypatch.setattr(Path, "iterdir", denied)
    context = _bgc_context_from_package(str(root), KEY)
    assert context["conservation_median_id"] == 95
    assert context.get("conservation_background_status") == "INVALID"


def test_real_stat_denial_does_not_become_unavailable(tmp_path, monkeypatch):
    from pathlib import Path
    root = package(tmp_path, target=95)
    original = Path.stat
    def denied(path, *args, **kwargs):
        if path == root / "blastp_online":
            raise PermissionError("synthetic stat denial")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "stat", denied)
    context = _bgc_context_from_package(str(root), KEY)
    assert context["conservation_median_id"] == 95
    assert context.get("conservation_background_status") == "INVALID"


def test_wrong_kind_background_is_invalid_without_erasing_clusterblast_target(tmp_path):
    root = package(tmp_path, cb=95)
    (root / "blastp_online").write_text("synthetic wrong-kind background")
    context = _bgc_context_from_package(str(root), KEY)
    assert context["conservation_median_id"] == 95
    assert context.get("conservation_background_status") == "INVALID"
