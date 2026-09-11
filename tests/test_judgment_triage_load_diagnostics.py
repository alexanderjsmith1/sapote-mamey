"""Corrupt triage evidence must not masquerade as optional absence.

The synthetic locus is TEST-001 / NODE_1_length_50000_cov_20.0 /
region001 / BGC001 throughout.
"""
from __future__ import annotations

import json
from pathlib import Path

from mamey import judgment_store
from mamey import seal_package as seal_mod


STRAIN = "TEST-001"
BGC = "BGC001"
NODE = "NODE_1_length_50000_cov_20.0"
REGION = "region001"
CARD = f"# Mode B — {STRAIN} / {NODE} / {REGION} / {BGC}\n§1 capacity context"


def _package(tmp_path: Path) -> Path:
    pkg = tmp_path / STRAIN / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(
        json.dumps({
            "strain_id": STRAIN,
            "bgcs": [{
                "strain": STRAIN,
                "full_node_or_contig": NODE,
                "region": REGION,
                "bgc_alias": BGC,
                "identity_display": f"{STRAIN} / {NODE} / {REGION} / {BGC}",
            }],
        }),
        encoding="utf-8",
    )
    judgment_store.init_register(pkg, STRAIN, [BGC])
    return pkg


def test_corrupt_triage_is_typed_in_write_time_verdict(tmp_path):
    pkg = _package(tmp_path)
    (pkg / f"{STRAIN}_4_triage_board.csv").write_bytes(b"\xff\xfe\x00bad")

    result = judgment_store.record_mode_b(pkg, BGC, CARD)

    assert result["verdict"]["locator"]["status"] == "ERROR"
    assert "triage" in result["verdict"]["locator"]["error"]
    assert result["verdict"]["claim_safety"]["clean"] is None
    assert "triage" in result["verdict"]["claim_safety"]["error"]


def test_missing_triage_retains_optional_write_time_fallback(tmp_path):
    pkg = _package(tmp_path)

    result = judgment_store.record_mode_b(pkg, BGC, CARD)

    assert result["verdict"]["locator"]["status"] == "NO_TRIAGE_ROW"
    assert "error" not in result["verdict"]["claim_safety"]


def test_corrupt_triage_compound_loader_blocks_claim_safety_seal_gate(tmp_path):
    pkg = _package(tmp_path)
    (pkg / f"{STRAIN}_4_triage_board.csv").write_bytes(b"\xff\xfe\x00bad")
    judgment_store.record_mode_b(pkg, BGC, CARD)

    result = seal_mod.seal_package(pkg, strict=True)
    claim = next(g for g in result["gates"] if g["name"] == "claim_safety")

    assert claim["status"] == "FAIL"
    assert claim["blocking"] is True
    assert any("triage board unreadable" in row["detail"] for row in claim["findings"])
