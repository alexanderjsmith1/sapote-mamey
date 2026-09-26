"""One removed-contig reader for the three tools that take a decontamination list.

The bundle's own decontamination tool, deliverable_tools/clade_decontam.py, writes
<clade>_contig_bins.tsv: EVERY contig, with a keep column. The decontam guard read keep == 0, but
bigscape_prep --drop-contigs and region_table_one_setting --drop-contigs read the first column of
every row. Given that file they dropped every region of the strain, kept contigs included, and
exited 0 because the drop list matched. Hermetic: real producer, real tools, generic IDs.
"""
import json
import os
import pathlib
import subprocess
import sys
import zipfile

import pytest

BUNDLE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUNDLE / "deliverable_tools"))
sys.path.insert(0, str(BUNDLE / "tools"))

import clade_decontam  # noqa: E402
import bigscape_input_decontam_guard as guard  # noqa: E402

KEEP = "NODE_1_length_900000_cov_40.1"
GONE = ["NODE_77_length_4000_cov_3.2", "NODE_78_length_3900_cov_2.9"]
GBK = "LOCUS test\n     CDS             1..30\n//\n"


def _bins(tmp_path):
    rows = [dict(contig=KEEP, len=900000, gc=70.1, cov=40.1, target_bit=900.0, contam_bit=0.0,
                 assignment="target", keep=True, seq="G")]
    rows += [dict(contig=c, len=4000, gc=51.0, cov=3.2, target_bit=0.0, contam_bit=800.0,
                  assignment="contaminant", keep=False, seq="A") for c in GONE]
    return pathlib.Path(clade_decontam.write_outputs(rows, str(tmp_path / "decontam"), clade="GEN-1")["bins_tsv"])


def _cohort(tmp_path):
    official = tmp_path / "OFFICIAL_DATA"
    official.mkdir(exist_ok=True)
    (official / "exclusions.json").write_text(json.dumps({"hard_excluded": []}))
    zdir = tmp_path / "zips"
    zdir.mkdir(exist_ok=True)
    with zipfile.ZipFile(zdir / "GEN-1.zip", "w") as z:
        z.writestr("GEN-1.json", '{"strictness": "loose"}')
        for i, rec in enumerate([KEEP, *GONE], 1):
            z.writestr(f"{rec}.region{i:03d}.gbk", GBK)
    with zipfile.ZipFile(zdir / "GEN-2.zip", "w") as z:
        z.writestr("GEN-2.json", '{"strictness": "loose"}')
        z.writestr("NODE_5_length_50000_cov_20.0.region001.gbk", GBK)
    env = dict(os.environ, MAMEY_OFFICIAL_DATA=str(official), MAMEY_DATA_ROOT=str(tmp_path))
    return zdir, env


def _tool(name, args, env):
    return subprocess.run([sys.executable, str(BUNDLE / "tools" / name), *args],
                          capture_output=True, text=True, env=env, cwd=BUNDLE)


def test_contig_bins_yields_only_the_removed_contigs(tmp_path):
    assert guard.removed_contig_ids(_bins(tmp_path)) == set(GONE)


@pytest.mark.parametrize("bad_keep", ["", "NA", "no", "2"])
def test_bin_table_rejects_unknown_keep_values(tmp_path, bad_keep):
    bins = _bins(tmp_path)
    text = bins.read_text().replace(f"{GONE[0]}\t4000\t51.0\t3.20\t0\t800\tcontaminant\t0",
                                    f"{GONE[0]}\t4000\t51.0\t3.20\t0\t800\tcontaminant\t{bad_keep}")
    assert text != bins.read_text()
    bins.write_text(text)
    with pytest.raises(ValueError, match="invalid keep value"):
        guard.removed_contig_ids(bins)


def test_bin_table_rejects_blank_contig_id(tmp_path):
    bins = _bins(tmp_path)
    bins.write_text(bins.read_text() + "\t4000\t51.0\t3.20\t0\t800\tcontaminant\t0\n")
    with pytest.raises(ValueError, match="needs a contig"):
        guard.removed_contig_ids(bins)


def test_bigscape_prep_keeps_regions_on_kept_contigs(tmp_path):
    zdir, env = _cohort(tmp_path)
    out = tmp_path / "staged"
    r = _tool("bigscape_prep.py", ["--inputs", str(zdir), "--out", str(out), "--strictness", "loose",
                                   "--drop-contigs", f"GEN-1={_bins(tmp_path)}"], env)
    assert r.returncode == 0, r.stderr
    staged = sorted(p.name for p in out.glob("GEN-1_*.gbk"))
    assert staged == [f"GEN-1_{KEEP}.region001.gbk"]
    assert "dropped 2 region(s) on 2 listed contig(s)" in r.stderr


def test_region_table_keeps_regions_on_kept_contigs(tmp_path):
    zdir, env = _cohort(tmp_path)
    table = tmp_path / "regions.tsv"
    r = _tool("region_table_one_setting.py", ["--zips", str(zdir), "--strictness", "loose", "--out", str(table),
                                              "--drop-contigs", f"GEN-1={_bins(tmp_path)}"], env)
    assert r.returncode == 0, r.stderr
    gen1 = [ln.split("\t")[2] for ln in table.read_text().splitlines()[1:] if ln.startswith("GEN-1\t")]
    assert gen1 == [KEEP]


def test_guard_and_stager_agree_on_one_file(tmp_path):
    zdir, env = _cohort(tmp_path)
    bins = _bins(tmp_path)
    out = tmp_path / "staged"
    _tool("bigscape_prep.py", ["--inputs", str(zdir), "--out", str(out), "--strictness", "loose",
                               "--drop-contigs", f"GEN-1={bins}"], env)
    for i, rec in enumerate([KEEP, *GONE], 1):  # stage the raw set too, so the guard has something to flag
        (tmp_path / "raw").mkdir(exist_ok=True)
        (tmp_path / "raw" / f"GEN-1_{rec}.region{i:03d}.gbk").write_text(GBK)
    raw = _tool("bigscape_input_decontam_guard.py", ["--regions", str(tmp_path / "raw"), "--removed", f"GEN-1={bins}"], env)
    clean = _tool("bigscape_input_decontam_guard.py", ["--regions", str(out), "--removed", f"GEN-1={bins}"], env)
    assert raw.returncode == 4 and "GEN-1: 2 of 3 staged regions on removed contigs" in raw.stdout
    assert clean.returncode == 0 and "GEN-1: 0 of 1 staged regions on removed contigs" in clean.stdout


@pytest.mark.parametrize("tool", ["bigscape_prep.py", "region_table_one_setting.py", "bigscape_input_decontam_guard.py"])
def test_bin_table_without_keep_column_is_refused(tmp_path, tool):
    zdir, env = _cohort(tmp_path)
    legacy = tmp_path / "legacy_bins.tsv"
    legacy.write_text(f"contig\tlength\tgc\tassignment\n{KEEP}\t900000\t70.1\ttarget\n{GONE[0]}\t4000\t51.0\tcontaminant\n")
    args = {"bigscape_prep.py": ["--inputs", str(zdir), "--out", str(tmp_path / "o"), "--strictness", "loose",
                                 "--drop-contigs", f"GEN-1={legacy}"],
            "region_table_one_setting.py": ["--zips", str(zdir), "--strictness", "loose",
                                            "--out", str(tmp_path / "t.tsv"), "--drop-contigs", f"GEN-1={legacy}"],
            "bigscape_input_decontam_guard.py": ["--regions", str(tmp_path), "--removed", f"GEN-1={legacy}"]}[tool]
    (tmp_path / "GEN-1_x.region001.gbk").write_text(GBK)
    r = _tool(tool, args, env)
    assert r.returncode == 2
    assert "without a keep column" in r.stderr


def test_plain_lists_read_as_before(tmp_path):
    headerless = tmp_path / "a.tsv"
    headerless.write_text(f"{GONE[0]}\tlow GC\n{GONE[1]}\tlow GC\n")
    with_header = tmp_path / "b.tsv"
    with_header.write_text(f"contig\tremoved_reason\n# comment\n{GONE[0]}\tx\n{GONE[1]}\tx\n")
    assert guard.removed_contig_ids(headerless) == guard.removed_contig_ids(with_header) == set(GONE)
    only_header = tmp_path / "c.tsv"
    only_header.write_text("contig\treason\n")
    assert guard.removed_contig_ids(only_header) == set()
