"""Lane CLAUDE_M5_v9.7.455_pks_piece_map: tools/pks_piece_map.py on synthetic GenBank files.
Invented reference proteins (synA, synB), modules and contigs (SYN_*). A stand-in `diamond` aligns each genome
protein to each reference protein at its best ungapped offset and writes real outfmt-6 rows (no DIAMOND needed)."""
import csv
import json
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/pks_piece_map.py"

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
q, d = fa(a[a.index("-q") + 1]), fa(a[a.index("-d") + 1])
for qi, qs in q.items():
    for di, ds in d.items():
        if len(ds) > len(qs): continue
        best = max(range(len(qs) - len(ds) + 1), key=lambda o: sum(x == y for x, y in zip(qs[o:], ds)))
        m = sum(x == y for x, y in zip(qs[best:], ds)); pid = 100.0 * m / len(ds)
        if pid >= 30:
            print(f"{{qi}}\\t{{di}}\\t{{pid:.1f}}\\t{{len(ds)}}\\t{{best + 1}}\\t{{best + len(ds)}}\\t1\\t{{len(ds)}}\\t1e-50\\t{{m}}")
'''

ALPHA = "ACDEFGHIKLMNPQRSTVWY"


def protein(n, seed):
    """A non-repeating invented sequence (linear congruential generator), so each piece aligns at one offset only."""
    x, out = seed * 7919 + 1, ["M"]
    for _ in range(n - 1):
        x = (x * 1103515245 + 12345) % 2**31; out.append(ALPHA[(x >> 16) % 20])
    return "".join(out)


SYNA, SYNB = protein(1600, 1), protein(1500, 2)


def qual(key, value):
    return f'                     /{key}="{value}"\n'


def gbk_record(name, length, feats):
    out = [f"LOCUS       {name}  {length} bp    DNA     linear   BCT 01-JAN-2026\n", f"VERSION     {name}\n",
           "FEATURES             Location/Qualifiers\n"]
    for kind, loc, quals in feats:
        out.append(f"     {kind:<16}{loc}\n")
        for k, v in quals:
            out.append(qual(k, v) if v is not None else f"                     /{k}\n")
    out.append("ORIGIN\n        1 " + ("acgt" * (length // 4 + 1))[:length] + "\n//\n")
    return "".join(out)


def reference_gbk(path, modules=True):
    feats = [("CDS", "1..4800", [("gene", "synA"), ("locus_tag", "synA"), ("translation", SYNA)]),
             ("CDS", "5001..9500", [("gene", "synB"), ("locus_tag", "synB"), ("translation", SYNB)]),
             ("CDS", "9601..9900", [("gene", "synC"), ("locus_tag", "synC"), ("translation", protein(100, 3))])]
    if modules:
        for tag, doms in (("synA", [(0, 300, "PKS_KS"), (320, 700, "PKS_AT"), (800, 1200, "PKS_KS"), (1220, 1600, "PKS_AT")]),
                          ("synB", [(0, 700, "PKS_KS"), (720, 1500, "PKS_AT")])):
            ids = []
            for i, (s, e, d) in enumerate(doms):
                did = f"nrpspksdomains_{tag}_{d}.{i + 1}"; ids.append(did)
                feats.append(("aSDomain", "1..10", [("aSDomain", d), ("domain_id", did), ("locus_tag", tag),
                                                    ("protein_start", str(s)), ("protein_end", str(e))]))
            for j in range(0, len(ids), 2):
                feats.append(("aSModule", "1..10", [("domains", ids[j]), ("domains", ids[j + 1]), ("locus_tags", tag), ("complete", None)]))
    Path(path).write_text(gbk_record("SYNREF", 10000, feats))


def genome_gbk(path, pieces):
    """pieces: list of (contig, contig_len, [(cds_start, protein), ...])."""
    recs = []
    for contig, L, cds in pieces:
        feats = [("CDS", f"{s}..{s + 3 * len(p) - 1}", [("locus_tag", f"{contig}_{i + 1}"), ("translation", p)]) for i, (s, p) in enumerate(cds)]
        recs.append(gbk_record(contig, L, feats))
    Path(path).write_text("".join(recs))


def mutate(s, every):
    return "".join(("W" if c != "W" else "Y") if i % every == 0 else c for i, c in enumerate(s))


TILED = [("SYN_c1", 1803, [(1, SYNA[0:600])]),                          # synA 1-600, CDS from base 1: at the contig start
         ("SYN_c2", 1830, [(10, SYNA[594:1200])]),                      # synA 595-1200: overlaps the first piece by 6 aa
         ("SYN_c3", 2702, [(1, SYNA[1200:1600]), (1501, SYNB[0:400])]),  # synA end + synB start on one contig: a junction
         ("SYN_c4", 3400, [(1, SYNB[400:1500])])]


@pytest.fixture
def env(tmp_path):
    ref = tmp_path / "ref.gbk"; reference_gbk(ref)
    dmd = tmp_path / "diamond"; dmd.write_text(STANDIN.format(py=sys.executable)); dmd.chmod(dmd.stat().st_mode | stat.S_IEXEC)
    return tmp_path, ref, dmd


def run(tmp_path, ref, dmd, genome, *extra, out="out"):
    return subprocess.run([sys.executable, str(TOOL), "--reference-gbk", str(ref), "--genome", str(genome), "--label", "SYN-1",
                           "--out", str(tmp_path / out), "--diamond", str(dmd), "--threads", "1", *extra], capture_output=True, text=True)


def tsv(p):
    return list(csv.DictReader(open(p), delimiter="\t"))


def test_tiled_pieces_modules_gaps_and_junction(env):
    tmp_path, ref, dmd = env
    g = tmp_path / "genome.gbk"; genome_gbk(g, TILED)
    r = run(tmp_path, ref, dmd, g); assert r.returncode == 0, r.stderr
    calls = {x["ref_protein"]: x for x in tsv(tmp_path / "out/PKS_PROTEIN_CALLS.tsv")}
    assert set(calls) == {"synA", "synB"}                                            # synC is under the 1,500 aa cut
    assert (calls["synA"]["call"], calls["synA"]["pieces"], calls["synA"]["largest_overlap_aa"]) == ("TILED", "3", "6")
    assert (calls["synB"]["call"], calls["synB"]["ref_covered_pct"]) == ("TILED", "100")
    mods = tsv(tmp_path / "out/PKS_PIECE_MAP.tsv")
    assert len(mods) == 3 and all(m["module_covered_pct"] == "100" for m in mods)
    assert [m["domains"] for m in mods][:2] == ["KS-AT", "KS-AT"]
    assert tsv(tmp_path / "out/PKS_GAPS.tsv") == []
    j = tsv(tmp_path / "out/PKS_JUNCTIONS.tsv")
    assert [(x["contig"], x["reference_proteins"]) for x in j] == [("SYN_c3", "synA + synB")]
    assert tsv(tmp_path / "out/PKS_PIECES.tsv")[0]["at_contig_end"] == "yes"
    assert "TILED" in (tmp_path / "out/PKS_PIECE_MAP.txt").read_text()


def test_a_piece_inside_another_makes_the_call_overlapping(env):
    tmp_path, ref, dmd = env
    g = tmp_path / "genome.gbk"; genome_gbk(g, TILED + [("SYN_c5", 1500, [(200, SYNA[100:400])])])
    assert run(tmp_path, ref, dmd, g).returncode == 0
    calls = {x["ref_protein"]: x for x in tsv(tmp_path / "out/PKS_PROTEIN_CALLS.tsv")}
    assert calls["synA"]["call"] == "OVERLAPPING" and "ks_module_placement" in calls["synA"]["note"]
    assert calls["synB"]["call"] == "TILED"


def test_low_identity_piece_is_left_out_but_reported_per_module(env):
    tmp_path, ref, dmd = env
    g = tmp_path / "genome.gbk"; genome_gbk(g, [("SYN_c1", 1803, [(1, SYNA[0:600])]), ("SYN_c9", 3000, [(300, mutate(SYNA[800:1600], 3))])])
    assert run(tmp_path, ref, dmd, g).returncode == 0
    pieces = tsv(tmp_path / "out/PKS_PIECES.tsv")
    assert {p["contig"] for p in pieces if p["ref_protein"] == "synA"} == {"SYN_c1"}       # the ~67 % piece is not a piece
    m2 = [m for m in tsv(tmp_path / "out/PKS_PIECE_MAP.tsv") if m["ref_protein"] == "synA" and m["module"] == "2"][0]
    assert m2["n_pieces"] == "0" and 60 < float(m2["best_identity_any_hsp_pct"]) < 85
    gaps = tsv(tmp_path / "out/PKS_GAPS.tsv")
    assert [(x["ref_protein"], x["gap_start"], x["gap_end"]) for x in gaps if x["ref_protein"] == "synA"] == [("synA", "601", "1600")]
    calls = {x["ref_protein"]: x["call"] for x in tsv(tmp_path / "out/PKS_PROTEIN_CALLS.tsv")}
    assert calls["synB"] == "NO_PIECES"


def test_antismash_zip_input_reads_the_whole_genome_genbank(env):
    tmp_path, ref, dmd = env
    g = tmp_path / "genome.gbk"; genome_gbk(g, TILED)
    z = tmp_path / "SYN-1.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("SYN-1.gbk", g.read_text()); zf.writestr("SYN_c3.region001.gbk", "LOCUS small\n//\n")
    assert run(tmp_path, ref, dmd, z).returncode == 0
    rec = json.loads((tmp_path / "out/RECEIPT.json").read_text())
    assert rec["genome"]["member"] == "SYN-1.gbk" and rec["calls"] == {"synA": "TILED", "synB": "TILED"}


@pytest.mark.parametrize("case", ["no_modules", "too_short", "no_diamond", "out_exists"])
def test_refusals_exit_2(env, case):
    tmp_path, ref, dmd = env
    g = tmp_path / "genome.gbk"; genome_gbk(g, TILED)
    extra = []
    if case == "no_modules":
        reference_gbk(ref, modules=False)
    elif case == "too_short":
        extra = ["--min-ref-length", "5000"]
    elif case == "no_diamond":
        dmd = tmp_path / "missing_diamond"
    else:
        (tmp_path / "out").mkdir()
    r = run(tmp_path, ref, dmd, g, *extra)
    assert r.returncode == 2 and "REFUSED" in r.stderr
