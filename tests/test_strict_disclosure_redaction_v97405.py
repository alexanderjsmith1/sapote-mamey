"""v9.7.405 — REPAIR_16 second half, owner-ruled in: the strict source-disclosure pass is REDACTED
by default. The gate exists to catch cohort identifiers leaking into a public tree; its own failure
output (a retained CI log) must not become the disclosure. `--show-identifiers` restores the verbose
form for interactive triage. Detection itself is pinned by test_strict_source_disclosure_audit_v97395
(which now asks for the verbose form explicitly)."""
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
    (root / "mamey" / "legacy.py").write_text('"""Calibrated on AS-705 and AS-216."""\nX = 1\n')
    (root / "tests" / "fixtures" / "exclusions.json").write_text('{"hard_excluded": ["AS-260"]}\n')
    hits = pra.strict_source_disclosure_findings(root)
    assert hits, "detection must still fire"
    joined = "\n".join(hits)
    for leaked in ("AS-705", "AS-216", "AS-260", "legacy.py", "exclusions.json"):
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
    (root / "tests" / "test_x.py").write_text('# reviewed in the Cerulean chat\n')
    redacted = pra.strict_source_disclosure_findings(root)
    assert any(h.startswith("STRICT_SOURCE_BANNED_IDENTITY: locator=tests/") for h in redacted), redacted
    assert "Cerulean" not in "\n".join(redacted)
    verbose = pra.strict_source_disclosure_findings(root, show_identifiers=True)
    assert any("banned identity 'Cerulean'" in h and "test_x.py" in h for h in verbose), verbose


def test_show_identifiers_restores_the_verbose_form(tmp_path):
    root = _root(tmp_path)
    (root / "mamey" / "legacy.py").write_text('"""AS-705"""\n')
    verbose = pra.strict_source_disclosure_findings(root, show_identifiers=True)
    assert any("cohort identifier in python source" in h and "legacy.py" in h and "AS-705" in h
               for h in verbose), verbose


def test_audit_threads_the_flag_through(tmp_path):
    root = _root(tmp_path)
    (root / "mamey" / "legacy.py").write_text('"""AS-705"""\n')
    default = pra.audit(root, strict_source_disclosure=True)
    assert any(h.startswith("STRICT_SOURCE_IDENTIFIER:") for h in default) and "AS-705" not in "\n".join(default)
    verbose = pra.audit(root, strict_source_disclosure=True, show_identifiers=True)
    assert any("AS-705" in h for h in verbose)


def _run(tool, *args):
    return subprocess.run([sys.executable, str(ROOT / "tools" / tool), *args],
                          capture_output=True, text=True, timeout=120)


def test_both_clis_redact_by_default_and_expand_on_flag(tmp_path):
    root = _root(tmp_path)
    (root / "mamey" / "legacy.py").write_text('"""AS-705"""\n')
    for tool, base in (("strict_source_disclosure_audit.py", []),
                       ("public_release_audit.py", ["--strict-source-disclosure"])):
        r = _run(tool, str(root), *base)
        assert r.returncode == 1, (tool, r.returncode, r.stdout, r.stderr)
        assert "AS-705" not in r.stdout + r.stderr and "redacted" in r.stdout, (tool, r.stdout)
        v = _run(tool, str(root), *base, "--show-identifiers")
        assert v.returncode == 1 and "AS-705" in v.stdout, (tool, v.stdout, v.stderr)
