"""Card M5_456_family_rarity_by_window: tools/family_rarity_by_window.py on a synthetic antiSMASH zip and proteome.
Invented genomes and sequences. A stand-in `diamond` computes identity of equal-length sequences position by position and
writes outfmt-6 rows (qseqid sseqid pident qcovhsp), so DIAMOND itself is not needed."""
import csv
import gzip
import json
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/family_rarity_by_window.py"
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
        if pid >= mid: print(f"{{qi}}\\t{{di}}\\t{{pid:.1f}}\\t100.0")
'''
A, B, C, D, E = ("MKVLAAGTWE" * 3, "MPRSTLLQAN" * 3, "MGHHKEEWTA" * 3, "MSSLLDPRVC" * 3, "MQQWERTYIP" * 3)


def gbk(region_no, products, cds):
    lines = ["LOCUS       NODE_x", "FEATURES             Location/Qualifiers", f"     region          1..9000",
             f'                     /product="{products}"', '                     /contig_edge="False"']
    for i, (tag, aa, kind) in enumerate(cds):
        lines += [f"     CDS             {i * 100 + 1}..{i * 100 + 90}", f'                     /locus_tag="{tag}"']
        if kind: lines.append(f'                     /gene_kind="{kind}"')
        lines.append(f'                     /translation="{aa}"')
    return "\n".join(lines) + "\nORIGIN\n//\n"


def write_inputs(tmp):
    zp = tmp / "SYN-Q.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("NODE_1_length_90000_cov_10.region001.gbk",
                   gbk(1, "T1PKS", [("q1", A, "biosynthetic"), ("q2", B, "biosynthetic"), ("q3", C, "biosynthetic-additional"),
                                    ("q4", D, "biosynthetic"), ("q5", E, "transport")]))           # 4 core genes
        z.writestr("NODE_2_length_50000_cov_10.region001.gbk",
                   gbk(1, "terpene", [("r1", A, "biosynthetic"), ("r2", E, "")]))                  # 1 core gene
    prot = []
    def genome(acc, layout):          # layout: [(contig, start, seq)]
        for c, s, seq in layout: prot.append(f">{acc}|{c}|{s}|{s + 90}|+\n{seq}\n")
    block = lambda c: [(c, 1000, A), (c, 3000, B), (c, 5000, C), (c, 7000, D)]
    for acc in ("GCF_000000011.1", "GCA_000000011.2", "WXYZ00000000", "CP000099"):
        genome(acc, block(f"{acc}_c1"))
    genome("GCA_000000077.1", [("g7_c1", 1000, A), ("g7_c1", 60000, B)])        # 2 core genes, 59 kb apart: scattered
    genome("GCA_000000066.1", [("g6_c1", 1000, A), ("g6_c2", 1000, B), ("g6_c2", 3000, C), ("g6_c2", 5000, D)])  # other family: B, C, D in one window
    genome("GCA_000000055.1", [("g5_c1", 1000, E)])                              # family genome without core hits
    (tmp / "proteomes.faa").write_text("".join(prot))
    gt = tmp / "genomes.tsv"
    gt.write_text("genome_acc\tgenus\tfamily\tassembly_accession\ttotal_bp\n"
                  "GCF_000000011.1\tGenus_a\tFam_x\t\t8000001\n"
                  "GCA_000000011.2\tGenus_a\tFam_x\t\t8000001\n"
                  "WXYZ00000000\tGenus_a\tFam_x\tGCA_000000022.1\t7000002\n"
                  "CP000099\tGenus_a\tFam_x\t\t7000002\n"
                  "GCA_000000077.1\tGenus_a\tFam_x\t\t6000007\n"
                  "GCA_000000055.1\tGenus_a\tFam_x\t\t5000005\n"
                  "GCA_000000066.1\tGenus_b\tFam_y\t\t4000006\n")
    idt = tmp / "identity.tsv"
    idt.write_text("contig\tregion\tidentity\nNODE_1_length_90000_cov_10\tregion001\tSYN-Q / NODE_1_length_90000_cov_10 / region001 / BGC001\n")
    dmd = tmp / "diamond"; dmd.write_text(STANDIN.format(py=sys.executable)); dmd.chmod(dmd.stat().st_mode | stat.S_IEXEC)
    return zp, gt, idt, dmd


def run(tmp, *extra, out="out", expect=0):
    zp, gt, idt, dmd = write_inputs(tmp) if not (tmp / "diamond").exists() else (tmp / "SYN-Q.zip", tmp / "genomes.tsv", tmp / "identity.tsv", tmp / "diamond")
    r = subprocess.run([sys.executable, str(TOOL), "--antismash-zip", str(zp), "--strain", "SYN-Q", "--proteomes", str(tmp / "proteomes.faa"),
                        "--genome-table", str(gt), "--query-family", "Fam_x", "--identity-table", str(idt), "--out", str(tmp / out),
                        "--diamond", str(dmd), "--threads", "1", *extra], capture_output=True, text=True)
    assert r.returncode == expect, r.stderr
    return tmp / out, r


def rows(out):
    return list(csv.DictReader(open(out / "FAMILY_RARITY.tsv"), delimiter="\t"))


def test_window_counts_and_family_rare_by_assembly(tmp_path):
    out, _ = run(tmp_path)
    r = rows(out)[0]
    assert r["identity"] == "SYN-Q / NODE_1_length_90000_cov_10 / region001 / BGC001" and r["core_genes_J1"] == "4"
    assert (r["family_ge30pct_core_one_window_by_entry"], r["family_ge30pct_core_one_window_by_assembly"]) == ("4", "2")
    assert (r["family_genomes_by_entry"], r["family_genomes_by_assembly"]) == ("6", "4")
    assert r["family_rare"] == "yes" and r["count_basis"] == "assembly"           # 2 assemblies: rare; 4 entries would not be
    assert r["family_scattered_ge30pct_core_not_one_window"] == "1"                # GCA_000000077.1: genes 59 kb apart
    assert (r["table_genomes_by_entry"], r["table_genomes_by_assembly"]) == ("7", "5")
    assert r["table_ge30pct_core_one_window"] == "3" and r["best_core_in_one_window"] == "4"   # + Fam_y genome: B, C, D on one contig


def test_count_by_entry_opt_out(tmp_path):
    out, _ = run(tmp_path, "--count-by", "entry")
    r = rows(out)[0]
    assert (r["count_basis"], r["family_ge30pct_core_one_window"], r["family_rare"]) == ("entry", "4", "no")
    assert r["family_ge30pct_core_one_window_by_assembly"] == "2"


def test_pass_list_and_small_region(tmp_path):
    out, _ = run(tmp_path)
    p = list(csv.DictReader(gzip.open(out / "PASS_GENOMES.tsv.gz", "rt"), delimiter="\t"))
    first = {x["genome_acc"] for x in p if x["identity"].endswith("BGC001")}
    assert first == {"GCF_000000011.1", "GCA_000000011.2", "WXYZ00000000", "CP000099", "GCA_000000077.1", "GCA_000000066.1"}
    assert {x["assembly_key"] for x in p if x["genome_acc"] in ("WXYZ00000000", "CP000099")} == {"GCA_000000022"}
    small = rows(out)[1]
    assert small["identity"] == "SYN-Q / NODE_2_length_50000_cov_10 / region001 / IDENTITY_HOLD"   # not in the identity table
    assert small["family_rare"].startswith("n/a")
    rec = json.loads((out / "RECEIPT.json").read_text())
    assert rec["counted"] == {"table_entries": 7, "table_assemblies": 5, "family_entries": 6, "family_assemblies": 4}
    assert rec["family_rare"] == 1 and rec["diamond"].endswith("STANDIN")


@pytest.mark.parametrize("case", ["out_exists", "no_diamond", "bad_table"])
def test_refusals_exit_2(tmp_path, case):
    write_inputs(tmp_path)
    if case == "out_exists":
        (tmp_path / "out").mkdir()
    elif case == "no_diamond":
        (tmp_path / "diamond").unlink(); (tmp_path / "diamond").mkdir()
    else:
        (tmp_path / "genomes.tsv").write_text("genome_acc\tgenus\tfamily\nGCA_1\tGenus_a\t\n")
    _, r = run(tmp_path, expect=2)
    assert "REFUSED" in r.stderr
