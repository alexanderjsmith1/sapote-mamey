"""Bug #1: verify_blastp.py — the BLASTp verify gate that SKILL.md / references/blastp.md
mandate but that was missing from the release. Exits nonzero on HTML_STUB / EMPTY / MISSING /
PARTIAL; exit 0 on real hit rows.
"""
import subprocess, sys, pathlib

_root = pathlib.Path(__file__).resolve().parents[1]
_script = _root / "scripts" / "verify_blastp.py"

# a minimal real -outfmt 10 / pipe-query HitTable (2 genes, real subject accessions)
_REAL = (
    "AS-1|BGC001|ctg1_10,WP_000000001.1,93.7,352,22,0,1,352,1,352,0.0,667,95.4\n"
    "AS-1|BGC001|ctg1_10,WP_000000002.1,90.1,350,31,0,1,350,1,350,0.0,640,94.0\n"
    "AS-1|BGC002|ctg2_5,WP_000000003.1,88.0,300,30,1,1,300,1,299,0.0,560,92.0\n"
)


def _run(*args):
    return subprocess.run([sys.executable, str(_script), *args],
                          capture_output=True, text=True).returncode


def test_real_hittable_passes(tmp_path):
    p = tmp_path / "ht.csv"; p.write_text(_REAL)
    assert _run("--hit-table", str(p)) == 0


def test_html_stub_fails(tmp_path):
    p = tmp_path / "stub.csv"; p.write_text("<html><body>QBlastInfo error</body></html>")
    assert _run("--hit-table", str(p)) == 1


def test_empty_fails(tmp_path):
    p = tmp_path / "empty.csv"; p.write_text("")
    assert _run("--hit-table", str(p)) == 1


def test_missing_file_fails(tmp_path):
    assert _run("--hit-table", str(tmp_path / "nope.csv")) == 1


def test_partial_coverage_fails(tmp_path):
    p = tmp_path / "ht.csv"; p.write_text(_REAL)
    # expect a gene that isn't in the table -> PARTIAL
    assert _run("--hit-table", str(p), "--expect", "ctg1_10,ctg2_5,ctg9_999") == 1


def test_full_coverage_passes(tmp_path):
    p = tmp_path / "ht.csv"; p.write_text(_REAL)
    assert _run("--hit-table", str(p), "--expect", "ctg1_10,ctg2_5") == 0
