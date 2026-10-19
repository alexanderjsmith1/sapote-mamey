"""v9.7.251 — the redactor rewrites CONTENT, never PATHS.

The v9.7.250 CODE-SCRUBBED artifact shipped `docs/reference/AS-421_AS-696_over_merge_decomposition.csv`:
every row inside redacted to AS-XXX, the strain IDs still in the filename — and repeated verbatim in
TIER_MANIFEST.txt, which is a file list. A content-only scrubber is structurally incapable of seeing this.

`audit_paths()` reports them. Renaming stays a human decision: references must move with the file.

Also pinned here: Python 3.12 splits f-strings into FSTRING_MIDDLE, which is not tokenize.STRING, so a
private ID inside an f-string literal was invisible to the redactor. `tools/build_cohort_precompute.py`
carried `AS-365/AS-705` in a WARN message through every previous public cut.
"""

from tests._synthetic_identity_fixture import synthetic_namespace_id
_PATH_A = synthetic_namespace_id("AS", width=3, case_index=812, separator=True)
_PATH_B = synthetic_namespace_id("AS", width=3, case_index=820, separator=True)
_TEXT_A = synthetic_namespace_id("AS", width=3, case_index=808, separator=True)
_TEXT_B = synthetic_namespace_id("AS", width=3, case_index=821, separator=True)

import importlib.util, pathlib, sys, tokenize, io

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("rpt", ROOT / "tools" / "redact_public_tier.py")
rpt = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(rpt)


def test_audit_paths_finds_a_strain_id_in_a_filename(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / f'{_PATH_A}_{_PATH_B}_notes.csv').write_text("x", encoding="utf-8")
    (tmp_path / "docs" / "clean.csv").write_text("x", encoding="utf-8")
    hits = rpt.audit_paths(tmp_path)
    assert hits == [f'docs/{_PATH_A}_{_PATH_B}_notes.csv']


def test_audit_paths_is_quiet_on_a_clean_tree(tmp_path):
    (tmp_path / "a.md").write_text("no ids", encoding="utf-8")
    assert rpt.audit_paths(tmp_path) == []


def test_audit_paths_does_not_flag_the_public_carve_outs(tmp_path):
    """AS-48 is enterocin AS-48 (a published peptide). One-digit AS-N is prose. Neither is a strain."""
    for name in ("enterocin_AS-48.md", "AS-1_note.md"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    assert rpt.audit_paths(tmp_path) == []


def test_redactor_rewrites_fstring_literals():
    src = ROOT / "tools" / "redact_public_tier.py"
    text = src.read_text(encoding="utf-8")
    assert "FSTRING_MIDDLE" in text, "f-string literals must be redacted (Python 3.12 tokenizes them apart)"


def test_redactor_actually_rewrites_an_id_inside_an_fstring(tmp_path):
    """Historical incident prose above is preserved; this injection uses fabricated controls.
    Public references are not synthetic, and this test grants no disclosure exception."""
    out = rpt.redact_py(f'warn = f"legitimate for {_TEXT_A}/{_TEXT_B} ({{x}})"\n')
    assert f'{_TEXT_A}' not in out and f'{_TEXT_B}' not in out and "AS-XXX" in out
    assert "{x}" in out, "the {expr} part of an f-string is code and must never be rewritten"
