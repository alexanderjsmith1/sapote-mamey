"""Lightweight regression checks for the v1.9.2 package contract.

These tests avoid requiring real antiSMASH input. They protect the cross-LLM
handoff contract that is easy to break accidentally: validate must import without
Biopython, the package must not contain the old brace-expansion artifact, and the
kernel/docs must point to manifest.json as the handoff object.
"""
from pathlib import Path


def test_no_brace_expansion_artifact():
    assert not Path('{mamey,docs,scripts,tests}').exists()


def test_kernel_mentions_manifest_schema():
    text = Path('docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md').read_text(encoding='utf-8')
    assert 'manifest.json' in text
    assert 'source_scans.glycosylation_arms' in text
    assert 'Do **not** assume a top-level `context` object' in text


def test_how_to_use_warns_custom_instructions_too_small():
    text = Path('docs/HOW_TO_USE.md').read_text(encoding='utf-8')
    assert 'will not fit' in text
    assert 'manifest.json' in text
    assert 'Project_Memory_Snapshot.json' in text


def test_validate_imports_without_parsers_import_side_effect():
    from mamey.validate import validate_package  # noqa: F401



def test_cell_provenance_in_required_suffixes():
    """L3: cell_provenance is written on every run; validate must require it."""
    from mamey.validate import REQUIRED_SUFFIXES
    assert any("7_cell_provenance.csv" in s for s in REQUIRED_SUFFIXES), \
        "7_cell_provenance.csv missing from REQUIRED_SUFFIXES"
