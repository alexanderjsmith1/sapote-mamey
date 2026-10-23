"""Card M5_456_region_presence_survey: tools/region_presence_survey.py on synthetic genomes.
Invented genomes and sequences. The "genome sequences" are written in protein letters so that a stand-in `tblastn` can align
each query against them directly (position x 3 = bp); a stand-in `diamond` does the same for the proteomes. Neither BLAST+
nor DIAMOND is needed. The cases follow J6 / J6B: a gene below 50 % identity, a gene the gene caller did not annotate, a gene cut
by a contig end, and two copies of one assembly."""
import csv
import json
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/region_presence_survey.py"
FA = '''def fa(p):
    s, c = {}, None
    for l in open(p):
        l = l.strip()
        if l.startswith(">"): c = l[1:].split()[0]; s[c] = ""
        elif c: s[c] += l
    return s
'''
DIAMOND = '''#!{py}
import sys
{fa}a = sys.argv[1:]
if a and a[0] == "version":
    print("diamond version SYNTHETIC-STANDIN"); sys.exit(0)
q, d, mid = fa(a[a.index("-q") + 1]), fa(a[a.index("-d") + 1]), float(a[a.index("--id") + 1])
for qi, qs in q.items():
    for di, ds in d.items():
        if len(qs) != len(ds): continue
        pid = 100.0 * sum(x == y for x, y in zip(qs, ds)) / len(qs)
        if pid >= mid: print(f"{{qi}}\\t{{di}}\\t{{pid:.1f}}\\t100.0\\t{{pid:.0f}}")
'''
TBLASTN = '''#!{py}
import sys
{fa}a = sys.argv[1:]
if a and a[0] == "-version":
    print("tblastn: SYNTHETIC-STANDIN"); sys.exit(0)
q, s = fa(a[a.index("-query") + 1]), fa(a[a.index("-subject") + 1])
for qi, qs in q.items():
    for si, ss in s.items():
        best = None
        for off in range(len(ss)):
            seg = ss[off:off + len(qs)]
            if len(seg) < 5: break
            m = sum(x == y for x, y in zip(qs, seg)); L = len(seg)
            if m / L >= 0.4 and (best is None or (m, -L) > (best[0], -best[1])): best = (m, L, off)
        if best:
            m, L, off = best
            print(f"{{qi}}\\t{{si}}\\t{{100.0 * m / L:.1f}}\\t{{L}}\\t{{len(qs)}}\\t1\\t{{L}}\\t{{off * 3 + 1}}\\t{{(off + L) * 3}}\\t1e-10\\t{{float(m)}}\\t{{100 * L // len(qs)}}")
'''
P = ["MKVLAAGTWE" * 3, "MPRSTLLQAN" * 3, "MGHHKEEWTA" * 3, "MSSLLDPRVC" * 3]
FILL = "X" * 40


def mut(s, k):                                     # change the first k positions: identity = 100 * (30 - k) / 30
    return "".join(("W" if c != "W" else "Y") if i < k else c for i, c in enumerate(s))


def setup_inputs(tmp):
    (tmp / "query.faa").write_text("".join(f">g{i + 1}\n{s}\n" for i, s in enumerate(P)))
    gdir = tmp / "genomes"; gdir.mkdir()
    def genome(name, contigs):
        (gdir / f"{name}.fna").write_text("".join(f">{c}\n{seq}\n" for c, seq in contigs))
    p3_low = mut(P[2], 17)                                                    # 43.3 %: below the protein rule's 50 %
    genome("GX", [("GX_c1", FILL + P[0] + FILL + P[1] + FILL + p3_low + FILL + P[3] + FILL)])
    genome("GZ", [("GZ_c1", FILL + P[0] + FILL + P[1] + FILL + p3_low + FILL + P[3] + FILL)])   # same assembly as GX
    genome("GY", [("GY_c1", FILL + P[0] + FILL), ("GY_c2", FILL + P[1] + FILL)])                # two genes, two contigs
    genome("GW", [("GW_c1", FILL + P[0] + FILL + P[3][:12])])                                    # g4 cut by the contig end: 40 % cover
    prot = [f">GX|GX_c1|100|190|+\n{P[0]}\n", f">GX|GX_c1|400|490|+\n{P[1]}\n", f">GX|GX_c1|700|790|+\n{p3_low}\n",
            f">GX|GX_c1|1000|1090|+\n{P[3]}\n", f">GY|GY_c1|100|190|+\n{P[0]}\n", f">GW|GW_c1|100|190|+\n{P[0]}\n"]  # GZ: g1-g4 not annotated
    (tmp / "proteomes.faa").write_text("".join(prot))
    (tmp / "genomes.tsv").write_text("genome_acc\tgenus\tnucleotide\tassembly_accession\ttotal_bp\n"
                                     "GX\tGenus_a\tgenomes/GX.fna\tGCA_000000099.1\t5000001\n"
                                     "GZ\tGenus_a\tgenomes/GZ.fna\t\t5000001\n"
                                     "GY\tGenus_a\tgenomes/GY.fna\t\t5000002\n"
                                     "GW\tGenus_a\tgenomes/GW.fna\t\t5000003\n")
    for name, body in (("diamond", DIAMOND), ("tblastn", TBLASTN)):
        f = tmp / name; f.write_text(body.format(py=sys.executable, fa=FA)); f.chmod(f.stat().st_mode | stat.S_IEXEC)


def run(tmp, *extra, out="out", expect=0, proteomes=True):
    args = [sys.executable, str(TOOL), "--query-faa", str(tmp / "query.faa"), "--genomes", str(tmp / "genomes.tsv"),
            "--out", str(tmp / out), "--tblastn", str(tmp / "tblastn"), "--diamond", str(tmp / "diamond"), "--threads", "1", *extra]
    if proteomes:
        args += ["--proteomes", str(tmp / "proteomes.faa")]
    r = subprocess.run(args, capture_output=True, text=True)
    assert r.returncode == expect, r.stderr
    return tmp / out, r


def table(p):
    return {x.get("genome_acc") or x["query_id"]: x for x in csv.DictReader(open(p), delimiter="\t")}


@pytest.fixture
def tmp(tmp_path):
    setup_inputs(tmp_path); return tmp_path


def test_both_rules_side_by_side(tmp):
    out, _ = run(tmp)
    g = table(out / "SURVEY_PER_GENOME.tsv")
    assert (g["GX"]["protein_J1_genes_found"], g["GX"]["tblastn_genes_found"], g["GX"]["tblastn_window_genes"]) == ("3", "4", "4")
    assert g["GX"]["tblastn_window_identity_min"] == "43.3"                   # found by tblastn, below the protein rule's floor
    assert (g["GZ"]["protein_J1_genes_found"], g["GZ"]["tblastn_window_genes"]) == ("0", "4")   # genes not annotated
    assert (g["GY"]["tblastn_genes_found"], g["GY"]["tblastn_window_genes"]) == ("2", "1")       # on two contigs
    assert g["GW"]["tblastn_genes_found"] == "1"                               # g4 at 40 % cover is below the 50 % rule


def test_cover_rule_is_a_parameter(tmp):
    out, _ = run(tmp, "--tblastn-min-cover", "30")
    assert table(out / "SURVEY_PER_GENOME.tsv")["GW"]["tblastn_genes_found"] == "2"


def test_assembly_keys_and_receipt(tmp):
    out, _ = run(tmp)
    k = table(out / "ASSEMBLY_KEYS.tsv")
    assert k["GX"]["assembly_key"] == k["GZ"]["assembly_key"] == "GCA_000000099"   # identical length in genus
    gene = table(out / "SURVEY_PER_GENE.tsv")
    assert (gene["g1"]["tblastn_genomes"], gene["g1"]["tblastn_assemblies"]) == ("4", "3")
    rec = json.loads((out / "RECEIPT.json").read_text())
    assert rec["genomes"] == {"entries": 4, "assemblies": 3}
    assert rec["tblastn_window_ge5"] == {"entries": 0, "assemblies": 0} and rec["tblastn"].endswith("STANDIN")
    assert len(list((out / "tblastn").glob("*.tsv"))) == 4


def test_without_proteomes_protein_rule_not_run(tmp):
    out, _ = run(tmp, proteomes=False)
    g = table(out / "SURVEY_PER_GENOME.tsv")
    assert g["GX"]["protein_J1_genes_found"] == "not run" and g["GX"]["tblastn_window_genes"] == "4"
    assert json.loads((out / "RECEIPT.json").read_text())["rules"]["protein_J1"] == "not run"


def test_query_cut_from_antismash_zip_with_flanks(tmp):
    def cds(i, tag, aa):
        return (f"     CDS             {i * 100 + 1}..{i * 100 + 90}\n                     /locus_tag=\"{tag}\"\n"
                f"                     /translation=\"{aa}\"\n")
    whole = "LOCUS       NODE_7_length_9000_cov_5\nFEATURES             Location/Qualifiers\n" + "".join(
        cds(i, f"t{i}", aa) for i, aa in enumerate(["MAAAAAAAAA" * 3] + P + ["MCCCCCCCCC" * 3])) + "ORIGIN\n//\n"
    region = "LOCUS       NODE_7_length_9000_cov_5\nFEATURES             Location/Qualifiers\n" + "".join(
        cds(i + 2, f"t{i + 2}", aa) for i, aa in enumerate(P[1:3])) + "ORIGIN\n//\n"
    zp = tmp / "SYN.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("SYN.gbk", whole); z.writestr("NODE_7_length_9000_cov_5.region001.gbk", region)
    r = subprocess.run([sys.executable, str(TOOL), "--antismash-zip", str(zp), "--contig", "NODE_7_length_9000_cov_5", "--region", "1",
                        "--flank", "1", "--genomes", str(tmp / "genomes.tsv"), "--out", str(tmp / "z"), "--tblastn", str(tmp / "tblastn")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    q = list(csv.DictReader(open(tmp / "z/QUERY_GENES.tsv"), delimiter="\t"))
    assert [x["locus_tag"] for x in q] == ["t1", "t2", "t3", "t4"] and [x["in_region"] for x in q] == ["flank", "yes", "yes", "flank"]


@pytest.mark.parametrize("case", ["out_exists", "no_tblastn", "no_query"])
def test_refusals_exit_2(tmp, case):
    if case == "out_exists":
        (tmp / "out").mkdir(); _, r = run(tmp, expect=2)
    elif case == "no_tblastn":
        (tmp / "tblastn").unlink(); (tmp / "tblastn").mkdir(); _, r = run(tmp, expect=2)
    else:
        r = subprocess.run([sys.executable, str(TOOL), "--genomes", str(tmp / "genomes.tsv"), "--out", str(tmp / "o"),
                            "--tblastn", str(tmp / "tblastn")], capture_output=True, text=True)
        assert r.returncode == 2
    assert "REFUSED" in r.stderr
