"""Source/stage text parity preserves genuine names and detects scientific-text drift."""
from __future__ import annotations

from tests._synthetic_identity_fixture import synthetic_namespace_id

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))


def test_redact_text_leaves_sid_untouched():
    """SID strain IDs are public (Chevrette 2019) and must survive
    verify_tier_derivation's redaction pass, matching the real tier-build
    policy (--as-only) rather than the previously-hardcoded as_only=False."""
    from verify_tier_derivation import redact_text

    text = "A BGC was detected in SID8370 (NODE_3 · region_004) with no close KCB match."
    redacted = redact_text(text)
    assert "SID8370" in redacted, (
        "SID strain IDs must NOT be redacted — they are public (Chevrette 2019). "
        "If this fails, as_only has regressed to False."
    )


def test_names_are_preserved_independently_of_legacy_switches(monkeypatch):
    import verify_tier_derivation as vtd
    text = "Strain AS-999; BGC class NRPS."
    for value in (None, "0", "1", "invalid"):
        if value is None: monkeypatch.delenv("AS_SCRUB", raising=False)
        else: monkeypatch.setenv("AS_SCRUB", value)
        assert vtd.redact_text(text) == text
        assert vtd.redact("docs/note.md", text) == text
        assert vtd.redact("data/labels.json", '{"AS-999":"NRPS"}') == '{"AS-999":"NRPS"}'


def test_public_derivation_models_internal_and_run_directory_stripping():
    from verify_tier_derivation import _is_stripped

    assert _is_stripped("future_improvements/gap_analysis.md")
    assert _is_stripped("runs/example/package.json")
    assert _is_stripped("runs-old/example/package.json")
    assert _is_stripped("private/cohort.tsv")
    assert _is_stripped("docs/legacy/obsolete.md")
    assert _is_stripped(".pytest_cache/README.md")
    assert not _is_stripped("mamey/cli.py")
    assert not _is_stripped("docs/PUBLIC_RELEASE_GUIDE.md")


def test_redact_py_leaves_sid_untouched():
    """Same fix, .py code-comment path (redact_py uses the same as_only flag)."""
    from verify_tier_derivation import redact_py

    text = '# Reference strain: SID8371\nSTRAIN_ID = "SID8371"\n'
    redacted = redact_py(text)
    assert "SID8371" in redacted


def test_path_level_derivation_keeps_python_byte_identical():
    from verify_tier_derivation import redact

    text = ('HOST_GROUPS = {"' + synthetic_namespace_id('AS', width=3, case_index=917, separator=True) + '": "ATTINE_ANT"}\n')
    assert redact("mamey/widget_data.py", text) == text


def test_derivation_checks_preserved_text_and_missing_or_changed_files(tmp_path, monkeypatch):
    import verify_tier_derivation as vtd
    source, stage = tmp_path / "source", tmp_path / "stage"
    source.mkdir(); stage.mkdir()
    text = "AS-999\tNRPS\n"
    (source / "labels.txt").write_text(text)
    (stage / "labels.txt").write_text(text)
    monkeypatch.setattr(sys, "argv", ["verify_tier_derivation", str(source), str(stage)])
    assert vtd.main() == 0
    (stage / "labels.txt").write_text("AS-999\tPKS\n")
    assert vtd.main() == 1
    (stage / "labels.txt").unlink()  # only this test's newly created file
    assert vtd.main() == 1
