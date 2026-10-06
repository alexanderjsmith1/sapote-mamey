"""Partner checks, automatic reference choice and the all-regions runner for the gap-rescue tool.

The owner, 2026-09-30, on four small contigs drawn beside an AS nucleoside cluster: "the question is whether they are part of
a nucleoside BGC, or if the matching genes are noise?" Checked by hand: two were housekeeping operons (a ThyX beside
DapA/DapB; ArgB inside the arginine operon, whose best MIBiG match was another cluster), one a common-family paralog, and
one a real pair. Then: "note this process you are doing should be part of the rggmci". And: "If we can patch this
ability into sapote mamey just like this I will be satisfied" (the map with an automatically chosen reference).
"""
import csv
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

from mamey import diamond_align as da

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("split_gene_check_helpers_pc",
                                              ROOT / "tests/test_445_gap_rescue_split_gene_check.py")
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
gdr = helpers.gdr
sys.path.insert(0, str(ROOT / "tools"))
spec2 = importlib.util.spec_from_file_location("gap_rescue_all_regions", ROOT / "tools/gap_rescue_all_regions.py")
allr = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(allr)


def _p(tag, contig, start, kind=""):
    return {"tag": tag, "contig": contig, "start": start, "end": start + 900, "strand": 1, "contig_len": 50000,
            "aa": "M" + "A" * 300, "kind": kind}


CORE = {"contig": "core", "start": 0, "end": 10000, "n": 1, "identity": "T / core / region001 / BGC001", "edge": "True"}


def _row(i, name, status, pid, ident=50.0):
    return {"reference_gene": i, "name": name, "status": status, "best_protein": pid, "best_identity_pct": ident}


def _hit(q, s, pident=60.0, cov=90.0, bits=300.0):
    return {"qseqid": q, "sseqid": s, "pident": pident, "qcovhsp": cov, "bitscore": bits}


def test_verdicts_from_paralogs_adjacency_and_lone_finds():
    prots = {"c1": _p("c1", "core", 1000), "x1": _p("x1", "ctgX", 1000), "x2": _p("x2", "ctgX", 5000),
             "y1": _p("y1", "ctgY", 1000), "z1": _p("z1", "ctgZ", 1000)}
    prots.update({f"p{i}": _p(f"p{i}", f"far{i}", 1000) for i in range(6)})
    rows = [_row(1, "r1", "PRESENT_IN_CORE", "c1"), _row(2, "r2", "MISSING_FOUND_CLEAR", "x1"),
            _row(3, "r3", "MISSING_FOUND_CLEAR", "x2"), _row(4, "r4", "MISSING_FOUND_CLEAR", "y1"),
            _row(5, "r5", "MISSING_FOUND_AMBIGUOUS", "z1")]
    hits = [_hit("g002", "x1"), _hit("g003", "x2"), _hit("g004", "y1"), _hit("g005", "z1")]
    hits += [_hit("g005", f"p{i}", 40.0) for i in range(6)]          # r5 has six more copies in the genome
    summary = gdr.partner_checks(rows, prots, hits, CORE, "BGC0000001")
    v = {r["name"]: r.get("partner_verdict") for r in rows}
    assert v == {"r1": None, "r2": "SUPPORTED", "r3": "SUPPORTED", "r4": "SINGLE_GENE", "r5": "PARALOG_FAMILY"}
    assert summary["reciprocal_mibig"].startswith("not run")


def test_a_find_whose_best_mibig_match_is_another_cluster_is_a_paralog_family_member(monkeypatch):
    prots = {"c1": _p("c1", "core", 1000), "y1": _p("y1", "ctgY", 1000)}
    rows = [_row(1, "r1", "PRESENT_IN_CORE", "c1"), _row(2, "r2", "MISSING_FOUND_CLEAR", "y1", 57.0)]
    monkeypatch.setattr(da, "search_db", lambda *a, **k: {"ok": True, "hits": [
        _hit("y1", "BGC0000002|7", 88.0, bits=600.0), _hit("y1", "BGC0000001|3", 57.0, bits=300.0)]})
    gdr.partner_checks(rows, prots, [_hit("g002", "y1")], CORE, "BGC0000001", mibig_db="mibig.dmnd")
    assert rows[1]["partner_verdict"] == "PARALOG_FAMILY"
    assert (rows[1]["reciprocal_best_mibig"], rows[1]["reciprocal_reference_identity"]) == ("BGC0000002", 57.0)
    # a reference outside MIBiG cannot be judged by the reciprocal search
    rows[1].pop("partner_verdict")
    s = gdr.partner_checks(rows, prots, [_hit("g002", "y1")], CORE, "MF055656", mibig_db="mibig.dmnd")
    assert rows[1]["partner_verdict"] == "SINGLE_GENE" and "not judged" in s["reciprocal_mibig"]


def test_a_lone_find_beside_housekeeping_genes_is_set_aside(monkeypatch):
    prots = {"c1": _p("c1", "core", 1000), "h0": _p("h0", "ctgH", 1000), "h1": _p("h1", "ctgH", 3000),
             "h2": _p("h2", "ctgH", 5000), "h3": _p("h3", "ctgH", 7000)}
    rows = [_row(1, "r1", "PRESENT_IN_CORE", "c1"), _row(2, "r2", "MISSING_FOUND_CLEAR", "h1")]
    monkeypatch.setattr(gdr, "_pfam_names", lambda seqs, hmm, cpus=4: {"h0": ["DHDPS"], "h2": ["DapB_N", "DapB_C"],
                                                                       "h3": ["bPH_12"]})
    gdr.partner_checks(rows, prots, [_hit("g002", "h1")], CORE, "BGC0000001", pfam_hmm="Pfam-A.hmm")
    assert rows[1]["partner_verdict"] == "HOUSEKEEPING_CONTEXT" and rows[1]["housekeeping_neighbours"] == 2
    assert "h0:DHDPS" in rows[1]["neighbour_pfams"]


def _mibig(tmp_path, sizes):
    d = tmp_path / "mibig"
    d.mkdir()
    for acc, kb in sizes.items():
        (d / f"{acc}.gbk").write_text(f"LOCUS       {acc}   {int(kb * 1000)} bp    DNA     linear   UNK 01-JAN-1980\n//\n")
    return d


def test_discovery_needs_two_proteins_a_biosynthetic_anchor_and_a_cluster_sized_reference(tmp_path):
    mdir = _mibig(tmp_path, {"BGC0000001": 40, "BGC0000002": 4150, "BGC0000003": 30, "BGC0000004": 20})
    prots = {"a": _p("a", "core", 1, "biosynthetic"), "b": _p("b", "core", 2000, "transport"),
             "c": _p("c", "core", 4000, "regulatory"), "d": _p("d", "core", 6000, "biosynthetic-additional")}
    hits = ([_hit(f"R|{x}", "BGC0000002|1", 70.0, bits=900.0) for x in "abcd"]      # a whole genome: too big
            + [_hit("R|a", "BGC0000001|2", 45.0), _hit("R|d", "BGC0000001|5", 40.0)]
            + [_hit("R|b", "BGC0000003|1", 60.0), _hit("R|c", "BGC0000003|2", 60.0)]   # no biosynthetic anchor
            + [_hit("R|a", "BGC0000004|1", 30.0), _hit("R|d", "BGC0000004|2", 30.0)])  # under 35%
    got = gdr.discover_references({"R": list("abcd")}, prots, None, mdir, hits=hits)["R"]
    assert got["reference"].name == "BGC0000001.gbk" and got["proteins"] == 2 and not got["tied"]


def test_the_kcb_rank_one_hit_is_the_reference_when_no_reference_is_given(tmp_path):
    z = helpers._genome(tmp_path)
    kcb = ("ClusterBlast scores for ctgA\n\nTable of genes, locations, strands and annotations of query cluster:\n"
           "a1\t1001\t1900\t+\t\t\n\nSignificant hits: \n1. BGC0000999\tref cluster compound\n\nDetails:\n\n>>\n"
           "1. BGC0000999\nSource: ref cluster compound\nType: NRP\n"
           "Number of proteins with BLAST hits to this cluster: 1\nCumulative BLAST score: 500\n\n"
           "Table of genes, locations, strands and annotations of subject cluster:\ng001\t1\t900\t+\tenzyme\n\n"
           "Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):\n"
           "a1\tg001\t80\t500\t99.0\t1e-100\n")
    with zipfile.ZipFile(z, "a") as zf:
        zf.writestr("knownclusterblast/ctgA_c1.txt", kcb)
    ref = helpers._reference(tmp_path)          # tmp_path/BGC0000999.gbk
    rows = helpers.BASE + [("g003", "q000003", 60, 50, 200, 1, 150)]
    hits = tmp_path / "hits.tsv"
    hits.write_text("".join("\t".join(map(str, r)) + "\n" for r in rows))
    out = tmp_path / "out"
    assert gdr.main(["--zip", str(z), "--label", "T", "--core", "ctgA.region001", "--mibig-dir", str(ref.parent),
                     "--out", str(out), "--hits", str(hits), "--no-figure"]) == 0
    rc = json.loads((out / "gap_rescue_receipt.json").read_text())
    assert rc["reference"] == "BGC0000999.gbk" and rc["reference_source"] == "KnownClusterBlast rank 1"
    assert rc["reference_name"] == "ref cluster compound"
    header = next(csv.reader(open(out / "gap_rescue.tsv"), delimiter="\t"))
    assert header[-len(gdr.PARTNER_CHECK_COLS):] == gdr.PARTNER_CHECK_COLS


def test_without_a_reference_or_a_mibig_folder_the_tool_says_why(tmp_path):
    z = helpers._genome(tmp_path)
    with pytest.raises(SystemExit, match="no reference"):
        gdr.main(["--zip", str(z), "--label", "T", "--core", "ctgA.region001", "--out", str(tmp_path / "o")])


def test_the_all_regions_runner_reads_the_genome_once_and_summarises_every_region(tmp_path, monkeypatch):
    rgdr = allr.gdr  # the runner's own copy of the tool module
    z = helpers._genome(tmp_path)
    ref = helpers._reference(tmp_path)
    rows = [dict(zip(["qseqid", "sseqid", "pident", "qcovhsp", "bitscore", "qstart", "qend"], r))
            for r in helpers.BASE + [("g003", "q000003", 60, 50, 200, 1, 150)]]
    monkeypatch.setattr(rgdr, "run_diamond", lambda ref_, prots, threads, sens=None: rows)
    calls = []
    real = rgdr.load_genome

    def load_once(*a):  # the synthetic genome carries no gene_kind; mark its proteins biosynthetic for the anchor rule
        calls.append(1)
        prots, regions = real(*a)
        for p in prots.values():
            p["kind"] = "biosynthetic"
        return prots, regions
    monkeypatch.setattr(rgdr, "load_genome", load_once)
    region_proteins = [f"q00000{i}" for i in (1, 2, 3)]
    disc = [{"qseqid": f"T / ctgA / region001 / BGC001|{p}", "sseqid": "BGC0000999|1", "pident": 60.0,
             "qcovhsp": 90.0, "bitscore": 300.0} for p in region_proteins]
    out = tmp_path / "all"
    got = allr.run_all(z, "T", out, ref.parent, None, {}, None, False, "ultra-sensitive", 1, False,
                       discovery_hits=disc)
    assert calls == [1]
    (r,) = [x for x in got if x["check"] == "run"]
    assert r["reference"] == "BGC0000999" and r["reference_source"].startswith("DIAMOND >= 35%")
    assert (out / "SUMMARY.tsv").exists() and (out / "gap_rescue_proteins.faa").exists()
    assert not (out / r["folder"] / "gap_rescue_proteins.faa").exists()


def test_discovery_survives_diamond_cutting_query_names_at_the_first_space(tmp_path, monkeypatch):
    """Region identities contain spaces ("T / ctgA / region001 / BGC001"); DIAMOND reports only the first word."""
    mdir = _mibig(tmp_path, {"BGC0000001": 40})
    prots = {"a": _p("a", "core", 1, "biosynthetic"), "d": _p("d", "core", 6000, "biosynthetic-additional")}

    def fake_search(query_fasta, db, **kw):
        ids = [line[1:].split()[0] for line in open(query_fasta) if line.startswith(">")]
        return {"ok": True, "hits": [_hit(i, "BGC0000001|1", 50.0) for i in ids]}
    monkeypatch.setattr(da, "search_db", fake_search)
    got = gdr.discover_references({"T / ctgA / region001 / BGC001": ["a", "d"]}, prots, "mibig.dmnd", mdir)
    assert got["T / ctgA / region001 / BGC001"]["reference"].name == "BGC0000001.gbk"
