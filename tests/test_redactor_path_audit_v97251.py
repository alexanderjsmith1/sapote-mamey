"""v9.7.251 — the redactor rewrites CONTENT, never PATHS.

The v9.7.250 CODE-SCRUBBED artifact shipped `docs/reference/AS-421_AS-696_over_merge_decomposition.csv`:
every row inside redacted to AS-XXX, the strain IDs still in the filename — and repeated verbatim in
TIER_MANIFEST.txt, which is a file list. A content-only scrubber is structurally incapable of seeing this.

`audit_paths()` reports them. Renaming stays a human decision: references must move with the file.

Also pinned here: Python 3.12 splits f-strings into FSTRING_MIDDLE, which is not tokenize.STRING, so a
private ID inside an f-string literal was invisible to the redactor. `tools/build_cohort_precompute.py`
carried `AS-365/AS-705` in a WARN message through every previous public cut.
"""
import importlib.util, pathlib, sys, tokenize, io

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("rpt", ROOT / "tools" / "redact_public_tier.py")
rpt = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(rpt)


def test_audit_paths_finds_a_strain_id_in_a_filename(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "AS-421_AS-696_notes.csv").write_text("x", encoding="utf-8")
    (tmp_path / "docs" / "clean.csv").write_text("x", encoding="utf-8")
    hits = rpt.audit_paths(tmp_path)
    assert hits == ["docs/AS-421_AS-696_notes.csv"]


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
    """The dev tree legitimately contains real AS ids; asserting their absence here would be wrong.
    What must hold is that the REDACTOR removes them from an f-string when it runs."""
    out = rpt.redact_py('warn = f"legitimate for AS-365/AS-705 ({x})"\n')
    assert "AS-365" not in out and "AS-705" not in out and "AS-XXX" in out
    assert "{x}" in out, "the {expr} part of an f-string is code and must never be rewritten"
