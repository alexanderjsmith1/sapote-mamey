"""tools/gene_synteny_map.py: a genome against a reference cluster, gene by gene, with ordered blocks.

2026-09-28: the per-gene view (a candidate match for each reference gene, identity and coverage, neighbouring
genes matched in order on one contig) is the convincing one; build it into this cut. Modular PKS genes are assigned by
KS placement when a placement table is given, because their best whole-gene match follows module paralogy.
"""
import csv
import importlib.util
import json
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("Bio")
pytest.importorskip("matplotlib")

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gene_synteny_map", ROOT / "tools/gene_synteny_map.py")
gsm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gsm)


def _gbk(name, genes, definition="test organism strain X"):
    """genes: [(locus_tag, gene, product, aa, is_pks)]; one region, each CDS 900 bp, PKS genes carry a KS aSDomain."""
    length = 1000 * (len(genes) + 1)
    lines = [f"LOCUS       {name:<16}{length:>12} bp    DNA     linear   UNK 01-JAN-1980",
             f"DEFINITION  {definition} {name}, whole genome shotgun sequence.", f"ACCESSION   {name}",
             f"VERSION     {name}", "FEATURES             Location/Qualifiers",
             f"     region          1..{length}", '                     /contig_edge="True"',
             '                     /product="T1PKS"']
    for i, (tag, gene, product, aa, pks) in enumerate(genes):
        lines += [f"     CDS             {i * 1000 + 1}..{i * 1000 + 900}", f'                     /locus_tag="{tag}"',
                  f'                     /gene="{gene}"', f'                     /product="{product}"',
                  f'                     /translation="{aa}"']
        if pks:
            lines += [f"     aSDomain        {i * 1000 + 31}..{i * 1000 + 600}", '                     /aSDomain="PKS_KS"',
                      f'                     /locus_tag="{tag}"', f'                     /domain_id="{tag}_ks"',
                      f'                     /translation="{aa[:100]}"']
    lines.append("ORIGIN")
    for start in range(0, length, 60):
        chunk = "a" * min(60, length - start)
        lines.append(f"{start + 1:>9} " + " ".join(chunk[j:j + 10] for j in range(0, len(chunk), 10)))
    return "\n".join(lines + ["//"]) + "\n"


AA = "M" + "ACDEFGHIKLMNPQRSTVWY" * 15
REF = [("r1", "tA", "tailoring enzyme", AA, False), ("r2", "tB", "ABC transporter", AA, False),
       ("r3", "tC", "tailoring enzyme", AA, False), ("r4", "pks1", "polyketide synthase", AA, True),
       ("r5", "pks2", "polyketide synthase", AA, True), ("r6", "reg", "transcriptional regulator", AA, False)]


def _setup(tmp_path):
    ref = tmp_path / "BGC0000999.gbk"
    ref.write_text(_gbk("REF1", REF))
    z = tmp_path / "genome.zip"
    with zipfile.ZipFile(z, "w") as zf:
        # contig 1 carries matches to tA, tB, tC in order; contig 2 a PKS fragment; contig 3 a bigger multi-module PKS
        zf.writestr("ctg1.region001.gbk", _gbk("ctg1", [("q1", "", "enzyme", AA, False), ("q2", "", "transporter", AA, False),
                                                        ("q3", "", "enzyme", AA, False)]))
        zf.writestr("ctg2.region001.gbk", _gbk("ctg2", [("q4", "", "PKS", AA, True)]))
        zf.writestr("ctg3.region001.gbk", _gbk("ctg3", [("q5", "", "PKS", AA, True), ("q6", "", "PKS", AA, True)]))
    return ref, z


def _hits(tmp_path, prots, rows):
    """rows: [(locus_tag, ref gene id, identity, bitscore)] -> a tabular file in the tool's column order."""
    by_tag = {v["locus"]: k for k, v in prots.items()}
    path = tmp_path / "hits.tsv"
    with open(path, "w") as fh:
        for tag, g, pid, bits in rows:
            fh.write("\t".join(map(str, [by_tag[tag], g, pid, 200, 201, 201, 100, 100, 1e-50, bits, 1, 200, 1, 200])) + "\n")
    return path


def _run(tmp_path, placement=None):
    ref, z = _setup(tmp_path)
    prots, _ = gsm.load_genome(z, "T")
    # contig 3 (two PKS modules) outscores contig 2 on pks1 by whole-gene best hit; KS placement says pks1 is contig 2
    hits = _hits(tmp_path, prots, [("q1", "g001", 82, 300), ("q2", "g002", 75, 280), ("q3", "g003", 90, 320),
                                   ("q4", "g004", 70, 250), ("q5", "g004", 72, 400), ("q6", "g005", 88, 390)])
    out = tmp_path / "out"
    argv = ["--zip", str(z), "--label", "T", "--reference", str(ref), "--reference-name", "ref cluster", "--out",
            str(out), "--hits", str(hits)]
    if placement:
        argv += ["--placement", str(placement)]
    assert gsm.main(argv) == 0
    rows = {r["name"]: r for r in csv.DictReader(open(out / "gene_synteny.tsv"), delimiter="\t")}
    return rows, json.loads((out / "gene_synteny_receipt.json").read_text()), out


def test_genes_blocks_and_outputs(tmp_path):
    rows, receipt, out = _run(tmp_path)
    assert (out / "gene_synteny.png").stat().st_size > 10_000
    assert receipt["genes_matched"] == 5 and receipt["reference_genes"] == 6
    assert receipt["blocks"][0] == ["tA", "tB", "tC"]
    assert rows["reg"]["best_identity_pct"] == ""
    assert rows["tA"]["region_identity"] == "T / ctg1 / region001 / BGC001"
    assert rows["tA"]["assigned_by"] == "best whole-gene match"


def test_pks_genes_without_placement_are_flagged(tmp_path):
    rows, receipt, _ = _run(tmp_path)
    assert rows["pks1"]["assigned_by"].startswith("best match; paralogous modules")
    assert "ctg3" in rows["pks1"]["region_identity"]   # the multi-module contig wins the whole-gene comparison
    assert receipt["pks_genes_by_placement"] == 0


def test_ks_placement_assigns_pks_genes_to_the_placed_contig(tmp_path):
    placement = tmp_path / "placement.tsv"
    placement.write_text("query\tverdict\treference\tmodule\n"
                         "T__NODE_2__region001__q4__q4_ks\tPLACED_ON_REFERENCE_MODULE\tBGC0000999\t1\n"
                         "T__NODE_3__region001__q6__q6_ks\tPLACED_ON_REFERENCE_MODULE\tBGC0000999\t2\n")
    rows, receipt, _ = _run(tmp_path, placement)
    assert rows["pks1"]["assigned_by"] == "KS placement" and "ctg2" in rows["pks1"]["region_identity"]
    assert rows["pks1"]["best_identity_pct"] == "70.0"
    assert rows["pks2"]["assigned_by"] == "KS placement" and "ctg3" in rows["pks2"]["region_identity"]
    assert receipt["pks_genes_by_placement"] == 2


def test_refuses_to_write_inside_the_bundle(tmp_path):
    ref, z = _setup(tmp_path)
    with pytest.raises(Exception):
        gsm.main(["--zip", str(z), "--label", "T", "--reference", str(ref), "--reference-name", "r", "--out",
                  str(ROOT / "tmp_gene_synteny_out"), "--hits", str(tmp_path / "none.tsv")])
    assert not (ROOT / "tmp_gene_synteny_out").exists()
