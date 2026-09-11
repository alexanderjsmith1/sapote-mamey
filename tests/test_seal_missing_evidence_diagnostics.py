"""Regression coverage for seal-time missing/unreadable evidence diagnostics.

Synthetic individual loci always carry complete identities in the manifest,
triage rows, and authored card headings.
"""
from __future__ import annotations

import csv
import builtins
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mamey import seal_package as seal_mod
from mamey.cli import seal_package_command
from mamey.judgment_store import init_register, record_batch_complete


STRAIN = "TEST-001"
BGC_1 = "BGC001"
NODE_1 = "NODE_1_length_50000_cov_20.0"
REGION_1 = "region001"
BGC_2 = "BGC002"
NODE_2 = "NODE_2_length_40000_cov_18.0"
REGION_2 = "region002"


def _package(tmp_path: Path) -> Path:
    pkg = tmp_path / STRAIN / "package"
    pkg.mkdir(parents=True)
    bgcs = [
        {
            "strain": STRAIN,
            "full_node_or_contig": NODE_1,
            "region": REGION_1,
            "bgc_alias": BGC_1,
            "identity_display": f"{STRAIN} / {NODE_1} / {REGION_1} / {BGC_1}",
        },
        {
            "strain": STRAIN,
            "full_node_or_contig": NODE_2,
            "region": REGION_2,
            "bgc_alias": BGC_2,
            "identity_display": f"{STRAIN} / {NODE_2} / {REGION_2} / {BGC_2}",
        },
    ]
    (pkg / "manifest.json").write_text(
        json.dumps({"strain_id": STRAIN, "mode": "gold", "bgcs": bgcs}),
        encoding="utf-8",
    )
    return pkg


def _write_triage(pkg: Path, aliases=(BGC_1,)) -> None:
    identities = {
        BGC_1: (NODE_1, REGION_1),
        BGC_2: (NODE_2, REGION_2),
    }
    with (pkg / f"{STRAIN}_4_triage_board.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "Rank", "BGC_ID", "Node_ID", "Contig", "antiSMASH_Region",
            "Products", "Misanchor_Flag",
        ])
        for rank, alias in enumerate(aliases, 1):
            node, region = identities[alias]
            writer.writerow([rank, alias, node, node, region, "RiPP", ""])


def _card_path(pkg: Path) -> Path:
    judgment = pkg / "judgment"
    judgment.mkdir(exist_ok=True)
    return judgment / f"{STRAIN}_{BGC_1}_mode_b.md"


def _complete_without_card(pkg: Path) -> None:
    init_register(pkg, STRAIN, [BGC_1])
    record_batch_complete(pkg, "session-1", [BGC_1])


@pytest.mark.parametrize("card_state", ["missing", "empty"])
def test_completed_register_card_absence_is_not_reported_as_gate_pass(tmp_path, card_state):
    pkg = _package(tmp_path)
    _write_triage(pkg)
    _complete_without_card(pkg)
    if card_state == "empty":
        _card_path(pkg).write_text("", encoding="utf-8")

    result = seal_mod.seal_package(pkg, strict=True)
    gates = {gate["name"]: gate for gate in result["gates"]}

    assert gates["mode_b_quality"]["status"] == "WARN"
    assert gates["locator_reconciliation"]["status"] == "FAIL"
    assert gates["claim_safety"]["status"] == "FAIL"
    assert any("filed card" in row["detail"] for row in gates["mode_b_quality"]["findings"])
    assert result["overall"] == "FAIL"
    assert result["exit_code"] == 1


def test_unreadable_completed_card_is_structured_not_a_seal_crash(tmp_path, monkeypatch):
    pkg = _package(tmp_path)
    _write_triage(pkg)
    _complete_without_card(pkg)
    card = _card_path(pkg)
    card.write_text(
        f"# Mode B — {STRAIN} / {NODE_1} / {REGION_1} / {BGC_1}\n§1 content",
        encoding="utf-8",
    )
    original_read_text = Path.read_text

    def fail_card_read(path: Path, *args, **kwargs):
        if path == card:
            raise PermissionError("synthetic unreadable filed card")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_card_read)
    result = seal_mod.seal_package(pkg, strict=True)
    gates = {gate["name"]: gate for gate in result["gates"]}

    assert gates["mode_b_quality"]["status"] == "WARN"
    assert gates["locator_reconciliation"]["status"] == "FAIL"
    assert gates["claim_safety"]["status"] == "FAIL"
    assert any("PermissionError" in row["detail"] for row in gates["claim_safety"]["findings"])


def test_cli_receipt_exposes_completed_register_missing_card(tmp_path, capsys):
    pkg = _package(tmp_path)
    _write_triage(pkg)
    _complete_without_card(pkg)
    out = tmp_path / "seal-output"

    exit_code = seal_package_command(SimpleNamespace(
        package_dir=str(pkg),
        strict=True,
        advisory=False,
        out=str(out),
    ))
    capsys.readouterr()
    receipt = json.loads((out / "seal_status.json").read_text(encoding="utf-8"))
    gates = {gate["name"]: gate for gate in receipt["gates"]}

    assert exit_code == 1
    assert gates["mode_b_quality"]["status"] == "WARN"
    assert gates["locator_reconciliation"]["status"] == "FAIL"
    assert gates["claim_safety"]["status"] == "FAIL"


def test_pending_register_without_card_retains_optional_absence_semantics(tmp_path):
    pkg = _package(tmp_path)
    _write_triage(pkg)
    init_register(pkg, STRAIN, [BGC_1])

    result = seal_mod.seal_package(pkg, strict=True)
    gates = {gate["name"]: gate for gate in result["gates"]}

    assert gates["mode_b_quality"]["status"] == "SKIP"
    assert gates["locator_reconciliation"]["status"] == "SKIP"
    assert gates["claim_safety"]["status"] == "WARN"
    assert not any(
        "filed card" in row["detail"]
        for name in ("mode_b_quality", "locator_reconciliation", "claim_safety")
        for row in gates[name]["findings"]
    )


def test_completed_card_without_matching_triage_row_fails_locator(tmp_path):
    pkg = _package(tmp_path)
    _write_triage(pkg, aliases=(BGC_2,))
    _complete_without_card(pkg)
    _card_path(pkg).write_text(
        f"# Mode B — {STRAIN} / {NODE_1} / {REGION_1} / {BGC_1}\n§1 content",
        encoding="utf-8",
    )

    result = seal_mod.seal_package(pkg, strict=True)
    locator = next(g for g in result["gates"] if g["name"] == "locator_reconciliation")

    assert locator["status"] == "FAIL"
    assert any("no matching triage row" in row["detail"] for row in locator["findings"])


def test_matching_readable_card_remains_free_of_missing_evidence_findings(tmp_path):
    pkg = _package(tmp_path)
    _write_triage(pkg)
    _complete_without_card(pkg)
    _card_path(pkg).write_text(
        f"# Mode B — {STRAIN} / {NODE_1} / {REGION_1} / {BGC_1}\n§1 content",
        encoding="utf-8",
    )

    result = seal_mod.seal_package(pkg, strict=True)
    gates = {gate["name"]: gate for gate in result["gates"]}

    for name in ("mode_b_quality", "locator_reconciliation", "claim_safety"):
        assert not any("filed card" in row["detail"] for row in gates[name]["findings"])


def test_unreadable_markdown_is_a_figure_reference_warning(tmp_path, monkeypatch):
    pkg = _package(tmp_path)
    report = pkg / "REPORT.md"
    report.write_text("No figure references.", encoding="utf-8")
    original_read_text = Path.read_text

    def fail_report_read(path: Path, *args, **kwargs):
        if path == report:
            raise PermissionError("synthetic unreadable report")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_report_read)
    gate = seal_mod._gate_figure_references(pkg)

    assert gate.status == "WARN"
    assert any("REPORT.md: unreadable" in row["detail"] for row in gate.findings)


def test_readable_markdown_without_figure_reference_keeps_figure_gate_pass(tmp_path):
    pkg = _package(tmp_path)
    (pkg / "REPORT.md").write_text("No figure references.", encoding="utf-8")

    gate = seal_mod._gate_figure_references(pkg)

    assert gate.status == "PASS"
    assert gate.findings == []


def test_corrupt_judgment_register_is_a_blocking_seal_gate(tmp_path):
    pkg = _package(tmp_path)
    _write_triage(pkg)
    register = pkg / f"{STRAIN}_judgment_register.json"
    register.write_text("{truncated", encoding="utf-8")

    result = seal_mod.seal_package(pkg, strict=True)
    quality = next(g for g in result["gates"] if g["name"] == "mode_b_quality")

    assert quality["status"] == "FAIL"
    assert quality["blocking"] is True
    assert "CORRUPT" in quality["detail"]
    assert result["exit_code"] == 1


def test_missing_judgment_register_retains_not_initialised_semantics(tmp_path):
    pkg = _package(tmp_path)
    _write_triage(pkg)

    result = seal_mod.seal_package(pkg, strict=True)
    quality = next(g for g in result["gates"] if g["name"] == "mode_b_quality")

    assert quality["status"] == "SKIP"
    assert quality["blocking"] is False


def test_corrupt_triage_without_filed_cards_is_not_optional_absence(tmp_path):
    pkg = _package(tmp_path)
    (pkg / f"{STRAIN}_4_triage_board.csv").write_bytes(b"\xff\xfe\x00bad")

    result = seal_mod.seal_package(pkg, strict=True)
    locator = next(g for g in result["gates"] if g["name"] == "locator_reconciliation")

    assert locator["status"] == "FAIL"
    assert locator["blocking"] is True
    assert "UnicodeDecodeError" in locator["detail"]


def test_missing_triage_without_filed_cards_retains_optional_absence(tmp_path):
    pkg = _package(tmp_path)

    result = seal_mod.seal_package(pkg, strict=True)
    locator = next(g for g in result["gates"] if g["name"] == "locator_reconciliation")

    assert locator["status"] == "SKIP"
    assert locator["detail"] == "no filed cards"


@pytest.mark.parametrize(
    ("blocked_import", "gate_name", "expected_detail"),
    [
        ("mamey.mode_b_quality_gate", "mode_b_quality", "import unavailable"),
        ("locator_reconciliation", "locator_reconciliation", "import unavailable"),
        ("claim_safety_linter", "claim_safety", "import unavailable"),
    ],
)
def test_required_gate_import_failure_with_filed_card_is_not_skip(
    tmp_path, monkeypatch, blocked_import, gate_name, expected_detail
):
    pkg = _package(tmp_path)
    _write_triage(pkg)
    _complete_without_card(pkg)
    _card_path(pkg).write_text(
        f"# Mode B — {STRAIN} / {NODE_1} / {REGION_1} / {BGC_1}\n§1 content",
        encoding="utf-8",
    )
    real_import = builtins.__import__

    def block_selected(name, *args, **kwargs):
        if name == blocked_import:
            raise ImportError(f"synthetic missing {blocked_import}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block_selected)
    triage = seal_mod._triage_rows(pkg)[0]
    gate_fn = {
        "mode_b_quality": lambda: seal_mod._gate_mode_b_quality(pkg, triage),
        "locator_reconciliation": lambda: seal_mod._gate_locator(pkg, triage),
        "claim_safety": lambda: seal_mod._gate_claim_safety(pkg),
    }[gate_name]

    gate = gate_fn()

    assert gate.status == "FAIL"
    assert gate.blocking is True
    assert expected_detail in gate.detail


@pytest.mark.parametrize(
    ("blocked_import", "gate_name", "expected_status"),
    [
        ("mamey.mode_b_quality_gate", "mode_b_quality", "SKIP"),
        ("locator_reconciliation", "locator_reconciliation", "SKIP"),
        ("claim_safety_linter", "claim_safety", "WARN"),
    ],
)
def test_optional_no_card_state_is_decided_before_specialist_import(
    tmp_path, monkeypatch, blocked_import, gate_name, expected_status
):
    pkg = _package(tmp_path)
    _write_triage(pkg)
    init_register(pkg, STRAIN, [BGC_1])
    real_import = builtins.__import__

    def block_selected(name, *args, **kwargs):
        if name == blocked_import:
            raise ImportError(f"synthetic missing {blocked_import}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block_selected)
    triage = seal_mod._triage_rows(pkg)[0]
    gate_fn = {
        "mode_b_quality": lambda: seal_mod._gate_mode_b_quality(pkg, triage),
        "locator_reconciliation": lambda: seal_mod._gate_locator(pkg, triage),
        "claim_safety": lambda: seal_mod._gate_claim_safety(pkg),
    }[gate_name]

    gate = gate_fn()

    assert gate.status == expected_status


def test_quality_evaluator_failure_is_structured_not_a_seal_crash(tmp_path, monkeypatch):
    from mamey import mode_b_quality_gate

    pkg = _package(tmp_path)
    _write_triage(pkg)
    _complete_without_card(pkg)
    _card_path(pkg).write_text(
        f"# Mode B — {STRAIN} / {NODE_1} / {REGION_1} / {BGC_1}\n§1 content",
        encoding="utf-8",
    )

    def fail_evaluation(*args, **kwargs):
        raise ValueError("synthetic quality evaluator failure")

    monkeypatch.setattr(mode_b_quality_gate, "evaluate_card", fail_evaluation)
    result = seal_mod.seal_package(pkg, strict=True)
    quality = next(g for g in result["gates"] if g["name"] == "mode_b_quality")

    assert quality["status"] == "WARN"
    assert any("quality evaluation error" in row["detail"] for row in quality["findings"])


def test_locator_evaluator_failure_is_structured_not_a_seal_crash(tmp_path, monkeypatch):
    import locator_reconciliation

    pkg = _package(tmp_path)
    _write_triage(pkg)
    _complete_without_card(pkg)
    _card_path(pkg).write_text(
        f"# Mode B — {STRAIN} / {NODE_1} / {REGION_1} / {BGC_1}\n§1 content",
        encoding="utf-8",
    )

    def fail_reconciliation(*args, **kwargs):
        raise ValueError("synthetic locator evaluator failure")

    monkeypatch.setattr(locator_reconciliation, "reconcile_heading_only", fail_reconciliation)
    result = seal_mod.seal_package(pkg, strict=True)
    locator = next(g for g in result["gates"] if g["name"] == "locator_reconciliation")

    assert locator["status"] == "FAIL"
    assert any("locator evaluation error" in row["detail"] for row in locator["findings"])
