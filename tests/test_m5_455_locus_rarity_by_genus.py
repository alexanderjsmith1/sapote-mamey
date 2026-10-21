"""Lane CLAUDE_M5_v9.7.455_locus_rarity_by_genus: tools/locus_rarity_by_genus.py on a synthetic extract kit.
Invented strains (SYN-*), genera (Genus_a/b) and sequences. A stand-in `diamond` computes identity of equal-length
sequences position by position and writes real outfmt-6 rows, so DIAMOND itself is not needed."""
import csv
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/locus_rarity_by_genus.py"
META_COLS = ["id", "source", "group", "genus", "strain", "origin", "locus_tag", "label", "subtype", "region_product",
             "length", "assembly", "record_id", "region", "locus_identity", "source_sha256", "assembly_binding"]

STANDIN = '''#!{py}
import sys
a = sys.argv[1:]
if a and a[0] == "version":
    print("diamond version SYNTHETIC-STANDIN"); sys.exit(0)
def fa(p):
    s, c = {{}}, None
    for l in open(p):
        l = l.strip()
        if l.startswith(">"): c = l[1:]; s[c] = ""
        elif c: s[c] += l
    return s
q, d, mid = fa(a[a.index("-q") + 1]), fa(a[a.index("-d") + 1]), float(a[a.index("--id") + 1])
for qi, qs in q.items():
    for di, ds in d.items():
        if len(qs) != len(ds): continue
        pid = 100.0 * sum(x == y for x, y in zip(qs, ds)) / len(qs)
        if pid >= mid: print(f"{{qi}}\\t{{di}}\\t{{pid:.1f}}\\t100.0\\t{{pid:.0f}}")
'''

G1, G2, G3, G4 = "MKVLAAGTWE" * 3, "MPRSTLLQAN" * 3, "MGHHKEEWTA" * 3, "MSSLLDPRVC" * 3


def mutate(s, k):  # change the first k positions: identity = 100 * (len - k) / len
    return "".join("W" if i < k and c != "W" else ("Y" if i < k else c) for i, c in enumerate(s))


def write_kit(kit):
    kit.mkdir()
    rows, faa = [], []
    def add(source, genus, strain, region, genes, kinds):
        for seq, kind in zip(genes, kinds):
            i = f"CDS{len(rows) + 1:05d}"
            rows.append(dict(id=i, source=source, group=source, genus=genus, strain=strain, origin=f"{strain}:{region}",
                             locus_tag=f"t{len(rows)}", subtype=kind, region_product="T1PKS", length=len(seq),
                             record_id=region.split(".region")[0], region=region))
            faa.append(f">{i}\n{seq}\n")
    q = [G1, G2, G3, G4]; kinds = ["biosynthetic", "biosynthetic-additional", "", "transport"]
    add("isolate", "Genus_a", "SYN-Q", "N1.region001.gbk", q, kinds)                    # the locus: 4 genes, 2 core
    add("isolate", "Genus_a", "SYN-Q", "N2.region001.gbk", q, kinds)                    # the query strain's own other copy: left out
    add("reference_held", "Genus_a", "SYN-R1", "R1.region003.gbk", q, kinds)           # 4/4, core 2/2
    add("reference_held", "Genus_a", "SYN-R2", "R2.region001.gbk", [mutate(G1, 6), G3], ["biosynthetic", ""])   # G1 at 80 %, G3: 2/4, core 1/2
    add("reference_held", "Genus_a", "SYN-R3", "R3.region001.gbk", [mutate(G1, 18)], ["biosynthetic"])          # G1 at 40 %: below 50, no match
    add("SID_held", "Genus_a", "SYN-S1", "S1.region002.gbk", [G1, G2, G4], kinds[:2] + ["transport"])          # 3/4, core 2/2
    add("isolate", "Genus_b", "SYN-A2", "A2.region001.gbk", [G2, G4], ["", ""])                                  # 2/4, core 1/2
    add("MIBiG", "", "BGC9999999", "BGC9999999.gbk", q, kinds)                                                    # never a target
    with open(kit / "REGION_CDS_META.tsv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=META_COLS, delimiter="\t", extrasaction="ignore", restval=""); w.writeheader(); w.writerows(rows)
    (kit / "REGION_CDS.faa").write_text("".join(faa))


@pytest.fixture
def setup(tmp_path):
    kit = tmp_path / "kit"; write_kit(kit)
    dmd = tmp_path / "diamond"; dmd.write_text(STANDIN.format(py=sys.executable)); dmd.chmod(dmd.stat().st_mode | stat.S_IEXEC)
    return tmp_path, kit, dmd


def run(tmp_path, kit, dmd, *extra, out="out"):
    return subprocess.run([sys.executable, str(TOOL), "--kit", str(kit), "--query-strain", "SYN-Q", "--query-region",
                           "N1.region001.gbk", "--alias", "synthetic locus", "--out", str(tmp_path / out), "--diamond", str(dmd),
                           "--threads", "1", *extra], capture_output=True, text=True)


def tsv(p):
    return list(csv.DictReader(open(p), delimiter="\t"))


def test_target_regions_and_core_counts(setup):
    tmp_path, kit, dmd = setup
    r = run(tmp_path, kit, dmd); assert r.returncode == 0, r.stderr
    t = {x["target_strain"]: x for x in tsv(tmp_path / "out/TARGET_REGIONS.tsv")}
    assert set(t) == {"SYN-R1", "SYN-R2", "SYN-S1", "SYN-A2"}            # no SYN-Q copy, no MIBiG, SYN-R3 below 50 %
    assert (t["SYN-R1"]["genes_matched"], t["SYN-R1"]["core_genes_matched"]) == ("4", "2")
    assert (t["SYN-R2"]["genes_matched"], t["SYN-R2"]["core_genes_matched"], t["SYN-R2"]["mean_identity_pct"]) == ("2", "1", "90.0")
    assert (t["SYN-S1"]["role"], t["SYN-S1"]["genes_matched"], t["SYN-S1"]["core_genes_matched"]) == ("SID", "3", "2")
    assert (t["SYN-A2"]["role"], t["SYN-A2"]["genus"]) == ("AS", "Genus_b")
    q = tsv(tmp_path / "out/QUERY_GENES.tsv")
    assert [x["core_gene"] for x in q] == ["yes", "yes", "no", "no"]
    assert "core genes: 2" in (tmp_path / "out/LOCUS.txt").read_text()


def test_public_and_sid_counted_apart(setup):
    tmp_path, kit, dmd = setup
    assert run(tmp_path, kit, dmd).returncode == 0
    g = {x["genus"]: x for x in tsv(tmp_path / "out/RARITY_BY_GENUS.tsv")}["Genus_a"]
    assert (g["genomes_with_region_ge50pct_genes_public"], g["genomes_with_region_ge50pct_genes_SID"]) == ("2", "1")
    assert (g["genomes_with_region_ge50pct_core_genes_public"], g["genomes_with_region_ge50pct_core_genes_ref_SID"]) == ("2", "3")
    assert (g["public_genomes"], g["SID_genomes"], g["other_AS_strains_in_genus"]) == ("3", "1", "0")   # SYN-Q not its own denominator
    pub = tsv(tmp_path / "out/TOP5_PUBLIC_REFERENCE.tsv"); assert {x["role"] for x in pub} == {"reference"}
    assert [x["target_strain"] for x in tsv(tmp_path / "out/TOP5_REFERENCE.tsv")] == ["SYN-R1", "SYN-S1", "SYN-R2"]


def test_genome_table_sets_denominators_and_receipt_records_it(setup):
    tmp_path, kit, dmd = setup
    gt = tmp_path / "genomes.tsv"
    gt.write_text("strain\tsource\tgenus\nSYN-R1\treference_held\tGenus_a\nSYN-R2\treference_held\tGenus_a\n"
                  "SYN-R3\treference_held\tGenus_a\nSYN-R4\treference_held\tGenus_a\nSYN-S1\tSID_held\tGenus_a\n")
    assert run(tmp_path, kit, dmd, "--genome-table", str(gt)).returncode == 0
    g = {x["genus"]: x for x in tsv(tmp_path / "out/RARITY_BY_GENUS.tsv")}["Genus_a"]
    assert g["public_genomes"] == "4"                                     # SYN-R4 has no region but is counted
    rec = json.loads((tmp_path / "out/RECEIPT.json").read_text())
    assert rec["denominators"] == "GENOME_TABLE" and rec["query"]["core_genes"] == 2 and rec["diamond"].endswith("STANDIN")


def test_exclude_removes_a_strain_from_targets_and_denominators(setup):
    tmp_path, kit, dmd = setup
    assert run(tmp_path, kit, dmd, "--exclude", "SYN-R1").returncode == 0
    assert "SYN-R1" not in {x["target_strain"] for x in tsv(tmp_path / "out/TARGET_REGIONS.tsv")}
    assert {x["genus"]: x for x in tsv(tmp_path / "out/RARITY_BY_GENUS.tsv")}["Genus_a"]["public_genomes"] == "2"


@pytest.mark.parametrize("case", ["no_region", "no_diamond", "out_exists"])
def test_refusals_exit_2(setup, case):
    tmp_path, kit, dmd = setup
    if case == "no_region":
        r = subprocess.run([sys.executable, str(TOOL), "--kit", str(kit), "--query-strain", "SYN-Q", "--query-region", "N9.region001.gbk",
                            "--out", str(tmp_path / "o"), "--diamond", str(dmd)], capture_output=True, text=True)
    elif case == "no_diamond":
        r = run(tmp_path, kit, tmp_path / "missing_diamond")
    else:
        (tmp_path / "out").mkdir(); r = run(tmp_path, kit, dmd)
    assert r.returncode == 2 and "REFUSED" in r.stderr
