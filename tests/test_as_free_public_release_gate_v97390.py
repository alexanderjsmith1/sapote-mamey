"""Public release excludes private payloads while preserving names and class associations."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import public_release_audit as audit_mod

if __package__ in (None, ""):
    from _synthetic_identity_fixture import synthetic_namespace_id
else:
    from tests._synthetic_identity_fixture import synthetic_namespace_id
_FORMAT_CASE_2 = synthetic_namespace_id('AS', width=3, case_index=821)
_FORMAT_CASE_1 = synthetic_namespace_id('AS', width=3, case_index=812)


def _minimal_root(tmp_path: Path) -> Path:
    (tmp_path / "mamey").mkdir()
    (tmp_path / "mamey" / "__init__.py").write_text('__version__ = "1.0.0"\n')
    (tmp_path / "BUILD_STAMP.txt").write_text("build=20260829v97390b\n")
    return tmp_path


def test_future_improvements_is_a_public_release_failure(tmp_path):
    root = _minimal_root(tmp_path)
    (root / "future_improvements").mkdir()
    (root / "future_improvements" / "plan.md").write_text("internal only\n")
    assert "internal future-work directory ships: future_improvements/" in audit_mod.audit(root)


def test_name_only_documentation_is_permitted(tmp_path):
    root = _minimal_root(tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "notes.md").write_text(f"Example from {_FORMAT_CASE_2}.\n")
    problems = audit_mod.audit(root)
    assert problems == []


def test_name_only_path_is_permitted(tmp_path):
    root = _minimal_root(tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / f"{_FORMAT_CASE_2}_notes.md").write_text("generic text\n")
    assert audit_mod.audit(root) == []


def test_python_names_keep_their_meaning(tmp_path):
    root = _minimal_root(tmp_path)
    (root / "mamey" / "legacy.py").write_text(
        f'def {_FORMAT_CASE_2.replace("-", "").lower()}_legacy_symbol():\n    """Calibrated on {_FORMAT_CASE_2}."""\n    return True\n'
    )
    # Names alone do not establish private payloads; preserve source semantics.
    assert audit_mod.audit(root) == []


def test_known_public_and_synthetic_exceptions_remain_allowed(tmp_path):
    root = _minimal_root(tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "compound.md").write_text("enterocin AS-48\n")
    (root / "tests").mkdir()
    (root / "tests" / "test_fixture.py").write_text(f'STRAIN = "{_FORMAT_CASE_2}"\n')
    (root / "tools").mkdir()
    (root / "tools" / "test_synthetic_ids.txt").write_text(f"{_FORMAT_CASE_2}\n")
    assert audit_mod.audit(root) == []


def test_synthetic_identifier_in_test_filename_remains_allowed(tmp_path):
    root = _minimal_root(tmp_path)
    (root / "tests").mkdir()
    (root / "tests" / f"test_{_FORMAT_CASE_2.replace("-", "").lower()}_fixture.py").write_text("# synthetic fixture\n")
    assert audit_mod.audit(root) == []


def test_documentation_reference_to_exact_test_filename_remains_resolvable(tmp_path):
    root = _minimal_root(tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "testing.md").write_text(
        "Regression: `test_as421_patchset_v9_7_240.py`.\n"
    )
    assert audit_mod.audit(root) == []

    from redact_public_tier import redact_text
    text = f"Regression: `test_as421_patchset_v9_7_240.py`; example strain {_FORMAT_CASE_1}."
    redacted = redact_text(text, as_only=True)
    assert "test_as421_patchset_v9_7_240.py" in redacted
    assert "example strain AS-XXX" in redacted


def test_builder_preserves_names_and_still_audits_content():
    script = (Path(__file__).resolve().parents[1] / "tools" / "make_public_tier.sh").read_text()
    assert '"$STAGE/future_improvements"' in script
    assert "-name 'runs*'" in script
    assert 'redact_public_tier.py" --tree' not in script
    assert 'public_release_audit.py" "$STAGE"' in script
    assert "post-pytest content privacy gate: PASS" in script
    assert 'verify_staged_test_snapshot' in script
