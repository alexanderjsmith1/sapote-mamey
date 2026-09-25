"""bigscape_prep --drop-contigs: regions on decontaminated-away contigs never reach a BiG-SCAPE run.

On 2026-09-24 the Actinomadura round-2 run staged AS-810's canonical loose zip, which antiSMASH built
on the raw 9,133-contig assembly. 10 of its 76 regions sit on contigs the 2026-08-19 decontamination
removed. The registry said so in free text; staging could not act on it. Hermetic, runs the real tool.
"""
import json
import os
import pathlib
import subprocess
import sys
import zipfile

BUNDLE = pathlib.Path(__file__).resolve().parents[1]
PREP = BUNDLE / "tools" / "bigscape_prep.py"


def _zip(path, records):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(f"{path.stem}.json", '{"strictness": "loose"}')
        for i, rec in enumerate(records, 1):
            z.writestr(f"{rec}.region{i:03d}.gbk", "LOCUS test\n     CDS             1..30\n//\n")


def _run(tmp_path, drop_spec):
    official = tmp_path / "OFFICIAL_DATA"
    official.mkdir(exist_ok=True)
    (official / "exclusions.json").write_text(json.dumps({"hard_excluded": []}))
    indir = tmp_path / "zips"
    indir.mkdir(exist_ok=True)
    _zip(indir / "AS-810.zip", ["NODE_1_length_900000_cov_40.1", "NODE_77_length_4000_cov_3.2", "NODE_78_length_3900_cov_2.9"])
    _zip(indir / "AS-001.zip", ["NODE_77_length_4000_cov_3.2"])
    removed = tmp_path / "removed.tsv"
    removed.write_text("NODE_77_length_4000_cov_3.2\tlow GC\nNODE_78_length_3900_cov_2.9\tlow GC\n")
    out = tmp_path / "out"
    env = dict(os.environ, MAMEY_OFFICIAL_DATA=str(official), MAMEY_DATA_ROOT=str(tmp_path))
    cmd = [sys.executable, str(PREP), "--inputs", str(indir), "--out", str(out), "--strictness", "loose",
           "--drop-contigs", drop_spec.format(tsv=removed)]
    return subprocess.run(cmd, capture_output=True, text=True, env=env), out


def test_listed_contigs_are_dropped_for_that_strain_only(tmp_path):
    r, out = _run(tmp_path, "AS-810={tsv}")
    assert r.returncode == 0, r.stderr
    staged = sorted(p.name for p in out.glob("*.gbk"))
    assert staged == ["AS-001_NODE_77_length_4000_cov_3.2.region001.gbk",
                      "AS-810_NODE_1_length_900000_cov_40.1.region001.gbk"]
    rows = (out / "DROPPED_CONTIG_REGIONS.tsv").read_text().splitlines()
    assert rows[0] == "strain\trecord\tsource_member" and len(rows) == 3
    assert all(r.startswith("AS-810\t") for r in rows[1:])


def test_a_drop_list_for_a_strain_that_did_not_stage_fails(tmp_path):
    r, _ = _run(tmp_path, "AS810={tsv}")
    assert r.returncode == 2
    assert "not staged" in r.stderr
