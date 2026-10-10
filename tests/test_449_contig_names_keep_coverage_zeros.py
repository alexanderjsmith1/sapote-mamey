"""Contig names read from antiSMASH GenBank records keep a 0 right after the point of a SPAdes coverage.

antiSMASH writes a SPAdes contig such as NODE_1_length_4000_cov_65.032271 with LOCUS and DEFINITION intact, but with
ACCESSION NODE_1_length_4000_cov_65 and VERSION NODE_1_length_4000_cov_65.32271. Biopython's rec.id is the VERSION
line, and it reads the part after the last point as an integer version, so the 0 is lost even when VERSION keeps it.
Names taken from rec.id then match no other table. The engine's rule (parsers._record_contig_id) takes the LOCUS name
for NODE_n_length_L_cov_ records and rec.id for everything else, so accession records (CP..., NZ_...) are unchanged.
"""
import csv
import importlib.util
import io
import json
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("Bio")
pytest.importorskip("matplotlib")

from Bio import SeqIO  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gdr = _load("gap_directed_rescue_contig_names", "tools/gap_directed_rescue.py")

AA = "M" + "ACDEFGHIKLMNPQRSTVWY" * 15  # 301 aa
C1, C2, C3 = ("NODE_1_length_4000_cov_65.032271", "NODE_2_length_8000_cov_7.04",   # a 0 right after the point
              "NODE_3_length_200000_cov_9.5")                                          # no 0: never affected
SHORT = ("NODE_1_length_4000_cov_65.32271", "NODE_2_length_8000_cov_7.4")             # what rec.id reads


def _header(name, length, accession_style=False):
    """LOCUS, DEFINITION, ACCESSION and VERSION as antiSMASH writes them."""
    if accession_style:
        acc, ver, definition = name, f"{name}.1", "Streptomyces exemplar chromosome, complete genome."
    else:
        acc = name.rsplit(".", 1)[0]
        ver = f"{acc}.{int(name.rsplit('.', 1)[1])}"   # the VERSION line drops the 0, as in antiSMASH's files
        definition = f"{name}."
    return [f"LOCUS       {name:<16}{length:>12} bp    DNA     linear   UNK 01-JAN-1980",
            f"DEFINITION  {definition}", f"ACCESSION   {acc}", f"VERSION     {ver}"]


def _record(name, genes, length, region=None, accession_style=False, comment=None):
    """genes: [(locus_tag, start, strand)], each 900 bp; region: (start, end, n, contig_edge)."""
    lines = _header(name, length, accession_style)
    if comment:
        lines += [f"COMMENT     {comment[0]}"] + [f"            {c}" for c in comment[1:]]
    lines.append("FEATURES             Location/Qualifiers")
    if region:
        s, e, n, edge = region
        lines += [f"     region          {s + 1}..{e}", f'                     /region_number="{n}"',
                  f'                     /contig_edge="{edge}"', '                     /product="saccharide"']
    for tag, s, strand in genes:
        loc = f"{s + 1}..{s + 900}" if strand > 0 else f"complement({s + 1}..{s + 900})"
        lines += [f"     CDS             {loc}", f'                     /locus_tag="{tag}"',
                  '                     /product="enzyme"', f'                     /translation="{AA}"']
    lines.append("ORIGIN")
    for start in range(0, length, 60):
        chunk = "a" * min(60, length - start)
        lines.append(f"{start + 1:>9} " + " ".join(chunk[j:j + 10] for j in range(0, len(chunk), 10)))
    return "\n".join(lines + ["//"]) + "\n"


def _reference(tmp_path):
    lines = ["LOCUS       REF1                    7000 bp    DNA     linear   UNK 01-JAN-1980",
             "DEFINITION  reference cluster.", "ACCESSION   REF1", "VERSION     REF1",
             "FEATURES             Location/Qualifiers"]
    for i in range(6):
        lines += [f"     CDS             {i * 1000 + 1}..{i * 1000 + 900}", f'                     /gene="r{i + 1}"',
                  '                     /product="enzyme"', '                     /gene_kind="biosynthetic-additional"',
                  f'                     /translation="{AA}"']
    lines.append("ORIGIN")
    for start in range(0, 7000, 60):
        lines.append(f"{start + 1:>9} " + " ".join("a" * 10 for _ in range(min(6, (7000 - start) // 10))))
    p = tmp_path / "BGC0000999.gbk"
    p.write_text("\n".join(lines + ["//"]) + "\n")
    return p


def _genome(tmp_path, names=(C1, C2, C3), accession_style=False, core_id=None):
    # names[0] (4 kb): the core region, to the contig end; names[1] (8 kb, no region); names[2] (200 kb)
    a, b, c = names
    core = _record(a, [("a1", 1000, 1), ("a2", 2000, 1), ("a3", 3000, 1)], 4000, region=(0, 4000, 1, "True"),
                   accession_style=accession_style)
    genome = (core + _record(b, [("b1", 0, 1), ("b2", 2000, 1), ("b3", 3000, 1)], 8000, accession_style=accession_style)
              + _record(c, [("c1", 50000, 1)], 200000, accession_style=accession_style))
    z = tmp_path / "genome.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("genome.gbk", genome)
        zf.writestr(f"{core_id or a}.region001.gbk", core)   # antiSMASH names region files by record id
    return z


# protein ids follow record then CDS order: q000001-3 on the core contig, q000004-6 on the second, q000007 on the third.
# r3 is split: its first half on a3 (core contig end), its second on b1 (second contig start).
HITS = [("g001", "q000001", 80, 99, 500, 1, 301), ("g002", "q000002", 75, 99, 480, 1, 301),
        ("g003", "q000003", 60, 50, 200, 1, 150), ("g003", "q000004", 55, 48, 180, 156, 301),
        ("g004", "q000005", 72, 99, 460, 1, 301), ("g005", "q000006", 65, 97, 420, 1, 301)]


def _run(tmp_path, names=(C1, C2, C3), accession_style=False, core_id=None):
    z = _genome(tmp_path, names, accession_style, core_id)
    hits = tmp_path / "hits.tsv"
    hits.write_text("".join("\t".join(map(str, r)) + "\n" for r in HITS))
    out = tmp_path / "out"
    assert gdr.main(["--zip", str(z), "--label", "T", "--core", f"{core_id or names[0]}.region001",
                     "--reference", str(_reference(tmp_path)), "--out", str(out), "--hits", str(hits),
                     "--no-figure"]) == 0
    table = {r["name"]: r for r in csv.DictReader(open(out / "gap_rescue.tsv"), delimiter="\t")}
    splits = list(csv.DictReader(open(out / "gap_rescue_split_genes.tsv"), delimiter="\t"))
    return z, table, splits, out


def test_the_engine_rule_keeps_the_zero_and_leaves_accession_records_alone():
    from mamey.parsers import _record_contig_id
    rec = next(SeqIO.parse(io.StringIO(_record(C1, [], 120)), "genbank"))
    assert rec.id == SHORT[0], "the defect: Biopython's rec.id is the VERSION line, without the 0"
    assert _record_contig_id(rec) == C1
    kept = _record(C1, [], 120).replace(f"VERSION     {SHORT[0]}", f"VERSION     {C1}")
    rec = next(SeqIO.parse(io.StringIO(kept), "genbank"))
    assert rec.id == SHORT[0] and _record_contig_id(rec) == C1, "Biopython drops the 0 even when VERSION keeps it"
    acc = next(SeqIO.parse(io.StringIO(_record("CP000001", [], 120, accession_style=True)), "genbank"))
    assert acc.id == "CP000001.1" and _record_contig_id(acc) == "CP000001.1"


def test_every_gap_rescue_output_keeps_the_zero(tmp_path):
    z, table, splits, out = _run(tmp_path)
    prots, regions = gdr.load_genome(z, "T")
    assert {p["contig"] for p in prots.values()} == {C1, C2, C3}
    assert [r["contig"] for r in regions] == [C1]
    assert {p["shown"] for p in prots.values()} == {f"T / {c}" for c in (C1, C2, C3)}
    assert table["r1"]["best_contig"] == C1 and table["r4"]["best_contig"] == C2
    (s,) = splits
    assert s["piece1_region_identity"].startswith(f"T / {C1} / region001")
    assert s["piece2_region_identity"] == f"T / {C2} (no antiSMASH region)"
    receipt = json.loads((out / "gap_rescue_receipt.json").read_text())
    assert receipt["core"].startswith(f"T / {C1} / region001")
    for f in out.iterdir():
        if f.suffix in {".tsv", ".json", ".md", ".txt", ".csv"}:
            text = f.read_text()
            assert not any(x in text for x in SHORT), f"{f.name} carries a name without its 0"


def test_an_accession_genome_keeps_its_record_ids(tmp_path):
    _, table, splits, _ = _run(tmp_path, names=("CP000001", "CP000002", "CP000003"), accession_style=True,
                               core_id="CP000001.1")
    assert table["r1"]["best_contig"] == "CP000001.1" and table["r4"]["best_contig"] == "CP000002.1"
    (s,) = splits
    assert s["piece2_region_identity"] == "T / CP000002.1 (no antiSMASH region)"


def test_the_dark_gene_scan_keeps_the_zero(tmp_path):
    dgs = _load("dark_gene_scan_contig_names", "tools/dark_gene_scan.py")
    got = dgs._extract_all_proteins(str(_genome(tmp_path)))
    assert set(got) == {C1, C2, C3}
    assert {p["contig"] for ps in got.values() for p in ps} == {C1, C2, C3}


def test_the_mlsa_assembly_from_genbank_keeps_the_zero(tmp_path):
    mlsa = _load("phylo_mlsa_contig_names", "tools/phylo_mlsa_from_antismash.py")
    assembly = mlsa.assembly_from_zip(_genome(tmp_path), min_bp=20)
    assert [name for name, _ in assembly["records"]] == [C1, C2, C3]
    assert not any(x.encode() in assembly["fasta_bytes"] for x in SHORT)


def test_the_gene_synteny_fallback_name_keeps_the_zero(tmp_path, monkeypatch):
    gsm = _load("gene_synteny_map_contig_names", "tools/gene_synteny_map.py")
    monkeypatch.setattr(gsm.parsers, "parse_bgcs_from_zip", lambda *a, **k: [])   # no engine record: the fallback
    prots, _ = gsm.load_genome(_genome(tmp_path), "T")
    assert {p["region"] for p in prots.values()} == {f"T / {C1} / region001 / ?"}


def test_the_companion_region_declaration_keeps_the_zero():
    from mamey.companion_evidence import validated_region
    comment = ["##antiSMASH-Data-START##", "Version      :: 8.0.4", "Orig. start  :: 0", "Orig. end    :: 4000",
               "##antiSMASH-Data-END##"]
    raw = _record(C1, [("a1", 1000, 1)], 4000, region=(0, 4000, 1, "True"), comment=comment).encode()
    bgc = {"contig": C1, "start": 0, "end": 4000, "region_number": 1, "antismash_region": "region001",
           "bgc_id": "BGC001"}
    got = validated_region(raw, "T", bgc, f"{C1}.region001.gbk")
    assert got["contig"] == C1 and got["state"] == "REGION_DECLARATION_BOUND"
