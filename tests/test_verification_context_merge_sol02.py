"""Cross-producer verification-context merge regressions.

The synthetic locus is FIXTURE-02 / NODE_1_length_12000_cov_20.000000 /
region001 / BGC001.  These tests preserve both producer findings while pinning
the existing package-value precedence for ordinary context keys.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from mamey import authored_verify
from mamey import mode_b_receipt as receipt
from mamey import __version__ as engine_version
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


def test_older_package_warning_is_typed_and_shared_by_both_doors(tmp_path: Path) -> None:
    package = _package(tmp_path)
    (package / "manifest.json").write_text(
        json.dumps({"strain_id": STRAIN, "workflow_version": "Mamey v1.9.113"}),
        encoding="utf-8",
    )

    direct = authored_verify._bgc_context_from_package(package, BGC)
    ingest = receipt._bgc_context_from_triage(package, BGC)
    for ctx in (direct, ingest):
        matches = [f for f in ctx[FINDINGS_KEY]
                   if f["code"] == "PACKAGE_WORKFLOW_VERSION_OLDER"]
        assert len(matches) == 1
        assert matches[0]["severity"] == "WARN"
        assert "1.9.113" in matches[0]["message"]
        assert engine_version in matches[0]["message"]
        assert BGC not in matches[0]["message"]
        assert str(package) not in matches[0]["message"]
    report = authored_verify.build_verify_report(
        card_name="fixture", profile="test", exit_code=0,
        findings=direct[FINDINGS_KEY], independent_roster_bound=False,
        package_core_denominator_bound=False,
    )
    assert report["warning_instances"] == 1
    assert report["category_summary"][0]["code"] == "PACKAGE_WORKFLOW_VERSION_OLDER"


def test_current_version_is_clean_and_malformed_version_is_typed_error(tmp_path: Path) -> None:
    package = _package(tmp_path)
    manifest = package / "manifest.json"
    manifest.write_text(json.dumps({"workflow_version": engine_version}), encoding="utf-8")
    assert FINDINGS_KEY not in authored_verify._bgc_context_from_package(package, BGC)

    manifest.write_text(json.dumps({"workflow_version": "not-a-version"}), encoding="utf-8")
    context = authored_verify._bgc_context_from_package(package, BGC)
    assert [f["code"] for f in context[FINDINGS_KEY]] == ["VERIFICATION_CONTEXT_MALFORMED"]


def test_emit_template_warns_once_before_writing(tmp_path: Path, monkeypatch, capsys) -> None:
    package = _package(tmp_path)
    (package / "manifest.json").write_text(
        json.dumps({"workflow_version": "1.9.113"}), encoding="utf-8")
    from mamey import blastp_gate, modeb_template_emitter
    monkeypatch.setattr(blastp_gate, "gate", lambda *_a, **_k: {"blocked": False, "message": ""})
    monkeypatch.setattr(modeb_template_emitter, "emit_card_template", lambda *_a, **_k: "fixture template")
    output = tmp_path / "template.md"
    args = SimpleNamespace(package=str(package), bgc=BGC, batch=False,
                           blastp_waiver=None, out=str(output))

    assert receipt.emit_modeb_template_command(args) == 0
    captured = capsys.readouterr()
    assert captured.err.count("PACKAGE_WORKFLOW_VERSION_OLDER") == 1
    assert "1.9.113" in captured.err and engine_version in captured.err
    assert output.read_text(encoding="utf-8") == "fixture template"


def test_emit_template_refuses_malformed_explicit_workflow_version(
    tmp_path: Path, capsys
) -> None:
    package = _package(tmp_path)
    (package / "manifest.json").write_text(
        json.dumps({"workflow_version": "not-a-version"}), encoding="utf-8")
    output = tmp_path / "template.md"
    args = SimpleNamespace(package=str(package), bgc=BGC, batch=False,
                           blastp_waiver=None, out=str(output))

    assert receipt.emit_modeb_template_command(args) == 1
    assert "VERIFICATION_CONTEXT_MALFORMED" in capsys.readouterr().err
    assert not output.exists()
