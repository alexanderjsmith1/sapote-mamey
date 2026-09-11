"""BC2 .401 audit: hooks/bgc_node_name_guard.sh — VERIFY/EXTEND task (ROSTER_401_SEEDS.md item
3, "audit control #5"): the guard's original check only ever inspected the FILENAME. Reproduced
live: a genuinely-named file (e.g. "notes.md") whose BODY cites a bare strain+BGC-number with
no node/contig token entirely escapes the guard, even under its own correct
`strain_data/AS-NNN/` scope — the exact wrong-attribution shape (WAC-01375) this guard exists
to catch, just moved from the filename into the prose.

Extended to also scan the file's own on-disk content (this hook is PostToolUse, so the write
has already landed) for `.md`/`.csv` files in scope, reusing the bundle's own authoritative
gate (`mamey.bgc_citation_gate.find_nodeless_bgc_citations()`) rather than a second,
independently-drifting regex.

No hook framework here has a prior test for this hook at all (confirmed: no
`test_bgc_node_name*.py` existed before this file) — first coverage.

Reproduces behavior directly via subprocess against the real hook script (no logic
reimplementation), matching the project's own hook-testing convention.
"""
from __future__ import annotations

import json
import subprocess
import pathlib

HOOKS_DIR = pathlib.Path(__file__).resolve().parents[1] / "hooks"
HOOK = HOOKS_DIR / "bgc_node_name_guard.sh"


def _run(file_path: str) -> tuple[str, int]:
    payload = json.dumps({"tool_input": {"file_path": file_path}})
    proc = subprocess.run(["bash", str(HOOK)], input=payload, capture_output=True,
                          text=True, cwd=str(pathlib.Path(HOOK).resolve().parents[1]))
    return proc.stderr, proc.returncode


def test_hook_present():
    assert HOOK.is_file(), "hooks/bgc_node_name_guard.sh not found"


# -- the actual regression this extension closes ----------------------------------------------

def test_content_only_bare_citation_now_caught(tmp_path, monkeypatch):
    """The real gap this card closes: a generically-named .md file, in scope, whose CONTENT
    (not filename) bare-cites strain+BGC with no node token."""
    strain_dir = tmp_path / "strain_data" / "AS-001"
    strain_dir.mkdir(parents=True)
    target = strain_dir / "notes.md"
    target.write_text("AS-001 / BGC016 shows strong T1PKS signal.\n")
    monkeypatch.chdir(tmp_path)
    err, rc = _run(str(target))
    assert rc == 2, f"expected the guard to warn; got rc={rc}, stderr={err!r}"
    assert "notes.md" in err
    assert "BGC016" in err


def test_content_check_only_applies_to_md_and_csv(tmp_path, monkeypatch):
    """Scoped narrowly per the seed's own wording ('md/csv deliverables') -- a non-md/csv file
    with the same bare citation in its content must not trigger the content scan (filename
    check still applies independently, but this file's name doesn't match BGC\\d+ either)."""
    strain_dir = tmp_path / "strain_data" / "AS-001"
    strain_dir.mkdir(parents=True)
    target = strain_dir / "notes.txt"
    target.write_text("AS-001 / BGC016 shows strong T1PKS signal.\n")
    monkeypatch.chdir(tmp_path)
    err, rc = _run(str(target))
    assert rc == 0, f"expected silence for a non-md/csv file; got rc={rc}, stderr={err!r}"


# -- no regression on the original filename-only behavior --------------------------------------

def test_bare_bgc_filename_still_caught(tmp_path, monkeypatch):
    strain_dir = tmp_path / "strain_data" / "AS-001"
    strain_dir.mkdir(parents=True)
    target = strain_dir / "BGC016_report.md"
    target.write_text("clean prose, no strain+BGC citation here\n")
    monkeypatch.chdir(tmp_path)
    err, rc = _run(str(target))
    assert rc == 2
    assert "Filename names a BGC by number only" in err


def test_properly_node_cited_filename_still_passes(tmp_path, monkeypatch):
    strain_dir = tmp_path / "strain_data" / "AS-001"
    strain_dir.mkdir(parents=True)
    target = strain_dir / "AS-001_NODE162_r001_BGC016_ModeB.md"
    target.write_text("AS-001 / NODE_162_length_5000_cov_12 / region001 / BGC016\n")
    monkeypatch.chdir(tmp_path)
    err, rc = _run(str(target))
    assert rc == 0, f"expected a fully node-cited file+content to pass clean; got {err!r}"


def test_out_of_scope_path_ignores_content_entirely(tmp_path, monkeypatch):
    """The guard's own path scope (strain_data/AS-NNN/) is unchanged by this card -- a bare
    citation OUTSIDE that scope is still not this guard's concern (a separate, larger scope
    question flagged but not acted on in this card)."""
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    target = docs_dir / "random_notes.md"
    target.write_text("AS-001 / BGC016 mentioned here with no node.\n")
    monkeypatch.chdir(tmp_path)
    err, rc = _run(str(target))
    assert rc == 0


# -- content-scan negative controls -------------------------------------------------------------

def test_content_with_proper_node_token_passes(tmp_path, monkeypatch):
    strain_dir = tmp_path / "strain_data" / "AS-001"
    strain_dir.mkdir(parents=True)
    target = strain_dir / "clean_notes.md"
    target.write_text("AS-001 / NODE_162_length_5000_cov_12 / region001 / BGC016 is strong.\n")
    monkeypatch.chdir(tmp_path)
    err, rc = _run(str(target))
    assert rc == 0, f"expected a properly node-cited body to pass; got {err!r}"


def test_count_phrase_does_not_false_positive(tmp_path, monkeypatch):
    """'37 BGCs total' is a count, not a citation -- gate_text()'s own \\bBGC\\d+\\b regex
    correctly never matches the bare word 'BGCs'."""
    strain_dir = tmp_path / "strain_data" / "AS-001"
    strain_dir.mkdir(parents=True)
    target = strain_dir / "summary.md"
    target.write_text("AS-001 has 37 BGCs total across the assembly.\n")
    monkeypatch.chdir(tmp_path)
    err, rc = _run(str(target))
    assert rc == 0, f"expected a count phrase to pass clean; got {err!r}"


def test_nonexistent_target_file_does_not_crash(tmp_path, monkeypatch):
    """The hook receives a file_path that may not exist on disk (e.g. a race, or a tool call
    that failed) -- must fail open, not crash."""
    monkeypatch.chdir(tmp_path)
    err, rc = _run(str(tmp_path / "strain_data" / "AS-001" / "gone.md"))
    assert rc == 0
