"""Cross-producer verification-context merge regressions.

The synthetic locus is FIXTURE-02 / NODE_1_length_12000_cov_20.000000 /
region001 / BGC001.  These tests preserve both producer findings while pinning
the existing package-value precedence for ordinary context keys.
"""
from __future__ import annotations

import json
from pathlib import Path

from mamey import authored_verify
from mamey import mode_b_receipt as receipt
from tests._modeb_card_fixtures import valid_modeb_card_stub


STRAIN = "FIXTURE-02"
BGC = "BGC001"
NODE = "NODE_1_length_12000_cov_20.000000"
REGION = "region001"
FINDINGS_KEY = "_verification_context_findings"


def _package(tmp_path: Path) -> Path:
    package = tmp_path / "package"
    package.mkdir()
    (package / "manifest.json").write_text(
        json.dumps({"strain_id": STRAIN}), encoding="utf-8"
    )
    (package / f"{STRAIN}_4_triage_board.csv").write_text(
        "BGC_ID,Products,Corrected_rank,Boundary,Lead_tier_auto\n"
        f"{BGC},TRIAGE_VALUE,1,Interior,Inventory\n",
        encoding="utf-8",
    )
    return package


def test_dual_malformed_sources_preserve_both_findings(tmp_path: Path) -> None:
    package = _package(tmp_path)
    (package / f"{STRAIN}_3_antismash_modules.csv").write_text(
        "bgc_id,feature_type\n"
        f"{BGC},aSModule,unexpected\n",
        encoding="utf-8",
    )
    (package / f"{STRAIN}_cds_table.csv").write_text(
        "wrong,header\nvalue,row\n", encoding="utf-8"
    )

    findings = receipt.lint_card_in_package(
        package,
        BGC,
        card_md=valid_modeb_card_stub(BGC, node=NODE, strain_id=STRAIN),
    )
    messages = [str(row.get("message", "")) for row in findings]

    assert any("antiSMASH modules table" in message for message in messages)
    assert any("CDS table" in message for message in messages)


def test_reserved_list_extends_deterministically_without_scalar_drift(
    tmp_path: Path, monkeypatch
) -> None:
    package = _package(tmp_path)
    (package / f"{STRAIN}_3_antismash_modules.csv").write_text(
        "bgc_id,feature_type\n"
        f"{BGC},aSModule,unexpected\n",
        encoding="utf-8",
    )
    triage_only = receipt._bgc_context_from_triage(package, BGC, _cross=False)
    triage_finding = triage_only[FINDINGS_KEY][0]
    package_finding = {
        "severity": "ERROR",
        "code": "VERIFICATION_CONTEXT_MALFORMED",
        "section": None,
        "message": "Package CDS table is present but malformed.",
    }
    monkeypatch.setattr(
        authored_verify,
        "_bgc_context_from_package",
        lambda *_a, **_k: {
            "Products": "PACKAGE_VALUE",
            FINDINGS_KEY: [package_finding, package_finding],
        },
    )

    first = receipt._bgc_context_from_triage(package, BGC)
    second = receipt._bgc_context_from_triage(package, BGC)

    assert first[FINDINGS_KEY] == [triage_finding, package_finding]
    assert second[FINDINGS_KEY] == first[FINDINGS_KEY]
    assert first["Products"] == "PACKAGE_VALUE"


def test_absent_optional_sources_remain_clean(tmp_path: Path) -> None:
    package = _package(tmp_path)

    context = receipt._bgc_context_from_triage(package, BGC)

    assert FINDINGS_KEY not in context
