"""tools/gap_directed_rescue.py split-gene check: one reference gene in two pieces at facing contig ends.

Alex, 2026-09-30: "Can we simply have another 'check' that addresses this blind spot". The gene table keeps one best
genome protein per reference gene and needs 50% coverage, so the second piece of a gene broken by the assembly read as
"no match". The check reads every hit again and reports the two pieces; it changes no status or partner.
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
spec = importlib.util.spec_from_file_location("gap_directed_rescue_split", ROOT / "tools/gap_directed_rescue.py")
gdr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gdr)

AA = "M" + "ACDEFGHIKLMNPQRSTVWY" * 15  # 301 aa


def _record(name, genes, length, region=None):
    """genes: [(locus_tag, start, strand)], each 900 bp; region: (start, end, n, contig_edge)."""
    lines = [f"LOCUS       {name:<16}{length:>12} bp    DNA     linear   UNK 01-JAN-1980",
             f"DEFINITION  test organism {name}, whole genome shotgun sequence.", f"ACCESSION   {name}",
             f"VERSION     {name}", "FEATURES             Location/Qualifiers"]
    if region:
        s, e, n, edge = region
        lines += [f"     region          {s + 1}..{e}", f'                     /region_number="{n}"',
                  f'                     /contig_edge="{edge}"', '                     /product="saccharide"']
    for tag, s, strand, *doms in genes:
        loc = f"{s + 1}..{s + 900}" if strand > 0 else f"complement({s + 1}..{s + 900})"
        lines += [f"     CDS             {loc}", f'                     /locus_tag="{tag}"',
                  '                     /product="enzyme"']
        lines += [f'                     /sec_met_domain="{d} (E-value: 1e-50, bitscore: 200.0, seeds: 10, '
                  f'tool: rule-based-clusters)"' for d in (doms[0] if doms else [])]
        lines += [f'                     /translation="{AA}"']
    lines.append("ORIGIN")
    for start in range(0, length, 60):
        chunk = "a" * min(60, length - start)
        lines.append(f"{start + 1:>9} " + " ".join(chunk[j:j + 10] for j in range(0, len(chunk), 10)))
    return "\n".join(lines + ["//"]) + "\n"


def _reference(tmp_path, domains=None):
    """domains: {gene number: [aSDomain names]} placed inside that reference gene."""
    lines = ["LOCUS       REF1                    7000 bp    DNA     linear   UNK 01-JAN-1980",
             "DEFINITION  reference cluster.", "ACCESSION   REF1", "VERSION     REF1",
             "FEATURES             Location/Qualifiers"]
    for i in range(6):
        lines += [f"     CDS             {i * 1000 + 1}..{i * 1000 + 900}", f'                     /gene="r{i + 1}"',
                  '                     /product="enzyme"', '                     /gene_kind="biosynthetic-additional"',
                  f'                     /translation="{AA}"']
        for k, d in enumerate((domains or {}).get(i + 1, [])):
            lines += [f"     aSDomain        {i * 1000 + 31 + k * 300}..{i * 1000 + 300 + k * 300}",
                      f'                     /aSDomain="{d}"']
    lines.append("ORIGIN")
    for start in range(0, 7000, 60):
        lines.append(f"{start + 1:>9} " + " ".join("a" * 10 for _ in range(min(6, (7000 - start) // 10))))
    p = tmp_path / "BGC0000999.gbk"
    p.write_text("\n".join(lines + ["//"]) + "\n")
    return p


def _genome(tmp_path, core_genes=(("a1", 1000, 1), ("a2", 2000, 1), ("a3", 3000, 1)), b1_domains=()):
    # ctgA (4 kb): the core region, running to the contig end; a3 ends 100 bp from it.
    # ctgB (8 kb, no region): b1 starts at the contig start; b2 and b3 lie inside.
    # ctgC (200 kb): c1 far from both ends.
    core = _record("ctgA", list(core_genes), 4000, region=(0, 4000, 1, "True"))
    genome = (core + _record("ctgB", [("b1", 0, 1, list(b1_domains)), ("b2", 2000, 1), ("b3", 3000, 1)], 8000)
              + _record("ctgC", [("c1", 50000, 1)], 200000))
    z = tmp_path / "genome.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("genome.gbk", genome)
        zf.writestr("ctgA.region001.gbk", core)
    return z


# protein ids follow record then CDS order: q000001-3 ctgA, q000004 b1, q000005 b2, q000006 b3, q000007 c1
BASE = [("g001", "q000001", 80, 99, 500, 1, 301), ("g002", "q000002", 75, 99, 480, 1, 301),
        ("g004", "q000005", 72, 99, 460, 1, 301), ("g005", "q000006", 65, 97, 420, 1, 301)]


def _run(tmp_path, rows, core_genes=None, figure=False, domains=None, b1_domains=()):
    z = (_genome(tmp_path, core_genes, b1_domains=b1_domains) if core_genes
         else _genome(tmp_path, b1_domains=b1_domains))
    hits = tmp_path / "hits.tsv"
    hits.write_text("".join("\t".join(map(str, r)) + "\n" for r in rows))
    out = tmp_path / "out"
    args = ["--zip", str(z), "--label", "T", "--core", "ctgA.region001", "--reference", str(_reference(tmp_path, domains)),
            "--out", str(out), "--hits", str(hits)]
    assert gdr.main(args + ([] if figure else ["--no-figure"])) == 0
    table = {r["name"]: r for r in csv.DictReader(open(out / "gap_rescue.tsv"), delimiter="\t")}
    splits = list(csv.DictReader(open(out / "gap_rescue_split_genes.tsv"), delimiter="\t"))
    return table, splits, json.loads((out / "gap_rescue_receipt.json").read_text()), out


def test_a_gene_broken_at_two_contig_ends_is_reported_split_and_the_gene_table_is_unchanged(tmp_path):
    rows = BASE + [("g003", "q000003", 60, 50, 200, 1, 150), ("g003", "q000004", 55, 48, 180, 156, 301)]
    table, splits, receipt, out = _run(tmp_path, rows, figure=True)
    (s,) = splits
    assert s["name"] == "r3" and s["status"] == "SPLIT_ACROSS_CONTIG_ENDS" and s["split_call"] == "CLEAR"
    assert (s["piece1_locus"], s["piece2_locus"]) == ("a3", "b1")
    assert (s["piece1_reference_range"], s["piece2_reference_range"]) == ("1-150", "156-301")
    assert s["piece1_region_identity"].startswith("T / ctgA / region001")
    assert s["piece2_region_identity"] == "T / ctgB (no antiSMASH region)"
    assert int(s["piece1_open_end_to_contig_end_bp"]) == 100 and int(s["piece2_open_end_to_contig_end_bp"]) == 0
    assert s["overlap_aa"] == "0" and s["reference_union_pct"] == "98"
    # the gene table and partners are exactly what they were: r3 stays "in core", b1 is not a find
    assert table["r3"]["status"] == "PRESENT_IN_CORE" and table["r3"]["best_locus"] == "a3"
    assert [p["partner_contig"] for p in receipt["partners"]] == ["ctgB"] and receipt["partners"][0]["clear_finds"] == 2
    assert receipt["split_gene_check"] == "run" and receipt["split_genes"][0]["piece2_locus"] == "b1"
    assert (out / "gap_rescue.png").stat().st_size > 10_000


def test_a_piece_far_from_a_contig_end_is_not_a_split(tmp_path):
    rows = BASE[:2] + [("g003", "q000003", 60, 50, 200, 1, 150), ("g003", "q000005", 55, 48, 180, 156, 301)]
    _, splits, receipt, _ = _run(tmp_path, rows)
    assert splits == [] and receipt["split_gene_check"] == "run"


def test_pieces_whose_open_ends_face_inward_are_not_a_split(tmp_path):
    """a3 holds the reference's end and b1 its start: each piece's open end points into its contig."""
    rows = BASE + [("g003", "q000003", 60, 48, 200, 156, 301), ("g003", "q000004", 55, 50, 180, 1, 150)]
    _, splits, _, _ = _run(tmp_path, rows)
    assert splits == []


def test_two_pieces_covering_the_same_stretch_are_paralogs_not_a_split(tmp_path):
    rows = BASE + [("g003", "q000003", 60, 50, 200, 1, 150), ("g003", "q000004", 55, 67, 180, 100, 301)]
    _, splits, _, _ = _run(tmp_path, rows)
    assert splits == []


def test_a_minus_strand_piece_at_a_contig_start_counts_by_its_c_terminal_end(tmp_path):
    """The core's first gene runs off the contig start on the minus strand, so its C-terminal end is the open one."""
    core_genes = (("a0", 0, -1), ("a1", 1000, 1), ("a2", 2000, 1))
    rows = [("g001", "q000002", 80, 99, 500, 1, 301), ("g002", "q000003", 75, 99, 480, 1, 301),
            ("g003", "q000001", 58, 66, 220, 13, 211), ("g003", "q000004", 52, 42, 120, 217, 342 - 41)]
    _, splits, _, _ = _run(tmp_path, rows, core_genes=core_genes)
    (s,) = splits
    assert (s["piece1_locus"], s["piece2_locus"]) == ("a0", "b1")
    assert int(s["piece1_open_end_to_contig_end_bp"]) == 0


@pytest.mark.parametrize("rival_pct, call", [(62, "RIVAL_STRONGER"), (50, "WEAK"), (40, "CLEAR")])
def test_a_whole_gene_match_elsewhere_decides_how_clear_the_split_is(tmp_path, rival_pct, call):
    """Pieces at 60% and 55%: a whole-gene match at least as close means paralog fragments; within 10 points is weak."""
    rows = BASE + [("g003", "q000003", 60, 50, 200, 1, 150), ("g003", "q000004", 55, 48, 180, 156, 301),
                   ("g003", "q000007", rival_pct, 95, 150, 1, 290)]
    _, splits, _, _ = _run(tmp_path, rows)
    (s,) = splits
    assert s["split_call"] == call and s["whole_gene_rival_locus"] == "c1"


def test_an_assembly_line_reference_gene_is_reported_but_left_unresolved(tmp_path):
    """A condensation or KS domain: module paralogy can fake two complementary pieces."""
    rows = BASE + [("g003", "q000003", 60, 50, 200, 1, 150), ("g003", "q000004", 55, 48, 180, 156, 301)]
    _, splits, _, _ = _run(tmp_path, rows, domains={3: ["Condensation_LCL", "AMP-binding"]})
    (s,) = splits
    assert s["split_call"] == "MODULAR_UNRESOLVED" and s["modular_reference_gene"] == "True"
    # a lone adenylation domain (a standalone adenylating enzyme) is not an assembly line
    (tmp_path / "one_a").mkdir()
    _, splits, _, _ = _run(tmp_path / "one_a", rows, domains={3: ["AMP-binding"]})
    assert splits[0]["split_call"] == "CLEAR"


def test_a_piece_from_an_assembly_line_protein_is_left_unresolved(tmp_path):
    """The reference gene is a single-domain enzyme, but the genome piece is part of a multi-module NRPS protein."""
    rows = BASE + [("g003", "q000003", 60, 50, 200, 1, 150), ("g003", "q000004", 55, 48, 180, 156, 301)]
    _, splits, _, _ = _run(tmp_path, rows, b1_domains=("Condensation_LCL", "AMP-binding"))
    (s,) = splits
    assert s["split_call"] == "MODULAR_UNRESOLVED"
    assert (s["modular_reference_gene"], s["modular_piece"]) == ("False", "True")


def test_a_hit_table_without_reference_coordinates_says_the_check_did_not_run(tmp_path):
    rows = [r[:5] for r in BASE + [("g003", "q000003", 60, 50, 200, 1, 150), ("g003", "q000004", 55, 48, 180, 156, 301)]]
    table, splits, receipt, _ = _run(tmp_path, rows)
    assert splits == [] and receipt["split_gene_check"].startswith("not run")
    assert table["r3"]["status"] == "PRESENT_IN_CORE"
