"""BC2-AP-01 (v9.7.395): redact_public_tier.py's audit_paths() must catch a private strain ID
leaked into a lowercase/mixed-case FILENAME, not just an uppercase one.

audit_paths() exists specifically to close the "content-only scrubbing cannot see this" gap for a
private strain ID leaked into a filename (see test_redactor_path_audit_v97251.py / CHANGELOG.md
v9.7.251) — but its internal pattern lacked re.IGNORECASE even though AS_RE, the near-identical
content-scrubbing pattern nine lines above it in the same file, has it. A lowercase or mixed-case
filename carrying the same private strain ID silently escaped this specific detector while the
uppercase form was caught.

Reproduced live against the unpatched tools/redact_public_tier.py before this fix.
"""
import importlib.util, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("rpt", ROOT / "tools" / "redact_public_tier.py")
rpt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rpt)


def test_audit_paths_finds_a_lowercase_strain_id_in_a_filename(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "as-705_over_merge_decomposition_backup.csv").write_text("x", encoding="utf-8")
    hits = rpt.audit_paths(tmp_path)
    assert hits == ["docs/as-705_over_merge_decomposition_backup.csv"], (
        f"a private strain ID leaked into a lowercase filename must be caught; got: {hits}"
    )


def test_audit_paths_finds_both_cases_in_a_mixed_tree(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "AS-705_notes.csv").write_text("x", encoding="utf-8")
    (tmp_path / "docs" / "as-705_notes_backup.csv").write_text("x", encoding="utf-8")
    (tmp_path / "docs" / "clean.csv").write_text("x", encoding="utf-8")
    hits = sorted(rpt.audit_paths(tmp_path))
    assert hits == sorted(["docs/AS-705_notes.csv", "docs/as-705_notes_backup.csv"])


def test_lowercase_public_carve_outs_still_not_flagged(tmp_path):
    # Regression guard: widening to IGNORECASE must not newly false-positive on a differently-cased
    # mention of a known public carve-out (enterocin AS-48; one-digit AS-N is prose).
    for name in ("enterocin_as-48.md", "enterocin_AS-48.md", "as-1_note.md"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    assert rpt.audit_paths(tmp_path) == []
