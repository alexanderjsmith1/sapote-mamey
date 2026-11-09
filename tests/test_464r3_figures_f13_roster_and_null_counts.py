"""F13 holds when a manifest BGC has no domain row, or a domain count is present but null."""
import json

import pytest

pytest.importorskip("matplotlib")

from mamey import cohort_figures as figures
from mamey import figure_policy


def _package(root, strain, bgcs, archs):
    package = root / strain / "package"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(json.dumps({
        "strain_id": strain, "workflow_version": "1.9.99",
        "bgcs": [{"bgc_id": b, "node_id": "CONTIG_1.1", "antismash_region": f"region00{i}"}
                 for i, b in enumerate(bgcs, 1)],
    }))
    (package / f"{strain}_1_intake.json").write_text(json.dumps({"antismash_version": "8.0.1"}))
    (package / "gene_data.json").write_text(json.dumps({"domain_arch": [
        {"bgc_id": b, "architecture": {"domain_counts": counts}} for b, counts in archs
    ]}))
    return {"pkg": str(package)}


def _eligible(*strains):
    return {s: {"genus": "Streptomyces", "cohort": "BEE", "assembly_state": "PASS"} for s in strains}


def test_manifest_bgc_without_domain_row_holds(tmp_path):
    source = {
        "EX-1": _package(tmp_path, "EX-1", ["BGC001", "BGC002", "BGC003"],
                         [("BGC001", {"PKS_KS": 1}), ("BGC002", {"NRPS_A": 2})]),
    }
    with pytest.raises(figure_policy.FigurePolicyError) as caught:
        figures._f13_rows(source, _eligible("EX-1"))
    assert caught.value.code == "F13_DOMAIN_ARCH_BGC_MISSING"
    assert "BGC003" in caught.value.detail


def test_null_domain_count_holds_instead_of_zero(tmp_path):
    source = {
        "EX-1": _package(tmp_path, "EX-1", ["BGC001", "BGC002"],
                         [("BGC001", {"PKS_KS": None}), ("BGC002", {"NRPS_A": 2})]),
    }
    with pytest.raises(figure_policy.FigurePolicyError) as caught:
        figures._f13_rows(source, _eligible("EX-1"))
    assert caught.value.code == "F13_DOMAIN_COUNT_MISSING"


def test_absent_domain_key_is_a_counted_zero(tmp_path):
    source = {
        "EX-1": _package(tmp_path, "EX-1", ["BGC001", "BGC002"],
                         [("BGC001", {"PKS_KS": 1}), ("BGC002", {"NRPS_A": 2})]),
    }
    rows, _bindings, _versions, regions = figures._f13_rows(source, _eligible("EX-1"))
    assert regions == 2
    assert len(rows) == 2
