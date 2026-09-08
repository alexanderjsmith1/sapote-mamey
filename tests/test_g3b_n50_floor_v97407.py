"""Regression test — v97401: phylo_preflight G3b gains an N50 floor (LOW_N50_BP).

Receipt: AS-150 (2026-09-01) — 1,347 contigs slipped UNDER the FRAGMENTED_CONTIGS=1,500 count
threshold, but N50 was 11.5 kb; SCG recovery was so gappy the tip took a 0.33 subs/site branch
(83% of tree depth) on the BUILT tree and had to be removed post hoc. Contig count alone misses
low-N50 shred; this floor catches it BEFORE the CPU is spent. Place in tests/.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import phylo_preflight as pf  # noqa: E402


def _fasta(tmp_path, name, lens):
    p = tmp_path / name
    with open(p, "w") as fh:
        for i, L in enumerate(lens):
            fh.write(f">c{i}\n" + "A" * L + "\n")
    return p


def test_fasta_stats_reports_n50_v97401(tmp_path):
    # 4 contigs 40/30/20/10 kb: total 100 kb, cumulative 40+30=70 >= 50 -> N50 = 30 kb
    p = _fasta(tmp_path, "x.fna", [40_000, 30_000, 20_000, 10_000])
    bp, nc, n50 = pf._fasta_stats(str(p))
    assert (bp, nc, n50) == (100_000, 4, 30_000)


def test_low_n50_shred_warns_below_count_threshold_the_AS150_case_v97401(tmp_path):
    # ~7 Mb in 1,400 x 5 kb contigs: count < FRAGMENTED_CONTIGS(1500) but N50=5 kb < LOW_N50_BP
    p = _fasta(tmp_path, "shred.fna", [5_000] * 1_400)
    fails, warns = [], []
    class R:
        def add(self, code, status, title, detail=""):
            if status == "WARN": warns.append((code, status, detail))
            elif status == "FAIL": fails.append((code, status, detail))
    pf.check_assembly_quality(R(), [str(p)])
    g3b = [d for c, s, d in warns if c == "G3b"]
    assert g3b and "N50" in g3b[0] and "shred" in g3b[0], (fails, warns)
    assert not fails, "low-N50 shred is a WARN (caption + attend), not a FAIL"


def test_healthy_genome_not_flagged_v97401(tmp_path):
    # ~7.6 Mb in 76 x 100 kb contigs: N50=100 kb — clean
    p = _fasta(tmp_path, "ok.fna", [100_000] * 76)
    fails, warns = [], []
    class R:
        def add(self, code, status, title, detail=""):
            if status == "WARN": warns.append((code, status, detail))
            elif status == "FAIL": fails.append((code, status, detail))
    pf.check_assembly_quality(R(), [str(p)])
    assert not [w for w in warns if w[0] == "G3b"] and not fails
