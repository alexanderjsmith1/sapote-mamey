import argparse
import json
import subprocess
import sys
from pathlib import Path

from mamey.cli import build_parser, main
from mamey.deliverables_registry import (
    CANONICAL_MENU_PATH,
    LEGACY_MENU_PATH,
    availability_for,
    load_registry,
    render_legacy_pointer,
    render_menu,
    validate_registry,
)


ROOT = Path(__file__).resolve().parents[1]


def _top_level_commands() -> set[str]:
    parser = build_parser()
    action = next(
        item for item in parser._actions
        if isinstance(item, argparse._SubParsersAction)
    )
    return set(action.choices)


def test_registry_is_valid_and_ids_are_stable():
    registry = load_registry()
    assert validate_registry(registry) == []
    ids = [item["id"] for item in registry["deliverables"]]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 20


def test_every_declared_cli_command_exists():
    commands = _top_level_commands()
    registry = load_registry()
    missing = sorted({
        command.split()[0]
        for item in registry["deliverables"]
        for command in item["commands"]
        if command.split()[0] not in commands
    })
    assert missing == []


def test_generated_menu_is_current():
    assert CANONICAL_MENU_PATH.read_text(encoding="utf-8") == render_menu()
    assert LEGACY_MENU_PATH.read_text(encoding="utf-8") == render_legacy_pointer()
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "generate_deliverables_menu.py"), "--check"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "DELIVERABLE_MENU_CURRENT" in result.stdout


def test_menu_carries_current_contract_not_stale_modeb_language():
    text = render_menu()
    assert "48-Section" in text
    assert "§1–§20" not in text
    assert "strain / full node-or-contig / region / BGC alias" in text
    assert "PRIVATE — AS-series data" not in text
    assert "Similarity is not identity" in text
    assert "missing or unbound evidence is not biological absence" in text


def test_deliverables_cli_lists_and_explains(capsys):
    assert main(["deliverables", "list", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert any(row["id"] == "M01" for row in rows)
    assert main(["deliverables", "explain", "M01", "--json"]) == 0
    item = json.loads(capsys.readouterr().out)
    assert item["name"] == "Mode B 48-Section Deep Dive"


def test_availability_is_local_read_only_and_fail_closed(tmp_path):
    registry = load_registry()
    modeb = next(item for item in registry["deliverables"] if item["id"] == "M01")
    missing = availability_for(modeb)
    assert missing.state == "INPUT_OR_LOCAL_DEPENDENCY_REQUIRED"
    assert "sealed_package" in missing.missing
    assert "exact_locus_identity" in missing.missing

    package = tmp_path / "package"
    package.mkdir()
    (package / "manifest.json").write_text("{}", encoding="utf-8")
    complete = availability_for(
        modeb,
        package=str(package),
        locus="STRAIN-001 / NODE_12_length_48000_cov_30.1 / region001 / BGC007",
    )
    assert complete.state == "JUDGMENT_REQUIRED"
    assert complete.missing == ()
    assert any("canonical_protein_roster" in note for note in complete.notes)


def test_external_workflow_never_self_authorizes():
    registry = load_registry()
    remote = next(item for item in registry["deliverables"] if item["id"] == "E03")
    result = availability_for(remote)
    assert result.state == "EXTERNAL_CONTACT_AUTHORIZATION_REQUIRED"
    assert any("external_contact_authorization" in note for note in result.notes)


def test_session_checklist_consumes_registry_and_does_not_call_presence_done(tmp_path):
    # v9.7.405: session_checklist now takes the governed durable-root interface (CODEX_396 recovery
    # locator repair 14) rather than a bare --scan; build the same portable fixture that
    # tests/test_recovery_locator_and_durability_root_v97396.py uses.
    outputs = tmp_path / "outputs" / "current"; outputs.mkdir(parents=True)
    config = tmp_path / "roots.json"
    config.write_text(json.dumps({"schema_version": "sapote_evidence_root_config_v1",
                                  "roots": {"session_outputs": {"path": "outputs"}}}), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "session_checklist.py"),
         "--durable-root-config", str(config), "--durable-root-id", "session_outputs",
         "--scan-relative", "current", "--receipt-relative", "receipts/close.json"],
        cwd=ROOT, text=True, capture_output=True, env={"PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "#5 Mode B 48-Section Deep Dive" in result.stdout
    assert "Artifact presence is not gate success" in result.stdout
    assert "Operational run records (not scientific deliverables)" in result.stdout
    assert "[x]=done" not in result.stdout.lower()
