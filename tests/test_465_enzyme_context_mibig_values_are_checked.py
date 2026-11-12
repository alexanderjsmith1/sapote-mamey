"""enzyme_family_context: a MIBiG row with a nonfinite score or identity, or an identity outside 0-100, is held and
counted; a hit whose strain/BGC/locus key sits on more than one contig or region is held."""
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cohort_enzyme_catalog as cec  # noqa: E402
import enzyme_family_context as efc  # noqa: E402
from test_465_enzyme_family_context import KS, cds, make  # noqa: E402


def hits(cat):
    return list(csv.DictReader(open(cat / "GENE_MIBIG_BEST.tsv"), delimiter="\t"))


@pytest.mark.parametrize("pid,score", [("nan", "300"), ("inf", "300"), ("150", "300"), ("-1", "300"),
                                       ("70", "nan"), ("70", "inf"), ("70", "-inf")])
def test_nonfinite_or_out_of_range_rows_are_held_and_counted(tmp_path, pid, score):
    root = tmp_path / "ws"
    root.mkdir()
    g = make(root, "N-1", {"BGC001": [cds("n1", KS, ["PKS_KS"])]}, {"BGC001": "T1PKS"},
             mibig_rows=[["N-1", "n1", "BGC0000001", "bad row", pid, "90", score],
                         ["N-1", "n1", "BGC0000002", "good row", "60", "90", "100"]])
    gt = root / "genomes.tsv"
    gt.write_text(f"strain\tgene_context\nN-1\t{g}\n")
    cec.build(gt, root, root / "cat")
    info = efc.build(root / "cat", gt, root)
    assert [h["mibig_accession"] for h in hits(root / "cat")] == ["BGC0000002"]
    assert info["mibig_input_gaps"] == {"N-1": {"rows_with_nonfinite_or_out_of_range_score": 1}}


def test_a_hit_whose_key_sits_on_two_regions_is_held(tmp_path):
    root = tmp_path / "ws"
    root.mkdir()
    g = make(root, "M-1", {"BGC001": [cds("m1", KS, ["PKS_KS"])]}, {"BGC001": "T1PKS"},
             mibig_rows=[["M-1", "m1", "BGC0000001", "c", "70", "90", "300"]])
    gt = root / "genomes.tsv"
    gt.write_text(f"strain\tgene_context\nM-1\t{g}\n")
    cat = root / "cat"
    cec.build(gt, root, cat)
    # a second catalog row with the same strain / BGC alias / locus tag on another contig: the MIBiG row cannot tell
    # which one it belongs to
    lines = (cat / "ENZYME_GENES.tsv").read_text().splitlines()
    lines.append(lines[1].replace("NODE_1 / region001", "NODE_9 / region004"))
    (cat / "ENZYME_GENES.tsv").write_text("\n".join(lines) + "\n")
    info = efc.build(cat, gt, root)
    assert hits(cat) == [] and info["mibig_input_gaps"] == {"M-1": {"hits_held_key_on_several_regions": 1}}
