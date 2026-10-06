"""tools/gap_directed_rescue.py: what the core's reference has and the core lacks, looked for across the whole genome.

2026-09-28: a real split-cluster rescue came from knowing what was missing (a halogenase), searching the
genome, picking the one clear candidate among paralogs, and checking coherence. The missing piece can sit on a contig
with no antiSMASH region, which region-to-region pairing cannot see.
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
spec = importlib.util.spec_from_file_location("gap_directed_rescue", ROOT / "tools/gap_directed_rescue.py")
gdr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gdr)

AA = "M" + "ACDEFGHIKLMNPQRSTVWY" * 15


def _record(name, genes, region=None, length=None):
    """genes: [(locus_tag, start)] each 900 bp forward; region: (start, end, n, contig_edge)."""
    length = length or max(s for _, s in genes) + 2000
    lines = [f"LOCUS       {name:<16}{length:>12} bp    DNA     linear   UNK 01-JAN-1980",
             f"DEFINITION  test organism {name}, whole genome shotgun sequence.", f"ACCESSION   {name}",
             f"VERSION     {name}", "FEATURES             Location/Qualifiers"]
    if region:
        s, e, n, edge = region
        lines += [f"     region          {s + 1}..{e}", f'                     /region_number="{n}"',
                  f'                     /contig_edge="{edge}"', '                     /product="T1PKS"']
    for tag, s in genes:
        lines += [f"     CDS             {s + 1}..{s + 900}", f'                     /locus_tag="{tag}"',
                  '                     /product="enzyme"', f'                     /translation="{AA}"']
    lines.append("ORIGIN")
    for start in range(0, length, 60):
        chunk = "a" * min(60, length - start)
        lines.append(f"{start + 1:>9} " + " ".join(chunk[j:j + 10] for j in range(0, len(chunk), 10)))
    return "\n".join(lines + ["//"]) + "\n"


def _reference(tmp_path, ks_genes=()):
    lines = ["LOCUS       REF1                    7000 bp    DNA     linear   UNK 01-JAN-1980",
             "DEFINITION  reference cluster.", "ACCESSION   REF1", "VERSION     REF1",
             "FEATURES             Location/Qualifiers"]
    for i in range(6):
        lines += [f"     CDS             {i * 1000 + 1}..{i * 1000 + 900}", f'                     /gene="r{i + 1}"',
                  '                     /product="enzyme"', '                     /gene_kind="biosynthetic-additional"',
                  f'                     /translation="{AA}"']
        if i + 1 in ks_genes:
            lines += [f"     aSDomain        {i * 1000 + 31}..{i * 1000 + 600}", '                     /aSDomain="PKS_KS"']
    lines.append("ORIGIN")
    for start in range(0, 7000, 60):
        lines.append(f"{start + 1:>9} " + " ".join("a" * 10 for _ in range(min(6, (7000 - start) // 10))))
    p = tmp_path / "BGC0000999.gbk"
    p.write_text("\n".join(lines + ["//"]) + "\n")
    return p


def _setup(tmp_path, ks_genes=()):
    # ctgA: the core region (r1-r3); ctgB: an 8 kb contig with no region carrying r4-r6;
    # ctgC: a long contig with a weaker paralog of r4.
    core = _record("ctgA", [("a1", 1000), ("a2", 2000), ("a3", 3000)], region=(900, 4000, 1, "True"), length=4000)
    genome = (core + _record("ctgB", [("b1", 1000), ("b2", 2000), ("b3", 3000)], length=8000)
              + _record("ctgC", [("c1", 50000)], length=200000))
    z = tmp_path / "genome.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("genome.gbk", genome)
        zf.writestr("ctgA.region001.gbk", core)
    # protein ids follow record then CDS order: q000001-3 ctgA, q000004-6 ctgB, q000007 ctgC
    rows = [("g001", "q000001", 80, 99, 500), ("g002", "q000002", 75, 99, 480), ("g003", "q000003", 70, 98, 450),
            ("g004", "q000004", 72, 99, 460), ("g004", "q000007", 40, 90, 200),
            ("g005", "q000005", 65, 97, 420), ("g006", "q000006", 60, 95, 400)]
    hits = tmp_path / "hits.tsv"
    hits.write_text("".join("\t".join(map(str, r)) + "\n" for r in rows))
    return z, _reference(tmp_path, ks_genes), hits


def _run(tmp_path, hits_rows=None):
    z, ref, hits = _setup(tmp_path)
    if hits_rows is not None:
        hits.write_text("".join("\t".join(map(str, r)) + "\n" for r in hits_rows))
    out = tmp_path / "out"
    assert gdr.main(["--zip", str(z), "--label", "T", "--core", "ctgA.region001", "--reference", str(ref),
                     "--reference-name", "ref cluster", "--out", str(out), "--hits", str(hits)]) == 0
    rows = {r["name"]: r for r in csv.DictReader(open(out / "gap_rescue.tsv"), delimiter="\t")}
    return rows, json.loads((out / "gap_rescue_receipt.json").read_text()), out


def test_missing_genes_found_on_a_contig_without_a_region(tmp_path):
    rows, receipt, out = _run(tmp_path)
    assert [rows[f"r{i}"]["status"] for i in (1, 2, 3)] == ["PRESENT_IN_CORE"] * 3
    assert all(rows[f"r{i}"]["status"] == "MISSING_FOUND_CLEAR" for i in (4, 5, 6))
    assert rows["r4"]["best_region_identity"] == "T / ctgB (no antiSMASH region)"
    (p,) = receipt["partners"]
    assert p["partner_contig"] == "ctgB" and p["clear_finds"] == 3 and p["biosynthetic_clear_finds"] == 3
    assert p["concentrated"] and p["split_plausible"]
    assert (out / "gap_rescue.png").stat().st_size > 10_000


def test_a_close_paralog_makes_the_find_ambiguous(tmp_path):
    rows, receipt, _ = _run(tmp_path, [("g001", "q000001", 80, 99, 500), ("g004", "q000004", 60, 99, 300),
                                       ("g004", "q000007", 58, 99, 290)])
    assert rows["r4"]["status"] == "MISSING_FOUND_AMBIGUOUS"
    assert rows["r5"]["status"] == "MISSING_NOT_FOUND"
    assert receipt["partners"] == []


def test_refuses_to_write_inside_the_bundle(tmp_path):
    z, ref, hits = _setup(tmp_path)
    with pytest.raises(Exception):
        gdr.main(["--zip", str(z), "--label", "T", "--core", "ctgA.region001", "--reference", str(ref),
                  "--out", str(ROOT / "tmp_gap_rescue_out"), "--hits", str(hits)])
    assert not (ROOT / "tmp_gap_rescue_out").exists()


def test_modular_pks_genes_do_not_make_a_partner(tmp_path):
    """A giant PKS gene's best whole-gene match follows module paralogy, so it never counts toward a partner."""
    z, ref, hits = _setup(tmp_path, ks_genes=(4, 5, 6))
    out = tmp_path / "out"
    assert gdr.main(["--zip", str(z), "--label", "T", "--core", "ctgA.region001", "--reference", str(ref),
                     "--out", str(out), "--hits", str(hits), "--no-figure"]) == 0
    rows = {r["name"]: r for r in csv.DictReader(open(out / "gap_rescue.tsv"), delimiter="\t")}
    assert rows["r4"]["modular_pks"] == "True" and rows["r4"]["status"] == "MISSING_FOUND_CLEAR"
    assert json.loads((out / "gap_rescue_receipt.json").read_text())["partners"] == []


def test_a_shared_best_match_keeps_only_the_closest_reference_gene(tmp_path):
    """Two reference genes whose best match is one genome protein: only the closer keeps it (reciprocal best)."""
    rows, _, _ = _run(tmp_path, [("g001", "q000001", 80, 99, 500), ("g002", "q000002", 75, 99, 480),
                                 ("g003", "q000003", 70, 98, 450), ("g004", "q000004", 72, 99, 460),
                                 ("g005", "q000004", 45, 90, 250), ("g006", "q000006", 60, 95, 400)])
    assert rows["r4"]["reciprocal_best"] == "True"
    assert rows["r5"]["reciprocal_best"] == "False"
