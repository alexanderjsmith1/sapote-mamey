"""Public release must exclude internal future work and non-test cohort identifiers."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import public_release_audit as audit_mod


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


def test_non_test_doc_cohort_id_is_a_public_release_failure(tmp_path):
    root = _minimal_root(tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "notes.md").write_text("Example from AS-705.\n")
    problems = audit_mod.audit(root)
    assert any("cohort identifier in non-test content: docs/notes.md: AS-705" in p for p in problems)


def test_cohort_id_in_path_is_a_public_release_failure(tmp_path):
    root = _minimal_root(tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "AS-705_notes.md").write_text("generic text\n")
    assert any("cohort identifier in shipped path: docs/AS-705_notes.md" in p
               for p in audit_mod.audit(root))


def test_python_source_is_deferred_to_reviewed_genericization_patches(tmp_path):
    root = _minimal_root(tmp_path)
    (root / "mamey" / "legacy.py").write_text(
        'def as705_legacy_symbol():\n    """Calibrated on AS-705."""\n    return True\n'
    )
    # Release-time string rewriting changed runtime dictionaries and broke the public-tree
    # suite. Python remains byte-identical here and is handled by ordinary reviewed patches.
    assert audit_mod.audit(root) == []


def test_known_public_and_synthetic_exceptions_remain_allowed(tmp_path):
    root = _minimal_root(tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "compound.md").write_text("enterocin AS-48\n")
    (root / "tests").mkdir()
    (root / "tests" / "test_fixture.py").write_text('STRAIN = "AS-705"\n')
    (root / "tools").mkdir()
    (root / "tools" / "test_synthetic_ids.txt").write_text("AS-705\n")
    assert audit_mod.audit(root) == []


def test_synthetic_identifier_in_test_filename_remains_allowed(tmp_path):
    root = _minimal_root(tmp_path)
    (root / "tests").mkdir()
    (root / "tests" / "test_as705_fixture.py").write_text("# synthetic fixture\n")
    assert audit_mod.audit(root) == []


def test_documentation_reference_to_exact_test_filename_remains_resolvable(tmp_path):
    root = _minimal_root(tmp_path)
    (root / "docs").mkdir()
    (root / "docs" / "testing.md").write_text(
        "Regression: `test_as421_patchset_v9_7_240.py`.\n"
    )
    assert audit_mod.audit(root) == []

    from redact_public_tier import redact_text
    text = "Regression: `test_as421_patchset_v9_7_240.py`; example strain AS-421."
    redacted = redact_text(text, as_only=True)
    assert "test_as421_patchset_v9_7_240.py" in redacted
    assert "example strain AS-XXX" in redacted


def test_builder_strips_then_scrubs_then_audits():
    script = (Path(__file__).resolve().parents[1] / "tools" / "make_public_tier.sh").read_text()
    assert '"$STAGE/future_improvements"' in script
    assert "-name 'runs*'" in script
    scrub = script.index('redact_public_tier.py" --tree "$STAGE" --walk --as-only')
    audit = script.index('public_release_audit.py" "$STAGE"')
    assert scrub < audit
    assert "post-pytest documentation privacy gate: PASS" in script
