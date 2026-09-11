"""Behavior test for comparator_discovery.py (BB09). Proves: it parses antiSMASH ClusterBlast
'Significant hits' into ranked comparator genomes + genus rollup, and distinguishes named vs sp.
Self-contained: builds a tiny fake antismash dir. (stdlib + subprocess)"""
import subprocess, sys, pathlib, csv

def _find_root(name):
    # v9.7.356 seal fix: resolve the BUNDLE layout ("tools/") as well as the authoring
    # workspace ("Tools/"). The folded tests hardcoded "Tools/", which exists only in the
    # author's tree, so collection ERRORed in the shipped bundle and for every other user.
    for p in pathlib.Path(__file__).resolve().parents:
        for d in ("tools", "Tools"):
            if (p / d / name).exists():
                return p, d
    raise RuntimeError(f"tools/{name} not found above test")
ROOT, _TOOLDIR = _find_root("comparator_discovery.py")
TOOL = ROOT / _TOOLDIR / "comparator_discovery.py"
PY = ROOT / "Tools" / "bin" / "python3"
PY = str(PY) if PY.exists() else sys.executable

CB = """ClusterBlast scores for c00001

Table of genes...

Significant hits:
1.\tNZ_CP111111\tStreptomyces armeniacus strain ATCC 15676 chromosome, complete genome
2.\tNZ_CP222222\tStreptomyces sp. XYZ chromosome, complete genome
3.\tNZ_CP333333\tSaccharothrix espanaensis strain DSM chromosome

Details:
>>
1.\tNZ_CP111111
Source: Streptomyces armeniacus strain ATCC 15676
"""


def test_parses_and_ranks_comparators(tmp_path):
    az = tmp_path / "antismash" / "clusterblast"; az.mkdir(parents=True)
    (az / "NODE_1_region001_c1.txt").write_text(CB)
    # a second region hitting the same top genome -> higher region support
    az2 = tmp_path / "antismash" / "clusterblast" / "NODE_2_region001_c1.txt"
    az2.write_text(CB.replace("c00001", "c00002"))
    out = tmp_path / "out"
    r = subprocess.run([PY, str(TOOL), "--dir", str(tmp_path / "antismash"),
                        "--strain", "AS-TEST", "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    rows = list(csv.DictReader(open(out / "AS-TEST_comparators.tsv"), delimiter="\t"))
    accs = {row["accession"] for row in rows}
    assert {"NZ_CP111111", "NZ_CP222222", "NZ_CP333333"} <= accs
    top = rows[0]  # ranked by region support: NZ_CP111111 hit by 2 regions
    assert top["accession"] == "NZ_CP111111" and int(top["n_regions"]) == 2
    # named vs sp. distinction
    named = {row["accession"]: row["named"] for row in rows}
    assert named["NZ_CP111111"] == "yes" and named["NZ_CP222222"] == "no"
    # genus rollup + fetch script emitted
    assert (out / "AS-TEST_comparator_genera.tsv").exists()
    assert (out / "fetch_AS-TEST_comparators.sh").exists()
