"""`run` refuses to write into `<outdir>/<strain>/package` when an earlier run's package is there.

The package folder was created with `exist_ok=True` and written into, so a second run into the
same outdir changed the earlier run's package.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(zip_path, outdir):
    return subprocess.run([sys.executable, "mamey_run.py", "run", "--strain", "SYNOCC",
                           "--input-zip", str(zip_path), "--taxonomy", "Streptomyces sp.",
                           "--mode", "gold", "--capped-session", "--outdir", str(outdir)],
                          cwd=ROOT, capture_output=True, text=True, timeout=900)


def _digest(folder):
    h = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(folder)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


def test_a_second_run_into_the_same_outdir_is_refused(tmp_path, synthetic_single_contig_full_locus_zip):
    outdir = tmp_path / "runs"
    first = _run(synthetic_single_contig_full_locus_zip, outdir)
    assert first.returncode == 0, first.stderr[-800:]
    package = outdir / "SYNOCC" / "package"
    before = _digest(outdir / "SYNOCC")
    second = _run(synthetic_single_contig_full_locus_zip, outdir)
    assert second.returncode == 2
    assert "REFUSED: [outdir]" in second.stderr and str(package) in second.stderr
    assert "--outdir" in second.stderr
    assert _digest(outdir / "SYNOCC") == before


def test_an_empty_package_folder_is_not_occupied(tmp_path):
    from mamey.cli import _refuse_occupied_package
    (tmp_path / "SYNOCC" / "package").mkdir(parents=True)
    assert _refuse_occupied_package(tmp_path, "SYNOCC") is False
    (tmp_path / "SYNOCC" / "package" / "manifest.json").write_text("{}", encoding="utf-8")
    assert _refuse_occupied_package(tmp_path, "SYNOCC") is True
