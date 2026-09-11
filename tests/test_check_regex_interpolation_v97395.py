"""v9.7.395: regression tests for tools/check_regex_interpolation.py — the unbound-alternation
regex gate.

Motivating shipped defect (fixed in the v9.7.395 pool): tools/modeb_card_guard.py interpolated a
15-genus alternation into rf"{GEN} sp\\.? \\((...)-associated" without wrapping it, so the tail
and its capture group bound only to the last genus and the ecology check silently vanished for
the other 14. The gate detects exactly that class: an interpolated constant carrying a top-level
'|' whose parse tree changes when the interpolation is wrapped in (?:...).

The negative cases matter as much as the positives: markdown tables and pipe-delimited data
f-strings (measured: 9 of 10 raw candidates on the live tree) must NOT be flagged, and a
correctly bound `({VAR})` site must stay clean.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tools" / "check_regex_interpolation.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_regex_interpolation_ut", GATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _scan(tmp_path, source):
    m = _load()
    p = tmp_path / "probe.py"
    p.write_text(source)
    return list(m.scan_file(p))


def _run(*args, cwd=ROOT):
    return subprocess.run([sys.executable, str(GATE), *args],
                          capture_output=True, text=True, cwd=str(cwd))


# --- the defect class ------------------------------------------------------------------------

def test_unbound_alternation_in_fstring_is_flagged(tmp_path):
    recs = _scan(tmp_path,
                 'import re\n'
                 'GEN = "Alpha|Beta|Gamma"\n'
                 'PAT = rf"{GEN} sp\\.? \\(([a-z]+)-associated"\n')
    assert len(recs) == 1 and recs[0]["var"] == "GEN", recs


def test_shipped_modeb_card_guard_shape_is_flagged(tmp_path):
    """The exact shape of the fixed 2026-08-31 bug must be caught."""
    recs = _scan(tmp_path,
                 'import re\n'
                 'GEN = ("Streptomyces|Micromonospora|Pseudonocardia|Nocardia|Kribbella|"\n'
                 '       "Nocardiopsis")\n'
                 'for pat in (r"AS-\\d+ is ([a-z\\- ]+?)-associated",\n'
                 '            rf"{GEN} sp\\.? \\(([a-z\\- ]+?)[-\\s]associated"):\n'
                 '    pass\n')
    assert any(r["var"] == "GEN" for r in recs), recs


def test_group_wrapped_interpolation_is_clean(tmp_path):
    recs = _scan(tmp_path,
                 'import re\n'
                 'GEN = "Alpha|Beta|Gamma"\n'
                 'A = rf"\\bAS-\\d+ is a ({GEN})\\b"\n'
                 'B = rf"(?:{GEN}) sp\\.? \\(([a-z]+)-associated"\n')
    assert recs == [], recs


def test_binop_concatenation_is_covered(tmp_path):
    recs = _scan(tmp_path,
                 'import re\n'
                 'TOKS = "cat|dog"\n'
                 'PAT = re.compile("\\\\bsaw a " + TOKS + " today")\n')
    assert len(recs) == 1 and recs[0]["var"] == "TOKS", recs


def test_backslash_free_direct_re_call_is_flagged(tmp_path):
    """No backslash anywhere, but the f-string is a direct re.search argument."""
    recs = _scan(tmp_path,
                 'import re\n'
                 'TOKS = "cat|dog"\n'
                 'm = re.search(f"a {TOKS} here", "text")\n')
    assert len(recs) == 1, recs


# --- the noise classes that must stay silent -------------------------------------------------

def test_markdown_table_fstring_is_not_flagged(tmp_path):
    recs = _scan(tmp_path,
                 'HDR = "| Gene | Hit | Identity |"\n'
                 'DOC = f"## Table\\n\\n{HDR}\\n|---|---|---|\\n"\n')
    assert recs == [], recs


def test_pipe_delimited_data_fstring_is_not_flagged(tmp_path):
    recs = _scan(tmp_path,
                 'q = "AS-901|BGC001|slot=1|role=core"\n'
                 'row = f"{q},WP_1.1,97.9,386"\n')
    assert recs == [], recs


def test_value_without_toplevel_alternation_is_clean(tmp_path):
    recs = _scan(tmp_path,
                 'import re\n'
                 'GRP = "(cat|dog)"\n'
                 'PAT = rf"\\bsaw a {GRP} today\\b"\n')
    assert recs == [], recs


# --- gate mechanics --------------------------------------------------------------------------

def test_missing_root_errors_not_passes(tmp_path):
    r = _run(cwd=tmp_path)
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
    assert "PASS" not in r.stdout


def test_empty_root_refuses_to_pass(tmp_path):
    (tmp_path / "empty").mkdir()
    r = _run("--root", str(tmp_path / "empty"))
    assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)


def test_shipped_tree_passes_and_reports_coverage():
    """Requires the v9.7.395 modeb_card_guard eco-regex fix (same pool) — the one shipped
    instance of this class. With it applied the tree is clean."""
    r = _run()
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "regex-interpolation gate: PASS" in r.stdout
    assert "file(s) scanned" in r.stdout
