"""guide-gate AS-XXX upstream-omission hardening — sidecar cross-check (v9.7.191).

Implements the 6-case test plan from DESIGN_NOTE_guide_gate_hardening.md: the gate errors ONLY on
interior-gene omission, warns on edge/FC differences, and degrades when the sidecar is absent.
"""
import json

from mamey.bgc_guide import guide_quality_gate


def _guide(bgc_id="BGC005", n=10):
    """Minimal guide dict that passes every OTHER gate check, so a failure isolates the cross-check."""
    return {
        "bgc_id": bgc_id,
        "audience": "both",
        "parts_present": ["P1", "P2", "P3", "P4", "P5"],
        "gene_count": n,
        "claim_safety_line": "capacity consistent with, never produces",
        "genes": [{"locus_tag": f"g{i}", "blastp_readout": "x", "blastp_tier": "TIER_A"} for i in range(n)],
    }


def _write_sidecar(tmp_path, bgc_id, gbk_cds, edge):
    p = tmp_path / "gene_count_crosscheck.json"
    p.write_text(json.dumps({"schema": "gene-count-crosscheck-1.0",
                             "per_bgc": {bgc_id: {"gbk_cds_count": gbk_cds,
                                                  "gbk_edge_cds_count": edge,
                                                  "gbk_source": "NODE_x.region001.gbk"}}}))
    return tmp_path


def test_interior_omission_errors(tmp_path):
    # GBK 27 CDS, 0 edge-droppable; guide has 24 -> 3 interior genes missing -> ERROR
    _write_sidecar(tmp_path, "BGC005", 27, 0)
    ok, errors, _ = guide_quality_gate(_guide(n=24), package=tmp_path)
    assert ok is False
    assert any("AS-XXX upstream-omission" in e for e in errors)


def test_edge_drop_is_ok_warning(tmp_path):
    # GBK 27, 2 edge-droppable; guide has 25 -> within budget -> pass, warning only (AS-162 268-vs-266)
    _write_sidecar(tmp_path, "BGC005", 27, 2)
    ok, errors, warnings = guide_quality_gate(_guide(n=25), package=tmp_path)
    assert ok is True
    assert not errors
    assert any("within edge-droppable budget" in w for w in warnings)


def test_exact_match_clean(tmp_path):
    _write_sidecar(tmp_path, "BGC005", 27, 0)
    ok, errors, warnings = guide_quality_gate(_guide(n=27), package=tmp_path)
    assert ok is True
    assert not errors
    assert not any("omission" in w or "GBK" in w for w in warnings)


def test_csv_gt_gbk_warns(tmp_path):
    _write_sidecar(tmp_path, "BGC005", 27, 0)
    ok, _, warnings = guide_quality_gate(_guide(n=28), package=tmp_path)
    assert ok is True
    assert any("carries genes not in the counted GBK" in w for w in warnings)


def test_absent_sidecar_degrades_warning(tmp_path):
    # no sidecar written -> pass with a degradation warning (not a false-fail)
    ok, errors, warnings = guide_quality_gate(_guide(n=10), package=tmp_path)
    assert ok is True
    assert any("degraded" in w for w in warnings)


def test_no_package_no_crosscheck():
    # backward-compat: called without package (old signature) -> no cross-check, no degradation warning
    ok, errors, warnings = guide_quality_gate(_guide(n=10))
    assert ok is True
    assert not any("cross-check" in w or "omission" in w for w in warnings)
