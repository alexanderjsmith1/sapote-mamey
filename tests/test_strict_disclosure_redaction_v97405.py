"""v9.7.405 — REPAIR_16 second half, owner-ruled in: the strict source-disclosure pass is REDACTED
by default. The standalone inventory reports identifier matches; its own diagnostic
output (a retained CI log) must not become the disclosure. `--show-identifiers` restores the verbose
form for interactive triage. Detection itself is pinned by test_strict_source_disclosure_audit_v97395
(which now asks for the verbose form explicitly)."""

from tests._synthetic_identity_fixture import synthetic_namespace_id
_CANARY = synthetic_namespace_id("AS", width=3, case_index=821, separator=True)

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import public_release_audit as pra  # noqa: E402

LOCATOR = re.compile(r"^STRICT_SOURCE_[A-Z_]+: locator=(tests|python)/<redacted:[0-9a-f]{12}>( count=\d+)?$")


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "tree"
    (root / "tests" / "fixtures").mkdir(parents=True)
    (root / "mamey").mkdir()
    (root / "tools").mkdir()
    (root / "tools" / "test_synthetic_ids.txt").write_text("AS-901\n")
    (root / "mamey" / "__init__.py").write_text('__version__ = "1.0.0"\n')
    (root / "BUILD_STAMP.txt").write_text("build=test\n")
    return root


def test_default_findings_are_typed_redacted_and_never_echo_identifier_or_path(tmp_path):
    root = _root(tmp_path)
    (root / "mamey" / "legacy.py").write_text((f'"""Calibrated on {_CANARY} and ' + synthetic_namespace_id('AS', width=3, case_index=917, separator=True) + '."""\nX = 1\n'))
    (root / "tests" / "fixtures" / "exclusions.json").write_text(('{"hard_excluded": ["' + synthetic_namespace_id('AS', width=3, case_index=918, separator=True) + '"]}\n'))
    hits = pra.strict_source_disclosure_findings(root)
    assert hits, "detection must still fire"
    joined = "\n".join(hits)
    for leaked in (f'{_CANARY}', (synthetic_namespace_id('AS', width=3, case_index=917, separator=True)), (synthetic_namespace_id('AS', width=3, case_index=918, separator=True)), "legacy.py", "exclusions.json"):
        assert leaked not in joined, (leaked, hits)
    assert all(LOCATOR.match(h) for h in hits), hits
    py = [h for h in hits if h.startswith("STRICT_SOURCE_IDENTIFIER: locator=python/")]
    assert py and py[0].endswith("count=2"), hits


def test_locator_is_stable_for_the_same_relative_path(tmp_path):
    a = pra._strict_locator(Path("mamey/legacy.py"), "python")
    b = pra._strict_locator(Path("mamey/legacy.py"), "python")
    c = pra._strict_locator(Path("mamey/other.py"), "python")
    assert a == b and a != c and a.startswith("python/<redacted:")


def test_banned_identity_is_redacted_by_default_and_named_on_request(tmp_path):
    root = _root(tmp_path)
    (root / "tests" / "test_x.py").write_text('# reviewed in the SYNTHETIC_PRIVATE_TEST_MARKER chat\n')
    redacted = pra.strict_source_disclosure_findings(root)
    assert any(h.startswith("STRICT_SOURCE_BANNED_IDENTITY: locator=tests/") for h in redacted), redacted
    assert "SYNTHETIC_PRIVATE_TEST_MARKER" not in "\n".join(redacted)
    verbose = pra.strict_source_disclosure_findings(root, show_identifiers=True)
    assert any("banned identity 'SYNTHETIC_PRIVATE_TEST_MARKER'" in h and "test_x.py" in h for h in verbose), verbose


def test_show_identifiers_restores_the_verbose_form(tmp_path):
    root = _root(tmp_path)
    (root / "mamey" / "legacy.py").write_text(f'"""{_CANARY}"""\n')
    verbose = pra.strict_source_disclosure_findings(root, show_identifiers=True)
    assert any("cohort identifier in python source" in h and "legacy.py" in h and f'{_CANARY}' in h
               for h in verbose), verbose


def test_release_strict_checks_do_not_confuse_names_with_private_payloads(tmp_path):
    root = _root(tmp_path)
    (root / "mamey" / "legacy.py").write_text(f'"""{_CANARY}"""\n')
    for verbose in (False, True):
        assert pra.audit(root, strict_source_disclosure=True, show_identifiers=verbose) == []
    (root / "tests" / "private_note.txt").write_text("SYNTHETIC_PRIVATE_TEST_MARKER\n")
    findings = pra.audit(root, strict_source_disclosure=True)
    assert any(h.startswith("STRICT_SOURCE_BANNED_IDENTITY:") for h in findings)
    assert "SYNTHETIC_PRIVATE_TEST_MARKER" not in "\n".join(findings)


def _run(tool, *args):
    import json
    profile = Path(args[0]).parent / "operator_policy.json"
    profile.write_text(json.dumps({
        "schema_version": "sapote_privacy_profile_v1", "profile_id": "synthetic-cli-policy",
        "default_tier": "INTERNAL", "tiers": [{"tier_id": "INTERNAL", "public_export": False}],
        "strain_assignments": [], "public_export_policy": {"private_identifiers": [
            {"identifier_id": "synthetic-marker", "literal": "SYNTHETIC_PRIVATE_TEST_MARKER"},
            {"identifier_id": "synthetic-marker-two", "literal": "regression_review"}]}}))
    if tool == "public_release_audit.py":
        args = (*args, "--privacy-profile", str(profile))
    return subprocess.run([sys.executable, str(ROOT / "tools" / tool), *args],
                          capture_output=True, text=True, timeout=120)


def test_diagnostic_cli_retains_inventory_while_release_cli_permits_names(tmp_path):
    root = _root(tmp_path)
    (root / "mamey" / "legacy.py").write_text(f'"""{_CANARY}"""\n')
    r = _run("strict_source_disclosure_audit.py", str(root))
    assert r.returncode == 1 and _CANARY not in r.stdout + r.stderr and "redacted" in r.stdout
    v = _run("strict_source_disclosure_audit.py", str(root), "--show-identifiers")
    assert v.returncode == 1 and _CANARY in v.stdout
    for flags in ([], ["--show-identifiers"]):
        r = _run("public_release_audit.py", str(root), "--strict-source-disclosure", *flags)
        assert r.returncode == 0 and "PUBLIC RELEASE AUDIT: PASS" in r.stdout
    (root / "tests" / "private_note.txt").write_text("SYNTHETIC_PRIVATE_TEST_MARKER\n")
    r = _run("public_release_audit.py", str(root), "--strict-source-disclosure")
    assert r.returncode == 1 and "SYNTHETIC_PRIVATE_TEST_MARKER" not in r.stdout + r.stderr

import pytest

@pytest.fixture(autouse=True)
def synthetic_private_vocabulary(monkeypatch):
    """Exercise identity detection using invented values, never deployment names."""
    monkeypatch.setattr(pra, "BANNED_IDENTITY", ("SYNTHETIC_PRIVATE_TEST_MARKER", "regression_review"))
