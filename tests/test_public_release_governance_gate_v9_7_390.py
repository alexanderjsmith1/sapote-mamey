"""v9.7.390 candidate: PUBLIC_RELEASE promotion requires active GOV-001 authority."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "public_release_audit.py"


def _load():
    spec = importlib.util.spec_from_file_location("public_release_audit_governance", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _tree(tmp_path: Path, decision: dict | None, *, duplicates: int = 1) -> Path:
    (tmp_path / "mamey").mkdir(parents=True)
    (tmp_path / "mamey" / "__init__.py").write_text('__version__ = "1.0.0"\n', encoding="utf-8")
    (tmp_path / "BUILD_STAMP.txt").write_text("build=test\n", encoding="utf-8")
    decisions = [] if decision is None else [decision.copy() for _ in range(duplicates)]
    (tmp_path / "GOVERNANCE_DECISIONS.json").write_text(
        json.dumps({"schema_version": "sapote.governance_decisions/1", "decisions": decisions}),
        encoding="utf-8",
    )
    return tmp_path


def _decision(status="ACTIVE", invalidated=False, signer="owner", date="2026-08-29"):
    return {
        "id": "GOV-001",
        "status": status,
        "condition_currently_true": invalidated,
        "asserted_signer": signer,
        "asserted_date": date,
    }


def test_active_signed_noninvalidated_decision_passes(tmp_path):
    mod = _load()
    assert mod.audit_governance(_tree(tmp_path, _decision()), "GOV-001") == []


def test_pending_repudiated_and_expired_fail_closed(tmp_path):
    mod = _load()
    for index, status in enumerate(("PENDING_OWNER_CONFIRMATION", "REPUDIATED", "EXPIRED")):
        root = _tree(tmp_path / str(index), _decision(status=status))
        hits = mod.audit_governance(root, "GOV-001")
        assert hits and "GOVERNANCE_DECISION_NOT_ACTIVE" in hits[0]


def test_active_but_invalidated_or_unsigned_fails_closed(tmp_path):
    mod = _load()
    invalid = mod.audit_governance(_tree(tmp_path / "invalid", _decision(invalidated=True)), "GOV-001")
    unsigned = mod.audit_governance(_tree(tmp_path / "unsigned", _decision(signer="")), "GOV-001")
    assert invalid and "GOVERNANCE_DECISION_INVALIDATED" in invalid[0]
    assert unsigned and "GOVERNANCE_DECISION_UNSIGNED" in unsigned[0]


def test_missing_duplicate_and_malformed_ledgers_fail_closed(tmp_path):
    mod = _load()
    missing = mod.audit_governance(_tree(tmp_path / "missing", None), "GOV-001")
    duplicate = mod.audit_governance(_tree(tmp_path / "duplicate", _decision(), duplicates=2), "GOV-001")
    malformed_root = _tree(tmp_path / "malformed", _decision())
    (malformed_root / "GOVERNANCE_DECISIONS.json").write_text("{", encoding="utf-8")
    malformed = mod.audit_governance(malformed_root, "GOV-001")
    assert "matched 0" in missing[0]
    assert "matched 2" in duplicate[0]
    assert "GOVERNANCE_LEDGER_UNREADABLE" in malformed[0]


def test_cli_governance_only_exit_codes(tmp_path):
    mod = _load()
    active = _tree(tmp_path / "active", _decision())
    pending = _tree(tmp_path / "pending", _decision(status="PENDING_OWNER_CONFIRMATION"))
    args = [str(active), "--governance-only", "--require-active-decision", "GOV-001"]
    assert mod.main(args) == 0
    args[0] = str(pending)
    assert mod.main(args) == 1


def test_public_builder_wires_gate_only_to_public_tier():
    script = (ROOT / "tools" / "make_public_tier.sh").read_text(encoding="utf-8")
    assert 'if [ "$TIER" = "public" ]; then' in script
    assert "--governance-only" in script
    assert "--require-active-decision GOV-001" in script
    assert "CODE candidate tiers remain available" in script
