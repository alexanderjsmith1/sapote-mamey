"""Card attine_452_bgc_class_summary_per_genome: bgc_class_summary.py --per-genome writes the complete class-by-genome
matrix the classes-per-genome figure (B02) reads: explicit zeros, saccharide left out, and only classes found in at
least --min-genomes genomes (default 3; the bee and moss S5 rules). Synthetic IDs only.
"""
import csv
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bgc_class_summary_pg", ROOT / "tools/bgc_class_summary.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
REGIONS = [("AS-971", "r1", "T1PKS;saccharide"), ("AS-971", "r2", "T1PKS"), ("AS-972", "r1", "T1PKS"),
           ("AS-973", "r1", "T1PKS;NRPS"), ("AS-974", "r1", "NRPS"), ("AS-974", "r2", "saccharide")]


def run(tmp_path, *extra, genomes=("AS-971", "AS-972", "AS-973", "AS-974")):
    tmp_path.mkdir(parents=True, exist_ok=True)
    r, g, out = tmp_path / "regions.tsv", tmp_path / "genomes.tsv", tmp_path / "matrix.tsv"
    r.write_text("strain\tregion_file\tproducts\n" + "".join(f"{s}\t{x}\t{p}\n" for s, x, p in REGIONS))
    g.write_text("strain\tgenus\n" + "".join(f"{s}\tSynthetica\n" for s in genomes))
    assert mod.main(["--regions", str(r), "--per-genome", str(g), "--out", str(out), *extra]) == 0
    return {(x["strain"], x["display"]): x for x in csv.DictReader(out.open(), delimiter="\t")}


def test_matrix_has_zeros_and_leaves_out_saccharide_and_rare_classes(tmp_path):
    m = run(tmp_path)
    assert {d for _, d in m} == {"Type I PKS"}                  # NRPS in 2 genomes and saccharide are left out
    assert [m[(s, "Type I PKS")]["count"] for s in ("AS-971", "AS-972", "AS-973", "AS-974")] == ["2", "1", "1", "0"]
    assert m[("AS-971", "Type I PKS")]["family"] == "PKS"


def test_min_genomes_keeps_rarer_classes(tmp_path):
    m = run(tmp_path, "--min-genomes", "2")
    assert {d for _, d in m} == {"Type I PKS", "NRPS"} and m[("AS-971", "NRPS")]["count"] == "0"


def test_genome_table_must_match_the_regions(tmp_path):
    with pytest.raises(ValueError, match="different strains"):
        run(tmp_path, genomes=("AS-971", "AS-972"))
