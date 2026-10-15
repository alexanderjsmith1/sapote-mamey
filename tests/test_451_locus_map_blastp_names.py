"""Unmatched reference-map genes may have independent annotation evidence.
Each displayed percentage must identify its comparison: top-ten database mean or named reference.
"""
import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("gap_rescue_locus_map_451", ROOT / "tools/gap_rescue_locus_map.py")
glm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glm)

REF = [{"i": k + 1, "name": f"abc{k}", "product": "enzyme", "kind": "biosynthetic", "s": k * 2.0, "e": k * 2.0 + 1.5,
        "strand": 1} for k in range(4)]
CORE = {"contig": "core", "start": 0, "end": 20000, "identity": "AS-0 / core / region001 / BGC001"}


def _genome():
    prots, rows = {}, []
    for k in range(4):
        prots[f"p{k}"] = {"tag": f"c{k}", "contig": "core", "start": 8000 + k * 2000, "end": 9500 + k * 2000,
                          "strand": 1, "contig_len": 20000}
        rows.append({"status": "PRESENT_IN_CORE", "best_protein": f"p{k}", "best_identity_pct": 80.0,
                     "reciprocal_best": True, "partner_verdict": ""})
    for j in range(3):   # unmatched genes before the matched block
        prots[f"u{j}"] = {"tag": f"u{j}", "contig": "core", "start": 1000 + j * 2000, "end": 2500 + j * 2000,
                          "strand": -1, "contig_len": 20000}
    return prots, rows


def _draw(monkeypatch, tmp_path, **kw):
    import matplotlib.pyplot as plt
    monkeypatch.setattr(glm, "reference_genes", lambda _p: (REF, 8.0))
    monkeypatch.setattr(plt, "close", lambda fig=None: None)
    prots, rows = _genome()
    return glm.draw_locus_map(tmp_path / "BGC0000000.gbk", rows, [], prots, [CORE], CORE, "AS-0", "test",
                              tmp_path / "m.png", **kw)


def test_no_names_given_draws_as_before(monkeypatch, tmp_path):
    res = _draw(monkeypatch, tmp_path)
    assert res["blastp_named"] == []
    assert "Grey labels" not in res["footnote"]


def test_unmatched_genes_with_a_blastp_name_are_named_and_matched_genes_are_not(monkeypatch, tmp_path):
    names = {"u0": {"top10_consensus_name": "acyl carrier protein", "top10_mean_identity": "84.7",
                    "function_class": "biosynthetic core", "function_class_ambiguous": "yes"},
             "c1": {"top10_consensus_name": "should not show", "top10_mean_identity": "90"}}
    res = _draw(monkeypatch, tmp_path, gene_names=names)
    assert res["blastp_named"] == ["u0"]
    assert '"<database> N%" is the mean identity of the top 10 hits in that database' in res["footnote"]


def test_another_reference_names_its_genes_and_says_so(monkeypatch, tmp_path):
    res = _draw(monkeypatch, tmp_path, gene_names={}, other_refs={"u1": ("mayamycin", 91.5)})
    assert res["blastp_named"] == ["u1"]
    assert "(mayamycin; 1 gene)" in res["footnote"]


def test_labels_say_what_the_percentage_is_measured_against():
    row = {"top10_consensus_name": "aromatase/cyclase", "top10_mean_identity": "84.4", "db": "nr"}
    assert glm._blastp_label(row) == "aromatase/cyclase (nr 84%)"
    assert glm._blastp_label(dict(row, db="ClusteredNR")) == "aromatase/cyclase (ClusteredNR 84%)"
    assert glm._blastp_label(dict(row, db="Swiss-Prot")) == "aromatase/cyclase (Swiss-Prot 84%)"
    assert glm._blastp_label(row, ("mayamycin", 82.2)) == "aromatase/cyclase (mayamycin ref 82%)"
    assert glm._blastp_label({}, ("mayamycin", 65.0)) == "unnamed protein (mayamycin ref 65%)"
    assert glm._blastp_label({"top10_consensus_name": "", "top10_mean_identity": "76.2", "db": "nr"}) == "unnamed protein (nr 76%)"
    assert glm._blastp_label({"top10_consensus_name": " ", "top10_mean_identity": "64.9", "db": "ClusteredNR"}) == \
        "unnamed protein (ClusteredNR 65%)"
    long = {"top10_consensus_name": "x" * 80, "top10_mean_identity": "70"}
    assert glm._blastp_label(long).startswith("x" * (glm.NAME_CHARS - 1) + "…")


def _run(folder, core, ref_name, rows):
    folder.mkdir()
    (folder / "gap_rescue_receipt.json").write_text(json.dumps({"core": core, "reference": "R.gbk",
                                                                "reference_name": ref_name}))
    with open(folder / "gap_rescue.tsv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["best_locus", "status", "best_identity_pct"], delimiter="\t")
        w.writeheader()
        w.writerows(rows)


def test_other_references_come_only_from_runs_of_the_same_region(tmp_path):
    core = CORE["identity"]
    _run(tmp_path / "this", core, "streptophenazine B/streptophenazine C", [])
    _run(tmp_path / "maya", core, "mayamycin", [
        {"best_locus": "u0", "status": "PRESENT_IN_CORE", "best_identity_pct": "82.2"},
        {"best_locus": "u0", "status": "PRESENT_IN_CORE", "best_identity_pct": "53.9"},
        {"best_locus": "u2", "status": "MISSING_NOT_FOUND", "best_identity_pct": "40"}])
    _run(tmp_path / "elsewhere", "AS-0 / other / region001 / BGC009", "kinamycin", [
        {"best_locus": "u1", "status": "PRESENT_IN_CORE", "best_identity_pct": "99"}])
    got = glm.load_other_references(tmp_path / "this", core)
    assert got == {"u0": ("mayamycin", 82.2)}


def test_first_name_table_wins_and_later_tables_fill_gaps(tmp_path):
    cols = ["strain", "gene", "top10_consensus_name", "top10_mean_identity", "db"]
    for name, rows in (("ncbi.tsv", [["AS-0", "g1", "ncbi name", "80", "nr"]]),
                       ("local.tsv", [["AS-0", "g1", "local name", "60", "Swiss-Prot"],
                                      ["AS-0", "g2", "only local", "55", "Swiss-Prot"],
                                      ["AS-1", "g3", "other strain", "50", "MIBiG"]])):
        (tmp_path / name).write_text("\t".join(cols) + "\n" + "".join("\t".join(r) + "\n" for r in rows))
    got = glm.load_gene_names([tmp_path / "ncbi.tsv", tmp_path / "local.tsv"], "AS-0")
    assert got["g1"]["top10_consensus_name"] == "ncbi name"
    assert got["g2"]["db"] == "Swiss-Prot"
    assert "g3" not in got
