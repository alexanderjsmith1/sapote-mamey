"""Card M5_456_rarity_by_assembly: tools/locus_rarity_by_genus.py counts genomes by assembly by default (v1.1.0).
Fixture tests/fixtures/locus_rarity_actinomadura_208_entries.tsv: the 208 Actinomadura entries of the M5 genome library
(public accessions with total length; assembly_accession filled where NCBI links a WGS id to its GCA, 21 Oct 2026).
The M5 duplicate-assembly map counts them as 142 assemblies, 12 of them through complete-genome CP/AP entries of the
same length as a GCA entry. The synthetic kit and stand-in `diamond` follow tests/test_m5_455_locus_rarity_by_genus.py."""
import csv
import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/locus_rarity_by_genus.py"
FIXTURE = ROOT / "tests/fixtures/locus_rarity_actinomadura_208_entries.tsv"
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
GENES = ["MKVLAAGTWE" * 3, "MPRSTLLQAN" * 3, "MGHHKEEWTA" * 3, "MSSLLDPRVC" * 3]
KINDS = ["biosynthetic", "biosynthetic-additional", "biosynthetic", "transport"]          # 3 core genes
CP_AP_MERGED = {"AP029191", "CP044407", "CP053892", "CP054932", "CP059572", "CP083237", "CP094265", "CP094266",
                "CP108331", "CP146086", "CP184335", "CP192011"}


def write_kit(kit, genus, targets):
    """targets: strains (reference_held) each carrying the whole locus."""
    kit.mkdir(); rows, faa = [], []
    def add(source, strain, region):
        for seq, kind in zip(GENES, KINDS):
            i = f"CDS{len(rows) + 1:05d}"
            rows.append(dict(id=i, source=source, group=source, genus=genus, strain=strain, origin=f"{strain}:{region}",
                             locus_tag=f"t{len(rows)}", subtype=kind, region_product="T1PKS", length=len(seq),
                             record_id=region.split(".region")[0], region=region))
            faa.append(f">{i}\n{seq}\n")
    add("isolate", "SYN-Q", "N1.region001.gbk")
    for t in targets:
        add("reference_held", t, f"{t}_c1.region001.gbk")
    with open(kit / "REGION_CDS_META.tsv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=META_COLS, delimiter="\t", extrasaction="ignore", restval=""); w.writeheader(); w.writerows(rows)
    (kit / "REGION_CDS.faa").write_text("".join(faa))


def run(tmp_path, kit, genome_table, *extra, out="out"):
    dmd = tmp_path / "diamond"
    if not dmd.exists():
        dmd.write_text(STANDIN.format(py=sys.executable)); dmd.chmod(dmd.stat().st_mode | stat.S_IEXEC)
    args = [sys.executable, str(TOOL), "--kit", str(kit), "--query-strain", "SYN-Q", "--query-region", "N1.region001.gbk",
            "--out", str(tmp_path / out), "--diamond", str(dmd), "--threads", "1", *extra]
    if genome_table:
        args += ["--genome-table", str(genome_table)]
    r = subprocess.run(args, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return tmp_path / out


def tsv(p):
    return list(csv.DictReader(open(p), delimiter="\t"))


def genus_row(out, genus):
    return {x["genus"]: x for x in tsv(out / "RARITY_BY_GENUS.tsv")}[genus]


def test_actinomadura_208_entries_are_142_assemblies(tmp_path):
    kit = tmp_path / "kit"; write_kit(kit, "Actinomadura", ["CP053892", "CP053892.1", "GCA_013211575.1"])
    out = run(tmp_path, kit, FIXTURE)
    g = genus_row(out, "Actinomadura")
    assert (g["ref_SID_genomes_by_entry"], g["ref_SID_genomes_by_assembly"]) == ("208", "142")
    assert g["ref_SID_genomes"] == "142" and g["count_basis"] == "assembly"           # by assembly is the default
    keys = tsv(out / "ASSEMBLY_KEYS.tsv")
    merged = {k["strain"].split(".")[0] for k in keys if "merged with GCA_" in k["rule"] and k["strain"][:2] in ("CP", "AP")}
    assert merged == CP_AP_MERGED                                                     # the 12 complete-genome merges
    assert {k["assembly_key"] for k in keys if k["strain"] in ("CP053892", "CP053892.1", "GCA_013211575.1")} == {"GCA_013211575"}
    rec = json.loads((out / "RECEIPT.json").read_text())
    assert rec["count_by"] == "assembly" and rec["counted"] == {"entries": 208, "assemblies": 142}


def test_three_copies_of_one_assembly_count_once(tmp_path):
    kit = tmp_path / "kit"; write_kit(kit, "Actinomadura", ["CP053892", "CP053892.1", "GCA_013211575.1"])
    g = genus_row(run(tmp_path, kit, FIXTURE), "Actinomadura")
    assert (g["genomes_with_region_ge30pct_core_genes_public_by_entry"], g["genomes_with_region_ge30pct_core_genes_public_by_assembly"]) == ("3", "1")
    t = tsv(tmp_path / "out/TARGET_REGIONS.tsv")
    assert {x["assembly_key"] for x in t} == {"GCA_013211575"} and len(t) == 3       # every target region is still listed


def flip_table(tmp_path):
    gt = tmp_path / "genomes.tsv"
    gt.write_text("strain\tsource\tgenus\tassembly_accession\ttotal_bp\n"
                  "GCF_000000011.1\treference_held\tGenus_a\t\t8000001\n"
                  "GCA_000000011.2\treference_held\tGenus_a\t\t8000001\n"          # GCF/GCA + version: one assembly
                  "WXYZ00000000\treference_held\tGenus_a\tGCA_000000022.1\t7000002\n"   # WGS id linked to its GCA
                  "CP000099\treference_held\tGenus_a\t\t7000002\n"                 # complete genome, same length: same assembly
                  "GCA_000000033.1\treference_held\tGenus_a\t\t9000003\n")         # no region: denominator only
    return gt


def test_flip_case_rare_by_assembly_not_rare_by_entry(tmp_path):
    kit = tmp_path / "kit"; write_kit(kit, "Genus_a", ["GCF_000000011.1", "GCA_000000011.2", "WXYZ00000000", "CP000099"])
    gt = flip_table(tmp_path)
    g = genus_row(run(tmp_path, kit, gt), "Genus_a")
    # 4 entries carry >= 30 % of the core (not rare at <= 2); they are 2 assemblies (rare at <= 2)
    assert g["genomes_with_region_ge30pct_core_genes_public_by_entry"] == "4"
    assert g["genomes_with_region_ge30pct_core_genes_public_by_assembly"] == "2"
    assert g["genomes_with_region_ge30pct_core_genes_public"] == "2"
    assert (g["public_genomes_by_entry"], g["public_genomes_by_assembly"], g["public_genomes"]) == ("5", "3", "3")


def test_count_by_entry_opt_out_restores_entry_counts(tmp_path):
    kit = tmp_path / "kit"; write_kit(kit, "Genus_a", ["GCF_000000011.1", "GCA_000000011.2", "WXYZ00000000", "CP000099"])
    gt = flip_table(tmp_path)
    out = run(tmp_path, kit, gt, "--count-by", "entry")
    g = genus_row(out, "Genus_a")
    assert g["count_basis"] == "entry"
    assert (g["genomes_with_region_ge30pct_core_genes_public"], g["public_genomes"]) == ("4", "5")
    assert g["genomes_with_region_ge30pct_core_genes_public_by_assembly"] == "2"      # both still reported
    assert json.loads((out / "RECEIPT.json").read_text())["count_by"] == "entry"


def test_without_lengths_only_id_rules_apply(tmp_path):
    kit = tmp_path / "kit"; write_kit(kit, "Genus_a", ["GCF_000000011.1", "GCA_000000011.2", "WXYZ00000000", "CP000099"])
    g = genus_row(run(tmp_path, kit, None), "Genus_a")                                # denominators = kit strains, no total_bp
    assert (g["public_genomes_by_entry"], g["public_genomes_by_assembly"]) == ("4", "3")   # only the GCF/GCA pair merges
