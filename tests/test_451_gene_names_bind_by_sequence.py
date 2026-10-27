"""Gene names and BLASTp results bind to a gene by its protein, not its locus tag (card 451_gene_names_bind_by_sequence).

Locus tags are numbered per antiSMASH run. In one working gene-name table, 9,709 of 29,274 rows carried a protein length
that differs from the canonical CDS with the same tag (one tag: 635 aa in the zip, 1,574 aa in the table), and the BLASTp
identity figures joined results to genes the same way.
"""
import csv
import hashlib
import importlib.util
import json
import os
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from mamey.blastp_ingest import BLASTP_HITS_SCHEMA  # noqa: E402
from mamey.protein_binding import (bind_name_rows, header_key, protein_sha256, tag_of)  # noqa: E402


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = {"A": "M" + "A" * 99, "B": "M" + "K" * 199, "C": "M" + "L" * 149, "D": "M" + "G" * 149}   # D: same length as C
# run 1 of a genome numbered ctg1_1 = A, ctg1_2 = B; run 2 inserted a gene, so ctg1_2 = C and B moved to ctg1_3
RUN2 = {"ctg1_1": P["A"], "ctg1_2": P["C"], "ctg1_3": P["B"]}
NAME_COLS = ["strain", "gene", "aa_length", "top10_consensus_name", "top10_mean_identity", "db", "protein_sha256"]


def _row(gene, prot=None, length=None, name="n"):
    return {"strain": "AS-1", "gene": gene, "aa_length": "" if length is None else str(length),
            "top10_consensus_name": name, "top10_mean_identity": "80", "db": "nr",
            "protein_sha256": protein_sha256(prot) if prot else ""}


# --- mamey/protein_binding.py --------------------------------------------------------------------------------------------

def test_shifted_tags_do_not_carry_a_name_to_the_wrong_gene():
    # run 1's ctg1_2 (protein B) was named; in run 2 that tag is protein C, and B is ctg1_3
    bound, how, lost = bind_name_rows([_row("ctg1_2", P["B"], 200, "B name")], RUN2)
    assert set(bound) == {"ctg1_3"} and bound["ctg1_3"]["top10_consensus_name"] == "B name"
    assert how == {"sha": 1} and not lost
    # without a sha, the length (200 vs 150 aa) refuses the tag and the row is left out, never guessed
    bound, how, lost = bind_name_rows([_row("ctg1_2", None, 200, "B name")], RUN2)
    assert bound == {} and how == {"unbound_length_differs": 1} and lost == {"ctg1_2"}


def test_an_equal_length_decoy_is_rejected_by_its_sequence():
    # the row searched protein D (150 aa); run 2's ctg1_2 is C, also 150 aa: the length agrees, the sequence does not
    bound, how, _ = bind_name_rows([_row("ctg1_2", P["D"], 150)], RUN2)
    assert bound == {} and how == {"unbound_sha_not_in_genome": 1}


def test_without_a_sha_the_tag_binds_only_when_lengths_agree_within_1_aa():
    rows = [_row("ctg1_1", None, 101, "within 1"), _row("ctg1_2", None, 155, "5 off"), _row("ctg1_3", None, None, "no length"),
            _row("ctg9_9", None, 100, "no such tag")]
    bound, how, lost = bind_name_rows(rows, RUN2)
    assert set(bound) == {"ctg1_1"}
    assert how == {"length": 1, "unbound_length_differs": 1, "unbound_no_sha_no_length": 1, "unbound_tag_not_in_genome": 1}
    assert lost == {"ctg1_2", "ctg1_3", "ctg9_9"}


def test_first_bound_row_wins_and_a_failed_row_does_not_block_a_later_table():
    rows = [_row("ctg1_2", P["D"], 150, "decoy from table 1"), _row("ctg1_2", P["C"], 150, "true from table 2")]
    bound, _, lost = bind_name_rows(rows, RUN2)
    assert bound["ctg1_2"]["top10_consensus_name"] == "true from table 2" and not lost


def test_query_header_formats_in_use_are_parsed():
    assert header_key("AS-972__BGC019__ctg19_74 aa=3171 why=clustered_gap_fill") == ("AS-972", "ctg19_74")
    assert header_key("AS-973|BGC063|slot=4|role=fallback|gene=ctg87_20|node=NODE_87") == ("AS-973", "ctg87_20")
    assert header_key("AS-974|ctg4_218|541aa") == ("AS-974", "ctg4_218")
    assert header_key("AS-971_loose__BGC033__ctg4_149 aa=79") == ("AS-971", "ctg4_149")
    assert header_key("ctg25_47", "AS-979") == ("AS-979", "ctg25_47")
    assert tag_of("AS-977__BGC011__ctg4_14") == "ctg4_14" and tag_of("ctg4_14") == "ctg4_14"
    assert protein_sha256("maa*\n") == protein_sha256("MAA") != ""


# --- tools/gap_rescue_locus_map.py -----------------------------------------------------------------------------------------

def test_locus_map_names_bind_to_the_drawn_genome(tmp_path):
    glm = _load("glm_bind_451", "tools/gap_rescue_locus_map.py")
    t = tmp_path / "names.tsv"
    with open(t, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=NAME_COLS, delimiter="\t"); w.writeheader()
        w.writerow(_row("ctg1_2", P["B"], 200, "B name"))
        w.writerow(_row("ctg1_1", None, 140, "wrong length"))
    prots = {f"q{i}": {"tag": tag, "aa": seq} for i, (tag, seq) in enumerate(RUN2.items())}
    names = glm.load_gene_names(t, "AS-1", prots)
    assert set(names) == {"ctg1_3"} and names.names_unbound == 1 and names.unbound_tags == {"ctg1_1"}
    assert names.binding == {"sha": 1, "unbound_length_differs": 1}
    old = glm.load_gene_names(t, "AS-1")            # no genome given: the earlier tag join, unchanged
    assert set(old) == {"ctg1_1", "ctg1_2"}


def test_locus_map_footnote_counts_names_left_out_on_drawn_genes(monkeypatch, tmp_path):
    glm = _load("glm_foot_451", "tools/gap_rescue_locus_map.py")
    import matplotlib
    matplotlib.use("Agg")
    ref = [{"i": k + 1, "name": f"abc{k}", "product": "enzyme", "kind": "biosynthetic", "s": k * 2.0, "e": k * 2.0 + 1.5,
            "strand": 1} for k in range(4)]
    core = {"contig": "core", "start": 0, "end": 20000, "identity": "AS-1 / core / region001 / BGC001"}
    prots, rows = {}, []
    for k in range(4):
        prots[f"p{k}"] = {"tag": f"c{k}", "contig": "core", "start": 8000 + k * 2000, "end": 9500 + k * 2000, "strand": 1,
                          "contig_len": 20000, "aa": "M" + "W" * (50 + k)}
        rows.append({"status": "PRESENT_IN_CORE", "best_protein": f"p{k}", "best_identity_pct": 80.0,
                     "reciprocal_best": True, "partner_verdict": ""})
    for j in range(3):
        prots[f"u{j}"] = {"tag": f"u{j}", "contig": "core", "start": 1000 + j * 2000, "end": 2500 + j * 2000, "strand": -1,
                          "contig_len": 20000, "aa": "M" + "P" * (80 + j)}
    names = glm.GeneNames({"u0": {"top10_consensus_name": "kept", "top10_mean_identity": "70"}})
    names.binding, names.unbound_tags = {"sha": 1, "unbound_sha_not_in_genome": 2}, frozenset({"u1", "u2"})
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (ref, 8.0))
    res = glm.draw_locus_map(tmp_path / "R.gbk", rows, [], prots, [core], core, "AS-1", "test", tmp_path / "m.png",
                             gene_names=names)
    assert res["blastp_named"] == ["u0"]
    assert "2 protein-search names were left out" in res["footnote"]


# --- tools/blastp_identity_figures.py ---------------------------------------------------------------------------------------

def _store(path, rows):
    con = sqlite3.connect(path)
    con.execute(f"CREATE TABLE hits ({', '.join(f'{n} {t}' + (' NOT NULL' if nn else '') for n, t, nn in BLASTP_HITS_SCHEMA)})")
    names = [c[0] for c in BLASTP_HITS_SCHEMA]
    for r in rows:
        full = dict.fromkeys(names) | {"workspace": "claude", "bgc_id": "B1", "provenance_suspect": 0} | r
        con.execute(f"INSERT INTO hits ({', '.join(names)}) VALUES ({', '.join('?' * len(names))})", [full[n] for n in names])
    con.commit(); con.close()


def _figure_world(tmp_path):
    root = tmp_path / "ws"
    pk = root / "pk"; pk.mkdir(parents=True)
    cds = [{"locus_tag": t, "aa_length": len(s), "gene_kind": "biosynthetic",
            "gene_functions": "biosynthetic (rule-based-clusters) T1PKS: PKS_KS"} for t, s in RUN2.items()]
    (pk / "AS-1_gene_context.jsonl").write_text(json.dumps({"cds": cds}) + "\n")
    (pk / "AS-1_proteins.faa").write_text("".join(f">{t} bgc=BGC001\n{s}\n" for t, s in RUN2.items()))
    # results computed on run 1: ctg1_2 there was protein B (200 aa); ctg1_1 was A (100 aa, same as run 2)
    rows = [dict(strain="AS-1", gene="ctg1_2", channel="ncbi_nr", hit_rank=r, pct_identity=90.0 - r, source_file="old.csv",
                 aa_length=200) for r in range(1, 4)]
    rows += [dict(strain="AS-1", gene="ctg1_1", channel="ncbi_nr", hit_rank=r, pct_identity=60.0, source_file="a.csv",
                  aa_length=100) for r in range(1, 3)]
    _store(tmp_path / "snap.sqlite", rows)
    g = tmp_path / "genomes.tsv"
    g.write_text("strain\tgenus\tblock\tgene_context\nAS-1\tStreptomyces\tIsolates\tpk/AS-1_gene_context.jsonl\n")
    return root, g, tmp_path / "snap.sqlite"


def _values(out):
    return {(r["strain"], r["gene"]): r for r in csv.DictReader(open(out / "GENE_VALUES.tsv"), delimiter="\t")}


def test_figure_results_bind_by_protein_not_tag(tmp_path):
    pytest.importorskip("matplotlib")
    bif = _load("bif_bind_451", "tools/blastp_identity_figures.py")
    root, g, snap = _figure_world(tmp_path)
    base = ["--genomes", str(g), "--store", str(snap), "--root", str(root), "--figure", "by-genome"]
    # tag join: run 1's protein B lands on run 2's ctg1_2 (protein C) -- the defect
    assert bif.main(base + ["--out", str(tmp_path / "tag"), "--binding", "locus_tag"]) == 0
    assert set(_values(tmp_path / "tag")) == {("AS-1", "ctg1_1"), ("AS-1", "ctg1_2")}
    # sequence binding without an index: the 200 aa query does not fit ctg1_2 (150 aa) and is left out
    assert bif.main(base + ["--out", str(tmp_path / "len")]) == 0
    assert set(_values(tmp_path / "len")) == {("AS-1", "ctg1_1")}
    info = json.loads((tmp_path / "len" / "RUN_INFO.json").read_text())
    assert info["results_unbound"] == 1 and info["results_binding"]["AS-1"] == {"length": 1, "unbound_length_differs": 1}
    # with a query index naming protein B, the result moves to run 2's ctg1_3
    qi = tmp_path / "qi.tsv"
    qi.write_text("strain\tgene\tsource_file\tprotein_sha256\tquery_aa_length\tbinding_evidence\n"
                  f"AS-1\tctg1_2\told.csv\t{protein_sha256(P['B'])}\t200\tledger_sha\n")
    assert bif.main(base + ["--out", str(tmp_path / "sha"), "--query-index", str(qi)]) == 0
    v = _values(tmp_path / "sha")
    assert set(v) == {("AS-1", "ctg1_1"), ("AS-1", "ctg1_3")} and v[("AS-1", "ctg1_3")]["hits_used"] == "3"


# --- tools/blastp_query_index.py ---------------------------------------------------------------------------------------------

def test_query_index_reads_the_sent_query_and_confirms_saved_ones_by_length(tmp_path):
    qix = _load("qix_451", "tools/blastp_query_index.py")
    res = tmp_path / "Blastp RESULTS"
    lane, q_new, q_old = res / "_LANE_X", res / "_QUERIES_X", res / "_QUERIES_OLD_superseded"
    for d in (lane / "results/AS-1/p1", q_new / "AS-1/p1", q_old / "AS-1/p1", res / "_QUERIES_STAGING/AS-1"):
        d.mkdir(parents=True)
    sent = f">AS-1__BGC001__ctg1_3 aa=200\n{P['B']}\n".encode()
    (q_new / "AS-1/p1/q.faa").write_bytes(sent)
    (q_old / "AS-1/p1/q.faa").write_bytes(f">AS-1__BGC001__ctg1_3\n{P['C']}\n".encode())   # same path, other bytes
    with open(lane / "_ledger.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["strain", "bgc", "file", "rid", "submit_iso", "status", "query_sha256"])
        w.writerow(["AS-1", "p1", "AS-1/p1/q.faa", "R", "2026-10-12 10:00:00", "fetched", hashlib.sha256(sent).hexdigest()])
    (lane / "results/AS-1/p1/p1_blastp_top10_clustered.csv").write_text(
        "strain,gene,aa_length,hit_rank,pct_identity\nAS-1,AS-1__BGC001__ctg1_3,200,1,80\n")
    # an old result with no ledger: one saved query of the same length confirms it; a length mismatch does not
    (res / "_QUERIES_STAGING/AS-1/s.faa").write_text(f">AS-1__BGC001__ctg1_1\n{P['A']}\n>AS-1__BGC001__ctg1_2\n{P['B']}\n")
    repo = tmp_path / "BLASTp Repository/AS-1/BGC001"; repo.mkdir(parents=True)
    (repo / "BGC001_blastp_top10.csv").write_text("strain,gene,aa_length,hit_rank,pct_identity\n"
                                                 "AS-1,ctg1_1,100,1,70\nAS-1,ctg1_2,150,1,70\nAS-1,ctg7_7,90,1,70\n")
    out = tmp_path / "qi.tsv"
    assert qix.main(["--root", str(tmp_path), "--out", str(out), "--extra-csv", "Blastp RESULTS/_LANE_X/results/*/*/*.csv",
                     "--extra-csv", "BLASTp Repository/*/*/*.csv"]) == 0
    got = {(r["gene"], r["source_file"].split("/")[0]): r for r in csv.DictReader(open(out), delimiter="\t")}
    lane_row = got[("AS-1__BGC001__ctg1_3", "Blastp RESULTS")]
    assert lane_row["binding_evidence"] == "ledger_sha" and lane_row["protein_sha256"] == protein_sha256(P["B"])
    assert got[("ctg1_1", "BLASTp Repository")]["binding_evidence"] == "saved_query_length_confirmed"
    assert got[("ctg1_1", "BLASTp Repository")]["protein_sha256"] == protein_sha256(P["A"])
    assert got[("ctg1_2", "BLASTp Repository")]["binding_evidence"] == "none"     # saved B is 200 aa; the result says 150
    assert got[("ctg7_7", "BLASTp Repository")]["protein_sha256"] == ""
    # --annotate copies a name table with the sha column added; nothing is overwritten
    names = tmp_path / "names.tsv"
    names.write_text("strain\tgene\tsource_file\ttop10_consensus_name\n"
                     "AS-1\tctg1_1\tBLASTp Repository/AS-1/BGC001/BGC001_blastp_top10.csv\tA name\n")
    ann = tmp_path / "names_sha.tsv"
    assert qix.main(["--root", str(tmp_path), "--annotate", str(names), "--index", str(out), "--out", str(ann)]) == 0
    row = next(csv.DictReader(open(ann), delimiter="\t"))
    assert row["protein_sha256"] == protein_sha256(P["A"]) and row["top10_consensus_name"] == "A name"
    with pytest.raises(SystemExit):
        qix.main(["--root", str(tmp_path), "--annotate", str(names), "--index", str(out), "--out", str(ann)])


def test_ledger_copy_changed_after_sending_is_not_trusted(tmp_path):
    qix = _load("qix2_451", "tools/blastp_query_index.py")
    res = tmp_path / "Blastp RESULTS"
    (res / "_L/results/AS-1/p1").mkdir(parents=True); (res / "_QUERIES_L/AS-1/p1").mkdir(parents=True)
    q = res / "_QUERIES_L/AS-1/p1/q.faa"
    q.write_text(f">AS-1__BGC001__ctg1_2\n{P['C']}\n")
    with open(res / "_L/_ledger.csv", "w", newline="") as fh:   # an older ledger: no query_sha256 column
        csv.writer(fh).writerows([["strain", "bgc", "file", "submit_iso", "status"],
                                  ["AS-1", "p1", "AS-1/p1/q.faa", "2026-01-01 00:00:00", "fetched"]])
    (res / "_L/results/AS-1/p1/r.csv").write_text("strain,gene,hit_rank,pct_identity\nAS-1,ctg1_2,1,80\n")
    out = tmp_path / "qi.tsv"
    qix.main(["--root", str(tmp_path), "--out", str(out), "--extra-csv", "Blastp RESULTS/_L/results/*/*/*.csv"])
    row = next(csv.DictReader(open(out), delimiter="\t"))
    assert row["binding_evidence"] == "none" and row["protein_sha256"] == ""   # file modified after the 1 Jan submit
    os.utime(q, (1.0e9, 1.0e9))                                                 # 2001: before the submit
    out2 = tmp_path / "qi2.tsv"
    qix.main(["--root", str(tmp_path), "--out", str(out2), "--extra-csv", "Blastp RESULTS/_L/results/*/*/*.csv"])
    row = next(csv.DictReader(open(out2), delimiter="\t"))
    assert row["binding_evidence"] == "ledger_unchanged" and row["protein_sha256"] == protein_sha256(P["C"])


def test_query_length_is_recovered_from_the_lane_blast_xml(tmp_path):
    qix = _load("qix3_451", "tools/blastp_query_index.py")
    res = tmp_path / "Blastp RESULTS"
    (res / "_L/results/AS-1/BGC001").mkdir(parents=True); (res / "_L/xml").mkdir(); (res / "_QUERIES_L/AS-1/BGC001").mkdir(parents=True)
    (res / "_QUERIES_L/AS-1/BGC001/q.faa").write_text(f">AS-1|BGC001|gene=ctg1_2\n{P['C']}\n")   # rewritten after sending
    with open(res / "_L/_ledger.csv", "w", newline="") as fh:
        csv.writer(fh).writerows([["strain", "bgc", "file", "rid", "submit_iso", "status"],
                                  ["AS-1", "BGC001", "AS-1/BGC001/q.faa", "RID1", "2026-01-01 00:00:00", "fetched"]])
    (res / "_L/xml/RID1-Alignment.xml").write_text(
        "<BlastXML2><Search><query-id>Query_1</query-id><query-title>AS-1|BGC001|slot=1|gene=ctg1_2|aa=200</query-title>\n"
        "<query-len>200</query-len></Search><Search><query-title>AS-1|BGC001|gene=ctg1_1</query-title><query-len>100</query-len>"
        "</Search></BlastXML2>")
    (res / "_L/results/AS-1/BGC001/r.csv").write_text("strain,gene,hit_rank,pct_identity\nAS-1,ctg1_2,1,80\nAS-1,ctg1_1,1,70\n")
    out = tmp_path / "qi.tsv"
    qix.main(["--root", str(tmp_path), "--out", str(out), "--extra-csv", "Blastp RESULTS/_L/results/*/*/*.csv"])
    got = {r["gene"]: r for r in csv.DictReader(open(out), delimiter="\t")}
    assert got["ctg1_2"]["binding_evidence"] == "xml_query_length" and got["ctg1_2"]["query_aa_length"] == "200"
    assert got["ctg1_2"]["protein_sha256"] == ""       # a length is not a protein: only the length rule may use it
    # bound to run 2 (ctg1_2 = C, 150 aa): the 200 aa query is refused; ctg1_1 (100 aa) binds by length
    bound, how, _ = bind_name_rows([{"gene": g, "aa_length": got[g]["query_aa_length"]} for g in ("ctg1_2", "ctg1_1")], RUN2)
    assert set(bound) == {"ctg1_1"} and how == {"length": 1, "unbound_length_differs": 1}


def test_lane_xml_length_is_used_only_when_every_xml_agrees(tmp_path):
    qix = _load("qix4_451", "tools/blastp_query_index.py")
    res = tmp_path / "Blastp RESULTS"
    (res / "_L/results/AS-1/BGC009").mkdir(parents=True); (res / "_L/xml").mkdir()
    (res / "_L/_ledger.csv").write_text("strain,bgc,file,rid,submit_iso,status\n")       # rotated: no row for BGC009
    x = "<Search><query-title>AS-1|BGC009|gene={g}</query-title><query-len>{n}</query-len></Search>"
    (res / "_L/xml/R1-Alignment.xml").write_text(x.format(g="ctg1_1", n=100) + x.format(g="ctg1_2", n=200))
    (res / "_L/xml/R2-Alignment.xml").write_text(x.format(g="ctg1_1", n=100) + x.format(g="ctg1_2", n=150))  # ctg1_2 disagrees
    (res / "_L/results/AS-1/BGC009/r.csv").write_text("strain,gene,hit_rank,pct_identity\nAS-1,ctg1_1,1,80\nAS-1,ctg1_2,1,70\n")
    out = tmp_path / "qi.tsv"
    qix.main(["--root", str(tmp_path), "--out", str(out), "--extra-csv", "Blastp RESULTS/_L/results/*/*/*.csv"])
    got = {r["gene"]: r for r in csv.DictReader(open(out), delimiter="\t")}
    assert (got["ctg1_1"]["binding_evidence"], got["ctg1_1"]["query_aa_length"]) == ("xml_lane_one_length", "100")
    assert (got["ctg1_2"]["binding_evidence"], got["ctg1_2"]["query_aa_length"]) == ("none", "")
