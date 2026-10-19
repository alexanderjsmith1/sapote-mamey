"""Lab Quest is removed (v9.7.450): no add-on, no command, no install path; old project folders still read."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import mamey
from mamey import cli
from mamey.portfolio_config import LEGACY_PROJECT_OUTPUT_DIR, PROJECT_OUTPUT_DIR, project_output_dir
from mamey.project_catalog import ProjectCatalog

ROOT = Path(mamey.__file__).resolve().parent.parent


def test_addon_source_docs_and_command_are_gone():
    assert not (ROOT / "sapote_addons" / "lab_quest").exists()
    assert not (ROOT / "docs" / "LAB_QUEST.md").exists()
    assert "lab-quest" not in cli.build_parser().format_help()
    assert "LAB_QUEST" not in (ROOT / "bundle_support" / "install_sapote_addons.sh").read_text()



def _has_removed_addon_mention(text, rel):
    terms = ("lab quest", "lab_quest", "lab-quest")
    if rel != "docs/FILE_ATLAS.csv":
        return any(term in text.lower() for term in terms)
    # Generated test_refs names regression coverage, not an available feature.
    # Retain and scan the CSV; only the exact removal-test basename is provenance.
    reader = csv.DictReader(io.StringIO(text, newline=""))
    columns = ["path", "loc", "summary", "n_defs", "n_classes", "fan_out", "imports_internal",
               "fan_in", "imported_by", "cli_verbs", "n_tests", "test_refs", "shell_refs", "orphan"]
    assert reader.fieldnames == columns, "unexpected file-atlas schema"
    for row in reader:
        assert set(row) == set(columns) and all(value is not None for value in row.values()), "malformed file-atlas row"
        for column, value in row.items():
            if column == "test_refs":
                value = ";".join(ref for ref in value.split(";") if ref != "test_450_lab_quest_removed.py")
            if any(term in value.lower() for term in terms):
                return True
    return False

def test_no_lab_quest_mention_in_shipped_code_or_current_docs():
    history = {"CHANGELOG.md", "ENGINE_LINEAGE.md", "SOURCE_CHECKSUMS_SHA256.txt", "TIER_MANIFEST.txt"}
    allowed = {"mamey/portfolio_config.py", "tools/gen_command_catalog.py", "tools/check_command_pointers.py",
               "docs/PROJECT_CATALOG.md"}  # the legacy folder name and the removal notes
    hits = []
    for d in ("mamey", "tools", "docs", "bundle_support", "sapote_addons"):
        for p in (ROOT / d).rglob("*"):
            if not p.is_file() or "__pycache__" in p.parts or p.name in history or p.suffix in (".pyc", ".png", ".pdf"):
                continue
            rel = p.relative_to(ROOT).as_posix()
            if rel in allowed:
                continue
            text = p.read_text(encoding="utf-8", errors="ignore").lower()
            if _has_removed_addon_mention(text, rel):
                hits.append(rel)
    assert not hits, hits


def test_new_projects_write_project_outputs(tmp_path):
    ProjectCatalog(tmp_path)
    assert (tmp_path / PROJECT_OUTPUT_DIR).is_dir()
    assert not (tmp_path / LEGACY_PROJECT_OUTPUT_DIR).exists()


def test_existing_legacy_folder_is_still_used(tmp_path):
    legacy = tmp_path / LEGACY_PROJECT_OUTPUT_DIR
    legacy.mkdir()
    (legacy / "keep.json").write_text(json.dumps({}))
    assert project_output_dir(tmp_path) == legacy
    ProjectCatalog(tmp_path)
    assert not (tmp_path / PROJECT_OUTPUT_DIR).exists()

def test_atlas_removal_reference_is_provenance_only():
    columns = ["path", "loc", "summary", "n_defs", "n_classes", "fan_out", "imports_internal",
               "fan_in", "imported_by", "cli_verbs", "n_tests", "test_refs", "shell_refs", "orphan"]
    row = dict.fromkeys(columns, "")
    row.update(path="tools/example.py", summary="Example tool.", test_refs="test_450_lab_quest_removed.py;test_other.py")
    def render(values):
        out = io.StringIO(newline="")
        writer = csv.DictWriter(out, fieldnames=columns)
        writer.writeheader()
        writer.writerow(values)
        return out.getvalue()
    assert not _has_removed_addon_mention(render(row), "docs/FILE_ATLAS.csv")
    for column in columns:
        changed = dict(row)
        changed[column] = "lab-quest"
        assert _has_removed_addon_mention(render(changed), "docs/FILE_ATLAS.csv"), column
    for bad in ("test_lab_quest_active.py", "test_450_lab_quest_removed.py suffix", "prefix_test_450_lab_quest_removed.py"):
        changed = dict(row, test_refs=bad)
        assert _has_removed_addon_mention(render(changed), "docs/FILE_ATLAS.csv")
    assert _has_removed_addon_mention("test_450_lab_quest_removed.py", "docs/other.csv")
    for text in ("", "path,test_refs\ntools/example.py,test_450_lab_quest_removed.py\n", ",".join(columns)+"\ntools/example.py\n", render(row).rstrip()+",extra\n"):
        try:
            _has_removed_addon_mention(text, "docs/FILE_ATLAS.csv")
        except AssertionError:
            pass
        else:
            raise AssertionError("malformed atlas must be refused")

