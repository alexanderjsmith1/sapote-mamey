"""The decontam guard reads a removed-contig list whose ids start with "contig".

In 442a the guard's plain-list fallback skipped every row whose first cell started with "contig",
meaning to skip a header. A list of contig_N ids therefore read as empty, and the guard reported
"0 of N staged regions on removed contigs" and exited 0 with a removed contig staged: it failed open.
Only an exact header cell (contig, record, record_id) is a header. Generic ids, real tool.
"""
import pathlib
import subprocess
import sys

BUNDLE = pathlib.Path(__file__).resolve().parents[1]
GUARD = BUNDLE / "tools" / "bigscape_input_decontam_guard.py"


def _run(tmp_path, listing):
    regions = tmp_path / "regions"
    regions.mkdir()
    for contig in ("contig_7", "contig_3"):
        (regions / f"GEN-1_{contig}.region001.gbk").write_text("LOCUS x\n//\n")
    removed = tmp_path / "removed.tsv"
    removed.write_text(listing)
    return subprocess.run([sys.executable, str(GUARD), "--regions", str(regions), "--removed", f"GEN-1={removed}"],
                          capture_output=True, text=True, cwd=BUNDLE)


def test_headerless_contig_named_list_is_read(tmp_path):
    r = _run(tmp_path, "contig_7\tlow GC\ncontig_12\tlow GC\n")
    assert r.returncode == 4, r.stdout + r.stderr
    assert "CONTAMINANT_REGION_STAGED\tGEN-1\tGEN-1_contig_7.region001.gbk" in r.stdout
    assert "GEN-1: 1 of 2 staged regions on removed contigs" in r.stdout


def test_contig_named_list_with_a_header_row_is_read(tmp_path):
    r = _run(tmp_path, "contig\treason\ncontig_7\tlow GC\n")
    assert r.returncode == 4, r.stdout + r.stderr
    assert "GEN-1: 1 of 2 staged regions on removed contigs" in r.stdout
