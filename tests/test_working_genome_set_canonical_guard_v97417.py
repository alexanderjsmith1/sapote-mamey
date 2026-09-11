"""v9.7.417 — `build_working_genome_set` must not silently overwrite its canonical deliverable.

The .413 canonical-overwrite guard reached two of the one-off-batch sibling tools
(`surface_flagged_leads`, `build_modeb_compilation`); .415 added the third
(`whole_bgc_majority_read`). This FOURTH sibling of the same family was still unguarded in the
.416 candidate: it lives in `deliverable_tools/`, its default output is
`$SAPOTE_WORKSPACE_ROOT/sapote_deliverables/WORKING_GENOME_SET_2026-08-03` (matching
`DATED_DIR_RE` exactly), and — unlike the guarded three — it had NO `--out` and NO `--force`,
so a bare "just run it and see" invocation silently rewrote the canonical dated deliverable in
place. That is the exact 2026-09-07 incident `canonical_write_guard` exists to prevent.

Filesystem-safety only: no score, no biology, no claim about any genome or locus. Judgment deferred.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "deliverable_tools" / "build_working_genome_set.py"
OUTDIR = "sapote_deliverables/WORKING_GENOME_SET_2026-08-03"


def _ws(tmp_path):
    """A minimal but real workspace: one per-family genome pool with two distinct .fna files."""
    g = tmp_path / "pools" / "famA" / "genomes"
    g.mkdir(parents=True)
    (g / "AS-999.fna").write_text(">AS-999_c1\nACGTACGTACGTACGT\n", encoding="utf-8")
    (g / "GCF_123.fna").write_text(">GCF_123_c1\nTTTTGGGGCCCCAAAA\n", encoding="utf-8")
    return tmp_path


def _run(ws, *extra):
    env = dict(os.environ, SAPOTE_WORKSPACE_ROOT=str(ws))
    return subprocess.run([sys.executable, str(TOOL), "--input-root", str(ws / "pools"), "--out", str(ws / OUTDIR), *extra],
                          capture_output=True, text=True, cwd=str(ROOT), env=env, timeout=120)


def test_source_imports_and_calls_the_guard():
    s = TOOL.read_text(encoding="utf-8")
    assert "from mamey.canonical_write_guard import" in s
    assert s.count("guard_canonical_write(") >= 1


def test_offers_force_and_out_escape_hatches():
    """A guard the caller cannot release is a one-way door; --force AND a --out redirect must exist."""
    s = TOOL.read_text(encoding="utf-8")
    assert '"--force"' in s and '"--in-place"' in s and '"--out"' in s


def test_fresh_run_creates_then_rerun_is_refused_and_preserves(tmp_path):
    ws = _ws(tmp_path)
    assert _run(ws).returncode == 0
    csv = ws / OUTDIR / "WORKING_GENOME_SET.csv"
    assert csv.is_file()
    csv.write_text("SENTINEL,DELIVERABLE\n", encoding="utf-8")   # stand in for the real deliverable
    r2 = _run(ws)                                                # rerun WITHOUT --force
    assert r2.returncode != 0, "unguarded: a silent in-place overwrite exits 0"
    assert "refusing to overwrite" in (r2.stderr + r2.stdout).lower()
    assert csv.read_text(encoding="utf-8") == "SENTINEL,DELIVERABLE\n"   # the guard never writes


def test_force_still_regenerates(tmp_path):
    ws = _ws(tmp_path)
    assert _run(ws).returncode == 0
    csv = ws / OUTDIR / "WORKING_GENOME_SET.csv"
    csv.write_text("SENTINEL\n", encoding="utf-8")
    assert _run(ws, "--force").returncode == 0                   # the escape hatch still works
    assert csv.read_text(encoding="utf-8") != "SENTINEL\n"       # deliberately regenerated


def test_out_redirect_leaves_canonical_untouched(tmp_path):
    ws = _ws(tmp_path)
    assert _run(ws).returncode == 0
    csv = ws / OUTDIR / "WORKING_GENOME_SET.csv"
    csv.write_text("SENTINEL\n", encoding="utf-8")
    alt = tmp_path / "alt_out"
    assert _run(ws, "--out", str(alt)).returncode == 0           # redirect instead of overwrite
    assert (alt / "WORKING_GENOME_SET.csv").is_file()
    assert csv.read_text(encoding="utf-8") == "SENTINEL\n"       # canonical deliverable untouched
